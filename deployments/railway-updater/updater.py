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
from email_service import EmailService


# Configuration
SHOPIFY_SHOP_URL = os.getenv("SHOPIFY_SHOP_URL", "Sinclairp.myshopify.com")
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_EXT_SHOPIFY_DATA")

# How often to run (in seconds)
RUN_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "300"))  # Default: 5 minutes

# Initialize email service
email_service = EmailService()


def log(message):
    """Log with timestamp"""
    print(f"[{datetime.now().isoformat()}] {message}")


def send_email(subject, body, html=False):
    """Send email notification via email service"""
    result = email_service.send_notification(subject, body, html=html)
    if not result:
        log("⚠️  Failed to send email notification")
    return result


def send_report(subject, body, html=False):
    """Send report email to ss@muffinsky.com"""
    result = email_service.send_report(subject, body, html=html)
    if not result:
        log("⚠️  Failed to send report email")
    return result


def get_order_stats(conn, sync_order_details=None):
    """Get aggregate order statistics from database"""
    cursor = conn.cursor()

    try:
        # Get stats for this sync from the orders that were just processed
        if sync_order_details:
            # Calculate directly from the sync data (no DB query needed!)
            this_sync_count = len(sync_order_details)
            this_sync_amount = sum(order['total_price'] for order in sync_order_details)

            # Convert to list of tuples for compatibility with email template
            this_sync_orders = [
                (order['order_number'], order['total_price'])
                for order in sync_order_details
            ]
        else:
            # Fallback if no sync data provided
            this_sync_count = 0
            this_sync_amount = 0
            this_sync_orders = []

        # Get today's stats (PT timezone: UTC-8)
        cursor.execute("""
            SELECT
                COUNT(*) as count,
                COALESCE(SUM(total_price), 0) as total_amount
            FROM orders
            WHERE DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles') =
                  DATE(NOW() AT TIME ZONE 'America/Los_Angeles')
            AND financial_status != 'pending'
        """)
        today = cursor.fetchone()
        today_count = today[0] if today else 0
        today_amount = float(today[1]) if today else 0

        # Get this week's stats (Monday to Sunday in PT timezone)
        cursor.execute("""
            SELECT
                COUNT(*) as count,
                COALESCE(SUM(total_price), 0) as total_amount
            FROM orders
            WHERE (created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles') >=
                  DATE_TRUNC('week', (NOW() AT TIME ZONE 'America/Los_Angeles'))
            AND financial_status != 'pending'
        """)
        week = cursor.fetchone()
        week_count = week[0] if week else 0
        week_amount = float(week[1]) if week else 0

        # Get last 14 days stats
        cursor.execute("""
            SELECT
                COUNT(*) as count,
                COALESCE(SUM(total_price), 0) as total_amount
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '14 days'
            AND financial_status != 'pending'
        """)
        last_14_days = cursor.fetchone()
        last_14_days_count = last_14_days[0] if last_14_days else 0
        last_14_days_amount = float(last_14_days[1]) if last_14_days else 0

        # Get last 30 days stats
        cursor.execute("""
            SELECT
                COUNT(*) as count,
                COALESCE(SUM(total_price), 0) as total_amount
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '30 days'
            AND financial_status != 'pending'
        """)
        last_30_days = cursor.fetchone()
        last_30_days_count = last_30_days[0] if last_30_days else 0
        last_30_days_amount = float(last_30_days[1]) if last_30_days else 0

        # Calculate average per day for last 30 days
        avg_per_day_count = last_30_days_count / 30.0 if last_30_days_count > 0 else 0
        avg_per_day_amount = last_30_days_amount / 30.0 if last_30_days_amount > 0 else 0

        # Get top 10 patterns in last 30 days
        # Revenue = (price * quantity) - line_discount - proportional_order_discount
        # Proportional order discount = (line_item_subtotal / order_subtotal_from_lines) * order_total_discounts
        # We calculate order subtotal from line items because Shopify's subtotal_price is post-discount
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
            WHERE o.created_at >= NOW() - INTERVAL '30 days'
            AND o.financial_status != 'pending'
            AND li.product_title IS NOT NULL
            GROUP BY li.product_title
            ORDER BY order_count DESC
            LIMIT 10
        """)
        top_patterns = cursor.fetchall()

        cursor.close()

        return {
            'this_sync': {'count': this_sync_count, 'amount': this_sync_amount, 'orders': this_sync_orders},
            'today': {'count': today_count, 'amount': today_amount},
            'week': {'count': week_count, 'amount': week_amount},
            'last_14_days': {'count': last_14_days_count, 'amount': last_14_days_amount},
            'last_30_days': {'count': last_30_days_count, 'amount': last_30_days_amount},
            'avg_per_day': {'count': avg_per_day_count, 'amount': avg_per_day_amount},
            'top_patterns': top_patterns
        }
    except Exception as e:
        log(f"⚠️  Error getting order stats: {e}")
        cursor.close()
        return None


def send_sync_complete_notification(orders_count, line_items_count, stats=None):
    """Send sync completion email with aggregate stats to ss@muffinsky.com"""
    # Get Brisbane time (UTC+10)
    from datetime import timezone, timedelta
    bne_tz = timezone(timedelta(hours=10))
    bne_time = datetime.now(bne_tz).strftime('%Y-%m-%d %H:%M:%S')

    # Calculate hours remaining until end of PT day (midnight PT = UTC-8)
    pt_tz = timezone(timedelta(hours=-8))
    pt_now = datetime.now(pt_tz)
    pt_midnight = pt_now.replace(hour=23, minute=59, second=59, microsecond=999999)
    hours_left_pt = (pt_midnight - pt_now).total_seconds() / 3600

    subject = "Shopify Sync Complete"

    # Build HTML email
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
        .section-title {{
            font-size: 14px;
            font-weight: 600;
            color: #667eea;
            margin: 20px 0 10px 0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px; }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
        }}
        td {{ padding: 8px; border-bottom: 1px solid #e5e5e5; }}
        tr:hover {{ background-color: #f9f9ff; }}
        .number {{ text-align: right; }}
        .pattern-item {{
            padding: 10px;
            margin: 5px 0;
            background-color: #f9f9ff;
            border-left: 3px solid #667eea;
            font-size: 13px;
        }}
        .pattern-stats {{ color: #666; font-size: 12px; margin-top: 4px; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 11px; border-top: 1px solid #e5e5e5; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">Shopify Sync Complete</div>
    </div>

    <div class="content">
        <div class="sync-info">
            <strong>This Sync ({bne_time} BNE)</strong><br>
            Orders imported/updated: <strong>{orders_count:,}</strong><br>
            Line items processed: <strong>{line_items_count:,}</strong>"""

    if stats:
        # Build order details list
        order_details = ""
        if stats['this_sync'].get('orders'):
            orders_list = []
            for order_num, amount in stats['this_sync']['orders']:
                orders_list.append(f"{order_num} (${float(amount):,.2f})")
            order_details = f"<br>Orders: {', '.join(orders_list)}"

        body += f"""<br>
            Total amount: <strong>${stats['this_sync']['amount']:,.2f}</strong>{order_details}
        </div>

        <div class="section-title">Sales Summary</div>
        <table>
            <tr>
                <th>Period</th>
                <th class="number">Orders</th>
                <th class="number">Revenue</th>
            </tr>
            <tr>
                <td><strong>Now (this sync)</strong></td>
                <td class="number">{stats['this_sync']['count']:,}</td>
                <td class="number">${stats['this_sync']['amount']:,.2f}</td>
            </tr>
            <tr>
                <td>Today ({hours_left_pt:.1f}h left PT)</td>
                <td class="number">{stats['today']['count']:,}</td>
                <td class="number">${stats['today']['amount']:,.2f}</td>
            </tr>
            <tr>
                <td>This Week</td>
                <td class="number">{stats['week']['count']:,}</td>
                <td class="number">${stats['week']['amount']:,.2f}</td>
            </tr>
            <tr>
                <td>Last 14 Days</td>
                <td class="number">{stats['last_14_days']['count']:,}</td>
                <td class="number">${stats['last_14_days']['amount']:,.2f}</td>
            </tr>
            <tr>
                <td>Last 30 Days</td>
                <td class="number">{stats['last_30_days']['count']:,}</td>
                <td class="number">${stats['last_30_days']['amount']:,.2f}</td>
            </tr>
            <tr style="background-color: #e8f5e9;">
                <td><strong>Avg/Day (30d)</strong></td>
                <td class="number"><strong>{stats['avg_per_day']['count']:.1f}</strong></td>
                <td class="number"><strong>${stats['avg_per_day']['amount']:,.2f}</strong></td>
            </tr>
        </table>

        <div class="section-title">Top 10 Patterns (Last 30 Days)</div>"""

        # Add top patterns if available
        if 'top_patterns' in stats and stats['top_patterns']:
            for idx, pattern in enumerate(stats['top_patterns'], 1):
                product_title = pattern[0]
                order_count = pattern[1]
                total_quantity = pattern[2]
                total_revenue = float(pattern[3])
                body += f"""
        <div class="pattern-item">
            <strong>{idx}. {product_title}</strong><br>
            <div class="pattern-stats">Orders: {order_count:,} | Qty: {total_quantity:,} | Revenue: ${total_revenue:,.2f}</div>
        </div>"""
        else:
            body += """
        <p>No pattern data available</p>"""

    body += f"""
    </div>

    <div class="footer">
        Next sync in {RUN_INTERVAL/60:.0f} minutes
    </div>
</body>
</html>"""

    send_report(subject, body, html=True)


