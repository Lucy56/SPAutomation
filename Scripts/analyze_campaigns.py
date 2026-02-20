#!/usr/bin/env python3
"""
Campaign Performance Analyzer
Analyzes UTM tracking data to measure campaign effectiveness
"""

import sqlite3
from datetime import datetime, timedelta
from db_schema import get_db_path

def get_campaign_performance(days=90):
    """Analyze performance of all campaigns"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    query = """
        SELECT
            COALESCE(utm_campaign, 'No Campaign') as campaign,
            COALESCE(utm_source, 'No Source') as source,
            COALESCE(utm_medium, 'No Medium') as medium,
            COUNT(DISTINCT order_id) as orders,
            SUM(total_price) as revenue,
            AVG(total_price) as avg_order_value,
            COUNT(DISTINCT customer_id) as customers
        FROM orders
        WHERE created_at >= ?
            AND financial_status = 'paid'
        GROUP BY utm_campaign, utm_source, utm_medium
        ORDER BY revenue DESC
    """

    cursor.execute(query, (cutoff_date,))
    results = cursor.fetchall()
    conn.close()

    return [{
        'campaign': row[0],
        'source': row[1],
        'medium': row[2],
        'orders': row[3],
        'revenue': row[4],
        'avg_order_value': row[5],
        'customers': row[6]
    } for row in results]

def get_weekly_specials_performance():
    """Analyze performance of weekly specials campaigns"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
        SELECT
            utm_campaign,
            DATE(created_at) as date,
            COUNT(DISTINCT order_id) as orders,
            SUM(total_price) as revenue,
            COUNT(DISTINCT customer_id) as customers
        FROM orders
        WHERE utm_campaign LIKE '%weekly%'
            AND financial_status = 'paid'
        GROUP BY utm_campaign, DATE(created_at)
        ORDER BY created_at DESC
    """

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    return [{
        'campaign': row[0],
        'date': row[1],
        'orders': row[2],
        'revenue': row[3],
        'customers': row[4]
    } for row in results]

def get_geographic_breakdown(days=90):
    """Analyze sales by country"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    query = """
        SELECT
            COALESCE(country, 'Unknown') as country,
            COUNT(DISTINCT order_id) as orders,
            SUM(total_price) as revenue,
            AVG(total_price) as avg_order_value,
            COUNT(DISTINCT customer_id) as customers
        FROM orders
        WHERE created_at >= ?
            AND financial_status = 'paid'
        GROUP BY country
        ORDER BY revenue DESC
    """

    cursor.execute(query, (cutoff_date,))
    results = cursor.fetchall()
    conn.close()

    return [{
        'country': row[0],
        'orders': row[1],
        'revenue': row[2],
        'avg_order_value': row[3],
        'customers': row[4]
    } for row in results]

def get_top_products_by_campaign(campaign_name):
    """Get top selling products for a specific campaign"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
        SELECT
            li.product_title,
            SUM(li.quantity) as units_sold,
            SUM(li.price * li.quantity) as revenue
        FROM line_items li
        JOIN orders o ON li.order_id = o.order_id
        WHERE o.utm_campaign = ?
            AND o.financial_status = 'paid'
        GROUP BY li.product_title
        ORDER BY units_sold DESC
        LIMIT 20
    """

    cursor.execute(query, (campaign_name,))
    results = cursor.fetchall()
    conn.close()

    return [{
        'title': row[0],
        'units_sold': row[1],
        'revenue': row[2]
    } for row in results]

if __name__ == '__main__':
    print("="*70)
    print("CAMPAIGN PERFORMANCE ANALYZER")
    print("="*70)

    # Overall campaign performance
    print("\n[1/4] Analyzing campaign performance (last 90 days)...")
    campaigns = get_campaign_performance(days=90)

    print("\n" + "="*70)
    print("TOP PERFORMING CAMPAIGNS")
    print("="*70)
    print(f"{'Campaign':<30} {'Source':<15} {'Orders':<8} {'Revenue':<12} {'AOV':<10}")
    print("-"*70)

    for campaign in campaigns[:20]:
        print(f"{campaign['campaign'][:29]:<30} "
              f"{campaign['source'][:14]:<15} "
              f"{campaign['orders']:<8} "
              f"${campaign['revenue']:<11,.2f} "
              f"${campaign['avg_order_value']:<9,.2f}")

    # Weekly specials performance
    print("\n[2/4] Analyzing weekly specials performance...")
    weekly_specials = get_weekly_specials_performance()

    if weekly_specials:
        print("\n" + "="*70)
        print("WEEKLY SPECIALS PERFORMANCE")
        print("="*70)
        for special in weekly_specials[:10]:
            print(f"\nCampaign: {special['campaign']}")
            print(f"  Date: {special['date']}")
            print(f"  Orders: {special['orders']}")
            print(f"  Revenue: ${special['revenue']:.2f}")
            print(f"  Customers: {special['customers']}")

    # Geographic breakdown
    print("\n[3/4] Analyzing geographic performance...")
    countries = get_geographic_breakdown(days=90)

    print("\n" + "="*70)
    print("SALES BY COUNTRY")
    print("="*70)
    print(f"{'Country':<20} {'Orders':<10} {'Revenue':<15} {'AOV':<10}")
    print("-"*70)

    for country in countries[:15]:
        print(f"{country['country']:<20} "
              f"{country['orders']:<10} "
              f"${country['revenue']:<14,.2f} "
              f"${country['avg_order_value']:<9,.2f}")

    print("\n[4/4] Analysis complete!")
    print("="*70)
