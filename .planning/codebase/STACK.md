# Technology Stack

**Analysis Date:** 2026-06-04

## Languages

**Primary:**
- Python 3.x - All application logic, transcription, AI analytics, and video processing.

**Secondary:**
- HTML/CSS - Custom inline styling for the Gradio user interface (`app.py`).

## Runtime

**Environment:**
- Python 3.x Runtime environment.
- Loaded on CPU with `int8` quantization for Whisper (`src/transcriber.py`).

**Package Manager:**
- pip - Dependencies declared in `requirements.txt`.
- Lockfile: None.

## Frameworks

**Core:**
- Gradio >= 4.0.0 - Web framework used to build the user interface and processing pipeline control panel (`app.py`).

**Testing:**
- None - No testing framework is currently configured or used in the project.

**Build/Dev:**
- None.

## Key Dependencies

**Critical:**
- `gradio` (>= 4.0.0) - For the web client UI.
- `faster-whisper` - Fast transcription using Whisper models on CPU via CTranslate2.
- `google-generativeai` - Official Google SDK for interacting with Gemini models (`gemini-1.5-flash`).
- `python-dotenv` - For loading environment variables (like `GEMINI_API_KEY`) from a `.env` file.

**Infrastructure:**
- `ffmpeg` - System-level dependency for audio extraction, video cropping, rendering subtitles, and merging tracks.
- `ffprobe` - System-level dependency for probing video duration and dimensions.

## Configuration

**Environment:**
- Configured via `.env` file or shell environment variables.
- Critical env vars: `GEMINI_API_KEY` (optional, can also be provided directly via the UI).

**Build:**
- `requirements.txt` - Python package dependencies.
- `packages.txt` - System package requirements (FFmpeg).

## Platform Requirements

**Development:**
- Windows, macOS, or Linux with Python 3.x and FFmpeg/ffprobe installed and available on system PATH.

**Production:**
- Any cloud platform or containerized environment supporting Python 3.x and FFmpeg (e.g., Hugging Face Spaces, Docker container, local server). CPU-efficient inference is configured by default.

---

*Stack analysis: 2026-06-04*
*Update after major dependency changes*
