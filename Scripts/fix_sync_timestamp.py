#!/usr/bin/env python3
"""
Fix incorrect sync timestamp in database
The sync_history table has a future date (2026) instead of 2025
"""

import os
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_EXT_SHOPIFY_DATA")

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Check current sync history
print("Current sync history:")
cursor.execute("""
    SELECT id, sync_started_at, last_order_date, status
    FROM sync_history
    ORDER BY sync_started_at DESC
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  {row}")

print("\nFixing timestamps...")

# Option 1: Delete all sync history to start fresh
cursor.execute("DELETE FROM sync_history")

# Option 2: Or set last sync to 1 day ago to fetch recent orders
# one_day_ago = (datetime.now() - timedelta(days=1)).isoformat()
# cursor.execute("""
#     UPDATE sync_history
#     SET last_order_date = %s
#     WHERE status = 'completed'
# """, (one_day_ago,))

conn.commit()

print("✅ Sync history cleared")
print("   Next sync will fetch all orders from the beginning")

# Check orders in database
cursor.execute("SELECT COUNT(*) FROM orders")
order_count = cursor.fetchone()[0]
print(f"\nCurrent orders in database: {order_count:,}")

cursor.close()
conn.close()
