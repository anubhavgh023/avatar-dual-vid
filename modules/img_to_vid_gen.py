import os
import time
import requests
import json
import base64
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image
from moviepy.editor import VideoFileClip
from celery_config import app as celery_app
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# MiniMax API configuration
API_KEY = os.getenv("MINIMAX_API_KEY")
BASE_URL = "https://api.minimaxi.chat/v1"
VIDEO_GENERATION_URL = f"{BASE_URL}/video_generation"
QUERY_STATUS_URL = f"{BASE_URL}/query/video_generation"
FILE_RETRIEVE_URL = f"{BASE_URL}/files/retrieve"

# Base directory for output
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(os.path.dirname(BASE_DIR), "downloads")

def validate_image(image_path: str) -> bool:
    """Validate the input image against MiniMax requirements."""
    if not os.path.exists(image_path):
        raise Exception(f"Image file not found: {image_path}")

    file_extension = os.path.splitext(image_path)[1].lower()
    if file_extension not in [".jpg", ".jpeg", ".png"]:
        raise Exception("Image must be in JPG or PNG format")

    file_size = os.path.getsize(image_path) / (1024 * 1024)
    if file_size > 20:
        raise Exception(f"Image size ({file_size:.2f}MB) exceeds 20MB limit")

    with Image.open(image_path) as img:
        width, height = img.size
        aspect_ratio = width / height
        min_side = min(width, height)
        if not (0.4 <= aspect_ratio <= 2.5):
            raise Exception(
                f"Image aspect ratio ({aspect_ratio:.2f}) must be between 2:5 (0.4) and 5:2 (2.5)"
            )
        if min_side <= 300:
            raise Exception(f"Image shorter side ({min_side}px) must exceed 300 pixels")

    return True

def resize_to_9_16(input_path: str, output_path: str) -> None:
    """Resize/crop the video to 9:16 aspect ratio (576x1024) using MoviePy."""
    try:
        clip = VideoFileClip(input_path)
        width, height = clip.size
        center_x = width / 2
        target_width = height * 9 / 16

        if target_width <= width:
            x1 = center_x - (target_width / 2)
            x2 = center_x + (target_width / 2)
            cropped_clip = clip.crop(x1=x1, y1=0, x2=x2, y2=height)
        else:
            target_height = width * 16 / 9
            center_y = height / 2
            y1 = center_y - (target_height / 2)
            y2 = center_y + (target_height / 2)
            cropped_clip = clip.crop(x1=0, y1=y1, x2=width, y2=y2)

        final_clip = cropped_clip.resize(width=576, height=1024)
        final_clip.write_videofile(
            output_path, codec="libx264", audio_codec="aac", preset="medium", fps=24
        )

        final_clip.close()
        cropped_clip.close()
        clip.close()
        logger.info(f"Video resized to 9:16 (576x1024) at: {output_path}")
    except Exception as e:
        logger.error(f"Failed to resize video with MoviePy: {str(e)}")
        raise

