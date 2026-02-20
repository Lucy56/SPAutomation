#!/usr/bin/env python3
"""
Pricing Tasks for Celery
Manages weekly specials pricing automation
"""

from celery import Task
from celery_app import app
import json
import os
from pathlib import Path
from price_manager import ShopifyPriceManager


@app.task(bind=True, name='tasks.pricing_tasks.start_weekly_sale', max_retries=3)
def start_weekly_sale(self):
    """
    Start weekly sale pricing
    Reads the latest weekly specials config and applies sale prices
    """
    try:
        # Find the latest weekly specials config
        config_dir = Path(__file__).parent.parent / 'config'
        configs = sorted(config_dir.glob('*-specials.json'), reverse=True)

        if not configs:
            raise Exception("No weekly specials config found")

        latest_config = configs[0]

        print(f"Loading config: {latest_config.name}")

        with open(latest_config, 'r') as f:
            config = json.load(f)

        # Apply sale prices
        manager = ShopifyPriceManager()
        results = manager.apply_weekly_specials(config)

        # Check for errors
        errors = [r for r in results if r['status'] == 'error']
        if errors:
            raise Exception(f"Failed to update {len(errors)} products: {errors}")

        return {
            'status': 'success',
            'config_file': latest_config.name,
            'patterns_updated': len(results),
            'results': results
        }

    except Exception as exc:
        # Retry with exponential backoff: 1min, 5min, 15min
        raise self.retry(exc=exc, countdown=60 * (5 ** self.request.retries))


@app.task(bind=True, name='tasks.pricing_tasks.end_weekly_sale', max_retries=3)
def end_weekly_sale(self):
    """
    End weekly sale pricing
    Restores original prices and clears compare_at_price
    """
    try:
        # Find the latest weekly specials config
        config_dir = Path(__file__).parent.parent / 'config'
        configs = sorted(config_dir.glob('*-specials.json'), reverse=True)

        if not configs:
            raise Exception("No weekly specials config found")

        latest_config = configs[0]

        print(f"Loading config: {latest_config.name}")

        with open(latest_config, 'r') as f:
            config = json.load(f)

        # End sale
        manager = ShopifyPriceManager()
        results = manager.end_weekly_specials(config)

        # Check for errors
        errors = [r for r in results if r['status'] == 'error']
        if errors:
            raise Exception(f"Failed to update {len(errors)} products: {errors}")

        return {
            'status': 'success',
            'config_file': latest_config.name,
            'patterns_updated': len(results),
            'results': results
        }

    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (5 ** self.request.retries))


@app.task(name='tasks.pricing_tasks.manual_price_update')
def manual_price_update(handle, sale_price, original_price):
    """
    Manual task to update a single product price
    Useful for testing or one-off updates
    """
    manager = ShopifyPriceManager()
    result = manager.set_sale_price(
        handle=handle,
        sale_price=sale_price,
        original_price=original_price
    )

    return {
        'status': 'success',
        'handle': handle,
        'result': result
    }
