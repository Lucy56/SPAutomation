#!/usr/bin/env python3
"""
Test script to generate a single pin with a specific variant
"""
import google.generativeai as genai
from PIL import Image
from pathlib import Path
import os
import sys
from dotenv import load_dotenv
import json

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


def generate_pin(pattern_name, variant_id, garment_type="top and dress", image_path=None):
    """Generate a Pinterest pin"""

    print("=" * 60)
    print(f"Generating Pinterest Pin - Variant {variant_id}")
    print("=" * 60)

    # Load variant config and prompt
    config, prompt_template = load_variant_config(variant_id)

    print(f"\nVariant: {config['variant_name']}")
    print(f"Pattern: {pattern_name}")
    print(f"Garment: {garment_type}")

    # Find image to use
    if image_path:
        sample_image = Path(image_path)
    else:
        # Find first image in sample_images
        sample_images = list(SAMPLE_IMAGES_DIR.glob("*.jpg")) + list(SAMPLE_IMAGES_DIR.glob("*.png"))
        if not sample_images:
            print(f"\n❌ Error: No images found in {SAMPLE_IMAGES_DIR}")
            return 1
        sample_image = sample_images[0]

    if not sample_image.exists():
        print(f"\n❌ Error: Sample image not found at {sample_image}")
        return 1

    print(f"\n✓ Using image: {sample_image.name}")

    # Load the image
    img = Image.open(sample_image)

    # Replace template variables in prompt
    prompt = prompt_template.replace('{pattern_name}', pattern_name)
    prompt = prompt.replace('{garment_type}', garment_type)

    print("\n" + "-" * 60)
    print("PROMPT:")
    print("-" * 60)
    print(prompt)
    print("-" * 60)

    # Initialize model
    model = genai.GenerativeModel(GEMINI_API_MODEL)
    print(f"\n✓ Using model: {GEMINI_API_MODEL}")

    # Send to Gemini
    print("\n⏳ Sending request to Gemini...")
    try:
        response = model.generate_content([prompt, img])

        print("\n" + "=" * 60)
        print("GEMINI RESPONSE")
        print("=" * 60)

        # Check response parts
        print(f"\nNumber of parts in response: {len(response.parts)}")

        saved_count = 0
        for i, part in enumerate(response.parts):
            print(f"\n--- Part {i} ---")

            # Check if it's text
            if hasattr(part, 'text') and part.text:
                print(f"Text content: {part.text[:200]}...")

            # Check if it's an image
            if hasattr(part, 'inline_data') and part.inline_data:
                print(f"Has inline_data: Yes")
                print(f"MIME type: {part.inline_data.mime_type}")

                # Create pattern/variant folder
                pattern_output_dir = OUTPUT_DIR / pattern_name / variant_id
                pattern_output_dir.mkdir(parents=True, exist_ok=True)

                # Save the image
                if hasattr(part.inline_data, 'data'):
                    output_filename = f"{pattern_name.lower()}_{variant_id}_{i}.png"
                    output_path = pattern_output_dir / output_filename

                    try:
                        image_data = part.inline_data.data
                        print(f"Image data size: {len(image_data)} bytes")

                        with open(output_path, 'wb') as f:
                            f.write(image_data)
                        print(f"✅ Saved image to: {output_path}")
                        saved_count += 1

                        # Save metadata
                        metadata = {
                            "pattern_name": pattern_name,
                            "variant_id": variant_id,
                            "variant_name": config['variant_name'],
                            "garment_type": garment_type,
                            "source_image": str(sample_image),
                            "pinterest_metadata": {
                                "title": config['pinterest_metadata_template']['title'].replace('{pattern_name}', pattern_name),
                                "description": config['pinterest_metadata_template']['description'].replace('{garment_type}', garment_type),
                                "keywords": [k.replace('{garment_type}', garment_type) for k in config['pinterest_metadata_template']['keywords']],
                                "hashtags": config['pinterest_metadata_template']['hashtags']
                            }
                        }

                        metadata_path = pattern_output_dir / f"{pattern_name.lower()}_{variant_id}_{i}_metadata.json"
                        with open(metadata_path, 'w') as f:
                            json.dump(metadata, f, indent=2)
                        print(f"✅ Saved metadata to: {metadata_path}")

                    except Exception as e:
                        print(f"❌ Error saving image: {e}")
                        import traceback
                        traceback.print_exc()

        print("\n" + "=" * 60)
        if saved_count > 0:
            print(f"\n✅ SUCCESS! Generated {saved_count} Pinterest pin(s)")
            print(f"📁 Saved to: {pattern_output_dir}")
        else:
            print("\n⚠️  No images were generated. Response may be text-only.")
        print("=" * 60 + "\n")

        return 0 if saved_count > 0 else 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test pin generation with variant')
    parser.add_argument('--pattern', default='Mirabel', help='Pattern name (default: Mirabel)')
    parser.add_argument('--variant', default='A', choices=['A', 'B', 'C', 'D', 'E'], help='Variant to test (default: A)')
    parser.add_argument('--garment', default='top and dress', help='Garment type (default: top and dress)')
    parser.add_argument('--image', help='Path to specific image (default: first image in sample_images/)')

    args = parser.parse_args()

    sys.exit(generate_pin(args.pattern, args.variant, args.garment, args.image))
