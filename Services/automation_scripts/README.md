# Sinclair Patterns Automation Scripts

Celery-based automation service for Shopify pricing, newsletters, and social media posting.

## Features

### ✅ Currently Implemented
- **Automatic Weekly Specials Pricing**
  - Starts sale every Monday at 12:00 AM AEST
  - Ends sale every Sunday at 11:59 PM AEST
  - Reads configuration from `config/*-specials.json`
  - Automatic retries on failure

### 🚧 Future Features (Placeholder tasks ready)
- **Newsletter Automation**
  - Auto-generate newsletter HTML
  - Auto-send via Sendy
- **Social Media Posting**
  - Pinterest pins
  - Facebook posts
  - Instagram posts

## Architecture

```
celery_app.py              # Main Celery application & schedule
price_manager.py           # Shopify API price management
tasks/
  ├── pricing_tasks.py     # Weekly pricing automation
  ├── newsletter_tasks.py  # Future: Newsletter tasks
  └── social_media_tasks.py # Future: Social media tasks
config/
  └── 2026-02-02-specials.json  # Weekly specials configuration
```

## Deployment on Railway

### 1. Create Railway Project

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project in this directory
cd Services/automation_scripts
railway init
```

### 2. Add Redis to Railway

1. Go to your Railway project dashboard
2. Click "New" → "Database" → "Add Redis"
3. Redis will auto-provision and set `REDIS_URL` environment variable

### 3. Set Environment Variables

In Railway dashboard, add:
```
SHOPIFY_API_KEY=772b26294ecd6f1bc70c198a59fdad79
SHOPIFY_API_SECRET=YOUR_SHOPIFY_SECRET
```

### 4. Deploy Services

Railway will deploy 3 services from Procfile:
- **worker**: Celery worker (executes tasks)
- **beat**: Celery beat (scheduler)
- **flower**: Monitoring dashboard (optional)

```bash
# Deploy
railway up

# Check logs
railway logs
```

### 5. Access Flower Dashboard (Optional)

Flower provides a web UI to monitor tasks:
- URL: `https://your-app.up.railway.app` (Railway will provide this)
- View scheduled tasks, task history, worker status

## Local Development

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (via Docker)
docker run -d -p 6379:6379 redis:7-alpine

# Set environment variables
cp .env.example .env
# Edit .env with your credentials
```

### Run Services

```bash
# Terminal 1: Start Celery Worker
celery -A celery_app worker --loglevel=info

# Terminal 2: Start Celery Beat (scheduler)
celery -A celery_app beat --loglevel=info

# Terminal 3: Start Flower (monitoring - optional)
celery -A celery_app flower --port=5555
# Access at http://localhost:5555
```

## Manual Task Execution

### Test Price Update Now

```bash
# Start sale for current week's specials
python -c "from tasks.pricing_tasks import start_weekly_sale; start_weekly_sale.delay()"

# End sale
python -c "from tasks.pricing_tasks import end_weekly_sale; end_weekly_sale.delay()"
```

### Using price_manager.py directly

```bash
# Start sale
python price_manager.py start_sale config/2026-02-02-specials.json

# End sale
python price_manager.py end_sale config/2026-02-02-specials.json
```

## Adding New Weekly Specials

1. Create new config file:
```bash
cp config/2026-02-02-specials.json config/2026-02-09-specials.json
```

2. Edit the new file with updated patterns and dates:
```json
{
  "patterns": [
    {
      "handle": "pattern-handle-here",
      "original_price": 10.99,
      "sale_price": 8.99
    }
  ],
  "start_date": "2026-02-09",
  "end_date": "2026-02-16",
  "theme": "Your Theme Here"
}
```

3. The service will automatically use the **latest** config file based on filename

## Schedule Configuration

Edit `celery_app.py` to modify schedules:

```python
app.conf.beat_schedule = {
    'start-weekly-specials': {
        'task': 'tasks.pricing_tasks.start_weekly_sale',
        'schedule': crontab(hour=0, minute=0, day_of_week=1),  # Monday 12 AM
    },
    'end-weekly-specials': {
        'task': 'tasks.pricing_tasks.end_weekly_sale',
        'schedule': crontab(hour=23, minute=59, day_of_week=0),  # Sunday 11:59 PM
    },
}
```

Redeploy after changes:
```bash
railway up
```

## Monitoring

### Via Flower
- Access Flower dashboard (deployed on Railway)
- View: Active tasks, scheduled tasks, task history, worker health

### Via Railway Logs
```bash
railway logs --service worker
railway logs --service beat
```

### Task Retries
- All pricing tasks retry 3 times on failure
- Exponential backoff: 1min → 5min → 15min

## Future: Adding Social Media Automation

When ready to implement Pinterest/Facebook/Instagram:

1. **Uncomment** social media schedules in `celery_app.py`
2. **Implement** API integrations in `tasks/social_media_tasks.py`
3. **Add** API credentials to Railway environment variables
4. **Deploy** updated code

Example flow:
```python
# Chain tasks together
from celery import chain

chain(
    start_weekly_sale.s(),                    # Set prices
    generate_newsletter.s(),                   # Create newsletter
    send_weekly_newsletter.s(),                # Send via Sendy
    post_to_all_platforms.s()                  # Post to social
)()
```

## Cost Estimate (Railway)

- **Hobby Plan**: $5/month (includes Redis + worker/beat)
- **Pro Plan**: $20/month (better for production)

Typical usage:
- 2-3 tasks/week = minimal compute
- Redis usage: <10MB
- Should fit in Hobby plan

## Support

For issues or questions:
1. Check Railway logs
2. Check Flower dashboard
3. Review task history in Redis
