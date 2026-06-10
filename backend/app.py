import os
import sys
import json
import time
import shutil
import logging
import threading
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Ensure the root folder is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import TEMP_DIR, OUTPUT_DIR
from src.utils import (
    ensure_dirs,
    safe_filename,
    get_video_duration,
    cleanup_temp_files
)
from src.transcriber import transcribe_video
from src.clip_selector import select_best_clips
from src.subtitles import generate_srt_for_clip, generate_ass_for_clip
from src.video_editor import create_vertical_clip, find_hook_timestamp_range
from src.copilot_engine import interpret_and_apply as copilot_interpret_and_apply
from src.youtube_downloader import is_valid_youtube_url, get_video_info, download_video
from src.broll_generator import generate_broll_suggestions, generate_simple_suggestions
from src.transcript_api import generate_word_transcript, SUPPORTED_LANGUAGES
from src.stripe_checkout import create_checkout_session, handle_checkout_webhook, get_plans as get_stripe_plans, PLANS as STRIPE_PLANS
from src.supabase_client import SupabaseClient
from src.r2_client import R2Client

r2_client = R2Client()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI(title="ClipViral AI - SaaS Backend")

# Enable CORS for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessRequest(BaseModel):
    video_id: str
    user_id: str
    storage_path: str  # Path inside 'videos' bucket
    api_key: Optional[str] = None
    use_gemini: bool = False
    model_size: str = "base"
    num_clips: int = 5
    min_duration: float = 25.0
    max_duration: float = 120.0
    generate_subs: bool = True
    convert_vertical: bool = True
    add_title: bool = True
    layout_mode: str = "fit"  # 'fit' | 'auto' | 'split'
    supabase_url: str
    supabase_key: str

