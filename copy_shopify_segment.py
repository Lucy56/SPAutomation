#!/usr/bin/env python3
"""
Copy/Duplicate a Shopify Customer Segment
Reads an existing segment and creates a copy with a new name
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

load_dotenv()


def get_shopify_token():
    """Get Shopify admin API access token using OAuth"""
    shop_url = os.getenv("SHOPIFY_SHOP_URL", "Sinclairp.myshopify.com")
    api_key = os.getenv("SHOPIFY_API_KEY", "YOUR_SHOPIFY_API_KEY")
    api_secret = os.getenv("SHOPIFY_API_SECRET", "YOUR_SHOPIFY_SECRET")

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


def list_segments(shop_name, access_token):
    """List all segments"""
    api_url = f"https://{shop_name}.myshopify.com/admin/api/2025-01/graphql.json"

    query = """
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
        "X-Shopify-Access-Token": access_token
    }

    response = requests.post(api_url, headers=headers, json={"query": query})
    return response.json()


def get_segment(shop_name, access_token, segment_id):
    """Get a specific segment by ID"""
    api_url = f"https://{shop_name}.myshopify.com/admin/api/2025-01/graphql.json"

    query = """
    query GetSegment($id: ID!) {
      segment(id: $id) {
        id
        name
        query
        creationDate
      }
    }
    """

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }

    payload = {
        "query": query,
        "variables": {"id": segment_id}
    }

    response = requests.post(api_url, headers=headers, json=payload)
    return response.json()


def create_segment(shop_name, access_token, name, query):
    """Create a new segment"""
    api_url = f"https://{shop_name}.myshopify.com/admin/api/2025-01/graphql.json"

    mutation = """
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

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }

    payload = {
        "query": mutation,
        "variables": {
            "name": name,
            "query": query
        }
    }

    response = requests.post(api_url, headers=headers, json=payload)
    return response.json()


def main_with_args(args):
    """Main function with command line arguments"""
    shop_url = os.getenv("SHOPIFY_SHOP_URL", "Sinclairp.myshopify.com")
    shop_name = shop_url.replace(".myshopify.com", "").replace("https://", "").replace("http://", "")

    print("🔑 Getting Shopify access token...")
    try:
        access_token = get_shopify_token()
        print("✓ Token obtained\n")
    except Exception as e:
        print(f"❌ Failed to get access token: {e}")
        sys.exit(1)

    # List segments to find the one to copy
    print("📋 Fetching segments...")
    segments_result = list_segments(shop_name, access_token)

    if "errors" in segments_result or "error" in segments_result:
        print(f"❌ Error fetching segments: {segments_result}")
        sys.exit(1)

    segments = segments_result.get("data", {}).get("segments", {}).get("edges", [])

    if not segments:
        print("No segments found.")
        sys.exit(1)

    # Find the segment
    source_segment = None
    if args.segment_id:
        for edge in segments:
            if edge["node"]["id"] == args.segment_id:
                source_segment = edge["node"]
                break
        if not source_segment:
            print(f"❌ Segment with ID '{args.segment_id}' not found.")
            sys.exit(1)
    elif args.segment_name:
        for edge in segments:
            if edge["node"]["name"].lower() == args.segment_name.lower():
                source_segment = edge["node"]
                break
        if not source_segment:
            print(f"❌ Segment with name '{args.segment_name}' not found.")
            sys.exit(1)

    print(f"✓ Found segment: {source_segment['name']}")
    print(f"  Query: {source_segment['query']}\n")

    # Determine new name
    new_name = args.new_name if args.new_name else f"{source_segment['name']} (Copy)"

    # Create the copy
    print(f"🚀 Creating segment: '{new_name}'")
    print(f"📊 Query: {source_segment['query']}")

    result = create_segment(shop_name, access_token, new_name, source_segment['query'])

    # Check for errors
    if "error" in result:
        print(f"❌ API Error: {result['error']}")
        sys.exit(1)

    data = result.get("data", {})
    segment_create = data.get("segmentCreate", {})
    user_errors = segment_create.get("userErrors", [])
    segment = segment_create.get("segment")

    if user_errors:
        print("\n❌ Segment creation failed with errors:")
        for error in user_errors:
            print(f"  - {error.get('field')}: {error.get('message')}")
        sys.exit(1)

    if segment:
        print("\n✅ Segment copied successfully!")
        print(f"   ID: {segment.get('id')}")
        print(f"   Name: {segment.get('name')}")
        print(f"   Query: {segment.get('query')}")
        print(f"   Created: {segment.get('creationDate')}")
    else:
        print("❌ Unexpected response format:")
        print(json.dumps(result, indent=2))
        sys.exit(1)


def main():
    """Main function to copy a segment"""

    shop_url = os.getenv("SHOPIFY_SHOP_URL", "Sinclairp.myshopify.com")
    shop_name = shop_url.replace(".myshopify.com", "").replace("https://", "").replace("http://", "")

    print("🔑 Getting Shopify access token...")
    try:
        access_token = get_shopify_token()
        print("✓ Token obtained\n")
    except Exception as e:
        print(f"❌ Failed to get access token: {e}")
        sys.exit(1)

    # List all segments
    print("📋 Fetching segments...")
    segments_result = list_segments(shop_name, access_token)

    if "errors" in segments_result or "error" in segments_result:
        print(f"❌ Error fetching segments: {segments_result}")
        sys.exit(1)

    segments = segments_result.get("data", {}).get("segments", {}).get("edges", [])

    if not segments:
        print("No segments found.")
        sys.exit(1)

    # Display segments
    print("\nAvailable segments:")
    print("-" * 80)
    for i, edge in enumerate(segments, 1):
        seg = edge["node"]
        print(f"{i}. {seg['name']}")
        print(f"   ID: {seg['id']}")
        print(f"   Query: {seg['query']}")
        print(f"   Created: {seg['creationDate']}")
        print()

    # Ask user which segment to copy
    try:
        choice = int(input("Enter the number of the segment to copy: "))
        if choice < 1 or choice > len(segments):
            print("Invalid choice.")
            sys.exit(1)

        source_segment = segments[choice - 1]["node"]

    except (ValueError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(0)

    # Ask for new name
    new_name = input(f"\nEnter new name for the copied segment (default: '{source_segment['name']} (Copy)'): ").strip()
    if not new_name:
        new_name = f"{source_segment['name']} (Copy)"

    # Create the copy
    print(f"\n🚀 Creating segment: '{new_name}'")
    print(f"📊 Query: {source_segment['query']}")

    result = create_segment(shop_name, access_token, new_name, source_segment['query'])

    # Check for errors
    if "error" in result:
        print(f"❌ API Error: {result['error']}")
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
        print("\n✅ Segment copied successfully!")
        print(f"   ID: {segment.get('id')}")
        print(f"   Name: {segment.get('name')}")
        print(f"   Query: {segment.get('query')}")
        print(f"   Created: {segment.get('creationDate')}")
    else:
        print("❌ Unexpected response format:")
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Copy/duplicate a Shopify customer segment')
    parser.add_argument('--segment-id', type=str, help='Segment ID to copy (e.g., gid://shopify/Segment/123)')
    parser.add_argument('--segment-name', type=str, help='Name of segment to copy (searches by name)')
    parser.add_argument('--new-name', type=str, help='Name for the new segment')

    args = parser.parse_args()

    if args.segment_id or args.segment_name:
        main_with_args(args)
    else:
        main()
