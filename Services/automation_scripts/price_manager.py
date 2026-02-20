#!/usr/bin/env python3
"""
Shopify Price Manager
Manages weekly specials pricing via Shopify Admin API
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ShopifyPriceManager:
    def __init__(self):
        self.shop_url = "https://Sinclairp.myshopify.com"
        self.api_version = "2024-10"
        self.access_token = self.get_access_token()
        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

    def get_access_token(self):
        """Get Shopify Admin API access token"""
        api_key = os.getenv('SHOPIFY_API_KEY', 'YOUR_SHOPIFY_API_KEY')
        api_secret = os.getenv('SHOPIFY_API_SECRET', 'YOUR_SHOPIFY_SECRET')

        response = requests.post(
            f"{self.shop_url}/admin/oauth/access_token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": api_secret
            }
        )
        return response.json()['access_token']

    def get_product_by_handle(self, handle):
        """Get product details by handle"""
        url = f"{self.shop_url}/admin/api/{self.api_version}/products.json"
        params = {"handle": handle}

        response = requests.get(url, headers=self.headers, params=params)
        products = response.json().get('products', [])

        return products[0] if products else None

    def update_variant_price(self, variant_id, new_price, compare_at_price=None):
        """Update variant price and compare_at_price"""
        url = f"{self.shop_url}/admin/api/{self.api_version}/variants/{variant_id}.json"

        data = {
            "variant": {
                "id": variant_id,
                "price": str(new_price)
            }
        }

        if compare_at_price is not None:
            data["variant"]["compare_at_price"] = str(compare_at_price) if compare_at_price else None

        response = requests.put(url, headers=self.headers, json=data)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to update variant {variant_id}: {response.text}")

    def set_sale_price(self, handle, sale_price, original_price):
        """Set sale price for a product (sets compare_at_price to original)"""
        product = self.get_product_by_handle(handle)

        if not product:
            raise Exception(f"Product not found: {handle}")

        variant = product['variants'][0]
        variant_id = variant['id']

        print(f"Setting sale for {product['title']}")
        print(f"  Original: ${original_price} -> Sale: ${sale_price}")

        result = self.update_variant_price(
            variant_id=variant_id,
            new_price=sale_price,
            compare_at_price=original_price
        )

        print(f"  ✓ Updated successfully")
        return result

    def end_sale(self, handle, original_price):
        """End sale for a product (restore original price, clear compare_at_price)"""
        product = self.get_product_by_handle(handle)

        if not product:
            raise Exception(f"Product not found: {handle}")

        variant = product['variants'][0]
        variant_id = variant['id']

        print(f"Ending sale for {product['title']}")
        print(f"  Restoring to: ${original_price}")

        result = self.update_variant_price(
            variant_id=variant_id,
            new_price=original_price,
            compare_at_price=None  # Clear the compare price
        )

        print(f"  ✓ Sale ended successfully")
        return result

    def apply_weekly_specials(self, specials_config):
        """
        Apply weekly specials from configuration

        Args:
            specials_config: dict with format:
            {
                "patterns": [
                    {"handle": "macy-...", "original_price": 9.99, "sale_price": 7.99},
                    ...
                ],
                "start_date": "2026-02-02",
                "end_date": "2026-02-09"
            }
        """
        print(f"\n{'='*60}")
        print(f"APPLYING WEEKLY SPECIALS")
        print(f"Start: {specials_config['start_date']}")
        print(f"End: {specials_config['end_date']}")
        print(f"{'='*60}\n")

        results = []
        for pattern in specials_config['patterns']:
            try:
                result = self.set_sale_price(
                    handle=pattern['handle'],
                    sale_price=pattern['sale_price'],
                    original_price=pattern['original_price']
                )
                results.append({
                    "handle": pattern['handle'],
                    "status": "success",
                    "result": result
                })
            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append({
                    "handle": pattern['handle'],
                    "status": "error",
                    "error": str(e)
                })

        return results

    def end_weekly_specials(self, specials_config):
        """
        End weekly specials from configuration
        """
        print(f"\n{'='*60}")
        print(f"ENDING WEEKLY SPECIALS")
        print(f"{'='*60}\n")

        results = []
        for pattern in specials_config['patterns']:
            try:
                result = self.end_sale(
                    handle=pattern['handle'],
                    original_price=pattern['original_price']
                )
                results.append({
                    "handle": pattern['handle'],
                    "status": "success",
                    "result": result
                })
            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append({
                    "handle": pattern['handle'],
                    "status": "error",
                    "error": str(e)
                })

        return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python price_manager.py <action> <config_file>")
        print("Actions: start_sale | end_sale")
        print("Example: python price_manager.py start_sale config/2026-02-02-specials.json")
        sys.exit(1)

    action = sys.argv[1]
    config_file = sys.argv[2]

    # Load configuration
    with open(config_file, 'r') as f:
        config = json.load(f)

    manager = ShopifyPriceManager()

    if action == "start_sale":
        results = manager.apply_weekly_specials(config)
    elif action == "end_sale":
        results = manager.end_weekly_specials(config)
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = sum(1 for r in results if r['status'] == 'error')
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")

    if error_count > 0:
        print("\nErrors:")
        for r in results:
            if r['status'] == 'error':
                print(f"  {r['handle']}: {r['error']}")
