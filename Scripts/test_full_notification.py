#!/usr/bin/env python3
"""
Test the complete sync notification with top patterns
"""

import os
import sys
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# Add the railway-updater directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../deployments/railway-updater'))

from email_service import EmailService

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_EXT_SHOPIFY_DATA")

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

print("="*70)
print("FULL SYNC NOTIFICATION TEST")
print("="*70)

# Get all stats from database
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Get stats for this sync
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount
    FROM orders
    WHERE synced_at >= NOW() - INTERVAL '10 minutes'
""")
this_sync = cursor.fetchone()

# Get today's stats
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount
    FROM orders
    WHERE DATE(created_at) = CURRENT_DATE
    AND financial_status != 'pending'
""")
today = cursor.fetchone()

# Get this week's stats
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount
    FROM orders
    WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)
    AND financial_status != 'pending'
""")
week = cursor.fetchone()

# Get this month's stats
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount
    FROM orders
    WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)
    AND financial_status != 'pending'
""")
month = cursor.fetchone()

# Get top 10 patterns in last 30 days
cursor.execute("""
    SELECT
        li.product_title,
        COUNT(DISTINCT o.order_id) as order_count,
        SUM(li.quantity) as total_quantity,
        COALESCE(SUM(li.quantity * li.price), 0) as total_revenue
    FROM line_items li
    JOIN orders o ON li.order_id = o.order_id
    WHERE o.created_at >= NOW() - INTERVAL '30 days'
    AND o.financial_status != 'pending'
    AND li.product_title IS NOT NULL
    GROUP BY li.product_title
    ORDER BY order_count DESC
    LIMIT 10
""")
top_patterns = cursor.fetchall()

cursor.close()
conn.close()

stats = {
    'this_sync': {'count': this_sync[0], 'amount': float(this_sync[1])},
    'today': {'count': today[0], 'amount': float(today[1])},
    'week': {'count': week[0], 'amount': float(week[1])},
    'month': {'count': month[0], 'amount': float(month[1])},
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

Today (so far):
  • Orders: {stats['today']['count']:,}
  • Revenue: ${stats['today']['amount']:,.2f}

This Week (so far):
  • Orders: {stats['week']['count']:,}
  • Revenue: ${stats['week']['amount']:,.2f}

This Month (so far):
  • Orders: {stats['month']['count']:,}
  • Revenue: ${stats['month']['amount']:,.2f}

Top 10 Patterns (Last 30 Days):"""

if top_patterns:
    for idx, pattern in enumerate(top_patterns, 1):
        product_title = pattern[0]
        order_count = pattern[1]
        total_quantity = pattern[2]
        total_revenue = float(pattern[3])
        body += f"""
  {idx}. {product_title}
     Orders: {order_count:,} | Qty: {total_quantity:,} | Revenue: ${total_revenue:,.2f}"""
else:
    body += """
  No pattern data available"""

body += f"""

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Next sync in 5 minutes.

[This is a TEST email from test_full_notification.py]
"""

print("\nEMAIL PREVIEW:")
print("="*70)
print(f"Subject: {subject}\n")
print(body)
print("="*70)

# Ask if user wants to send test email
response = input("\nSend test email to ss@muffinsky.com? (yes/no): ").strip().lower()

if response in ['yes', 'y']:
    email_service = EmailService()
    result = email_service.send_report(subject, body)

    if result:
        print("✅ Test email sent successfully!")
        print("   Check ss@muffinsky.com")
    else:
        print("❌ Failed to send test email")
else:
    print("Skipped sending email")