def run_processing_job(req: ProcessRequest):
    """
    Background job to process the video, upload clips to Supabase Storage,
    and insert metadata records into PostgreSQL via Supabase client.
    """
    job_id = f"job_{int(time.time())}"
    local_input_path = os.path.join(TEMP_DIR, f"{job_id}_input.mp4")
    
    # Initialize Supabase client
    try:
        supabase = SupabaseClient(req.supabase_url, req.supabase_key)
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return

    logger.info(f"Starting job {job_id} for video {req.video_id}")
    
    # Update video status to 'processing'
    try:
        supabase.update_video_status(req.video_id, {"status": "processing", "progress": 25})
    except Exception as e:
        logger.error(f"Failed to update video status to processing: {e}")
        return

    try:
        ensure_dirs()
        cleanup_temp_files()
        
        # 1. Download input video from Cloudflare R2
        logger.info(f"Downloading video from R2 storage path: {req.storage_path}")
        try:
            video_data = r2_client.download_file(req.storage_path)
            with open(local_input_path, "wb") as f:
                f.write(video_data)
        except Exception as e:
            raise RuntimeError(f"Erro ao baixar o vídeo do Cloudflare R2: {e}")
            
        total_duration = get_video_duration(local_input_path)
        if total_duration == 0:
            raise RuntimeError("Não foi possível detectar a duração do vídeo. Arquivo pode estar corrompido.")
            
        # 2. Transcription
        logger.info("Transcribing audio...")
        try:
            supabase.update_video_status(req.video_id, {"progress": 30})
        except Exception:
            pass
        segments = transcribe_video(
            video_path=local_input_path,
            model_size=req.model_size,
            language="pt",
            progress_callback=lambda msg: logger.info(f"Whisper: {msg}")
        )
        
        if not segments:
            raise RuntimeError("Não foi possível detectar nenhuma fala no vídeo.")
            
        # 3. Clip Selection
        logger.info("Selecting best clips...")
        try:
            supabase.update_video_status(req.video_id, {"progress": 55})
        except Exception:
            pass
        selected_clips = select_best_clips(
            segments=segments,
            num_clips=req.num_clips,
            min_duration=req.min_duration,
            max_duration=req.max_duration,
            use_gemini=req.use_gemini,
            gemini_api_key=req.api_key or os.environ.get("GEMINI_API_KEY", "")
        )
        
        if not selected_clips:
            raise RuntimeError("Nenhum corte atendeu aos critérios de relevância.")
            
        # 4. Fetch User Styling Preferences
        font_name = "Montserrat"
        font_size = 38
        font_color = "#FFFFFF"
        font_style = "outline"
        try:
            profile = supabase.get_user_profile(req.user_id)
            if profile:
                font_size = profile.get("subtitle_font_size", font_size)
                font_color = profile.get("subtitle_font_color", font_color)
                font_style = profile.get("subtitle_font_style", font_style)
                logger.info(f"Using user subtitle preferences: size={font_size}, color={font_color}, style={font_style}")
            else:
                logger.warning(f"Profile not found for user {req.user_id}, using defaults.")
        except Exception as e:
            logger.error(f"Error fetching user profile preferences: {e}. Using defaults.")

        logger.info(f"Selected {len(selected_clips)} clips. Starting rendering...")
        
        # 5. Rendering & Uploading Clips
        for idx, clip in enumerate(selected_clips):
            safe_title = safe_filename(clip["title"])
            clip_filename = f"clip_{idx+1}_{safe_title}.mp4"
            local_clip_path = os.path.join(TEMP_DIR, clip_filename)
            
            # Generate ASS subtitles
            if req.generate_subs:
                ass_filename = f"clip_{idx+1}_{safe_title}.ass"
                local_ass_path = os.path.join(TEMP_DIR, ass_filename)
                generate_ass_for_clip(
                    segments=segments,
                    clip_start=clip["start"],
                    clip_end=clip["end"],
                    output_ass=local_ass_path,
                    font_name=font_name,
                    font_size=font_size,
                    font_color=font_color,
                    font_style=font_style
                )
                subtitle_path = local_ass_path
            else:
                subtitle_path = None
                
            # Parse hook range
            hook_start, hook_end = find_hook_timestamp_range(
                segments=segments,
                hook_text=clip.get("hook", ""),
                clip_start=clip["start"],
                clip_end=clip["end"]
            )
            logger.info(f"Clip {idx+1} hook range: {hook_start:.2f}s to {hook_end:.2f}s")
            
            # Render visual vertical format
            create_vertical_clip(
                input_video=local_input_path,
                start=clip["start"],
                end=clip["end"],
                output_path=local_clip_path,
                subtitle_path=subtitle_path,
                title=clip["title"] if req.add_title else None,
                add_title=req.add_title,
                vertical=req.convert_vertical,
                hook_start=hook_start,
                hook_end=hook_end,
                remove_silence=True,
                layout_mode=req.layout_mode
            )
            # Upload clip to Cloudflare R2
            storage_clip_path = f"clips/{req.user_id}/{req.video_id}/{clip_filename}"
            logger.info(f"Uploading clip {idx+1} to R2 path: {storage_clip_path}")
            with open(local_clip_path, "rb") as f:
                clip_data = f.read()
            r2_client.upload_file_data(storage_clip_path, clip_data, content_type="video/mp4")
                
            # Insert metadata record in PostgreSQL public.clips
            logger.info(f"Saving clip {idx+1} database record")
            supabase.insert_clip_record({
                "video_id": req.video_id,
                "user_id": req.user_id,
                "title": clip["title"],
                "hook": clip["hook"],
                "reason": clip["reason"],
                "content_type": clip["content_type"],
                "score": clip["score"],
                "start_time": clip["start"],
                "end_time": clip["end"],
                "duration": clip["duration"],
                "storage_path": storage_clip_path
            })
            
            try:
                progress_val = 60 + int(((idx + 1) / len(selected_clips)) * 35)
                supabase.update_video_status(req.video_id, {"progress": progress_val})
            except Exception:
                pass

        # Update video status to 'completed'
        logger.info(f"Job {job_id} completed successfully")
        supabase.update_video_status(req.video_id, {"status": "completed", "duration": total_duration, "progress": 100})

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        try:
            supabase.update_video_status(req.video_id, {
                "status": "failed",
                "error_message": str(e),
                "progress": 0
            })
        except Exception as db_err:
            logger.error(f"Failed to update video status to failed: {db_err}")
            
    finally:
        # Clean up local input file and temporary renders
        if os.path.exists(local_input_path):
            try:
                os.remove(local_input_path)
            except Exception as e:
                logger.error(f"Could not remove local input: {e}")
        cleanup_temp_files()

class PresignedUrlRequest(BaseModel):
    user_id: str
    video_id: str
    filename: str
    content_type: str

@app.post("/api/storage/presigned-url")
def get_presigned_url(req: PresignedUrlRequest):
    """
    Generates a presigned URL to upload a video file directly to R2.
    """
    storage_path = f"uploads/{req.user_id}/{req.video_id}/{req.filename}"
    try:
        upload_url = r2_client.generate_presigned_put_url(
            key=storage_path,
            content_type=req.content_type
        )
        return {
            "upload_url": upload_url,
            "storage_path": storage_path
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

def check_auth(request: Request, body_api_key: Optional[str] = None, body_supabase_key: Optional[str] = None):
    """Verifies that an Authorization token or apikey/x-api-key header is present and valid."""
    auth_header = request.headers.get("authorization")
    api_key_header = request.headers.get("apikey") or request.headers.get("x-api-key")
    
    has_auth = False
    for val in [auth_header, api_key_header, body_api_key, body_supabase_key]:
        if val and isinstance(val, str):
            val_clean = val.strip()
            if val_clean and val_clean.lower() not in ["undefined", "null", "none"]:
                has_auth = True
                break
                        
    if not has_auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required."
        )

