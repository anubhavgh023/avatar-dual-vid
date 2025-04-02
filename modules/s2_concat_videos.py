import os
from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips,
    AudioFileClip,
    concatenate_audioclips,
    AudioClip,
)
from typing import Tuple

# Get the directory of the current script (modules/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define paths relative to the root directory
AVATAR_VIDEO = os.path.join(BASE_DIR, "..", "downloads", "avatar.mp4")
DEMO_VIDEO = os.path.join(BASE_DIR, "..", "downloads", "real_video.mp4")
OUTPUT_PATH = os.path.join(BASE_DIR, "..", "downloads", "combined_vid.mp4")


def concat_videos(
    avatar_vid: str, real_demo_vid: str, output_path: str = None
) -> Tuple[bool, str]:
    """
    Concatenate two videos using MoviePy with no pause. Audio from real_demo_vid only plays
    during its portion, not during avatar_vid.

    Args:
        avatar_vid (str): Path to the first video (avatar video, no audio in output)
        real_demo_vid (str): Path to the second video (real demo video, with audio if present)
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

        # Process clips
        avatar_clip = resize_clip(
            avatar_clip
        ).without_audio()  # Ensure no audio for avatar
        demo_clip = resize_clip(demo_clip)

        # Concatenate video clips
        final_clip = concatenate_videoclips([avatar_clip, demo_clip], method="compose")

        # Handle audio: silence during avatar, then demo audio
        if demo_clip.audio:
            avatar_duration = avatar_clip.duration
            # Create a silent audio clip for the avatar duration
            silent_audio = AudioClip(
                make_frame=lambda t: 0,
                duration=avatar_duration,
                fps=demo_clip.audio.fps,
            )
            # Concatenate silent audio with demo audio
            final_audio = concatenate_audioclips([silent_audio, demo_clip.audio])
            final_clip = final_clip.set_audio(final_audio)
        # If no audio in demo_clip, final_clip remains silent (due to .without_audio() on avatar)

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
        if demo_clip.audio:
            silent_audio.close()
            final_audio.close()
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