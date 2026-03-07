#!/usr/bin/env python3
"""
Test the new table format for sync notifications
"""

import os
import sys
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../deployments/railway-updater'))
from email_service import EmailService

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_EXT_SHOPIFY_DATA")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Get all stats
cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_price), 0) FROM orders WHERE synced_at >= NOW() - INTERVAL '10 minutes'")
this_sync = cursor.fetchone()

cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_price), 0) FROM orders WHERE DATE(created_at) = CURRENT_DATE AND financial_status != 'pending'")
today = cursor.fetchone()

cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_price), 0) FROM orders WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE) AND financial_status != 'pending'")
week = cursor.fetchone()

cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_price), 0) FROM orders WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE) AND financial_status != 'pending'")
month = cursor.fetchone()

cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_price), 0) FROM orders WHERE created_at >= NOW() - INTERVAL '30 days' AND financial_status != 'pending'")
last_30_days = cursor.fetchone()

cursor.execute("""
    SELECT li.product_title, COUNT(DISTINCT o.order_id), SUM(li.quantity), COALESCE(SUM(li.quantity * li.price), 0)
    FROM line_items li JOIN orders o ON li.order_id = o.order_id
    WHERE o.created_at >= NOW() - INTERVAL '30 days' AND o.financial_status != 'pending' AND li.product_title IS NOT NULL
    GROUP BY li.product_title ORDER BY COUNT(DISTINCT o.order_id) DESC LIMIT 10
""")
top_patterns = cursor.fetchall()

cursor.close()
conn.close()

stats = {
    'this_sync': {'count': this_sync[0], 'amount': float(this_sync[1])},
    'today': {'count': today[0], 'amount': float(today[1])},
    'week': {'count': week[0], 'amount': float(week[1])},
    'month': {'count': month[0], 'amount': float(month[1])},
    'last_30_days': {'count': last_30_days[0], 'amount': float(last_30_days[1])},
    'avg_per_day': {
        'count': last_30_days[0] / 30.0 if last_30_days[0] > 0 else 0,
        'amount': float(last_30_days[1]) / 30.0 if float(last_30_days[1]) > 0 else 0
    },
    'top_patterns': top_patterns
}

# Build email
subject = "✅ Shopify Sync Complete (TEST)"
orders_count = stats['this_sync']['count']
line_items_count = orders_count * 2

body = f"""Shopify sync completed successfully!

This Sync:
  • Orders imported/updated: {orders_count:,}
  • Line items processed: {line_items_count:,}
  • Total amount: ${stats['this_sync']['amount']:,.2f}

═══════════════════════════════════════════════════════════════════════
SALES SUMMARY
═══════════════════════════════════════════════════════════════════════

Period              │ Orders          │ Revenue
────────────────────┼─────────────────┼─────────────────────────────
Now (this sync)     │ {stats['this_sync']['count']:>15,} │ ${stats['this_sync']['amount']:>15,.2f}
Today               │ {stats['today']['count']:>15,} │ ${stats['today']['amount']:>15,.2f}
This Week           │ {stats['week']['count']:>15,} │ ${stats['week']['amount']:>15,.2f}
This Month          │ {stats['month']['count']:>15,} │ ${stats['month']['amount']:>15,.2f}
Last 30 Days        │ {stats['last_30_days']['count']:>15,} │ ${stats['last_30_days']['amount']:>15,.2f}
Avg/Day (30d)       │ {stats['avg_per_day']['count']:>15,.1f} │ ${stats['avg_per_day']['amount']:>15,.2f}

═══════════════════════════════════════════════════════════════════════
TOP 10 PATTERNS (LAST 30 DAYS)
═══════════════════════════════════════════════════════════════════════
"""

if top_patterns:
    for idx, pattern in enumerate(top_patterns, 1):
        product_title = pattern[0]
        order_count = pattern[1]
        total_quantity = pattern[2]
        total_revenue = float(pattern[3])
        body += f"""
{idx:>2}. {product_title}
    Orders: {order_count:>4,} │ Qty: {total_quantity:>4,} │ Revenue: ${total_revenue:>8,.2f}"""
else:
    body += """
No pattern data available"""

body += f"""

═══════════════════════════════════════════════════════════════════════

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Next sync in 5 minutes.

[This is a TEST email from test_table_format.py]
"""

print("="*70)
print("EMAIL PREVIEW")
print("="*70)
print(f"Subject: {subject}\n")
print(body)
print("="*70)

response = input("\nSend test email to ss@muffinsky.com? (yes/no): ").strip().lower()

if response in ['yes', 'y']:
    email_service = EmailService()
    result = email_service.send_report(subject, body)
    if result:
        print("✅ Test email sent!")
        print("   Check ss@muffinsky.com")
    else:
        print("❌ Failed to send")
else:
    print("Skipped")
