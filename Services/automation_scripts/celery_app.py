#!/usr/bin/env python3
"""
Celery Application for Sinclair Patterns Automation
Handles scheduled tasks for pricing, newsletters, and social media
"""

from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Celery
app = Celery(
    'sinclair_automation',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    include=[
        'tasks.pricing_tasks',
        'tasks.newsletter_tasks',
        'tasks.social_media_tasks'  # Future: Pinterest, Facebook, IG
    ]
)

# Celery configuration
app.conf.update(
    timezone='Australia/Brisbane',  # Gold Coast, QLD
    enable_utc=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Celery Beat Schedule (cron-like scheduling)
app.conf.beat_schedule = {
    # Weekly Specials - Start Sale (Every Monday 12:00 AM AEST)
    'start-weekly-specials': {
        'task': 'tasks.pricing_tasks.start_weekly_sale',
        'schedule': crontab(hour=0, minute=0, day_of_week=1),  # Monday midnight
        'options': {
            'expires': 3600,  # Expire after 1 hour if not executed
        }
    },

    # Weekly Specials - End Sale (Every Sunday 11:59 PM AEST)
    'end-weekly-specials': {
        'task': 'tasks.pricing_tasks.end_weekly_sale',
        'schedule': crontab(hour=23, minute=59, day_of_week=0),  # Sunday 11:59 PM
        'options': {
            'expires': 3600,
        }
    },

    # Future: Send Newsletter (Every Monday 9:00 AM AEST)
    # 'send-weekly-newsletter': {
    #     'task': 'tasks.newsletter_tasks.send_weekly_newsletter',
    #     'schedule': crontab(hour=9, minute=0, day_of_week=1),
    # },

    # Future: Post to Pinterest (Every Monday 10:00 AM AEST)
    # 'post-pinterest-special': {
    #     'task': 'tasks.social_media_tasks.post_to_pinterest',
    #     'schedule': crontab(hour=10, minute=0, day_of_week=1),
    # },

    # Future: Post to Facebook/Instagram (Every Monday 11:00 AM AEST)
    # 'post-facebook-special': {
    #     'task': 'tasks.social_media_tasks.post_to_facebook',
    #     'schedule': crontab(hour=11, minute=0, day_of_week=1),
    # },
}

if __name__ == '__main__':
    app.start()
