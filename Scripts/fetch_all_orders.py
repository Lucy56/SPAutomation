#!/usr/bin/env python3
"""
Initial Fetch: Download ALL historical orders from Shopify
This is a one-time operation to populate the database
"""

import os
import sqlite3
import requests
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from db_schema import get_db_path, initialize_database

def get_shopify_token():
    """Get Shopify admin API access token"""
    shop_url = "https://Sinclairp.myshopify.com"
    api_key = "YOUR_SHOPIFY_API_KEY"
    api_secret = "YOUR_SHOPIFY_SECRET"

    response = requests.post(
        f"{shop_url}/admin/oauth/access_token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": api_secret
        }
    )
    return response.json()['access_token']

def extract_utm_params(order):
    """Extract UTM parameters from landing_site"""
    landing_site = order.get('landing_site', '')
    if not landing_site:
        return None, None, None, None, None

    try:
        parsed = urlparse(landing_site)
        params = parse_qs(parsed.query)

        return (
            params.get('utm_source', [None])[0],
            params.get('utm_medium', [None])[0],
            params.get('utm_campaign', [None])[0],
            params.get('utm_content', [None])[0],
            params.get('utm_term', [None])[0]
        )
    except:
        return None, None, None, None, None

def fetch_all_orders_from_shopify(token):
    """Fetch ALL orders with pagination"""
    shop_url = "https://Sinclairp.myshopify.com"
    headers = {"X-Shopify-Access-Token": token}

    all_orders = []
    url = f"{shop_url}/admin/api/2024-10/orders.json?status=any&limit=250"

    page_count = 0

    print("Fetching all historical orders from Shopify...")
    print("This may take several minutes...\n")

    while url:
        page_count += 1
        print(f"  Page {page_count}: Fetching...", end="", flush=True)

        response = requests.get(url, headers=headers)
        data = response.json()
        orders = data.get('orders', [])

        all_orders.extend(orders)
        print(f" got {len(orders)} orders (total: {len(all_orders)})")

        # Check for pagination
        link_header = response.headers.get('Link', '')
        if 'rel="next"' in link_header:
            # Extract next URL from Link header
            next_link = [link.strip() for link in link_header.split(',') if 'rel="next"' in link][0]
            url = next_link.split(';')[0].strip('<>')
        else:
            url = None

    print(f"\n✓ Fetched {len(all_orders)} total orders across {page_count} pages")
    return all_orders

def save_orders_to_db(orders):
    """Save orders and line items to database"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    sync_start = datetime.now().isoformat()

    print(f"\nSaving {len(orders)} orders to database...")

    orders_saved = 0
    line_items_saved = 0

    for i, order in enumerate(orders, 1):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(orders)} orders...")

        # Extract UTM parameters
        utm_source, utm_medium, utm_campaign, utm_content, utm_term = extract_utm_params(order)

        # Extract shipping address for geographic data
        shipping = order.get('shipping_address') or {}

        # Prepare discount codes
        discount_codes = ','.join([dc['code'] for dc in order.get('discount_applications', [])])

        # Insert order
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO orders (
                    order_id, order_number, order_name, created_at, updated_at, processed_at,
                    customer_id, email,
                    country, country_code, province, city,
                    total_price, subtotal_price, total_tax, total_discounts, currency,
                    referring_site, landing_site, source_name,
                    utm_source, utm_medium, utm_campaign, utm_content, utm_term,
                    financial_status, fulfillment_status, cancelled_at, cancel_reason,
                    tags, note, discount_codes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order['id'],
                order.get('order_number'),
                order.get('name'),
                order.get('created_at'),
                order.get('updated_at'),
                order.get('processed_at'),
                order.get('customer', {}).get('id') if order.get('customer') else None,
                order.get('email'),
                shipping.get('country'),
                shipping.get('country_code'),
                shipping.get('province'),
                shipping.get('city'),
                float(order.get('total_price', 0)),
                float(order.get('subtotal_price', 0)),
                float(order.get('total_tax', 0)),
                float(order.get('total_discounts', 0)),
                order.get('currency'),
                order.get('referring_site'),
                order.get('landing_site'),
                order.get('source_name'),
                utm_source, utm_medium, utm_campaign, utm_content, utm_term,
                order.get('financial_status'),
                order.get('fulfillment_status'),
                order.get('cancelled_at'),
                order.get('cancel_reason'),
                order.get('tags'),
                order.get('note'),
                discount_codes
            ))
            orders_saved += 1

            # Insert line items
            for item in order.get('line_items', []):
                cursor.execute("""
                    INSERT OR REPLACE INTO line_items (
                        line_item_id, order_id, product_id, variant_id,
                        product_title, variant_title, sku, vendor,
                        quantity, price, total_discount, product_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['id'],
                    order['id'],
                    item.get('product_id'),
                    item.get('variant_id'),
                    item.get('title'),
                    item.get('variant_title'),
                    item.get('sku'),
                    item.get('vendor'),
                    item.get('quantity'),
                    float(item.get('price', 0)),
                    float(item.get('total_discount', 0)),
                    item.get('product_type')
                ))
                line_items_saved += 1

        except sqlite3.IntegrityError as e:
            print(f"    Warning: Skipping duplicate order {order['id']}")
            continue

    sync_end = datetime.now().isoformat()

    # Record sync history
    cursor.execute("""
        INSERT INTO sync_history (
            sync_type, sync_started_at, sync_completed_at,
            records_fetched, last_order_date, status
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        'initial_full_fetch',
        sync_start,
        sync_end,
        len(orders),
        max([o['created_at'] for o in orders]) if orders else None,
        'completed'
    ))

    conn.commit()
    conn.close()

    print(f"\n✓ Saved {orders_saved} orders and {line_items_saved} line items to database")
    return orders_saved, line_items_saved

if __name__ == '__main__':
    print("="*70)
    print("SINCLAIR PATTERNS - INITIAL DATA FETCH")
    print("="*70)
    print("\nThis script will:")
    print("  1. Initialize the SQLite database")
    print("  2. Fetch ALL historical orders from Shopify")
    print("  3. Save orders, line items, and UTM tracking to database")
    print("\nThis is a ONE-TIME operation and may take 5-10 minutes.")
    print("="*70)

    input("\nPress Enter to continue...")

    # Step 1: Initialize database
    print("\n[1/4] Initializing database...")
    initialize_database()

    # Step 2: Get Shopify token
    print("\n[2/4] Getting Shopify access token...")
    token = get_shopify_token()
    print("  ✓ Token obtained")

    # Step 3: Fetch all orders
    print("\n[3/4] Fetching all orders from Shopify...")
    orders = fetch_all_orders_from_shopify(token)

    # Step 4: Save to database
    print("\n[4/4] Saving to database...")
    orders_saved, line_items_saved = save_orders_to_db(orders)

    print("\n" + "="*70)
    print("INITIAL FETCH COMPLETE!")
    print("="*70)
    print(f"  Orders saved: {orders_saved}")
    print(f"  Line items saved: {line_items_saved}")
    print(f"  Database location: {get_db_path()}")
    print("\nNext steps:")
    print("  • Run 'python3 update_recent_orders.py' for daily updates")
    print("  • Run 'python3 analyze_weekly_specials.py' for pattern analysis")
    print("="*70)
