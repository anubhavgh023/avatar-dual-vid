import os
from moviepy.editor import VideoFileClip, concatenate_videoclips
from typing import Tuple

# Get the directory of the current script (modules/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define paths relative to the root directory
AVATAR_VIDEO = os.path.join(BASE_DIR, "..", "downloads", "avatar.mp4")
DEMO_VIDEO = os.path.join(BASE_DIR, "..", "downloads", "real_demo.mp4")
OUTPUT_PATH = os.path.join(BASE_DIR, "..", "downloads", "combined_vid.mp4")


def concat_videos(
    avatar_vid: str, real_demo_vid: str, output_path: str = None
) -> Tuple[bool, str]:
    """
    Concatenate two videos using MoviePy with no pause, handling cases with/without audio.

    Args:
        avatar_vid (str): Path to the first video (avatar video)
        real_demo_vid (str): Path to the second video (real demo video)
        output_path (str, optional): Path for the output video. If None, generates a default name.

    Returns:
        Tuple[bool, str]: (success_status, output_path_or_error_message)
    """
    # Validate inputs
    if not os.path.exists(avatar_vid):
        return False, f"Avatar video file does not exist: {avatar_vid}"
    if not os.path.exists(real_demo_vid):
        return False, f"Real demo video file does not exist: {real_demo_vid}"

    # Set default output path if not provided
    if output_path is None:
        avatar_name = os.path.splitext(os.path.basename(avatar_vid))[0]
        demo_name = os.path.splitext(os.path.basename(real_demo_vid))[0]
        output_path = f"concat_{avatar_name}_{demo_name}.mp4"

    try:
        # Load video clips
        avatar_clip = VideoFileClip(avatar_vid)
        demo_clip = VideoFileClip(real_demo_vid)

        # Target resolution (720x1280, matching your inputs)
        target_width = 720
        target_height = 1280

        # Resize and pad/crop to target resolution
        def resize_clip(clip):
            aspect = clip.w / clip.h
            target_aspect = target_width / target_height

            if aspect > target_aspect:
                # Wider than target: resize to height, crop width
                clip = clip.resize(height=target_height)
                x_center = clip.w / 2
                clip = clip.crop(
                    x1=x_center - target_width / 2,
                    x2=x_center + target_width / 2,
                    y1=0,
                    y2=target_height,
                )
            else:
                # Taller than target: resize to width, crop height
                clip = clip.resize(width=target_width)
                y_center = clip.h / 2
                clip = clip.crop(
                    x1=0,
                    x2=target_width,
                    y1=y_center - target_height / 2,
                    y2=y_center + target_height / 2,
                )
            return clip.set_fps(30)  # Set consistent frame rate

        avatar_clip = resize_clip(avatar_clip)
        demo_clip = resize_clip(demo_clip)

        # Concatenate videos
        final_clip = concatenate_videoclips([avatar_clip, demo_clip], method="compose")

        # Use audio from real_demo_vid if available, otherwise keep avatar's or none
        if demo_clip.audio:
            final_clip = final_clip.set_audio(demo_clip.audio)
        elif avatar_clip.audio:
            final_clip = final_clip.set_audio(avatar_clip.audio)

        # Write output
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="fast",
            threads=os.cpu_count(),
            bitrate="4000k",
        )

        # Clean up
        avatar_clip.close()
        demo_clip.close()
        final_clip.close()

        return True, output_path

    except Exception as e:
        return False, f"Error concatenating videos: {str(e)}"


# Example usage
if __name__ == "__main__":
    avatar_video = AVATAR_VIDEO
    demo_video = DEMO_VIDEO

    success, result = concat_videos(avatar_video, demo_video, OUTPUT_PATH)

    if success:
        print(f"Videos concatenated successfully. Output saved at: {result}")
    else:
        print(f"Error: {result}")




# FFMPEG version, giving errors, and having edge cases
# import subprocess
# import os
# from typing import Tuple

# # Get the directory of the current script (modules/)
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# # Define paths relative to the root directory
# AVATAR_VIDEO = os.path.join(BASE_DIR, "..", "downloads", "avatar.mp4")
# DEMO_VIDEO = os.path.join(BASE_DIR, "..", "downloads", "real_demo.mp4")
# OUTPUT_PATH = os.path.join(BASE_DIR, "..", "downloads", "combined_vid.mp4")

