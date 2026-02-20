# Sinclair Patterns Analytics Database System

## Overview

Comprehensive SQLite database system for analyzing Shopify orders, customer behavior, campaign performance, and product sales patterns.

---

## 📁 File Structure

```
SinclairHelper/
├── Data/
│   └── shopify_orders.db          # SQLite database (created after first fetch)
├── Scripts/
│   ├── db_schema.py                # Database schema and initialization
│   ├── fetch_all_orders.py         # ONE-TIME: Fetch all historical orders
│   ├── update_recent_orders.py     # DAILY: Sync recent orders
│   ├── analyze_patterns_db.py      # Weekly specials pattern analysis
│   └── analyze_campaigns.py        # Campaign performance analysis
└── Docs/
    ├── weeklySpecials.json         # Track featured patterns
    └── Database_Analytics_System.md # This file
```

---

## 🗄️ Database Schema

### Tables

**1. `orders`** - Complete order information
- Order details (id, number, dates, status)
- Customer info (id, email)
- **Geographic data** (country, province, city)
- Financial data (totals, discounts, currency)
- **UTM tracking** (source, medium, campaign, content, term)
- Marketing attribution (referring_site, landing_site)

**2. `line_items`** - Products in each order
- Product identification (id, title, SKU)
- Pricing and quantity
- Links to orders table

**3. `products`** - Product catalog
- Product details
- Creation/publication dates
- Tags and categorization

**4. `customers`** - Customer information
- Contact details
- Geographic location
- Marketing preferences
- Lifetime value stats

**5. `sync_history`** - Track database updates
- Sync timestamps
- Records fetched
- Status tracking

---

## 🚀 Getting Started

### Initial Setup (ONE TIME ONLY)

**Step 1: Initialize database and fetch all historical data**

```bash
cd Scripts
python3 fetch_all_orders.py
```

**What this does:**
- Creates SQLite database
- Fetches ALL orders from Shopify (5,000+ orders)
- Extracts UTM parameters
- Saves to database
- **Duration:** ~5-10 minutes

**You'll see:**
```
SINCLAIR PATTERNS - INITIAL DATA FETCH
=====================================

Page 1: Fetching... got 250 orders (total: 250)
Page 2: Fetching... got 250 orders (total: 500)
...
✓ Fetched 5,431 total orders across 22 pages
✓ Saved 5,431 orders and 12,456 line items to database
```

---

### Daily/Weekly Updates

**Step 2: Keep database current (run daily or weekly)**

```bash
python3 update_recent_orders.py
```

**What this does:**
- Checks last sync date
- Fetches only NEW orders since then
- Updates database
- **Duration:** ~30 seconds

---

## 📊 Analysis Scripts

### 1. Weekly Specials Pattern Analyzer

**Purpose:** Suggest patterns for weekly specials based on sales data

```bash
python3 analyze_patterns_db.py
```

**What it analyzes:**
- ✓ Top sellers (last 90 days)
- ✓ Historical bestsellers (2 years ago, same season)
- ✓ Underrated patterns (low but steady sales)
- ✓ Market basket analysis (products bought together)
- ✓ Excludes recently featured patterns

**Output:**
- 2-3 cohesive pattern sets
- Reasoning for each set
- Sales statistics
- Saved to `Output/weekly_specials_analysis_db.json`

**Example output:**
```
SET 1: Bestseller Bundle
========================
Reasoning: Built around current bestseller 'Harper...' with complementary patterns

1. Harper classic knit cardigan (Bestseller)
   Units sold: 245
   Revenue: $2,695.50

2. Sunset knit lounge pants (Recent Release)
   Units sold: 42
   Revenue: $461.58

3. Indra one shoulder knit top (Underrated)
   Units sold: 8
   Revenue: $87.92
```

---

### 2. Campaign Performance Analyzer

**Purpose:** Measure effectiveness of marketing campaigns via UTM tracking

```bash
python3 analyze_campaigns.py
```

**What it analyzes:**
- Campaign performance (by utm_campaign)
- Traffic sources (by utm_source, utm_medium)
- Weekly specials ROI
- Geographic breakdown
- Top products per campaign

