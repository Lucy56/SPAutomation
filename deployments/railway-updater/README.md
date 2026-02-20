# Shopify Orders Updater - Railway Cron Service

Automated service that syncs Shopify orders to PostgreSQL database hourly.

## What It Does

1. Connects to PostgreSQL database on Railway
2. Fetches orders updated since last sync from Shopify
3. Updates orders, line items, and tracks refunds
4. Sends email notifications (first record, every 10k records, completion summary)
5. Runs continuously every hour with lock protection to prevent overlapping syncs

## Files

- `updater.py` - Main sync script
- `requirements.txt` - Python dependencies
- `Procfile` - Railway worker configuration
- `runtime.txt` - Python version specification

## Environment Variables

Set these in Railway project settings:

```
DATABASE_URL=postgresql://user:password@host:port/database
SHOPIFY_SHOP_URL=Sinclairp.myshopify.com
SHOPIFY_API_KEY=your_api_key
SHOPIFY_API_SECRET=your_api_secret
UPDATE_INTERVAL=3600  # Optional: seconds between updates (default 1 hour)

# Email notifications (optional)
EMAIL_HOST=smtp.zoho.com.au  # SMTP server
EMAIL_PORT=587  # SMTP port
EMAIL_HOST_USER=hello@sinclairpatterns.com  # SMTP username
EMAIL_HOST_PASSWORD=your_email_password  # SMTP password
DEFAULT_FROM_EMAIL=hello@sinclairpatterns.com  # From address
NOTIFICATION_EMAIL=hello@sinclairpatterns.com  # Notification recipient
EMAIL_NOTIFICATION_INTERVAL=10000  # Send progress email every N records (default 10000)
```

## Deployment to Railway

### Option 1: Railway CLI

```bash
cd deployments/railway-updater
railway login
railway link  # Link to existing project or create new one
railway up
```

### Option 2: GitHub Integration

1. Push code to GitHub
2. In Railway dashboard:
   - Create new project
   - Connect to GitHub repository
   - Set root directory to `deployments/railway-updater`
   - Add environment variables
   - Deploy

## Monitoring

Check logs in Railway dashboard to see:
- Sync start/completion
- Number of orders updated
- Any errors

Email notifications will be sent to the configured recipient:
- **First record imported**: Confirms sync has started
- **Every 10k records**: Progress updates during large syncs
- **Completion summary**: Final count of orders and line items updated

## Local Testing

```bash
# Set environment variables
export DATABASE_EXT_SHOPIFY_DATA="postgresql://..."
export SHOPIFY_SHOP_URL="Sinclairp.myshopify.com"
export SHOPIFY_API_KEY="..."
export SHOPIFY_API_SECRET="..."
export UPDATE_INTERVAL="60"  # 1 minute for testing

# Run updater
python updater.py
```

## Database Schema

The updater syncs to these PostgreSQL tables:
- `orders` - Order data with UTM tracking
- `line_items` - Products purchased
- `sync_history` - Sync tracking

## Troubleshooting

**Connection errors:**
- Check DATABASE_URL is correct
- Verify Railway PostgreSQL service is running

**No orders syncing:**
- Check Shopify API credentials
- Verify last_sync_date in sync_history table

**Worker not running:**
- Check Railway logs
- Verify Procfile is correct
- Ensure worker is enabled in Railway settings
