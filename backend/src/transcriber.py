import os
import time
import requests
from faster_whisper import WhisperModel
from src.config import TEMP_DIR, DEFAULT_WHISPER_MODEL
from src.utils import run_command

def transcribe_video(video_path, model_size=DEFAULT_WHISPER_MODEL, language="pt", progress_callback=None):
    """
    Extracts audio from video and transcribes it using Groq Whisper API (with local faster-whisper fallback).
    
    Parameters:
      video_path (str): Path to input video file.
      model_size (str): Size of the Whisper model ('tiny', 'base', 'small') for local fallback.
      language (str): Language code (e.g., 'pt').
      progress_callback (func): Optional callback function to report progress.
      
    Returns:
      list: A list of dicts, each with 'start', 'end', and 'text'.
    """
    if progress_callback:
        progress_callback("Iniciando extração de áudio...")
    
    # Ensure temp dir exists
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Extract audio using FFmpeg as compressed MP3 to stay under 25MB
    audio_filename = f"audio_{int(time.time())}.mp3"
    audio_path = os.path.join(TEMP_DIR, audio_filename)
    
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", "-b:a", "32k",
        audio_path
    ]
    
    try:
        run_command(ffmpeg_cmd, log_func=print)
    except Exception as e:
        print(f"Error during audio extraction: {e}")
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise RuntimeError("Erro ao extrair o áudio do vídeo. Verifique se o vídeo possui uma faixa de áudio válida.")
        
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise RuntimeError("O arquivo de áudio extraído está vazio ou inexistente.")

    # 1. Try Groq Whisper API first
    groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_api_key:
        if progress_callback:
            progress_callback("Utilizando transcrição em nuvem via Groq Whisper API...")
        try:
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            headers = {
                "Authorization": f"Bearer {groq_api_key}"
            }
            with open(audio_path, "rb") as f:
                files = {
                    "file": (os.path.basename(audio_path), f, "audio/mpeg")
                }
                data = {
                    "model": "whisper-large-v3",
                    "language": language,
                    "response_format": "verbose_json"
                }
                response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
                
            if response.status_code == 200:
                res_data = response.json()
                segments = []
                for seg in res_data.get("segments", []):
                    segments.append({
                        "start": round(seg.get("start", 0.0), 2),
                        "end": round(seg.get("end", 0.0), 2),
                        "text": seg.get("text", "").strip()
                    })
                if progress_callback:
                    progress_callback(f"Transcrição em nuvem concluída. Encontrados {len(segments)} segmentos.")
                return segments
            else:
                print(f"Groq API returned error status {response.status_code}: {response.text}")
                # Fall through to local fallback
        except Exception as e:
            print(f"Groq API call failed: {e}. Falling back to local Whisper...")
            # Fall through to local fallback

    # 2. Local Fallback (faster-whisper on CPU)
    if progress_callback:
        progress_callback(f"Carregando modelo Whisper local ({model_size}) na CPU...")
        
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
    except Exception as e:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise RuntimeError(f"Falha ao carregar o modelo Whisper local: {e}")

    if progress_callback:
        progress_callback(f"Transcrevendo áudio localmente em '{language}'...")
        
    try:
        segments_generator, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            word_timestamps=False
        )
        
        segments = []
        for segment in segments_generator:
            segments.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip()
            })
            
        if progress_callback:
            progress_callback(f"Transcrição local concluída. Encontrados {len(segments)} segmentos.")
            
        return segments
        
    except Exception as e:
        raise RuntimeError(f"Erro durante a transcrição local: {e}")
    finally:
        # Always clean up the extracted audio file
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"Cleaned up extracted audio: {audio_path}")
            except Exception as e:
                print(f"Could not remove temp audio file: {e}")