@celery_app.task(bind=True)
def generate_video_task(self, image_path: str, prompt: str = None) -> dict:
    """
    Celery task to generate a cinematic video from an image using MiniMax's I2V-01-Director model.
    """
    logger.info(f"Starting task for image: {image_path}, prompt: {prompt}")
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Validating image'})
        logger.info("Validating image")
        validate_image(image_path)
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)

        self.update_state(state='PROGRESS', meta={'status': 'Encoding image'})
        logger.info("Encoding image to base64")
        file_extension = os.path.splitext(image_path)[1].lower()
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")
            image_base64 = f"data:image/{'jpeg' if file_extension in ['.jpg', '.jpeg'] else 'png'};base64,{image_data}"

        if not prompt:
            prompt = (
                "A romantic scene extends from the input image in a 9:16 frame, set in an elegant restaurant at dusk, "
                "illuminated by flickering candlelight. The girl, seated at a beautifully set table, smiles softly as she "
                "lifts a wine glass, her eyes sparkling with warmth. She brushes a strand of hair behind her ear, while her "
                "date leans forward, sharing a quiet laugh. The vertical composition captures the intimate table setting and "
                "overhead chandeliers. The camera begins with a [Static shot] to frame the tender moment, then [Pushes in] "
                "to focus on the girl’s radiant smile, and ends with a [Tilt up] to reveal the glowing ambiance of the "
                "restaurant’s decor, with cinematic lighting and smooth, fluid motion."
            )

        self.update_state(state='PROGRESS', meta={'status': 'Submitting video generation task'})
        logger.info("Submitting video generation task")
        payload = json.dumps({
            "model": "I2V-01-Director",
            "prompt": prompt,
            "first_frame_image": image_base64,
            "prompt_optimizer": True,
        })
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(VIDEO_GENERATION_URL, headers=headers, data=payload)
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"API response: {json.dumps(response_data, indent=2)}")

        status_code = response_data.get("base_resp", {}).get("status_code", -1)
        status_msg = response_data.get("base_resp", {}).get("status_msg", "Unknown error")
        if status_code != 0:
            raise Exception(f"API error (status_code: {status_code}): {status_msg}")

        task_id = response_data.get("task_id")
        if not task_id:
            raise Exception("No task_id returned from API")
        logger.info(f"Video generation task submitted successfully, task ID: {task_id}")

        self.update_state(state='PROGRESS', meta={'status': 'Polling for video generation status'})
        logger.info("Polling for video generation status")
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(20)
            url = f"{QUERY_STATUS_URL}?task_id={task_id}"
            headers = {"Authorization": f"Bearer {API_KEY}"}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()
            logger.info(f"API response: {json.dumps(result, indent=2)}")

            status = result.get("status")
            status_code = result.get("base_resp", {}).get("status_code", -1)
            status_msg = result.get("base_resp", {}).get("status_msg", "Unknown error")
            if status_code != 0:
                raise Exception(f"Query error (status_code: {status_code}): {status_msg}")

            logger.info(f"Task status: {status} (attempt {attempt + 1}/{max_attempts})")
            self.update_state(state='PROGRESS', meta={'status': f'Processing (attempt {attempt + 1}/{max_attempts})'})

            if status == "Success":
                file_id = result.get("file_id")
                if not file_id:
                    raise Exception("No file_id returned for successful task")
                break
            elif status in ["Fail", "Unknown"]:
                raise Exception(f"Video generation failed with status: {status}")
            elif status in ["Queueing", "Preparing", "Processing"]:
                continue
            else:
                raise Exception(f"Unknown task status: {status}")
        else:
            raise Exception("Timed out waiting for video generation")

        self.update_state(state='PROGRESS', meta={'status': 'Downloading video'})
        logger.info("Video generated successfully, downloading now")
        url = f"{FILE_RETRIEVE_URL}?file_id={file_id}"
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"API response: {json.dumps(response_data, indent=2)}")

        status_code = response_data.get("base_resp", {}).get("status_code", -1)
        status_msg = response_data.get("base_resp", {}).get("status_msg", "Unknown error")
        if status_code != 0:
            raise Exception(f"File retrieval error (status_code: {status_code}): {status_msg}")

        download_url = response_data.get("file", {}).get("download_url")
        if not download_url:
            raise Exception("No download_url returned from API")

        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        temp_output_path = os.path.join(DOWNLOADS_DIR, f"temp_video_{current_time}.mp4")
        final_output_path = os.path.join(DOWNLOADS_DIR, f"video_{current_time}.mp4")

        logger.info(f"Downloading video to: {temp_output_path}")
        with open(temp_output_path, "wb") as f:
            f.write(requests.get(download_url).content)
        logger.info(f"Video downloaded to temporary path: {temp_output_path}")

        self.update_state(state='PROGRESS', meta={'status': 'Resizing video to 9:16'})
        logger.info("Resizing video to 9:16")
        resize_to_9_16(temp_output_path, final_output_path)
        os.remove(temp_output_path)
        logger.info(f"Final 9:16 video saved to: {final_output_path}")

        return {"success": True, "video_path": final_output_path, "error": None}
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        self.update_state(state='FAILURE', meta={'status': 'Failed', 'error': str(e)})
        raise  # Raise the exception to let Celery handle it properly

