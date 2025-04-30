from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from urllib.parse import urlparse
from modules.s1_overlay_text_to_avatar import add_text_to_avatar
from modules.s2_concat_videos import concat_videos
from modules.s3_add_bgm import add_bgm_to_video
from modules.vertical_concat import combine_videos_vertically  # Import the new function
from helpers.aws_s3_downloader import download_from_s3
from helpers.aws_uploader import upload_to_s3
from modules.v1_img_gen import generate_image
from modules.img_to_vid_gen import generate_video_from_image  # Import the new function
from celery_config import app as celery_app  # Import Celery app
from celery.result import AsyncResult
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://ugc-ai.vercel.app","https://vibepost.anubhavsamanta.tech"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)


# Existing request body model for /process-video/
class VideoRequest(BaseModel):
    text: str  # content
    avatar_video: str  # s3_url
    real_video: str  # s3_url
    fontStyle: str
    bgm: Optional[str] = None  # Optional background music path
    text_position: str  # Options: "top", "center", "bottom"


# New request body model for /vertical-concat/
class VerticalConcatRequest(BaseModel):
    real_vid: str  # S3 URL to real video
    game_vid: str  # S3 URL to game video
    bgm: Optional[str] = None  # Optional S3 URL to background music
    position: str  # "top" or "bottom"


# New request body model for /img-generation/
class ImageGenerationRequest(BaseModel):
    prompt: str  # Text prompt for image generation


class ImageToVideoRequest(BaseModel):
    prompt: str
    image_url: str  # S3 URL to the input image

# Base directory for output paths (root of project)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")


@app.get("/")
async def root():
    return {"success": True}


@app.get("/health-check")
async def health_check():
    return {"health-status": True}


