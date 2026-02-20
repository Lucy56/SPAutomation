#!/usr/bin/env python3
"""
Simple CLI to generate Pinterest pins

Usage:
    python generate_pin.py CrewW                           # Auto-generate text with Gemini
    python generate_pin.py CrewW "Sew This Weekend"        # Use custom text
    python generate_pin.py Mimosa --count 3                # Generate 3 pins
"""
import sys
import argparse
from pathlib import Path
from src.services.s3_service import S3Service
from src.services.pin_generator import PinGenerator
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Generate Pinterest pins for sewing patterns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_pin.py CrewW
  python generate_pin.py CrewW "Sew This Weekend"
  python generate_pin.py Mimosa --count 3
  python generate_pin.py CrewM "Easy Weekend Project" --count 2
        """
    )

    parser.add_argument('pattern_name', help='Name of the pattern (e.g., CrewW, Mimosa)')
    parser.add_argument('text_overlay', nargs='?', default=None,
                       help='Optional custom text overlay (auto-generated if not provided)')
    parser.add_argument('--count', type=int, default=1,
                       help='Number of pins to generate (default: 1)')

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info(f"Generating Pinterest Pins for: {args.pattern_name}")
    logger.info("=" * 60)

    # Initialize services
    s3 = S3Service()
    pin_gen = PinGenerator()

    # Download images from S3
    logger.info(f"\n[Step 1] Downloading {args.count} image(s) from S3...")
    try:
        image_paths = s3.download_pattern_images(args.pattern_name, count=args.count)

        if not image_paths:
            logger.error(f"No images found for pattern: {args.pattern_name}")
            logger.info(f"Available patterns in S3: CrewW, CrewM, Mimosa, etc.")
            return 1

        logger.info(f"✅ Downloaded {len(image_paths)} image(s)")
        for img in image_paths:
            logger.info(f"  - {img.name}")
    except Exception as e:
        logger.error(f"Failed to download images: {e}")
        return 1

    # Generate pins
    logger.info(f"\n[Step 2] Generating {len(image_paths)} Pinterest pin(s)...")
    results = []

    for i, img_path in enumerate(image_paths, 1):
        logger.info(f"\n--- Pin {i}/{len(image_paths)} ---")
        try:
            result = pin_gen.generate_pin(
                source_image_path=img_path,
                text_overlay=args.text_overlay,  # None if auto-generate
                pattern_name=args.pattern_name
            )
            results.append(result)

            logger.info(f"✅ Pin created: {result['image_path'].name}")
            logger.info(f"   Text: '{result['text_overlay']}'")
            logger.info(f"   Title: {result['metadata']['title']}")

        except Exception as e:
            logger.error(f"❌ Failed to generate pin: {e}")
            results.append({'success': False, 'error': str(e)})

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    success_count = sum(1 for r in results if r.get('image_path'))
    logger.info(f"\n✅ Successfully generated {success_count}/{len(results)} pins\n")

    for i, result in enumerate(results, 1):
        if result.get('image_path'):
            logger.info(f"Pin {i}:")
            logger.info(f"  File: {result['image_path'].name}")
            logger.info(f"  Text: '{result['text_overlay']}'")
            logger.info(f"  Title: {result['metadata']['title']}")
            logger.info(f"  Hashtags: {', '.join(result['metadata']['hashtags'][:3])}")
            logger.info("")

    logger.info(f"📁 All pins saved to: data/output/")
    logger.info("=" * 60 + "\n")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
