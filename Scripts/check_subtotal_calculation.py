#!/usr/bin/env python3
"""
Check how subtotal_price is calculated and if we need to use line items
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_EXT_SHOPIFY_DATA')

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("="*80)
print("CHECKING SUBTOTAL CALCULATION")
print("="*80)

# Check orders with discounts
cursor.execute("""
    SELECT
        o.order_id,
        o.subtotal_price,
        o.total_discounts,
        o.total_price,
        SUM(li.quantity * li.price) as calculated_subtotal_from_lines
    FROM orders o
    JOIN line_items li ON o.order_id = li.order_id
    WHERE o.total_discounts > 0
    AND o.created_at >= NOW() - INTERVAL '5 days'
    GROUP BY o.order_id, o.subtotal_price, o.total_discounts, o.total_price
    ORDER BY o.created_at DESC
    LIMIT 10
""")

print("\nOrders with discounts:")
print("-"*80)
results = cursor.fetchall()
for row in results:
    print(f"\nOrder: {row[0]}")
    print(f"  Shopify subtotal_price: ${float(row[1]):,.2f}")
    print(f"  Calculated from lines:  ${float(row[4]):,.2f}")
    print(f"  Total discounts:        ${float(row[2]):,.2f}")
    print(f"  Total price:            ${float(row[3]):,.2f}")
    print(f"  Match: {abs(float(row[1]) - float(row[4])) < 0.01}")

# Check the specific Harper orders
print("\n" + "="*80)
print("HARPER ORDERS - Subtotal comparison:")
print("-"*80)

cursor.execute("""
    SELECT
        o.order_id,
        o.subtotal_price as shopify_subtotal,
        o.total_discounts,
        o.total_price,
        SUM(li.quantity * li.price) as line_items_subtotal,
        li.product_title
    FROM orders o
    JOIN line_items li ON o.order_id = li.order_id
    WHERE li.product_title ILIKE '%harper%'
    AND o.total_discounts > 0
    AND o.created_at >= NOW() - INTERVAL '5 days'
    GROUP BY o.order_id, o.subtotal_price, o.total_discounts, o.total_price, li.product_title
    LIMIT 10
""")

harper_orders = cursor.fetchall()
for row in harper_orders:
    shopify_sub = float(row[1])
    line_sub = float(row[4])
    discount = float(row[2])
    total = float(row[3])

    print(f"\nOrder: {row[0]}")
    print(f"  Product: {row[5]}")
    print(f"  Shopify subtotal:    ${shopify_sub:,.2f}")
    print(f"  Line items subtotal: ${line_sub:,.2f}")
    print(f"  Order discount:      ${discount:,.2f}")
    print(f"  Order total:         ${total:,.2f}")
    print(f"  Expected: ${line_sub:,.2f} - ${discount:,.2f} = ${line_sub - discount:,.2f}")
    print(f"  Actual:   ${total:,.2f}")

cursor.close()
conn.close()

print("\n" + "="*80)
print("CONCLUSION:")
print("  If Shopify's subtotal_price is 0 when there's a 100% discount,")
print("  we need to calculate subtotal from line items instead.")
print("="*80)
