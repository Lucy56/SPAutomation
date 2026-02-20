"""AWS S3 service for fetching pattern images"""
import boto3
from pathlib import Path
from typing import List, Dict
from src.config.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_S3_BUCKET,
    AWS_S3_REGION,
    AWS_S3_BASE_PATH,
    SAMPLE_IMAGES_DIR
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class S3Service:
    """Service for interacting with AWS S3 to fetch pattern images"""

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_S3_REGION
        )
        self.bucket = AWS_S3_BUCKET

    def list_pattern_images(self, pattern_name: str, limit: int = 15) -> List[Dict]:
        """
        List images for a specific pattern from S3

        Args:
            pattern_name: Name of the pattern (e.g., 'CrewM', 'Mimosa')
            limit: Maximum number of images to return

        Returns:
            List of dictionaries with image metadata
        """
        prefix = f"{AWS_S3_BASE_PATH}{pattern_name}/"
        logger.info(f"Listing images from s3://{self.bucket}/{prefix}")

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=limit
            )

            if 'Contents' not in response:
                logger.warning(f"No images found for pattern: {pattern_name}")
                return []

            images = []
            for obj in response['Contents']:
                key = obj['Key']
                # Filter for image files
                if any(key.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    images.append({
                        'key': key,
                        'filename': Path(key).name,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })

            logger.info(f"Found {len(images)} images for {pattern_name}")
            return images[:limit]

        except Exception as e:
            logger.error(f"Error listing S3 objects: {e}")
            raise

    def download_image(self, s3_key: str, local_path: Path) -> Path:
        """
        Download an image from S3 to local filesystem

        Args:
            s3_key: S3 object key
            local_path: Local destination path

        Returns:
            Path to downloaded file
        """
        try:
            logger.info(f"Downloading {s3_key} to {local_path}")
            self.s3_client.download_file(self.bucket, s3_key, str(local_path))
            return local_path
        except Exception as e:
            logger.error(f"Error downloading from S3: {e}")
            raise

    def download_pattern_images(self, pattern_name: str, count: int = 5) -> List[Path]:
        """
        Download sample images for a pattern

        Args:
            pattern_name: Name of the pattern
            count: Number of images to download

        Returns:
            List of paths to downloaded images
        """
        images = self.list_pattern_images(pattern_name, limit=count)
        downloaded_paths = []

        for img in images[:count]:
            filename = f"{pattern_name}_{img['filename']}"
            local_path = SAMPLE_IMAGES_DIR / filename

            # Skip if already downloaded
            if local_path.exists():
                logger.info(f"Image already exists: {local_path}")
                downloaded_paths.append(local_path)
                continue

            self.download_image(img['key'], local_path)
            downloaded_paths.append(local_path)

        return downloaded_paths

    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for an S3 object

        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL string
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
