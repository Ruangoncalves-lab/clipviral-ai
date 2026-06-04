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
