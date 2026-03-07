#!/usr/bin/env python3
"""
Build Customer Profiles
Aggregates order data to create comprehensive customer profiles
Tracks: LTV, conversion (free->paid), acquisition source
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_batch

load_dotenv()


def get_db_connection():
    """Get PostgreSQL connection"""
    database_url = os.getenv("DATABASE_EXT_SHOPIFY_DATA")
    if not database_url:
        print("❌ DATABASE_EXT_SHOPIFY_DATA not found")
        sys.exit(1)
    return psycopg2.connect(database_url)


def determine_acquisition_source(first_order):
    """
    Determine customer acquisition source from first order
    Priority: Email > Social > Paid Ads > Organic > Direct
    """
    utm_source = first_order.get('utm_source', '')
    utm_medium = first_order.get('utm_medium', '')
    utm_campaign = first_order.get('utm_campaign', '')
    referring = first_order.get('referring_site', '') or ''

    # EMAIL: utm_source='S' + utm_medium='email'
    if utm_source == 'S' and utm_medium == 'email':
        return 'email', 'newsletter', utm_campaign

    # SOCIAL: UTM or referring site
    social_platforms = ['facebook', 'instagram', 'pinterest', 'tiktok']
    if utm_source and utm_source.lower() in social_platforms:
        return 'social', utm_source.lower(), utm_campaign

    for platform in social_platforms:
        if platform in referring.lower():
            return 'social', platform, None

    # PAID ADS
    if utm_medium and utm_medium.lower() in ['cpc', 'paid', 'ppc']:
        return 'paid_ads', utm_source or 'unknown', utm_campaign

    # ORGANIC SEARCH
    if 'google.com' in referring.lower():
        return 'organic', 'google', None

    # DIRECT
    if not referring and not utm_source:
        return 'direct', 'direct', None

    return 'unknown', 'unknown', utm_campaign


def is_free_order(order):
    """Check if order was free (total price ≤ $0.01)"""
    return float(order.get('total_price', 0)) <= 0.01


def get_free_pattern_info(order_id, conn):
    """Get free pattern details from line items"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product_id, product_title
        FROM line_items
        WHERE order_id = %s
        LIMIT 1
    """, (order_id,))

    result = cursor.fetchone()
    cursor.close()

    if result:
        product_id, product_title = result

        # Extract pattern name (Harper, Valley, Sunset, Mojo)
        pattern_name = 'Other'
        for name in ['Harper', 'Valley', 'Sunset', 'Mojo']:
            if name.lower() in product_title.lower():
                pattern_name = name
                break

        return product_id, pattern_name

    return None, 'Unknown'


def build_customer_profile(customer_id, conn):
    """Build complete profile for a single customer"""
    cursor = conn.cursor()

    # Get all paid orders for this customer, ordered chronologically
    cursor.execute("""
        SELECT
            order_id,
            created_at,
            total_price,
            financial_status,
            utm_source,
            utm_medium,
            utm_campaign,
            referring_site,
            discount_codes
        FROM orders
        WHERE customer_id = %s
          AND financial_status = 'paid'
        ORDER BY created_at ASC
    """, (customer_id,))

    orders = cursor.fetchall()
    cursor.close()

    if not orders:
        return None  # No paid orders for this customer

    # Convert to dict for easier access
    orders_list = []
    for order in orders:
        orders_list.append({
            'order_id': order[0],
            'created_at': order[1],
            'total_price': order[2],
            'financial_status': order[3],
            'utm_source': order[4],
            'utm_medium': order[5],
            'utm_campaign': order[6],
            'referring_site': order[7],
            'discount_codes': order[8]
        })

    # FIRST ORDER
    first_order = orders_list[0]
    first_order_date = first_order['created_at']
    first_order_id = first_order['order_id']
    first_order_amount = float(first_order['total_price'])
    first_is_free = is_free_order(first_order)

    # FREE PATTERN INFO (if first order was free)
    first_free_pattern_id = None
    first_free_pattern_name = None
    first_free_discount_code = None

    if first_is_free:
        first_free_pattern_id, first_free_pattern_name = get_free_pattern_info(first_order_id, conn)
        first_free_discount_code = first_order['discount_codes']

    # ACQUISITION SOURCE
    acq_source, acq_channel, acq_campaign = determine_acquisition_source(first_order)

    # CONVERSION TRACKING
    has_paid_purchase = False
    first_paid_order_date = None
    first_paid_order_id = None
    days_to_first_paid = None

    # Find first PAID order (price > $0.01)
    for order in orders_list:
        if float(order['total_price']) > 0.01:
            has_paid_purchase = True
            first_paid_order_date = order['created_at']
            first_paid_order_id = order['order_id']

            # Calculate days to conversion (if first was free)
            if first_is_free:
                delta = first_paid_order_date - first_order_date
                days_to_first_paid = delta.days

            break

    # LTV METRICS (all paid orders)
    total_orders = len(orders_list)
    total_spent = sum(float(o['total_price']) for o in orders_list)
    avg_order_value = total_spent / total_orders if total_orders > 0 else 0
    last_order_date = orders_list[-1]['created_at']

    # CUSTOMER TYPE
    if first_is_free and has_paid_purchase:
        customer_type = 'converted_customer'
    elif first_is_free and not has_paid_purchase:
        customer_type = 'free_only'
    else:
        customer_type = 'paid_customer'

    # Get customer email
    cursor = conn.cursor()
    cursor.execute("""
        SELECT email, created_at
        FROM orders
        WHERE customer_id = %s
        LIMIT 1
    """, (customer_id,))

    result = cursor.fetchone()
    cursor.close()

    if not result:
        return None

    email = result[0]
    customer_created_at = result[1]

    return {
        'customer_id': customer_id,
        'email': email,
        'created_at': customer_created_at,
        'first_order_date': first_order_date,
        'first_order_id': first_order_id,
        'first_order_type': 'free' if first_is_free else 'paid',
        'first_order_amount': first_order_amount,
        'first_free_pattern_id': first_free_pattern_id,
        'first_free_pattern_name': first_free_pattern_name,
        'first_free_discount_code': first_free_discount_code,
        'acquisition_source': acq_source,
        'acquisition_channel': acq_channel,
        'acquisition_campaign': acq_campaign,
        'has_paid_purchase': has_paid_purchase,
        'first_paid_order_date': first_paid_order_date,
        'first_paid_order_id': first_paid_order_id,
        'days_to_first_paid': days_to_first_paid,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'avg_order_value': avg_order_value,
        'last_order_date': last_order_date,
        'customer_type': customer_type
    }


def insert_customer_profiles(profiles, conn):
    """Batch insert customer profiles"""
    cursor = conn.cursor()

    sql = """
        INSERT INTO customers (
            customer_id, email, created_at,
            first_order_date, first_order_id, first_order_type, first_order_amount,
            first_free_pattern_id, first_free_pattern_name, first_free_discount_code,
            acquisition_source, acquisition_channel, acquisition_campaign,
            has_paid_purchase, first_paid_order_date, first_paid_order_id, days_to_first_paid,
            total_orders, total_spent, avg_order_value, last_order_date,
            customer_type, last_aggregated_at
        ) VALUES (
            %(customer_id)s, %(email)s, %(created_at)s,
            %(first_order_date)s, %(first_order_id)s, %(first_order_type)s, %(first_order_amount)s,
            %(first_free_pattern_id)s, %(first_free_pattern_name)s, %(first_free_discount_code)s,
            %(acquisition_source)s, %(acquisition_channel)s, %(acquisition_campaign)s,
            %(has_paid_purchase)s, %(first_paid_order_date)s, %(first_paid_order_id)s, %(days_to_first_paid)s,
            %(total_orders)s, %(total_spent)s, %(avg_order_value)s, %(last_order_date)s,
            %(customer_type)s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (customer_id) DO UPDATE SET
            total_orders = EXCLUDED.total_orders,
            total_spent = EXCLUDED.total_spent,
            avg_order_value = EXCLUDED.avg_order_value,
            last_order_date = EXCLUDED.last_order_date,
            has_paid_purchase = EXCLUDED.has_paid_purchase,
            first_paid_order_date = EXCLUDED.first_paid_order_date,
            first_paid_order_id = EXCLUDED.first_paid_order_id,
            days_to_first_paid = EXCLUDED.days_to_first_paid,
            customer_type = EXCLUDED.customer_type,
            last_aggregated_at = CURRENT_TIMESTAMP
    """

    execute_batch(cursor, sql, profiles, page_size=1000)
    conn.commit()
    cursor.close()


def build_all_customer_profiles():
    """Build profiles for ALL customers from historical data"""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("=" * 70)
    print("BUILDING CUSTOMER PROFILES FROM HISTORICAL DATA")
    print("=" * 70)

    # Get all unique customer IDs
    print("\n[1/3] Finding all customers...")
    cursor.execute("""
        SELECT DISTINCT customer_id
        FROM orders
        WHERE customer_id IS NOT NULL
          AND financial_status = 'paid'
        ORDER BY customer_id
    """)

    customer_ids = [row[0] for row in cursor.fetchall()]
    total_customers = len(customer_ids)

    print(f"  Found {total_customers:,} unique customers")

    # Build profiles
    print("\n[2/3] Building customer profiles...")
    profiles = []
    processed = 0
    skipped = 0

    for i, customer_id in enumerate(customer_ids, 1):
        if i % 1000 == 0:
            print(f"  Progress: {i:,}/{total_customers:,} ({i/total_customers*100:.1f}%)")

        profile = build_customer_profile(customer_id, conn)
        if profile:
            profiles.append(profile)
            processed += 1
        else:
            skipped += 1

        # Batch insert every 5000 profiles
        if len(profiles) >= 5000:
            insert_customer_profiles(profiles, conn)
            profiles = []

    # Insert remaining profiles
    if profiles:
        insert_customer_profiles(profiles, conn)

    print(f"\n  ✓ Processed: {processed:,} customers")
    print(f"  ✓ Skipped: {skipped:,} customers (no orders)")

    # Show summary stats
    print("\n[3/3] Summary Statistics...")
    cursor.execute("""
        SELECT
            customer_type,
            COUNT(*) as count,
            SUM(total_spent) as total_revenue,
            AVG(total_spent) as avg_ltv
        FROM customers
        GROUP BY customer_type
        ORDER BY count DESC
    """)

    print("\n  Customer Segments:")
    print("  " + "=" * 66)
    print(f"  {'Type':<20} {'Count':>10} {'Revenue':>15} {'Avg LTV':>15}")
    print("  " + "=" * 66)

    for row in cursor.fetchall():
        cust_type, count, revenue, avg_ltv = row
        print(f"  {cust_type:<20} {count:>10,} ${revenue:>14,.2f} ${avg_ltv:>14,.2f}")

    # Conversion stats
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE first_order_type = 'free') as total_free,
            COUNT(*) FILTER (WHERE customer_type = 'converted_customer') as converted,
            AVG(days_to_first_paid) FILTER (WHERE customer_type = 'converted_customer') as avg_days
        FROM customers
    """)

    row = cursor.fetchone()
    total_free, converted, avg_days = row

    if total_free > 0:
        conversion_rate = (converted / total_free) * 100
        print(f"\n  Free Pattern Conversion:")
        print(f"    Total free downloads: {total_free:,}")
        print(f"    Converted to paid: {converted:,}")
        print(f"    Conversion rate: {conversion_rate:.1f}%")
        if avg_days:
            print(f"    Avg days to convert: {avg_days:.0f} days")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("✅ Customer profiles built successfully!")
    print("=" * 70)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build customer profiles')
    parser.add_argument('--full-history', action='store_true', help='Build all customer profiles from scratch')
    parser.add_argument('--customer-id', type=int, help='Build profile for specific customer')

    args = parser.parse_args()

    if args.full_history:
        build_all_customer_profiles()
    elif args.customer_id:
        conn = get_db_connection()
        profile = build_customer_profile(args.customer_id, conn)
        if profile:
            insert_customer_profiles([profile], conn)
            print(f"✅ Profile updated for customer {args.customer_id}")
        else:
            print(f"❌ No data found for customer {args.customer_id}")
        conn.close()
    else:
        print("Usage:")
        print("  --full-history     Build all customer profiles")
        print("  --customer-id ID   Build profile for specific customer")
