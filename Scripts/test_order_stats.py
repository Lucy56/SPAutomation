#!/usr/bin/env python3
"""
Test the order stats queries
"""

import os
import sys
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# Add the railway-updater directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../deployments/railway-updater'))

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_EXT_SHOPIFY_DATA")

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

print("="*70)
print("ORDER STATISTICS TEST")
print("="*70)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Test 1: Recent sync (last 10 minutes)
print("\n📊 Orders from last 10 minutes:")
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount
    FROM orders
    WHERE synced_at >= NOW() - INTERVAL '10 minutes'
""")
result = cursor.fetchone()
print(f"   Count: {result[0]:,}")
print(f"   Amount: ${float(result[1]):,.2f}")

# Test 2: Today's orders
print("\n📊 Today's orders (created today):")
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount
    FROM orders
    WHERE DATE(created_at) = CURRENT_DATE
    AND financial_status != 'pending'
""")
result = cursor.fetchone()
print(f"   Count: {result[0]:,}")
print(f"   Amount: ${float(result[1]):,.2f}")

# Test 3: This week's orders
print("\n📊 This week's orders (Monday to now):")
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount
    FROM orders
    WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)
    AND financial_status != 'pending'
""")
result = cursor.fetchone()
print(f"   Count: {result[0]:,}")
print(f"   Amount: ${float(result[1]):,.2f}")

# Test 4: This month's orders
print("\n📊 This month's orders:")
cursor.execute("""
    SELECT
        COUNT(*) as count,
        COALESCE(SUM(total_price), 0) as total_amount
    FROM orders
    WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)
    AND financial_status != 'pending'
""")
result = cursor.fetchone()
print(f"   Count: {result[0]:,}")
print(f"   Amount: ${float(result[1]):,.2f}")

# Test 5: Show current date/time for reference
print("\n📅 Current database time:")
cursor.execute("SELECT NOW(), CURRENT_DATE")
result = cursor.fetchone()
print(f"   NOW(): {result[0]}")
print(f"   CURRENT_DATE: {result[1]}")

# Test 6: Show week start for reference
print("\n📅 Week boundaries:")
cursor.execute("SELECT DATE_TRUNC('week', CURRENT_DATE), DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '6 days'")
result = cursor.fetchone()
print(f"   Week starts: {result[0]} (Monday)")
print(f"   Week ends: {result[1]} (Sunday)")

# Test 7: Show month boundaries
print("\n📅 Month boundaries:")
cursor.execute("SELECT DATE_TRUNC('month', CURRENT_DATE), DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day'")
result = cursor.fetchone()
print(f"   Month starts: {result[0]}")
print(f"   Month ends: {result[1]}")

cursor.close()
conn.close()

print("\n" + "="*70)
print("✅ All stats queries completed successfully!")
print("="*70)
