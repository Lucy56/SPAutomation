# Pinterest Pin Generator

Automated Pinterest pin creation using Google Gemini AI for sewing pattern marketing.

## Features

- **Image Analysis**: Uses Gemini Vision to analyze pattern images
- **Smart Text Overlays**: AI-generated text overlays optimized for Pinterest
- **SEO Metadata**: Automatically generates titles, descriptions, hashtags, and keywords
- **Composition Analysis**: Determines optimal text placement based on image content
- **Batch Processing**: Generate multiple pins from a collection of images
- **Multiple Sources**: Fetch images from AWS S3, Dropbox, or local files

## Project Structure

```
pinterest-pin-generator/
├── src/
│   ├── config/
│   │   └── settings.py          # Configuration and environment variables
│   ├── services/
│   │   ├── s3_service.py        # AWS S3 image fetching
│   │   ├── gemini_service.py    # Google Gemini API integration
│   │   └── pin_generator.py    # Pin image creation
│   └── utils/
│       └── logger.py            # Logging configuration
├── data/
│   ├── sample_images/           # Downloaded source images
│   ├── sample_texts/            # Text overlay templates
│   └── output/                  # Generated pins
├── main.py                      # Main entry point for testing
├── requirements.txt             # Python dependencies
└── .env                         # Environment variables (not in git)
```

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required environment variables:
- `GEMINI_API_KEY` - Google Gemini API key
- `AWS_ACCESS_KEY_ID` - AWS S3 access key
- `AWS_SECRET_ACCESS_KEY` - AWS S3 secret key

3. **Run the test:**
```bash
python main.py
```

## Usage

### Basic Pin Generation

```python
from src.services.pin_generator import PinGenerator
from pathlib import Path

# Initialize
generator = PinGenerator()

# Generate a single pin
result = generator.generate_pin(
    source_image_path=Path('data/sample_images/pattern.jpg'),
    pattern_name='CrewW',
    text_overlay='Perfect Summer Dress'  # Optional - will auto-generate if not provided
)

print(f"Pin saved to: {result['image_path']}")
print(f"Title: {result['metadata']['title']}")
```

### Batch Processing

```python
from src.services.s3_service import S3Service
from src.services.pin_generator import PinGenerator

# Fetch images from S3
s3 = S3Service()
images = s3.download_pattern_images('CrewW', count=10)

# Generate pins
generator = PinGenerator()
results = generator.batch_generate(images, pattern_name='CrewW')
```

## How It Works

1. **Image Acquisition**: Fetches pattern images from S3, Dropbox, or local storage
2. **Composition Analysis**: Gemini analyzes the image to determine:
   - Subject location
   - Best text placement
   - Dominant colors
   - Optimal text color for readability
3. **Text Generation**: Gemini creates:
   - Multiple text overlay options
   - Pinterest-optimized title
   - SEO-friendly description
   - Relevant hashtags and keywords
4. **Image Composition**: Combines source image with text overlay at optimal placement
5. **Output**: Saves Pinterest-ready 1000x1500px image with all metadata

## Next Steps

- [ ] Add web scraping service for sinclairpatterns.com
- [ ] Implement Pinterest posting automation
- [ ] Add analytics tracking
- [ ] Create A/B testing framework
- [ ] Build scheduler for optimal posting times