**Use cases:**
- Which campaigns drive most revenue?
- What's the ROI of weekly specials?
- Which traffic sources convert best?
- Email vs social media performance

---

## 💡 Advanced Queries

### Example: Find patterns bought together

```python
from Scripts.analyze_patterns_db import find_frequently_bought_together

# Find what customers buy with Harper cardigan
companions = find_frequently_bought_together(product_id=123456, min_occurrences=3)

# Result: [(Sunset pants, 45 times), (Journey hoodie, 32 times), ...]
```

### Example: Geographic analysis

```sql
-- Top selling patterns in Australia
SELECT
    li.product_title,
    SUM(li.quantity) as units
FROM line_items li
JOIN orders o ON li.order_id = o.order_id
WHERE o.country = 'Australia'
GROUP BY li.product_title
ORDER BY units DESC
LIMIT 10;
```

### Example: Seasonal patterns

```sql
-- Sales by month
SELECT
    strftime('%Y-%m', created_at) as month,
    COUNT(*) as orders,
    SUM(total_price) as revenue
FROM orders
WHERE financial_status = 'paid'
GROUP BY month
ORDER BY month DESC;
```

---

## 📈 Enabled Analytics

### 1. **Market Basket Analysis**
- "Customers who bought X also bought Y"
- Create cohesive pattern bundles
- Cross-sell recommendations

### 2. **Geographic Insights**
- Top countries by revenue
- Seasonal differences (hemispheres)
- Shipping cost analysis

### 3. **Campaign Attribution**
- UTM tracking for all campaigns
- ROI measurement
- Channel effectiveness

### 4. **Customer Segmentation**
- New vs repeat customers
- High-value vs casual buyers
- Geographic segments

### 5. **Product Lifecycle**
- Sales trajectory after release
- Evergreen vs trending patterns
- Retirement candidates

### 6. **Seasonal Trends**
- Monthly/quarterly patterns
- Year-over-year comparisons
- Forecast demand

---

## 🔄 Maintenance Schedule

**Daily (automated via cron):**
```bash
0 2 * * * cd /path/to/SinclairHelper/Scripts && python3 update_recent_orders.py
```

**Weekly (before creating newsletter):**
```bash
python3 analyze_patterns_db.py
```

**Monthly (reporting):**
```bash
python3 analyze_campaigns.py
```

---

## 🛠️ Technical Details

**Database:** SQLite 3
- **Location:** `Data/shopify_orders.db`
- **Size:** ~50-100 MB for 5,000+ orders
- **Query speed:** <100ms for most queries
- **Backup:** Copy `.db` file to backup location

**Indexes created for fast queries:**
- Order dates, countries, customers
- Product IDs
- UTM parameters

**Dependencies:**
- Python 3.7+
- `requests` (for Shopify API)
- `sqlite3` (built into Python)

---

## 🎯 Next Steps

1. **Run initial fetch** (one time)
   ```bash
   python3 fetch_all_orders.py
   ```

2. **Analyze current data**
   ```bash
   python3 analyze_patterns_db.py
   python3 analyze_campaigns.py
   ```

3. **Set up daily sync** (cron job)
   ```bash
   crontab -e
   # Add: 0 2 * * * cd /path/to/Scripts && python3 update_recent_orders.py
   ```

4. **Use for weekly specials**
   - Run analyzer
   - Review suggested sets
   - Create newsletter
   - Track in weeklySpecials.json

---

## 📝 Notes

- **Shopify API token expires in 24 hours** - Script re-authenticates automatically
- **Initial fetch** takes 5-10 minutes - only run ONCE
- **Updates** take ~30 seconds - run daily/weekly
- **Analysis** is instant - queries local database

---

## 🚨 Troubleshooting

**Database not found:**
```bash
python3 Scripts/db_schema.py  # Re-initialize database
```

**No data returned:**
- Check if initial fetch completed
- Verify database has records: `sqlite3 Data/shopify_orders.db "SELECT COUNT(*) FROM orders;"`

**Slow queries:**
- Database may need vacuuming: `sqlite3 Data/shopify_orders.db "VACUUM;"`

---

**Database ready!** Start with `python3 fetch_all_orders.py`
