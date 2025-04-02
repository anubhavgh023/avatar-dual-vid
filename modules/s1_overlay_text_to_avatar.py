from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import os

# Get the directory of the current script (modules/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define paths relative to the root directory
AVATAR_VIDEO = os.path.join(BASE_DIR, "..", "assets", "avatar.mp4")
DEMO_VIDEO = os.path.join(BASE_DIR, "..", "assets", "real_demo.mp4")

# Global font styles dictionary
FONT_STYLES = {
    "poppins": {
        "font": os.path.join(
            BASE_DIR, "..", "assets", "fonts", "Poppins-ExtraBold.ttf"
        ),
        "size": 48,
    },
    "poetsenOne": {
        "font": os.path.join(
            BASE_DIR, "..", "assets", "fonts", "PoetsenOne-Regular.ttf"
        ),
        "size": 48,
    },
    "alfaSlab": {
        "font": os.path.join(
            BASE_DIR, "..", "assets", "fonts", "AlfaSlabOne-Regular.ttf"
        ),
        "size": 48,
    },
    "titanOne": {
        "font": os.path.join(
            BASE_DIR, "..", "assets", "fonts", "TitanOne-Regular.ttf"
        ),
        "size": 48,
    },
}

# Global settings (unchanged)
FONT_COLOR = "white"
STROKE_COLOR = "black"
STROKE_WIDTH = 2
LETTER_SPACING = -1
INTERLINE_SPACING = -10


def add_text_to_avatar(
    video_path, text, position="center", fontStyle="poppins", output_path=None
):
    """
    Add text overlay to a 9:16 video in the specified position.

    Parameters:
    -----------
    video_path : str
        Path to the input video file
    text : str
        Text to overlay on the video
    position : str
        Where to place the text. Options: "top", "center", "bottom"
    fontStyle : str, optional
        Name of the font style to use from FONT_STYLES (e.g., "poppins", "fredoka")
    output_path : str, optional
        Path for the output video

    Returns:
    --------
    str
        Path to the output video file
    """
    # Validate font style selection
    if fontStyle not in FONT_STYLES:
        raise ValueError(
            f"Font style '{fontStyle}' not found in FONT_STYLES. Available: {list(FONT_STYLES.keys())}"
        )

    selected_style = FONT_STYLES[fontStyle]
    if not os.path.exists(selected_style["font"]):
        raise FileNotFoundError(f"Font file not found at: {selected_style['font']}")

    # Set output path if not provided
    if output_path is None:
        filename, ext = os.path.splitext(video_path)
        output_path = f"{filename}_text{ext}"

    # Load the video and make sure duration is set
    video = VideoFileClip(video_path)

    # Force duration calculation if not already set
    if not hasattr(video, "duration") or video.duration is None:
        video.duration = video.reader.duration

    # # Check if video has 9:16 aspect ratio (with some tolerance)
    width, height = video.size
    # ratio = width / height
    # target_ratio = 9 / 16

    # tolerance = 0.05
    # if abs(ratio - target_ratio) > tolerance:
    #     video.close()
    #     raise ValueError(
    #         f"Video aspect ratio is {width}x{height} ({ratio:.2f}), not 9:16 mobile aspect ratio"
    #     )

    # Create text clip with padding (use width with 40px total padding)
    max_width = int(width * 0.9)  # 90% of video width for padding

    # Split text into lines if it's too long
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        # Estimate if current line is too long (rough estimate)
        if len(" ".join(current_line)) * selected_style["size"] * 0.5 > max_width:
            # Remove last word and add line
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]  # Start new line with current word

    # Add final line
    if current_line:
        lines.append(" ".join(current_line))

    # Join lines with newlines
    wrapped_text = "\n".join(lines)

    # Create text clip using the selected font style
    txt_clip = TextClip(
        wrapped_text,
        fontsize=selected_style["size"],
        color=FONT_COLOR,
        font=selected_style["font"],
        stroke_color=STROKE_COLOR,
        stroke_width=STROKE_WIDTH,
        kerning=LETTER_SPACING,
        interline=INTERLINE_SPACING,
        method="caption",
        align="center",
        size=(max_width, None),
    )

    # Set duration to match video
    txt_clip = txt_clip.set_duration(video.duration)

    # Position the text based on parameter
    if position == "top":
        y_pos = height * 0.1
    elif position == "center":
        y_pos = (height - txt_clip.h) / 2
    elif position == "bottom":
        y_pos = height * 0.8 - txt_clip.h
    else:
        y_pos = (height - txt_clip.h) / 2  # Default to center

    # Set position (centered horizontally)
    txt_clip = txt_clip.set_position(("center", y_pos))

    # Create the final composite clip
    final_clip = CompositeVideoClip([video, txt_clip])

    # Ensure the final clip has the same duration as the video
    final_clip = final_clip.set_duration(video.duration)

    # Write the result
    final_clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast",
        logger=None,
    )

    # Close the clips
    video.close()
    txt_clip.close()
    final_clip.close()

    return output_path


# Example usage
if __name__ == "__main__":
    try:
        # Using default "poppins" style
        output = add_text_to_avatar(
            video_path=AVATAR_VIDEO,
            text="This is a TikTok style caption with proper wrapping and positioning!",
            position="bottom",
            fontStyle="titanOne"
        )
        print(f"Video created")

    except Exception as e:
        print(f"Error: {e}")
