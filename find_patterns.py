#!/usr/bin/env python3
"""
Find Apollo and Lotte patterns in Shopify
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

shop_url = "https://Sinclairp.myshopify.com"
api_version = "2024-10"

# Get API credentials
api_key = os.getenv('SHOPIFY_API_KEY', 'YOUR_SHOPIFY_API_KEY')
api_secret = os.getenv('SHOPIFY_API_SECRET', 'YOUR_SHOPIFY_SECRET')

# Get access token
response = requests.post(
    f"{shop_url}/admin/oauth/access_token",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": api_secret
    }
)
access_token = response.json()['access_token']

headers = {
    "X-Shopify-Access-Token": access_token,
    "Content-Type": "application/json"
}

# Search for Apollo and Lotte patterns
search_terms = ["Apollo", "Lotte"]

for term in search_terms:
    print(f"\n=== Searching for {term} ===\n")

    url = f"{shop_url}/admin/api/{api_version}/products.json"
    params = {"title": term, "limit": 10}

    response = requests.get(url, headers=headers, params=params)
    products = response.json().get('products', [])

    if products:
        for product in products:
            print(f"Title: {product['title']}")
            print(f"Handle: {product['handle']}")
            print(f"URL: https://sinclairpatterns.com/products/{product['handle']}")

            # Get first variant for pricing
            if product['variants']:
                variant = product['variants'][0]
                print(f"Price: ${variant['price']}")
                if variant.get('compare_at_price'):
                    print(f"Compare at: ${variant['compare_at_price']}")

            # Get first image
            if product['images']:
                print(f"Image: {product['images'][0]['src']}")

            print(f"\nBody HTML:\n{product.get('body_html', 'No description')[:200]}...")
            print("\n" + "-"*50)
    else:
        print(f"No products found for '{term}'")

        # Try broader search
        print(f"\nTrying broader search (all products)...")
        response = requests.get(f"{shop_url}/admin/api/{api_version}/products.json",
                              headers=headers, params={"limit": 250})
        all_products = response.json().get('products', [])

        matching = [p for p in all_products if term.lower() in p['title'].lower()]
        if matching:
            print(f"\nFound {len(matching)} products with '{term}' in title:")
            for product in matching:
                print(f"  - {product['title']} (Handle: {product['handle']})")
        else:
            print(f"No products found with '{term}' in title")