@app.post("/process-video")
async def process_video(request: VideoRequest):
    """
    Process a video by downloading from S3, overlaying text, concatenating videos, optionally adding BGM,
    and uploading the final video to S3.

    Parameters (in request body):
    - text: Text to overlay on the avatar video
    - avatar_video: S3 URL to the avatar video
    - real_video: S3 URL to the real demo video
    - fontStyle: Font style for text overlay
    - bgm: Optional path or S3 URL to background music
    - text_position: Position of text ("top", "center", "bottom")

    Returns:
    - JSON with success status, local final video path, and S3 presigned URL
    """
    # Validate text_position
    valid_positions = ["top", "center", "bottom"]
    if request.text_position not in valid_positions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid text_position. Must be one of: {valid_positions}",
        )

    print("------------REQUEST-------------")
    print(request)
    print("------------REQUEST-------------")

    # Define local paths for downloaded files
    avatar_local_path = os.path.join(DOWNLOADS_DIR, "avatar.mp4")
    real_local_path = os.path.join(DOWNLOADS_DIR, "real_video.mp4")
    bgm_local_path = os.path.join(DOWNLOADS_DIR, "bgm_1.mp3")

    # Step 0: Download videos from S3
    try:
        download_from_s3(request.avatar_video, avatar_local_path)
        download_from_s3(request.real_video, real_local_path)
        if request.bgm and request.bgm.strip():  # Only download BGM if provided
            download_from_s3(request.bgm, bgm_local_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

    # Step 1: Overlay text on avatar video
    try:
        avatar_with_text_path = os.path.join(DOWNLOADS_DIR, "avatar_with_text.mp4")
        add_text_to_avatar(
            video_path=avatar_local_path,
            text=request.text,
            position=request.text_position,
            fontStyle=request.fontStyle,
            output_path=avatar_with_text_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step 1 failed: {str(e)}")

    # Step 2: Concatenate avatar video (with text) and real video
    try:
        combined_vid_path = os.path.join(DOWNLOADS_DIR, "combined_vid.mp4")
        success, result = concat_videos(
            avatar_vid=avatar_with_text_path,
            real_demo_vid=real_local_path,
            output_path=combined_vid_path,
        )
        if not success:
            raise Exception(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step 2 failed: {str(e)}")

    # Step 3: Add BGM if provided, otherwise skip
    final_output_path = combined_vid_path
    if request.bgm:
        try:
            final_output_path = os.path.join(DOWNLOADS_DIR, "combined_vid_with_bgm.mp4")
            success, result = add_bgm_to_video(
                video_path=combined_vid_path,
                bgm_path=bgm_local_path,
                output_path=final_output_path,
                bgm_volume=0.3,
            )
            if not success:
                raise Exception(result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Step 3 failed: {str(e)}")

    # Step 4: Upload final video to S3 and get presigned URL
    try:
        s3_url = upload_to_s3(final_output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step 4 failed: {str(e)}")

    # Return success status, local path, and S3 URL
    return {"success": True, "s3_url": s3_url}


@app.post("/vertical-concat")
async def vertical_concat(request: VerticalConcatRequest):
    """
    Combine two videos vertically (game video and real video) with a 9:16 aspect ratio,
    optionally add background music, and upload to S3.

    Parameters (in request body):
    - real_vid: S3 URL to the real video
    - game_vid: S3 URL to the game video
    - bgm: Optional S3 URL to background music
    - position: Position of real video ("top" or "bottom")

    Returns:
    - JSON with success status and S3 presigned URL
    """
    # Validate position
    valid_positions = ["top", "bottom"]
    if request.position not in valid_positions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid position. Must be one of: {valid_positions}",
        )

    print("------------VERTICAL CONCAT REQUEST-------------")
    print(request)
    print("------------VERTICAL CONCAT REQUEST-------------")

    # Define local paths for downloaded files
    game_local_path = os.path.join(DOWNLOADS_DIR, "game_vid.mp4")
    real_local_path = os.path.join(DOWNLOADS_DIR, "real_vertical_video.mp4")
    bgm_local_path = os.path.join(DOWNLOADS_DIR, "bgm_1.mp3")
    vertical_output_path = os.path.join(DOWNLOADS_DIR, "vertical_combined_vid.mp4")

    # Step 1: Download videos and BGM from S3
    try:
        download_from_s3(request.game_vid, game_local_path)
        download_from_s3(request.real_vid, real_local_path)
        if request.bgm and request.bgm.strip():  # Only download BGM if provided
            download_from_s3(request.bgm, bgm_local_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

    # Step 2: Combine videos vertically
    try:
        result = combine_videos_vertically(
            game_vid=game_local_path,
            real_vid=real_local_path,
            position=request.position,
            output_path=vertical_output_path,
        )
        if not result:
            raise Exception("Vertical concatenation failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step 2 failed: {str(e)}")

    # Step 3: Add BGM if provided, otherwise skip
    final_output_path = vertical_output_path
    if request.bgm:
        try:
            final_output_path = os.path.join(
                DOWNLOADS_DIR, "vertical_combined_with_bgm.mp4"
            )
            success, result = add_bgm_to_video(
                video_path=vertical_output_path,
                bgm_path=bgm_local_path,
                output_path=final_output_path,
                bgm_volume=0.3,
            )
            if not success:
                raise Exception(result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Step 3 failed: {str(e)}")

    # Step 4: Upload final video to S3 and get presigned URL
    try:
        s3_url = upload_to_s3(final_output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step 4 failed: {str(e)}")

    # Return success status and S3 URL
    return {"success": True, "s3_url": s3_url}


# ========== Image Generation =================
@app.post("/img-generation")
async def generate_image_endpoint(request: ImageGenerationRequest):
    """
    Generate an image using Segmind's Juggernaut Pro Flux API, upload it to S3, and return the S3 URL.

    Parameters (in request body):
    - prompt: Text prompt for image generation

    Returns:
    - JSON with success status and S3 presigned URL
    """
    # Step 1: Validate the prompt
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    print("------------IMAGE GENERATION REQUEST-------------")
    print(request)
    print("------------IMAGE GENERATION REQUEST-------------")

    # Step 2: Generate the image using Segmind API
    image_output_path = os.path.join(DOWNLOADS_DIR, "generated_image.jpg")
    try:
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)  # Ensure downloads directory exists
        success = generate_image(request.prompt, image_output_path)
        if not success:
            raise Exception("Image generation failed")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Step 2 failed: Image generation error - {str(e)}"
        )

    # Step 3: Upload the generated image to S3
    try:
        s3_url = upload_to_s3(image_output_path)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Step 3 failed: S3 upload error - {str(e)}"
        )

    # Step 4: Return success status and S3 URL
    return {"success": True, "s3_link": s3_url}


# ========== Image to Video Generation =================
@app.post("/img-to-vid-gen")
async def image_to_video(request: ImageToVideoRequest):
    """
    Queue a video generation task from an image using MiniMax's I2V-01-Director model.

    Parameters (in request body):
    - image_url: S3 URL to the input image
    - prompt: Descriptive prompt for video generation

    Returns:
    - JSON with success status and task ID
    """
    print("------------IMAGE TO VIDEO GENERATION REQUEST-------------")
    print(request)
    print("------------IMAGE TO VIDEO GENERATION REQUEST-------------")

    # Step 1: Download the image from S3 and validate
    try:
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)
        image_local_path = os.path.join(DOWNLOADS_DIR, "input_image.jpg")
        download_from_s3(request.image_url, image_local_path)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Step 1 failed: Image download error - {str(e)}"
        )

    # Step 2: Queue video generation task
    try:
        task_id = generate_video_from_image(image_local_path, request.prompt)
        return {
            "success": True,
            "task_id": task_id,
            "message": "Video generation task queued",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Step 2 failed: Task queue error - {str(e)}"
        )


@app.get("/task-status/{task_id}")
async def task_status(task_id: str):
    """
    Check the status of a video generation task.

    Parameters:
    - task_id: ID of the Celery task

    Returns:
    - JSON with task status, result, and error (if any)
    """
    task = AsyncResult(task_id, app=celery_app)
    if task.state == "PENDING":
        return {
            "success": True,
            "task_id": task_id,
            "status": "Pending",
            "result": None,
            "error": None,
        }
    elif task.state == "PROGRESS":
        return {
            "success": True,
            "task_id": task_id,
            "status": task.state,
            "progress": task.info.get("status", "Processing"),
            "result": None,
            "error": None,
        }
    elif task.state == "SUCCESS":
        result = task.get()
        return {
            "success": result["success"],
            "task_id": task_id,
            "status": "Success",
            "result": {
                "s3_link": (
                    upload_to_s3(result["video_path"]) if result["success"] else None
                )
            },
            "error": result["error"],
        }
    elif task.state == "FAILURE":
        return {
            "success": False,
            "task_id": task_id,
            "status": "Failed",
            "result": None,
            "error": str(task.info),
        }
    else:
        return {
            "success": False,
            "task_id": task_id,
            "status": task.state,
            "result": None,
            "error": "Unknown task state",
        }