#!/usr/bin/env python3
"""
Shopify Orders Updater - Railway Cron Service
Runs hourly to sync Shopify orders to PostgreSQL
"""

import os
import sys
import time
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# Configuration
SHOPIFY_SHOP_URL = os.getenv("SHOPIFY_SHOP_URL", "Sinclairp.myshopify.com")
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_EXT_SHOPIFY_DATA")

# Email configuration
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.zoho.com.au")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_HOST_USER", "hello@sinclairpatterns.com")
EMAIL_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_FROM = os.getenv("DEFAULT_FROM_EMAIL", "hello@sinclairpatterns.com")
EMAIL_TO = os.getenv("NOTIFICATION_EMAIL", "hello@sinclairpatterns.com")

# How often to run (in seconds)
RUN_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "300"))  # Default: 5 minutes

# Email notification interval
EMAIL_NOTIFICATION_INTERVAL = int(os.getenv("EMAIL_NOTIFICATION_INTERVAL", "10000"))  # Every 10k records


def log(message):
    """Log with timestamp"""
    print(f"[{datetime.now().isoformat()}] {message}")


def send_email(subject, body, html=False):
    """Send email notification"""
    if not EMAIL_PASSWORD:
        log("⚠️  Email password not configured, skipping email notification")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO

        if html:
            part = MIMEText(body, 'html')
        else:
            part = MIMEText(body, 'plain')

        msg.attach(part)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        log(f"✉️  Email sent: {subject}")
        return True

    except Exception as e:
        log(f"⚠️  Failed to send email: {e}")
        return False


def send_progress_notification(orders_count, line_items_count, is_first=False, is_final=False):
    """Send progress update email"""
    if is_first:
        subject = "🚀 Shopify Sync Started - First Record Imported"
        body = f"""
Shopify sync has started!

First order imported successfully.
Expected total: Will update every {EMAIL_NOTIFICATION_INTERVAL:,} records.

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    elif is_final:
        subject = "✅ Shopify Sync Complete"
        body = f"""
Shopify sync completed successfully!

Orders updated: {orders_count:,}
Line items updated: {line_items_count:,}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Next sync in {RUN_INTERVAL/3600:.1f} hours.
"""
    else:
        subject = f"📊 Shopify Sync Progress: {orders_count:,} orders"
        body = f"""
Sync in progress...

Orders processed so far: {orders_count:,}
Line items processed: {line_items_count:,}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    send_email(subject, body)


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


