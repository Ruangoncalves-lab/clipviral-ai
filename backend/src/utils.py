import os
import re
import json
import subprocess
import urllib.request
from src.config import (
    TEMP_DIR,
    OUTPUT_DIR,
    DEFAULT_MIN_CLIP_DURATION,
    DEFAULT_MAX_CLIP_DURATION
)

def ensure_dirs():
    """Ensure temp and output directories exist."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def safe_filename(text):
    """Sanitize text to create a safe file name."""
    s = re.sub(r'[^\w\s-]', '', text).strip()
    s = re.sub(r'[-\s]+', '_', s)
    return s.lower()[:50]

def seconds_to_srt_time(seconds):
    """Convert float seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def run_command(cmd_args, log_func=print):
    """Execute a system command using subprocess safely and log output."""
    if log_func:
        log_func(f"Executing: {' '.join(cmd_args)}")
    
    # Run the process
    result = subprocess.run(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    if result.returncode != 0:
        if log_func:
            log_func(f"Command failed with code {result.returncode}.\nStderr: {result.stderr}")
        raise RuntimeError(f"Command failed with code {result.returncode}: {result.stderr}")
    
    return result.stdout

def cleanup_temp_files():
    """Remove temporary files from the temp directory."""
    if not os.path.exists(TEMP_DIR):
        return
    for f in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, f)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error removing temp file {file_path}: {e}")

def get_video_duration(video_path):
    """Retrieve duration of a video file using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    try:
        output = subprocess.check_output(cmd, text=True).strip()
        return float(output)
    except Exception as e:
        print(f"Error getting video duration of {video_path}: {e}")
        return 0.0

def create_report_json(clips, path):
    """Export clips report to a JSON file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(clips, f, indent=4, ensure_ascii=False)

def clamp_clip_duration(duration, min_val=DEFAULT_MIN_CLIP_DURATION, max_val=DEFAULT_MAX_CLIP_DURATION):
    """Clamp the duration of a clip between standard bounds."""
    return max(min_val, min(max_val, duration))

def format_duration(seconds):
    """Format seconds to user-friendly text (e.g. 1m 15s or 45s)."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

def get_font_path():
    """Retrieve path of Montserrat-Bold font, downloading it if not present."""
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
    os.makedirs(font_dir, exist_ok=True)
    font_path = os.path.join(font_dir, "Montserrat-Bold.ttf")
    
    if not os.path.exists(font_path):
        print("Montserrat-Bold font not found in resources. Downloading...")
        url = "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Bold.ttf"
        try:
            # Set timeout to prevent hanging
            urllib.request.urlretrieve(url, font_path)
            print("Font downloaded successfully.")
        except Exception as e:
            print(f"Error downloading font: {e}. Falling back to default system font.")
            # Fallback to system default
            if os.name == 'nt':
                system_font = "C:\\Windows\\Fonts\\arial.ttf"
                if os.path.exists(system_font):
                    return system_font
            else:
                system_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if os.path.exists(system_font):
                    return system_font
            # If everything else fails, let FFmpeg search for 'Arial' or 'sans-serif'
            return "Arial"
            
    return font_path
