#!/usr/bin/env python3
"""
Practice creating Pinterest pins with existing sample images
Use this to refine prompts and test different styles
"""
import sys
from pathlib import Path
from src.services.pin_generator import PinGenerator
from src.config.settings import SAMPLE_IMAGES_DIR, OUTPUT_DIR
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    logger.info("=" * 60)
    logger.info("Pinterest Pin Practice - Using Sample Images")
    logger.info("=" * 60)

    # Get all sample images
    image_files = list(SAMPLE_IMAGES_DIR.glob("*.jpg")) + list(SAMPLE_IMAGES_DIR.glob("*.png"))

    if not image_files:
        logger.error("No sample images found in data/sample_images/")
        logger.info("Please add some images to data/sample_images/ first")
        return 1

    logger.info(f"\nFound {len(image_files)} sample images:")
    for img in image_files:
        logger.info(f"  - {img.name}")

    # Initialize pin generator
    pin_gen = PinGenerator()

    # Generate pins
    logger.info(f"\n{'='*60}")
    logger.info("Generating Pinterest Pins")
    logger.info(f"{'='*60}\n")

    results = []

    for i, img_path in enumerate(image_files, 1):
        logger.info(f"[{i}/{len(image_files)}] Processing: {img_path.name}")

        try:
            # Extract pattern name from filename
            pattern_name = img_path.stem.split('_')[0]

            # Generate pin with AI
            result = pin_gen.generate_pin(
                source_image_path=img_path,
                text_overlay=None,  # Let Gemini generate text
                pattern_name=pattern_name
            )

            logger.info(f"✅ SUCCESS!")
            logger.info(f"   Output: {result['image_path'].name}")
            logger.info(f"   Text Overlay: '{result['text_overlay']}'")
            logger.info(f"   Title: {result['metadata']['title']}")
            logger.info(f"   Hashtags: {', '.join(result['metadata']['hashtags'][:3])}")
            logger.info("")

            results.append(result)

        except Exception as e:
            logger.error(f"❌ FAILED: {e}\n")
            results.append({'success': False, 'image': img_path.name, 'error': str(e)})

    # Summary
    logger.info("=" * 60)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 60)

    success_count = sum(1 for r in results if r.get('image_path'))
    logger.info(f"\n✅ Successfully generated {success_count}/{len(results)} pins\n")

    logger.info("Generated Pins:")
    for i, result in enumerate(results, 1):
        if result.get('image_path'):
            logger.info(f"\n{i}. {result['image_path'].name}")
            logger.info(f"   Text: '{result['text_overlay']}'")
            logger.info(f"   Title: {result['metadata']['title']}")
            logger.info(f"   Description: {result['metadata']['description'][:100]}...")

    logger.info(f"\n📁 All pins saved to: {OUTPUT_DIR}")
    logger.info("=" * 60 + "\n")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
