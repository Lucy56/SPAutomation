#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL
Copies all orders, line_items, and sync history to Railway PostgreSQL
"""

import sqlite3
import sys
from datetime import datetime
from db_schema import get_db_path
from pg_schema import get_db_connection
import psycopg2.extras


def migrate_orders(sqlite_conn, pg_conn, batch_size=1000):
    """Migrate orders from SQLite to PostgreSQL"""
    print("📦 Migrating orders...")

    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    # Get total count
    sqlite_cursor.execute("SELECT COUNT(*) FROM orders")
    total = sqlite_cursor.fetchone()[0]
    print(f"   Total orders to migrate: {total}")

    # Fetch in batches
    offset = 0
    migrated = 0

    while offset < total:
        sqlite_cursor.execute(f"""
            SELECT order_id, order_number, order_name, created_at, updated_at, processed_at,
                   customer_id, email, country, country_code, province, city,
                   total_price, subtotal_price, total_tax, total_discounts, currency,
                   referring_site, landing_site, source_name,
                   utm_source, utm_medium, utm_campaign, utm_content, utm_term,
                   financial_status, fulfillment_status, cancelled_at, cancel_reason,
                   tags, note, discount_codes, synced_at
            FROM orders
            LIMIT {batch_size} OFFSET {offset}
        """)

        rows = sqlite_cursor.fetchall()
        if not rows:
            break

        # Insert into PostgreSQL
        psycopg2.extras.execute_values(
            pg_cursor,
            """
            INSERT INTO orders (
                order_id, order_number, order_name, created_at, updated_at, processed_at,
                customer_id, email, country, country_code, province, city,
                total_price, subtotal_price, total_tax, total_discounts, currency,
                referring_site, landing_site, source_name,
                utm_source, utm_medium, utm_campaign, utm_content, utm_term,
                financial_status, fulfillment_status, cancelled_at, cancel_reason,
                tags, note, discount_codes, synced_at
            ) VALUES %s
            ON CONFLICT (order_id) DO UPDATE SET
                updated_at = EXCLUDED.updated_at,
                synced_at = EXCLUDED.synced_at
            """,
            rows
        )

        pg_conn.commit()
        migrated += len(rows)
        offset += batch_size

        print(f"   Progress: {migrated}/{total} ({migrated*100//total}%)", end='\r')

    print(f"\n✅ Migrated {migrated} orders")


def migrate_line_items(sqlite_conn, pg_conn, batch_size=5000):
    """Migrate line items from SQLite to PostgreSQL"""
    print("📦 Migrating line items...")

    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    # Get total count
    sqlite_cursor.execute("SELECT COUNT(*) FROM line_items")
    total = sqlite_cursor.fetchone()[0]
    print(f"   Total line items to migrate: {total}")

    # Fetch in batches
    offset = 0
    migrated = 0

    while offset < total:
        sqlite_cursor.execute(f"""
            SELECT line_item_id, order_id, product_id, variant_id,
                   product_title, variant_title, sku, vendor,
                   quantity, price, total_discount, product_type, synced_at
            FROM line_items
            LIMIT {batch_size} OFFSET {offset}
        """)

        rows = sqlite_cursor.fetchall()
        if not rows:
            break

        # Insert into PostgreSQL
        psycopg2.extras.execute_values(
            pg_cursor,
            """
            INSERT INTO line_items (
                line_item_id, order_id, product_id, variant_id,
                product_title, variant_title, sku, vendor,
                quantity, price, total_discount, product_type, synced_at
            ) VALUES %s
            ON CONFLICT (line_item_id) DO UPDATE SET
                synced_at = EXCLUDED.synced_at
            """,
            rows
        )

        pg_conn.commit()
        migrated += len(rows)
        offset += batch_size

        print(f"   Progress: {migrated}/{total} ({migrated*100//total}%)", end='\r')

    print(f"\n✅ Migrated {migrated} line items")


def migrate_sync_history(sqlite_conn, pg_conn):
    """Migrate sync history from SQLite to PostgreSQL"""
    print("📦 Migrating sync history...")

    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    sqlite_cursor.execute("""
        SELECT sync_type, sync_started_at, sync_completed_at,
               records_fetched, last_order_date, status, error_message
        FROM sync_history
    """)

    rows = sqlite_cursor.fetchall()

    if rows:
        psycopg2.extras.execute_values(
            pg_cursor,
            """
            INSERT INTO sync_history (
                sync_type, sync_started_at, sync_completed_at,
                records_fetched, last_order_date, status, error_message
            ) VALUES %s
            """,
            rows
        )

        pg_conn.commit()
        print(f"✅ Migrated {len(rows)} sync records")
    else:
        print("   No sync history to migrate")


def main():
    """Main migration function"""
    print("="*70)
    print("MIGRATING SQLITE DATA TO POSTGRESQL")
    print("="*70)

    # Connect to SQLite
    sqlite_path = get_db_path()
    if not sqlite_path.exists():
        print(f"❌ SQLite database not found at {sqlite_path}")
        sys.exit(1)

    print(f"\n📂 Source: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)

    # Connect to PostgreSQL
    print("🔌 Connecting to PostgreSQL...")
    try:
        pg_conn = get_db_connection()
        print("✅ Connected to PostgreSQL\n")
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        sys.exit(1)

    # Confirm before proceeding
    response = input("This will migrate all data to PostgreSQL. Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled")
        sys.exit(0)

    start_time = datetime.now()

    try:
        # Migrate data
        migrate_orders(sqlite_conn, pg_conn)
        migrate_line_items(sqlite_conn, pg_conn)
        migrate_sync_history(sqlite_conn, pg_conn)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*70)
        print("MIGRATION COMPLETE!")
        print("="*70)
        print(f"Duration: {duration:.2f} seconds")

        # Show final stats
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute("SELECT COUNT(*) FROM orders")
        orders_count = pg_cursor.fetchone()[0]
        pg_cursor.execute("SELECT COUNT(*) FROM line_items")
        line_items_count = pg_cursor.fetchone()[0]

        print(f"\nFinal counts in PostgreSQL:")
        print(f"  Orders: {orders_count:,}")
        print(f"  Line Items: {line_items_count:,}")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        pg_conn.rollback()
        sys.exit(1)

    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == '__main__':
    main()
