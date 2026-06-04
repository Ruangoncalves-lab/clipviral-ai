# Phase 3: Advanced Video Editing Pipeline - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Enhance the video rendering pipeline with advanced, professional video editing features including TikTok-style karaoke subtitles (ASS format), auto-zoom effects on hook sentences, and automated silence removal.

</domain>

<decisions>
## Implementation Decisions

### TikTok-Style Karaoke Subtitles (ASS Format)
- **D-01:** Replace the static SRT subtitles file generator with an Advanced SubStation Alpha (.ass) generator.
- **D-02:** Program dynamic word-by-word highlights using ASS karaoke tags (`{\kf<duration>}` in centiseconds).
- **D-03:** Fetch the user's styling preferences (font size, style, primary color) from the Supabase `profiles` table to customize the subtitle rendering dynamically per user.

### Auto-Zoom / Jump Cuts
- **D-04:** Ask Gemini 1.5 Pro to identify the exact start and end timestamps of the "hook sentence" inside each selected clip.
- **D-05:** Apply a dynamic FFmpeg crop filter to perform a centered 10% to 15% zoom-in during these hook timestamps to create engaging "jump cuts" automatically.

### Automated Silence Removal
- **D-06:** Detect silence periods (volume below -40dB for longer than 1.0 second) using FFmpeg's `silencedetect` filter.
- **D-07:** Construct a dynamic FFmpeg filter complex to trim out silent periods and concatenate the remaining active video and audio segments, maintaining perfect audio-video synchronization.

### the agent's Discretion
- Default font to Montserrat if the user hasn't selected a preference.
- Style transition timings (e.g. fade-in/fade-out duration set to 0.5s).
- Subtitle vertical position (MarginV) adjustment for mobile layout ratios.

</decisions>

<canonical_refs>
## Canonical References

### Video Rendering
- `backend/src/video_editor.py` — FFmpeg layout, resizing, and rendering logic.
- `backend/src/subtitles.py` — Subtitle time interpolation and formatting.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/src/video_editor.py`: The `create_vertical_clip` function already does resizing, scaling, and subtitle burning. We will modify it to handle ASS burning, zoom filters, and silence removal.
- `backend/src/subtitles.py`: The chunking and interpolation logic can be adapted to write ASS file blocks instead of SRT entries.

### Established Patterns
- FFmpeg filter graphs are constructed dynamically in Python and executed using `subprocess`.

</code_context>

<deferred>
## Deferred Ideas

- Sound effects (SFX) inserts at transition points — Deferred to keep rendering time lightweight.

</deferred>

---

*Phase: 03-advanced-video-editing-pipeline*
*Context gathered: 2026-06-04*
