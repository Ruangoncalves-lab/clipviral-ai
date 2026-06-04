# Codebase Concerns

**Analysis Date:** 2026-06-04

## Tech Debt

**Whisper Model Instantiation on Every Call:**
- Issue: `WhisperModel` is loaded from disk into RAM on every call to `transcribe_video()`.
- Files: `src/transcriber.py` (lines 54-59)
- Why: Simple script design that doesn't cache the model instance between run requests.
- Impact: Substantial latency penalty (adds several seconds per execution) and CPU spike on every transcription.
- Fix approach: Implement a model registry or singleton cache in `src/transcriber.py` that keeps the loaded model in memory.

**Hardcoded Portuguese Transcription:**
- Issue: The transcriber is hardcoded to transcribe only Portuguese (`language="pt"`).
- Files: `app.py` (line 83)
- Why: Simplified setup specifically targeted at Portuguese speakers.
- Impact: Videos in English or other languages will be transcribed incorrectly or with poor accuracy.
- Fix approach: Add a language selector dropdown in `app.py` (Gradio blocks) and propagate the selection to `transcribe_video()`.

## Security Considerations

**API Key Exposure via Gradio State:**
- Risk: The Gemini API Key is entered in plain text (though type is "password", it resides in memory) or read from environment variables.
- Files: `app.py` (lines 111, 230)
- Current mitigation: Gradio password type hides inputs in the browser.
- Recommendations: Validate that the API key is not logged or written to temporary debug files.

## Performance Bottlenecks

**Synchronous Local Rendering and Transcription:**
- Problem: The video editing and audio transcription steps run synchronously in the main web execution thread.
- Files: `app.py:process_video_pipeline`, `src/video_editor.py`
- Measurement: Large files block the application for minutes. CPU/RAM usage spikes to 100%.
- Cause: Subprocess execution is blocking and synchronous.
- Improvement path: Run processing tasks using a queue system, task workers, or background thread pools (`concurrent.futures`).

**Montserrat Font Download during Video Rendering:**
- Problem: If the font is missing, it is downloaded synchronously during the video processing pipeline.
- Files: `src/utils.py` (lines 98-125)
- Measurement: Adds several seconds or fails/hangs if internet connection is offline or slow.
- Cause: Synchronous `urllib.request.urlretrieve` call.
- Improvement path: Pre-package the `.ttf` font directly in the repository under `src/resources/` or download it on app startup inside the `__main__` block of `app.py`.

## Fragile Areas

**FFmpeg String Escaping for Titles and Subtitles:**
- Files: `src/video_editor.py` (lines 34-45, 111-122, 125-135)
- Why fragile: Escaping text for the FFmpeg `drawtext` and `subtitles` filter is highly error-prone (e.g., handling backslashes, single quotes, and colons in Windows paths).
- Common failures: Title overlay fails to render or crashes FFmpeg when quotes or colons are in the title text or folder path.
- Safe modification: Carefully test inputs with single quotes and colons before modifying filters. Use relative paths with forward slashes (already implemented for SRT files) to avoid Windows backslash issues.

**Gemini JSON Parsing:**
- Files: `src/gemini_analyzer.py` (lines 62-74)
- Why fragile: Relies on the model returning valid JSON matching a specific schema. If Gemini outputs additional conversational text or fails to close brackets, JSON parsing fails.
- Common failures: `json.JSONDecodeError` during API result parsing fallback.
- Safe modification: Use Pydantic models for structured generation configuration if supported by the model version.

## Scaling Limits

**Local Output Storage Leak:**
- Current capacity: Output files are kept indefinitely under `output/`.
- Limit: Disk storage capacity of the host system.
- Symptoms at limit: No disk space errors, causing video editing, audio extraction, or OS commands to fail.
- Scaling path: Implement an automatic cleanup step in `src/utils.py:cleanup_temp_files()` that also purges output runs older than a configured age (e.g. 24 hours).

## Test Coverage Gaps

**Zero Automated Tests:**
- What's not tested: All code (including core selection algorithms and FFmpeg graph builders) has 0% automated coverage.
- Risk: Changes to regex, overlap calculations, or subtitle styling can break the pipeline silently without immediate feedback.
- Priority: High.
- Difficulty to test: Low for utility functions; medium for FFmpeg/Whisper integration (requires mocking or test fixtures).

---

*Concerns audit: 2026-06-04*
*Update as issues are fixed or new ones discovered*
