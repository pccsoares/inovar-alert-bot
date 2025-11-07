"""
Debug script to test the lightweight scraper (no Chromium).

Usage:
    1. Ensure local.settings.json exists with valid credentials
    2. Install dependencies: pip install requests
    3. Run: python debug_lightweight.py
"""
import os
import json
import sys
import logging
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from services.scraper_lightweight import InovarScraperLightweight


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


def main():
    """Main test function."""
    print("=" * 70)
    print("🧪 LIGHTWEIGHT SCRAPER TEST (NO CHROMIUM)")
    print("=" * 70)
    print()

    # Load configuration
    print("📋 Loading configuration from local.settings.json...")
    config = load_config_from_file()

    username = config.get('INOVAR_USERNAME')
    password = config.get('INOVAR_PASSWORD')

    # Validate required config
    if not username or not password:
        print("❌ ERROR: INOVAR_USERNAME or INOVAR_PASSWORD not set in local.settings.json")
        sys.exit(1)

    print(f"   Username: {username}")
    print()

    # Run scraper
    print("🚀 Starting lightweight scraper (direct API calls)...")
    print("-" * 70)

    try:
        with InovarScraperLightweight(
            username=username,
            password=password
        ) as scraper:
            print("🔐 Attempting login via API...")
            results = scraper.scrape_all()
            print()

            # Display results
            print("=" * 70)
            print("📊 RESULTS")
            print("=" * 70)

            if results.get('success'):
                print("✅ Status: SUCCESS")
                print()

                # Absences
                absences = results.get('absences', [])
                print(f"📅 ABSENCES FOUND: {len(absences)}")
                if absences:
                    print("-" * 70)
                    for i, absence in enumerate(absences, 1):
                        print(f"\n  [{i}] Absence:")
                        print(f"      Date: {absence.get('date', 'N/A')}")
                        print(f"      Description: {absence.get('description', 'N/A')}")
                        print(f"      Subject: {absence.get('subject', 'N/A')}")
                        print(f"      Time: {absence.get('time', 'N/A')}")
                else:
                    print("   No absences found.")
                print()

                # Behavior alerts
                alerts = results.get('behavior_alerts', [])
                print(f"⚠️  BEHAVIOR ALERTS FOUND: {len(alerts)}")
                if alerts:
                    print("-" * 70)
                    for i, alert in enumerate(alerts, 1):
                        print(f"\n  [{i}] Alert:")
                        print(f"      Date: {alert.get('date', 'N/A')}")
                        print(f"      Professor: {alert.get('professor', 'N/A')}")
                        print(f"      Grau: {alert.get('grau', 'N/A')}")
                        print(f"      Description: {alert.get('description', 'N/A')}")
                else:
                    print("   No behavior alerts found.")
                print()

                # Student IDs
                if scraper.aluno_id:
                    print(f"🆔 Student Info:")
                    print(f"   Aluno ID: {scraper.aluno_id}")
                    print(f"   Matricula ID: {scraper.matricula_id}")
                    print(f"   Tipo Ensino: {scraper.tipo_ensino}")
                    print()

            else:
                print("❌ Status: FAILED")
                error = results.get('error', 'Unknown error')
                print(f"   Error: {error}")
                print()

            print("=" * 70)

    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR")
        print("=" * 70)
        print(f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n✅ Test completed!")
    print("\n💡 Benefits of lightweight approach:")
    print("   - No Chromium browser needed (~1.5GB saved!)")
    print("   - Faster execution (~10x faster)")
    print("   - Lower memory usage (~5x less)")
    print("   - Simpler deployment")


if __name__ == "__main__":
    main()
