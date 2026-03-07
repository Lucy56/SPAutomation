#!/usr/bin/env python3
"""
Check order-level discount codes
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_EXT_SHOPIFY_DATA')

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# First, check what discount-related fields exist in orders table
print("="*80)
print("ORDERS TABLE COLUMNS (discount related):")
print("="*80)

cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'orders'
    AND (column_name ILIKE '%discount%' OR column_name ILIKE '%code%')
    ORDER BY ordinal_position
""")

for row in cursor.fetchall():
    print(f"  {row[0]:30} {row[1]}")

# Check for orders with discount codes
print("\n" + "="*80)
print("SAMPLE ORDERS WITH DISCOUNT CODES:")
print("="*80)

cursor.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'orders'
    ORDER BY ordinal_position
""")

all_columns = [row[0] for row in cursor.fetchall()]
print(f"\nAll order columns: {', '.join(all_columns)}")

# Check if there's a discount_codes or similar field
if 'discount_codes' in all_columns:
    print("\n✓ Found 'discount_codes' column")
    cursor.execute("""
        SELECT order_id, discount_codes, total_price, total_discounts, created_at
        FROM orders
        WHERE discount_codes IS NOT NULL AND discount_codes != ''
        ORDER BY created_at DESC
        LIMIT 10
    """)

    results = cursor.fetchall()
    print(f"\nOrders with discount codes: {len(results)}")
    for row in results:
        print(f"\nOrder: {row[0]}")
        print(f"  Discount codes: {row[1]}")
        print(f"  Total price: ${float(row[2]):.2f}")
        disc = float(row[3]) if row[3] else 0
        print(f"  Total discounts: ${disc:.2f}")
        print(f"  Date: {row[4]}")

if 'total_discounts' in all_columns:
    print("\n✓ Found 'total_discounts' column")
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN total_discounts > 0 THEN 1 ELSE 0 END) as with_discount
        FROM orders
    """)
    stats = cursor.fetchone()
    print(f"\nTotal orders: {stats[0]:,}")
    print(f"Orders with total_discounts > 0: {stats[1]:,}")

# Now check Harper orders specifically with discount info
print("\n" + "="*80)
print("HARPER ORDERS WITH DISCOUNTS:")
print("="*80)

cursor.execute("""
    SELECT
        o.order_id,
        o.total_price,
        o.total_discounts,
        o.discount_codes,
        li.product_title,
        li.quantity,
        li.price,
        li.total_discount as line_discount,
        o.created_at
    FROM orders o
    JOIN line_items li ON o.order_id = li.order_id
    WHERE li.product_title ILIKE '%harper%'
    AND o.created_at >= NOW() - INTERVAL '30 days'
    AND o.financial_status <> 'pending'
    AND (o.total_discounts > 0 OR li.total_discount > 0)
    ORDER BY o.created_at DESC
    LIMIT 20
""")

harper_discounts = cursor.fetchall()
print(f"\nHarper orders with discounts: {len(harper_discounts)}")
for row in harper_discounts:
    order_disc = float(row[2]) if row[2] else 0
    line_disc = float(row[7]) if row[7] else 0
    print(f"\nOrder: {row[0]}")
    print(f"  Order total: ${float(row[1]):.2f} | Order discount: ${order_disc:.2f}")
    print(f"  Discount code: {row[3] if row[3] else 'None'}")
    print(f"  Product: {row[4]}")
    print(f"  Line: Qty {row[5]} × ${float(row[6]):.2f} | Line discount: ${line_disc:.2f}")
    print(f"  Date: {row[8]}")

cursor.close()
conn.close()
