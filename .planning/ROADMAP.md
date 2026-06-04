# Roadmap - Milestone v1.0

## Phase 1: Database, Auth, and Storage Foundation
Goal: Set up the core database schemas, authentication, and object storage integration with Cloudflare R2.
Requirements: DB-01, AUTH-01, STORAGE-01, STORAGE-02
Success Criteria:
1. Users can register and log in via Next.js.
2. User profile records are created in Supabase PostgreSQL database.
3. Original video uploads are stored in Cloudflare R2 and can be downloaded securely.
4. Database tables for videos and clips successfully track state (pending, processing, completed).

## Phase 2: Fast Cloud Transcription and AI Selection
Goal: Integrate Groq Whisper API for rapid transcription and Gemini 1.5 Pro/Flash for selecting viral candidates.
Requirements: TRANS-01, TRANS-02, SELECTION-01
Success Criteria:
1. Large video files are split/compressed to mono audio under 25MB.
2. Groq transcribes a 1-hour audio in less than 30 seconds.
3. Gemini 1.5 Pro analyzes transcription and returns high-quality candidate clips with scores, titles, hooks, and reasons.

## Phase 3: Advanced Video Editing Pipeline
Goal: Enhance FFmpeg rendering with TikTok-style karaoke subtitles, jump cuts, silence removal, and fade transitions.
Requirements: EDIT-01, EDIT-02, EDIT-03, EDIT-04
Success Criteria:
1. Rendered vertical clips feature ASS subtitles with active-word color highlights.
2. Video automatically zooms in during high-impact moments identified by the AI.
3. Long silent gaps in the audio track are detected and excised.
4. Rendered video has a clean fade-in and fade-out transition.

## Phase 4: Next.js Frontend Dashboard
Goal: Build a premium Next.js dashboard UI to upload videos, view candidates, preview clips, and download them.
Requirements: UI-01, UI-02, UI-03, UI-04
Success Criteria:
1. Interactive drag-and-drop dashboard showing list of uploaded videos and processing status.
2. Beautiful visual gallery of generated clips showing viral scores and explanations.
3. Integrated video player to preview 9:16 vertical cuts directly on the website.
4. One-click download buttons for each clip and a JSON/Markdown report package.
