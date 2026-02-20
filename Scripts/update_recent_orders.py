#!/usr/bin/env python3
"""
Incremental Update: Fetch only new orders since last sync
Run this daily/weekly to keep database current
"""

import sqlite3
import requests
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from db_schema import get_db_path

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

def get_last_sync_date():
    """Get the date of the last successful sync"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT last_order_date FROM sync_history
        WHERE status = 'completed'
        ORDER BY sync_completed_at DESC
        LIMIT 1
    """)

    result = cursor.fetchone()
    conn.close()

    if result and result[0]:
        return result[0]
    else:
        # If no sync history, get earliest order from database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(created_at) FROM orders")
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            return result[0]

    # Default to 7 days ago if no history
    return (datetime.now() - timedelta(days=7)).isoformat()

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

def fetch_recent_orders(token, since_date):
    """Fetch orders created after since_date"""
    shop_url = "https://Sinclairp.myshopify.com"
    headers = {"X-Shopify-Access-Token": token}

    all_orders = []
    url = f"{shop_url}/admin/api/2024-10/orders.json?status=any&limit=250&created_at_min={since_date}&updated_at_min={since_date}"

    print(f"Fetching orders since {since_date}...")

    page_count = 0
    while url:
        page_count += 1
        print(f"  Page {page_count}...", end="", flush=True)

        response = requests.get(url, headers=headers)
        data = response.json()
        orders = data.get('orders', [])

        all_orders.extend(orders)
        print(f" {len(orders)} orders")

        # Check for pagination
        link_header = response.headers.get('Link', '')
        if 'rel="next"' in link_header:
            next_link = [link.strip() for link in link_header.split(',') if 'rel="next"' in link][0]
            url = next_link.split(';')[0].strip('<>')
        else:
            url = None

    print(f"✓ Fetched {len(all_orders)} new/updated orders")
    return all_orders

def update_database(orders):
    """Update database with new orders"""
    if not orders:
        print("No new orders to update")
        return 0, 0

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    sync_start = datetime.now().isoformat()

    orders_updated = 0
    line_items_updated = 0

    for order in orders:
        utm_source, utm_medium, utm_campaign, utm_content, utm_term = extract_utm_params(order)
        shipping = order.get('shipping_address') or {}
        discount_codes = ','.join([dc['code'] for dc in order.get('discount_applications', [])])

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
            order['id'], order.get('order_number'), order.get('name'),
            order.get('created_at'), order.get('updated_at'), order.get('processed_at'),
            order.get('customer', {}).get('id') if order.get('customer') else None,
            order.get('email'),
            shipping.get('country'), shipping.get('country_code'),
            shipping.get('province'), shipping.get('city'),
            float(order.get('total_price', 0)), float(order.get('subtotal_price', 0)),
            float(order.get('total_tax', 0)), float(order.get('total_discounts', 0)),
            order.get('currency'),
            order.get('referring_site'), order.get('landing_site'), order.get('source_name'),
            utm_source, utm_medium, utm_campaign, utm_content, utm_term,
            order.get('financial_status'), order.get('fulfillment_status'),
            order.get('cancelled_at'), order.get('cancel_reason'),
            order.get('tags'), order.get('note'), discount_codes
        ))
        orders_updated += 1

        # Delete old line items for this order
        cursor.execute("DELETE FROM line_items WHERE order_id = ?", (order['id'],))

        # Insert line items
        for item in order.get('line_items', []):
            cursor.execute("""
                INSERT INTO line_items (
                    line_item_id, order_id, product_id, variant_id,
                    product_title, variant_title, sku, vendor,
                    quantity, price, total_discount, product_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item['id'], order['id'], item.get('product_id'), item.get('variant_id'),
                item.get('title'), item.get('variant_title'), item.get('sku'), item.get('vendor'),
                item.get('quantity'), float(item.get('price', 0)),
                float(item.get('total_discount', 0)), item.get('product_type')
            ))
            line_items_updated += 1

    sync_end = datetime.now().isoformat()

    # Record sync history
    cursor.execute("""
        INSERT INTO sync_history (
            sync_type, sync_started_at, sync_completed_at,
            records_fetched, last_order_date, status
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        'incremental_update',
        sync_start,
        sync_end,
        len(orders),
        max([o['created_at'] for o in orders]) if orders else None,
        'completed'
    ))

    conn.commit()
    conn.close()

    return orders_updated, line_items_updated

if __name__ == '__main__':
    print("="*70)
    print("SINCLAIR PATTERNS - INCREMENTAL UPDATE")
    print("="*70)

    # Get last sync date
    print("\n[1/4] Checking last sync...")
    last_sync = get_last_sync_date()
    print(f"  Last sync: {last_sync}")

    # Get token
    print("\n[2/4] Getting Shopify access token...")
    token = get_shopify_token()
    print("  ✓ Token obtained")

    # Fetch recent orders
    print("\n[3/4] Fetching recent orders...")
    orders = fetch_recent_orders(token, last_sync)

    # Update database
    print("\n[4/4] Updating database...")
    orders_updated, line_items_updated = update_database(orders)

    print("\n" + "="*70)
    print("UPDATE COMPLETE!")
    print("="*70)
    print(f"  Orders updated: {orders_updated}")
    print(f"  Line items updated: {line_items_updated}")
    print("="*70)
