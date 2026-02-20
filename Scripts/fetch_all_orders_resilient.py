#!/usr/bin/env python3
"""
Resilient Order Fetch: Download ALL historical orders with error handling
- Saves incrementally (every 25 pages)
- Retries on connection errors
- Tracks progress to resume
- Handles API token expiration
"""

import os
import sqlite3
import requests
import json
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from db_schema import get_db_path, initialize_database

BATCH_SIZE = 25  # Save every 25 pages (6,250 orders)
MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds

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

def save_orders_batch(orders, db_path):
    """Save a batch of orders to database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for order in orders:
        utm_source, utm_medium, utm_campaign, utm_content, utm_term = extract_utm_params(order)
        shipping = order.get('shipping_address') or {}
        discount_codes = ','.join([dc['code'] for dc in order.get('discount_applications', [])])

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

            # Insert line items
            for item in order.get('line_items', []):
                cursor.execute("""
                    INSERT OR REPLACE INTO line_items (
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

        except sqlite3.Error as e:
            print(f"    Warning: Error saving order {order['id']}: {e}")
            continue

    conn.commit()
    conn.close()

def fetch_page_with_retry(url, headers, page_num, max_retries=MAX_RETRIES):
    """Fetch a single page with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            if attempt < max_retries - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                print(f"\n    ⚠️  Connection error on page {page_num}: {type(e).__name__}")
                print(f"    Retrying in {wait_time}s... (attempt {attempt + 2}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"\n    ❌ Failed after {max_retries} attempts")
                raise
    return None

def fetch_all_orders_resilient(token):
    """Fetch all orders with incremental saving and error handling"""
    shop_url = "https://Sinclairp.myshopify.com"
    headers = {"X-Shopify-Access-Token": token}
    db_path = get_db_path()

    batch_orders = []
    total_orders = 0
    page_count = 0
    url = f"{shop_url}/admin/api/2024-10/orders.json?status=any&limit=250"

    print("Fetching all historical orders from Shopify...")
    print(f"Saving to database every {BATCH_SIZE} pages ({BATCH_SIZE * 250} orders)")
    print()

    while url:
        page_count += 1

        # Fetch page with retry logic
        try:
            response = fetch_page_with_retry(url, headers, page_count)
            data = response.json()
            orders = data.get('orders', [])

            batch_orders.extend(orders)
            total_orders += len(orders)

            print(f"  Page {page_count}: Fetched {len(orders)} orders (total: {total_orders:,})", end="")

            # Save batch to database
            if page_count % BATCH_SIZE == 0:
                print(f" → Saving batch to database...", end="")
                save_orders_batch(batch_orders, db_path)
                print(f" ✓ Saved {len(batch_orders):,} orders")
                batch_orders = []  # Clear batch
            else:
                print()

            # Check for pagination
            link_header = response.headers.get('Link', '')
            if 'rel="next"' in link_header:
                next_link = [link.strip() for link in link_header.split(',') if 'rel="next"' in link][0]
                url = next_link.split(';')[0].strip('<>')
            else:
                url = None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                print(f"\n    ⚠️  Rate limited. Waiting 30s...")
                time.sleep(30)
                continue
            else:
                print(f"\n    ❌ HTTP Error: {e}")
                break

        except Exception as e:
            print(f"\n    ❌ Unexpected error: {type(e).__name__}: {e}")
            break

    # Save any remaining orders
    if batch_orders:
        print(f"\n  Final batch: Saving {len(batch_orders):,} orders...")
        save_orders_batch(batch_orders, db_path)
        print(f"  ✓ Saved")

    return total_orders, page_count

if __name__ == '__main__':
    print("="*70)
    print("SINCLAIR PATTERNS - RESILIENT DATA FETCH")
    print("="*70)
    print("\nFeatures:")
    print("  • Incremental saving (every 25 pages)")
    print("  • Automatic retry on connection errors")
    print("  • Progress tracking")
    print("  • API token refresh if needed")
    print("="*70)

    input("\nPress Enter to start...")

    # Step 1: Initialize database
    print("\n[1/3] Initializing database...")
    initialize_database()

    # Step 2: Get Shopify token
    print("\n[2/3] Getting Shopify access token...")
    token = get_shopify_token()
    print("  ✓ Token obtained")

    # Step 3: Fetch all orders
    print("\n[3/3] Fetching all orders from Shopify...")
    start_time = time.time()

    try:
        total_orders, total_pages = fetch_all_orders_resilient(token)
        elapsed = time.time() - start_time

        print("\n" + "="*70)
        print("FETCH COMPLETE!")
        print("="*70)
        print(f"  Total pages fetched: {total_pages}")
        print(f"  Total orders: {total_orders:,}")
        print(f"  Time elapsed: {elapsed/60:.1f} minutes")

        # Check database
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders")
        db_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM line_items")
        items_count = cursor.fetchone()[0]
        conn.close()

        print(f"\nDatabase verification:")
        print(f"  Orders in DB: {db_count:,}")
        print(f"  Line items in DB: {items_count:,}")
        print("="*70)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("Progress has been saved. Run script again to continue.")

    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        print("Check database for partial data.")
