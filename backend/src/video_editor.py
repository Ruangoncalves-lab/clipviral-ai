import os
import re
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

def detect_silence_gaps(video_path, start, duration, noise_threshold=-40, min_duration=1.0):
    """
    Runs FFmpeg silencedetect to find silent intervals in the video slice.
    Returns a list of tuples (silence_start, silence_end) relative to the slice start (0.0).
    """
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.2f}",
        "-t", f"{duration:.2f}",
        "-i", video_path,
        "-af", f"silencedetect=n={noise_threshold}dB:d={min_duration}",
        "-f", "null", "-"
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
        stderr = result.stderr
        
        silences = []
        start_time = None
        
        for line in stderr.splitlines():
            if "silence_start" in line:
                match = re.search(r"silence_start:\s*([\d\.]+)", line)
                if match:
                    start_time = float(match.group(1))
            elif "silence_end" in line:
                match = re.search(r"silence_end:\s*([\d\.]+)", line)
                if match and start_time is not None:
                    end_time = float(match.group(1))
                    silences.append((start_time, end_time))
                    start_time = None
                    
        return silences
    except Exception as e:
        print(f"Error detecting silence: {e}")
        return []

def get_active_intervals(total_duration, silences):
    """
    Converts list of silence gaps into active intervals.
    """
    if not silences:
        return [(0.0, total_duration)]
        
    active = []
    current_time = 0.0
    
    for s_start, s_end in silences:
        if s_start > current_time:
            if s_start - current_time > 0.1:
                active.append((current_time, s_start))
        current_time = s_end
        
    if current_time < total_duration:
        if total_duration - current_time > 0.1:
            active.append((current_time, total_duration))
            
    return active

