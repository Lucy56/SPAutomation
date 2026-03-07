#!/usr/bin/env python3
"""
Test UTC-8 (GMT-8) fixed timezone queries
"""

import os
import psycopg2
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_EXT_SHOPIFY_DATA')

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("="*80)
print("TESTING UTC-8 (GMT-8) FIXED TIMEZONE QUERIES")
print("="*80)

# Get current time in different timezones
cursor.execute("""
    SELECT
        NOW() as utc_time,
        (NOW() AT TIME ZONE 'UTC') AT TIME ZONE 'Etc/GMT+8' as shop_time,
        (NOW() AT TIME ZONE 'UTC') AT TIME ZONE 'America/Los_Angeles' as la_time
""")
result = cursor.fetchone()
print(f"\nCurrent UTC time:        {result[0]}")
print(f"Current Shop time (GMT-8): {result[1]}")
print(f"Current LA time (PDT/PST): {result[2]}")
print(f"\nNote: 'Etc/GMT+8' means UTC-8 (fixed, no DST)")

# Test NEW query with UTC-8
print("\n" + "="*80)
print("TODAY (using UTC-8 fixed offset):")
print("="*80)
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount,
        MIN(created_at) as first_order,
        MAX(created_at) as last_order,
        DATE((NOW() AT TIME ZONE 'UTC') AT TIME ZONE 'Etc/GMT+8') as shop_today
    FROM orders
    WHERE DATE((created_at AT TIME ZONE 'UTC') AT TIME ZONE 'Etc/GMT+8') =
          DATE((NOW() AT TIME ZONE 'UTC') AT TIME ZONE 'Etc/GMT+8')
    AND financial_status <> 'pending'
""")
result = cursor.fetchone()
print(f"Shop date (UTC-8): {result[4]}")
print(f"Orders: {result[0]:,}")
print(f"Revenue: ${float(result[1]):,.2f}")
if result[2]:
    print(f"First order (UTC): {result[2]}")
    print(f"Last order (UTC):  {result[3]}")

# Test THIS WEEK with UTC-8
print("\n" + "="*80)
print("THIS WEEK (using UTC-8 fixed offset):")
print("="*80)
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount,
        DATE(DATE_TRUNC('week', ((NOW() AT TIME ZONE 'UTC') AT TIME ZONE 'Etc/GMT+8'))) as week_start
    FROM orders
    WHERE ((created_at AT TIME ZONE 'UTC') AT TIME ZONE 'Etc/GMT+8') >=
          DATE_TRUNC('week', ((NOW() AT TIME ZONE 'UTC') AT TIME ZONE 'Etc/GMT+8'))
    AND financial_status <> 'pending'
""")
result = cursor.fetchone()
print(f"Week starts: {result[2]}")
print(f"Orders: {result[0]:,}")
print(f"Revenue: ${float(result[1]):,.2f}")

# Show sample orders from today (UTC-8)
print("\n" + "="*80)
print("SAMPLE ORDERS FROM TODAY (UTC-8):")
print("="*80)
cursor.execute("""
    SELECT
        order_number,
        created_at,
        (created_at AT TIME ZONE 'UTC') AT TIME ZONE 'Etc/GMT+8' as shop_time,
        total_price,
        financial_status
    FROM orders
    WHERE DATE((created_at AT TIME ZONE 'UTC') AT TIME ZONE 'Etc/GMT+8') =
          DATE((NOW() AT TIME ZONE 'UTC') AT TIME ZONE 'Etc/GMT+8')
    AND financial_status <> 'pending'
    ORDER BY created_at DESC
    LIMIT 5
""")

for row in cursor.fetchall():
    print(f"\nOrder {row[0]}")
    print(f"  UTC:      {row[1]}")
    print(f"  Shop:     {row[2]}")
    print(f"  Total:    ${float(row[3]):,.2f}")
    print(f"  Status:   {row[4]}")

# Check last 7 days by shop date
print("\n" + "="*80)
print("LAST 7 DAYS (by UTC-8 date):")
print("="*80)
cursor.execute("""
    SELECT
        DATE((created_at AT TIME ZONE 'UTC') AT TIME ZONE 'Etc/GMT+8') as shop_date,
        COUNT(*) as count,
        SUM(total_price) as revenue
    FROM orders
    WHERE created_at >= (NOW() - INTERVAL '7 days')
    AND financial_status <> 'pending'
    GROUP BY shop_date
    ORDER BY shop_date DESC
""")

for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]:>4,} orders | ${float(row[2]):>10,.2f}')

cursor.close()
conn.close()

print("\n" + "="*80)
