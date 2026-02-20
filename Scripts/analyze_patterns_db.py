#!/usr/bin/env python3
"""
Weekly Specials Analyzer - Database Version
Analyzes sales data from SQLite database to suggest weekly specials
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from db_schema import get_db_path

def load_recent_specials():
    """Load recently featured patterns to avoid repetition"""
    specials_file = Path(__file__).parent.parent / 'Docs' / 'weeklySpecials.json'
    recently_featured = set()
    if specials_file.exists():
        with open(specials_file, 'r') as f:
            data = json.load(f)
            for entry in data.get('weekly_specials_history', []):
                recently_featured.update(entry['patterns'])

    # Also load free patterns to exclude
    free_patterns_file = Path(__file__).parent.parent / 'Docs' / 'free_patterns_config.json'
    if free_patterns_file.exists():
        with open(free_patterns_file, 'r') as f:
            free_config = json.load(f)
            for pattern in free_config.get('free_patterns', []):
                # Add free pattern names to exclusion list
                recently_featured.add(pattern['name'])

    return set(recently_featured)

def get_top_sellers(days=90, limit=30):
    """Get top selling patterns in the last N days"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    query = """
        SELECT
            li.product_title,
            li.product_id,
            SUM(li.quantity) as units_sold,
            SUM(li.price * li.quantity) as revenue,
            COUNT(DISTINCT li.order_id) as num_orders
        FROM line_items li
        JOIN orders o ON li.order_id = o.order_id
        WHERE o.created_at >= ?
            AND o.financial_status = 'paid'
            AND li.price > 0
            AND li.product_title NOT LIKE '%free%'
            AND li.product_title NOT LIKE '%(Free)%'
        GROUP BY li.product_id, li.product_title
        ORDER BY units_sold DESC
        LIMIT ?
    """

    cursor.execute(query, (cutoff_date, limit))
    results = cursor.fetchall()
    conn.close()

    return [{
        'title': row[0],
        'product_id': row[1],
        'units_sold': row[2],
        'revenue': row[3],
        'num_orders': row[4],
        'category': 'recent_bestseller'
    } for row in results]

def get_historical_bestsellers(start_days_ago=730, end_days_ago=640, limit=30):
    """Get bestsellers from 2 years ago (same season)"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    start_date = (datetime.now() - timedelta(days=start_days_ago)).isoformat()
    end_date = (datetime.now() - timedelta(days=end_days_ago)).isoformat()

    query = """
        SELECT
            li.product_title,
            li.product_id,
            SUM(li.quantity) as units_sold,
            SUM(li.price * li.quantity) as revenue
        FROM line_items li
        JOIN orders o ON li.order_id = o.order_id
        WHERE o.created_at BETWEEN ? AND ?
            AND o.financial_status = 'paid'
            AND li.price > 0
            AND li.product_title NOT LIKE '%free%'
            AND li.product_title NOT LIKE '%(Free)%'
        GROUP BY li.product_id, li.product_title
        ORDER BY units_sold DESC
        LIMIT ?
    """

    cursor.execute(query, (start_date, end_date, limit))
    results = cursor.fetchall()
    conn.close()

    return [{
        'title': row[0],
        'product_id': row[1],
        'units_sold': row[2],
        'revenue': row[3],
        'category': 'historical_bestseller'
    } for row in results]

