#!/usr/bin/env python3
"""
Generate Pinterest pin for Mirabel pattern using custom prompt
Saves output to the main Output folder
"""
import google.generativeai as genai
from PIL import Image
import base64
from pathlib import Path
import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_MODEL = os.getenv('GEMINI_API_MODEL', 'gemini-3-pro-image-preview')
genai.configure(api_key=GEMINI_API_KEY)

# Paths
BASE_DIR = Path(__file__).parent.parent
SAMPLE_IMAGE = Path(__file__).parent / 'data' / 'sample_images' / 'sample_photo.jpg'
OUTPUT_DIR = BASE_DIR / 'Output'

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_mirabel_pin():
    """Generate Pinterest pin for Mirabel pattern with custom prompt"""

    print("=" * 60)
    print("Generating Pinterest Pin for Mirabel Pattern")
    print("=" * 60)

    # Check if sample image exists
    if not SAMPLE_IMAGE.exists():
        print(f"❌ Error: Sample image not found at {SAMPLE_IMAGE}")
        return 1

    print(f"\n✓ Using image: {SAMPLE_IMAGE}")
    print(f"✓ Output folder: {OUTPUT_DIR}")

    # Load the image
    img = Image.open(SAMPLE_IMAGE)

    # Custom prompt for Mirabel pattern
    prompt = """Using this photo make a Pinterest pin. Follow pallets rules, font colors and balance rules, margins and correct composition. Make sure that background colors and style complement the photo and make the garment pop. Remove the background, enhance the photo if needed. This pin is for a pdf sewing pattern Mirabel top and dress by Sinclair Patterns. Add call to action button.

Requirements:
- Remove or blur the background to make the garment stand out
- Use complementary colors that enhance the garment's blue and cream tones
- Follow Pinterest best practices (1000x1500px optimal)
- Add text overlay with pattern name "Mirabel Top & Dress"
- Include "Sinclair Patterns" branding
- Add a call-to-action button (e.g., "Get Pattern", "Shop Now", "Download PDF")
- Ensure proper margins and visual balance
- Use readable, professional fonts
- Make the design eye-catching for Pinterest feeds

Generate a complete, ready-to-use Pinterest pin image."""

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
            print(f"Type: {type(part)}")

            # Check if it's text
            if hasattr(part, 'text') and part.text:
                print(f"Text content: {part.text[:500]}...")

            # Check if it's an image
            if hasattr(part, 'inline_data') and part.inline_data:
                print(f"Has inline_data: Yes")
                print(f"MIME type: {part.inline_data.mime_type}")

                # Try to save the image
                if hasattr(part.inline_data, 'data'):
                    output_filename = f"mirabel_pinterest_pin_{i}.png"
                    output_path = OUTPUT_DIR / output_filename

                    try:
                        # The data is already bytes, not base64 encoded
                        image_data = part.inline_data.data
                        print(f"Image data size: {len(image_data)} bytes")

                        with open(output_path, 'wb') as f:
                            f.write(image_data)
                        print(f"✅ Saved image to: {output_path}")
                        saved_count += 1
                    except Exception as e:
                        print(f"❌ Error saving image: {e}")
                        import traceback
                        traceback.print_exc()

        print("\n" + "=" * 60)
        if saved_count > 0:
            print(f"\n✅ SUCCESS! Generated {saved_count} Pinterest pin(s)")
            print(f"📁 Saved to: {OUTPUT_DIR}")
        else:
            print("\n⚠️  No images were generated. Response may be text-only.")
            print("    Try using a different Gemini model or prompt.")
        print("=" * 60 + "\n")

        return 0 if saved_count > 0 else 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(generate_mirabel_pin())
