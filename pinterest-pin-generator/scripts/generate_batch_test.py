#!/usr/bin/env python3
"""
Generate multiple pins with a specific variant from different images
"""
import google.generativeai as genai
from PIL import Image
from pathlib import Path
import os
import sys
from dotenv import load_dotenv
import json
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_MODEL = os.getenv('GEMINI_API_MODEL', 'gemini-3-pro-image-preview')
genai.configure(api_key=GEMINI_API_KEY)

# Paths
BASE_DIR = Path(__file__).parent.parent
PROMPT_VARIANTS_DIR = BASE_DIR / 'prompt_variants'
SAMPLE_IMAGES_DIR = BASE_DIR / 'data' / 'sample_images'
OUTPUT_DIR = BASE_DIR / 'data' / 'pins_generated'

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_variant_config(variant_id):
    """Load variant configuration"""
    variant_dir = PROMPT_VARIANTS_DIR / variant_id
    config_path = variant_dir / 'config.json'
    prompt_path = variant_dir / 'image_prompt.txt'

    with open(config_path, 'r') as f:
        config = json.load(f)

    with open(prompt_path, 'r') as f:
        prompt_template = f.read()

    return config, prompt_template


def generate_pin_from_image(image_path, pattern_name, variant_id, config, prompt_template, garment_type, pin_number):
    """Generate a single Pinterest pin from an image"""

    print(f"\n{'='*60}")
    print(f"Pin {pin_number} - {image_path.name}")
    print(f"{'='*60}")

    # Load the image
    img = Image.open(image_path)

    # Replace template variables in prompt
    prompt = prompt_template.replace('{pattern_name}', pattern_name)
    prompt = prompt.replace('{garment_type}', garment_type)

    print(f"✓ Loaded image: {image_path.name}")
    print(f"⏳ Sending request to Gemini...")

    # Initialize model
    model = genai.GenerativeModel(GEMINI_API_MODEL)

    try:
        response = model.generate_content([prompt, img])

        # Check response parts
        for i, part in enumerate(response.parts):
            # Check if it's an image
            if hasattr(part, 'inline_data') and part.inline_data:
                # Create pattern/variant folder
                pattern_output_dir = OUTPUT_DIR / pattern_name / variant_id
                pattern_output_dir.mkdir(parents=True, exist_ok=True)

                # Save the image
                if hasattr(part.inline_data, 'data'):
                    output_filename = f"{pattern_name.lower()}_{variant_id}_{pin_number:03d}.png"
                    output_path = pattern_output_dir / output_filename

                    image_data = part.inline_data.data

                    with open(output_path, 'wb') as f:
                        f.write(image_data)

                    print(f"✅ Saved: {output_filename} ({len(image_data)} bytes)")

                    # Generate pattern slug for URL
                    pattern_slug = pattern_name.lower().replace(' ', '-')

                    # Save comprehensive metadata
                    metadata = {
                        "pattern_name": pattern_name,
                        "variant_id": variant_id,
                        "variant_name": config['variant_name'],
                        "garment_type": garment_type,
                        "source_image": image_path.name,
                        "pin_number": pin_number,
                        "pinterest_metadata": {
                            "title": config['pinterest_metadata_template']['title'].replace('{pattern_name}', pattern_name),
                            "description": config['pinterest_metadata_template']['description'].replace('{garment_type}', garment_type).replace('{pattern_name}', pattern_name),
                            "link": config['pinterest_metadata_template']['link'].replace('{pattern_slug}', pattern_slug).replace('{image_number}', f"{pin_number:03d}"),
                            "alt_text": config['pinterest_metadata_template']['alt_text'].replace('{pattern_name}', pattern_name).replace('{garment_type}', garment_type),
                            "keywords": [k.replace('{garment_type}', garment_type).replace('{pattern_name}', pattern_name) for k in config['pinterest_metadata_template']['keywords']],
                            "board_suggestions": config['pinterest_metadata_template'].get('board_suggestions', []),
                            "hashtags": config['pinterest_metadata_template']['hashtags'],
                            "seo_tags": [tag.replace('{pattern_name}', pattern_name).replace('{garment_type}', garment_type) for tag in config['pinterest_metadata_template'].get('seo_tags', [])]
                        }
                    }

                    metadata_path = pattern_output_dir / f"{pattern_name.lower()}_{variant_id}_{pin_number:03d}_metadata.json"
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=2)

                    return True

        print(f"⚠️  No image generated from this photo")
        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def generate_batch(pattern_name, variant_id, garment_type, count=5):
    """Generate multiple pins with one variant"""

    print("=" * 60)
    print(f"Batch Pin Generation - Variant {variant_id}")
    print("=" * 60)
    print(f"\nPattern: {pattern_name}")
    print(f"Variant: {variant_id}")
    print(f"Count: {count}")
    print(f"Garment Type: {garment_type}")

    # Load variant config and prompt
    config, prompt_template = load_variant_config(variant_id)
    print(f"\n✓ Loaded variant: {config['variant_name']}")

    # Get sample images
    sample_images = list(SAMPLE_IMAGES_DIR.glob("*.jpg")) + list(SAMPLE_IMAGES_DIR.glob("*.png"))
    sample_images = [img for img in sample_images if not img.name.startswith('.')]

    if not sample_images:
        print(f"\n❌ Error: No images found in {SAMPLE_IMAGES_DIR}")
        return 1

    # Randomly select requested count
    if len(sample_images) > count:
        sample_images = random.sample(sample_images, count)
    print(f"✓ Randomly selected {len(sample_images)} images to process")

    # Generate pins
    results = []
    for idx, img_path in enumerate(sample_images, 1):
        success = generate_pin_from_image(
            img_path,
            pattern_name,
            variant_id,
            config,
            prompt_template,
            garment_type,
            idx
        )
        results.append({'image': img_path.name, 'success': success})

    # Summary
    print("\n" + "=" * 60)
    print("BATCH COMPLETE")
    print("=" * 60)

    success_count = sum(1 for r in results if r['success'])
    print(f"\n✅ Successfully generated {success_count}/{len(results)} pins")
    print(f"📁 Saved to: {OUTPUT_DIR / pattern_name / variant_id}\n")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate batch of pins with one variant')
    parser.add_argument('--pattern', default='Mirabel', help='Pattern name (default: Mirabel)')
    parser.add_argument('--variant', default='A', choices=['A', 'B', 'C', 'D', 'E'], help='Variant to test (default: A)')
    parser.add_argument('--garment', default='top and dress', help='Garment type (default: top and dress)')
    parser.add_argument('--count', type=int, default=5, help='Number of pins to generate (default: 5)')

    args = parser.parse_args()

    sys.exit(generate_batch(args.pattern, args.variant, args.garment, args.count))
