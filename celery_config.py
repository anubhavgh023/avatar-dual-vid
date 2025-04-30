# celery_config.py
import os
import sys
from celery import Celery
from dotenv import load_dotenv

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Initialize Celery
app = Celery(
    "tasks",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,  # Results expire after 1 hour
)

# Explicitly include the module containing tasks
app.autodiscover_tasks(["modules.img_to_vid_gen"])



