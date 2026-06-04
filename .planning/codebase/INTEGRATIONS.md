# External Integrations

**Analysis Date:** 2026-06-04

## APIs & External Services

**Generative AI & Analytics:**
- Google Gemini API - Used to analyze video transcripts, grade viral potential, generate titles, identify hooks, and categorize clip content.
  - SDK/Client: `google-generativeai` Python SDK
  - Auth: API key read from `GEMINI_API_KEY` environment variable or provided manually in the UI text input.
  - Models used: `gemini-1.5-flash` (`src/gemini_analyzer.py`)
  - Integration method: REST API client wrapper.

**Assets & Typography:**
- Google Fonts (GitHub Raw CDN) - Downloads Montserrat-Bold font if not found locally.
  - Target URL: `https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Bold.ttf`
  - Integration: `urllib.request.urlretrieve` inside `src/utils.py`
  - Fallbacks: Falls back to Arial/DejaVu system fonts if download fails.

## Data Storage

**File Storage (Local):**
- Temporary Storage:
  - Directory: `temp/` (defined in `src/config.py` as `TEMP_DIR`)
  - Purpose: Stores extracted audio (`.wav`) files for Whisper transcription and generated subtitle files (`.srt`) prior to burn-in.
  - Cleanup: Purged on every pipeline run by `cleanup_temp_files()` in `src/utils.py`.
- Output Storage:
  - Directory: `output/run_[timestamp]/` (defined in `src/config.py` as `OUTPUT_DIR`)
  - Purpose: Contains final cropped vertical MP4 video clips and the clips report JSON file.
  - Persistence: Retained locally until manual deletion.

## Authentication & Identity

- None. There is no user authentication system; it runs as a local web application.

## Monitoring & Observability

- Console/Stdout: Standard python print statements and Gradio Progress callback outputs for error and execution tracing.

## Environment Configuration

**Development & Production:**
- Required env vars: `GEMINI_API_KEY` (optional, can be supplied in the Gradio web UI).
- Secrets location: `.env` file in the project root.

---

*Integration audit: 2026-06-04*
*Update when adding/removing external services*
