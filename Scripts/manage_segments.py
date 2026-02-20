#!/usr/bin/env python3
"""
Manage Local Customer Segments
Creates database views for customer segments based on product purchases or other criteria
"""

import sqlite3
import sys
from pathlib import Path
from db_schema import get_db_path


class SegmentManager:
    def __init__(self):
        self.db_path = get_db_path()
        if not self.db_path.exists():
            print(f"❌ Database not found at {self.db_path}")
            print("Run db_schema.py first to initialize the database")
            sys.exit(1)

    def create_product_segment(self, segment_name, product_id, description=None):
        """
        Create a view for customers who purchased a specific product

        Args:
            segment_name: Name for the segment (will be prefixed with 'segment_')
            product_id: Shopify product ID
            description: Optional description
        """
        view_name = f"segment_{segment_name.lower().replace(' ', '_').replace('-', '_')}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Drop existing view if it exists
        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")

        # Create the view
        query = f"""
        CREATE VIEW {view_name} AS
        SELECT DISTINCT
            o.customer_id,
            o.email,
            COUNT(DISTINCT o.order_id) as order_count,
            SUM(o.total_price) as total_spent,
            MIN(o.created_at) as first_purchase_date,
            MAX(o.created_at) as last_purchase_date,
            GROUP_CONCAT(DISTINCT o.country) as countries,
            li.product_title
        FROM orders o
        JOIN line_items li ON o.order_id = li.order_id
        WHERE li.product_id = {product_id}
        GROUP BY o.customer_id, o.email, li.product_title
        ORDER BY last_purchase_date DESC
        """

        cursor.execute(query)

        # Store segment metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS segment_metadata (
                segment_name TEXT PRIMARY KEY,
                view_name TEXT,
                segment_type TEXT,
                query_filter TEXT,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO segment_metadata
            (segment_name, view_name, segment_type, query_filter, description)
            VALUES (?, ?, ?, ?, ?)
        """, (segment_name, view_name, 'product', f"product_id = {product_id}", description))

        conn.commit()

        # Get count
        cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
        count = cursor.fetchone()[0]

        conn.close()

        print(f"✅ Created segment: {segment_name}")
        print(f"   View name: {view_name}")
        print(f"   Customers: {count}")
        print(f"   Filter: product_id = {product_id}")

        return view_name

    def create_multi_product_segment(self, segment_name, product_ids, description=None):
        """
        Create a view for customers who purchased any of the specified products

        Args:
            segment_name: Name for the segment
            product_ids: List of Shopify product IDs
            description: Optional description
        """
        view_name = f"segment_{segment_name.lower().replace(' ', '_').replace('-', '_')}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")

        product_ids_str = ','.join(map(str, product_ids))

        query = f"""
        CREATE VIEW {view_name} AS
        SELECT DISTINCT
            o.customer_id,
            o.email,
            COUNT(DISTINCT o.order_id) as order_count,
            SUM(o.total_price) as total_spent,
            MIN(o.created_at) as first_purchase_date,
            MAX(o.created_at) as last_purchase_date,
            GROUP_CONCAT(DISTINCT o.country) as countries,
            GROUP_CONCAT(DISTINCT li.product_title) as products_purchased
        FROM orders o
        JOIN line_items li ON o.order_id = li.order_id
        WHERE li.product_id IN ({product_ids_str})
        GROUP BY o.customer_id, o.email
        ORDER BY last_purchase_date DESC
        """

        cursor.execute(query)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS segment_metadata (
                segment_name TEXT PRIMARY KEY,
                view_name TEXT,
                segment_type TEXT,
                query_filter TEXT,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO segment_metadata
            (segment_name, view_name, segment_type, query_filter, description)
            VALUES (?, ?, ?, ?, ?)
        """, (segment_name, view_name, 'multi_product', f"product_id IN ({product_ids_str})", description))

        conn.commit()

        cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
        count = cursor.fetchone()[0]

        conn.close()

        print(f"✅ Created segment: {segment_name}")
        print(f"   View name: {view_name}")
        print(f"   Customers: {count}")
        print(f"   Filter: product_id IN ({product_ids_str})")

        return view_name

    def create_custom_segment(self, segment_name, where_clause, description=None):
        """
        Create a custom segment with any WHERE clause

        Args:
            segment_name: Name for the segment
            where_clause: SQL WHERE clause (without the WHERE keyword)
            description: Optional description
        """
        view_name = f"segment_{segment_name.lower().replace(' ', '_').replace('-', '_')}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")

        query = f"""
        CREATE VIEW {view_name} AS
        SELECT DISTINCT
            o.customer_id,
            o.email,
            COUNT(DISTINCT o.order_id) as order_count,
            SUM(o.total_price) as total_spent,
            MIN(o.created_at) as first_purchase_date,
            MAX(o.created_at) as last_purchase_date,
            GROUP_CONCAT(DISTINCT o.country) as countries
        FROM orders o
        LEFT JOIN line_items li ON o.order_id = li.order_id
        WHERE {where_clause}
        GROUP BY o.customer_id, o.email
        ORDER BY last_purchase_date DESC
        """

        cursor.execute(query)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS segment_metadata (
                segment_name TEXT PRIMARY KEY,
                view_name TEXT,
                segment_type TEXT,
                query_filter TEXT,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO segment_metadata
            (segment_name, view_name, segment_type, query_filter, description)
            VALUES (?, ?, ?, ?, ?)
        """, (segment_name, view_name, 'custom', where_clause, description))

        conn.commit()

        cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
        count = cursor.fetchone()[0]

        conn.close()

        print(f"✅ Created segment: {segment_name}")
        print(f"   View name: {view_name}")
        print(f"   Customers: {count}")
        print(f"   Filter: {where_clause}")

        return view_name

    def list_segments(self):
        """List all created segments"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if metadata table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='segment_metadata'
        """)

        if not cursor.fetchone():
            print("No segments created yet")
            conn.close()
            return

        cursor.execute("""
            SELECT segment_name, view_name, segment_type, query_filter, description, created_at
            FROM segment_metadata
            ORDER BY created_at DESC
        """)

        segments = cursor.fetchall()

        if not segments:
            print("No segments created yet")
        else:
            print("\n📊 Local Customer Segments")
            print("=" * 80)
            for seg in segments:
                name, view, seg_type, query_filter, desc, created = seg

                # Get count
                cursor.execute(f"SELECT COUNT(*) FROM {view}")
                count = cursor.fetchone()[0]

                print(f"\n{name}")
                print(f"  Type: {seg_type}")
                print(f"  View: {view}")
                print(f"  Customers: {count}")
                print(f"  Filter: {query_filter}")
                if desc:
                    print(f"  Description: {desc}")
                print(f"  Created: {created}")

        conn.close()

    def export_segment(self, segment_name, output_file=None):
        """Export segment to CSV"""
        view_name = f"segment_{segment_name.lower().replace(' ', '_').replace('-', '_')}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if view exists
        cursor.execute(f"""
            SELECT name FROM sqlite_master
            WHERE type='view' AND name='{view_name}'
        """)

        if not cursor.fetchone():
            print(f"❌ Segment '{segment_name}' not found")
            conn.close()
            return

        cursor.execute(f"SELECT * FROM {view_name}")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        if not output_file:
            output_file = f"{segment_name.replace(' ', '_')}_segment.csv"

        import csv
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        conn.close()

        print(f"✅ Exported {len(rows)} customers to {output_file}")
        return output_file

    def delete_segment(self, segment_name):
        """Delete a segment"""
        view_name = f"segment_{segment_name.lower().replace(' ', '_').replace('-', '_')}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")
        cursor.execute("DELETE FROM segment_metadata WHERE segment_name = ?", (segment_name,))

        conn.commit()
        conn.close()

        print(f"✅ Deleted segment: {segment_name}")


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description='Manage local customer segments')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Create product segment
    create_parser = subparsers.add_parser('create', help='Create a product segment')
    create_parser.add_argument('name', help='Segment name')
    create_parser.add_argument('product_id', type=int, help='Product ID')
    create_parser.add_argument('--description', help='Segment description')

    # Create multi-product segment
    multi_parser = subparsers.add_parser('create-multi', help='Create segment for multiple products')
    multi_parser.add_argument('name', help='Segment name')
    multi_parser.add_argument('product_ids', help='Comma-separated product IDs')
    multi_parser.add_argument('--description', help='Segment description')

    # Create custom segment
    custom_parser = subparsers.add_parser('create-custom', help='Create custom segment')
    custom_parser.add_argument('name', help='Segment name')
    custom_parser.add_argument('where_clause', help='SQL WHERE clause')
    custom_parser.add_argument('--description', help='Segment description')

    # List segments
    subparsers.add_parser('list', help='List all segments')

    # Export segment
    export_parser = subparsers.add_parser('export', help='Export segment to CSV')
    export_parser.add_argument('name', help='Segment name')
    export_parser.add_argument('--output', help='Output file path')

    # Delete segment
    delete_parser = subparsers.add_parser('delete', help='Delete a segment')
    delete_parser.add_argument('name', help='Segment name')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    manager = SegmentManager()

    if args.command == 'create':
        manager.create_product_segment(args.name, args.product_id, args.description)
    elif args.command == 'create-multi':
        product_ids = [int(pid.strip()) for pid in args.product_ids.split(',')]
        manager.create_multi_product_segment(args.name, product_ids, args.description)
    elif args.command == 'create-custom':
        manager.create_custom_segment(args.name, args.where_clause, args.description)
    elif args.command == 'list':
        manager.list_segments()
    elif args.command == 'export':
        manager.export_segment(args.name, args.output)
    elif args.command == 'delete':
        manager.delete_segment(args.name)


if __name__ == '__main__':
    main()
