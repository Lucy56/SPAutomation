#!/usr/bin/env python3
"""
Test PT timezone queries
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
print("TESTING PT TIMEZONE QUERIES")
print("="*80)

# Get current time in different timezones
cursor.execute("SELECT NOW(), NOW() AT TIME ZONE 'America/Los_Angeles'")
utc_time, pt_time = cursor.fetchone()
print(f"\nCurrent UTC time: {utc_time}")
print(f"Current PT time:  {pt_time}")

# Test OLD query (using CURRENT_DATE - database timezone)
print("\n" + "="*80)
print("OLD QUERY (using CURRENT_DATE):")
print("="*80)
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount,
        MIN(created_at) as first_order,
        MAX(created_at) as last_order
    FROM orders
    WHERE DATE(created_at) = CURRENT_DATE
    AND financial_status != 'pending'
""")
old_result = cursor.fetchone()
print(f"Orders: {old_result[0]:,}")
print(f"Revenue: ${float(old_result[1]):,.2f}")
if old_result[2]:
    print(f"First order: {old_result[2]}")
    print(f"Last order:  {old_result[3]}")

# Test NEW query (using PT timezone)
print("\n" + "="*80)
print("NEW QUERY (using PT timezone):")
print("="*80)
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount,
        MIN(created_at) as first_order,
        MAX(created_at) as last_order
    FROM orders
    WHERE DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles') =
          DATE(NOW() AT TIME ZONE 'America/Los_Angeles')
    AND financial_status != 'pending'
""")
new_result = cursor.fetchone()
print(f"Orders: {new_result[0]:,}")
print(f"Revenue: ${float(new_result[1]):,.2f}")
if new_result[2]:
    print(f"First order: {new_result[2]}")
    print(f"Last order:  {new_result[3]}")

# Show some sample orders from today PT
print("\n" + "="*80)
print("SAMPLE ORDERS FROM TODAY (PT):")
print("="*80)
cursor.execute("""
    SELECT
        order_number,
        created_at,
        created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles' as pt_time,
        total_price,
        financial_status
    FROM orders
    WHERE DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles') =
          DATE(NOW() AT TIME ZONE 'America/Los_Angeles')
    AND financial_status != 'pending'
    ORDER BY created_at DESC
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"\nOrder {row[0]}")
    print(f"  UTC: {row[1]}")
    print(f"  PT:  {row[2]}")
    print(f"  Total: ${float(row[3]):,.2f}")
    print(f"  Status: {row[4]}")

cursor.close()
conn.close()

print("\n" + "="*80)
print("Expected: 581 orders")
print("="*80)
