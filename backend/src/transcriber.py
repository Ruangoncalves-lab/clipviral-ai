import os
import time
from faster_whisper import WhisperModel
from src.config import TEMP_DIR, DEFAULT_WHISPER_MODEL
from src.utils import run_command

def transcribe_video(video_path, model_size=DEFAULT_WHISPER_MODEL, language="pt", progress_callback=None):
    """
    Extracts audio from video and transcribes it using faster-whisper on CPU.
    
    Parameters:
      video_path (str): Path to input video file.
      model_size (str): Size of the Whisper model ('tiny', 'base', 'small').
      language (str): Language code (e.g., 'pt').
      progress_callback (func): Optional callback function to report progress.
      
    Returns:
      list: A list of dicts, each with 'start', 'end', and 'text'.
    """
    if progress_callback:
        progress_callback("Iniciando extração de áudio...")
    
    # Ensure temp dir exists
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Extract audio using FFmpeg
    audio_filename = f"audio_{int(time.time())}.wav"
    audio_path = os.path.join(TEMP_DIR, audio_filename)
    
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        audio_path
    ]
    
    try:
        run_command(ffmpeg_cmd, log_func=print)
    except Exception as e:
        print(f"Error during audio extraction: {e}")
        # Clean up in case of failure
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise RuntimeError("Erro ao extrair o áudio do vídeo. Verifique se o vídeo possui uma faixa de áudio válida.")
        
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise RuntimeError("O arquivo de áudio extraído está vazio ou inexistente.")

    if progress_callback:
        progress_callback(f"Carregando modelo Whisper ({model_size}) na CPU...")
        
    # Load Whisper model using int8 for CPU efficiency
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
    except Exception as e:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise RuntimeError(f"Falha ao carregar o modelo Whisper: {e}")

    if progress_callback:
        progress_callback(f"Transcrevendo áudio em '{language}'...")
        
    try:
        # Transcribe
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
            progress_callback(f"Transcrição concluída. Encontrados {len(segments)} segmentos.")
            
        return segments
        
    except Exception as e:
        raise RuntimeError(f"Erro durante a transcrição: {e}")
    finally:
        # Always clean up the extracted audio file
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"Cleaned up extracted audio: {audio_path}")
            except Exception as e:
                print(f"Could not remove temp audio file: {e}")
