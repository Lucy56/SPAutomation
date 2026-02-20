#!/usr/bin/env python3
"""
Sendy Connector Script
Manages newsletter campaigns via Sendy API
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SendyConnector:
    def __init__(self):
        self.api_key = os.getenv('SENDY_API_KEY')
        self.api_host = os.getenv('SENDY_API_HOST')
        self.from_email = os.getenv('SENDY_FROM_EMAIL')
        self.reply_to = os.getenv('SENDY_REPLY_TO')
        self.brand_id = os.getenv('SENDY_BRANDID')

        # Load default settings
        config_path = Path(__file__).parent.parent / 'Docs' / 'sendy_config.json'
        with open(config_path, 'r') as f:
            config = json.load(f)
            self.defaults = config['sendy_defaults']

    def create_campaign(self, metadata_file, html_file):
        """
        Create a campaign in Sendy

        Args:
            metadata_file: Path to campaign metadata JSON file
            html_file: Path to campaign HTML file

        Returns:
            dict: Response from Sendy API
        """
        # Load metadata
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)['campaign']

        # Load HTML content
        with open(html_file, 'r') as f:
            html_content = f.read()

        # Prepare API endpoint
        url = f"https://{self.api_host}/api/campaigns/create.php"

        # Prepare data for API
        data = {
            'api_key': self.api_key,
            'from_name': metadata.get('from_name', 'Sinclair Patterns'),
            'from_email': metadata.get('from_email', self.from_email),
            'reply_to': metadata.get('reply_to', self.reply_to),
            'title': metadata['title'],
            'subject': metadata['subject'],
            'html_text': html_content,
            'brand_id': metadata.get('brand_id', self.brand_id),
            'track_opens': metadata.get('track_opens', self.defaults['track_opens']),
            'track_clicks': metadata.get('track_clicks', self.defaults['track_clicks']),
            'send_campaign': metadata.get('send_campaign', self.defaults['send_campaign']),
        }

        # Add list_ids if send_campaign is 1, or if it's a draft with lists specified
        if 'list_ids' in metadata:
            data['list_ids'] = metadata['list_ids']

        # Add scheduling if specified
        if 'schedule_date_time' in metadata:
            data['schedule_date_time'] = metadata['schedule_date_time']
            if 'schedule_timezone' in metadata:
                data['schedule_timezone'] = metadata['schedule_timezone']

        # Make API request
        print(f"Creating campaign: {metadata['title']}")
        print(f"Subject: {metadata['subject']}")
        print(f"API URL: {url}")
        print(f"Track Opens: {data['track_opens']} (anonymous)")
        print(f"Track Clicks: {data['track_clicks']} (anonymous)")
        print(f"Send Campaign: {data['send_campaign']} (0=draft, 1=send)")
        print(f"Brand ID: {data['brand_id']}")
        print(f"Lists: {data.get('list_ids', 'Not specified')}")
        if 'schedule_date_time' in data:
            print(f"Scheduled For: {data['schedule_date_time']} ({data.get('schedule_timezone', 'No timezone specified')})")
        print("\nSending request to Sendy...")

        response = requests.post(url, data=data)

        return {
            'status_code': response.status_code,
            'response': response.text,
            'success': response.status_code == 200 and ('Campaign created' in response.text or 'Campaign scheduled' in response.text)
        }

    def get_lists(self):
        """Get all subscriber lists"""
        # This would require additional API implementation
        # Sendy doesn't have a dedicated API endpoint for listing all lists
        # But we have them in .env
        return os.getenv('SENDY_LISTS', '').split(',')


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python sendy_connector.py <metadata_json> <html_file>")
        print("Example: python sendy_connector.py ../Output/Newsletters/2026-01-19-WeeklySpecials-metadata.json ../Output/Newsletters/2026-01-19-WeeklySpecials.html")
        sys.exit(1)

    metadata_file = sys.argv[1]
    html_file = sys.argv[2]

    connector = SendyConnector()
    result = connector.create_campaign(metadata_file, html_file)

    print("\n" + "="*50)
    print("RESULT:")
    print("="*50)
    print(f"Status Code: {result['status_code']}")
    print(f"Response: {result['response']}")
    print(f"Success: {result['success']}")

    if result['success']:
        print("\n✓ Campaign created successfully in Sendy!")
    else:
        print("\n✗ Failed to create campaign")
        sys.exit(1)
