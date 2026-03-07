#!/usr/bin/env python3
"""
Test the proportional discount calculation for revenue
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_EXT_SHOPIFY_DATA')

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("="*80)
print("TESTING PROPORTIONAL DISCOUNT CALCULATION")
print("="*80)

# First, test with the OLD query (without order-level discounts)
cursor.execute("""
    SELECT
        li.product_title,
        COUNT(DISTINCT o.order_id) as order_count,
        SUM(li.quantity) as total_quantity,
        COALESCE(SUM((li.quantity * li.price) - li.total_discount), 0) as total_revenue
    FROM line_items li
    JOIN orders o ON li.order_id = o.order_id
    WHERE li.product_title ILIKE '%harper%'
    AND o.created_at >= NOW() - INTERVAL '30 days'
    AND o.financial_status != 'pending'
    AND o.financial_status <> 'pending'
    GROUP BY li.product_title
    ORDER BY order_count DESC
""")

print("\nOLD CALCULATION (line item discounts only):")
print("-"*80)
old_results = cursor.fetchall()
for row in old_results:
    print(f"{row[0]}")
    print(f"  Orders: {row[1]:,} | Qty: {row[2]:,} | Revenue: ${float(row[3]):,.2f}")

# Now test with the NEW query (with proportional order-level discounts using calculated subtotals)
cursor.execute("""
    WITH order_subtotals AS (
        SELECT
            order_id,
            SUM(quantity * price) as calculated_subtotal
        FROM line_items
        GROUP BY order_id
    )
    SELECT
        li.product_title,
        COUNT(DISTINCT o.order_id) as order_count,
        SUM(li.quantity) as total_quantity,
        COALESCE(SUM(
            (li.quantity * li.price)
            - li.total_discount
            - (
                CASE
                    WHEN os.calculated_subtotal > 0
                    THEN ((li.quantity * li.price) / os.calculated_subtotal) * o.total_discounts
                    ELSE 0
                END
            )
        ), 0) as total_revenue
    FROM line_items li
    JOIN orders o ON li.order_id = o.order_id
    JOIN order_subtotals os ON o.order_id = os.order_id
    WHERE li.product_title ILIKE '%harper%'
    AND o.created_at >= NOW() - INTERVAL '30 days'
    AND o.financial_status != 'pending'
    GROUP BY li.product_title
    ORDER BY order_count DESC
""")

print("\n" + "="*80)
print("NEW CALCULATION (with proportional order discounts):")
print("-"*80)
new_results = cursor.fetchall()
for row in new_results:
    print(f"{row[0]}")
    print(f"  Orders: {row[1]:,} | Qty: {row[2]:,} | Revenue: ${float(row[3]):,.2f}")

# Show the difference
print("\n" + "="*80)
print("DIFFERENCE:")
print("-"*80)
if old_results and new_results:
    old_rev = float(old_results[0][3])
    new_rev = float(new_results[0][3])
    diff = old_rev - new_rev
    print(f"Old revenue: ${old_rev:,.2f}")
    print(f"New revenue: ${new_rev:,.2f}")
    print(f"Difference:  ${diff:,.2f} ({diff/old_rev*100:.1f}% reduction)")

# Show a detailed example of one Harper order with discount
print("\n" + "="*80)
print("DETAILED EXAMPLE - One Harper order with discount:")
print("-"*80)

cursor.execute("""
    WITH order_subtotals AS (
        SELECT
            order_id,
            SUM(quantity * price) as calculated_subtotal
        FROM line_items
        GROUP BY order_id
    )
    SELECT
        o.order_id,
        o.subtotal_price as shopify_subtotal,
        os.calculated_subtotal,
        o.total_discounts,
        o.total_price,
        li.product_title,
        li.quantity,
        li.price,
        li.total_discount as line_discount,
        (li.quantity * li.price) as line_subtotal,
        CASE
            WHEN os.calculated_subtotal > 0
            THEN ((li.quantity * li.price) / os.calculated_subtotal) * o.total_discounts
            ELSE 0
        END as proportional_order_discount,
        (li.quantity * li.price) - li.total_discount -
        CASE
            WHEN os.calculated_subtotal > 0
            THEN ((li.quantity * li.price) / os.calculated_subtotal) * o.total_discounts
            ELSE 0
        END as net_revenue
    FROM orders o
    JOIN line_items li ON o.order_id = li.order_id
    JOIN order_subtotals os ON o.order_id = os.order_id
    WHERE li.product_title ILIKE '%harper%'
    AND o.total_discounts > 0
    AND o.created_at >= NOW() - INTERVAL '10 days'
    AND o.financial_status != 'pending'
    LIMIT 5
""")

examples = cursor.fetchall()
for row in examples:
    print(f"\nOrder: {row[0]}")
    print(f"  Shopify subtotal:     ${float(row[1]):,.2f}")
    print(f"  Calculated subtotal:  ${float(row[2]):,.2f}")
    print(f"  Order discount:       ${float(row[3]):,.2f}")
    print(f"  Order total:          ${float(row[4]):,.2f}")
    print(f"  Product: {row[5]}")
    print(f"  Line: {row[6]} × ${float(row[7]):,.2f} = ${float(row[9]):,.2f}")
    print(f"  Line discount: ${float(row[8]):,.2f}")
    print(f"  Proportional order discount: ${float(row[10]):,.2f}")
    print(f"  → Net revenue: ${float(row[11]):,.2f}")

cursor.close()
conn.close()

print("\n" + "="*80)
print("✅ Test complete")
print("="*80)
