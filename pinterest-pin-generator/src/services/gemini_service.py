"""Google Gemini API service for image analysis and text generation"""
import google.generativeai as genai
import json
import re
from pathlib import Path
from typing import Dict, List
from PIL import Image
from src.config.settings import GEMINI_API_KEY, GEMINI_API_MODEL
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


class GeminiService:
    """Service for interacting with Google Gemini API"""

    def __init__(self):
        # Use model from environment variable
        self.model = genai.GenerativeModel(GEMINI_API_MODEL)
        logger.info(f"Initialized Gemini with model: {GEMINI_API_MODEL}")

    def generate_pin_description(self, image_path: Path, context: Dict = None) -> Dict:
        """
        Generate Pinterest pin metadata using Gemini vision model

        Args:
            image_path: Path to pattern image
            context: Additional context (pattern name, target audience, etc.)

        Returns:
            Dictionary with title, description, hashtags, keywords
        """
        context = context or {}
        pattern_name = context.get('pattern_name', 'Unknown Pattern')
        target = context.get('target', 'sewers and fashion enthusiasts')

        logger.info(f"Generating pin description for: {image_path.name}")

        try:
            img = Image.open(image_path)

            prompt = f"""You are a Pinterest marketing expert specializing in sewing patterns.
Analyze this sewing pattern image and create compelling Pinterest pin metadata.

Context:
- Pattern Name: {pattern_name}
- Target Audience: {target}
- Goal: Drive traffic, engagement, and sales

Generate the following in JSON format:
{{
  "title": "Catchy pin title (40-60 characters)",
  "description": "Engaging description (200-400 characters) with benefits and call-to-action",
  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4"]
}}

Make it click-worthy, SEO-optimized, and authentic. Focus on benefits, not just features."""

            response = self.model.generate_content([prompt, img])
            text = response.text

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                metadata = json.loads(json_match.group(0))
                logger.info(f"Generated metadata: {metadata['title']}")
                return metadata
            else:
                logger.warning("Could not parse JSON from Gemini response")
                return {'raw_response': text}

        except Exception as e:
            logger.error(f"Error generating description: {e}")
            raise

    def generate_text_overlays(self, image_path: Path, context: Dict = None) -> List[Dict]:
        """
        Generate text overlay suggestions for Pinterest pins

        Args:
            image_path: Path to pattern image
            context: Context about the pattern

        Returns:
            List of text overlay suggestions with style hints
        """
        context = context or {}
        pattern_name = context.get('pattern_name', 'Sewing Pattern')

        logger.info(f"Generating text overlays for: {image_path.name}")

        try:
            img = Image.open(image_path)

            prompt = f"""Analyze this sewing pattern image for {pattern_name}.

Create 5 different text overlay options perfect for Pinterest pins. Each should be:
- SHORT (2-6 words maximum)
- Eye-catching and click-worthy
- Varied in approach (urgency, benefit, curiosity, skill-level, seasonality)

Examples of good text overlays:
- "Easy Beginner Dress"
- "Perfect Summer Wardrobe"
- "Sew This Weekend"
- "Trending Pattern 2024"

Return as JSON array:
[
  {{"text": "Short catchy text", "style": "urgency|benefit|curiosity|skill|seasonal"}},
  ...
]

Focus on what makes someone want to click and save the pin."""

            response = self.model.generate_content([prompt, img])
            text = response.text

            # Extract JSON array
            json_match = re.search(r'\[[\s\S]*\]', text)
            if json_match:
                overlays = json.loads(json_match.group(0))
                logger.info(f"Generated {len(overlays)} text overlay options")
                return overlays
            else:
                logger.warning("Using default text overlays")
                return [
                    {"text": "New Pattern Alert", "style": "urgency"},
                    {"text": "Sew This Today", "style": "action"},
                    {"text": "Perfect Fit Guaranteed", "style": "benefit"}
                ]

        except Exception as e:
            logger.error(f"Error generating text overlays: {e}")
            raise

    def analyze_composition(self, image_path: Path) -> Dict:
        """
        Analyze image composition for optimal text placement

        Args:
            image_path: Path to image

        Returns:
            Composition analysis with placement suggestions
        """
        logger.info(f"Analyzing composition: {image_path.name}")

        try:
            img = Image.open(image_path)

            prompt = """Analyze this sewing pattern image for Pinterest pin optimization.

Provide:
1. Where is the main subject/garment located?
2. Best area for text overlay (won't obscure important details)
3. Dominant colors in the image
4. Recommended text color for maximum readability
5. Overall image quality

Return as JSON:
{
  "subject_area": "top|middle|bottom|left|right|center",
  "text_placement": "top|bottom|top-left|top-right|bottom-left|bottom-right",
  "dominant_colors": ["#hexcode1", "#hexcode2"],
  "text_color": "white|black|custom-hex",
  "quality": "excellent|good|needs-improvement",
  "suggestions": "Brief suggestions for improvement"
}"""

            response = self.model.generate_content([prompt, img])
            text = response.text

            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                composition = json.loads(json_match.group(0))
                logger.info(f"Composition: text placement = {composition.get('text_placement')}")
                return composition
            else:
                return {'raw_response': text}

        except Exception as e:
            logger.error(f"Error analyzing composition: {e}")
            raise
