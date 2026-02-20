#!/usr/bin/env python3
"""
Resumable Order Fetch: Fetches ALL orders with smart resume capability
- Checks database for existing orders
- Resumes from last fetched order
- Saves every page (no data loss)
- Handles errors gracefully
"""

import sqlite3
import requests
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from db_schema import get_db_path, initialize_database

MAX_RETRIES = 5
RETRY_DELAY = 10

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

def get_db_progress():
    """Check how many orders are already in database"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get count and latest order
    cursor.execute("SELECT COUNT(*), MAX(created_at), MAX(order_id) FROM orders")
    count, last_date, last_id = cursor.fetchone()

    conn.close()
    return count or 0, last_date, last_id

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

def save_order(order, db_path):
    """Save a single order to database immediately"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    utm_source, utm_medium, utm_campaign, utm_content, utm_term = extract_utm_params(order)
    shipping = order.get('shipping_address') or {}
    # Handle discount codes safely - some may not have 'code' field
    try:
        discount_codes = ','.join([dc.get('code', '') for dc in order.get('discount_applications', []) if dc.get('code')])
    except:
        discount_codes = ''

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

        conn.commit()
        conn.close()
        return True

    except sqlite3.Error as e:
        conn.close()
        print(f"    ⚠️  Error saving order {order.get('id')}: {e}")
        return False

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
                print(f"\n    ⚠️  Connection error: {type(e).__name__}")
                print(f"    Retrying in {wait_time}s... (attempt {attempt + 2}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"\n    ❌ Failed after {max_retries} attempts")
                raise
    return None

def fetch_all_orders_resumable(token):
    """Fetch all orders with resume capability"""
    shop_url = "https://Sinclairp.myshopify.com"
    headers = {"X-Shopify-Access-Token": token}
    db_path = get_db_path()

    # Check progress
    existing_count, last_date, last_id = get_db_progress()

    if existing_count > 0:
        print(f"\n📊 Found {existing_count:,} orders already in database")
        print(f"   Last order: {last_date} (ID: {last_id})")
        print(f"   Resuming from this point...\n")
        url = f"{shop_url}/admin/api/2024-10/orders.json?status=any&limit=250&order=created_at+asc&created_at_min={last_date}"
    else:
        print(f"\n📊 Starting fresh fetch (database is empty)\n")
        url = f"{shop_url}/admin/api/2024-10/orders.json?status=any&limit=250&order=created_at+asc"

    page_count = 0
    orders_saved = 0
    orders_skipped = 0

    print("Fetching orders from Shopify...")
    print("Saving each page immediately (no data loss on interruption)\n")

    while url:
        page_count += 1

        try:
            response = fetch_page_with_retry(url, headers, page_count)
            data = response.json()
            orders = data.get('orders', [])

            if not orders:
                print("  No more orders to fetch")
                break

            # Save each order immediately
            page_saved = 0
            page_skipped = 0

            for order in orders:
                # Skip if already in DB
                if existing_count > 0 and order['id'] <= last_id:
                    page_skipped += 1
                    continue

                if save_order(order, db_path):
                    page_saved += 1
                else:
                    page_skipped += 1

            orders_saved += page_saved
            orders_skipped += page_skipped

            print(f"  Page {page_count}: Saved {page_saved} orders "
                  f"(skipped {page_skipped}) | Total: {existing_count + orders_saved:,}")

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
                print(f"    Progress saved. Restart script to resume.")
                break

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted by user")
            print(f"    Saved: {orders_saved:,} new orders")
            print(f"    Total in DB: {existing_count + orders_saved:,}")
            print(f"    Run script again to resume from here.")
            raise

        except Exception as e:
            print(f"\n    ❌ Unexpected error: {type(e).__name__}: {e}")
            print(f"    Progress saved. Restart script to resume.")
            break

    return orders_saved, page_count

if __name__ == '__main__':
    print("="*70)
    print("SINCLAIR PATTERNS - RESUMABLE ORDER FETCH")
    print("="*70)
    print("\nFeatures:")
    print("  • ✓ Checks database for existing orders")
    print("  • ✓ Resumes from last saved order")
    print("  • ✓ Saves EVERY page (no data loss)")
    print("  • ✓ Automatic retry on errors")
    print("  • ✓ Can be stopped and restarted anytime")
    print("="*70)

    # Step 1: Initialize database
    print("\n[1/3] Initializing database...")
    initialize_database()

    # Step 2: Get Shopify token
    print("\n[2/3] Getting Shopify access token...")
    token = get_shopify_token()
    print("  ✓ Token obtained")

    # Step 3: Fetch orders
    print("\n[3/3] Fetching orders...")
    start_time = time.time()

    try:
        new_orders, total_pages = fetch_all_orders_resumable(token)
        elapsed = time.time() - start_time

        print("\n" + "="*70)
        print("FETCH COMPLETE!")
        print("="*70)
        print(f"  Pages fetched: {total_pages}")
        print(f"  New orders saved: {new_orders:,}")
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

        print(f"\nDatabase stats:")
        print(f"  Total orders: {db_count:,}")
        print(f"  Total line items: {items_count:,}")
        print("="*70)

    except KeyboardInterrupt:
        pass  # Already handled above

    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        print("Check database for saved data. Restart to resume.")
