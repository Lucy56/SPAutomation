#!/usr/bin/env python3
"""
Test the top patterns query
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_EXT_SHOPIFY_DATA")

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

print("="*70)
print("TOP PATTERNS TEST (Last 30 Days)")
print("="*70)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Get top 10 patterns in last 30 days
cursor.execute("""
    SELECT
        li.product_title,
        COUNT(DISTINCT o.order_id) as order_count,
        SUM(li.quantity) as total_quantity,
        COALESCE(SUM(li.quantity * li.price), 0) as total_revenue
    FROM line_items li
    JOIN orders o ON li.order_id = o.order_id
    WHERE o.created_at >= NOW() - INTERVAL '30 days'
    AND o.financial_status != 'pending'
    AND li.product_title IS NOT NULL
    GROUP BY li.product_title
    ORDER BY order_count DESC
    LIMIT 10
""")

top_patterns = cursor.fetchall()

print("\nTop 10 Patterns by Order Count:")
print("-" * 70)

if top_patterns:
    for idx, pattern in enumerate(top_patterns, 1):
        product_title = pattern[0]
        order_count = pattern[1]
        total_quantity = pattern[2]
        total_revenue = float(pattern[3])

        print(f"\n{idx}. {product_title}")
        print(f"   Orders: {order_count:,} | Qty: {total_quantity:,} | Revenue: ${total_revenue:,.2f}")
else:
    print("No pattern data available")

# Preview email format
print("\n" + "="*70)
print("EMAIL PREVIEW:")
print("="*70)

email_body = """Top 10 Patterns (Last 30 Days):"""

if top_patterns:
    for idx, pattern in enumerate(top_patterns, 1):
        product_title = pattern[0]
        order_count = pattern[1]
        total_quantity = pattern[2]
        total_revenue = float(pattern[3])
        email_body += f"""
  {idx}. {product_title}
     Orders: {order_count:,} | Qty: {total_quantity:,} | Revenue: ${total_revenue:,.2f}"""
else:
    email_body += """
  No pattern data available"""

print(email_body)

cursor.close()
conn.close()

print("\n" + "="*70)
print("✅ Query completed successfully!")
print("="*70)