def generate_video_from_image(image_path: str, prompt: str = None) -> str:
    """Wrapper function to queue a Celery task for video generation."""
    logger.info(f"Queuing video generation task for image: {image_path}")
    task = generate_video_task.delay(image_path, prompt)
    return task.id

if __name__ == "__main__":
    try:
        image_path = "generated_image.jpg"
        task_id = generate_video_from_image(image_path)
        logger.info(f"Video generation task queued with ID: {task_id}")
    except Exception as e:
        logger.error(f"Error: {str(e)}")

        
        
# ============================

# working: timing issues no message queue
# import os
# import time
# import requests
# import json
# import base64
# from datetime import datetime
# from dotenv import load_dotenv
# from PIL import Image
# from moviepy.editor import VideoFileClip

# # Load environment variables
# load_dotenv()

# # MiniMax API configuration
# API_KEY = os.getenv("MINIMAX_API_KEY")
# BASE_URL = "https://api.minimaxi.chat/v1"
# VIDEO_GENERATION_URL = f"{BASE_URL}/video_generation"
# QUERY_STATUS_URL = f"{BASE_URL}/query/video_generation"
# FILE_RETRIEVE_URL = f"{BASE_URL}/files/retrieve"

# # Base directory for output (consistent with main.py)
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DOWNLOADS_DIR = os.path.join(os.path.dirname(BASE_DIR), "downloads")


# def validate_image(image_path: str) -> bool:
#     """Validate the input image against MiniMax requirements."""
#     if not os.path.exists(image_path):
#         raise Exception(f"Image file not found: {image_path}")

#     file_extension = os.path.splitext(image_path)[1].lower()
#     if file_extension not in [".jpg", ".jpeg", ".png"]:
#         raise Exception("Image must be in JPG or PNG format")

#     file_size = os.path.getsize(image_path) / (1024 * 1024)
#     if file_size > 20:
#         raise Exception(f"Image size ({file_size:.2f}MB) exceeds 20MB limit")

#     with Image.open(image_path) as img:
#         width, height = img.size
#         aspect_ratio = width / height
#         min_side = min(width, height)
#         if not (0.4 <= aspect_ratio <= 2.5):
#             raise Exception(
#                 f"Image aspect ratio ({aspect_ratio:.2f}) must be between 2:5 (0.4) and 5:2 (2.5)"
#             )
#         if min_side <= 300:
#             raise Exception(f"Image shorter side ({min_side}px) must exceed 300 pixels")

#     return True



# def resize_to_9_16(input_path: str, output_path: str) -> None:
#     """
#     Resize/crop the video to 9:16 aspect ratio (576x1024) using MoviePy.

#     Args:
#         input_path (str): Path to the input video file
#         output_path (str): Path to save the resized video
#     """
#     try:
#         # Load the video clip
#         clip = VideoFileClip(input_path)

#         # Get original dimensions
#         width, height = clip.size

#         # Calculate the center point for cropping
#         center_x = width / 2

#         # Calculate desired width based on 9:16 ratio from current height
#         # If the video is already narrower than the target ratio, we'll need to crop height instead
#         target_width = height * 9 / 16

#         if target_width <= width:
#             # Crop width to achieve 9:16
#             x1 = center_x - (target_width / 2)
#             x2 = center_x + (target_width / 2)
#             cropped_clip = clip.crop(x1=x1, y1=0, x2=x2, y2=height)
#         else:
#             # Crop height to achieve 9:16
#             target_height = width * 16 / 9
#             center_y = height / 2
#             y1 = center_y - (target_height / 2)
#             y2 = center_y + (target_height / 2)
#             cropped_clip = clip.crop(x1=0, y1=y1, x2=width, y2=y2)

#         # Resize to 576x1024
#         final_clip = cropped_clip.resize(width=576, height=1024)

#         # Write the result
#         final_clip.write_videofile(
#             output_path, codec="libx264", audio_codec="aac", preset="medium", fps=24
#         )

#         # Close the clips to release resources
#         final_clip.close()
#         cropped_clip.close()
#         clip.close()

#         print(f"Video resized to 9:16 (576x1024) at: {output_path}")

#     except Exception as e:
#         raise Exception(f"Failed to resize video with MoviePy: {str(e)}")