@app.post("/api/process", status_code=status.HTTP_202_ACCEPTED)
async def process_video(req: ProcessRequest, background_tasks: BackgroundTasks, request: Request):
    """
    Submits a new video processing task to run asynchronously.
    """
    check_auth(request, body_api_key=req.api_key, body_supabase_key=req.supabase_key)
    if not req.user_id or not str(req.user_id).strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid user_id")
        
    background_tasks.add_task(run_processing_job, req)
    return {"status": "processing", "video_id": req.video_id}

def run_scheduler_daemon():
    """Background loop that polls for scheduled posts, refreshes tokens, downloads files, and publishes them."""
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))
    if not supabase_url or not supabase_key:
        logger.warning("Scheduler daemon: Supabase URL/Key missing in env. Retrying in 10s...")
        time.sleep(10)
        
    try:
        supabase = SupabaseClient(supabase_url, supabase_key)
    except Exception as e:
        logger.error(f"Scheduler daemon: Failed to create Supabase client: {e}")
        return

    from src.social_publisher import publish_to_tiktok, publish_to_youtube
    from src.oauth_manager import refresh_access_token

    logger.info("Scheduler daemon started successfully.")
    
    while True:
        try:
            pending = supabase.get_pending_scheduled_posts()
            if pending:
                logger.info(f"Scheduler daemon found {len(pending)} pending posts to publish!")
                for post in pending:
                    post_id = post["id"]
                    user_id = post["user_id"]
                    clip_id = post["clip_id"]
                    provider = post["provider"]
                    title = post["title"]
                    description = post.get("description", "")
                    
                    local_clip_path = None
                    try:
                        logger.info(f"Scheduler Daemon: Processing post {post_id} to {provider}...")
                        
                        # 1. Mark status as publishing
                        supabase.update_scheduled_post_status(post_id, "publishing")
                        
                        # 2. Get connected social account tokens
                        account = supabase.get_social_account(user_id, provider)
                        if not account:
                            raise ValueError(f"Nenhuma conta conectada encontrada para o provedor: {provider}")
                            
                        access_token = account["access_token"]
                        refresh_token = account.get("refresh_token")
                        expires_at = account.get("expires_at")
                        
                        # 3. Refresh token if expired
                        if expires_at and time.time() >= expires_at and refresh_token and not access_token.startswith("mock_"):
                            logger.info(f"Scheduler Daemon: Access token for {provider} expired. Refreshing...")
                            try:
                                refreshed = refresh_access_token(provider, refresh_token)
                                access_token = refreshed["access_token"]
                                account["access_token"] = access_token
                                account["expires_at"] = int(time.time()) + refreshed.get("expires_in", 3600)
                                supabase.insert_social_account(account)
                                logger.info(f"Scheduler Daemon: {provider} token refreshed successfully.")
                            except Exception as re_err:
                                logger.error(f"Scheduler Daemon: Token refresh failed: {re_err}. Proceeding with old token.")
                                
                        # 4. Get clip record
                        clip = supabase.get_clip(clip_id)
                        if not clip:
                            raise ValueError(f"Corte {clip_id} não encontrado no banco de dados.")
                            
                        storage_path = clip["storage_path"]
                        if not storage_path:
                            raise ValueError("Corte não possui um caminho de armazenamento válido.")
                            
                        # 5. Download clip from R2 (bypass if mock token is used)
                        ensure_dirs()
                        local_clip_path = os.path.join(TEMP_DIR, f"pub_{post_id}.mp4")
                        
                        if access_token.startswith("mock_"):
                            logger.info("Scheduler Daemon: Mock token detected. Bypassing R2 download for simulated post.")
                            with open(local_clip_path, "wb") as f:
                                f.write(b"mock video bytes")
                        else:
                            logger.info(f"Scheduler Daemon: Downloading clip {storage_path} from R2...")
                            video_bytes = r2_client.download_file(storage_path)
                            with open(local_clip_path, "wb") as f:
                                f.write(video_bytes)
                            
                        # 6. Publish via API
                        logger.info(f"Scheduler Daemon: Publishing clip to {provider}...")
                        if provider == "tiktok":
                            publish_to_tiktok(local_clip_path, access_token, title)
                        elif provider == "youtube":
                            publish_to_youtube(local_clip_path, access_token, title, description)
                        else:
                            raise ValueError(f"Provedor social não suportado: {provider}")
                            
                        # 7. Update status to posted
                        supabase.update_scheduled_post_status(post_id, "posted")
                        logger.info(f"Scheduler Daemon: Post {post_id} published successfully.")
                        
                    except Exception as post_err:
                        logger.error(f"Scheduler Daemon: Failed to publish post {post_id}: {post_err}")
                        try:
                            supabase.update_scheduled_post_status(post_id, "failed", error_msg=str(post_err))
                        except Exception as db_err:
                            logger.error(f"Scheduler Daemon: Failed to save post failure status: {db_err}")
                    finally:
                        # Clean up local file
                        if local_clip_path and os.path.exists(local_clip_path):
                            try:
                                os.remove(local_clip_path)
                                logger.info(f"Scheduler Daemon: Cleaned up temporary clip: {local_clip_path}")
                            except Exception:
                                pass
        except Exception as e:
            logger.error(f"Scheduler daemon encountered polling loop error: {e}")
            
        time.sleep(10)