# def has_audio_stream(video_path: str) -> bool:
#     """Check if a video file has an audio stream using ffprobe."""
#     probe_cmd = [
#         "ffprobe",
#         "-v",
#         "error",
#         "-show_streams",
#         "-select_streams",
#         "a",
#         video_path,
#     ]
#     probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
#     return bool(probe_result.stdout.strip())

# def concat_videos(
#     avatar_vid: str, real_demo_vid: str, output_path: str = None
# ) -> Tuple[bool, str]:
#     """
#     Concatenate two videos using FFmpeg with no pause, handling cases with/without audio.

#     Args:
#         avatar_vid (str): Path to the first video (avatar video)
#         real_demo_vid (str): Path to the second video (real demo video)
#         output_path (str, optional): Path for the output video. If None, generates a default name.

#     Returns:
#         Tuple[bool, str]: (success_status, output_path_or_error_message)
#     """
#     # Validate inputs
#     if not os.path.exists(avatar_vid):
#         return False, f"Avatar video file does not exist: {avatar_vid}"
#     if not os.path.exists(real_demo_vid):
#         return False, f"Real demo video file does not exist: {real_demo_vid}"

#     # Set default output path if not provided
#     if output_path is None:
#         avatar_name = os.path.splitext(os.path.basename(avatar_vid))[0]
#         demo_name = os.path.splitext(os.path.basename(real_demo_vid))[0]
#         output_path = f"concat_{avatar_name}_{demo_name}.mp4"

#     # Check for audio in both videos
#     avatar_has_audio = has_audio_stream(avatar_vid)
#     demo_has_audio = has_audio_stream(real_demo_vid)

#     # Define the filter complex based on audio presence
#     if avatar_has_audio and demo_has_audio:
#         # Both videos have audio
#         filter_complex = (
#             "[0:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,fps=30[v0];"
#             "[1:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,fps=30[v1];"
#             "[v0][0:a:0][v1][1:a:0]concat=n=2:v=1:a=1[v][a]"
#         )
#     elif avatar_has_audio and not demo_has_audio:
#         # Only avatar has audio
#         filter_complex = (
#             "[0:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih/2,fps=30[v0];"
#             "[1:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,fps=30[v1];"
#             "[v0][0:a:0][v1]concat=n=2:v=1:a=1[v][a]"
#         )
#     elif not avatar_has_audio and demo_has_audio:
#         # Only demo has audio
#         filter_complex = (
#             "[0:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,fps=30[v0];"
#             "[1:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,fps=30[v1];"
#             "[v0][v1][1:a:0]concat=n=2:v=1:a=1[v][a]"
#         )
#     else:
#         # Neither video has audio
#         filter_complex = (
#             "[0:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,fps=30[v0];"
#             "[1:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,fps=30[v1];"
#             "[v0][v1]concat=n=2:v=1:a=0[v]"
#         )

#     # FFmpeg command
#     ffmpeg_cmd = [
#         "ffmpeg",
#         "-i",
#         avatar_vid,
#         "-i",
#         real_demo_vid,
#         "-filter_complex",
#         filter_complex,
#         "-map",
#         "[v]",
#     ]
#     if avatar_has_audio or demo_has_audio:
#         ffmpeg_cmd.extend(["-map", "[a]"])
#     ffmpeg_cmd.extend([
#         "-c:v",
#         "libx264",
#         "-c:a",
#         "aac",
#         "-preset",
#         "fast",
#         "-r",
#         "30",
#         "-y",
#         output_path,
#     ])

#     try:
#         result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
#         if result.returncode != 0:
#             return False, f"FFmpeg error: {result.stderr}"
#         return True, output_path
#     except Exception as e:
#         return False, f"Error concatenating videos: {str(e)}"


# # Example usage
# if __name__ == "__main__":
#     avatar_video = AVATAR_VIDEO
#     demo_video = DEMO_VIDEO

#     success, result = concat_videos(avatar_video, demo_video, OUTPUT_PATH)

#     if success:
#         print(f"Videos concatenated successfully. Output saved at: {result}")
#     else:
#         print(f"Error: {result}")
