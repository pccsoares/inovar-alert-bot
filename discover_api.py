"""
API Discovery Script - Logs all network requests to find API endpoints.

This script runs the scraper with network interception enabled to capture
all HTTP requests and responses, allowing us to discover the backend APIs.

Usage:
    1. Ensure local.settings.json exists with valid credentials
    2. Install dependencies: pip install -r requirements.txt
    3. Install Playwright: playwright install chromium
    4. Run: python discover_api.py
"""
import os
import json
import sys
from pathlib import Path
from datetime import datetime

# Fix Windows encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.sync_api import sync_playwright


# Store captured requests
captured_requests = []


def log_request(request):
    """Log HTTP request details."""
    captured_requests.append({
        'timestamp': datetime.now().isoformat(),
        'method': request.method,
        'url': request.url,
        'headers': dict(request.headers),
        'post_data': request.post_data if request.method in ['POST', 'PUT', 'PATCH'] else None
    })


def log_response(response):
    """Log HTTP response details."""
    for req in reversed(captured_requests):
        if req['url'] == response.url and 'status' not in req:
            req['status'] = response.status
            req['status_text'] = response.status_text
            req['response_headers'] = dict(response.headers)

            # Try to capture response body for API calls
            if '/api/' in response.url and response.status == 200:
                try:
                    content_type = response.headers.get('content-type', '')
                    if 'json' in content_type.lower():
                        body = response.body()
                        req['response_body'] = body.decode('utf-8')[:1000]  # First 1000 chars
                except:
                    pass
            break


def load_config_from_file():
    """Load configuration from local.settings.json."""
    settings_file = Path(__file__).parent / "local.settings.json"

    if not settings_file.exists():
        print("❌ ERROR: local.settings.json not found!")
        print("\n📝 Please create it from local.settings.json.example:")
        print("   copy local.settings.json.example local.settings.json")
        print("   Then edit it with your credentials.\n")
        sys.exit(1)

    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
            return settings.get('Values', {})
    except Exception as e:
        print(f"❌ ERROR: Failed to load local.settings.json: {e}")
        sys.exit(1)


def discover_apis():
    """Run the scraper with network interception to discover APIs."""
    print("=" * 70)
    print("🔍 API DISCOVERY - NETWORK REQUEST CAPTURE")
    print("=" * 70)
    print()

    # Load configuration
    print("📋 Loading configuration from local.settings.json...")
    config = load_config_from_file()

    username = config.get('INOVAR_USERNAME')
    password = config.get('INOVAR_PASSWORD')
    login_url = config.get('INOVAR_LOGIN_URL', 'https://aevf.inovarmais.com/consulta/app/index.html#/login')
    home_url = config.get('INOVAR_HOME_URL', 'https://aevf.inovarmais.com/consulta/app/index.html#/home')

    # Validate required config
    if not username or not password:
        print("❌ ERROR: INOVAR_USERNAME or INOVAR_PASSWORD not set in local.settings.json")
        sys.exit(1)

    print(f"   Username: {username}")
    print(f"   Login URL: {login_url}")
    print(f"   Home URL: {home_url}")
    print()

    # Run scraper with network interception
    print("🌐 Starting browser with network monitoring...")
    print("-" * 70)
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Show browser to see what's happening
        context = browser.new_context()
        page = context.new_page()

        # Enable network interception
        page.on('request', log_request)
        page.on('response', log_response)

        try:
            # Step 1: Navigate to login page
            print("🔐 Step 1: Navigating to login page...")
            page.goto(login_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            print(f"   Captured {len(captured_requests)} requests so far")
            print()

            # Step 2: Login
            print("🔐 Step 2: Performing login...")

            # Find and fill username
            username_input = page.locator("input[type='text'], input[type='number'], input:not([type='password'])").first
            username_input.click()
            page.wait_for_timeout(500)
            username_input.fill(username)
            page.wait_for_timeout(500)

            # Find and fill password
            password_input = page.locator("input[type='password']").first
            password_input.click()
            page.wait_for_timeout(500)
            password_input.fill(password)
            page.wait_for_timeout(1000)

            # Submit
            submit_button = page.locator("button[type='submit'], button:has-text('Entrar')").first
            if submit_button.is_visible():
                submit_button.click()
            else:
                password_input.press("Enter")

            # Wait for login response
            page.wait_for_timeout(5000)
            page.wait_for_load_state("networkidle", timeout=15000)
            print(f"   Login complete. Captured {len(captured_requests)} requests so far")
            print()

            # Step 3: Navigate to home page
            print("🏠 Step 3: Navigating to home page...")
            page.goto(home_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            print(f"   Captured {len(captured_requests)} requests so far")
            print()

            # Step 4: Navigate to comportamento page
            comportamento_url = "https://aevf.inovarmais.com/consulta/app/index.html#/comportamento"
            print("⚠️  Step 4: Navigating to comportamento page...")
            page.goto(comportamento_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            print(f"   Captured {len(captured_requests)} requests so far")
            print()

            # Keep browser open for manual inspection
            print("✅ Network capture complete!")
            print()
            print("=" * 70)
            print("📊 CAPTURED REQUESTS SUMMARY")
            print("=" * 70)
            print()

            # Filter and display API requests
            api_requests = [r for r in captured_requests if '/api/' in r['url']]

            print(f"Total requests captured: {len(captured_requests)}")
            print(f"API requests found: {len(api_requests)}")
            print()

            if api_requests:
                print("🔍 API ENDPOINTS DISCOVERED:")
                print("-" * 70)
                for i, req in enumerate(api_requests, 1):
                    print(f"\n[{i}] {req['method']} {req['url']}")
                    print(f"    Status: {req.get('status', 'N/A')}")
                    if req.get('post_data'):
                        print(f"    POST Data: {req['post_data'][:200]}")
                    if req.get('response_body'):
                        print(f"    Response (preview): {req['response_body'][:200]}...")
            else:
                print("⚠️  No API requests found. The portal might use:")
                print("   - Server-side rendering (all HTML generated server-side)")
                print("   - APIs with different patterns (not /api/)")
                print()
                print("Let's check all requests to key endpoints:")
                print("-" * 70)

                # Show all requests to the portal domain
                portal_requests = [r for r in captured_requests
                                  if 'inovarmais.com' in r['url']
                                  and r['method'] in ['GET', 'POST']
                                  and r.get('status') == 200]

                for i, req in enumerate(portal_requests[:20], 1):  # Show first 20
                    print(f"\n[{i}] {req['method']} {req['url']}")
                    print(f"    Status: {req.get('status', 'N/A')}")
                    if req.get('post_data'):
                        print(f"    POST Data: {req['post_data'][:200]}")

            print()
            print("=" * 70)
            print()

            # Save full capture to file
            output_file = Path(__file__).parent / "api_capture.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(captured_requests, f, indent=2, ensure_ascii=False)

            print(f"💾 Full request capture saved to: {output_file}")
            print()
            print("Press Enter to close browser and exit...")
            input()

        except Exception as e:
            print()
            print("=" * 70)
            print("❌ ERROR")
            print("=" * 70)
            print(f"Exception occurred: {e}")
            import traceback
            traceback.print_exc()

            # Still save what we captured
            output_file = Path(__file__).parent / "api_capture.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(captured_requests, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Partial capture saved to: {output_file}")

        finally:
            browser.close()


if __name__ == "__main__":
    discover_apis()