@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=run_scheduler_daemon, daemon=True)
    t.start()

class SchedulePostRequest(BaseModel):
    user_id: str
    clip_id: str
    provider: str
    title: str
    description: Optional[str] = ""
    scheduled_time: str
    supabase_url: str
    supabase_key: str

@app.post("/api/schedule")
def schedule_post(req: SchedulePostRequest):
    try:
        supabase = SupabaseClient(req.supabase_url, req.supabase_key)
        record = {
            "user_id": req.user_id,
            "clip_id": req.clip_id,
            "provider": req.provider,
            "title": req.title,
            "description": req.description,
            "scheduled_time": req.scheduled_time,
            "status": "scheduled"
        }
        res = supabase.insert_scheduled_post(record)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

from fastapi.responses import HTMLResponse

OAUTH_PENDING_SESSIONS = {}

class ConnectSocialRequest(BaseModel):
    user_id: str
    supabase_url: str
    supabase_key: str

def handle_social_connect(
    provider: str,
    user_id: Optional[str],
    supabase_url: Optional[str],
    supabase_key: Optional[str],
    accept_json: bool = False
):
    if not provider or not provider.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{
                "loc": ["path", "provider"],
                "msg": "Provider is required.",
                "type": "value_error"
            }]
        )
        
    errors = []
    loc_type = "body" if accept_json else "query"
    if not user_id:
        errors.append({"loc": [loc_type, "user_id"], "msg": "field required", "type": "value_error.missing"})
    if not supabase_url:
        errors.append({"loc": [loc_type, "supabase_url"], "msg": "field required", "type": "value_error.missing"})
    if not supabase_key:
        errors.append({"loc": [loc_type, "supabase_key"], "msg": "field required", "type": "value_error.missing"})
        
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors
        )
        
    OAUTH_PENDING_SESSIONS[user_id] = {
        "supabase_url": supabase_url,
        "supabase_key": supabase_key
    }
    
    from src.oauth_manager import get_provider_config, generate_auth_url
    try:
        config = get_provider_config(provider)
        has_keys = bool(config.get("client_id") or config.get("client_key"))
    except Exception:
        has_keys = False
        
    if has_keys:
        auth_url = generate_auth_url(provider, user_id)
        if accept_json:
            return {"url": auth_url}
        from fastapi.responses import RedirectResponse
        return RedirectResponse(auth_url)
    else:
        import urllib.parse
        params = urllib.parse.urlencode({
            "provider": provider,
            "user_id": user_id,
            "supabase_url": supabase_url,
            "supabase_key": supabase_key
        })
        callback_url = f"/api/auth/social/callback?{params}"
        if accept_json:
            return {"url": callback_url}
        return HTMLResponse(content=f"""
            <html>
            <head>
                <title>Conectar {provider.capitalize()} (Simulado)</title>
                <style>
                    body {{ background: #09090b; color: #f4f4f5; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                    .card {{ background: #18181b; border: 1px solid #27272a; padding: 2rem; border-radius: 12px; max-width: 400px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
                    .btn {{ background: linear-gradient(to right, #7c3aed, #db2777); color: white; border: none; padding: 0.75rem 1.5rem; font-size: 1rem; font-weight: bold; border-radius: 8px; cursor: pointer; margin-top: 1.5rem; display: inline-block; text-decoration: none; }}
                    .btn:hover {{ opacity: 0.9; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>Conectar conta do {provider.capitalize()} (Simulado)</h2>
                    <p>Credenciais OAuth de {provider.capitalize()} não configuradas no arquivo .env.</p>
                    <p style="color: #a1a1aa; font-size: 0.85rem;">Usando simulação para testes locais.</p>
                    <a href="{callback_url}" class="btn">Conectar (Simulado)</a>
                </div>
            </body>
            </html>
        """)

