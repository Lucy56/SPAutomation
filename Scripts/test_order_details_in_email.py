#!/usr/bin/env python3
"""
Test the order details in sync notification
"""

import os
import sys
import psycopg2
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../deployments/railway-updater'))
from email_service import EmailService

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_EXT_SHOPIFY_DATA")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Get recent orders to simulate a sync
cursor.execute("""
    SELECT order_number, total_price
    FROM orders
    WHERE created_at >= NOW() - INTERVAL '24 hours'
    ORDER BY created_at DESC
    LIMIT 5
""")
recent_orders = cursor.fetchall()

cursor.close()
conn.close()

print("="*80)
print("TEST ORDER DETAILS IN EMAIL")
print("="*80)

# Simulate stats with order details
orders_count = len(recent_orders)
total_amount = sum(float(order[1]) for order in recent_orders)

print(f"\nSimulated sync:")
print(f"  Orders: {orders_count}")
print(f"  Total amount: ${total_amount:.2f}")
print(f"\nOrder details:")
for order_num, amount in recent_orders:
    print(f"  {order_num} (${float(amount):.2f})")

# Build the email preview
bne_tz = timezone(timedelta(hours=10))
bne_time = datetime.now(bne_tz).strftime('%Y-%m-%d %H:%M:%S')

pt_tz = timezone(timedelta(hours=-8))
pt_now = datetime.now(pt_tz)
pt_midnight = pt_now.replace(hour=23, minute=59, second=59, microsecond=999999)
hours_left_pt = (pt_midnight - pt_now).total_seconds() / 3600

# Build order details
orders_list = []
for order_num, amount in recent_orders:
    orders_list.append(f"{order_num} (${float(amount):,.2f})")
order_details = f"<br>Orders: {', '.join(orders_list)}"

preview = f"""
<div class="sync-info">
    <strong>This Sync ({bne_time} BNE)</strong><br>
    Orders imported/updated: <strong>{orders_count:,}</strong><br>
    Line items processed: <strong>{orders_count * 2:,}</strong><br>
    Total amount: <strong>${total_amount:,.2f}</strong>{order_details}
</div>
"""

print("\n" + "="*80)
print("EMAIL PREVIEW (HTML):")
print("="*80)
print(preview)

print("\n" + "="*80)
print("TEXT VERSION:")
print("="*80)
print(f"This Sync ({bne_time} BNE)")
print(f"Orders imported/updated: {orders_count:,}")
print(f"Line items processed: {orders_count * 2:,}")
print(f"Total amount: ${total_amount:,.2f}")
print(f"Orders: {', '.join(orders_list)}")

print("\n" + "="*80)
response = input("\nSend test email to ss@muffinsky.com? (yes/no): ").strip().lower()

if response in ['yes', 'y']:
    # Create full HTML email
    body = f"""<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Lato', Arial, sans-serif; line-height: 1.5; color: #333; font-size: 14px; margin: 0; padding: 0; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .header-title {{ margin: 0; font-size: 16px; font-weight: 400; }}
        .content {{ padding: 20px; max-width: 800px; margin: 0 auto; }}
        .sync-info {{
            background-color: #f9f9ff;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #667eea;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">Shopify Sync Complete (TEST)</div>
    </div>
    <div class="content">
        {preview}
        <p style="color: #999; font-size: 11px; margin-top: 20px;">
            This is a TEST email to verify order details are displayed correctly.
        </p>
    </div>
</body>
</html>"""

    email_service = EmailService()
    result = email_service.send_report("Shopify Sync Complete (TEST - Order Details)", body, html=True)

    if result:
        print("✅ Test email sent!")
        print("   Check ss@muffinsky.com")
    else:
        print("❌ Failed to send")
else:
    print("Skipped")
