#!/usr/bin/env python3
"""
Analyze Shopify sales data and suggest weekly specials
"""

import os
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# Get Shopify access token (expires in 24 hours)
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

def fetch_all_orders(token, start_date, end_date):
    """Fetch all orders within date range"""
    shop_url = "https://Sinclairp.myshopify.com"
    headers = {"X-Shopify-Access-Token": token}

    all_orders = []
    url = f"{shop_url}/admin/api/2024-10/orders.json?status=any&limit=250&created_at_min={start_date}&created_at_max={end_date}"

    print(f"Fetching orders from {start_date} to {end_date}...")

    while url:
        response = requests.get(url, headers=headers)
        data = response.json()
        all_orders.extend(data.get('orders', []))

        # Check for pagination
        link_header = response.headers.get('Link', '')
        if 'rel="next"' in link_header:
            # Extract next URL from Link header
            next_url = link_header.split(';')[0].strip('<>')
            url = next_url
        else:
            url = None

    print(f"  → Fetched {len(all_orders)} orders")
    return all_orders

def analyze_product_sales(orders):
    """Analyze which products were sold and how many times"""
    product_sales = defaultdict(lambda: {'count': 0, 'revenue': 0, 'titles': set()})

    for order in orders:
        for item in order.get('line_items', []):
            product_id = item['product_id']
            product_title = item['title']
            quantity = item['quantity']
            price = float(item['price'])

            product_sales[product_id]['count'] += quantity
            product_sales[product_id]['revenue'] += price * quantity
            product_sales[product_id]['titles'].add(product_title)

    # Convert to list and add title
    results = []
    for product_id, data in product_sales.items():
        results.append({
            'product_id': product_id,
            'title': list(data['titles'])[0] if data['titles'] else 'Unknown',
            'units_sold': data['count'],
            'revenue': data['revenue']
        })

    return sorted(results, key=lambda x: x['units_sold'], reverse=True)

def load_recent_specials():
    """Load recently featured patterns to avoid repetition"""
    specials_file = Path(__file__).parent.parent / 'Docs' / 'weeklySpecials.json'
    if specials_file.exists():
        with open(specials_file, 'r') as f:
            data = json.load(f)
            recent = []
            for entry in data.get('weekly_specials_history', []):
                recent.extend(entry['patterns'])
            return recent
    return []

def suggest_pattern_sets(recent_sales, historical_sales, recent_specials):
    """Suggest pattern combinations based on criteria"""
    print("\n" + "="*70)
    print("PATTERN SELECTION ANALYSIS")
    print("="*70)

    # Filter out recently featured patterns
    print(f"\nRecently featured patterns (excluded): {', '.join(recent_specials)}")

    # Categorize patterns
    print("\n--- TOP SELLERS (Last 3 months) ---")
    for i, pattern in enumerate(recent_sales[:15], 1):
        print(f"{i}. {pattern['title']}: {pattern['units_sold']} units (${pattern['revenue']:.2f})")

    print("\n--- HISTORICAL BESTSELLERS (2 years ago) ---")
    for i, pattern in enumerate(historical_sales[:15], 1):
        print(f"{i}. {pattern['title']}: {pattern['units_sold']} units (${pattern['revenue']:.2f})")

    # Identify underrated patterns (sold but not top performers)
    print("\n--- UNDERRATED PATTERNS (Low sales but still active) ---")
    underrated = [p for p in recent_sales if 1 <= p['units_sold'] <= 10]
    for i, pattern in enumerate(underrated[:15], 1):
        print(f"{i}. {pattern['title']}: {pattern['units_sold']} units")

    return {
        'top_recent': recent_sales[:30],
        'top_historical': historical_sales[:30],
        'underrated': underrated[:30]
    }

if __name__ == '__main__':
    print("WEEKLY SPECIALS ANALYZER")
    print("="*70)

    # Get access token
    print("\n1. Getting Shopify access token...")
    token = get_shopify_token()
    print("   ✓ Token obtained")

    # Calculate date ranges
    today = datetime.now()
    three_months_ago = (today - timedelta(days=90)).strftime('%Y-%m-%d')
    two_years_ago_start = (today - timedelta(days=730)).strftime('%Y-%m-%d')
    two_years_ago_end = (today - timedelta(days=640)).strftime('%Y-%m-%d')

    # Fetch orders
    print("\n2. Fetching recent orders (last 3 months)...")
    recent_orders = fetch_all_orders(token, three_months_ago, today.strftime('%Y-%m-%d'))

    print("\n3. Fetching historical orders (2 years ago, same period)...")
    historical_orders = fetch_all_orders(token, two_years_ago_start, two_years_ago_end)

    # Analyze sales
    print("\n4. Analyzing product sales...")
    recent_sales = analyze_product_sales(recent_orders)
    historical_sales = analyze_product_sales(historical_orders)

    # Load recent specials
    print("\n5. Loading recent specials to avoid repetition...")
    recent_specials = load_recent_specials()

    # Suggest patterns
    categorized = suggest_pattern_sets(recent_sales, historical_sales, recent_specials)

    # Save analysis
    output_file = Path(__file__).parent.parent / 'Output' / 'weekly_specials_analysis.json'
    with open(output_file, 'w') as f:
        json.dump({
            'analysis_date': today.strftime('%Y-%m-%d'),
            'recent_sales': recent_sales,
            'historical_sales': historical_sales,
            'categorized': categorized,
            'recent_specials': recent_specials
        }, f, indent=2)

    print(f"\n✓ Analysis saved to: {output_file}")
    print("\nNext step: Review the data and select 3 cohesive patterns for the newsletter")
