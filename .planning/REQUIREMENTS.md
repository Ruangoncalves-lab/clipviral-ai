# Milestone v1.0 Requirements - Cloud SaaS with Professional Editing

## Categories

### Database & Auth
- [ ] **DB-01**: Define Supabase PostgreSQL schema for Profiles (users), Videos, and Clips.
- [ ] **AUTH-01**: Implement user authentication (signup/login/logout) via Supabase Auth in Next.js.

### Cloud Infrastructure & Storage
- [ ] **STORAGE-01**: Integrate Cloudflare R2 bucket for uploading original long videos and downloading generated clips.
- [ ] **STORAGE-02**: Automatic local temp file cleanup on backend after upload to R2.

### AI & Transcription
- [ ] **TRANS-01**: Implement audio track extraction from long videos and compression (low-bitrate MP3/AAC) under 25MB.
- [ ] **TRANS-02**: Integrate Groq Whisper API for rapid speech-to-text audio transcription.
- [ ] **SELECTION-01**: Integrate Gemini 1.5 Pro (Free Tier) to analyze transcriptions and identify high-impact candidate clips (with fallback to Gemini 1.5 Flash).

### Video Editing (FFmpeg)
- [ ] **EDIT-01**: Implement TikTok-style karaoke subtitles (ASS format) with word-by-word highlights in a contrasting color (yellow/green).
- [ ] **EDIT-02**: Implement automated "Jump Cuts" (dynamic zoom-ins/outs) at key moments suggested by the AI.
- [ ] **EDIT-03**: Implement automatic silence/pause removal from the audio track.
- [ ] **EDIT-04**: Apply smooth fade-in/fade-out transitions for audio/video at start/end of clips.

### Dashboard UI
- [ ] **UI-01**: Build Next.js Dashboard layout with responsive design, sidebar navigation, and user profile.
- [ ] **UI-02**: Create Video Upload flow with drag-and-drop support, uploading to storage, and triggering background processing.
- [ ] **UI-03**: Create Candidates & Clips View, displaying identified clips, details (viral score, title, hook, reason), and embedded video player for preview.
- [ ] **UI-04**: Add individual download links for clips (.mp4) and reports.

---

## Future Requirements
- [ ] Direct social media publishing (TikTok/Instagram API).
- [ ] Custom subtitle styling template editor.

## Out of Scope
- Multiple simultaneous video processing tasks per user (limited to 1 concurrent job to avoid CPU overload).
- Face tracking/Re-framing using computer vision models (focused on dynamic zoom-in and background blur for V1.0).
