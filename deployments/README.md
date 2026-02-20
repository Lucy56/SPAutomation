# Deployments

This folder contains all services that are deployed to external platforms (Railway, Vercel, AWS, etc.)

## Structure

```
deployments/
├── railway-updater/     # Hourly cron service to sync Shopify orders to PostgreSQL
└── README.md           # This file
```

## Services

### railway-updater

**Purpose:** Automatically sync Shopify orders to PostgreSQL database every hour

**Platform:** Railway
**Type:** Worker/Cron
**Schedule:** Hourly (configurable via `UPDATE_INTERVAL` env var)

**Required Environment Variables:**
- `DATABASE_URL` or `DATABASE_EXT_SHOPIFY_DATA` - PostgreSQL connection string
- `SHOPIFY_SHOP_URL` - Your Shopify store URL
- `SHOPIFY_API_KEY` - Shopify API key
- `SHOPIFY_API_SECRET` - Shopify API secret
- `UPDATE_INTERVAL` - Update interval in seconds (default: 3600 = 1 hour)

**Deployment:**
```bash
cd deployments/railway-updater
railway up
```

## Local Development vs Deployment

**Local Scripts** (in `/Scripts/`):
- Used for one-time operations
- Manual migrations
- Local testing
- Development tools

**Deployment Services** (in `/deployments/`):
- Automated cron jobs
- Production services
- Externally hosted applications
- Continuous operations

## Note for Claude Code

When creating or modifying deployment services:
1. Always place them in the `deployments/` folder
2. Include a README.md for each service
3. List all required environment variables
4. Provide deployment instructions
5. Keep deployment code separate from local scripts
