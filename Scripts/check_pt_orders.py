#!/usr/bin/env python3
"""
Check orders by PT date
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_EXT_SHOPIFY_DATA')

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# What day is TODAY in PT?
cursor.execute("SELECT DATE(NOW() AT TIME ZONE 'America/Los_Angeles')")
pt_today = cursor.fetchone()[0]
print(f'Today in PT: {pt_today}')

# Count all orders for that PT date
cursor.execute("""
    SELECT
        DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles') as pt_date,
        COUNT(*) as count,
        SUM(total_price) as revenue
    FROM orders
    WHERE DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles') = %s
    AND financial_status <> 'pending'
    GROUP BY pt_date
""", (pt_today,))

result = cursor.fetchone()
if result:
    print(f'Orders on {result[0]}: {result[1]:,}')
    print(f'Revenue: ${float(result[2]):,.2f}')
else:
    print('No orders found for today')

# Also check the last few days
print('\nLast 7 days (PT):')
cursor.execute("""
    SELECT
        DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles') as pt_date,
        COUNT(*) as count,
        SUM(total_price) as revenue
    FROM orders
    WHERE created_at >= (NOW() AT TIME ZONE 'America/Los_Angeles' - INTERVAL '7 days')
    AND financial_status <> 'pending'
    GROUP BY pt_date
    ORDER BY pt_date DESC
""")

for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]:>4,} orders | ${float(row[2]):>10,.2f}')

cursor.close()
conn.close()
