# Inovar Guardian Bot

A lightweight automation tool that helps parents stay informed about their children's school activity on **Inovar Consulta**, the platform used by many Portuguese schools.

Since Inovar doesn't send timely alerts for new notes or absences, this bot checks daily for updates and sends notifications automatically.

## 🚀 Features

🔔 **Daily Notifications** — Get alerted when your child:
- Has a new absence (Falta)
- Receives a behavior note from a teacher (Aviso de Comportamento)
- Gets marked late (Pontualidade)
- Is missing materials (Material)

📧 **Email alerts** sent automatically
⚡ **Lightweight** - runs without browser automation
🔒 **Secure** - your credentials stay private
🎯 **Smart detection** - no duplicate notifications

## 💡 Why This Exists

Inovar Consulta is useful but lacks proactive notifications.
As a parent, it's easy to miss when a teacher leaves a note or a class is skipped.
This bot solves that problem — acting as a digital assistant that monitors your child's progress and keeps you informed without daily manual checks.

## 🧩 How It Works

1. The bot logs into Inovar Consulta
2. It retrieves student data via direct API calls (absences, behavior notes, etc.)
3. It compares today's data with the previous check
4. If something new appears (e.g., a missed class or a teacher note), it sends an email alert
5. Runs automatically every day at 14:00 UTC (3pm Lisbon time)

## 🛠️ Tech Stack

- **Python 3.11** - Lightweight scripting
- **Azure Functions** - Serverless automation (runs daily)
- **Direct API Calls** - No browser needed (fast & efficient)
- **Webshare Proxy** - Bypasses Cloudflare protection
- **SQLite** - Tracks seen events (no duplicate notifications)
- **SMTP Email** - AWS SES for notifications

---

## 📚 Technical Documentation

*The sections below are for developers/technical users setting up the bot.*

## Architecture

```
┌─────────────────┐
│  Timer Trigger  │  (Daily at 14:00 UTC)
│  HTTP Trigger   │  (Manual on-demand)
└────────┬────────┘
         │
         ▼
  ┌──────────────┐
  │Alert Checker │
  └──────┬───────┘
         │
    ┌────┴────────────────┐
    ▼                     ▼
┌─────────┐         ┌──────────┐
│ Scraper │         │ Database │
│(Requests)│         │(SQLite)  │
│Direct API│         │          │
└────┬────┘         └────┬─────┘
     │                   │
     │  New Events?      │
     └────────┬──────────┘
              ▼
       ┌─────────────┐
       │   Email     │
       │  Notifier   │
       └─────────────┘
```

## Project Structure

```
inovar-alert-bot/
├── models/
│   ├── __init__.py
│   └── database.py               # SQLModel for alert events
├── services/
│   ├── __init__.py
│   ├── scraper_lightweight.py    # Lightweight API scraper (requests)
│   ├── email_notifier.py         # SMTP email sender
│   └── alert_checker.py          # Main orchestrator
├── utils/
│   ├── __init__.py
│   └── config.py                 # Configuration management
├── timer_trigger/
│   ├── __init__.py               # Daily timer function
│   └── function.json
├── http_trigger/
│   ├── __init__.py               # Manual HTTP function
│   └── function.json
├── requirements.txt
├── host.json
├── local.settings.json.example
├── Dockerfile
├── debug_lightweight.py          # Test script for lightweight scraper
└── .dockerignore
```

## Setup

### Prerequisites

- Python 3.11+
- Azure Functions Core Tools v4
- Docker Desktop (optional, for containerized deployment)
- Azure subscription

### Local Development

1. **Clone the repository**

```bash
git clone <repository-url>
cd inovar-alert-bot
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
# No browser installation needed - uses lightweight API approach!
```

3. **Configure settings**

Copy `local.settings.json.example` to `local.settings.json`:

```bash
cp local.settings.json.example local.settings.json
```

Update the following values:

```json
{
  "Values": {
    "ALERT_EMAIL_TO": "your-email@example.com",
    "ALERT_EMAIL_TO_FALLBACK": "backup-email@example.com"
  }
}
```

**Important**: Never commit `local.settings.json` to version control (already in `.gitignore`).

4. **Run locally**

```bash
func start
```

The function will be available at:
- Timer trigger: Runs automatically on schedule
- HTTP trigger: `http://localhost:7071/api/http_trigger`

### Manual Testing

Test the HTTP endpoint:

```bash
curl http://localhost:7071/api/http_trigger
```

