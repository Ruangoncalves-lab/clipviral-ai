# Architecture

**Analysis Date:** 2026-06-04

## Pattern Overview

**Overall:** Layered Monolithic local Web Application (Gradio UI + Pipeline Coordinator).

**Key Characteristics:**
- **Local Heavyweight Processing:** Speech-to-text (Whisper) and video editing (FFmpeg) run locally on CPU/Host.
- **Stateless Pipeline:** Execution is sequential and doesn't rely on databases; state is handled via on-disk input/output files.
- **Hybrid Semantic Selection:** Leverages either remote AI API (Gemini) or local heuristics (keyword scoring) to identify clips.

## Layers

```
+-------------------------------------------------------------+
|                     User Interface Layer                    |
|             (Gradio Web Application - app.py)               |
+------------------------------------+------------------------+
                                     |
                                     v
+-------------------------------------------------------------+
|                     Coordination Layer                      |
|             (process_video_pipeline - app.py)               |
+-------------------+----------------+--------------------+---+
                    |                |                    |
                    v                v                    v
+----------------------+   +------------------+   +-------------------+
|  Transcription Layer |   | Selection Layer  |   |   Editing Layer   |
| (src/transcriber.py) |   | (src/clip_selec) |   | (src/video_editor)|
+----------------------+   +--------+---------+   +---------+---------+
                                    |                       |
                                    +------------+----------+
                                                 |
                                                 v
                               +--------------------------------------+
                               |          Core Utilities Layer        |
                               |    (src/utils.py, src/config.py)     |
                               +--------------------------------------+
```

**User Interface Layer (`app.py`):**
- Purpose: Provides the web UI layout, custom styles, forms, and handles user interactions.
- Contains: Gradio Blocks layout, options accordion, inputs/outputs definition.

**Coordination Layer (`app.py`):**
- Purpose: Directs the video pipeline steps in sequence: initializes, transcribes, selects clips, crops, generates subtitles, and exports files.
- Contains: `process_video_pipeline()` orchestrator function.

**Transcription Layer (`src/transcriber.py`):**
- Purpose: Handles audio extraction and speech-to-text transcription.
- Contains: Whisper model loading, audio track conversion, and segment parsing.

**Selection Layer (`src/clip_selector.py`):**
- Purpose: Assembles consecutive transcript segments and ranks them by viral potential.
- Contains: Candidate segment grouping, overlap suppression algorithm, and calls to Gemini or local analyzers.
- Modules: `src/gemini_analyzer.py` (Gemini API) and `src/rule_analyzer.py` (local regex/keyword analyzer).

**Editing & Subtitles Layer (`src/video_editor.py`, `src/subtitles.py`):**
- Purpose: Crops video, creates dynamic subtitles, overlays elements, and renders files.
- Contains: FFmpeg complex filters builders, SRT formatting logic, font loading.

**Utility Layer (`src/utils.py`, `src/config.py`):**
- Purpose: Shared configuration, folder setup, safe file name generation, and subprocess command running.

## Data Flow

**Video Processing Pipeline Lifecycle:**

1. **Upload & Probe:** The user uploads a video file. `get_video_duration()` uses `ffprobe` to verify the video length and format.
2. **Audio Extraction:** `transcribe_video()` runs FFmpeg to convert the video's audio track to a mono 16kHz WAV file in the `temp/` folder.
3. **Speech-to-Text:** `faster-whisper` transcribes the WAV file on CPU, outputting raw time-stamped text segments. The WAV file is immediately deleted.
4. **Candidate Bundling:** `build_candidate_clips()` groups segments into candidate windows (between 25-120 seconds) checking for natural pause markers (punctuation, silence).
5. **Viral Scoring:** Candidates are analyzed:
   - *AI Mode:* `analyze_candidates_with_gemini()` sends text snippets to the Gemini API, returning viral score, top-center titles, initial hooks, and category.
   - *Local Mode:* `analyze_candidates_locally()` searches for viral keywords (e.g. "o segredo", "cuidado"), counts filler words, and calculates scores.
6. **Greedy Filtering:** The selector sorts candidates by score and picks non-overlapping ones (allowing max 15% overlap) up to the requested count.
7. **Subtitle Chunking:** For each selected clip, `generate_srt_for_clip()` splits long sentences into max 4-word uppercase subtitle chunks with interpolated timestamps.
8. **Render Clip:** `create_vertical_clip()` builds an FFmpeg filter graph:
   - Scale-crop background to 1080x1920 and apply a box blur.
   - Scale foreground video to fit.
   - Burn-in SRT subtitles at the bottom.
   - Draw text overlay for the title at the top.
   - Encodes via `libx264` to `output/run_[timestamp]/`.
9. **Report & Output:** Metadata is exported to `relatorio_cortes.json` and results are loaded into the Gradio UI gallery.

## Key Abstractions

**Analyzer Interface:**
- Purpose: Evaluates a list of candidate transcript clips and returns them with metadata.
- Implementations: `src/gemini_analyzer.py` and `src/rule_analyzer.py`.

**Subprocess Executor (`src/utils.py`):**
- Purpose: Safe interface for running command line commands (FFmpeg, ffprobe), capturing return codes, and redirecting outputs to logs.
- Function: `run_command()`.

## Entry Points

**Web Interface Entry Point:**
- Location: `app.py`
- Command: `python app.py`
- Responsibility: Launches the Gradio web server at `http://127.0.0.1:7860`.

## Error Handling

**Strategy:**
- User errors (e.g., empty video upload, failed rendering) are caught in the pipeline and thrown as `gr.Error(mensagem)` to show up in the web UI.
- Command-line errors (e.g., corrupt video files, missing FFmpeg) raise `RuntimeError` inside `run_command` and clean up temporary WAV files before exiting.

---

*Architecture analysis: 2026-06-04*
*Update when major patterns change*
