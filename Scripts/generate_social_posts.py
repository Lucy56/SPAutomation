#!/usr/bin/env python3
"""
Generate social media posts from Sinclair Patterns product links

Usage:
    python generate_social_posts.py https://sinclairpatterns.com/products/apollo-knit-colorblocked-hoodie-for-men-pdf
"""

import os
import sys
import requests
import re
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class SocialMediaPostGenerator:
    """Generate social media posts for Sinclair Patterns products"""

    def __init__(self):
        self.shop_url = f"https://{os.getenv('SHOPIFY_SHOP_URL')}"
        self.api_key = os.getenv('SHOPIFY_API_KEY')
        self.api_secret = os.getenv('SHOPIFY_API_SECRET')
        self.access_token = None

    def authenticate(self):
        """Authenticate with Shopify API"""
        response = requests.post(
            f"{self.shop_url}/admin/oauth/access_token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret
            }
        )

        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            return True
        else:
            print(f"Authentication failed: {response.status_code}")
            return False

    def extract_handle_from_url(self, url: str) -> Optional[str]:
        """Extract product handle from Sinclair Patterns URL"""
        # Match URLs like: https://sinclairpatterns.com/products/apollo-knit-colorblocked-hoodie-for-men-pdf
        match = re.search(r'/products/([a-z0-9-]+)', url)
        if match:
            return match.group(1)
        return None

    def fetch_product_by_handle(self, handle: str) -> Optional[Dict]:
        """Fetch product data from Shopify by handle"""
        if not self.access_token:
            if not self.authenticate():
                return None

        headers = {"X-Shopify-Access-Token": self.access_token}
        url = f"{self.shop_url}/admin/api/2024-10/products.json?handle={handle}"

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            products = response.json().get('products', [])
            if products:
                return products[0]

        return None

    def clean_html(self, html_text: str) -> str:
        """Clean HTML tags from text"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_text)
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_key_features(self, product: Dict) -> Dict:
        """Extract key features from product data"""
        title = product.get('title', '')
        body_html = product.get('body_html', '')
        tags = product.get('tags', '').split(', ')

        # Extract price info
        price = None
        compare_price = None
        if product.get('variants'):
            variant = product['variants'][0]
            price = float(variant.get('price', 0))
            compare_price = variant.get('compare_at_price')
            if compare_price:
                compare_price = float(compare_price)

        # Extract main image
        main_image = None
        if product.get('images'):
            main_image = product['images'][0]['src']

        # Extract product type and target audience from title/tags
        product_type = product.get('product_type', '')

        # Clean description
        description = self.clean_html(body_html)

        # Extract size range from description
        size_match = re.search(r'(XS-\w+|US\d+-US\d+)', description)
        size_range = size_match.group(1) if size_match else ''

        return {
            'title': title,
            'description': description,
            'product_type': product_type,
            'tags': tags,
            'price': price,
            'compare_price': compare_price,
            'main_image': main_image,
            'size_range': size_range,
            'handle': product.get('handle', '')
        }

    def generate_facebook_group_post(self, features: Dict) -> str:
        """Generate Facebook Group post with giveaway announcement"""
        title = features['title']
        product_url = f"https://sinclairpatterns.com/products/{features['handle']}"
        price = features['price']
        compare_price = features['compare_price']
        size_range = features['size_range']

        # Calculate discount if applicable
        discount_text = ""
        if compare_price and compare_price > price:
            discount_pct = int(((compare_price - price) / compare_price) * 100)
            discount_text = f"🎉 NOW {discount_pct}% OFF! Was ${compare_price:.2f}, now just ${price:.2f}! "
        elif price:
            discount_text = f"Only ${price:.2f}! "

        post = f"""🎁 GIVEAWAY ALERT! 🎁

We're giving away the {title}!

{discount_text}This amazing pattern is perfect for creating your next handmade wardrobe staple.

{f'Available in sizes: {size_range}' if size_range else ''}

🌟 HOW TO ENTER:
1️⃣ Like this post
2️⃣ Comment below with your favorite sewing project
3️⃣ Tag a sewing friend who would love this pattern!

Winner will be announced in 48 hours! Good luck everyone! 🍀

Want it now? Grab it here: {product_url}

#SinclairPatterns #SewingGiveaway #PDFSewingPattern #SewingCommunity #Giveaway
"""
        return post

    def generate_instagram_post(self, features: Dict, use_ai: bool = False) -> str:
        """Generate Instagram post with hashtags"""
        title = features['title']
        product_type = features['product_type']
        tags = features['tags']
        product_url = f"https://sinclairpatterns.com/products/{features['handle']}"

        # Generate hashtags
        if use_ai:
            hashtags = self._generate_ai_hashtags(features)
        else:
            hashtags = self._generate_default_hashtags(features)

        # Create engaging caption
        caption = f"""✨ New Pattern Alert! ✨

Introducing our {title}!

Perfect for sewists who love creating unique, handmade pieces that fit perfectly and showcase their personal style.

💫 Link in bio or DM us for the pattern link!