Expected response:

```json
{
  "status": "success",
  "timestamp": "2025-11-07T14:00:00.000000",
  "new_absences": 2,
  "new_behavior_alerts": 1,
  "email_sent": true
}
```

## Configuration

### Environment Variables

All configuration can be set via environment variables or `local.settings.json`:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `INOVAR_USERNAME` | Portal login username | Yes | - |
| `INOVAR_PASSWORD` | Portal login password | Yes | - |
| `INOVAR_LOGIN_URL` | Login page URL | No | `https://aevf.inovarmais.com/consulta/app/index.html#/login` |
| `INOVAR_HOME_URL` | Home page URL | No | `https://aevf.inovarmais.com/consulta/app/index.html#/home` |
| `WEBSHARE_API_KEY` | Webshare proxy API key | Yes (Azure only) | - |
| `SMTP_HOST` | SMTP server hostname | Yes | - |
| `SMTP_PORT` | SMTP port | No | `587` |
| `SMTP_USER` | SMTP username/access key | Yes | - |
| `SMTP_PASS` | SMTP password/secret key | Yes | - |
| `SMTP_FROM` | From email address | Yes | - |
| `ALERT_EMAIL_TO` | Primary recipient email | Recommended | - |
| `ALERT_EMAIL_TO_FALLBACK` | Fallback recipient email | No | - |
| `DATABASE_PATH` | SQLite database file | No | `alerts.db` |
| `TIMEZONE` | Timezone for timestamps | No | `Europe/Lisbon` |

### Timer Schedule

The timer trigger uses CRON expression `0 0 14 * * *` (14:00 UTC daily).

To change the schedule, edit `timer_trigger/function.json`:

```json
{
  "schedule": "0 0 14 * * *"
}
```

CRON format: `{second} {minute} {hour} {day} {month} {day-of-week}`

Examples:
- `0 0 14 * * *` - Daily at 14:00 UTC
- `0 30 13 * * *` - Daily at 13:30 UTC
- `0 0 8,14,20 * * *` - Three times daily: 8:00, 14:00, 20:00 UTC

## Why Webshare Proxy?

The Inovar portal uses **Cloudflare bot protection** to prevent automated scraping. This creates a challenge when deploying to Azure:

### The Problem
- ✅ **Works locally**: Your home IP address is trusted and passes Cloudflare checks
- ❌ **Fails in Azure**: Datacenter IPs are flagged as bots and receive "Just a moment..." challenge pages
- Result: Login requests return `403 Forbidden` with `cf-mitigated: challenge` headers