# # def resize_to_9_16(input_path: str, output_path: str) -> None:
# #     """Resize/crop the video to 9:16 aspect ratio (576x1024) using ffmpeg."""
# #     try:
# #         cmd = [
# #             "ffmpeg",
# #             "-i",
# #             input_path,
# #             "-vf",
# #             "crop=720:1280,scale=576:1024",
# #             "-c:a",
# #             "copy",
# #             "-y",
# #             output_path,
# #         ]
# #         subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# #         print(f"Video resized to 9:16 (576x1024) at: {output_path}")
# #     except subprocess.CalledProcessError as e:
# #         raise Exception(f"Failed to resize video with ffmpeg: {e.stderr.decode()}")
# #     except FileNotFoundError:
# #         raise Exception(
# #             "ffmpeg not found. Please install ffmpeg and ensure it's in PATH."
# #         )


# def generate_video_from_image(image_path: str, prompt: str = None) -> str:
#     """
#     Generate a cinematic video from an image using MiniMax's I2V-01-Director model.

#     Parameters:
#     -----------
#     image_path : str
#         Local path to the input image (JPG/PNG, aspect ratio 2:5 to 5:2, shorter side >300px, <20MB).
#     prompt : str, optional
#         Descriptive prompt for video generation with camera movement instructions.
#         If None, a default cinematic prompt is used tailored to the 9:16 aspect ratio.

#     Returns:
#     --------
#     str
#         Local path to the downloaded and resized video file.
#     """
#     # Step 1: Validate inputs
#     if not API_KEY:
#         raise Exception("MINIMAX_API_KEY environment variable not set")

#     validate_image(image_path)
#     os.makedirs(DOWNLOADS_DIR, exist_ok=True)

#     # Step 2: Convert image to base64
#     try:
#         file_extension = os.path.splitext(image_path)[1].lower()
#         with open(image_path, "rb") as image_file:
#             image_data = base64.b64encode(image_file.read()).decode("utf-8")
#             image_base64 = f"data:image/{'jpeg' if file_extension in ['.jpg', '.jpeg'] else 'png'};base64,{image_data}"
#     except Exception as e:
#         raise Exception(f"Failed to encode image to base64: {str(e)}")

#     # Step 3: Craft cinematic prompt
#     if not prompt:
#         prompt = (
#             "A romantic scene extends from the input image in a 9:16 frame, set in an elegant restaurant at dusk, illuminated by flickering candlelight. The girl, seated at a beautifully set table, smiles softly as she lifts a wine glass, her eyes sparkling with warmth. She brushes a strand of hair behind her ear, while her date leans forward, sharing a quiet laugh. The vertical composition captures the intimate table setting and overhead chandeliers. The camera begins with a [Static shot] to frame the tender moment, then [Pushes in] to focus on the girl’s radiant smile, and ends with a [Tilt up] to reveal the glowing ambiance of the restaurant’s decor, with cinematic lighting and smooth, fluid motion."
#         )

#     # Step 4: Submit video generation task
#     try:
#         print("Submitting video generation task...")
#         payload = json.dumps(
#             {
#                 "model": "I2V-01-Director",
#                 "prompt": prompt,
#                 "first_frame_image": image_base64,
#                 "prompt_optimizer": True,
#             }
#         )
#         headers = {
#             "Authorization": f"Bearer {API_KEY}",
#             "Content-Type": "application/json",
#         }
#         response = requests.post(VIDEO_GENERATION_URL, headers=headers, data=payload)
#         response.raise_for_status()
#         response_data = response.json()
#         print(f"API response: {json.dumps(response_data, indent=2)}")

#         status_code = response_data.get("base_resp", {}).get("status_code", -1)
#         status_msg = response_data.get("base_resp", {}).get(
#             "status_msg", "Unknown error"
#         )
#         if status_code != 0:
#             raise Exception(f"API error (status_code: {status_code}): {status_msg}")

