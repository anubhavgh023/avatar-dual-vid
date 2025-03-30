import os
import boto3
from urllib.parse import urlparse


# Base directory for output paths (root of project)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

# AWS S3 client
s3_client = boto3.client("s3")


def download_from_s3(s3_url: str, local_path: str) -> None:
    """
    Download a file from an S3 URL and save it to a local path.

    Parameters:
    -----------
    s3_url : str
        The S3 URL (e.g., s3://bucket-name/key or https://bucket-name.s3.region.amazonaws.com/key)
    local_path : str
        Local path to save the downloaded file

    Raises:
    -------
    Exception
        If the download fails
    """
    # Parse the S3 URL
    parsed_url = urlparse(s3_url)
    
    # Handle s3:// scheme
    if parsed_url.scheme == "s3":
        bucket = parsed_url.netloc
        key = parsed_url.path.lstrip("/")
    # Handle https:// scheme (e.g., from S3 presigned URLs or public links)
    elif parsed_url.scheme == "https" and "s3" in parsed_url.netloc:
        # Extract bucket and key from URL like https://bucket-name.s3.region.amazonaws.com/key
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