# Phase 2 Plan - Fast Cloud Transcription and AI Selection

## Goal
Integrate Groq Whisper API for rapid speech-to-text transcription (with audio compression and local fallback), and update the selection workflow to use Gemini 1.5 Pro with pre-filtering.

## Tasks
- [ ] **Audio Extraction and Compression**
  - [ ] Modify `backend/src/transcriber.py` to extract audio using FFmpeg as a 32kbps mono MP3 file.
- [ ] **Groq Whisper Integration**
  - [ ] Implement a Groq Whisper API helper in `backend/src/transcriber.py` using `requests`.
  - [ ] Parse `verbose_json` segment timestamps into standard segment lists.
  - [ ] Implement local fallback to `faster-whisper` when `GROQ_API_KEY` is missing or on API failures.
- [ ] **Gemini 1.5 Pro and Pre-Filtering**
  - [ ] Modify `backend/src/gemini_analyzer.py` to target `gemini-1.5-pro`.
  - [ ] Update `backend/src/clip_selector.py` to run the local rule analyzer first, sort, and slice the top 40 candidates.
  - [ ] Send only these top 40 candidates to the Gemini API and merge evaluations.
