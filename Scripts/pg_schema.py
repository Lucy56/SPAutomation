#!/usr/bin/env python3
"""
PostgreSQL Schema for Sinclair Patterns Analytics
Creates tables optimized for PostgreSQL
"""

import os
import sys
from dotenv import load_dotenv

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("❌ psycopg2 not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2
    from psycopg2.extras import execute_values

load_dotenv()


def get_db_connection():
    """Get PostgreSQL connection from environment"""
    database_url = os.getenv("DATABASE_EXT_SHOPIFY_DATA")

    if not database_url or database_url == "postgresql://user:password@host:port/database":
        print("❌ DATABASE_EXT_SHOPIFY_DATA not found in environment")
        print("Add to .env file:")
        print("DATABASE_EXT_SHOPIFY_DATA=postgresql://user:password@host:port/database")
        sys.exit(1)

    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)


def initialize_database():
    """Create all tables and indexes for PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("Creating PostgreSQL tables...")

    # Orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id BIGINT PRIMARY KEY,
            order_number BIGINT,
            order_name TEXT,
            created_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE,
            processed_at TIMESTAMP WITH TIME ZONE,

            -- Customer info
            customer_id BIGINT,
            email TEXT,

            -- Geographic data
            country TEXT,
            country_code TEXT,
            province TEXT,
            city TEXT,

            -- Financial data
            total_price NUMERIC(10, 2),
            subtotal_price NUMERIC(10, 2),
            total_tax NUMERIC(10, 2),
            total_discounts NUMERIC(10, 2),
            currency TEXT,

            -- Marketing & Attribution (JSONB for flexibility)
            referring_site TEXT,
            landing_site TEXT,
            source_name TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            utm_content TEXT,
            utm_term TEXT,

            -- Order status
            financial_status TEXT,
            fulfillment_status TEXT,
            cancelled_at TIMESTAMP WITH TIME ZONE,
            cancel_reason TEXT,

            -- Metadata
            tags TEXT,
            note TEXT,
            discount_codes TEXT,

            -- Tracking
            synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Line items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS line_items (
            id SERIAL PRIMARY KEY,
            line_item_id BIGINT UNIQUE,
            order_id BIGINT REFERENCES orders(order_id) ON DELETE CASCADE,

            -- Product identification
            product_id BIGINT,
            variant_id BIGINT,
            product_title TEXT,
            variant_title TEXT,
            sku TEXT,
            vendor TEXT,

            -- Pricing & quantity
            quantity INTEGER,
            price NUMERIC(10, 2),
            total_discount NUMERIC(10, 2),

            -- Product categorization
            product_type TEXT,

            -- Tracking
            synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id BIGINT PRIMARY KEY,
            title TEXT,
            handle TEXT,
            product_type TEXT,
            vendor TEXT,

            -- Dates
            created_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE,
            published_at TIMESTAMP WITH TIME ZONE,

            -- Metadata
            tags TEXT,
            status TEXT,

            -- Tracking
            synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id BIGINT PRIMARY KEY,
            email TEXT,
            first_name TEXT,
            last_name TEXT,

            -- Geographic
            country TEXT,
            province TEXT,
            city TEXT,

            -- Marketing
            accepts_marketing BOOLEAN,
            marketing_opt_in_level TEXT,

            -- Customer stats
            orders_count INTEGER,
            total_spent NUMERIC(10, 2),

            -- Dates
            created_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE,

            -- Tracking
            synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Sync tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_history (
            id SERIAL PRIMARY KEY,
            sync_type TEXT,
            sync_started_at TIMESTAMP WITH TIME ZONE,
            sync_completed_at TIMESTAMP WITH TIME ZONE,
            records_fetched INTEGER,
            last_order_date TIMESTAMP WITH TIME ZONE,
            status TEXT,
            error_message TEXT
        )
    """)

    # Segment metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS segment_metadata (
            segment_name TEXT PRIMARY KEY,
            view_name TEXT,
            segment_type TEXT,
            query_filter TEXT,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    print("Creating indexes...")

    # Create indexes for performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_country ON orders(country)",
        "CREATE INDEX IF NOT EXISTS idx_orders_email ON orders(email)",
        "CREATE INDEX IF NOT EXISTS idx_orders_utm_campaign ON orders(utm_campaign)",
        "CREATE INDEX IF NOT EXISTS idx_orders_utm_source ON orders(utm_source)",

        "CREATE INDEX IF NOT EXISTS idx_line_items_order ON line_items(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_line_items_product ON line_items(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_line_items_variant ON line_items(variant_id)",

        "CREATE INDEX IF NOT EXISTS idx_products_type ON products(product_type)",
        "CREATE INDEX IF NOT EXISTS idx_products_handle ON products(handle)",

        "CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)",
        "CREATE INDEX IF NOT EXISTS idx_customers_country ON customers(country)",
    ]

    for index_sql in indexes:
        cursor.execute(index_sql)

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ PostgreSQL database initialized successfully!")


def get_db_stats():
    """Get statistics about the database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {}
    for table in ['orders', 'line_items', 'products', 'customers']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        result = cursor.fetchone()
        stats[table] = result[0] if result else 0

    # Get date range of orders
    cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM orders")
    date_range = cursor.fetchone()
    stats['date_range'] = date_range

    # Get last sync
    cursor.execute("""
        SELECT sync_completed_at, records_fetched
        FROM sync_history
        ORDER BY id DESC
        LIMIT 1
    """)
    last_sync = cursor.fetchone()
    stats['last_sync'] = last_sync

    cursor.close()
    conn.close()

    return stats


if __name__ == '__main__':
    print("Initializing Sinclair Patterns Analytics Database (PostgreSQL)")
    print("=" * 70)

    initialize_database()

    print("\nDatabase tables created:")
    print("  • orders - Complete order information with UTM tracking")
    print("  • line_items - Products purchased in each order")
    print("  • products - Product catalog")
    print("  • customers - Customer information")
    print("  • sync_history - Track data synchronization")
    print("  • segment_metadata - Track customer segments")

    print("\nIndexes created for fast queries on:")
    print("  • Dates, countries, customers, products")
    print("  • UTM parameters for campaign analysis")

    try:
        stats = get_db_stats()
        print(f"\nCurrent database stats:")
        print(f"  Orders: {stats.get('orders', 0)}")
        print(f"  Line Items: {stats.get('line_items', 0)}")
        print(f"  Products: {stats.get('products', 0)}")
        print(f"  Customers: {stats.get('customers', 0)}")
    except Exception as e:
        print(f"\nNote: {e}")

    print("\n✅ PostgreSQL database ready!")
