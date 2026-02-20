#!/usr/bin/env python3
"""
Simple test without AI - just create pins with hardcoded text to verify image generation works
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from src.services.s3_service import S3Service
from src.config.settings import SAMPLE_PATTERNS, SAMPLE_IMAGES_DIR, OUTPUT_DIR, PIN_WIDTH, PIN_HEIGHT
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_simple_pin(source_path: Path, text: str, output_filename: str) -> Path:
    """Create a simple Pinterest pin with text overlay"""
    logger.info(f"Creating pin from {source_path.name} with text: '{text}'")

    # Open and resize source image
    img = Image.open(source_path)

    # Calculate crop to maintain 2:3 aspect ratio
    target_ratio = PIN_HEIGHT / PIN_WIDTH  # 1.5
    img_ratio = img.height / img.width

    if img_ratio > target_ratio:
        # Image is taller - crop height
        new_height = int(img.width * target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))
    else:
        # Image is wider - crop width
        new_width = int(img.height / target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))

    # Resize to Pinterest dimensions
    img = img.resize((PIN_WIDTH, PIN_HEIGHT), Image.Resampling.LANCZOS)

    # Add text overlay
    draw = ImageDraw.Draw(img)

    # Try to load a nice font
    font_size = 80
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()

    # Get text size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center text at top
    x = (PIN_WIDTH - text_width) // 2
    y = 80

    # Draw shadow
    for offset in range(1, 4):
        draw.text((x + offset, y + offset), text, font=font, fill=(0, 0, 0, 200))

    # Draw main text
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    # Save
    output_path = OUTPUT_DIR / output_filename
    img.save(output_path, 'JPEG', quality=95, optimize=True)

    logger.info(f"✅ Saved pin to: {output_path}")
    return output_path


def main():
    logger.info("=" * 60)
    logger.info("Simple Pinterest Pin Generator Test (No AI)")
    logger.info("=" * 60)

    # Download images
    s3 = S3Service()
    test_pattern = "CrewW"

    logger.info(f"\n[Step 1] Downloading {test_pattern} images from S3...")
    image_paths = s3.download_pattern_images(test_pattern, count=3)
    logger.info(f"Downloaded {len(image_paths)} images")

    # Sample text overlays
    sample_texts = [
        "New Pattern Alert",
        "Sew This Weekend",
        "Perfect Summer Dress",
    ]

    logger.info("\n[Step 2] Creating Pinterest pins...")
    results = []

    for i, (img_path, text) in enumerate(zip(image_paths, sample_texts), 1):
        try:
            output_filename = f"test_pin_{i}_{img_path.stem}.jpg"
            pin_path = create_simple_pin(img_path, text, output_filename)
            results.append({'success': True, 'path': pin_path, 'text': text})
        except Exception as e:
            logger.error(f"Failed to create pin {i}: {e}")
            results.append({'success': False, 'error': str(e)})

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)
    success_count = sum(1 for r in results if r.get('success'))
    logger.info(f"\n✅ Created {success_count}/{len(results)} pins successfully\n")

    for i, result in enumerate(results, 1):
        if result.get('success'):
            logger.info(f"Pin {i}: {result['path'].name}")
            logger.info(f"  Text: '{result['text']}'")
        else:
            logger.error(f"Pin {i}: FAILED - {result.get('error')}")

    logger.info(f"\n📁 Output directory: {OUTPUT_DIR}\n")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
