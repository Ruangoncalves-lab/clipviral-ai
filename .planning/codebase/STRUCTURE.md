# Codebase Structure

**Analysis Date:** 2026-06-04

## Directory Layout

```
clipviral-ai/
├── output/                 # Rendered vertical clips and run reports
├── src/                    # Python source packages
│   ├── resources/          # Resources folder (stores downloaded font files)
│   ├── clip_selector.py    # Candidate segmentation and greedy selector
│   ├── config.py           # Path configs and default constants
│   ├── gemini_analyzer.py  # Gemini model transcript scorer
│   ├── rule_analyzer.py    # Local keyword and punctuation scorer
│   ├── subtitles.py        # SRT formatter and dynamic chunk splitters
│   ├── transcriber.py      # Audio extraction and Whisper runner
│   ├── utils.py            # CLI execution, time formatting, and font downloader
│   └── video_editor.py     # FFmpeg filter builder and video render engine
├── temp/                   # Gitignored temp directory for wav files and srt scripts
├── .env                    # Local environment secrets (API Keys)
├── .gitignore              # Ignored folder settings (temp, output, pycache)
├── app.py                  # Gradio application entry point and pipeline orchestrator
├── packages.txt            # System dependencies manifest
├── README.md               # User-facing manual and installation guide
└── requirements.txt        # Python dependencies manifest
```

## Directory Purposes

**src/**
- Purpose: Application core packages and business logic.
- Contains: `*.py` files implementing individual components of the pipeline.
- Subdirectories: `resources/` (stores binary assets).

**src/resources/**
- Purpose: Host asset binaries needed at runtime.
- Contains: Montserrat font files (e.g. `Montserrat-Bold.ttf`). Created dynamically at startup or download.

**temp/**
- Purpose: Temporary workspace directory.
- Contains: Extracted `.wav` audio tracks and individual clip `.srt` subtitles.
- Committed: No (configured in `.gitignore`).

**output/**
- Purpose: Host finalized exported videos.
- Contains: Subfolders named `run_[timestamp]/` with MP4 vertical videos and `relatorio_cortes.json`.
- Committed: No (configured in `.gitignore`).

## Key File Locations

**Entry Points:**
- `app.py` - Web server interface launch and pipeline conductor.

**Configuration:**
- `src/config.py` - Default parameters, video aspect ratios, and workspace folder locations.
- `requirements.txt` - Python module dependencies.
- `packages.txt` - OS package requirements.
- `.env` - Credentials storage.

**Core Logic:**
- `src/transcriber.py` - Whisper wrapper.
- `src/clip_selector.py` - Groups segments and handles overlap checks.
- `src/video_editor.py` - FFmpeg filter generator and rendering process.

## Naming Conventions

**Files:**
- snake_case for python files in `src/` (e.g., `clip_selector.py`).
- lowercase for entry points (`app.py`).

**Directories:**
- lowercase for all workspace directories (`src/`, `temp/`, `output/`).

## Where to Add New Code

**New Visual Effect / Crop Pattern:**
- Implementation: `src/video_editor.py` - modify `create_vertical_clip()` filter graphs.

**New Evaluation Heuristic (e.g., Sentiment Analysis):**
- Implementation: `src/rule_analyzer.py` - add criteria, or create `src/sentiment_analyzer.py` and import in `src/clip_selector.py`.

**New Config / Aspect Ratio option:**
- Constants: Add to `src/config.py`.
- Form Controls: Add input options in `app.py` (Gradio layout).

---

*Structure analysis: 2026-06-04*
*Update when directory structure changes*
