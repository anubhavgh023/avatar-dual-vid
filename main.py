from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from urllib.parse import urlparse
from modules.s1_overlay_text_to_avatar import add_text_to_avatar
from modules.s2_concat_videos import concat_videos
from modules.s3_add_bgm import add_bgm_to_video
from helpers.aws_s3_downloader import download_from_s3

app = FastAPI()


# Define the request body model
class VideoRequest(BaseModel):
    text: str # content
    avatar_video: str # s3_url
    real_video: str # s3_url
    fontStyle:str
    bgm: Optional[str] = None  # Optional background music path
    text_position: str  # Options: "top", "center", "bottom"


# Base directory for output paths (root of project)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")


@app.post("/process-video/")
async def process_video(request: VideoRequest):
    """
    Process a video by downloading from S3, overlaying text, concatenating videos, and optionally adding BGM.

    Parameters (in request body):
    - text: Text to overlay on the avatar video
    - avatar_video: S3 URL to the avatar video
    - real_video: S3 URL to the real demo video
    - bgm: Optional path or S3 URL to background music
    - text_position: Position of text ("top", "center", "bottom")

    Returns:
    - JSON with the final video path
    """
    # Validate text_position
    valid_positions = ["top", "center", "bottom"]
    if request.text_position not in valid_positions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid text_position. Must be one of: {valid_positions}",
        )


    print('------------REQUEST-------------')
    print(request)
    print('------------REQUEST-------------')

    # Define local paths for downloaded files
    avatar_local_path = os.path.join(DOWNLOADS_DIR, "avatar.mp4")
    real_local_path = os.path.join(DOWNLOADS_DIR, "real_video.mp4")
    bgm_local_path = os.path.join(DOWNLOADS_DIR,"bgm_1.mp4") 

    # Step 0: Download videos from S3
    try:
        download_from_s3(request.avatar_video, avatar_local_path)
        download_from_s3(request.real_video, real_local_path)
        download_from_s3(request.bgm,bgm_local_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

    # Step 1: Overlay text on avatar video
    try:
        avatar_with_text_path = os.path.join(DOWNLOADS_DIR, "avatar_with_text.mp4")
        add_text_to_avatar(
            video_path=avatar_local_path,
            text=request.text,
            position=request.text_position,
            fontStyle="poppins",  # Default font
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
            # Check if bgm is an S3 URL; download if so
            if request.bgm.startswith("s3://") or "s3" in request.bgm:
                bgm_local_path = os.path.join(DOWNLOADS_DIR, "bgm_1.mp3")
                download_from_s3(request.bgm, bgm_local_path)
            else:
                bgm_local_path = request.bgm  # Assume local path if not S3

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

    # Return the final video path
    return {"final_video_path": final_output_path}


# @app.post("/process-video/")
# async def process_video(request: VideoRequest):
#     """
#     Process a video by overlaying text, concatenating videos, and optionally adding BGM.

#     Parameters (in request body):
#     - text: Text to overlay on the avatar video
#     - avatar_video: Path to the avatar video
#     - real_video: Path to the real demo video
#     - bgm: Optional path to background music
#     - text_position: Position of text ("top", "center", "bottom")

#     Returns:
#     - JSON with the final video path
#     """
#     # Validate text_position
#     valid_positions = ["top", "center", "bottom"]
#     if request.text_position not in valid_positions:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Invalid text_position. Must be one of: {valid_positions}",
#         )

#     print(request)

#     # Step 1: Overlay text on avatar video
#     try:
#         avatar_with_text_path = os.path.join(
#             BASE_DIR, "downloads", "avatar_with_text.mp4"
#         )
#         add_text_to_avatar(
#             # video_path=request.avatar_video,
#             video_path="downloads/avatar.mp4", # testing
#             text=request.text,
#             position=request.text_position,
#             fontStyle=request.fontStyle,  # Default font, adjustable if needed
#             output_path=avatar_with_text_path,
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Step 1 failed: {str(e)}")

#     # Step 2: Concatenate avatar video (with text) and real video
#     try:
#         combined_vid_path = os.path.join(BASE_DIR, "downloads", "combined_vid.mp4")
#         success, result = concat_videos(
#             avatar_vid=avatar_with_text_path,
#             # real_demo_vid=request.real_video,
#             real_demo_vid="downloads/real_video.mp4",
#             output_path=combined_vid_path,
#         )
#         if not success:
#             raise Exception(result)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Step 2 failed: {str(e)}")

#     # Step 3: Add BGM if provided, otherwise skip
#     final_output_path = combined_vid_path
#     if request.bgm:
#         try:
#             final_output_path = os.path.join(
#                 BASE_DIR, "downloads", "combined_vid_with_bgm.mp4"
#             )
#             success, result = add_bgm_to_video(
#                 video_path=combined_vid_path,
#                 # bgm_path=f"assets/{request.bgm}",
#                 bgm_path="assets/bgm_1.mp3",
#                 output_path=final_output_path,
#                 bgm_volume=0.3,  # Default volume, adjustable if needed
#             )
#             if not success:
#                 raise Exception(result)
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"Step 3 failed: {str(e)}")

#     # Return the final video path
#     return {"final_video_path": final_output_path}
