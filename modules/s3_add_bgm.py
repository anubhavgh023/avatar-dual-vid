import subprocess
import os
from typing import Tuple

# Get the directory of the current script (modules/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define paths relative to the root directory
COMBINED_VID = os.path.join(BASE_DIR, "..", "downloads", "combined_vid.mp4")
BGM = os.path.join(
    BASE_DIR, "..", "assets", "bgm_1.mp3"
)  # Adjust if bgm_1.mp3 is different


def add_bgm_to_video(
    video_path: str = COMBINED_VID,
    bgm_path: str = BGM,
    output_path: str = None,
    bgm_volume: float = 0.25,
) -> Tuple[bool, str]:
    """
    Add background music to a video using FFmpeg without re-encoding the video stream,
    preserving the original audio and mixing it with BGM at adjustable volume.

    Parameters:
    -----------
    video_path : str
        Path to the input video file (default: combined_vid.mp4)
    bgm_path : str
        Path to the background music file (default: bgm_1.mp3)
    output_path : str, optional
        Path for the output video file. If None, generates a default name.
    bgm_volume : float, optional
        Volume level for the BGM (0.0 to 1.0, where 1.0 is full volume, default: 0.25)

    Returns:
    --------
    Tuple[bool, str]
        (success_status, output_path_or_error_message)
    """
    # Validate input paths
    if not os.path.exists(video_path):
        return False, f"Video file not found at: {video_path}"
    if not os.path.exists(bgm_path):
        return False, f"Background music file not found at: {bgm_path}"

    # Validate bgm_volume
    if not 0.0 <= bgm_volume <= 1.0:
        return False, f"bgm_volume must be between 0.0 and 1.0, got {bgm_volume}"

    # Set default output path if not provided
    if output_path is None:
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(
            BASE_DIR, "..", "downloads", f"{video_name}_with_bgm.mp4"
        )

    # Make sure the output directory exists
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    # FFmpeg command to add background music while keeping original audio
    ffmpeg_cmd = [
        "ffmpeg",
        "-i",
        video_path,  # Input video
        "-i",
        bgm_path,  # Input background music
        "-c:v",
        "copy",  # Copy video stream without re-encoding
        "-filter_complex",
        # Extract audio from original video and BGM, adjust BGM volume, mix them together
        f"[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[original];"
        f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume={bgm_volume}[bgm];"
        f"[original][bgm]amix=inputs=2:duration=shortest[a]",
        "-map",
        "0:v:0",  # Map video from first input
        "-map",
        "[a]",  # Map mixed audio
        "-c:a",
        "aac",  # Encode audio to AAC
        "-shortest",  # Match output duration to shortest input
        "-y",  # Overwrite output file if exists
        output_path,
    ]

    try:
        # Execute FFmpeg command
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"FFmpeg error: {result.stderr}"
        return True, output_path
    except Exception as e:
        return False, f"Error adding background music: {str(e)}"


# Example usage
if __name__ == "__main__":
    success, result = add_bgm_to_video(bgm_volume=0.25)  # Set BGM to 25% volume
    if success:
        print(f"Background music added successfully. Output saved at: {result}")
    else:
        print(f"Error: {result}")
