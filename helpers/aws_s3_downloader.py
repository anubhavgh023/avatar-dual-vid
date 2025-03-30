import os
import boto3
from urllib.parse import urlparse


# Base directory for output paths (root of project)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

# AWS S3 client
s3_client = boto3.client("s3")


def download_from_s3(s3_url: str, local_path: str) -> None:
    # Parse the S3 URL
    parsed_url = urlparse(s3_url)
    
    # Handle s3:// scheme
    if parsed_url.scheme == "s3":
        bucket = parsed_url.netloc
        key = parsed_url.path.lstrip("/")
    elif parsed_url.scheme == "https" and "s3" in parsed_url.netloc:
        bucket = parsed_url.netloc.split(".")[0]
        key = parsed_url.path.lstrip("/")
    else:
        raise ValueError(f"Invalid S3 URL: {s3_url}")

    try:
        # Ensure downloads directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        # Download the file
        s3_client.download_file(bucket, key, local_path)
    except Exception as e:
        raise Exception(f"Failed to download {s3_url}: {str(e)}")