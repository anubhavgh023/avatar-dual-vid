import requests
import os
from dotenv import load_dotenv


def generate_image(prompt, output_path="output.jpg"):
    """
    Generate an image using Segmind's Juggernaut Pro Flux API.

    Args:
        prompt (str): The text prompt describing the image.
        output_path (str): Path to save the generated image (default: 'output.jpg').

    Returns:
        bool: True if image generation and saving is successful, False otherwise.
    """
    # Load environment variables from .env file
    load_dotenv()
    api_key = os.getenv("SEGMIND_API_KEY")

    if not api_key:
        print("Error: SEGMIND_API_KEY environment variable not set")
        return False

    # API endpoint
    url = "https://api.segmind.com/v1/juggernaut-pro-flux"

    # Request payload with 9:16 ratio (576x1024)
    data = {
        "positivePrompt": prompt,
        "width": 576,  # Width for 9:16 ratio
        "height": 1024,  # Height for 9:16 ratio
        "steps": 25,
        "seed": 1184522,  # Fixed seed for reproducibility
        "CFGScale": 7,
        "outputFormat": "JPG",
        "scheduler": "Euler",
    }

    headers = {"x-api-key": api_key}

    try:
        # Send POST request to Segmind API
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()  # Raises an error for 4xx/5xx status codes

        # Save the generated image
        with open(output_path, "wb") as f:
            f.write(response.content)

        print(f"Image saved successfully to {output_path}")
        print(
            f"Remaining credits: {response.headers.get('x-remaining-credits', 'N/A')}"
        )
        return True

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e} - {response.text}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False
    except IOError as e:
        print(f"Failed to save image: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    sample_prompt = (
        "Middle-aged man sitting alone at diner counter, 3am, half-eaten pie, "
        "reflection in window, fluorescent lighting casting shadows."
    )
    generate_image(sample_prompt, "diner_image.jpg")