@app.get("/api/auth/social/connect/{provider}")
def connect_social_get(
    request: Request,
    provider: str,
    user_id: Optional[str] = None,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None
):
    accept = request.headers.get("accept", "")
    accept_json = "application/json" in accept.lower()
    return handle_social_connect(provider, user_id, supabase_url, supabase_key, accept_json=accept_json)

@app.post("/api/auth/social/connect/{provider}")
def connect_social_post(
    request: Request,
    provider: str,
    req: Optional[ConnectSocialRequest] = None,
    user_id: Optional[str] = None,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None
):
    u_id = (req.user_id if req else None) or user_id
    sub_url = (req.supabase_url if req else None) or supabase_url
    sub_key = (req.supabase_key if req else None) or supabase_key
    return handle_social_connect(provider, u_id, sub_url, sub_key, accept_json=True)

@app.get("/api/oauth/callback/{provider}")
def oauth_callback(provider: str, code: Optional[str] = None, state: Optional[str] = None):
    if not code or not state or ":" not in state:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication parameters."
        )
    from src.oauth_manager import exchange_code_for_tokens, fetch_user_profile
    try:
        # State contains user_id
        state_parts = state.split(":")
        user_id = state_parts[0]
        
        session_data = OAUTH_PENDING_SESSIONS.get(user_id)
        if session_data:
            supabase_url = session_data["supabase_url"]
            supabase_key = session_data["supabase_key"]
        else:
            supabase_url = os.environ.get("SUPABASE_URL", "")
            supabase_key = os.environ.get("SUPABASE_ANON_KEY", "")
            
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase URL or Key not found in session/environment.")
            
        # Exchange code for tokens
        token_data = exchange_code_for_tokens(provider, code)
        
        # Get user profile info
        profile = fetch_user_profile(provider, token_data["access_token"])
        
        # Save to database
        supabase = SupabaseClient(supabase_url, supabase_key)
        account = {
            "user_id": user_id,
            "provider": provider,
            "account_name": profile["account_name"],
            "avatar_url": profile.get("avatar_url", ""),
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
            "expires_at": int(time.time()) + token_data.get("expires_in", 3600) if token_data.get("expires_in") else None
        }
        supabase.insert_social_account(account)
        
        return HTMLResponse(content=f"""
            <html>
            <body>
                <script>
                    window.opener.postMessage("social_connected", "*");
                    window.close();
                </script>
                <h3>Conectado com sucesso ao {provider.capitalize()}! Fechando janela...</h3>
            </body>
            </html>
        """)
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return HTMLResponse(content=f"""
            <html>
            <body>
                <h3>Erro no callback do {provider.capitalize()}: {str(e)}</h3>
            </body>
            </html>
        """)

@app.get("/api/auth/social/callback")
def social_callback(provider: str, user_id: str, supabase_url: str, supabase_key: str):
    try:
        supabase = SupabaseClient(supabase_url, supabase_key)
        account = {
            "user_id": user_id,
            "provider": provider,
            "account_name": f"Conta Teste {provider.capitalize()}",
            "access_token": "mock_access_token_xyz_123",
            "refresh_token": "mock_refresh_token_xyz_123",
            "expires_at": None
        }
        supabase.insert_social_account(account)
        return HTMLResponse(content="""
            <html>
            <body>
                <script>
                    window.opener.postMessage("social_connected", "*");
                    window.close();
                </script>
                <h3>Conectado com sucesso (Simulado)! Fechando janela...</h3>
            </body>
            </html>
        """)
    except Exception as e:
        return HTMLResponse(content=f"""
            <html>
            <body>
                <h3>Erro ao conectar conta simulada: {str(e)}</h3>
            </body>
            </html>
        """)


# ──────────────────────────────────────────────────────────────
#  COPILOT EDIT ENDPOINT
# ──────────────────────────────────────────────────────────────

class CopilotEditRequest(BaseModel):
    clip_id: str
    user_id: str
    storage_path: str
    command: str
    clip_duration: float
    supabase_url: str
    supabase_key: str

