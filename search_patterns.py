#!/usr/bin/env python3
"""
Search for Apollo and Lotte patterns in Shopify
"""

import requests
import json

def get_shopify_token():
    """Get Shopify admin API access token"""
    shop_url = "https://Sinclairp.myshopify.com"
    api_key = "YOUR_SHOPIFY_API_KEY"
    api_secret = "YOUR_SHOPIFY_SECRET"

    response = requests.post(
        f"{shop_url}/admin/oauth/access_token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": api_secret
        }
    )
    return response.json()['access_token']

def fetch_all_products(token):
    """Fetch all products from Shopify"""
    shop_url = "https://Sinclairp.myshopify.com"
    headers = {"X-Shopify-Access-Token": token}

    all_products = []
    url = f"{shop_url}/admin/api/2024-10/products.json?limit=250"

    print("Fetching all products from Shopify...")

    while url:
        response = requests.get(url, headers=headers)
        data = response.json()
        products = data.get('products', [])
        all_products.extend(products)

        print(f"  Fetched {len(all_products)} products so far...")

        # Check for pagination
        link_header = response.headers.get('Link', '')
        if 'rel="next"' in link_header:
            next_link = [link.strip() for link in link_header.split(',') if 'rel="next"' in link][0]
            url = next_link.split(';')[0].strip('<>')
        else:
            url = None

    print(f"\n✓ Total products fetched: {len(all_products)}\n")
    return all_products

def search_for_patterns(products, search_terms):
    """Search for patterns containing search terms"""
    results = {}

    for term in search_terms:
        print(f"\n{'='*70}")
        print(f"Searching for: {term}")
        print('='*70)

        matches = [p for p in products if term.lower() in p['title'].lower()]

        if matches:
            results[term] = matches
            for product in matches:
                print(f"\n✓ FOUND: {product['title']}")
                print(f"  Handle: {product['handle']}")
                print(f"  URL: https://sinclairpatterns.com/products/{product['handle']}")

                if product['variants']:
                    variant = product['variants'][0]
                    print(f"  Price: ${variant['price']}")
                    if variant.get('compare_at_price'):
                        print(f"  Compare at: ${variant['compare_at_price']}")

                if product['images']:
                    print(f"  Main Image: {product['images'][0]['src']}")
                    print(f"  Total Images: {len(product['images'])}")

                # Show first 200 chars of description
                body = product.get('body_html', '').replace('<p>', '').replace('</p>', ' ').replace('<br>', ' ')
                if body:
                    print(f"  Description: {body[:200]}...")
        else:
            print(f"\n✗ No products found matching '{term}'")

            # Try partial matches
            partial_matches = [p for p in products if any(word.lower() in p['title'].lower() for word in term.split())]
            if partial_matches:
                print(f"\n  Possible related patterns:")
                for p in partial_matches[:5]:
                    print(f"    - {p['title']}")

    return results

if __name__ == "__main__":
    token = get_shopify_token()
    products = fetch_all_products(token)

    search_terms = ["Apollo", "Lotte"]
    results = search_for_patterns(products, search_terms)

    # Save results to JSON
    output = {}
    for term, matches in results.items():
        output[term] = [{
            'title': p['title'],
            'handle': p['handle'],
            'url': f"https://sinclairpatterns.com/products/{p['handle']}",
            'price': p['variants'][0]['price'] if p['variants'] else None,
            'image': p['images'][0]['src'] if p['images'] else None,
            'body_html': p.get('body_html', '')
        } for p in matches]

    with open('pattern_search_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n\n✓ Results saved to pattern_search_results.json")
