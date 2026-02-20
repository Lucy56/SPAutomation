#!/usr/bin/env python3
"""
Resumable Order Fetch for PostgreSQL: Fetches ALL orders with smart resume capability
- Checks database for existing orders
- Resumes from last fetched order
- Saves every page (no data loss)
- Handles errors gracefully
"""

import os
import psycopg2
from psycopg2.extras import execute_values
import requests
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

MAX_RETRIES = 5
RETRY_DELAY = 10

# Configuration
SHOPIFY_SHOP_URL = os.getenv("SHOPIFY_SHOP_URL", "Sinclairp.myshopify.com")
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_EXT_SHOPIFY_DATA")


def get_shopify_token():
    """Get Shopify admin API access token using OAuth"""
    if not SHOPIFY_SHOP_URL.startswith("http"):
        shop_url = f"https://{SHOPIFY_SHOP_URL}"
    else:
        shop_url = SHOPIFY_SHOP_URL

    response = requests.post(
        f"{shop_url}/admin/oauth/access_token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": SHOPIFY_API_KEY,
            "client_secret": SHOPIFY_API_SECRET
        }
    )

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Failed to get access token: {response.status_code} - {response.text}")


def get_db_progress():
    """Check how many orders are already in database"""
    conn = psycopg2.connect(DATABASE_URL)
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


def save_orders_batch(orders, last_id=None):
    """Save a batch of orders to database immediately"""
    if not orders:
        return 0, 0

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    orders_saved = 0
    line_items_saved = 0

    try:
        for order in orders:
            # Skip if already in DB
            if last_id and order['id'] <= last_id:
                continue

            utm_source, utm_medium, utm_campaign, utm_content, utm_term = extract_utm_params(order)
            shipping = order.get('shipping_address') or {}
            discount_codes = ','.join([dc['code'] for dc in order.get('discount_applications', []) if dc.get('code')])

            # Get gateway (payment method)
            gateway = None
            if order.get('payment_gateway_names'):
                gateway = order['payment_gateway_names'][0] if order['payment_gateway_names'] else None

            # Get total shipping
            total_shipping = 0
            for shipping_line in order.get('shipping_lines', []):
                total_shipping += float(shipping_line.get('price', 0))

            execute_values(
                cursor,
                """
                INSERT INTO orders (
                    order_id, order_number, order_name, created_at, updated_at, processed_at,
                    customer_id, email, country, country_code, province, city,
                    total_price, subtotal_price, total_tax, total_discounts, currency,
                    referring_site, landing_site, source_name,
                    utm_source, utm_medium, utm_campaign, utm_content, utm_term,
                    financial_status, fulfillment_status, cancelled_at, cancel_reason,
                    tags, note, discount_codes, gateway, total_shipping, checkout_id
                ) VALUES %s
                ON CONFLICT (order_id) DO UPDATE SET
                    updated_at = EXCLUDED.updated_at,
                    financial_status = EXCLUDED.financial_status,
                    fulfillment_status = EXCLUDED.fulfillment_status,
                    tags = EXCLUDED.tags,
                    synced_at = CURRENT_TIMESTAMP
                """,
                [(
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
                    order.get('tags'), order.get('note'), discount_codes,
                    gateway, total_shipping, order.get('checkout_id')
                )]
            )
            orders_saved += 1

            # Delete old line items for this order
            cursor.execute("DELETE FROM line_items WHERE order_id = %s", (order['id'],))

            # Insert line items
            line_items_data = []
            for item in order.get('line_items', []):
                line_items_data.append((
                    item['id'], order['id'], item.get('product_id'), item.get('variant_id'),
                    item.get('title'), item.get('variant_title'), item.get('sku'), item.get('vendor'),
                    item.get('quantity'), float(item.get('price', 0)),
                    float(item.get('total_discount', 0)), item.get('product_type')
                ))

            if line_items_data:
                execute_values(
                    cursor,
                    """
                    INSERT INTO line_items (
                        line_item_id, order_id, product_id, variant_id,
                        product_title, variant_title, sku, vendor,
                        quantity, price, total_discount, product_type
                    ) VALUES %s
                    """,
                    line_items_data
                )
                line_items_saved += len(line_items_data)

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"    ⚠️  Error saving batch: {e}")
        raise
    finally:
        conn.close()

    return orders_saved, line_items_saved


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
    if not SHOPIFY_SHOP_URL.startswith("http"):
        shop_url = f"https://{SHOPIFY_SHOP_URL}"
    else:
        shop_url = SHOPIFY_SHOP_URL

    headers = {"X-Shopify-Access-Token": token}

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
    total_orders_saved = 0
    total_line_items_saved = 0

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

            # Save batch immediately
            orders_saved, line_items_saved = save_orders_batch(orders, last_id)

            total_orders_saved += orders_saved
            total_line_items_saved += line_items_saved

            print(f"  Page {page_count}: Saved {orders_saved} orders, {line_items_saved} line items | "
                  f"Total: {existing_count + total_orders_saved:,}")

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
            print(f"    Saved: {total_orders_saved:,} new orders")
            print(f"    Total in DB: {existing_count + total_orders_saved:,}")
            print(f"    Run script again to resume from here.")
            raise

        except Exception as e:
            print(f"\n    ❌ Unexpected error: {type(e).__name__}: {e}")
            print(f"    Progress saved. Restart script to resume.")
            import traceback
            traceback.print_exc()
            break

    return total_orders_saved, total_line_items_saved, page_count


if __name__ == '__main__':
    print("="*70)
    print("SHOPIFY TO POSTGRESQL - RESUMABLE ORDER FETCH")
    print("="*70)
    print("\nFeatures:")
    print("  • ✓ Checks database for existing orders")
    print("  • ✓ Resumes from last saved order")
    print("  • ✓ Saves EVERY page (no data loss)")
    print("  • ✓ Automatic retry on errors")
    print("  • ✓ Can be stopped and restarted anytime")
    print("="*70)

    if not DATABASE_URL:
        print("\n❌ DATABASE_URL not set")
        print("   Set DATABASE_URL or DATABASE_EXT_SHOPIFY_DATA environment variable")
        exit(1)

    if not SHOPIFY_API_KEY or not SHOPIFY_API_SECRET:
        print("\n❌ Shopify credentials not set")
        exit(1)

    # Step 1: Get Shopify token
    print("\n[1/2] Getting Shopify access token...")
    token = get_shopify_token()
    print("  ✓ Token obtained")

    # Step 2: Fetch orders
    print("\n[2/2] Fetching orders...")
    start_time = time.time()

    try:
        new_orders, new_line_items, total_pages = fetch_all_orders_resumable(token)
        elapsed = time.time() - start_time

        print("\n" + "="*70)
        print("FETCH COMPLETE!")
        print("="*70)
        print(f"  Pages fetched: {total_pages}")
        print(f"  New orders saved: {new_orders:,}")
        print(f"  New line items saved: {new_line_items:,}")
        print(f"  Time elapsed: {elapsed/60:.1f} minutes")

        # Check database
        conn = psycopg2.connect(DATABASE_URL)
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