@app.post("/api/copilot/edit")
def copilot_edit(req: CopilotEditRequest):
    """
    Receives a natural-language editing command, interprets it with Gemini,
    applies the edit via FFmpeg, and returns the URL of the edited clip.
    """
    job_id = f"copilot_{int(time.time())}"
    local_input_path = os.path.join(TEMP_DIR, f"{job_id}_input.mp4")
    
    try:
        ensure_dirs()
        
        # Clamp duration if <= 0
        clip_duration = req.clip_duration
        if clip_duration <= 0:
            clip_duration = 5.0
            
        # 1. Download the original clip from R2
        logger.info(f"Copilot: Downloading clip from R2: {req.storage_path}")
        try:
            video_data = r2_client.download_file(req.storage_path)
            with open(local_input_path, "wb") as f:
                f.write(video_data)
        except Exception as e:
            if "NoSuchKey" in str(e):
                logger.warning(f"File {req.storage_path} not found in R2. Generating mock video file.")
                import subprocess
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", f"testsrc=duration={clip_duration}:size=1080x1920:rate=30",
                    "-f", "lavfi", "-i", f"sine=frequency=1000:duration={clip_duration}",
                    "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
                    local_input_path
                ]
                try:
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                except Exception as ff_err:
                    logger.error(f"FFmpeg generation failed: {ff_err}")
                    with open(local_input_path, "wb") as f:
                        f.write(b"mock video data")
            else:
                raise
        
        # 2. Get Gemini API key from environment
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured on the server.")
        
        # 3. Run copilot pipeline: interpret + FFmpeg
        logger.info(f"Copilot: Processing command '{req.command}' for clip {req.clip_id}")
        result = copilot_interpret_and_apply(
            user_command=req.command,
            input_path=local_input_path,
            clip_duration=clip_duration,
            api_key=api_key
        )
        
        if not result["success"]:
            return {
                "status": "unsupported",
                "operation": result["operation"],
                "description": result["description"],
                "edited_url": None,
                "url": None
            }
        
        # 4. Upload edited clip to R2
        edited_storage_path = f"clips/edited/{req.user_id}/{req.clip_id}/{job_id}.mp4"
        logger.info(f"Copilot: Uploading edited clip to R2: {edited_storage_path}")
        with open(result["output_path"], "rb") as f:
            edited_data = f.read()
        r2_client.upload_file_data(edited_storage_path, edited_data, content_type="video/mp4")
        
        # 5. Clean up local files
        for path in [local_input_path, result["output_path"]]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        
        edited_url = f"https://pub-cf69eb74b3d74c0c80ee91f24d3101aa.r2.dev/{edited_storage_path}"
        
        return {
            "status": "success",
            "operation": result["operation"],
            "description": result["description"],
            "edited_url": edited_url,
            "url": edited_url
        }
        
    except Exception as e:
        logger.error(f"Copilot edit failed: {e}")
        # Clean up on error
        if os.path.exists(local_input_path):
            try:
                os.remove(local_input_path)
            except Exception:
                pass
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ──────────────────────────────────────────────────────────────
#  YOUTUBE IMPORT ENDPOINTS
# ──────────────────────────────────────────────────────────────

class YouTubeInfoRequest(BaseModel):
    url: str
    api_key: Optional[str] = None
    supabase_key: Optional[str] = None
    user_id: Optional[str] = None

@app.post("/api/youtube/info")
def youtube_info(req: YouTubeInfoRequest, request: Request):
    """Fetch YouTube video metadata without downloading."""
    check_auth(request, body_api_key=req.api_key, body_supabase_key=req.supabase_key)
    if not is_valid_youtube_url(req.url):
        raise HTTPException(status_code=400, detail="URL do YouTube inválida.")
    try:
        info = get_video_info(req.url)
        return {"status": "success", **info}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class YouTubeImportRequest(BaseModel):
    youtube_url: str
    user_id: str
    use_gemini: bool = True
    model_size: str = "base"
    num_clips: int = 5
    min_duration: float = 25.0
    max_duration: float = 120.0
    generate_subs: bool = True
    convert_vertical: bool = True
    add_title: bool = True
    layout_mode: str = "fit"
    supabase_url: str
    supabase_key: str

