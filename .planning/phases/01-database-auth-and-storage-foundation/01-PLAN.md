# Phase 1 Plan - Database, Auth, and Storage Foundation

## Goal
Implement the core database tables (Profiles, Videos, Clips), set up user authentication via Supabase Auth, and connect the Next.js frontend and FastAPI backend to Cloudflare R2 for secure, client-side direct uploads.

## Tasks
- [x] **Database & Profile Customization**
  - [x] Add `subtitle_font_size`, `subtitle_font_color`, and `subtitle_font_style` to profiles table in `schema.sql`.
  - [x] Apply initial schema script on the active Supabase project database `cortes`.
- [x] **Backend R2 Integration**
  - [x] Add `boto3` dependency to `requirements.txt`.
  - [x] Create `src/r2_client.py` for Cloudflare R2 presigned URL generation and file downloads/uploads.
  - [x] Add `/api/storage/presigned-url` endpoint to `app.py`.
- [x] **Frontend Auth Setup**
  - [x] Initialize `@supabase/supabase-js` client in `frontend/src/lib/supabaseClient.ts`.
  - [x] Create login and registration pages in Next.js.
- [x] **Frontend R2 Upload Flow**
  - [x] Create `UploadVideo` component for browser direct-to-R2 upload with progress tracking.
  - [x] Connect successful uploads to `public.videos` database inserts and trigger background clips processing.
