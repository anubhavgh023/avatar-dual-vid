

import os
from moviepy.editor import (
    VideoFileClip,
    clips_array,
    concatenate_videoclips,
)
import concurrent.futures


def combine_videos_vertically(game_vid, real_vid, position="top", output_path=None):
    """
    Optimized version to combine two videos vertically with a 9:16 aspect ratio using MoviePy.
    The game video will loop to match the duration of the real video.

    Args:
        game_vid (str): Path to the game video file
        real_vid (str): Path to the real video file
        position (str): Position of the real video, either "top" or "bottom"
        output_path (str, optional): Path for the output video

    Returns:
        str: Path to the output video file
    """
    # Get the directory of the current script (modules/)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Define default output path if not provided
    if output_path is None:
        output_path = os.path.join(
            BASE_DIR, "..", "downloads", "vertical_combined_vid.mp4"
        )

    try:
        # Load videos with optimized settings
        # Set audio=False for game clip since we'll discard it anyway
        game_clip = VideoFileClip(game_vid, audio=False, target_resolution=(None, None))
        real_clip = VideoFileClip(real_vid, target_resolution=(None, None))

        # Get the duration of the real video
        real_duration = real_clip.duration

        # Target dimensions for 9:16 aspect ratio
        target_width = 900
        target_height = 1600

        # Calculate heights for each video (60% for real_vid, 40% for game_vid)
        real_height = int(target_height * 0.6)  # 960px
        game_height = target_height - real_height  # 640px

        # Use concurrent processing for parallel clip processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Define functions to process each clip
            def process_game_clip():
                # For game clip (no audio)
                gc = game_clip

                # Resize while maintaining aspect ratio
                game_aspect = gc.w / gc.h
                target_game_aspect = target_width / game_height

                if game_aspect > target_game_aspect:
                    # Video is wider than target - resize to match height, then crop width
                    gc = gc.resize(height=game_height)
                    # Crop to target width
                    x_center = gc.w / 2
                    gc = gc.crop(
                        x1=x_center - target_width / 2,
                        y1=0,
                        x2=x_center + target_width / 2,
                        y2=game_height,
                    )
                else:
                    # Video is taller than target - resize to match width, then crop height
                    gc = gc.resize(width=target_width)
                    # Crop to target height
                    y_center = gc.h / 2
                    gc = gc.crop(
                        x1=0,
                        y1=y_center - game_height / 2,
                        x2=target_width,
                        y2=y_center + game_height / 2,
                    )

                # Loop the game clip to match real video duration
                game_duration = gc.duration

                # Create a looping version of the game clip
                if real_duration > game_duration:
                    # Calculate how many full loops we need
                    num_loops = int(real_duration / game_duration) + 1

                    # Create a list of the same clip repeated
                    loop_clips = [gc.copy() for _ in range(num_loops)]

                    # Concatenate them
                    looped_gc = concatenate_videoclips(loop_clips)

                    # Trim to exact real video duration
                    looped_gc = looped_gc.subclip(0, real_duration)

                    return looped_gc
                else:
                    # If game video is already longer, just trim it
                    return gc.subclip(0, real_duration)

            def process_real_clip():
                # For real clip (keeping audio)
                rc = real_clip
                real_aspect = rc.w / rc.h
                target_real_aspect = target_width / real_height

                if real_aspect > target_real_aspect:
                    # Video is wider than target - resize to match height, then crop width
                    rc = rc.resize(height=real_height)
                    # Crop to target width
                    x_center = rc.w / 2
                    rc = rc.crop(
                        x1=x_center - target_width / 2,
                        y1=0,
                        x2=x_center + target_width / 2,
                        y2=real_height,
                    )
                else:
                    # Video is taller than target - resize to match width, then crop height
                    rc = rc.resize(width=target_width)
                    # Crop to target height
                    y_center = rc.h / 2
                    rc = rc.crop(
                        x1=0,
                        y1=y_center - real_height / 2,
                        x2=target_width,
                        y2=y_center + real_height / 2,
                    )
                return rc

            # Process clips in parallel
            game_future = executor.submit(process_game_clip)
            real_future = executor.submit(process_real_clip)

            # Get processed clips
            game_clip = game_future.result()
            real_clip = real_future.result()

        # Create the vertical stack based on position
        if position.lower() == "top":
            clips = [[real_clip], [game_clip]]
        else:
            clips = [[game_clip], [real_clip]]

        # Create final clip with correct dimensions
        final_clip = clips_array(clips)

        # Make sure dimensions are exactly 900x1600 (only if needed)
        if final_clip.w != target_width or final_clip.h != target_height:
            final_clip = final_clip.resize((target_width, target_height))

        # Write the output file with optimized settings
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            threads=os.cpu_count(),
            preset="faster",  # Use a faster preset for encoding
            bitrate="4000k",  # Adjust bitrate as needed
        )

        # Close clips to release resources
        game_clip.close()
        real_clip.close()
        final_clip.close()

        print(f"Successfully created combined video: {output_path}")
        return output_path

    except Exception as e:
        print(f"Error combining videos: {str(e)}")
        return None


# Example usage
if __name__ == "__main__":
    # Get the directory of the current script (modules/)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Define paths relative to the root directory
    GAME_VIDEO = os.path.join(BASE_DIR, "..", "downloads", "avatar.mp4")
    REAL_VIDEO = os.path.join(BASE_DIR, "..", "downloads", "real_video.mp4")
    OUTPUT_PATH = os.path.join(BASE_DIR, "..", "downloads", "vertical_combined_vid.mp4")

    # Combine videos
    result = combine_videos_vertically(
        GAME_VIDEO, REAL_VIDEO, position="top", output_path=OUTPUT_PATH
    )
    if result:
        print(f"Successfully created combined video: {result}")
    else:
        print("Failed to create combined video")
