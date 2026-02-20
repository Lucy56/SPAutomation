# Deployment Guide

## Prerequisites

1. **Railway Account** - Sign up at https://railway.app
2. **Railway CLI** (optional) - `npm install -g @railway/cli`
3. **PostgreSQL Database** - Already set up on Railway

## Deploy Shopify Orders Updater

### Step 1: Prepare Environment Variables

You'll need these values from your `.env` file:
- `DATABASE_EXT_SHOPIFY_DATA` - Your Railway PostgreSQL connection string
- `SHOPIFY_SHOP_URL` - `Sinclairp.myshopify.com`
- `SHOPIFY_API_KEY` - Your Shopify API key
- `SHOPIFY_API_SECRET` - Your Shopify API secret

### Step 2: Deploy via Railway Dashboard

1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account (if not already connected)
5. Select this repository
6. Configure deployment:
   - **Root Directory**: `deployments/railway-updater`
   - **Start Command**: Leave blank (uses Procfile)

7. Add environment variables:
   ```
   DATABASE_URL = [paste your DATABASE_EXT_SHOPIFY_DATA value]
   SHOPIFY_SHOP_URL = Sinclairp.myshopify.com
   SHOPIFY_API_KEY = [paste your API key]
   SHOPIFY_API_SECRET = [paste your API secret]
   UPDATE_INTERVAL = 3600
   ```

8. Click "Deploy"

### Step 3: Verify Deployment

1. Go to Railway dashboard
2. Click on your updater service
3. Go to "Logs" tab
4. You should see:
   ```
   [timestamp] STARTING SHOPIFY SYNC
   [timestamp] Connecting to PostgreSQL...
   [timestamp] ✓ Connected
   [timestamp] ✓ Token obtained
   [timestamp] SYNC COMPLETE!
   ```

### Alternative: Deploy via Railway CLI

```bash
cd deployments/railway-updater

# Login to Railway
railway login

# Create new project
railway init

# Add environment variables
railway variables set DATABASE_URL="postgresql://..."
railway variables set SHOPIFY_SHOP_URL="Sinclairp.myshopify.com"
railway variables set SHOPIFY_API_KEY="..."
railway variables set SHOPIFY_API_SECRET="..."
railway variables set UPDATE_INTERVAL="3600"

# Deploy
railway up

# View logs
railway logs
```

## Monitoring

### Check Sync Status

Connect to your PostgreSQL database and check:

```sql
SELECT * FROM sync_history ORDER BY sync_completed_at DESC LIMIT 10;
```

### View Logs

Railway Dashboard → Your Service → Logs tab

### Check Order Count

```sql
SELECT COUNT(*) FROM orders;
SELECT MAX(created_at) FROM orders;
```

## Troubleshooting

**Service keeps crashing:**
- Check environment variables are set correctly
- View logs for error messages
- Ensure DATABASE_URL is correct

**No orders syncing:**
- Check Shopify API credentials
- Verify last_sync_date in sync_history
- Check Shopify API rate limits

**High memory usage:**
- Reduce batch size in updater.py
- Increase UPDATE_INTERVAL

## Updating the Service

1. Make changes to code locally
2. Push to GitHub
3. Railway will automatically redeploy

Or with CLI:
```bash
cd deployments/railway-updater
railway up
```

## Cost

Railway offers:
- **Free tier**: 500 hours/month, $5 credit
- **Pro tier**: $20/month for team features

This updater should run within free tier limits.
