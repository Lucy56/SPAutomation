#!/usr/bin/env python3
"""
Enhanced PostgreSQL Schema for Sinclair Patterns Analytics
Includes refunds, customer tags, payment gateway, and aggregation tables
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2

load_dotenv()


def get_db_connection():
    """Get PostgreSQL connection from environment"""
    database_url = os.getenv("DATABASE_EXT_SHOPIFY_DATA")

    if not database_url or database_url == "postgresql://user:password@host:port/database":
        print("❌ DATABASE_EXT_SHOPIFY_DATA not found in environment")
        sys.exit(1)

    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)


def enhance_schema():
    """Add new fields and tables to existing schema"""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("🔧 Enhancing PostgreSQL schema...")

    # Add new columns to orders table
    print("  Adding new columns to orders table...")
    new_order_columns = [
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS gateway TEXT",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS checkout_id BIGINT",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS browser_ip TEXT",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS total_shipping NUMERIC(10, 2)",
    ]

    for sql in new_order_columns:
        try:
            cursor.execute(sql)
        except Exception as e:
            print(f"    Note: {e}")

    # Add new columns to customers table
    print("  Adding new columns to customers table...")
    new_customer_columns = [
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS customer_tags TEXT",
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS state TEXT",  # customer state/status
    ]

    for sql in new_customer_columns:
        try:
            cursor.execute(sql)
        except Exception as e:
            print(f"    Note: {e}")

    # Create refunds table
    print("  Creating refunds table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS refunds (
            refund_id BIGINT PRIMARY KEY,
            order_id BIGINT REFERENCES orders(order_id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE,
            processed_at TIMESTAMP WITH TIME ZONE,

            -- Refund details
            note TEXT,
            user_id BIGINT,

            -- Financial
            total_refunded NUMERIC(10, 2),

            -- Tracking
            synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create refund line items table
    print("  Creating refund_line_items table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS refund_line_items (
            id SERIAL PRIMARY KEY,
            refund_id BIGINT REFERENCES refunds(refund_id) ON DELETE CASCADE,
            line_item_id BIGINT,
            quantity INTEGER,
            subtotal NUMERIC(10, 2),
            total_tax NUMERIC(10, 2),

            -- Tracking
            synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create daily stats aggregation table
    print("  Creating daily_stats table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date DATE PRIMARY KEY,

            -- Order metrics
            total_orders INTEGER,
            total_revenue NUMERIC(12, 2),
            total_tax NUMERIC(12, 2),
            total_discounts NUMERIC(12, 2),
            avg_order_value NUMERIC(10, 2),

            -- Customer metrics
            new_customers INTEGER,
            returning_customers INTEGER,

            -- Product metrics
            total_items_sold INTEGER,
            unique_products_sold INTEGER,

            -- Calculated at
            calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create product stats aggregation table
    print("  Creating product_stats table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_stats (
            product_id BIGINT,
            date DATE,

            -- Sales metrics
            units_sold INTEGER,
            revenue NUMERIC(12, 2),
            orders_count INTEGER,
            unique_customers INTEGER,

            -- Performance
            avg_price NUMERIC(10, 2),
            refund_count INTEGER,
            refund_amount NUMERIC(12, 2),

            -- Calculated at
            calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (product_id, date)
        )
    """)

    # Create customer LTV table
    print("  Creating customer_ltv table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_ltv (
            customer_id BIGINT PRIMARY KEY,
            email TEXT,

            -- Lifetime metrics
            total_orders INTEGER,
            total_spent NUMERIC(12, 2),
            avg_order_value NUMERIC(10, 2),

            -- Dates
            first_order_date TIMESTAMP WITH TIME ZONE,
            last_order_date TIMESTAMP WITH TIME ZONE,

            -- Cohort
            cohort_month TEXT,  -- YYYY-MM format

            -- Engagement
            days_since_first_order INTEGER,
            days_since_last_order INTEGER,

            -- Classification
            customer_segment TEXT,  -- VIP, Regular, At Risk, Lost, etc.

            -- Calculated at
            calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create UTM performance table
    print("  Creating utm_performance table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS utm_performance (
            date DATE,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,

            -- Metrics
            sessions INTEGER,
            orders INTEGER,
            revenue NUMERIC(12, 2),
            new_customers INTEGER,

            -- Performance
            conversion_rate NUMERIC(5, 4),
            avg_order_value NUMERIC(10, 2),

            -- Calculated at
            calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (date, utm_source, utm_medium, utm_campaign)
        )
    """)

    conn.commit()

    # Create indexes
    print("  Creating indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_refunds_order ON refunds(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_refunds_created ON refunds(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_refund_line_items_refund ON refund_line_items(refund_id)",

        "CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date)",
        "CREATE INDEX IF NOT EXISTS idx_product_stats_date ON product_stats(date)",
        "CREATE INDEX IF NOT EXISTS idx_product_stats_product ON product_stats(product_id)",

        "CREATE INDEX IF NOT EXISTS idx_customer_ltv_segment ON customer_ltv(customer_segment)",
        "CREATE INDEX IF NOT EXISTS idx_customer_ltv_cohort ON customer_ltv(cohort_month)",
        "CREATE INDEX IF NOT EXISTS idx_customer_ltv_email ON customer_ltv(email)",

        "CREATE INDEX IF NOT EXISTS idx_utm_date ON utm_performance(date)",
        "CREATE INDEX IF NOT EXISTS idx_utm_campaign ON utm_performance(utm_campaign)",

        "CREATE INDEX IF NOT EXISTS idx_customers_tags ON customers(customer_tags)",
        "CREATE INDEX IF NOT EXISTS idx_orders_gateway ON orders(gateway)",
    ]

    for index_sql in indexes:
        try:
            cursor.execute(index_sql)
        except Exception as e:
            print(f"    Note: {e}")

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ Schema enhanced successfully!")


def show_tables():
    """Show all tables in the database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    tables = cursor.fetchall()

    print("\n📊 Database Tables:")
    print("=" * 60)
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  • {table[0]:<30} {count:>10,} records")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    print("Enhanced PostgreSQL Schema for Analytics")
    print("=" * 70)

    enhance_schema()
    show_tables()

    print("\n✅ Database ready for analytics!")
    print("\nNew tables added:")
    print("  • refunds - Track refunds and returns")
    print("  • refund_line_items - Refund details")
    print("  • daily_stats - Daily aggregated metrics")
    print("  • product_stats - Product performance by day")
    print("  • customer_ltv - Customer lifetime value")
    print("  • utm_performance - Campaign performance")
