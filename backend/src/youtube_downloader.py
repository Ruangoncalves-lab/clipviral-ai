"""
youtube_downloader.py — Download videos from YouTube using yt-dlp.
Validates URLs, extracts metadata, and downloads MP4 to a local path.
"""
import os
import re
import logging

logger = logging.getLogger("youtube_downloader")

try:
    import yt_dlp
except ImportError:
    yt_dlp = None
    logger.warning("yt-dlp is not installed. YouTube imports will not be available.")


# ──────────────────────────────────────────────────────────────
#  URL VALIDATION
# ──────────────────────────────────────────────────────────────

YOUTUBE_REGEX = re.compile(
    r'(?:https?://)?(?:www\.|m\.)?'
    r'(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|youtu\.be/)'
    r'([a-zA-Z0-9_-]{11})'
)

def is_valid_youtube_url(url: str) -> bool:
    """Check if a URL is a valid YouTube video link."""
    return bool(YOUTUBE_REGEX.search(url.strip()))

def extract_video_id(url: str) -> str | None:
    """Extract the 11-character YouTube video ID from a URL."""
    match = YOUTUBE_REGEX.search(url.strip())
    return match.group(1) if match else None


# ──────────────────────────────────────────────────────────────
#  METADATA EXTRACTION
# ──────────────────────────────────────────────────────────────

def get_video_info(url: str) -> dict:
    """
    Fetch video metadata without downloading.
    Returns: { title, duration, thumbnail, channel, upload_date, video_id }
    """
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed.")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Untitled'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'channel': info.get('channel', info.get('uploader', 'Unknown')),
                'upload_date': info.get('upload_date', ''),
                'video_id': info.get('id', ''),
            }
    except Exception as e:
        logger.error(f"Failed to extract video info: {e}")
        raise RuntimeError(f"Erro ao obter informações do vídeo: {e}")


# ──────────────────────────────────────────────────────────────
#  VIDEO DOWNLOAD
# ──────────────────────────────────────────────────────────────

def download_video(url: str, output_path: str, max_duration: int = 3600) -> dict:
    """
    Download a YouTube video as MP4.
    
    Args:
        url: YouTube video URL
        output_path: Full path to save the downloaded MP4 file
        max_duration: Maximum video duration in seconds (default 1 hour)
    
    Returns:
        dict with keys: title, duration, filepath, video_id
    
    Raises:
        ValueError: If URL is invalid or video exceeds max duration
        RuntimeError: If download fails
    """
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed.")
    
    if not is_valid_youtube_url(url):
        raise ValueError("URL do YouTube inválida. Use o formato: https://youtube.com/watch?v=...")
    
    # First, check metadata to validate duration
    info = get_video_info(url)
    
    if info['duration'] > max_duration:
        raise ValueError(
            f"Vídeo muito longo ({info['duration']}s). "
            f"O limite máximo é de {max_duration // 60} minutos."
        )
    
    if info['duration'] <= 0:
        raise ValueError("Não foi possível determinar a duração do vídeo.")
    
    logger.info(f"Downloading YouTube video: '{info['title']}' ({info['duration']}s)")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Remove extension from output_path since yt-dlp adds it
    output_template = output_path
    if output_template.endswith('.mp4'):
        output_template = output_template[:-4]
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_template + '.%(ext)s',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'socket_timeout': 30,
        'retries': 3,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logger.error(f"YouTube download failed: {e}")
        raise RuntimeError(f"Erro ao baixar vídeo do YouTube: {e}")
    
    # Find the actual downloaded file
    final_path = output_template + '.mp4'
    if not os.path.exists(final_path):
        # Try to find any file with this base name
        base_dir = os.path.dirname(output_template)
        base_name = os.path.basename(output_template)
        for f in os.listdir(base_dir):
            if f.startswith(base_name):
                final_path = os.path.join(base_dir, f)
                break
    
    if not os.path.exists(final_path):
        raise RuntimeError("Download concluído mas o arquivo não foi encontrado.")
    
    logger.info(f"YouTube video downloaded successfully to: {final_path}")
    
    return {
        'title': info['title'],
        'duration': info['duration'],
        'filepath': final_path,
        'video_id': info['video_id'],
        'channel': info['channel'],
        'thumbnail': info['thumbnail'],
    }
