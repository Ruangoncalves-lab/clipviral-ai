# Phase 3 Plan - Advanced Video Editing Pipeline

## Goal
Implement advanced video rendering capabilities (ASS karaoke subtitles, automatic zoom-ins on hook timestamps, and silence removal) using FFmpeg.

## Tasks
- [ ] **ASS Subtitle Generator (Karaoke style)**
  - [ ] Implement `generate_ass_for_clip` inside `backend/src/subtitles.py` that outputs `.ass` files.
  - [ ] Distribute word durations inside chunks and apply `{\kf<centiseconds>}` karaoke tags.
  - [ ] Update `backend/app.py` to retrieve user profile settings from Supabase and pass styling parameters to the subtitle generator.
- [ ] **Dynamic Hook Zoom-In (Jump Cuts)**
  - [ ] Match the Gemini-selected hook text to subtitle segments to identify the exact hook start/end times.
  - [ ] Implement dynamic crop zoom filter logic in `backend/src/video_editor.py` using FFmpeg crop filters.
- [ ] **FFmpeg Silence Removal**
  - [ ] Implement silence detection helper that parses FFmpeg `silencedetect` logs.
  - [ ] Construct dynamic trim and concat filters to cut out silent parts.