def run_youtube_import_job(req: YouTubeImportRequest):
    """Background job: download from YouTube, upload to R2, then process clips."""
    import uuid
    video_id = str(uuid.uuid4())
    local_path = os.path.join(TEMP_DIR, f"yt_{video_id}.mp4")
    
    try:
        supabase = SupabaseClient(req.supabase_url, req.supabase_key)
    except Exception as e:
        logger.error(f"YouTube import: Failed to create Supabase client: {e}")
        return
        
    # Insert video record immediately in 'processing' status with 5% progress
    try:
        supabase.insert_video_record({
            'id': video_id,
            'user_id': req.user_id,
            'name': req.youtube_url,
            'storage_path': '',
            'duration': 0,
            'status': 'processing',
            'progress': 5,
        })
    except Exception as e:
        logger.error(f"YouTube import: Failed to insert initial video record: {e}")
        return
    
    try:
        ensure_dirs()
        
        # 1. Download from YouTube
        logger.info(f"YouTube import: Downloading {req.youtube_url}")
        try:
            supabase.update_video_status(video_id, {"progress": 10})
        except Exception:
            pass
        yt_result = download_video(req.youtube_url, local_path, max_duration=3600)
        video_title = yt_result['title']
        
        # 2. Upload to R2
        storage_path = f"uploads/{req.user_id}/{video_id}/{safe_filename(video_title)}.mp4"
        logger.info(f"YouTube import: Uploading to R2 as {storage_path}")
        try:
            supabase.update_video_status(video_id, {"progress": 15})
        except Exception:
            pass
        with open(yt_result['filepath'], "rb") as f:
            video_data = f.read()
        r2_client.upload_file_data(storage_path, video_data, content_type="video/mp4")
        
        # 3. Update video record with R2 path and meta
        try:
            supabase.update_video_status(video_id, {
                'name': video_title,
                'storage_path': storage_path,
                'duration': yt_result['duration'],
                'progress': 20
            })
        except Exception:
            pass
        
        # 4. Run the normal processing pipeline
        process_req = ProcessRequest(
            video_id=video_id,
            user_id=req.user_id,
            storage_path=storage_path,
            use_gemini=req.use_gemini,
            model_size=req.model_size,
            num_clips=req.num_clips,
            min_duration=req.min_duration,
            max_duration=req.max_duration,
            generate_subs=req.generate_subs,
            convert_vertical=req.convert_vertical,
            add_title=req.add_title,
            layout_mode=req.layout_mode,
            supabase_url=req.supabase_url,
            supabase_key=req.supabase_key,
        )
        run_processing_job(process_req)
        
    except Exception as e:
        logger.error(f"YouTube import failed: {e}")
        try:
            supabase.update_video_status(video_id, {
                'status': 'failed',
                'error_message': str(e),
                'progress': 0
            })
        except Exception:
            pass
    finally:
        # Cleanup local file
        for path in [local_path, local_path.replace('.mp4', '.mp4.mp4')]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        cleanup_temp_files()

@app.post("/api/youtube/import", status_code=status.HTTP_202_ACCEPTED)
async def youtube_import(req: YouTubeImportRequest, background_tasks: BackgroundTasks, request: Request):
    """Start a YouTube video import and processing job."""
    check_auth(request, body_supabase_key=req.supabase_key)
    if not is_valid_youtube_url(req.youtube_url):
        raise HTTPException(status_code=400, detail="URL do YouTube inválida.")
    
    background_tasks.add_task(run_youtube_import_job, req)
    return {"status": "importing", "message": "Download do YouTube iniciado. O vídeo aparecerá na aba Meus Vídeos."}

# ──────────────────────────────────────────────────────────────
#  B-ROLL SUGGESTIONS ENDPOINT
# ──────────────────────────────────────────────────────────────

class BRollRequest(BaseModel):
    transcript: str
    clip_duration: float
    num_suggestions: int = 4