{hashtags}
"""
        return caption

    def _generate_default_hashtags(self, features: Dict) -> str:
        """Generate default hashtags based on product features"""
        base_tags = [
            '#SinclairPatterns',
            '#SewingPattern',
            '#PDFPattern',
            '#SewYourOwnClothes',
            '#HandmadeWardrobe'
        ]

        # Add product-specific tags
        product_type = features['product_type'].lower()
        tags = features['tags']

        additional_tags = []

        # Product type tags
        if 'dress' in product_type or 'dress' in tags:
            additional_tags.extend(['#DressPattern', '#SewADress'])
        if 'hoodie' in product_type or 'hoodie' in tags:
            additional_tags.extend(['#HoodiePattern', '#CasualSewing'])
        if 'top' in product_type or 'tops' in tags:
            additional_tags.extend(['#TopPattern', '#SewTops'])

        # Fabric type tags
        if 'knit' in tags or 'knits' in tags:
            additional_tags.extend(['#KnitSewing', '#SewingKnits'])
        if 'woven' in tags:
            additional_tags.extend(['#WovenFabric'])

        # Skill level tags
        additional_tags.extend(['#SewingCommunity', '#ISewMyOwnClothes', '#SewistsOfInstagram'])

        # Gender tags
        if 'men' in tags:
            additional_tags.append('#MensSewing')
        if 'women' in tags:
            additional_tags.append('#WomensSewing')

        # Combine and limit to 30 hashtags (Instagram limit)
        all_tags = base_tags + additional_tags
        return ' '.join(all_tags[:30])

    def _generate_ai_hashtags(self, features: Dict) -> str:
        """Generate AI-powered hashtags (placeholder for future AI integration)"""
        # TODO: Integrate with Gemini or Claude API
        # For now, return default hashtags
        return self._generate_default_hashtags(features)

    def generate_facebook_page_post(self, features: Dict) -> str:
        """Generate professional Facebook Page post"""
        title = features['title']
        description = features['description']
        product_url = f"https://sinclairpatterns.com/products/{features['handle']}"
        price = features['price']
        size_range = features['size_range']

        # Extract first meaningful paragraph from description
        paragraphs = description.split('.')
        intro = '. '.join(paragraphs[:2]) + '.' if len(paragraphs) > 1 else description[:200]

        post = f"""✨ {title} ✨

{intro}

{f'📏 Available in sizes: {size_range}' if size_range else ''}
{f'💰 Just ${price:.2f}' if price else ''}

This PDF pattern includes:
• Detailed step-by-step instructions with photos
• Multiple size options with different height ranges
• Both A4/Letter and A0/Copyshop formats
• Projector file for easy printing
• Full email and Facebook group support

Perfect for sewists of all skill levels who want to create professional-quality garments that fit perfectly!

🛍️ Get your pattern now: {product_url}

Have questions? Drop them in the comments below! 💬

#SinclairPatterns #SewingPattern #PDFSewingPattern #HandmadeClothing #SewingCommunity
"""
        return post

    def generate_all_posts(self, product_url: str, use_ai: bool = False) -> Dict[str, str]:
        """Generate all social media posts for a product URL"""
        # Extract handle
        handle = self.extract_handle_from_url(product_url)
        if not handle:
            return {'error': 'Could not extract product handle from URL'}

        # Fetch product data
        product = self.fetch_product_by_handle(handle)
        if not product:
            return {'error': f'Could not fetch product with handle: {handle}'}

        # Extract features
        features = self.extract_key_features(product)

        # Generate posts
        return {
            'product_title': features['title'],
            'product_url': f"https://sinclairpatterns.com/products/{handle}",
            'facebook_group': self.generate_facebook_group_post(features),
            'instagram': self.generate_instagram_post(features, use_ai),
            'facebook_page': self.generate_facebook_page_post(features)
        }


def main():
    """Main function to run the script"""
    if len(sys.argv) < 2:
        print("Usage: python generate_social_posts.py <product_url>")
        print("Example: python generate_social_posts.py https://sinclairpatterns.com/products/apollo-knit-colorblocked-hoodie-for-men-pdf")
        sys.exit(1)

    product_url = sys.argv[1]
    use_ai = '--ai' in sys.argv

    generator = SocialMediaPostGenerator()
    posts = generator.generate_all_posts(product_url, use_ai)

    if 'error' in posts:
        print(f"Error: {posts['error']}")
        sys.exit(1)

    # Display results
    print("=" * 80)
    print(f"SOCIAL MEDIA POSTS FOR: {posts['product_title']}")
    print(f"URL: {posts['product_url']}")
    print("=" * 80)

    print("\n" + "=" * 80)
    print("FACEBOOK GROUP POST (GIVEAWAY)")
    print("=" * 80)
    print(posts['facebook_group'])

    print("\n" + "=" * 80)
    print("INSTAGRAM POST")
    print("=" * 80)
    print(posts['instagram'])

    print("\n" + "=" * 80)
    print("FACEBOOK PAGE POST")
    print("=" * 80)
    print(posts['facebook_page'])

    # Save to file
    output_dir = Path(__file__).parent.parent / 'Output'
    output_dir.mkdir(exist_ok=True)

    handle = generator.extract_handle_from_url(product_url)
    output_file = output_dir / f"social_posts_{handle}.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"SOCIAL MEDIA POSTS FOR: {posts['product_title']}\n")
        f.write(f"URL: {posts['product_url']}\n")
        f.write("=" * 80 + "\n\n")

        f.write("FACEBOOK GROUP POST (GIVEAWAY)\n")
        f.write("=" * 80 + "\n")
        f.write(posts['facebook_group'] + "\n\n")

        f.write("INSTAGRAM POST\n")
        f.write("=" * 80 + "\n")
        f.write(posts['instagram'] + "\n\n")

        f.write("FACEBOOK PAGE POST\n")
        f.write("=" * 80 + "\n")
        f.write(posts['facebook_page'] + "\n")

    print("\n" + "=" * 80)
    print(f"✓ Posts saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
