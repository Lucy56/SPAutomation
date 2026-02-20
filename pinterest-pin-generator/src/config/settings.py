"""Configuration settings for Pinterest Pin Generator"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
SAMPLE_IMAGES_DIR = DATA_DIR / 'sample_images'
SAMPLE_TEXTS_DIR = DATA_DIR / 'sample_texts'
OUTPUT_DIR = DATA_DIR / 'output'

# Ensure directories exist
for directory in [DATA_DIR, SAMPLE_IMAGES_DIR, SAMPLE_TEXTS_DIR, OUTPUT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_MODEL = os.getenv('GEMINI_API_MODEL', 'gemini-3-pro-image-preview')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN')

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET', 'sinclairpatterns')
AWS_S3_REGION = os.getenv('AWS_S3_REGION', 'us-east-1')
AWS_S3_BASE_PATH = 'MAIL/patterns/'

# Website
PATTERN_WEBSITE_URL = os.getenv('PATTERN_WEBSITE_URL', 'https://sinclairpatterns.com')

# Pinterest settings
PIN_WIDTH = int(os.getenv('PIN_WIDTH', 1000))
PIN_HEIGHT = int(os.getenv('PIN_HEIGHT', 1500))

# Sample patterns
SAMPLE_PATTERNS = os.getenv('SAMPLE_PATTERNS', 'CrewM,CrewW,Mimosa').split(',')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
