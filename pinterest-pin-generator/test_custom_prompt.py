#!/usr/bin/env python3
"""
Test custom Gemini prompt for Pinterest pin generation
"""
import google.generativeai as genai
from PIL import Image
from pathlib import Path
from src.config.settings import GEMINI_API_KEY, GEMINI_API_MODEL, SAMPLE_IMAGES_DIR, OUTPUT_DIR
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


def test_custom_prompt():
    """Test your custom prompt with Gemini"""

    logger.info("=" * 60)
    logger.info("Testing Custom Gemini Prompt")
    logger.info("=" * 60)

    # Load the image
    image_path = SAMPLE_IMAGES_DIR / "CrewW_Crew_Rect_grad.jpg"

    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        return 1

    logger.info(f"\nUsing image: {image_path.name}")
    img = Image.open(image_path)

    # Your custom prompt
    prompt = """Create a Pinterest image for this sewing pattern with a call out infant download.
Fashion style illustration should strictly follow the supplied line drawing design, including stitching lines,
decorations and other elements since they reflect garment design which is very important.
Soft and modern colors, postures and faces. Attractive friendly face.
Crew pullover pdf pattern by Sinclair patterns pick only one from the illustration.
Follow pallets rules, font colors and balance rules, margins and correct composition."""

    logger.info("\nPrompt:")
    logger.info("-" * 60)
    logger.info(prompt)
    logger.info("-" * 60)

    # Initialize model
    model = genai.GenerativeModel(GEMINI_API_MODEL)
    logger.info(f"\nUsing model: {GEMINI_API_MODEL}")

    # Send to Gemini
    logger.info("\nSending to Gemini...")
    try:
        response = model.generate_content([prompt, img])

        logger.info("\n" + "=" * 60)
        logger.info("GEMINI RESPONSE")
        logger.info("=" * 60)

        # Check response parts
        logger.info(f"\nNumber of parts: {len(response.parts)}")

        for i, part in enumerate(response.parts):
            logger.info(f"\nPart {i}:")
            logger.info(f"  Type: {type(part)}")

            # Check if it's text
            if hasattr(part, 'text'):
                logger.info(f"  Text: {part.text[:200]}...")

            # Check if it's an image
            if hasattr(part, 'inline_data'):
                logger.info(f"  Has inline_data: {part.inline_data}")

                # Try to save the image
                if part.inline_data and hasattr(part.inline_data, 'data'):
                    import base64
                    output_image = OUTPUT_DIR / f"gemini_generated_part_{i}.png"
                    image_data = base64.b64decode(part.inline_data.data)
                    with open(output_image, 'wb') as f:
                        f.write(image_data)
                    logger.info(f"  ✅ Saved image to: {output_image}")

        logger.info("\n" + "=" * 60)

    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    logger.info("\n" + "=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(test_custom_prompt())
