#!/usr/bin/env python3
"""
Image Enhancement Processor
Processes images with AI-guided enhancements, background removal, and colored backgrounds.

Features:
- Gemini Vision API for intelligent image analysis
- Automatic lighting and skin tone enhancement
- AI-guided background removal
- Custom background color (#DADADA)
- Batch processing with random selection
"""

import os
import sys
import random
import json
import re
from pathlib import Path
from typing import Dict, Tuple, Optional
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
from datetime import datetime

# Add pinterest-pin-generator to path to use its Gemini setup
pinterest_path = Path(__file__).parent.parent / "pinterest-pin-generator"
sys.path.insert(0, str(pinterest_path))

import google.generativeai as genai
from dotenv import load_dotenv
from rembg import remove

# Load environment variables from pinterest-pin-generator
env_path = pinterest_path / ".env"
load_dotenv(env_path)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_API_MODEL", "gemini-pro-vision")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)


class ImageEnhancementProcessor:
    """Process images with AI-guided enhancements and background removal"""

    def __init__(self, background_color="#DADADA"):
        """
        Initialize processor

        Args:
            background_color: Hex color for background (default: #DADADA)
        """
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.background_color = background_color
        print(f"✓ Initialized with Gemini model: {GEMINI_MODEL}")
        print(f"✓ Background color: {background_color}")

    def analyze_image_for_enhancement(self, image_path: Path) -> Dict:
        """
        Use Gemini to analyze image and suggest enhancements

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with enhancement suggestions
        """
        print(f"\n📸 Analyzing image: {image_path.name}")

        try:
            img = Image.open(image_path)

            prompt = """Analyze this fashion/garment photograph for Pinterest-style enhancement.

Provide detailed analysis and recommendations:

1. **Lighting Quality**: Is it underexposed, overexposed, or well-lit?
2. **Skin Tones**: Do skin tones need warming, cooling, or are they natural?
3. **Contrast**: Does it need more or less contrast?
4. **Sharpness**: Is the image sharp enough or does it need enhancement?
5. **Colors**: Are colors vibrant enough or do they need saturation boost?
6. **Subject Location**: Where is the main subject/person in the image?
7. **Background**: Describe the background - is it simple or complex?

Return as JSON:
{
  "brightness_adjustment": -0.2 to 0.2 (negative = darken, positive = brighten),
  "contrast_adjustment": 0.8 to 1.3 (1.0 = no change),
  "color_saturation": 0.8 to 1.3 (1.0 = no change),
  "sharpness": 0.8 to 1.5 (1.0 = no change),
  "skin_tone_warmth": -0.1 to 0.1 (negative = cooler, positive = warmer),
  "subject_area": "Describe where the person/garment is located",
  "background_complexity": "simple|moderate|complex",
  "recommendations": "Brief enhancement suggestions"
}

Make recommendations suitable for Pinterest - bright, clear, appealing images."""

            response = self.model.generate_content([prompt, img])
            text = response.text

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                analysis = json.loads(json_match.group(0))
                print(f"  ✓ Analysis complete: {analysis.get('recommendations', 'N/A')}")
                return analysis
            else:
                print(f"  ⚠ Could not parse JSON, using defaults")
                return self._default_enhancement_settings()

        except Exception as e:
            print(f"  ✗ Error analyzing image: {e}")
            return self._default_enhancement_settings()

    def _default_enhancement_settings(self) -> Dict:
        """Return default enhancement settings if analysis fails"""
        return {
            "brightness_adjustment": 0.05,
            "contrast_adjustment": 1.1,
            "color_saturation": 1.15,
            "sharpness": 1.1,
            "skin_tone_warmth": 0.02,
            "subject_area": "center",
            "background_complexity": "moderate",
            "recommendations": "Default Pinterest-style enhancement"
        }

    def get_subject_mask_guidance(self, image_path: Path) -> Dict:
        """
        Use Gemini to provide guidance for subject detection

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with subject detection guidance
        """
        print(f"  🎯 Getting subject detection guidance...")

        try:
            img = Image.open(image_path)

            prompt = """Analyze this fashion photograph to help identify the subject (person wearing garment) for background removal.

Provide guidance on:
1. Where is the person located (percentage from edges)?
2. What is the dominant color of the background?
3. Are there clear edges between subject and background?
4. Is the background uniform or varied?

Return as JSON:
{
  "subject_bounds_percentage": {
    "left": 0-100,
    "top": 0-100,
    "right": 0-100,
    "bottom": 0-100
  },
  "background_dominant_color": "description or hex if possible",
  "edge_clarity": "sharp|moderate|soft",
  "background_type": "solid|gradient|textured|complex",
  "removal_difficulty": "easy|moderate|difficult"
}"""

            response = self.model.generate_content([prompt, img])
            text = response.text

            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                guidance = json.loads(json_match.group(0))
                print(f"  ✓ Subject guidance: {guidance.get('removal_difficulty', 'N/A')} removal")
                return guidance
            else:
                print(f"  ⚠ Using default subject guidance")
                return {"removal_difficulty": "moderate"}

        except Exception as e:
            print(f"  ✗ Error getting subject guidance: {e}")
            return {"removal_difficulty": "moderate"}

    def enhance_image(self, img: Image.Image, analysis: Dict) -> Image.Image:
        """
        Apply enhancements to image based on analysis

        Args:
            img: PIL Image object
            analysis: Enhancement analysis from Gemini

        Returns:
            Enhanced PIL Image
        """
        print(f"  🎨 Applying enhancements...")

        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Apply brightness
        brightness_adj = analysis.get('brightness_adjustment', 0)
        if brightness_adj != 0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.0 + brightness_adj)

        # Apply contrast
        contrast_adj = analysis.get('contrast_adjustment', 1.0)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast_adj)

        # Apply color saturation
        saturation_adj = analysis.get('color_saturation', 1.0)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(saturation_adj)

        # Apply sharpness
        sharpness_adj = analysis.get('sharpness', 1.0)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(sharpness_adj)

        # Skin tone warmth adjustment (simple approach using color balance)
        warmth = analysis.get('skin_tone_warmth', 0)
        if warmth != 0:
            img = self._adjust_warmth(img, warmth)

        print(f"  ✓ Enhancements applied")
        return img

    def _adjust_warmth(self, img: Image.Image, warmth: float) -> Image.Image:
        """
        Adjust color warmth (adds orange/blue tint)

        Args:
            img: PIL Image
            warmth: -1 to 1 (negative = cooler, positive = warmer)

        Returns:
            Adjusted image
        """
        # Convert warmth to RGB adjustment
        r_adjust = int(warmth * 20)
        b_adjust = int(-warmth * 20)

        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b = pixels[x, y]
                r = max(0, min(255, r + r_adjust))
                b = max(0, min(255, b + b_adjust))
                pixels[x, y] = (r, g, b)

        return img

    def remove_background_ai(self, img: Image.Image) -> Image.Image:
        """
        AI-based background removal using rembg with better model and post-processing

        Args:
            img: PIL Image (already enhanced)

        Returns:
            Image with transparent background
        """
        print(f"  ✂️  Removing background (AI-based)...")

        # Use rembg with u2net_human_seg model - better for people/fashion
        # Also apply post-processing to clean up edges
        output = remove(
            img,
            alpha_matting=True,           # Better edge detection
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=10,  # Slightly erode to avoid artifacts
            post_process_mask=True         # Clean up the mask
        )

        # Additional edge smoothing
        if output.mode == 'RGBA':
            # Get alpha channel
            alpha = output.split()[3]

            # Apply slight blur to alpha for smoother edges
            alpha = alpha.filter(ImageFilter.GaussianBlur(radius=1))

            # Put the smoothed alpha back
            r, g, b, _ = output.split()
            output = Image.merge('RGBA', (r, g, b, alpha))

        print(f"  ✓ Background removed successfully")
        return output

    def add_colored_background(self, img: Image.Image, color: str = None) -> Image.Image:
        """
        Add colored background to transparent image

        Args:
            img: PIL Image with transparency
            color: Hex color (default: self.background_color)

        Returns:
            Image with colored background
        """
        if color is None:
            color = self.background_color

        print(f"  🎨 Adding background color: {color}")

        # Convert hex to RGB
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))

        # Create new background
        background = Image.new('RGB', img.size, rgb)

        # Paste image onto background using alpha channel
        if img.mode == 'RGBA':
            background.paste(img, (0, 0), img)
        else:
            background.paste(img, (0, 0))

        print(f"  ✓ Background added")
        return background

    def process_image(self, image_path: Path, output_dir: Path) -> Dict:
        """
        Complete processing pipeline for one image

        Args:
            image_path: Path to source image
            output_dir: Directory for output

        Returns:
            Dictionary with processing results
        """
        print(f"\n{'='*60}")
        print(f"Processing: {image_path.name}")
        print(f"{'='*60}")

        start_time = datetime.now()

        try:
            # Step 1: Analyze for enhancements
            analysis = self.analyze_image_for_enhancement(image_path)

            # Step 2: Load and enhance image
            img = Image.open(image_path)
            enhanced_img = self.enhance_image(img, analysis)

            # Step 3: Remove background using AI
            no_bg_img = self.remove_background_ai(enhanced_img)

            # Step 4: Add colored background
            final_img = self.add_colored_background(no_bg_img)

            # Step 5: Save output
            output_path = output_dir / f"enhanced_{image_path.name}"
            final_img.save(output_path, 'JPEG', quality=95, optimize=True)

            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\n✓ SUCCESS - Saved to: {output_path.name}")
            print(f"  Processing time: {elapsed:.2f}s")

            return {
                'success': True,
                'input': str(image_path),
                'output': str(output_path),
                'analysis': analysis,
                'processing_time': elapsed
            }

        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            return {
                'success': False,
                'input': str(image_path),
                'error': str(e)
            }

    def process_batch(self, input_dir: Path, count: int = 3, output_subdir: str = "output") -> list[Dict]:
        """
        Process multiple random images from directory

        Args:
            input_dir: Directory containing images
            count: Number of images to process
            output_subdir: Name of output subdirectory

        Returns:
            List of processing results
        """
        print(f"\n{'='*60}")
        print(f"IMAGE ENHANCEMENT BATCH PROCESSOR")
        print(f"{'='*60}")
        print(f"Input directory: {input_dir}")
        print(f"Processing: {count} random images")
        print(f"Background color: {self.background_color}")
        print(f"{'='*60}\n")

        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.heic'}
        all_images = [
            f for f in input_dir.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

        if not all_images:
            print("✗ No images found in directory")
            return []

        print(f"Found {len(all_images)} images in directory")

        # Randomly select images
        selected = random.sample(all_images, min(count, len(all_images)))
        print(f"Randomly selected {len(selected)} images:\n")
        for i, img in enumerate(selected, 1):
            print(f"  {i}. {img.name}")

        # Create output directory
        output_dir = input_dir / output_subdir
        output_dir.mkdir(exist_ok=True)
        print(f"\nOutput directory: {output_dir}\n")

        # Process each image
        results = []
        for i, img_path in enumerate(selected, 1):
            print(f"\n[{i}/{len(selected)}]")
            result = self.process_image(img_path, output_dir)
            results.append(result)

        # Summary
        print(f"\n{'='*60}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*60}")

        successful = sum(1 for r in results if r['success'])
        print(f"Successful: {successful}/{len(results)}")

        if successful > 0:
            avg_time = sum(r.get('processing_time', 0) for r in results if r['success']) / successful
            print(f"Average processing time: {avg_time:.2f}s")

        print(f"\nOutput files saved to: {output_dir}")

        return results


def main():
    """Main entry point"""

    # Configuration
    INPUT_DIR = Path("/Users/sanna/Dev/Experiments/SinclairHelper/Samples/Pictures to process/Fiona_woven_blouse_2026-02-20")
    NUM_IMAGES = 3
    BACKGROUND_COLOR = "#DADADA"

    # Validate input directory
    if not INPUT_DIR.exists():
        print(f"✗ Error: Input directory does not exist: {INPUT_DIR}")
        return

    # Initialize processor
    processor = ImageEnhancementProcessor(background_color=BACKGROUND_COLOR)

    # Process batch
    results = processor.process_batch(
        input_dir=INPUT_DIR,
        count=NUM_IMAGES,
        output_subdir="output"
    )

    # Save results to JSON
    results_file = INPUT_DIR / "output" / "processing_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
