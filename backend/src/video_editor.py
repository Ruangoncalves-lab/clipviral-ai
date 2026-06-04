import os
import subprocess
from src.config import VIDEO_WIDTH, VIDEO_HEIGHT, TEMP_DIR
from src.utils import run_command, get_font_path

def get_video_dimensions(video_path):
    """Retrieve width and height of video."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0", video_path
    ]
    try:
        output = subprocess.check_output(cmd, text=True).strip()
        w, h = map(int, output.split('x'))
        return w, h
    except Exception as e:
        print(f"Error getting dimensions for {video_path}: {e}")
        return 1920, 1080 # Default fallback

def has_audio_stream(video_path):
    """Check if the video file contains an audio stream."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    try:
        output = subprocess.check_output(cmd, text=True).strip()
        return "audio" in output
    except Exception:
        return False

def ffmpeg_escape_text(text):
    """Escape text for FFmpeg drawtext filter."""
    # Escape backslash
    t = text.replace('\\', '\\\\')
    # Escape single quote
    t = t.replace("'", "'\\''")
    # Escape colon
    t = t.replace(':', '\\:')
    # Escape percent sign
    t = t.replace('%', '\\%')
    return t

def create_vertical_clip(input_video, start, end, output_path, srt_path=None, title=None, add_title=True, vertical=True):
    """
    Cut video and transform it into a vertical (1080x1920) clip with blurred background,
    subtitles, and title overlay using FFmpeg.
    
    Parameters:
      input_video (str): Path to input video file.
      start (float): Start time of the clip in seconds.
      end (float): End time of the clip in seconds.
      output_path (str): Path to write the output MP4 file.
      srt_path (str): Optional path to subtitles SRT file.
      title (str): Optional title text for the top.
      add_title (bool): Whether to add the title.
      vertical (bool): Whether to format as vertical 9:16.
    """
    # 1. Validate and clamp duration
    start = max(0.0, float(start))
    duration = float(end) - start
    
    # Force limit to 120s
    if duration > 120.0:
        duration = 120.0
        
    if duration <= 0:
        raise ValueError("A duração do corte deve ser maior que zero segundos.")
        
    print(f"Rendering clip: {start}s to {start + duration}s (duration: {duration:.2f}s) -> {output_path}")
    
    # 2. Get video dimensions and check format
    width, height = get_video_dimensions(input_video)
    is_horizontal = width > height
    has_audio = has_audio_stream(input_video)
    
    # Get custom Montserrat font path
    font_path = get_font_path()
    
    # 3. Build FFmpeg Filter Graph
    filters = []
    curr_link = "[0:v]"
    
    if vertical:
        if is_horizontal:
            # Layout horizontal on vertical: split into background and foreground.
            # Background: scale to increase, crop to fill 1080x1920, and boxblur.
            # Foreground: scale to width 1080, preserve height aspect ratio (divisible by 2).
            # Overlay centered vertically.
            filters.append(
                f"{curr_link}split=2[bg][fg];"
                f"[bg]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},boxblur=20:10[bg_blur];"
                f"[fg]scale={VIDEO_WIDTH}:-2[fg_scaled];"
                f"[bg_blur][fg_scaled]overlay=0:(H-h)/2[merged]"
            )
            curr_link = "[merged]"
        else:
            # Already vertical/square: Scale and crop to fill 1080x1920
            filters.append(
                f"{curr_link}scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}[merged]"
            )
            curr_link = "[merged]"
            
    # Apply subtitles if path provided
    if srt_path and os.path.exists(srt_path):
        # Build safe relative path using forward slashes to prevent escape issues on Windows/Linux
        rel_srt = os.path.relpath(srt_path, start=os.getcwd()).replace("\\", "/")
        rel_srt_esc = rel_srt.replace("'", "'\\''").replace(":", "\\:")
        
        # Style subtitles: white text, black border, Montserrat bold font, bottom aligned
        filters.append(
            f"{curr_link}subtitles='{rel_srt_esc}':force_style='"
            f"Fontname=Montserrat,Fontsize=22,PrimaryColour=&HFFFFFF,"
            f"OutlineColour=&H000000,BorderStyle=1,Outline=2.5,Alignment=2,MarginV=140"
            f"'[subbed]"
        )
        curr_link = "[subbed]"
        
    # Apply Title if provided
    if add_title and title:
        esc_title = ffmpeg_escape_text(title.upper())
        rel_font = os.path.relpath(font_path, start=os.getcwd()).replace("\\", "/")
        rel_font_esc = rel_font.replace("'", "'\\''").replace(":", "\\:")
        
        # Style Title: uppercase, top-centered, boxed semi-transparent background
        filters.append(
            f"{curr_link}drawtext=text='{esc_title}':x=(w-text_w)/2:y=180:"
            f"fontfile='{rel_font_esc}':fontsize=44:fontcolor=white:box=1:"
            f"boxcolor=black@0.4:boxborderw=15[titled]"
        )
        curr_link = "[titled]"
        
    filter_complex_str = ";".join(filters)
    
    # 4. Assemble Command
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.2f}",
        "-t", f"{duration:.2f}",
        "-i", input_video
    ]
    
    if filter_complex_str:
        cmd.extend(["-filter_complex", filter_complex_str, "-map", curr_link])
    else:
        # Default maps if no filters are applied
        cmd.extend(["-map", "0:v"])
        
    if has_audio:
        cmd.extend(["-map", "0:a"])
        
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "veryfast", # Optimal for CPU environments like spaces
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ])
    
    # Execute the command
    try:
        run_command(cmd, log_func=print)
        print(f"Successfully generated clip at: {output_path}")
    except Exception as e:
        print(f"FFmpeg failed for clip starting at {start}s: {e}")
        raise RuntimeError(f"Erro na renderização do corte com o FFmpeg: {e}")
