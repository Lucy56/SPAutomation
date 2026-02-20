#!/usr/bin/env python3
"""
Pinterest Pin Generator - Main entry point

Test the pin generation system with sample images
"""
import sys
from pathlib import Path
from src.services.s3_service import S3Service
from src.services.gemini_service import GeminiService
from src.services.pin_generator import PinGenerator
from src.config.settings import SAMPLE_PATTERNS, SAMPLE_IMAGES_DIR, OUTPUT_DIR
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Main execution function"""
    logger.info("=" * 60)
    logger.info("Pinterest Pin Generator - Test Run")
    logger.info("=" * 60)

    # Initialize services
    s3 = S3Service()
    pin_gen = PinGenerator()

    # Test with first pattern
    test_pattern = SAMPLE_PATTERNS[0] if SAMPLE_PATTERNS else "CrewW"
    logger.info(f"\nTesting with pattern: {test_pattern}")

    # Step 1: Download sample images from S3
    logger.info("\n[Step 1] Downloading sample images from S3...")
    try:
        image_paths = s3.download_pattern_images(test_pattern, count=5)
        logger.info(f"Downloaded {len(image_paths)} images")
        for path in image_paths:
            logger.info(f"  - {path.name}")
    except Exception as e:
        logger.error(f"Failed to download images: {e}")
        logger.info("Checking for existing images in sample directory...")
        image_paths = list(SAMPLE_IMAGES_DIR.glob("*.jpg")) + list(SAMPLE_IMAGES_DIR.glob("*.png"))
        if not image_paths:
            logger.error("No images found. Please add images to data/sample_images/ or fix S3 credentials")
            return 1

    if not image_paths:
        logger.error("No images to process")
        return 1

    # Step 2: Generate pins with Gemini
    logger.info(f"\n[Step 2] Generating Pinterest pins with Gemini...")
    results = pin_gen.batch_generate(image_paths[:5], pattern_name=test_pattern)

    # Step 3: Display results
    logger.info("\n" + "=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)

    success_count = sum(1 for r in results if r.get('success'))
    logger.info(f"\nGenerated {success_count}/{len(results)} pins successfully")

    for i, result in enumerate(results, 1):
        if result.get('success'):
            logger.info(f"\n--- Pin {i} ---")
            logger.info(f"Output: {result['image_path'].name}")
            logger.info(f"Text Overlay: {result['text_overlay']}")

            metadata = result.get('metadata', {})
            if 'title' in metadata:
                logger.info(f"Title: {metadata['title']}")
                logger.info(f"Description: {metadata['description'][:100]}...")
                logger.info(f"Hashtags: {', '.join(metadata.get('hashtags', []))}")
        else:
            logger.error(f"\n--- Pin {i} FAILED ---")
            logger.error(f"Error: {result.get('error')}")

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"{'=' * 60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