def get_underrated_patterns(days=90, min_sales=1, max_sales=10, limit=30):
    """Get patterns with low but steady sales"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    query = """
        SELECT
            li.product_title,
            li.product_id,
            SUM(li.quantity) as units_sold,
            SUM(li.price * li.quantity) as revenue
        FROM line_items li
        JOIN orders o ON li.order_id = o.order_id
        WHERE o.created_at >= ?
            AND o.financial_status = 'paid'
            AND li.price > 0
            AND li.product_title NOT LIKE '%free%'
            AND li.product_title NOT LIKE '%(Free)%'
        GROUP BY li.product_id, li.product_title
        HAVING units_sold BETWEEN ? AND ?
        ORDER BY units_sold DESC
        LIMIT ?
    """

    cursor.execute(query, (cutoff_date, min_sales, max_sales, limit))
    results = cursor.fetchall()
    conn.close()

    return [{
        'title': row[0],
        'product_id': row[1],
        'units_sold': row[2],
        'revenue': row[3],
        'category': 'underrated'
    } for row in results]

def find_frequently_bought_together(product_id, min_occurrences=2):
    """Find products frequently bought together with given product"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
        SELECT
            li2.product_title,
            li2.product_id,
            COUNT(*) as times_bought_together
        FROM line_items li1
        JOIN line_items li2 ON li1.order_id = li2.order_id
        WHERE li1.product_id = ?
            AND li2.product_id != ?
        GROUP BY li2.product_id, li2.product_title
        HAVING times_bought_together >= ?
        ORDER BY times_bought_together DESC
        LIMIT 10
    """

    cursor.execute(query, (product_id, product_id, min_occurrences))
    results = cursor.fetchall()
    conn.close()

    return [{
        'title': row[0],
        'product_id': row[1],
        'times_together': row[2]
    } for row in results]

def suggest_cohesive_sets(top_recent, historical, underrated, recent_specials):
    """Suggest 2-3 cohesive pattern sets based on criteria"""

    # Filter out recently featured patterns
    def filter_recent(patterns):
        return [p for p in patterns if p['title'] not in recent_specials]

    top_recent = filter_recent(top_recent)
    historical = filter_recent(historical)
    underrated = filter_recent(underrated)

    sets = []

    # SET 1: Top seller + complementary patterns
    if top_recent:
        bestseller = top_recent[0]
        companions = find_frequently_bought_together(bestseller['product_id'])

        set1_patterns = [bestseller]

        # Find historical or underrated companion
        for companion in companions:
            matching = [p for p in historical + underrated if p['product_id'] == companion['product_id']]
            if matching:
                set1_patterns.append(matching[0])
                break

        # Add an underrated pattern
        if len(set1_patterns) < 3 and underrated:
            set1_patterns.append(underrated[0])

        if len(set1_patterns) >= 2:
            sets.append({
                'name': 'Bestseller Bundle',
                'patterns': set1_patterns[:3],
                'reasoning': f"Built around current bestseller '{bestseller['title']}' with complementary patterns"
            })

    # SET 2: Historical + modern update
    if historical and top_recent:
        set2_patterns = [historical[0], top_recent[1] if len(top_recent) > 1 else top_recent[0]]
        if underrated:
            set2_patterns.append(underrated[1] if len(underrated) > 1 else underrated[0])

        sets.append({
            'name': 'Timeless Classics',
            'patterns': set2_patterns[:3],
            'reasoning': "Mix of proven historical bestseller with current popular pattern"
        })

    # SET 3: Underrated gems
    if len(underrated) >= 3:
        sets.append({
            'name': 'Hidden Gems',
            'patterns': underrated[:3],
            'reasoning': "Showcase quality patterns that deserve more attention"
        })

    return sets

if __name__ == '__main__':
    print("="*70)
    print("WEEKLY SPECIALS PATTERN ANALYZER (Database Version)")
    print("="*70)

    # Load recent specials to avoid repetition
    print("\n[1/6] Loading recent specials history...")
    recent_specials = load_recent_specials()
    if recent_specials:
        print(f"  Excluding {len(recent_specials)} recently featured patterns")

    # Get top sellers (last 3 months)
    print("\n[2/6] Analyzing top sellers (last 90 days)...")
    top_recent = get_top_sellers(days=90, limit=30)
    print(f"  Found {len(top_recent)} top sellers")

    # Get historical bestsellers
    print("\n[3/6] Analyzing historical bestsellers (2 years ago)...")
    historical = get_historical_bestsellers(limit=30)
    print(f"  Found {len(historical)} historical bestsellers")

    # Get underrated patterns
    print("\n[4/6] Finding underrated patterns...")
    underrated = get_underrated_patterns(days=90, min_sales=1, max_sales=10, limit=30)
    print(f"  Found {len(underrated)} underrated patterns")

    # Suggest sets
    print("\n[5/6] Creating cohesive pattern sets...")
    suggested_sets = suggest_cohesive_sets(top_recent, historical, underrated, recent_specials)

    # Display results
    print("\n[6/6] Analysis complete!")
    print("\n" + "="*70)
    print("SUGGESTED PATTERN SETS FOR WEEKLY SPECIALS")
    print("="*70)

    for i, pset in enumerate(suggested_sets, 1):
        print(f"\n{'='*70}")
        print(f"SET {i}: {pset['name']}")
        print(f"{'='*70}")
        print(f"Reasoning: {pset['reasoning']}\n")

        for j, pattern in enumerate(pset['patterns'], 1):
            print(f"{j}. {pattern['title']}")
            print(f"   Category: {pattern['category']}")
            print(f"   Units sold: {pattern.get('units_sold', 'N/A')}")
            print(f"   Revenue: ${pattern.get('revenue', 0):.2f}")
            print()

    # Save analysis
    output = {
        'analysis_date': datetime.now().isoformat(),
        'top_recent_sellers': top_recent[:15],
        'historical_bestsellers': historical[:15],
        'underrated_patterns': underrated[:15],
        'suggested_sets': suggested_sets,
        'excluded_patterns': list(recent_specials)
    }

    output_file = Path(__file__).parent.parent / 'Output' / 'weekly_specials_analysis_db.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Full analysis saved to: {output_file}")
    print("="*70)
