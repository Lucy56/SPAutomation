#!/usr/bin/env python3
"""
New Release E2/E3 Suppression - Sync pattern buyers to Sendy list.

Fetches all purchasers of a pattern from the local Shopify DB and
subscribes them to a Sendy list so they can be excluded from E2/E3.

Usage:
    # First run the orders updater to make sure DB is current:
    python3 update_recent_orders.py

    # Then run this script:
    python3 new_release_suppression.py --handle helen-stretch-pants-with-a-yoke-and-contoured-waistband-pdf-sewing-pattern --list-id YOUR_SENDY_LIST_ID

    # Dry run (no subscribing, just shows count):
    python3 new_release_suppression.py --handle helen-... --list-id xxx --dry-run

Steps to set up in Sendy:
    1. Go to Sendy -> Lists -> Create new list (e.g. "Helen Buyers")
    2. Copy the list ID from the list URL or settings
    3. Pass it as --list-id
    4. When sending E2/E3, click "Exclude lists" and select this list
"""

import sqlite3
import requests
import time
import argparse
import sys
from db_schema import get_db_path

SENDY_API_KEY = "9beSlQPv8LFt5tZP9cP2"
SENDY_HOST = "https://mail.sinclairpatterns.com"
SHOPIFY_STORE = "https://sinclairpatterns.com"


def get_product_id_from_handle(handle):
    """Look up product ID from Shopify product handle via public JSON API."""
    url = f"{SHOPIFY_STORE}/products/{handle}.json"
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        print(f"  ERROR: Could not fetch product '{handle}' (status {response.status_code})")
        sys.exit(1)
    product = response.json().get("product", {})
    product_id = product.get("id")
    title = product.get("title", "Unknown")
    return product_id, title


def get_buyers_from_db(product_id):
    """Query local DB for all unique purchaser emails for a product."""
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
    """Subscribe a single email to a Sendy list. Returns True on success."""
    response = requests.post(
        f"{SENDY_HOST}/subscribe",
        data={
            "api_key": SENDY_API_KEY,
            "list": list_id,
            "email": email,
            "boolean": "true"
        },
        timeout=10
    )
    return response.text.strip() == "1"


def main():
    parser = argparse.ArgumentParser(
        description="Sync pattern buyers to Sendy suppression list for E2/E3 exclusion"
    )
    parser.add_argument(
        "--handle", required=True,
        help="Shopify product handle (e.g. helen-stretch-pants-with-a-yoke-and-contoured-waistband-pdf-sewing-pattern)"
    )
    parser.add_argument(
        "--list-id", required=True,
        help="Sendy list ID to subscribe buyers to (create this list in Sendy first)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show buyer count without actually subscribing anyone"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("SINCLAIR PATTERNS - New Release Suppression")
    print("=" * 60)

    # Step 1 - resolve product
    print(f"\n[1/3] Looking up product '{args.handle}'...")
    product_id, title = get_product_id_from_handle(args.handle)
    print(f"  Product: {title}")
    print(f"  ID: {product_id}")

    # Step 2 - query buyers
    print(f"\n[2/3] Querying local DB for purchasers...")
    emails = get_buyers_from_db(product_id)
    print(f"  Found {len(emails)} unique buyers to suppress")

    if not emails:
        print("\n  No buyers found. Either no one has purchased yet, or the DB needs updating.")
        print("  Run: python3 update_recent_orders.py")
        sys.exit(0)

    if args.dry_run:
        print(f"\n  [DRY RUN] Would subscribe {len(emails)} emails to list {args.list_id}")
        for e in emails[:10]:
            print(f"    {e}")
        if len(emails) > 10:
            print(f"    ... and {len(emails) - 10} more")
        print("\n  Re-run without --dry-run to subscribe.")
        sys.exit(0)

    # Step 3 - subscribe
    print(f"\n[3/3] Subscribing to Sendy list '{args.list_id}'...")
    success = 0
    failed = 0
    errors = []

    for i, email in enumerate(emails, 1):
        ok = subscribe_to_sendy(email, args.list_id)
        if ok:
            success += 1
        else:
            failed += 1
            errors.append(email)

        if i % 50 == 0:
            print(f"  {i}/{len(emails)} processed...")
            time.sleep(0.5)  # gentle rate limiting

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"  Pattern:     {title}")
    print(f"  Subscribed:  {success}")
    print(f"  Failed:      {failed}")
    if errors:
        print(f"\n  Failed emails:")
        for e in errors:
            print(f"    {e}")
    print(f"\n  Next step: when sending E2/E3 in Sendy,")
    print(f"  exclude list ID '{args.list_id}' to suppress buyers.")
    print("=" * 60)


if __name__ == "__main__":
    main()
