# Testing Patterns

**Analysis Date:** 2026-06-04

## Test Framework

**Runner:**
- None. The project currently has no configured automated test runner (like `pytest` or `unittest`).

**Assertion Library:**
- None.

**Run Commands:**
- No automated test commands are configured in `package.json` or as Python scripts.

## Test File Organization

- There is currently no `tests/` directory or `*.test.py` files in the repository. All logic is verified manually.

## Manual Verification Procedure

Since automated testing is not yet established, features must be manually tested using the following checklist after modifications:

### 1. Verification of the Local Web UI
1. Start the server locally:
   ```bash
   python app.py
   ```
2. Open the browser page at `http://127.0.0.1:7860`.
3. Upload a sample horizontal video (16:9).
4. Run under two separate test modes:
   - **Local Heuristics Mode:** Leave "Usar análise com Gemini AI" unchecked.
   - **Gemini AI Mode:** Check "Usar análise com Gemini AI" and paste a valid `GEMINI_API_KEY` (or let it load from the environment).
5. Click **🚀 Gerar cortes** and watch the Gradio progress bar.

### 2. Output Validation
Inspect the folder `output/run_[timestamp]/` to confirm:
- [ ] At least one clip is generated (unless Whisper finds zero speech segments).
- [ ] Generated MP4 clips are cropped to vertical 9:16 layout (e.g. horizontal video merged with a blurred background layer).
- [ ] Subtitles are burned into the video at the bottom in bold uppercase Montserrat font.
- [ ] A title overlay is burned in at the top.
- [ ] `relatorio_cortes.json` is present and contains valid JSON detailing clip position, title, score, hook, category, start/end timestamps, and filenames.

### 3. Error Handling Verification
- Test file upload with corrupt files or non-video formats to ensure a clean red error box displays in the UI rather than crashing the web server process.
- Verify that the `temp/` folder contains no leftover `.wav` files after processing finishes or crashes.

## Recommended Test Additions (Future Roadmap)

**1. Unit Testing with Pytest:**
- Add `pytest` to `requirements.txt`.
- Mock out `google.generativeai` and `faster_whisper` to test core logic in isolation.
- Target functions for unit testing:
  - `src/utils.py:safe_filename()`
  - `src/utils.py:seconds_to_srt_time()`
  - `src/clip_selector.py:build_candidate_clips()` (test segmentation boundaries)
  - `src/clip_selector.py:select_best_clips()` (test overlap suppression algorithm)

**2. Integration Testing:**
- Write an integration test executing `process_video_pipeline` using a small mock 5-second video asset.

---

*Testing analysis: 2026-06-04*
*Update when testing patterns change*
