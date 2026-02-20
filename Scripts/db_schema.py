#!/usr/bin/env python3
"""
Database Schema for Sinclair Patterns Analytics
SQLite database for comprehensive order and customer analysis
"""

import sqlite3
from pathlib import Path

def get_db_path():
    """Get path to SQLite database"""
    return Path(__file__).parent.parent / 'Data' / 'shopify_orders.db'

def initialize_database():
    """Create all tables and indexes"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Orders table - comprehensive order information
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            order_number INTEGER,
            order_name TEXT,
            created_at TEXT,
            updated_at TEXT,
            processed_at TEXT,

            -- Customer info
            customer_id INTEGER,
            email TEXT,

            -- Geographic data
            country TEXT,
            country_code TEXT,
            province TEXT,
            city TEXT,

            -- Financial data
            total_price REAL,
            subtotal_price REAL,
            total_tax REAL,
            total_discounts REAL,
            currency TEXT,

            -- Marketing & Attribution
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
            cancelled_at TEXT,
            cancel_reason TEXT,

            -- Metadata
            tags TEXT,
            note TEXT,
            discount_codes TEXT,

            -- Tracking
            synced_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Line items table - products in each order
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS line_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_item_id INTEGER UNIQUE,
            order_id INTEGER,

            -- Product identification
            product_id INTEGER,
            variant_id INTEGER,
            product_title TEXT,
            variant_title TEXT,
            sku TEXT,
            vendor TEXT,

            -- Pricing & quantity
            quantity INTEGER,
            price REAL,
            total_discount REAL,

            -- Product categorization
            product_type TEXT,

            -- Tracking
            synced_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    """)

    # Products table - product catalog
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            title TEXT,
            handle TEXT,
            product_type TEXT,
            vendor TEXT,

            -- Dates
            created_at TEXT,
            updated_at TEXT,
            published_at TEXT,

            -- Metadata
            tags TEXT,
            status TEXT,

            -- Tracking
            synced_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Customers table - customer information
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            email TEXT,
            first_name TEXT,
            last_name TEXT,

            -- Geographic
            country TEXT,
            province TEXT,
            city TEXT,

            -- Marketing
            accepts_marketing INTEGER,
            marketing_opt_in_level TEXT,

            -- Customer stats
            orders_count INTEGER,
            total_spent REAL,

            -- Dates
            created_at TEXT,
            updated_at TEXT,

            -- Tracking
            synced_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Sync tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type TEXT,
            sync_started_at TEXT,
            sync_completed_at TEXT,
            records_fetched INTEGER,
            last_order_date TEXT,
            status TEXT,
            error_message TEXT
        )
    """)

    # Create indexes for performance
    print("Creating indexes...")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_country ON orders(country)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_utm_campaign ON orders(utm_campaign)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_utm_source ON orders(utm_source)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_items_order ON line_items(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_items_product ON line_items(product_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_items_created ON line_items(synced_at)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_type ON products(product_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_created ON products(created_at)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_country ON customers(country)")

    conn.commit()
    conn.close()

    print(f"✓ Database initialized at: {db_path}")
    return db_path

def get_db_stats():
    """Get statistics about the database"""
    db_path = get_db_path()
    if not db_path.exists():
        return "Database not initialized"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    stats = {}
    for table in ['orders', 'line_items', 'products', 'customers']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = cursor.fetchone()[0]

    # Get date range of orders
    cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM orders")
    date_range = cursor.fetchone()
    stats['date_range'] = date_range

    # Get last sync
    cursor.execute("SELECT sync_completed_at, records_fetched FROM sync_history ORDER BY id DESC LIMIT 1")
    last_sync = cursor.fetchone()
    stats['last_sync'] = last_sync

    conn.close()
    return stats

if __name__ == '__main__':
    print("Initializing Sinclair Patterns Analytics Database")
    print("="*60)

    db_path = initialize_database()

    print("\nDatabase tables created:")
    print("  • orders - Complete order information with UTM tracking")
    print("  • line_items - Products purchased in each order")
    print("  • products - Product catalog")
    print("  • customers - Customer information")
    print("  • sync_history - Track data synchronization")

    print("\nIndexes created for fast queries on:")
    print("  • Dates, countries, customers, products")
    print("  • UTM parameters for campaign analysis")

    stats = get_db_stats()
    print(f"\nCurrent database stats:")
    print(f"  Orders: {stats.get('orders', 0)}")
    print(f"  Line Items: {stats.get('line_items', 0)}")
    print(f"  Products: {stats.get('products', 0)}")
    print(f"  Customers: {stats.get('customers', 0)}")

    print(f"\n✓ Database ready at: {db_path}")
