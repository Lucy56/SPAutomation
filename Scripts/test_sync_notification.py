#!/usr/bin/env python3
"""
Test the sync notification with real stats
"""

import os
import sys
import psycopg2
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
print("SYNC NOTIFICATION TEST")
print("="*70)

# Get stats from database
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
this_sync_count = this_sync[0]
this_sync_amount = float(this_sync[1])

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
today_count = today[0]
today_amount = float(today[1])

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
week_count = week[0]
week_amount = float(week[1])

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
month_count = month[0]
month_amount = float(month[1])

cursor.close()
conn.close()

stats = {
    'this_sync': {'count': this_sync_count, 'amount': this_sync_amount},
    'today': {'count': today_count, 'amount': today_amount},
    'week': {'count': week_count, 'amount': week_amount},
    'month': {'count': month_count, 'amount': month_amount}
}

print("\nStats gathered:")
print(f"  This sync: {stats['this_sync']['count']} orders, ${stats['this_sync']['amount']:,.2f}")
print(f"  Today: {stats['today']['count']} orders, ${stats['today']['amount']:,.2f}")
print(f"  This week: {stats['week']['count']} orders, ${stats['week']['amount']:,.2f}")
print(f"  This month: {stats['month']['count']} orders, ${stats['month']['amount']:,.2f}")

# Build email body
from datetime import datetime

subject = "✅ Shopify Sync Complete (TEST)"

orders_count = this_sync_count
line_items_count = orders_count * 2  # Simulated

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

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Next sync in 5 minutes.

[This is a TEST email from test_sync_notification.py]
"""

print("\n" + "="*70)
print("EMAIL PREVIEW:")
print("="*70)
print(f"Subject: {subject}")
print(f"\n{body}")
print("="*70)

# Ask if user wants to send test email
response = input("\nSend test email? (yes/no): ").strip().lower()

if response in ['yes', 'y']:
    email_service = EmailService()
    result = email_service.send_notification(subject, body)

    if result:
        print("✅ Test email sent successfully!")
        print(f"   Check {email_service.email_to}")
    else:
        print("❌ Failed to send test email")
else:
    print("Skipped sending email")
