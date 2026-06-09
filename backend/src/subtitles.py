import os
from src.utils import seconds_to_srt_time

def split_segment_into_chunks(segment, max_words=4, max_chars=28):
    """
    Splits a segment into smaller chunks with linearly interpolated timestamps
    to make subtitles appear more dynamic and readable on screen.
    """
    text = segment["text"].strip()
    words = text.split()
    if not words:
        return []
    
    start_time = segment["start"]
    end_time = segment["end"]
    duration = end_time - start_time
    total_words = len(words)
    
    chunks = []
    current_words = []
    current_char_count = 0
    
    # Track word indices for time interpolation
    chunk_start_idx = 0
    
    for i, word in enumerate(words):
        current_words.append(word)
        current_char_count += len(word) + 1 # +1 for space
        
        # Check if we should close the chunk
        should_split = (
            len(current_words) >= max_words or 
            current_char_count >= max_chars or 
            i == total_words - 1
        )
        
        if should_split:
            chunk_end_idx = i
            
            # Interpolate timestamps linearly
            c_start = start_time + (chunk_start_idx / total_words) * duration
            c_end = start_time + ((chunk_end_idx + 1) / total_words) * duration
            
            # Prevent overlap or negative durations
            if c_end <= c_start:
                c_end = c_start + 0.1
                
            chunk_text = " ".join(current_words).upper() # Uppercase for style
            
            chunks.append({
                "start": round(c_start, 2),
                "end": round(c_end, 2),
                "text": chunk_text
            })
            
            # Reset for next chunk
            current_words = []
            current_char_count = 0
            chunk_start_idx = i + 1
            
    return chunks

def generate_srt_for_clip(segments, clip_start, clip_end, output_srt):
    """
    Filter segments for a specific clip window, adjust timestamps to begin at 00:00:00,
    split them into dynamic chunks, and write a valid SRT file.
    
    Parameters:
      segments (list): Original transcription segments.
      clip_start (float): Start time of the clip.
      clip_end (float): End time of the clip.
      output_srt (str): Path to write the output SRT file.
    """
    # 1. Filter and crop segments to the clip window
    clip_segments = []
    for seg in segments:
        # Check for overlap
        if seg["end"] <= clip_start or seg["start"] >= clip_end:
            continue
            
        # Crop segment to fit clip bounds
        seg_start = max(clip_start, seg["start"])
        seg_end = min(clip_end, seg["end"])
        
        if seg_end > seg_start:
            clip_segments.append({
                "start": seg_start,
                "end": seg_end,
                "text": seg["text"]
            })
            
    # 2. Split into smaller chunks for dynamic captions
    dynamic_chunks = []
    for seg in clip_segments:
        dynamic_chunks.extend(split_segment_into_chunks(seg))
        
    # 3. Adjust timestamps relative to clip_start and write SRT file
    with open(output_srt, 'w', encoding='utf-8') as f:
        srt_index = 1
        for chunk in dynamic_chunks:
            # Adjust times
            rel_start = max(0.0, chunk["start"] - clip_start)
            rel_end = max(0.1, chunk["end"] - clip_start)
            
            # Prevent ending after clip duration
            clip_duration = clip_end - clip_start
            if rel_start >= clip_duration:
                continue
            if rel_end > clip_duration:
                rel_end = clip_duration
                
            # Write subtitle entry
            start_str = seconds_to_srt_time(rel_start)
            end_str = seconds_to_srt_time(rel_end)
            
            f.write(f"{srt_index}\n")
            f.write(f"{start_str} --> {end_str}\n")
            f.write(f"{chunk['text']}\n\n")
            
            srt_index += 1
            
    print(f"Generated SRT subtitles at: {output_srt}")

def seconds_to_ass_time(secs):
    """Convert seconds to ASS timestamp format (H:MM:SS.CS)"""
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    cs = int(round((secs - int(secs)) * 100))
    if cs == 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_ass_for_clip(segments, clip_start, clip_end, output_ass, font_name="Montserrat", font_size=38, font_color="#FFFFFF", font_style="outline"):
    """
    Generate Advanced SubStation Alpha (.ass) subtitles for a clip window.
    Applies karaoke dynamic highlighting using {\kf<duration>} tags based on word length.
    """
    # 1. Filter and crop segments
    clip_segments = []
    for seg in segments:
        if seg["end"] <= clip_start or seg["start"] >= clip_end:
            continue
        seg_start = max(clip_start, seg["start"])
        seg_end = min(clip_end, seg["end"])
        if seg_end > seg_start:
            clip_segments.append({
                "start": seg_start,
                "end": seg_end,
                "text": seg["text"]
            })
            
    # 2. Split into dynamic chunks (max 3-4 words per line for high readability)
    dynamic_chunks = []
    for seg in clip_segments:
        dynamic_chunks.extend(split_segment_into_chunks(seg, max_words=3, max_chars=22))
        
    # 3. Format primary color from CSS Hex (#RRGGBB) to ASS hex (&H00BBGGRR)
    ass_primary_color = "&H00FFFFFF" # Default: Opaque White
    ass_secondary_color = "&H0000FFFF" # Default: Opaque Yellow highlight
    
    if font_color.startswith("#"):
        hex_color = font_color.lstrip("#")
        if len(hex_color) == 6:
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            ass_primary_color = f"&H00{b}{g}{r}"
            
    # Set border style (1 = outline, 3 = opaque background box)
    border_style = 1
    outline = 2.5
    back_color = "&H60000000" # Semi-transparent black outline background
    if font_style == "box":
        border_style = 3
        outline = 4.0
        back_color = "&H00000000" # Solid black box background
        
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font_name},{font_size},{ass_primary_color},{ass_secondary_color},&H00000000,{back_color},1,0,0,0,100,100,0,0,{border_style},{outline},0,2,10,10,360,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    
    clip_duration = clip_end - clip_start
    
    with open(output_ass, 'w', encoding='utf-8') as f:
        f.write(header)
        for chunk in dynamic_chunks:
            rel_start = max(0.0, chunk["start"] - clip_start)
            rel_end = max(0.1, chunk["end"] - clip_start)
            
            if rel_start >= clip_duration:
                continue
            if rel_end > clip_duration:
                rel_end = clip_duration
                
            start_str = seconds_to_ass_time(rel_start)
            end_str = seconds_to_ass_time(rel_end)
            
            # Format word timing inside chunk
            words = chunk["text"].split()
            if not words:
                continue
                
            # Distribute time by character length to approximate speech speed
            char_counts = [len(w) for w in words]
            total_chars = sum(char_counts)
            total_duration_cs = int(round((rel_end - rel_start) * 100))
            
            word_durations = []
            if total_chars > 0:
                for count in char_counts:
                    word_durations.append(int(round((count / total_chars) * total_duration_cs)))
            else:
                word_durations = [total_duration_cs // len(words)] * len(words)
                
            # Align rounding discrepancies to matching total duration
            diff = total_duration_cs - sum(word_durations)
            if word_durations:
                word_durations[-1] += diff
                
            # Build ASS tags
            ass_text = ""
            for w, dur in zip(words, word_durations):
                # Ensure minimum 1 centisecond duration for tags
                dur = max(1, dur)
                ass_text += f"{{\\kf{dur}}}{w} "
            ass_text = ass_text.strip()
            
            f.write(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{ass_text}\n")
            
    print(f"Generated ASS subtitles at: {output_ass}")