def find_hook_timestamp_range(segments, hook_text, clip_start, clip_end):
    """
    Find the timestamp range of the hook within the clip.
    Normalizes text to match words in the segments.
    """
    if not hook_text:
        return clip_start, min(clip_end, clip_start + 3.5)
        
    def clean(t):
        return re.sub(r'[^\w\s]', '', t.lower()).strip()
        
    hook_clean = clean(hook_text)
    hook_words = hook_clean.split()
    if not hook_words:
        return clip_start, min(clip_end, clip_start + 3.5)
        
    # Filter segments that overlap with this clip
    clip_segs = [s for s in segments if s["end"] > clip_start and s["start"] < clip_end]
    if not clip_segs:
        return clip_start, min(clip_end, clip_start + 3.5)
        
    # Build list of all words with timestamps
    all_words = []
    for s in clip_segs:
        words = s["text"].split()
        if not words:
            continue
        seg_dur = s["end"] - s["start"]
        for idx, w in enumerate(words):
            w_start = s["start"] + (idx / len(words)) * seg_dur
            w_end = s["start"] + ((idx + 1) / len(words)) * seg_dur
            all_words.append({
                "word": clean(w),
                "start": w_start,
                "end": w_end
            })
            
    if not all_words:
        return clip_start, min(clip_end, clip_start + 3.5)
        
    best_start = clip_start
    best_end = min(clip_end, clip_start + 3.5)
    
    n_hook = len(hook_words)
    n_all = len(all_words)
    
    best_match_count = 0
    for i in range(max(1, n_all - n_hook + 1)):
        matches = 0
        for j in range(min(n_hook, n_all - i)):
            if hook_words[j] in all_words[i+j]["word"] or all_words[i+j]["word"] in hook_words[j]:
                matches += 1
        if matches > best_match_count:
            best_match_count = matches
            best_start = all_words[i]["start"]
            best_end = all_words[i + min(n_hook, n_all - i) - 1]["end"]
            
    # Fallback if match count is low
    if best_match_count < max(1, n_hook // 2):
        first_seg_start = clip_segs[0]["start"]
        h_start = max(clip_start, first_seg_start)
        h_end = min(clip_end, h_start + 3.5)
        return h_start, h_end
        
    h_start = max(clip_start, best_start)
    h_end = min(clip_end, best_end)
    
    if h_end - h_start < 1.0:
        h_end = min(clip_end, h_start + 2.0)
    if h_end - h_start > 6.0:
        h_end = h_start + 5.0
        
    return h_start, h_end

def create_vertical_clip(input_video, start, end, output_path, subtitle_path=None, srt_path=None, title=None, add_title=True, vertical=True, hook_start=None, hook_end=None, remove_silence=True, layout_mode="fit"):
    """
    Cut video and transform it into a vertical (1080x1920) clip with blurred background,
    subtitles, hook zoom-in, silence removal, and title overlay using FFmpeg.
    Supports layout_mode: 'auto' (detect and center face / split), 'split' (podcast stacked split), 'fit' (fit-with-blur background).
    """
    from src.face_tracker import detect_and_track_faces

    # Backward compatibility
    if srt_path and not subtitle_path:
        subtitle_path = srt_path

    # 1. Validate and clamp duration
    start = max(0.0, float(start))
    duration = float(end) - start
    
    # Force limit to 120s
    if duration > 120.0:
        duration = 120.0
        
    if duration <= 0:
        raise ValueError("A duração do corte deve ser maior que zero segundos.")
        
    print(f"Rendering clip ({layout_mode}): {start}s to {start + duration}s (duration: {duration:.2f}s) -> {output_path}")
    
    # 2. Get video dimensions and check format
    width, height = get_video_dimensions(input_video)
    is_horizontal = width > height
    has_audio = has_audio_stream(input_video)
    
    # Get custom Montserrat font path
    font_path = get_font_path()
    
    # 3. Build FFmpeg Filter Graph
    filters = []
    curr_link = "[0:v]"
    curr_audio_link = None
    
    if vertical:
        if is_horizontal:
            # Process reframing based on layout preferences
            if layout_mode in ["auto", "split"]:
                try:
                    layout_type, coords = detect_and_track_faces(input_video, start, duration)
                except Exception as e:
                    print(f"Face tracking failed: {e}. Falling back to 'fit' layout.")
                    layout_type = "fit"
                    coords = []
            else:
                layout_type = "fit"
                coords = []

            # If split screen requested or auto-detected dual speakers
            if (layout_mode == "split" or (layout_mode == "auto" and layout_type == "split")) and len(coords) >= 2:
                print("Applying Split-Screen podcast crop filters...")
                face1_x = coords[0]['x']
                face2_x = coords[1]['x']
                
                crop_w = int(height * 9 / 8)
                crop_w = (crop_w // 2) * 2
                crop_h = height
                
                crop1_x = max(0, min(width - crop_w, int(face1_x - crop_w / 2)))
                crop2_x = max(0, min(width - crop_w, int(face2_x - crop_w / 2)))
                
                filters.append(
                    f"{curr_link}split=2[sp1][sp2];"
                    f"[sp1]crop={crop_w}:{crop_h}:{crop1_x}:0,scale={VIDEO_WIDTH}:960[top];"
                    f"[sp2]crop={crop_w}:{crop_h}:{crop2_x}:0,scale={VIDEO_WIDTH}:960[bottom];"
                    f"[top][bottom]vstack[merged]"
                )
                curr_link = "[merged]"

            # If Auto Reframe active or single face tracking
            elif (layout_mode == "auto" or layout_mode == "reframe") and len(coords) >= 1 and coords[0]['w'] > 0:
                print("Applying Auto Reframe face tracking crop filter...")
                face_x = coords[0]['x']
                
                crop_w = int(height * 9 / 16)
                crop_w = (crop_w // 2) * 2
                crop_h = height
                
                crop_x = max(0, min(width - crop_w, int(face_x - crop_w / 2)))
                
                filters.append(
                    f"{curr_link}crop={crop_w}:{crop_h}:{crop_x}:0,scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}[merged]"
                )
                curr_link = "[merged]"

            # Otherwise, use standard fit-with-blur background
            else:
                print("Applying fit-with-blurred background filters...")
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
    if subtitle_path and os.path.exists(subtitle_path):
        # Build safe relative path using forward slashes to prevent escape issues on Windows/Linux
        rel_sub = os.path.relpath(subtitle_path, start=os.getcwd()).replace("\\", "/")
        rel_sub_esc = rel_sub.replace("'", "'\\''").replace(":", "\\:")
        
        if subtitle_path.endswith('.ass'):
            filters.append(f"{curr_link}subtitles='{rel_sub_esc}'[subbed]")
        else:
            # Style subtitles: white text, black border, Montserrat bold font, bottom aligned
            filters.append(
                f"{curr_link}subtitles='{rel_sub_esc}':force_style='"
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
        
    # Apply Hook Auto-Zoom (Centered 15% crop zoom, i.e., 1 / 0.85 = 1.176x) during hook window
    if hook_start is not None and hook_end is not None and hook_end > hook_start:
        rel_hook_start = max(0.0, hook_start - start)
        rel_hook_end = min(duration, hook_end - start)
        if rel_hook_end > rel_hook_start:
            print(f"Applying hook auto-zoom from {rel_hook_start:.2f}s to {rel_hook_end:.2f}s")
            filters.append(
                f"{curr_link}split=2[orig_zoom][zoom_src];"
                f"[zoom_src]crop=iw*0.85:ih*0.85:(iw-ow)/2:(ih-oh)/2,scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}[zoomed];"
                f"[orig_zoom][zoomed]overlay=0:0:enable='between(t,{rel_hook_start:.2f},{rel_hook_end:.2f})'[zoomed_out]"
            )
            curr_link = "[zoomed_out]"

    # Apply Silence Removal
    if remove_silence and has_audio:
        print("Running silence detection...")
        silences = detect_silence_gaps(input_video, start, duration, noise_threshold=-40, min_duration=1.0)
        if silences:
            print(f"Detected {len(silences)} silence gaps. Calculating active intervals...")
            active_intervals = get_active_intervals(duration, silences)
            if len(active_intervals) > 1 or (len(active_intervals) == 1 and active_intervals[0][1] < duration - 0.1):
                print(f"Trimming out silences. Active intervals: {active_intervals}")
                trim_filters = []
                for i, (s_act, e_act) in enumerate(active_intervals):
                    trim_filters.append(f"{curr_link}trim=start={s_act:.2f}:end={e_act:.2f},setpts=PTS-STARTPTS[v{i}]")
                    trim_filters.append(f"[0:a]atrim=start={s_act:.2f}:end={e_act:.2f},asetpts=PTS-STARTPTS[a{i}]")
                    
                concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(active_intervals)))
                trim_filters.append(f"{concat_inputs}concat=n={len(active_intervals)}:v=1:a=1[outv][outa]")
                
                filters.extend(trim_filters)
                curr_link = "[outv]"
                curr_audio_link = "[outa]"
            else:
                print("No significant silence gaps to remove after filtering.")
        else:
            print("No silence gaps detected.")
            
    # Apply smooth fade-in/fade-out transitions for audio/video at start/end of clips (EDIT-04)
    fade_duration = 0.5
    if remove_silence and has_audio and 'active_intervals' in locals() and len(active_intervals) > 1:
        final_duration = sum(e_act - s_act for s_act, e_act in active_intervals)
    else:
        final_duration = duration

    if final_duration > fade_duration * 2:
        fade_out_start = final_duration - fade_duration
        
        # Apply video fade
        filters.append(f"{curr_link}fade=t=in:st=0:d={fade_duration},fade=t=out:st={fade_out_start:.2f}:d={fade_duration}[faded_v]")
        curr_link = "[faded_v]"
        
        # Apply audio fade
        if has_audio:
            audio_src = curr_audio_link if curr_audio_link else "[0:a]"
            filters.append(f"{audio_src}afade=t=in:ss=0:d={fade_duration},afade=t=out:st={fade_out_start:.2f}:d={fade_duration}[faded_a]")
            curr_audio_link = "[faded_a]"

    filter_complex_str = ";".join(filters)
    
    # 4. Assemble Command
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.2f}",
        "-t", f"{duration:.2f}",
        "-i", input_video
    ]
    
    if filter_complex_str:
        cmd.extend(["-filter_complex", filter_complex_str])
        if curr_audio_link:
            cmd.extend(["-map", curr_link, "-map", curr_audio_link])
        else:
            cmd.extend(["-map", curr_link])
            if has_audio:
                cmd.extend(["-map", "0:a"])
    else:
        cmd.extend(["-map", "0:v"])
        if has_audio:
            cmd.extend(["-map", "0:a"])
        
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ])
    
    try:
        run_command(cmd, log_func=print)
        print(f"Successfully generated clip at: {output_path}")
    except Exception as e:
        print(f"FFmpeg failed for clip starting at {start}s: {e}")
        raise RuntimeError(f"Erro na renderização do corte com o FFmpeg: {e}")
