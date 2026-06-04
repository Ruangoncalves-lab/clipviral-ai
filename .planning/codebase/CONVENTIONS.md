# Coding Conventions

**Analysis Date:** 2026-06-04

## Naming Patterns

**Files:**
- snake_case for all modules inside the `src/` directory (e.g. `clip_selector.py`, `gemini_analyzer.py`).
- lowercase for runtime entry scripts (e.g. `app.py`).

**Functions:**
- snake_case for all functions (e.g. `select_best_clips()`, `create_vertical_clip()`, `safe_filename()`).
- Clear action-verbs for functions (e.g., `build_candidate_clips`, `generate_srt_for_clip`, `cleanup_temp_files`).

**Variables:**
- snake_case for standard local and global variables (e.g. `selected_clips`, `api_key`, `is_good_stop`).
- UPPER_SNAKE_CASE for config parameters and constants (e.g. `BASE_DIR`, `DEFAULT_WHISPER_MODEL`, `VIRAL_KEYWORDS`, `VIDEO_WIDTH`).

**Types / Classes:**
- No custom classes or complex type annotations are defined in this repository.
- Standard primitive types are used (e.g., list of dictionaries representing segments or candidates).

## Code Style

**Formatting:**
- standard PEP 8 spacing (4 spaces indentation).
- Max line length is kept under 120 characters where possible.
- Mix of single (`'`) and double (`"`) quotes for string values. Double quotes used consistently for UI texts and docstrings.

## Import Organization

**Order:**
1. Standard Python libraries (`os`, `sys`, `time`, `re`, `json`, `subprocess`).
2. Third-party packages (`gradio`, `dotenv`, `faster_whisper`, `google.generativeai`).
3. Local application imports (e.g., `from src.config import ...`, `from src.utils import ...`).

**Grouping:**
- Grouped by imports type, separated by a blank line.
- Avoid wildcard imports (`from module import *`) — list imported symbols explicitly.

## Error Handling

**Patterns:**
- **Local Exceptions:** Internal domain functions throw `RuntimeError` or `ValueError` with detailed, low-level technical messages.
- **UI Error Guarding:** `app.py` coordinates steps inside a `try/except` block and transforms caught exceptions into user-friendly `gr.Error` notifications to prevent UI crashes.
- **Resource Cleanup:** Temporary files (like audio extractions) are wrapped in `try/finally` blocks in `transcriber.py` to guarantee disk cleanup.

## Logging

**Framework:**
- Standard `print()` statements for backend console output.
- **Subprocess logger:** `run_command` accepts a `log_func` (defaulting to `print`) to log executed command lines and capture stderr if commands fail.
- **User Interface Progress:** Gradio progress callback (`gr.Progress()`) is threaded through the functions to output step percentages and status messages to the browser.

## Comments

**When to Comment:**
- Explain natural constraints (e.g. `# Force limit to 120s`, `# Aspect ratio must be divisible by 2`).
- Describe complex regular expressions or FFmpeg filter layers.
- Avoid commenting obvious statements (e.g. `ensure_dirs()`).

**Docstrings:**
- Recommended for public interface methods.
- Document function parameter types, defaults, and returns.

---

*Convention analysis: 2026-06-04*
*Update when patterns change*
