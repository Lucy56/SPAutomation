"""Pinterest pin image generator"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
from typing import Dict, Tuple
from src.config.settings import PIN_WIDTH, PIN_HEIGHT, OUTPUT_DIR
from src.services.gemini_service import GeminiService
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PinGenerator:
    """Generate Pinterest-optimized pin images with text overlays"""

    def __init__(self):
        self.gemini = GeminiService()
        self.pin_size = (PIN_WIDTH, PIN_HEIGHT)

    def generate_pin(
        self,
        source_image_path: Path,
        text_overlay: str = None,
        pattern_name: str = "Pattern",
        output_filename: str = None
    ) -> Dict:
        """
        Generate a complete Pinterest pin from source image

        Args:
            source_image_path: Path to source image
            text_overlay: Optional text to overlay (will generate if None)
            pattern_name: Name of the pattern
            output_filename: Custom output filename

        Returns:
            Dictionary with pin details (path, metadata, etc.)
        """
        logger.info(f"Generating pin from: {source_image_path.name}")

        # Step 1: Analyze composition
        composition = self.gemini.analyze_composition(source_image_path)
        logger.info(f"Composition analysis complete")

        # Step 2: Generate or use provided text overlay
        if not text_overlay:
            overlays = self.gemini.generate_text_overlays(
                source_image_path,
                {'pattern_name': pattern_name}
            )
            text_overlay = overlays[0]['text'] if overlays else "New Pattern"
            logger.info(f"Generated text overlay: '{text_overlay}'")

        # Step 3: Generate metadata
        metadata = self.gemini.generate_pin_description(
            source_image_path,
            {'pattern_name': pattern_name}
        )

        # Step 4: Create the pin image
        if not output_filename:
            output_filename = f"pin_{pattern_name}_{Path(source_image_path).stem}.jpg"

        output_path = self.create_pin_image(
            source_image_path,
            text_overlay,
            composition,
            output_filename
        )

        return {
            'image_path': output_path,
            'text_overlay': text_overlay,
            'metadata': metadata,
            'composition': composition
        }

    def create_pin_image(
        self,
        source_path: Path,
        text: str,
        composition: Dict,
        output_filename: str
    ) -> Path:
        """
        Create Pinterest pin image with text overlay

        Args:
            source_path: Source image path
            text: Text to overlay
            composition: Composition analysis from Gemini
            output_filename: Output filename

        Returns:
            Path to created pin image
        """
        logger.info(f"Creating pin image with text: '{text}'")

        # Open and resize source image to Pinterest dimensions
        img = Image.open(source_path)
        img = self.resize_to_pinterest(img)

        # Add text overlay
        img_with_text = self.add_text_overlay(img, text, composition)

        # Save
        output_path = OUTPUT_DIR / output_filename
        img_with_text.save(output_path, 'JPEG', quality=95, optimize=True)

        logger.info(f"Pin saved to: {output_path}")
        return output_path

    def resize_to_pinterest(self, img: Image.Image) -> Image.Image:
        """Resize image to Pinterest optimal dimensions (1000x1500)"""
        # Calculate crop box to maintain aspect ratio
        target_ratio = PIN_HEIGHT / PIN_WIDTH  # 1.5 (2:3 ratio)
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

        # Resize to target dimensions
        img = img.resize((PIN_WIDTH, PIN_HEIGHT), Image.Resampling.LANCZOS)
        return img

    def add_text_overlay(
        self,
        img: Image.Image,
        text: str,
        composition: Dict
    ) -> Image.Image:
        """
        Add text overlay to image with optimal placement and styling

        Args:
            img: PIL Image
            text: Text to overlay
            composition: Composition analysis

        Returns:
            Image with text overlay
        """
        draw = ImageDraw.Draw(img)

        # Determine text color
        text_color_pref = composition.get('text_color', 'white')
        if text_color_pref == 'black':
            text_color = (0, 0, 0, 255)
            shadow_color = (255, 255, 255, 200)
        else:
            text_color = (255, 255, 255, 255)
            shadow_color = (0, 0, 0, 200)

        # Try to load a nice font, fallback to default
        font_size = 80
        try:
            # Try system fonts
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", font_size)
            except:
                logger.warning("Could not load custom font, using default")
                font = ImageFont.load_default()

        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Determine position based on composition
        placement = composition.get('text_placement', 'top').lower()
        x = (PIN_WIDTH - text_width) // 2  # Center horizontally

        if 'bottom' in placement:
            y = PIN_HEIGHT - text_height - 100
        elif 'middle' in placement or 'center' in placement:
            y = (PIN_HEIGHT - text_height) // 2
        else:  # top
            y = 80

        # Draw text shadow for better readability
        for offset in range(1, 4):
            draw.text(
                (x + offset, y + offset),
                text,
                font=font,
                fill=shadow_color
            )

        # Draw main text
        draw.text((x, y), text, font=font, fill=text_color)

        return img

    def batch_generate(
        self,
        image_paths: list[Path],
        pattern_name: str = "Pattern"
    ) -> list[Dict]:
        """
        Generate multiple pins from a list of images

        Args:
            image_paths: List of source image paths
            pattern_name: Name of the pattern

        Returns:
            List of pin generation results
        """
        results = []

        for i, img_path in enumerate(image_paths, 1):
            logger.info(f"Processing image {i}/{len(image_paths)}: {img_path.name}")

            try:
                result = self.generate_pin(img_path, pattern_name=pattern_name)
                result['success'] = True
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to generate pin for {img_path.name}: {e}")
                results.append({
                    'success': False,
                    'source_image': img_path,
                    'error': str(e)
                })

        return results
