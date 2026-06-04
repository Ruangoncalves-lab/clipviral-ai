# Phase 2: Fast Cloud Transcription and AI Selection - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate Groq Whisper API for ultra-fast, cloud-based audio transcription of long video uploads. Integrate Gemini 1.5 Pro for deep AI analysis and selection of viral candidate clips.

</domain>

<decisions>
## Implementation Decisions

### Audio Compression
- **D-01:** Extract audio from the video and compress it using FFmpeg into a low-bitrate MP3 format (mono, 32kbps, 16kHz) to ensure a 1-hour video's audio track size remains strictly below Groq's 25MB upload limit (typically ~10-15MB).

### Cloud Transcription (Groq)
- **D-02:** Use the Groq Whisper API (`whisper-large-v3` model) with `verbose_json` response format to fetch segment timestamps.
- **D-03:** Implement a local fallback: if `GROQ_API_KEY` is missing or if the API rate limit is exceeded, automatically fallback to local `faster-whisper` (CPU) transcription.

### AI Selection Pre-Filtering
- **D-04:** Pre-filter candidate clips locally using the keyword rule analyzer to identify the top 40 candidates, and send only these top candidates to the Gemini 1.5 Pro API. This avoids output token limits (8192 tokens) and prevents request timeouts.
- **D-05:** Configure the Gemini API call to use the `gemini-1.5-pro` model for high-quality viral evaluation, falling back to `gemini-1.5-flash` or local rules on error.

### the agent's Discretion
- Choice of specific Whisper model version (e.g., `whisper-large-v3` or `whisper-large-v3-turbo`).
- Custom request timeout parameters for Groq API.
- Prompt framing details for Gemini 1.5 Pro.

</decisions>

<canonical_refs>
## Canonical References

### AI Integrations
- `backend/src/transcriber.py` — Audio extraction and Whisper transcription logic.
- `backend/src/gemini_analyzer.py` — Gemini SDK integration and candidate evaluation prompt.
- `backend/src/clip_selector.py` — Orchestrates candidate generation and selection.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/src/rule_analyzer.py`: Can be used to score and rank candidates locally before sending the top ones to Gemini.
- `backend/src/transcriber.py`: Already handles audio extraction; needs modification for MP3 compression and Groq HTTP call.

### Established Patterns
- Pydantic model configurations are used for requests.
- Environment variables are read via `dotenv` in the backend.

</code_context>

<deferred>
## Deferred Ideas

- Transcription of multiple audio languages (defaulting strictly to Portuguese `pt` for V1.0).

</deferred>

---

*Phase: 02-fast-cloud-transcription-and-ai-selection*
*Context gathered: 2026-06-04*
