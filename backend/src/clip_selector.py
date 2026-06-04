import os
from src.config import DEFAULT_MIN_CLIP_DURATION, DEFAULT_MAX_CLIP_DURATION
from src.rule_analyzer import analyze_candidates_locally
from src.gemini_analyzer import analyze_candidates_with_gemini

def build_candidate_clips(segments, min_duration, max_duration):
    """
    Groups consecutive segments into potential candidate clips with durations
    between min_duration and max_duration (hard limit of 120 seconds).
    
    Parameters:
      segments (list): Segments from the transcriber.
      min_duration (float): Minimum clip duration in seconds.
      max_duration (float): Maximum clip duration in seconds.
      
    Returns:
      list: A list of candidate dicts with text and timestamps.
    """
    min_duration = float(min_duration)
    # Absolute upper limit is 120 seconds
    max_duration = min(120.0, float(max_duration))
    
    candidates = []
    num_segments = len(segments)
    
    for i in range(num_segments):
        start_time = segments[i]["start"]
        text_parts = []
        
        # Merge subsequent segments
        for j in range(i, num_segments):
            end_time = segments[j]["end"]
            duration = end_time - start_time
            
            # If adding this segment exceeds our limit, stop before adding it
            if duration > max_duration:
                break
                
            text_parts.append(segments[j]["text"])
            
            # We have a valid candidate if it is at least the minimum duration
            if duration >= min_duration:
                # Identify if this is a natural place to end a clip
                # 1. Ends with terminal punctuation
                is_good_stop = segments[j]["text"].endswith(('.', '!', '?'))
                # 2. A long pause until the next segment starts
                if not is_good_stop and j + 1 < num_segments:
                    pause = segments[j+1]["start"] - segments[j]["end"]
                    if pause > 1.2:
                        is_good_stop = True
                
                # Close candidate if it's a good stop, we are near the max, or at the end of segments
                is_near_max = (j + 1 < num_segments and (segments[j+1]["end"] - start_time > max_duration))
                is_last_seg = (j == num_segments - 1)
                
                if is_good_stop or is_near_max or is_last_seg:
                    candidates.append({
                        "id": f"c_{i}_{j}",
                        "start": round(start_time, 2),
                        "end": round(end_time, 2),
                        "duration": round(duration, 2),
                        "text": " ".join(text_parts).strip()
                    })
                    break # Move to next start segment to avoid redundant nested windows
                    
    return candidates

def select_best_clips(segments, num_clips, min_duration=DEFAULT_MIN_CLIP_DURATION, 
                      max_duration=DEFAULT_MAX_CLIP_DURATION, use_gemini=False, 
                      gemini_api_key=""):
    """
    Selects the best non-overlapping video clips.
    
    Parameters:
      segments (list): Output list of segments from the transcriber.
      num_clips (int): Number of clips to generate.
      min_duration (float): Minimum duration of clips.
      max_duration (float): Maximum duration of clips.
      use_gemini (bool): Whether to use Google Gemini API.
      gemini_api_key (str): Google Gemini API Key.
      
    Returns:
      list: Best selected clips matching format.
    """
    if not segments:
        return []
        
    # 1. Build candidates
    candidates = build_candidate_clips(segments, min_duration, max_duration)
    print(f"Generated {len(candidates)} candidate clips from transcription.")
    
    if not candidates:
        return []
        
    # 2. Evaluate all candidates locally first for pre-filtering
    print("Evaluating candidate clips locally for pre-filtering...")
    local_evaluated = analyze_candidates_locally(candidates)
    
    evaluated_candidates = None
    
    # 3. Try Gemini analysis on top 40 candidates if requested
    if use_gemini and gemini_api_key:
        # Sort locally evaluated candidates to select top 40
        local_evaluated.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = local_evaluated[:40]
        
        print(f"Sending top {len(top_candidates)} candidates to Gemini 1.5 Pro...")
        # Pass the top candidates (which contain text, start, end, duration) to Gemini
        gemini_results = analyze_candidates_with_gemini(top_candidates, gemini_api_key)
        
        if gemini_results is not None:
            # Merge Gemini results back: map of candidate id -> gemini result
            gemini_map = {item["id"]: item for item in gemini_results}
            merged_list = []
            for item in local_evaluated:
                c_id = item["id"]
                if c_id in gemini_map:
                    merged_list.append(gemini_map[c_id])
                else:
                    merged_list.append(item)
            evaluated_candidates = merged_list
        else:
            print("Gemini analysis failed or returned empty results. Falling back fully to local rule-based scores.")
            evaluated_candidates = local_evaluated
    else:
        evaluated_candidates = local_evaluated
        
    # 4. Sort by score in descending order
    evaluated_candidates.sort(key=lambda x: x["score"], reverse=True)
    
    # 5. Greedy Selection with overlap suppression
    selected_clips = []
    max_overlap_ratio = 0.15 # Allow max 15% overlap between selected clips
    
    for cand in evaluated_candidates:
        if len(selected_clips) >= num_clips:
            break
            
        # Check overlaps
        is_overlapping = False
        c_start = cand["start"]
        c_end = cand["end"]
        c_dur = c_end - c_start
        
        for sel in selected_clips:
            s_start = sel["start"]
            s_end = sel["end"]
            
            # Intersection interval
            overlap_start = max(c_start, s_start)
            overlap_end = min(c_end, s_end)
            
            if overlap_end > overlap_start:
                overlap_len = overlap_end - overlap_start
                overlap_ratio = overlap_len / c_dur
                if overlap_ratio > max_overlap_ratio:
                    is_overlapping = True
                    break
                    
        if not is_overlapping:
            # Absolute sanity check for the 120 seconds maximum duration
            if cand["end"] - cand["start"] > 120.0:
                cand["end"] = cand["start"] + 120.0
                cand["duration"] = 120.0
                
            selected_clips.append(cand)
            
    # Sort selected clips chronologically for output structure consistency
    selected_clips.sort(key=lambda x: x["start"])
    return selected_clips
