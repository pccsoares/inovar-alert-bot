"""
Debug script to troubleshoot login issues.

This script runs the browser in VISIBLE mode and takes screenshots
at each step to help identify why login is failing.

Usage:
    python debug_login.py
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

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def load_config_from_file():
    """Load configuration from local.settings.json."""
    settings_file = Path(__file__).parent / "local.settings.json"

    if not settings_file.exists():
        print("❌ ERROR: local.settings.json not found!")
        sys.exit(1)

    with open(settings_file, 'r') as f:
        settings = json.load(f)
        return settings.get('Values', {})


def main():
    """Main debug function."""
    print("=" * 70)
    print("🔍 LOGIN DEBUG MODE")
    print("=" * 70)
    print()

    # Create screenshots directory
    screenshots_dir = Path(__file__).parent / "debug_screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    print(f"📁 Screenshots will be saved to: {screenshots_dir}")
    print()

    # Load configuration
    config = load_config_from_file()
    username = config.get('INOVAR_USERNAME')
    password = config.get('INOVAR_PASSWORD')
    login_url = config.get('INOVAR_LOGIN_URL')
    home_url = config.get('INOVAR_HOME_URL')

    print(f"📋 Configuration:")
    print(f"   Username: {username}")
    print(f"   Password: {'*' * len(password) if password else 'NOT SET'}")
    print(f"   Login URL: {login_url}")
    print()

    # Start browser in VISIBLE mode
    print("🌐 Starting VISIBLE browser (you will see it open)...")
    print("   Close the browser manually when done inspecting.")
    print()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,  # VISIBLE BROWSER
            slow_mo=1000  # Slow down actions by 1 second each
        )
        page = browser.new_page()

        try:
            # Step 1: Navigate to login page
            print("📍 Step 1: Navigating to login page...")
            page.goto(login_url, wait_until="networkidle", timeout=30000)
            page.screenshot(path=str(screenshots_dir / "01_login_page.png"))
            print(f"   ✅ Screenshot saved: 01_login_page.png")
            print(f"   Current URL: {page.url}")
            print()

            # Step 2: Wait and inspect page
            print("📍 Step 2: Waiting for page to fully load...")
            page.wait_for_timeout(3000)

            # Save page HTML
            html_file = screenshots_dir / "01_login_page.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(page.content())
            print(f"   ✅ Page HTML saved: 01_login_page.html")
            print()

            # Step 3: Find all input fields
            print("📍 Step 3: Analyzing login form...")
            print("   Looking for input fields...")

            all_inputs = page.query_selector_all("input")
            print(f"   Found {len(all_inputs)} input fields:")
            for i, inp in enumerate(all_inputs):
                input_type = inp.get_attribute("type") or "text"
                input_id = inp.get_attribute("id") or "(no id)"
                input_name = inp.get_attribute("name") or "(no name)"
                input_placeholder = inp.get_attribute("placeholder") or "(no placeholder)"
                input_class = inp.get_attribute("class") or "(no class)"

                print(f"      [{i+1}] type={input_type}, id={input_id}, name={input_name}")
                print(f"          placeholder={input_placeholder}")
                print(f"          class={input_class}")
            print()

            # Step 4: Find all buttons
            print("📍 Step 4: Looking for buttons...")
            all_buttons = page.query_selector_all("button")
            all_submits = page.query_selector_all("input[type='submit']")

            print(f"   Found {len(all_buttons)} <button> elements:")
            for i, btn in enumerate(all_buttons):
                btn_text = btn.inner_text() if btn else ""
                btn_type = btn.get_attribute("type") or "(no type)"
                btn_id = btn.get_attribute("id") or "(no id)"
                btn_class = btn.get_attribute("class") or "(no class)"
                print(f"      [{i+1}] text='{btn_text}', type={btn_type}, id={btn_id}")
                print(f"          class={btn_class}")

            print(f"   Found {len(all_submits)} <input type='submit'> elements:")
            for i, sub in enumerate(all_submits):
                sub_value = sub.get_attribute("value") or "(no value)"
                sub_id = sub.get_attribute("id") or "(no id)"
                print(f"      [{i+1}] value='{sub_value}', id={sub_id}")
            print()

            # Step 5: Try to find username field
            print("📍 Step 5: Attempting to find username field...")
            username_selectors = [
                "input#username",
                "input[name='username']",
                "input[type='text']",
                "input[type='number']",
                "input[placeholder*='utilizador' i]",
                "input[placeholder*='user' i]",
                "input[ng-model*='username' i]",
                "input[ng-model*='user' i]",
            ]

            username_input = None
            username_selector_used = None
            for selector in username_selectors:
                try:
                    test_input = page.query_selector(selector)
                    if test_input and test_input.is_visible():
                        username_input = test_input
                        username_selector_used = selector
                        print(f"   ✅ Found with selector: {selector}")
                        break
                except:
                    continue

            if not username_input:
                print("   ❌ Could not find username input field!")
                print("   Please check the screenshots and HTML file.")
                return
            print()

            # Step 6: Try to find password field
            print("📍 Step 6: Attempting to find password field...")
            password_selectors = [
                "input#password",
                "input[name='password']",
                "input[type='password']",
                "input[placeholder*='password' i]",
                "input[placeholder*='senha' i]",
                "input[ng-model*='password' i]",
            ]

            password_input = None
            password_selector_used = None
            for selector in password_selectors:
                try:
                    test_input = page.query_selector(selector)
                    if test_input and test_input.is_visible():
                        password_input = test_input
                        password_selector_used = selector
                        print(f"   ✅ Found with selector: {selector}")
                        break
                except:
                    continue

            if not password_input:
                print("   ❌ Could not find password input field!")
                print("   Please check the screenshots and HTML file.")
                return
            print()

            # Step 7: Fill in credentials
            print("📍 Step 7: Filling in credentials...")
            username_input.fill(username)
            print(f"   ✅ Username entered")
            page.screenshot(path=str(screenshots_dir / "02_username_filled.png"))

            password_input.fill(password)
            print(f"   ✅ Password entered")
            page.screenshot(path=str(screenshots_dir / "03_password_filled.png"))
            print()

            # Step 8: Find and click submit button
            print("📍 Step 8: Looking for submit button...")
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Entrar')",
                "button:has-text('Login')",
                "a:has-text('Entrar')",
                "button.btn-primary",
                "button.submit",
            ]

            submit_button = None
            submit_selector_used = None
            for selector in submit_selectors:
                try:
                    test_button = page.query_selector(selector)
                    if test_button and test_button.is_visible():
                        submit_button = test_button
                        submit_selector_used = selector
                        print(f"   ✅ Found with selector: {selector}")
                        break
                except:
                    continue

            if not submit_button:
                print("   ❌ Could not find submit button!")
                print("   Please check the screenshots.")
                return
            print()

            # Step 9: Click submit
            print("📍 Step 9: Clicking submit button...")
            submit_button.click()
            print("   ✅ Button clicked, waiting for navigation...")

            # Wait for navigation
            page.wait_for_timeout(5000)
            page.screenshot(path=str(screenshots_dir / "04_after_submit.png"))
            print(f"   ✅ Screenshot saved: 04_after_submit.png")
            print(f"   Current URL: {page.url}")
            print()

            # Step 10: Check if login succeeded
            print("📍 Step 10: Checking login result...")
            current_url = page.url.lower()

            if "login" in current_url:
                print("   ❌ STILL ON LOGIN PAGE - Login failed!")
                print("   Check for error messages on the page.")

                # Look for error messages
                error_selectors = [
                    ".error",
                    ".alert",
                    ".alert-danger",
                    "[class*='error']",
                    "[class*='alert']"
                ]

                for selector in error_selectors:
                    errors = page.query_selector_all(selector)
                    for error in errors:
                        error_text = error.inner_text()
                        if error_text.strip():
                            print(f"   ⚠️  Error message: {error_text}")
            else:
                print("   ✅ NAVIGATED AWAY FROM LOGIN PAGE - Likely successful!")
                print(f"   Current URL: {page.url}")
            print()

            # Keep browser open for manual inspection
            print("=" * 70)
            print("🔍 BROWSER INSPECTION MODE")
            print("=" * 70)
            print("The browser will stay open for manual inspection.")
            print("You can interact with the page to see what's wrong.")
            print("Check the debug_screenshots folder for saved images and HTML.")
            print()
            print("Recommended selectors based on findings:")
            print(f"   Username: {username_selector_used}")
            print(f"   Password: {password_selector_used}")
            print(f"   Submit: {submit_selector_used}")
            print()
            print("Press Enter to close the browser and exit...")
            input()

        except Exception as e:
            print()
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

            # Save screenshot on error
            try:
                page.screenshot(path=str(screenshots_dir / "99_error.png"))
                print(f"   Error screenshot saved: 99_error.png")
            except:
                pass

            print("\nPress Enter to close browser...")
            input()

        finally:
            browser.close()


if __name__ == "__main__":
    main()