def send_sync_error_notification(error_message, orders_processed=0):
    """Send email notification when sync fails to ss@muffinsky.com"""
    subject = "Shopify Sync Failed"

    body = f"""Shopify sync encountered an error!

Error: {error_message}

Orders processed before error: {orders_processed:,}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The sync will retry in {RUN_INTERVAL/60:.0f} minutes.
"""

    send_report(subject, body)


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

    # First try to get from sync_history
    cursor.execute("""
        SELECT last_order_date FROM sync_history
        WHERE status = 'completed'
        ORDER BY sync_completed_at DESC
        LIMIT 1
    """)

    result = cursor.fetchone()

    if result and result[0]:
        cursor.close()
        return result[0]

    # If no sync history, check the latest order in database
    cursor.execute("""
        SELECT MAX(updated_at) FROM orders
    """)

    result = cursor.fetchone()
    cursor.close()

    if result and result[0]:
        log(f"No sync history found, using latest order date: {result[0]}")
        return result[0]

    # Default to 24 hours ago if database is empty
    log("No orders in database, starting from 24 hours ago")
    return (datetime.now() - timedelta(hours=24)).isoformat()


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
        return 0, 0, []

    cursor = conn.cursor()
    orders_updated = 0
    line_items_updated = 0
    updated_order_ids = []
    sync_order_details = []  # Store (order_number, total_price) for this sync

    for idx, order in enumerate(orders, 1):
        updated_order_ids.append(order['id'])

        # Collect order details for sync summary
        sync_order_details.append({
            'order_number': order.get('order_number'),
            'total_price': float(order.get('total_price', 0))
        })
        utm_source, utm_medium, utm_campaign, utm_content, utm_term = extract_utm_params(order)
        shipping = order.get('shipping_address') or {}

        # Handle discount codes safely - discount_applications may have different structures
        try:
            discount_codes = ','.join([dc.get('code', '') for dc in order.get('discount_applications', []) if dc.get('code')])
        except:
            discount_codes = ''

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

    conn.commit()
    cursor.close()

    return orders_updated, line_items_updated, sync_order_details


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
        orders_updated, line_items_updated, sync_order_details = update_orders(conn, orders)

        # Get aggregate stats before closing connection
        log("Gathering statistics...")
        stats = get_order_stats(conn, sync_order_details)

        # Release lock and record completion
        # Add 1 second to last_order_date to avoid fetching the same order again
        if orders:
            last_updated = max([o['updated_at'] for o in orders])
            # Parse the ISO timestamp and add 1 second
            from dateutil import parser
            last_dt = parser.parse(last_updated)
            last_order_date = (last_dt + timedelta(seconds=1)).isoformat()
        else:
            last_order_date = last_sync

        release_lock(conn, lock_id, len(orders), last_order_date, 'completed')

        conn.close()

        log("="*70)
        log("SYNC COMPLETE!")
        log(f"  Orders updated: {orders_updated}")
        log(f"  Line items updated: {line_items_updated}")
        if stats:
            log("")
            log("SALES SUMMARY:")
            log(f"  Now (this sync):  {stats['this_sync']['count']:>6,} orders | ${stats['this_sync']['amount']:>10,.2f}")
            log(f"  Today:            {stats['today']['count']:>6,} orders | ${stats['today']['amount']:>10,.2f}")
            log(f"  This Week:        {stats['week']['count']:>6,} orders | ${stats['week']['amount']:>10,.2f}")
            log(f"  Last 14 Days:     {stats['last_14_days']['count']:>6,} orders | ${stats['last_14_days']['amount']:>10,.2f}")
            log(f"  Last 30 Days:     {stats['last_30_days']['count']:>6,} orders | ${stats['last_30_days']['amount']:>10,.2f}")
            log(f"  Avg/Day (30d):    {stats['avg_per_day']['count']:>6,.1f} orders | ${stats['avg_per_day']['amount']:>10,.2f}")
        log("="*70)

        # Send completion notification with stats (always send, even if 0 orders)
        send_sync_complete_notification(orders_updated, line_items_updated, stats)

        return True

    except Exception as e:
        log(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

        # Send error notification
        error_message = f"{type(e).__name__}: {str(e)}"
        send_sync_error_notification(error_message, orders_processed=0)

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
