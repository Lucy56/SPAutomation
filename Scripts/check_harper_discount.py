#!/usr/bin/env python3
"""
Check Harper Cardigan discount data
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_EXT_SHOPIFY_DATA')

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Check Harper Cardigan specifically
cursor.execute("""
    SELECT
        li.product_title,
        li.quantity,
        li.price,
        li.total_discount,
        (li.quantity * li.price) as gross_revenue,
        (li.quantity * li.price) - li.total_discount as net_revenue,
        o.order_id,
        o.total_price as order_total
    FROM line_items li
    JOIN orders o ON li.order_id = o.order_id
    WHERE li.product_title LIKE '%Harper%Cardigan%'
    AND o.created_at >= NOW() - INTERVAL '30 days'
    AND o.financial_status <> 'pending'
    ORDER BY o.created_at DESC
    LIMIT 10
""")

print('HARPER CARDIGAN - RECENT ORDERS:')
print('='*80)
results = cursor.fetchall()
for row in results:
    print(f'Product: {row[0]}')
    print(f'  Qty: {row[1]} | Price: ${row[2]:.2f} | Discount: ${row[3]:.2f}')
    print(f'  Gross: ${row[4]:.2f} | Net: ${row[5]:.2f}')
    print(f'  Order: {row[6]} | Order Total: ${row[7]:.2f}')
    print()

# Get the total
cursor.execute("""
    SELECT
        COUNT(DISTINCT o.order_id) as order_count,
        SUM(li.quantity) as total_quantity,
        SUM(li.quantity * li.price) as gross_revenue,
        SUM(li.total_discount) as total_discounts,
        SUM((li.quantity * li.price) - li.total_discount) as net_revenue
    FROM line_items li
    JOIN orders o ON li.order_id = o.order_id
    WHERE li.product_title LIKE '%Harper%Cardigan%'
    AND o.created_at >= NOW() - INTERVAL '30 days'
    AND o.financial_status <> 'pending'
""")

totals = cursor.fetchone()
print('='*80)
print('HARPER CARDIGAN TOTALS (Last 30 Days):')
print(f'  Orders: {totals[0]}')
print(f'  Quantity: {totals[1]}')
print(f'  Gross Revenue: ${totals[2]:.2f}')
print(f'  Total Discounts: ${totals[3]:.2f}')
print(f'  Net Revenue: ${totals[4]:.2f}')
print()

# Check if the issue is that total_discount is always 0
cursor.execute("""
    SELECT COUNT(*), SUM(CASE WHEN total_discount > 0 THEN 1 ELSE 0 END) as with_discount
    FROM line_items
    WHERE product_title LIKE '%Harper%Cardigan%'
""")
discount_check = cursor.fetchone()
print(f'Total Harper line items: {discount_check[0]}')
print(f'Line items with discount > 0: {discount_check[1]}')

cursor.close()
conn.close()
