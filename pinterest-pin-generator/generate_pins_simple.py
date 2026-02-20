#!/usr/bin/env python3
"""
Simplified Pinterest Pin Generator using Gemini Image Generation
Single prompt - generate high-engagement pins directly
"""
import sys
from pathlib import Path
import google.generativeai as genai
from PIL import Image
import requests
from io import BytesIO
from src.services.s3_service import S3Service
from src.config.settings import GEMINI_API_KEY, SAMPLE_IMAGES_DIR, OUTPUT_DIR
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


def generate_pinterest_pin_with_gemini(pattern_name: str, reference_image_path: Path = None) -> Path:
    """
    Generate a high-engagement Pinterest pin using Gemini image generation

    Args:
        pattern_name: Name of the sewing pattern
        reference_image_path: Optional reference image to guide generation

    Returns:
        Path to generated pin
    """
    logger.info(f"Generating Pinterest pin for: {pattern_name}")

    # Use Gemini's image generation model
    model = genai.GenerativeModel('gemini-2.0-flash-exp-image-generation')

    # Craft the prompt
    if reference_image_path:
        ref_img = Image.open(reference_image_path)

        prompt = f"""Create a high-engagement Pinterest pin image for a sewing pattern called "{pattern_name}".

Style Requirements:
- Airy, light, and modern aesthetic
- Pinterest-optimized dimensions (1000x1500px or 2:3 aspect ratio)
- Professional and click-worthy design
- Include eye-catching text overlay that says something like "Sew This Weekend" or "New Pattern: {pattern_name}"
- Use the reference image as inspiration for the garment/pattern style
- Soft, appealing colors
- Clean, readable typography
- Leave some breathing room around text

Design for maximum engagement - make it irresistible to click and save!"""

        # Generate with reference image
        response = model.generate_content([prompt, ref_img])
    else:
        prompt = f"""Create a high-engagement Pinterest pin image for a sewing pattern called "{pattern_name}".

Style Requirements:
- Airy, light, and modern aesthetic
- Pinterest-optimized dimensions (1000x1500px or 2:3 aspect ratio)
- Professional and click-worthy design
- Include eye-catching text overlay about sewing this pattern
- Soft, appealing colors with plenty of white space
- Show a stylish garment sketch or illustration
- Clean, readable typography
- Modern indie sewing pattern vibe

Design for maximum engagement - make it irresistible to click and save!"""

        response = model.generate_content(prompt)

    # Save the generated image
    output_filename = f"gemini_pin_{pattern_name}_{Path(reference_image_path).stem if reference_image_path else 'generated'}.png"
    output_path = OUTPUT_DIR / output_filename

    # Get the image from response
    if hasattr(response, 'images') and response.images:
        # Save first generated image
        response.images[0].save(output_path)
        logger.info(f"✅ Generated pin saved to: {output_path}")
        return output_path
    elif hasattr(response, 'result'):
        # Alternative response format
        with open(output_path, 'wb') as f:
            f.write(response.result)
        logger.info(f"✅ Generated pin saved to: {output_path}")
        return output_path
    else:
        logger.error(f"Could not extract image from Gemini response: {response}")
        raise ValueError("No image in Gemini response")


def main():
    logger.info("=" * 60)
    logger.info("Simplified Gemini Pinterest Pin Generator")
    logger.info("=" * 60)

    # Test patterns
    test_patterns = [
        {"name": "CrewW", "use_reference": True},
        {"name": "Mimosa", "use_reference": False},  # Generate from scratch
    ]

    s3 = S3Service()
    results = []

    for pattern_info in test_patterns:
        pattern_name = pattern_info["name"]
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {pattern_name}")
        logger.info(f"{'='*60}\n")

        reference_image = None

        if pattern_info["use_reference"]:
            # Download reference image from S3
            logger.info("Downloading reference image from S3...")
            images = s3.download_pattern_images(pattern_name, count=1)
            if images:
                reference_image = images[0]
                logger.info(f"Using reference: {reference_image.name}")

        try:
            # Generate pin with Gemini
            pin_path = generate_pinterest_pin_with_gemini(
                pattern_name=pattern_name,
                reference_image_path=reference_image
            )
            results.append({
                'success': True,
                'pattern': pattern_name,
                'path': pin_path,
                'used_reference': reference_image is not None
            })
        except Exception as e:
            logger.error(f"Failed to generate pin for {pattern_name}: {e}")
            results.append({
                'success': False,
                'pattern': pattern_name,
                'error': str(e)
            })

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)

    success_count = sum(1 for r in results if r['success'])
    logger.info(f"\n✅ Generated {success_count}/{len(results)} pins\n")

    for result in results:
        if result['success']:
            ref_status = "with reference image" if result['used_reference'] else "from scratch"
            logger.info(f"✅ {result['pattern']}: {result['path'].name} ({ref_status})")
        else:
            logger.error(f"❌ {result['pattern']}: {result['error']}")

    logger.info(f"\n📁 Output directory: {OUTPUT_DIR}\n")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