def get_last_sync_date(conn):
    """Get the date of the last successful sync"""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT last_order_date FROM sync_history
        WHERE status = 'completed'
        ORDER BY sync_completed_at DESC
        LIMIT 1
    """)

    result = cursor.fetchone()
    cursor.close()

    if result and result[0]:
        return result[0]

    # Default to 1 hour ago if no sync history
    return (datetime.now() - timedelta(hours=1)).isoformat()


def fetch_recent_orders(token, since_date):
    """Fetch orders created or updated after since_date"""
    if not SHOPIFY_SHOP_URL.startswith("http"):
        shop_url = f"https://{SHOPIFY_SHOP_URL}"
    else:
        shop_url = SHOPIFY_SHOP_URL

    headers = {"X-Shopify-Access-Token": token}

    all_orders = []
    url = f"{shop_url}/admin/api/2024-10/orders.json?status=any&limit=250&updated_at_min={since_date}"

    log(f"Fetching orders updated since {since_date}...")

    page_count = 0
    while url:
        page_count += 1
        log(f"  Fetching page {page_count}...")

        response = requests.get(url, headers=headers)
        data = response.json()
        orders = data.get('orders', [])

        all_orders.extend(orders)

        # Check for pagination
        link_header = response.headers.get('Link', '')
        if 'rel="next"' in link_header:
            next_link = [link.strip() for link in link_header.split(',') if 'rel="next"' in link][0]
            url = next_link.split(';')[0].strip('<>')
        else:
            url = None

    log(f"✓ Fetched {len(all_orders)} orders")
    return all_orders


def update_orders(conn, orders):
    """Update orders in PostgreSQL with progress notifications"""
    if not orders:
        log("No orders to update")
        return 0, 0

    cursor = conn.cursor()
    orders_updated = 0
    line_items_updated = 0
    first_email_sent = False
    last_notification_count = 0

    for idx, order in enumerate(orders, 1):
        utm_source, utm_medium, utm_campaign, utm_content, utm_term = extract_utm_params(order)
        shipping = order.get('shipping_address') or {}
        discount_codes = ','.join([dc['code'] for dc in order.get('discount_applications', [])])

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
        orders_updated += 1

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
            line_items_updated += len(line_items_data)

        # Send first record notification
        if not first_email_sent and orders_updated == 1:
            send_progress_notification(orders_updated, line_items_updated, is_first=True)
            first_email_sent = True

        # Send progress notifications every EMAIL_NOTIFICATION_INTERVAL records
        elif orders_updated - last_notification_count >= EMAIL_NOTIFICATION_INTERVAL:
            send_progress_notification(orders_updated, line_items_updated)
            last_notification_count = orders_updated

    conn.commit()
    cursor.close()

    # Send final notification
    if orders_updated > 0:
        send_progress_notification(orders_updated, line_items_updated, is_final=True)

    return orders_updated, line_items_updated


def check_and_acquire_lock(conn):
    """Check if another sync is running and acquire lock"""
    cursor = conn.cursor()

    # Check for running syncs
    cursor.execute("""
        SELECT id, sync_started_at
        FROM sync_history
        WHERE status = 'running'
        ORDER BY sync_started_at DESC
        LIMIT 1
    """)

    running_sync = cursor.fetchone()

    if running_sync:
        sync_id, started_at = running_sync
        # If running for more than 2 hours, consider it stale
        if (datetime.now() - started_at.replace(tzinfo=None)).total_seconds() > 7200:
            log(f"Found stale lock from {started_at}, clearing it...")
            cursor.execute("UPDATE sync_history SET status = 'timeout' WHERE id = %s", (sync_id,))
            conn.commit()
        else:
            cursor.close()
            return False, None

    # Acquire lock by creating a 'running' entry
    cursor.execute("""
        INSERT INTO sync_history (
            sync_type, sync_started_at, status
        ) VALUES (%s, %s, %s)
        RETURNING id
    """, ('hourly_update', datetime.now(), 'running'))

    lock_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()

    return True, lock_id


def release_lock(conn, lock_id, records_fetched, last_order_date, status, error=None):
    """Release lock and update sync record"""
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE sync_history SET
            sync_completed_at = %s,
            records_fetched = %s,
            last_order_date = %s,
            status = %s,
            error_message = %s
        WHERE id = %s
    """, (
        datetime.now(),
        records_fetched,
        last_order_date,
        status,
        error,
        lock_id
    ))

    conn.commit()
    cursor.close()


def run_update():
    """Run a single update cycle with lock protection"""
    log("="*70)
    log("STARTING SHOPIFY SYNC")
    log("="*70)

    lock_id = None
    conn = None

    try:
        # Connect to database
        log("Connecting to PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        log("✓ Connected")

        # Check for running syncs and acquire lock
        log("Checking for running syncs...")
        acquired, lock_id = check_and_acquire_lock(conn)

        if not acquired:
            log("⚠️  Another sync is already running. Skipping this run.")
            conn.close()
            return False

        log("✓ Lock acquired")

        # Get last sync date
        last_sync = get_last_sync_date(conn)
        log(f"Last sync: {last_sync}")

        # Get Shopify token
        log("Getting Shopify access token...")
        token = get_shopify_token()
        log("✓ Token obtained")

        # Fetch orders
        orders = fetch_recent_orders(token, last_sync)

        # Update database
        log("Updating database...")
        orders_updated, line_items_updated = update_orders(conn, orders)

        # Release lock and record completion
        last_order_date = max([o['updated_at'] for o in orders]) if orders else last_sync
        release_lock(conn, lock_id, len(orders), last_order_date, 'completed')

        conn.close()

        log("="*70)
        log("SYNC COMPLETE!")
        log(f"  Orders updated: {orders_updated}")
        log(f"  Line items updated: {line_items_updated}")
        log("="*70)

        return True

    except Exception as e:
        log(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

        try:
            if conn and lock_id:
                release_lock(conn, lock_id, 0, None, 'failed', str(e))
            if conn:
                conn.close()
        except:
            pass

        return False


def main():
    """Main loop - run updates on schedule"""
    log("Shopify Orders Updater - Railway Cron Service")
    log(f"Update interval: {RUN_INTERVAL} seconds ({RUN_INTERVAL/3600} hours)")

    if not DATABASE_URL:
        log("❌ DATABASE_URL not set")
        sys.exit(1)

    if not SHOPIFY_API_KEY or not SHOPIFY_API_SECRET:
        log("❌ Shopify credentials not set")
        sys.exit(1)

    # Run immediately on start
    run_update()

    # Then run on schedule
    while True:
        log(f"\nSleeping for {RUN_INTERVAL} seconds...")
        time.sleep(RUN_INTERVAL)
        run_update()


if __name__ == '__main__':
    main()
