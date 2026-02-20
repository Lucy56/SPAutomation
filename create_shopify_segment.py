#!/usr/bin/env python3
"""
Shopify Customer Segment Creator
Creates a customer segment using the Shopify GraphQL Admin API
"""

import os
import sys
import requests
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_shopify_token():
    """Get Shopify admin API access token using OAuth"""
    shop_url = os.getenv("SHOPIFY_SHOP_URL", "Sinclairp.myshopify.com")
    api_key = os.getenv("SHOPIFY_API_KEY", "YOUR_SHOPIFY_API_KEY")
    api_secret = os.getenv("SHOPIFY_API_SECRET", "YOUR_SHOPIFY_SECRET")

    # Ensure shop_url has https://
    if not shop_url.startswith("http"):
        shop_url = f"https://{shop_url}"

    response = requests.post(
        f"{shop_url}/admin/oauth/access_token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": api_secret
        }
    )

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Failed to get access token: {response.status_code} - {response.text}")


class ShopifySegmentCreator:
    def __init__(self, shop_name: str, access_token: str):
        """
        Initialize the Shopify API client

        Args:
            shop_name: Your Shopify shop name (e.g., 'your-store' from your-store.myshopify.com)
            access_token: Admin API access token
        """
        self.shop_name = shop_name
        self.access_token = access_token
        # Try 2025-01 API version for segment support
        self.api_url = f"https://{shop_name}.myshopify.com/admin/api/2025-01/graphql.json"

    def create_segment(self, name: str, query: str) -> Dict[str, Any]:
        """
        Create a customer segment in Shopify

        Args:
            name: Name of the segment
            query: Shopify search query (e.g., "product_id:9759576228080")

        Returns:
            Dictionary containing the API response
        """
        graphql_query = """
        mutation CreateCustomerSegment($name: String!, $query: String!) {
          segmentCreate(name: $name, query: $query) {
            segment {
              id
              name
              query
              creationDate
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        variables = {
            "name": name,
            "query": query
        }

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }

        payload = {
            "query": graphql_query,
            "variables": variables
        }

        print(f"\nDEBUG - API URL: {self.api_url}")
        print(f"DEBUG - Payload: {json.dumps(payload, indent=2)}\n")

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "status_code": getattr(e.response, 'status_code', None)
            }

    def list_segments(self) -> Dict[str, Any]:
        """
        List all segments to find the one to copy

        Returns:
            Dictionary containing the segments list
        """
        graphql_query = """
        query {
          segments(first: 50) {
            edges {
              node {
                id
                name
                query
                creationDate
              }
            }
          }
        }
        """

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }

        payload = {
            "query": graphql_query
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "status_code": getattr(e.response, 'status_code', None)
            }

    def get_segment(self, segment_id: str) -> Dict[str, Any]:
        """
        Retrieve a segment by ID to verify it was created

        Args:
            segment_id: The segment ID (e.g., "gid://shopify/Segment/123456")

        Returns:
            Dictionary containing the segment details
        """
        graphql_query = """
        query GetSegment($id: ID!) {
          segment(id: $id) {
            id
            name
            query
            creationDate
          }
        }
        """

        variables = {
            "id": segment_id
        }

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }

        payload = {
            "query": graphql_query,
            "variables": variables
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "status_code": getattr(e.response, 'status_code', None)
            }


def main():
    """Main function to create and test a segment"""

    # Get shop URL from environment
    shop_url = os.getenv("SHOPIFY_SHOP_URL", "Sinclairp.myshopify.com")

    # Extract shop name from URL
    shop_name = shop_url.replace(".myshopify.com", "").replace("https://", "").replace("http://", "")

    # Get access token via OAuth
    print("🔑 Getting Shopify access token...")
    try:
        access_token = get_shopify_token()
        print("✓ Token obtained")
    except Exception as e:
        print(f"❌ Failed to get access token: {e}")
        sys.exit(1)

    # Initialize the client
    client = ShopifySegmentCreator(shop_name, access_token)

    # Test segment configuration
    # NOTE: products_purchased filter with MATCHES is not yet supported via API
    # Use --name and --query arguments to test different queries
    segment_name = "test segment"
    segment_query = "email_subscription_status = 'SUBSCRIBED'"

    print(f"🚀 Creating segment: '{segment_name}'")
    print(f"📊 Query: {segment_query}")
    print()

    # Create the segment
    result = client.create_segment(segment_name, segment_query)

    # Check for errors
    if "error" in result:
        print(f"❌ API Error: {result['error']}")
        if result.get("status_code"):
            print(f"Status Code: {result['status_code']}")
        sys.exit(1)

    # Parse the response
    data = result.get("data", {})
    segment_create = data.get("segmentCreate", {})
    user_errors = segment_create.get("userErrors", [])
    segment = segment_create.get("segment")

    # Check for user errors
    if user_errors:
        print("❌ Segment creation failed with errors:")
        for error in user_errors:
            print(f"  - {error.get('field')}: {error.get('message')}")
        sys.exit(1)

    # Success!
    if segment:
        print("✅ Segment created successfully!")
        print(f"   ID: {segment.get('id')}")
        print(f"   Name: {segment.get('name')}")
        print(f"   Query: {segment.get('query')}")
        print(f"   Created: {segment.get('creationDate')}")
        print()

        # Verify by fetching the segment
        segment_id = segment.get('id')
        print(f"🔍 Verifying segment by fetching it...")
        verify_result = client.get_segment(segment_id)

        if "error" not in verify_result:
            verify_segment = verify_result.get("data", {}).get("segment")
            if verify_segment:
                print("✅ Verification successful!")
                print(f"   Segment '{verify_segment.get('name')}' is accessible")
            else:
                print("⚠️  Verification: Segment not found in response")
        else:
            print(f"⚠️  Verification failed: {verify_result.get('error')}")
    else:
        print("❌ Unexpected response format:")
        print(json.dumps(result, indent=2))
        sys.exit(1)


def main_custom(segment_name: str, segment_query: str):
    """Run with custom parameters"""
    shop_url = os.getenv("SHOPIFY_SHOP_URL", "Sinclairp.myshopify.com")
    shop_name = shop_url.replace(".myshopify.com", "").replace("https://", "").replace("http://", "")

    print("🔑 Getting Shopify access token...")
    try:
        access_token = get_shopify_token()
        print("✓ Token obtained")
    except Exception as e:
        print(f"❌ Failed to get access token: {e}")
        sys.exit(1)

    client = ShopifySegmentCreator(shop_name, access_token)

    print(f"🚀 Creating segment: '{segment_name}'")
    print(f"📊 Query: {segment_query}")
    print()

    result = client.create_segment(segment_name, segment_query)

    if "error" in result:
        print(f"❌ API Error: {result['error']}")
        if result.get("status_code"):
            print(f"Status Code: {result['status_code']}")
        sys.exit(1)

    data = result.get("data", {})
    segment_create = data.get("segmentCreate", {})
    user_errors = segment_create.get("userErrors", [])
    segment = segment_create.get("segment")

    if user_errors:
        print("❌ Segment creation failed with errors:")
        for error in user_errors:
            print(f"  - {error.get('field')}: {error.get('message')}")
        sys.exit(1)

    if segment:
        print("✅ Segment created successfully!")
        print(f"   ID: {segment.get('id')}")
        print(f"   Name: {segment.get('name')}")
        print(f"   Query: {segment.get('query')}")
        print(f"   Created: {segment.get('creationDate')}")



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Create a Shopify customer segment')
    parser.add_argument('--name', type=str, help='Segment name')
    parser.add_argument('--query', type=str, help='Segment query')

    args = parser.parse_args()

    # Override defaults if provided
    if args.name and args.query:
        main_custom(args.name, args.query)
    else:
        main()
