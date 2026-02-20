#!/usr/bin/env python3
"""
Sync pattern buyers from Shopify DB to a Sendy suppression list.

Usage:
    python3 sync_buyers_to_sendy.py --product-id 9846865133808 --list-id YOUR_LIST_ID

Before running:
    1. Create a list in Sendy UI (e.g. "Helen_Buyers")
    2. Get the list ID from Sendy
    3. Run this script with that list ID

The script will subscribe all purchasers of the given product to that list.
When sending E2/E3 in Sendy, exclude that list.
"""

import sqlite3
import requests
import time
import argparse
from db_schema import get_db_path

SENDY_API_KEY = "9beSlQPv8LFt5tZP9cP2"
SENDY_HOST = "https://mail.sinclairpatterns.com"


def get_buyers(product_id):
    """Query DB for all unique purchaser emails for a given product ID."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT o.email
        FROM orders o
        JOIN line_items li ON o.order_id = li.order_id
        WHERE li.product_id = ?
        AND o.email IS NOT NULL AND o.email != ''
        ORDER BY o.email
    """, (product_id,))
    emails = [row[0].strip().lower() for row in cursor.fetchall()]
    conn.close()
    return emails


def subscribe_to_sendy(email, list_id):
    """Subscribe a single email to a Sendy list."""
    response = requests.post(
        f"{SENDY_HOST}/subscribe",
        data={
            "api_key": SENDY_API_KEY,
            "list": list_id,
            "email": email,
            "boolean": "true"
        }
    )
    return response.text.strip()


def main():
    parser = argparse.ArgumentParser(description="Sync pattern buyers to Sendy suppression list")
    parser.add_argument("--product-id", type=int, required=True, help="Shopify product ID")
    parser.add_argument("--list-id", type=str, required=True, help="Sendy list ID to subscribe buyers to")
    parser.add_argument("--dry-run", action="store_true", help="Print emails without subscribing")
    args = parser.parse_args()

    print("=" * 60)
    print("SINCLAIR PATTERNS - Sync Buyers to Sendy")
    print("=" * 60)

    print(f"\n[1/2] Querying DB for product {args.product_id}...")
    emails = get_buyers(args.product_id)
    print(f"  Found {len(emails)} unique purchasers")

    if args.dry_run:
        print("\n[DRY RUN] Would subscribe:")
        for e in emails:
            print(f"  {e}")
        return

    print(f"\n[2/2] Subscribing to Sendy list {args.list_id}...")
    success = 0
    failed = 0
    for i, email in enumerate(emails, 1):
        result = subscribe_to_sendy(email, args.list_id)
        if result == "1":
            success += 1
        else:
            print(f"  WARNING: {email} -> {result}")
            failed += 1

        if i % 50 == 0:
            print(f"  Progress: {i}/{len(emails)}...")
            time.sleep(1)  # avoid rate limiting

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"  Subscribed: {success}")
    print(f"  Failed:     {failed}")
    print(f"\nNow exclude list '{args.list_id}' when sending E2/E3 in Sendy.")
    print("=" * 60)


if __name__ == "__main__":
    main()
