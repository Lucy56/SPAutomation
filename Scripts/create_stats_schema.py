#!/usr/bin/env python3
"""
Create Stats Aggregation Schema
Creates tables for customer profiles, daily stats, and weekly stats
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2

load_dotenv()


def get_db_connection():
    """Get PostgreSQL connection from environment"""
    database_url = os.getenv("DATABASE_EXT_SHOPIFY_DATA")

    if not database_url:
        print("❌ DATABASE_EXT_SHOPIFY_DATA not found in environment")
        sys.exit(1)

    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)


def create_schema():
    """Create all tables and indexes for stats aggregation"""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("🔧 Creating stats aggregation schema...")
    print("=" * 70)

    # 1. ENHANCED CUSTOMERS TABLE
    print("\n📊 Creating customers table...")

    # Drop existing customers table if it exists (for clean setup)
    cursor.execute("DROP TABLE IF EXISTS customers CASCADE")

    cursor.execute("""
        CREATE TABLE customers (
            customer_id BIGINT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE,

            -- FIRST ORDER TRACKING
            first_order_date TIMESTAMP WITH TIME ZONE,
            first_order_id BIGINT,
            first_order_type TEXT,          -- 'paid' or 'free'
            first_order_amount NUMERIC(10, 2),

            -- FREE PATTERN TRACKING (if first order was free)
            first_free_pattern_id BIGINT,
            first_free_pattern_name TEXT,   -- 'Harper', 'Valley', 'Sunset', 'Mojo'
            first_free_discount_code TEXT,

            -- ACQUISITION SOURCE
            acquisition_source TEXT,         -- 'email', 'social', 'organic', 'direct', 'unknown'
            acquisition_channel TEXT,        -- 'newsletter', 'facebook', 'google', etc.
            acquisition_campaign TEXT,       -- UTM campaign

            -- CONVERSION TRACKING
            has_paid_purchase BOOLEAN DEFAULT FALSE,
            first_paid_order_date TIMESTAMP WITH TIME ZONE,
            first_paid_order_id BIGINT,
            days_to_first_paid INTEGER,      -- NULL if never converted

            -- LIFETIME VALUE
            total_orders INTEGER DEFAULT 0,
            total_spent NUMERIC(12, 2) DEFAULT 0,
            avg_order_value NUMERIC(10, 2) DEFAULT 0,
            last_order_date TIMESTAMP WITH TIME ZONE,

            -- SEGMENTATION
            customer_type TEXT,  -- 'paid_customer', 'converted_customer', 'free_only'

            -- TRACKING
            last_aggregated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("  ✓ Customers table created")

    # Create indexes for customers
    print("  Creating indexes...")
    indexes_customers = [
        "CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)",
        "CREATE INDEX IF NOT EXISTS idx_customers_type ON customers(customer_type)",
        "CREATE INDEX IF NOT EXISTS idx_customers_first_order_type ON customers(first_order_type)",
        "CREATE INDEX IF NOT EXISTS idx_customers_converted ON customers(has_paid_purchase)",
        "CREATE INDEX IF NOT EXISTS idx_customers_first_order_date ON customers(first_order_date)",
    ]

    for idx_sql in indexes_customers:
        cursor.execute(idx_sql)

    print("  ✓ Customer indexes created")

    # 2. DAILY STATS TABLE
    print("\n📅 Creating daily_stats table...")

    # Drop existing table for clean setup
    cursor.execute("DROP TABLE IF EXISTS daily_stats CASCADE")

    cursor.execute("""
        CREATE TABLE daily_stats (
            date DATE PRIMARY KEY,

            -- REVENUE METRICS
            total_revenue NUMERIC(12, 2) DEFAULT 0,
            total_orders INTEGER DEFAULT 0,
            avg_order_value NUMERIC(10, 2) DEFAULT 0,

            -- NEW CUSTOMERS (by first order type)
            new_customers_paid INTEGER DEFAULT 0,      -- First order = paid
            new_customers_free INTEGER DEFAULT 0,      -- First order = free
            new_customers_total INTEGER DEFAULT 0,

            -- CONVERSIONS (free → paid that day)
            conversions_count INTEGER DEFAULT 0,
            conversions_revenue NUMERIC(12, 2) DEFAULT 0,
            avg_days_to_convert NUMERIC(6, 2),

            -- FREE PATTERN DOWNLOADS (new customers)
            harper_downloads INTEGER DEFAULT 0,
            valley_downloads INTEGER DEFAULT 0,
            sunset_downloads INTEGER DEFAULT 0,
            mojo_downloads INTEGER DEFAULT 0,
            other_free_downloads INTEGER DEFAULT 0,

            -- ACQUISITION BREAKDOWN (new customers)
            new_from_email INTEGER DEFAULT 0,
            new_from_social INTEGER DEFAULT 0,
            new_from_organic INTEGER DEFAULT 0,
            new_from_direct INTEGER DEFAULT 0,
            new_from_unknown INTEGER DEFAULT 0,

            -- TRACKING
            calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("  ✓ Daily stats table created")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date)")
    print("  ✓ Daily stats index created")

    # 3. WEEKLY STATS TABLE
    print("\n📆 Creating weekly_stats table...")

    # Drop existing table for clean setup
    cursor.execute("DROP TABLE IF EXISTS weekly_stats CASCADE")

    cursor.execute("""
        CREATE TABLE weekly_stats (
            year INTEGER NOT NULL,
            week_number INTEGER NOT NULL,           -- ISO week number (1-53)
            week_start_date DATE NOT NULL,          -- Monday of that week
            week_end_date DATE NOT NULL,            -- Sunday of that week

            -- REVENUE METRICS (sum of week)
            total_revenue NUMERIC(12, 2) DEFAULT 0,
            total_orders INTEGER DEFAULT 0,
            avg_order_value NUMERIC(10, 2) DEFAULT 0,

            -- NEW CUSTOMERS (sum of week)
            new_customers_paid INTEGER DEFAULT 0,
            new_customers_free INTEGER DEFAULT 0,
            new_customers_total INTEGER DEFAULT 0,

            -- CONVERSIONS (sum of week)
            conversions_count INTEGER DEFAULT 0,
            conversions_revenue NUMERIC(12, 2) DEFAULT 0,
            avg_days_to_convert NUMERIC(6, 2),

            -- CONVERSION RATE (calculated)
            conversion_rate NUMERIC(5, 2),          -- % of all-time free customers who converted

            -- FREE PATTERN DOWNLOADS (sum of week)
            harper_downloads INTEGER DEFAULT 0,
            valley_downloads INTEGER DEFAULT 0,
            sunset_downloads INTEGER DEFAULT 0,
            mojo_downloads INTEGER DEFAULT 0,
            other_free_downloads INTEGER DEFAULT 0,
            total_free_downloads INTEGER DEFAULT 0,

            -- ACQUISITION BREAKDOWN (sum of week)
            new_from_email INTEGER DEFAULT 0,
            new_from_social INTEGER DEFAULT 0,
            new_from_organic INTEGER DEFAULT 0,
            new_from_direct INTEGER DEFAULT 0,
            new_from_unknown INTEGER DEFAULT 0,

            -- TRACKING
            calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (year, week_number)
        )
    """)

    print("  ✓ Weekly stats table created")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_weekly_stats_start_date ON weekly_stats(week_start_date)")
    print("  ✓ Weekly stats index created")

    conn.commit()
    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("✅ Schema created successfully!")
    print("\nTables created:")
    print("  • customers - Customer profiles with conversion tracking")
    print("  • daily_stats - Daily aggregated metrics")
    print("  • weekly_stats - Weekly aggregated metrics")


def show_table_status():
    """Show current table row counts"""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n" + "=" * 70)
    print("📊 Current Table Status:")
    print("=" * 70)

    tables = ['customers', 'daily_stats', 'weekly_stats']

    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table:<20} {count:>10,} records")
        except Exception as e:
            print(f"  {table:<20} ERROR: {e}")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    print("Stats Aggregation Schema Creator")
    print("=" * 70)

    create_schema()
    show_table_status()

    print("\n✅ Ready for data aggregation!")
    print("\nNext steps:")
    print("  1. Run: python Scripts/build_customer_profiles.py --full-history")
    print("  2. Run: python Scripts/aggregate_daily_stats.py --full-history")
    print("  3. Run: python Scripts/aggregate_weekly_stats.py --full-history")
