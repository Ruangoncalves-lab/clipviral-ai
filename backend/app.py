import os
import sys
import time
import shutil
import logging
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

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
from src.subtitles import generate_srt_for_clip
from src.video_editor import create_vertical_clip
from src.supabase_client import SupabaseClient
from src.r2_client import R2Client

r2_client = R2Client()

load_dotenv()
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
        supabase.update_video_status(req.video_id, {"status": "processing"})
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
            
        logger.info(f"Selected {len(selected_clips)} clips. Starting rendering...")
        
        # 4. Rendering & Uploading Clips
        for idx, clip in enumerate(selected_clips):
            safe_title = safe_filename(clip["title"])
            clip_filename = f"clip_{idx+1}_{safe_title}.mp4"
            local_clip_path = os.path.join(TEMP_DIR, clip_filename)
            
            srt_filename = f"clip_{idx+1}_{safe_title}.srt"
            local_srt_path = os.path.join(TEMP_DIR, srt_filename)
            
            # Generate SRT subtitles
            if req.generate_subs:
                generate_srt_for_clip(segments, clip["start"], clip["end"], local_srt_path)
                srt_path = local_srt_path
            else:
                srt_path = None
                
            # Render visual vertical format
            create_vertical_clip(
                input_video=local_input_path,
                start=clip["start"],
                end=clip["end"],
                output_path=local_clip_path,
                srt_path=srt_path,
                title=clip["title"] if req.add_title else None,
                add_title=req.add_title,
                vertical=req.convert_vertical
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

        # Update video status to 'completed'
        logger.info(f"Job {job_id} completed successfully")
        supabase.update_video_status(req.video_id, {"status": "completed", "duration": total_duration})

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        try:
            supabase.update_video_status(req.video_id, {
                "status": "failed",
                "error_message": str(e)
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

@app.post("/api/process", status_code=status.HTTP_202_ACCEPTED)
async def process_video(req: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Submits a new video processing task to run asynchronously.
    """
    background_tasks.add_task(run_processing_job, req)
    return {"status": "processing", "video_id": req.video_id}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
