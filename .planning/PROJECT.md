# ClipViral AI SaaS

## What This Is
ClipViral AI is a software platform designed to convert long videos into short, high-impact vertical clips (9:16) suitable for TikTok, Instagram Reels, and YouTube Shorts. It uses AI-driven transcription, scoring heuristics, and FFmpeg processing to extract clips with high viral potential and burn-in styled titles and subtitles.

## Core Value
To easily and automatically turn long video files into highly engaging, styled vertical clips ready for social media publishing.

## Requirements

### Validated
- ✓ Local Whisper-based speech-to-text audio transcription
- ✓ Subtitle chunk generation with linear timestamp interpolation
- ✓ Keyword-based and Gemini-assisted viral scoring heuristics
- ✓ FFmpeg-based vertical video cropping, background blurring, and text overlays
- ✓ Restructure the monorepo into separate `/frontend` (Next.js) and `/backend` (FastAPI) directories

### Active
- [ ] Implement database schema in Supabase for Profiles, Videos, and Clips [DB-01]
- [ ] Set up user authentication (signup/login) via Supabase Auth in Next.js [AUTH-01]
- [ ] Integrate Cloudflare R2 for video and clip storage [STORAGE-01]
- [ ] Integrate Groq Whisper API for fast, free audio transcription [TRANS-01]
- [ ] Integrate Gemini 1.5 Pro for high-quality viral clip selection [SELECTION-01]
- [ ] Implement TikTok-style karaoke subtitles (ASS format) with word-by-word highlights [EDIT-01]
- [ ] Implement automated "Jump Cuts" (dynamic zoom-ins) at key moments [EDIT-02]
- [ ] Implement automated silence removal from video [EDIT-03]
- [ ] Create Next.js dashboard UI for video uploads, candidates, and clip downloads [UI-01]


### Out of Scope
- Direct publishing to social media accounts (TikTok/Instagram API integrations) — Deferred to focus on core video processing and SaaS foundations.
- Custom template editor (drag-and-drop subtitle editors) — Out of scope for the initial SaaS release; styling is standardized.

## Context
- The project is transitioning from a single-user local Gradio script into a multi-tenant SaaS application.
- Supabase is selected for authentication, PostgreSQL database, and object storage due to ready-to-use services.
- The existing video editor logic relies heavily on local FFmpeg execution, which will be migrated to the `/backend` folder.

## Constraints
- **Tech Stack**: Next.js (frontend), FastAPI (backend), Supabase (auth/db/storage), and FFmpeg.
- **Resource Constraints**: Video processing is CPU-heavy. The backend must handle execution asynchronously to prevent request timeouts.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Next.js Frontend | Modern React framework for building fast, premium SaaS dashboards | — Pending |
| FastAPI Backend | Reuses existing Python logic while supporting high-performance async endpoints | — Pending |
| Supabase Auth & DB | Speeds up SaaS launch by handling database, user sessions, and video storage | — Pending |

## Evolution
This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-04 after SaaS transformation plan approval*