#         task_id = response_data.get("task_id")
#         if not task_id:
#             raise Exception("No task_id returned from API")
#         print(f"Video generation task submitted successfully, task ID: {task_id}")
#     except requests.exceptions.HTTPError as e:
#         raise Exception(
#             f"Failed to submit video generation task: HTTP error - {str(e)} - {response.text}"
#         )
#     except Exception as e:
#         raise Exception(f"Failed to submit video generation task: {str(e)}")

#     # Step 5: Poll for task status
#     try:
#         print("Polling for video generation status...")
#         max_attempts = 30  # Updated to 30 attempts
#         for attempt in range(max_attempts):
#             time.sleep(20)  # Updated to 20 seconds
#             url = f"{QUERY_STATUS_URL}?task_id={task_id}"
#             headers = {"Authorization": f"Bearer {API_KEY}"}
#             response = requests.get(url, headers=headers)
#             response.raise_for_status()
#             result = response.json()
#             print(f"API response: {json.dumps(result, indent=2)}")

#             status = result.get("status")
#             status_code = result.get("base_resp", {}).get("status_code", -1)
#             status_msg = result.get("base_resp", {}).get("status_msg", "Unknown error")
#             if status_code != 0:
#                 raise Exception(
#                     f"Query error (status_code: {status_code}): {status_msg}"
#                 )

#             print(f"Task status: {status} (attempt {attempt + 1}/{max_attempts})")

#             if status == "Success":
#                 file_id = result.get("file_id")
#                 if not file_id:
#                     raise Exception("No file_id returned for successful task")
#                 break
#             elif status in ["Fail", "Unknown"]:
#                 raise Exception(f"Video generation failed with status: {status}")
#             elif status in ["Queueing", "Preparing", "Processing"]:
#                 continue
#             else:
#                 raise Exception(f"Unknown task status: {status}")
#         else:
#             raise Exception("Timed out waiting for video generation")
#     except requests.exceptions.HTTPError as e:
#         raise Exception(
#             f"Failed to query video generation status: HTTP error - {str(e)} - {response.text}"
#         )
#     except Exception as e:
#         raise Exception(f"Failed to query video generation status: {str(e)}")

#     # Step 6: Retrieve and download the video
#     try:
#         print("Video generated successfully, downloading now...")
#         url = f"{FILE_RETRIEVE_URL}?file_id={file_id}"
#         headers = {"Authorization": f"Bearer {API_KEY}"}
#         response = requests.get(url, headers=headers)
#         response.raise_for_status()
#         response_data = response.json()
#         print(f"API response: {json.dumps(response_data, indent=2)}")

#         status_code = response_data.get("base_resp", {}).get("status_code", -1)
#         status_msg = response_data.get("base_resp", {}).get(
#             "status_msg", "Unknown error"
#         )
#         if status_code != 0:
#             raise Exception(
#                 f"File retrieval error (status_code: {status_code}): {status_msg}"
#             )

#         download_url = response_data.get("file", {}).get("download_url")
#         if not download_url:
#             raise Exception("No download_url returned from API")

#         current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
#         temp_output_path = os.path.join(DOWNLOADS_DIR, f"temp_video_{current_time}.mp4")
#         final_output_path = os.path.join(DOWNLOADS_DIR, f"video_{current_time}.mp4")

#         with open(temp_output_path, "wb") as f:
#             f.write(requests.get(download_url).content)
#         print(f"Video downloaded to temporary path: {temp_output_path}")
#     except requests.exceptions.HTTPError as e:
#         raise Exception(
#             f"Failed to download video: HTTP error - {str(e)} - {response.text}"
#         )
#     except Exception as e:
#         raise Exception(f"Failed to download video: {str(e)}")

#     # Step 7: Resize video to 9:16 (576x1024)
#     try:
#         resize_to_9_16(temp_output_path, final_output_path)
#         os.remove(temp_output_path)
#         print(f"Final 9:16 video saved to: {final_output_path}")
#         return final_output_path
#     except Exception as e:
#         raise Exception(f"Failed to process video to 9:16: {str(e)}")


# if __name__ == "__main__":
#     try:
#         image_path = "generated_image.jpg"  # Replace with your image path
#         video_path = generate_video_from_image(image_path)
#         print(f"Video generated successfully at: {video_path}")
#     except Exception as e:
#         print(f"Error: {str(e)}")
