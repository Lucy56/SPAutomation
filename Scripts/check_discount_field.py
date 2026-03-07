#!/usr/bin/env python3
"""
Check if total_discount field is populated correctly
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_EXT_SHOPIFY_DATA')

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Find products with any discount
print("="*80)
print("CHECKING DISCOUNT FIELD POPULATION")
print("="*80)

cursor.execute("""
    SELECT COUNT(*) as total_line_items,
           SUM(CASE WHEN total_discount > 0 THEN 1 ELSE 0 END) as items_with_discount,
           SUM(CASE WHEN total_discount IS NULL THEN 1 ELSE 0 END) as items_null_discount
    FROM line_items
""")
stats = cursor.fetchone()
print(f"\nTotal line items: {stats[0]:,}")
print(f"Items with discount > 0: {stats[1]:,}")
print(f"Items with NULL discount: {stats[2]:,}")
print(f"Percentage with discount: {(stats[1]/stats[0]*100):.1f}%")

# Find example line items with discounts
print("\n" + "="*80)
print("SAMPLE LINE ITEMS WITH DISCOUNTS:")
print("="*80)

cursor.execute("""
    SELECT
        li.product_title,
        li.quantity,
        li.price,
        li.total_discount,
        o.order_id,
        o.created_at
    FROM line_items li
    JOIN orders o ON li.order_id = o.order_id
    WHERE li.total_discount > 0
    ORDER BY o.created_at DESC
    LIMIT 10
""")

results = cursor.fetchall()
for row in results:
    print(f"\nProduct: {row[0]}")
    print(f"  Qty: {row[1]} | Price: ${row[2]:.2f} | Discount: ${row[3]:.2f}")
    print(f"  Order: {row[4]} | Date: {row[5]}")

# Now search for Harper in all line items
print("\n" + "="*80)
print("SEARCHING FOR HARPER PRODUCTS (ALL TIME):")
print("="*80)

cursor.execute("""
    SELECT DISTINCT product_title
    FROM line_items
    WHERE product_title ILIKE '%harper%'
    LIMIT 10
""")

harper_products = cursor.fetchall()
if harper_products:
    print(f"\nFound {len(harper_products)} Harper products:")
    for row in harper_products:
        print(f"  - {row[0]}")

    # Get stats for each Harper product
    print("\n" + "="*80)
    print("HARPER PRODUCT STATS (Last 30 Days):")
    print("="*80)

    cursor.execute("""
        SELECT
            li.product_title,
            COUNT(DISTINCT o.order_id) as order_count,
            SUM(li.quantity) as total_quantity,
            COALESCE(SUM(li.quantity * li.price), 0) as gross_revenue,
            COALESCE(SUM(li.total_discount), 0) as total_discounts,
            COALESCE(SUM((li.quantity * li.price) - li.total_discount), 0) as net_revenue
        FROM line_items li
        JOIN orders o ON li.order_id = o.order_id
        WHERE li.product_title ILIKE '%harper%'
        AND o.created_at >= NOW() - INTERVAL '30 days'
        AND o.financial_status <> 'pending'
        GROUP BY li.product_title
        ORDER BY order_count DESC
    """)

    harper_stats = cursor.fetchall()
    for row in harper_stats:
        print(f"\n{row[0]}")
        print(f"  Orders: {row[1]:,} | Qty: {row[2]:,}")
        print(f"  Gross: ${row[3]:,.2f} | Discounts: ${row[4]:,.2f} | Net: ${row[5]:,.2f}")
else:
    print("\nNo Harper products found")

cursor.close()
conn.close()