### The Solution: Webshare Proxy
[Webshare](https://www.webshare.io/) provides **residential proxy IPs** that appear as regular home connections:
- Bypasses Cloudflare bot detection
- Provides rotating IP addresses from real residential locations
- The bot **auto-detects** when running in Azure and enables the proxy automatically
- Local testing continues to work **without proxy** (faster and free)

### Setup
1. Create a free account at [webshare.io](https://www.webshare.io/)
2. Get your API key from the dashboard
3. Add `WEBSHARE_API_KEY` to your Azure Function App settings (see deployment section below)

**Note**: The proxy is only activated when the bot detects it's running in Azure (via `WEBSITE_INSTANCE_ID` environment variable). Local development doesn't use or require the proxy.

## Deployment to Azure

### Option 1: Direct Deployment (Recommended)

The simplest way to deploy is using Azure Functions Core Tools:

**Prerequisites:**
- [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local) installed
- Logged into Azure: `az login`
- Function App already created in Azure

**Step 1:** Configure Webshare API Key (required for Cloudflare bypass)

```bash
az functionapp config appsettings set \
  --name inovar-alert-bot \
  --resource-group <your-resource-group> \
  --settings WEBSHARE_API_KEY="<your-webshare-api-key>"
```

**Step 2:** Deploy the function

```bash
func azure functionapp publish inovar-alert-bot
```

**Step 3:** Wait 2-3 minutes for deployment to complete, then test

```bash
curl https://inovar-alert-bot.azurewebsites.net/api/http_trigger
```

**Benefits:**
- ✅ One-command deployment
- ✅ Automatic dependency installation
- ✅ No manual ZIP creation needed
- ✅ Works perfectly with lightweight API approach
- ✅ Built-in build process on Azure

### Option 2: Container Deployment (Advanced)

For users who prefer containerized deployments:

1. **Build and push Docker image**

```bash
# Login to Azure
az login

# Create Azure Container Registry (if not exists)
az acr create --resource-group <resource-group> --name <registry-name> --sku Basic

# Build and push image
az acr build --registry <registry-name> --image inovar-alert-bot:latest .
```

2. **Create Function App**

```bash
az functionapp create \
  --resource-group <resource-group> \
  --name <function-app-name> \
  --storage-account <storage-account> \
  --plan <app-service-plan> \
  --runtime custom \
  --deployment-container-image-name <registry-name>.azurecr.io/inovar-alert-bot:latest
```

3. **Configure App Settings**

```bash
az functionapp config appsettings set \
  --name <function-app-name> \
  --resource-group <resource-group> \
  --settings \
    WEBSHARE_API_KEY="<your-webshare-api-key>" \
    ALERT_EMAIL_TO="your-email@example.com" \
    ALERT_EMAIL_TO_FALLBACK="backup@example.com"
```

## How It Works

1. **Timer Trigger**: Function runs daily at 14:00 UTC
2. **Login**: Direct API call to `https://aevf.inovarmais.com/consulta/api/loginFU/`
   - Authenticates with base64-encoded credentials
   - Receives JWT token and student/matricula IDs
3. **Fetch Absences**: GET `https://aevf.inovarmais.com/consulta/api/faltas/{matricula_id}/{tipo_ensino}`
   - Returns JSON with all absences (Faltas) directly
4. **Fetch Behavior Alerts**: GET `https://aevf.inovarmais.com/consulta/api/comportamento/{matricula_id}/{tipo_ensino}`
   - Returns JSON with all behavior alerts (Comportamentos) directly
5. **Deduplicate**: Checks SQLite database for existing events
6. **Notify**: Sends email ONLY if new events detected
7. **Store**: Saves new events to database with `notified=true` flag

### Why Lightweight?

The bot uses **direct API calls** instead of browser automation:
- ✅ **No Chromium/Playwright needed** - reduces Docker image from ~1.5GB to ~150MB
- ✅ **10x faster execution** - API calls complete in seconds vs. minutes
- ✅ **Lower memory usage** - ~50MB vs. ~500MB RAM
- ✅ **Simpler deployment** - no browser dependencies or system packages
- ✅ **More reliable** - no browser crashes or rendering issues

## Database Schema

```sql
CREATE TABLE alert_events (
    id INTEGER PRIMARY KEY,
    event_id TEXT UNIQUE,              -- Generated unique ID
    event_type TEXT,                   -- "absence" or "behavior_alert"
    date TEXT,                         -- Event date (YYYY-MM-DD)
    description TEXT,                  -- Event description
    raw_data TEXT,                     -- JSON string of raw event
    first_seen DATETIME,               -- UTC timestamp
    notified BOOLEAN                   -- Email sent flag
);
```

## Email Template

The email includes:

- **Subject**: `Inovar Alert - X Nova(s) Falta(s) e Y Novo(s) Aviso(s)`
- **Body**: HTML formatted with:
  - 📅 Novas Faltas section (absences with date, subject, period)
  - ⚠️ Novos Avisos section (behavior alerts)
  - Timestamp of generation

## Troubleshooting

### SMTP Authentication Errors

Verify AWS SES credentials:
- Check `SMTP_USER` and `SMTP_PASS` in settings
- Ensure sending email is verified in AWS SES console

### No Email Received

Check function logs:

```bash
# Local
func start

# Azure
az functionapp log tail --name <function-app-name> --resource-group <resource-group>
```

Look for:
- `No new events detected, skipping email` - Expected if no new data
- `Email sent successfully` - Email was sent
- `Error sending email: ...` - SMTP connection issue

### Database Locked

If SQLite database is locked, the Azure Function app may be running multiple instances. Consider:
- Using Azure Premium plan with single instance
- Migrating to Azure SQL Database or Cosmos DB for multi-instance support

## Security Notes

- **Credentials**: Never commit `local.settings.json` or hardcode passwords
- **SMTP**: Use App Passwords or API keys (not account passwords)
- **Azure Key Vault**: For production, store secrets in Key Vault and reference in App Settings

## License

MIT

## ❤️ Acknowledgments

- **Inovar +AZ** for maintaining the school management system
- Every parent who wishes school systems were a bit more automated 😄

---

Feel free to fork, adapt, and improve this project!

## Support

For issues or questions, please open an issue in the repository.
