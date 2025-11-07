# Inovar +AZ School Alerts

Azure Function (Python) that monitors a student's Inovar +AZ portal for new absences (Faltas) and behavior/teacher alerts (Avisos), sending email notifications when new events are detected.

## Features

- **Automated Monitoring**: Timer-triggered function runs daily at 14:00 UTC
- **Lightweight API Scraping**: Direct API calls (no browser/Chromium needed!)
- **Fast & Efficient**: 10x faster than browser automation, minimal resource usage
- **Smart Detection**: SQLite database tracks seen events to avoid duplicate notifications
- **Dual Triggers**: Timer (daily) + HTTP endpoint (on-demand testing)
- **Email Alerts**: AWS SES SMTP integration with HTML email templates
- **Minimal Container**: Tiny Docker image (~100-200MB vs ~1-2GB with Chromium)

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

## Deployment to Azure

### Option 1: Container Deployment (Recommended)

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
    ALERT_EMAIL_TO="your-email@example.com" \
    ALERT_EMAIL_TO_FALLBACK="backup@example.com"
```

### Option 2: Direct Deployment

```bash
# Deploy directly from local files
func azure functionapp publish <function-app-name> --build remote
```

**Note**: Direct deployment now works without containers thanks to the lightweight API approach!

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

## Support

For issues or questions, please open an issue in the repository.