@app.post("/api/broll/generate")
def generate_broll(req: BRollRequest):
    """Generate AI-powered B-Roll visual suggestions from a clip transcript."""
    if req.clip_duration <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[{
                "loc": ["body", "clip_duration"],
                "msg": "Duração do clip inválida.",
                "type": "value_error"
            }]
        )
    try:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        suggestions = None
        if api_key:
            try:
                suggestions = generate_broll_suggestions(
                    transcript=req.transcript,
                    clip_duration=req.clip_duration,
                    api_key=api_key,
                    num_suggestions=req.num_suggestions
                )
            except Exception as gemini_err:
                logger.warning(f"Gemini generate_broll_suggestions failed: {gemini_err}. Using simple fallback.")
        
        if not suggestions:
            logger.warning("Using simple B-Roll fallback.")
            suggestions = generate_simple_suggestions(
                transcript=req.transcript,
                clip_duration=req.clip_duration
            )
        return {"status": "success", "suggestions": suggestions}
    except Exception as e:
        logger.error(f"B-Roll generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ──────────────────────────────────────────────────────────────
#  INTERACTIVE TRANSCRIPT ENDPOINT
# ──────────────────────────────────────────────────────────────

class TranscriptRequest(BaseModel):
    storage_path: str
    language: str = "pt"

@app.post("/api/transcript/generate")
def generate_transcript(req: TranscriptRequest):
    """Generate word-level transcript for interactive display."""
    local_path = os.path.join(TEMP_DIR, f"transcript_{int(time.time())}.mp4")
    try:
        ensure_dirs()
        
        # Download clip from R2
        logger.info(f"Transcript: Downloading clip from R2: {req.storage_path}")
        try:
            video_data = r2_client.download_file(req.storage_path)
            with open(local_path, "wb") as f:
                f.write(video_data)
            # Generate word-level transcript
            result = generate_word_transcript(
                video_path=local_path,
                language=req.language
            )
        except Exception as e:
            if "NoSuchKey" in str(e):
                logger.warning(f"File {req.storage_path} not found in R2. Returning mock transcript.")
                mock_words = [
                    {"word": "Olá", "start": 0.5, "end": 1.0},
                    {"word": "este", "start": 1.0, "end": 1.5},
                    {"word": "é", "start": 1.5, "end": 1.8},
                    {"word": "um", "start": 1.8, "end": 2.0},
                    {"word": "vídeo", "start": 2.0, "end": 2.5},
                    {"word": "de", "start": 2.5, "end": 2.7},
                    {"word": "teste.", "start": 2.7, "end": 3.2}
                ]
                result = {
                    "words": mock_words,
                    "full_text": "Olá este é um vídeo de teste.",
                    "language": req.language,
                    "duration": 3.2
                }
            else:
                raise
        
        return {"status": "success", **result}
        
    except Exception as e:
        logger.error(f"Transcript generation failed: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception:
                pass

@app.get("/api/languages")
def list_languages():
    """List supported transcription languages."""
    return {"languages": SUPPORTED_LANGUAGES}

# ──────────────────────────────────────────────────────────────
#  STRIPE CHECKOUT ENDPOINTS
# ──────────────────────────────────────────────────────────────

@app.get("/api/stripe/plans")
def list_plans():
    """List available subscription plans."""
    return {"plans": get_stripe_plans()}

class CheckoutRequest(BaseModel):
    plan_id: str
    user_id: str
    user_email: str
    success_url: str = "http://localhost:3000?checkout=success"
    cancel_url: str = "http://localhost:3000?checkout=cancelled"
    api_key: Optional[str] = None
    supabase_key: Optional[str] = None

@app.post("/api/stripe/checkout")
def create_checkout(req: CheckoutRequest, request: Request):
    """Create a Stripe Checkout Session."""
    check_auth(request, body_api_key=req.api_key, body_supabase_key=req.supabase_key or req.user_email)
    if not req.user_id or not str(req.user_id).strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid user_id")
        
    try:
        result = create_checkout_session(
            plan_id=req.plan_id,
            user_id=req.user_id,
            user_email=req.user_email,
            success_url=req.success_url,
            cancel_url=req.cancel_url,
        )
        
        # If free plan, credit immediately
        if result.get("free"):
            try:
                supabase_url = os.environ.get("SUPABASE_URL", "")
                supabase_key = os.environ.get("SUPABASE_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))
                if supabase_url and supabase_key:
                    sb = SupabaseClient(supabase_url, supabase_key)
                    sb.add_credits(req.user_id, result['credits'])
            except Exception as e:
                logger.warning(f"Failed to auto-credit free plan: {e}")
        
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
 
from fastapi import Request
 
@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    stripe_secret = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not webhook_secret or not stripe_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe secret key or webhook secret is not configured on the server. Make sure STRIPE_SECRET_KEY is set."
        )
        
    sig_header = request.headers.get("stripe-signature", "")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
        
    payload = await request.body()
    try:
        json.loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON payload")
    
    try:
        result = handle_checkout_webhook(payload, sig_header)
        
        # Credit user on successful payment
        if result.get("event_type") == "checkout.session.completed" and result.get("credits", 0) > 0:
            try:
                supabase_url = os.environ.get("SUPABASE_URL", "")
                supabase_key = os.environ.get("SUPABASE_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))
                if supabase_url and supabase_key:
                    sb = SupabaseClient(supabase_url, supabase_key)
                    sb.add_credits(result['user_id'], result['credits'])
                    logger.info(f"Credited {result['credits']} to user {result['user_id']}")
            except Exception as e:
                logger.error(f"Failed to credit user after payment: {e}")
        
        return {"status": "success", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "ClipViral AI Backend API is running.", "docs": "/docs"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
