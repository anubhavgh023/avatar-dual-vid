# Use official Python runtime as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements file (create this next)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install FFmpeg and ImageMagick
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Copy a custom ImageMagick policy file to allow necessary operations
COPY policy.xml /etc/ImageMagick-6/policy.xml

# Copy the entire project
COPY . .

# Expose port 8000
EXPOSE 8000

# Command to run the FastAPI server
CMD ["fastapi","run", "main.py", "--host", "0.0.0.0", "--port", "8000"]