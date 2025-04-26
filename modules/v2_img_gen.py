import requests
import os
from dotenv import load_dotenv


def generate_image(prompt, output_path="output.png"):
    """
    Generate an image using Segmind's GPT-Image-1 API and save it to a file.

    Args:
        prompt (str): The text prompt describing the image to generate.
        output_path (str): Path where the generated image will be saved.

    Returns:
        bool: True if successful, False otherwise.
    """
    # Load API key from environment variable
    load_dotenv()
    api_key = os.getenv("SEGMIND_API_KEY")

    if not api_key:
        print("Error: SEGMIND_API_KEY environment variable not set")
        return False

    # API endpoint
    url = "https://api.segmind.com/v1/gpt-image-1"

    # Request payload with exact parameters from the example
    data = {
        "prompt": prompt,
        "size": "auto",
        "quality": "auto",
        "background": "opaque",
        "output_compression": 100,
        "output_format": "png",
    }

    headers = {"x-api-key": api_key}

    try:
        # Send request to API
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()

        # Save the image
        with open(output_path, "wb") as f:
            f.write(response.content)

        print(f"Image successfully saved to {output_path}")
        return True

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
        print(f"Response: {response.text}")
        return False

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    # Example prompt
    prompt = input("Enter your image prompt: ")

    # Generate the image
    output_file = "generated_image.png"
    generate_image(prompt, output_file)