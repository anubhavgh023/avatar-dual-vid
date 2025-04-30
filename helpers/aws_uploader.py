import os
import boto3
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)


def upload_to_s3(file_path: str) -> str:
    """
    Upload a file to S3 and return a presigned URL.

    Parameters:
    -----------
    file_path : str
        Local path to the file to upload

    Returns:
    --------
    str
        Presigned URL for the uploaded file
    """
    # Determine file extension and content type
    file_extension = os.path.splitext(file_path)[1].lower()
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
    }
    content_type = content_types.get(file_extension, "application/octet-stream")
    file_type = "image" if file_extension in [".jpg", ".jpeg", ".png"] else "video"

    # Generate a timestamped filename with correct extension
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"{file_type}_{current_time}{file_extension}"

    s3_path = f"uploads/{file_name}"
    bucket_name = os.getenv("S3_BUCKET_NAME")
    try:
        # Upload the file to S3 with appropriate ContentType
        s3_client.upload_file(
            file_path, bucket_name, s3_path, ExtraArgs={"ContentType": content_type}
        )

        # Generate a presigned URL valid for 1 hour (3600 seconds)
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": s3_path},
            ExpiresIn=3600,  # 1 hour
        )
        return presigned_url
    except Exception as e:
        raise Exception(f"Failed to upload to S3: {str(e)}")

# working: issue in img upload
# import os
# import boto3
# from dotenv import load_dotenv
# from datetime import datetime

# # Load environment variables
# load_dotenv()

# # Initialize S3 client
# s3_client = boto3.client(
#     "s3",
#     aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
#     aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
#     region_name=os.getenv("AWS_REGION"),
# )


# def upload_to_s3(file_path: str) -> str:
#     """
#     Upload a file to S3 and return a presigned URL.

#     Parameters:
#     -----------
#     file_path : str
#         Local path to the file to upload

#     Returns:
#     --------
#     str
#         Presigned URL for the uploaded file
#     """
#     # Generate a timestamped filename
#     current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
#     file_name = f"video_{current_time}.mp4"

#     s3_path = f"uploads/{file_name}"
#     bucket_name = os.getenv("S3_BUCKET_NAME")
#     try:
#         # Upload the file to S3
#         s3_client.upload_file(
#             file_path, bucket_name, s3_path, ExtraArgs={"ContentType": "video/mp4"}
#         )

#         # Generate a presigned URL valid for 1 hour (3600 seconds)
#         presigned_url = s3_client.generate_presigned_url(
#             "get_object",
#             Params={"Bucket": bucket_name, "Key": s3_path},
#             ExpiresIn=3600,  # 1 hour
#         )
#         return presigned_url
#     except Exception as e:
#         raise Exception(f"Failed to upload to S3: {str(e)}")
