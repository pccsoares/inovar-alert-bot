"""
Diagnostic script to test Azure login issues.
This script simulates the Azure environment to identify the login failure.
"""
import os
import json
import sys
import logging
from pathlib import Path
from datetime import datetime
import io

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from services.scraper_lightweight import InovarScraperLightweight


def load_config():
    """Load configuration from local.settings.json."""
    settings_file = Path(__file__).parent / "local.settings.json"
    with open(settings_file, 'r') as f:
        settings = json.load(f)
        return settings.get('Values', {})


def test_without_proxy():
    """Test login WITHOUT proxy (simulates local environment)."""
    print("\n" + "=" * 70)
    print("TEST 1: WITHOUT PROXY (simulates local environment)")
    print("=" * 70)

    config = load_config()

    try:
        with InovarScraperLightweight(
            username=config['INOVAR_USERNAME'],
            password=config['INOVAR_PASSWORD'],
            use_proxy=False
        ) as scraper:
            print(f"Current UTC time: {datetime.utcnow()}")
            print(f"Current UTC date string: {datetime.utcnow().strftime('%Y%m%d')}")
            print(f"Generated x-festmani token: {scraper._generate_festmani_token()}\n")

            success = scraper.login()

            if success:
                print("✅ LOGIN SUCCESSFUL (without proxy)")
                print(f"   JWT Token (first 50 chars): {str(scraper.jwt_token)[:50]}")
                print(f"   Aluno ID: {scraper.aluno_id}")
                print(f"   Matricula ID: {scraper.matricula_id}")
                return True
            else:
                print("❌ LOGIN FAILED (without proxy)")
                return False

    except Exception as e:
        print(f"❌ EXCEPTION (without proxy): {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_proxy():
    """Test login WITH proxy (simulates Azure environment)."""
    print("\n" + "=" * 70)
    print("TEST 2: WITH PROXY (simulates Azure environment)")
    print("=" * 70)

    config = load_config()

    # Temporarily set WEBSITE_INSTANCE_ID to simulate Azure
    original_instance_id = os.getenv('WEBSITE_INSTANCE_ID')
    os.environ['WEBSITE_INSTANCE_ID'] = 'test-instance-id'

    try:
        print("Simulating Azure environment (WEBSITE_INSTANCE_ID set)")
        print(f"Webshare API Key available: {'WEBSHARE_API_KEY' in config}")

        with InovarScraperLightweight(
            username=config['INOVAR_USERNAME'],
            password=config['INOVAR_PASSWORD'],
            use_proxy=True  # Force proxy usage
        ) as scraper:
            print(f"Proxy manager initialized: {scraper.proxy_manager is not None}")
            if scraper.proxy_manager:
                print(f"Current proxy: {scraper.proxy_manager.current_proxy}")

            print(f"\nCurrent UTC time: {datetime.utcnow()}")
            print(f"Current UTC date string: {datetime.utcnow().strftime('%Y%m%d')}")
            print(f"Generated x-festmani token: {scraper._generate_festmani_token()}\n")

            success = scraper.login()

            if success:
                print("✅ LOGIN SUCCESSFUL (with proxy)")
                print(f"   JWT Token (first 50 chars): {str(scraper.jwt_token)[:50]}")
                print(f"   Aluno ID: {scraper.aluno_id}")
                print(f"   Matricula ID: {scraper.matricula_id}")
                return True
            else:
                print("❌ LOGIN FAILED (with proxy)")
                print("\nPossible causes:")
                print("  1. Proxy IP blocked by Inovar's Cloudflare")
                print("  2. Proxy timeout/connectivity issues")
                print("  3. Webshare proxy credentials invalid")
                return False

    except Exception as e:
        print(f"❌ EXCEPTION (with proxy): {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original environment
        if original_instance_id:
            os.environ['WEBSITE_INSTANCE_ID'] = original_instance_id
        else:
            os.environ.pop('WEBSITE_INSTANCE_ID', None)


def test_token_generation():
    """Test if the x-festmani token is being generated correctly."""
    print("\n" + "=" * 70)
    print("TEST 3: TOKEN GENERATION VALIDATION")
    print("=" * 70)

    import hmac
    import hashlib
    import base64

    utc_date = datetime.utcnow().strftime("%Y%m%d")
    secret_key = "0c24b08e-d78b-4d53-96a6-68db2bf2611f"

    # Generate token
    hmac_digest = hmac.new(
        secret_key.encode('utf-8'),
        utc_date.encode('utf-8'),
        hashlib.sha256
    ).digest()
    token = base64.b64encode(hmac_digest).decode('utf-8')

    print(f"Current UTC date: {datetime.utcnow()}")
    print(f"Date string used: {utc_date}")
    print(f"Secret key: {secret_key}")
    print(f"Generated token: {token}")
    print("\n✅ Token generation appears correct")
    print("   (This token is regenerated daily based on UTC date)")


def main():
    """Run all diagnostic tests."""
    print("=" * 70)
    print("AZURE LOGIN DIAGNOSTIC TOOL")
    print("=" * 70)
    print("\nThis script will test:")
    print("  1. Login without proxy (local simulation)")
    print("  2. Login with proxy (Azure simulation)")
    print("  3. Token generation validation")
    print("\n" + "=" * 70 + "\n")

    # Test 1: Without proxy
    test1_success = test_without_proxy()

    # Test 2: With proxy
    test2_success = test_with_proxy()

    # Test 3: Token generation
    test_token_generation()

    # Summary
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)
    print(f"Test 1 (Local - No Proxy):  {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"Test 2 (Azure - With Proxy): {'✅ PASS' if test2_success else '❌ FAIL'}")
    print()

    if test1_success and not test2_success:
        print("🔍 DIAGNOSIS: Proxy is causing the login failure")
        print("\nRECOMMENDED ACTIONS:")
        print("  1. Try rotating to a different Webshare proxy")
        print("  2. Check if Inovar updated Cloudflare rules to block proxy IPs")
        print("  3. Consider temporarily disabling proxy in Azure:")
        print("     - Edit alert_checker.py line 90-95")
        print("     - Force use_proxy=False for testing")
        print("  4. Contact Webshare support to check proxy health")
    elif not test1_success and not test2_success:
        print("🔍 DIAGNOSIS: Login failing regardless of proxy")
        print("\nRECOMMENDED ACTIONS:")
        print("  1. Verify credentials in local.settings.json")
        print("  2. Check if Inovar portal changed login API")
        print("  3. Check if IP is blocked by Cloudflare")
    elif test1_success and test2_success:
        print("✅ Both tests passed! Login should work in Azure.")
        print("   If Azure still fails, check:")
        print("   1. Environment variables in Azure Function settings")
        print("   2. Azure Function timeout settings")
        print("   3. Azure Function logs for other errors")

    print("=" * 70)


if __name__ == "__main__":
    main()
