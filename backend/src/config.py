import os

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

DEFAULT_LANGUAGE = "pt"
DEFAULT_WHISPER_MODEL = "base"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

MAX_CLIP_DURATION = 120
DEFAULT_MIN_CLIP_DURATION = 25
DEFAULT_MAX_CLIP_DURATION = 120
