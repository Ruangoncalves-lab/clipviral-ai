"""
transcript_api.py — Word-level transcript generation for interactive karaoke display.
Uses Whisper with word_timestamps=True to get per-word timing data.
"""
import os
import time
import logging
import requests

logger = logging.getLogger("transcript_api")

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None
    logger.warning("faster-whisper not installed. Local transcription not available.")

from src.config import TEMP_DIR, DEFAULT_WHISPER_MODEL
from src.utils import run_command


SUPPORTED_LANGUAGES = {
    "pt": "Português",
    "en": "English",
    "es": "Español",
}


def generate_word_transcript(
    video_path: str,
    language: str = "pt",
    model_size: str = "base"
) -> dict:
    """
    Generates a word-level transcript from a video/audio file.
    
    Returns:
        {
            "words": [{ "word": str, "start": float, "end": float }],
            "full_text": str,
            "language": str,
            "duration": float
        }
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Extract audio
    audio_filename = f"transcript_audio_{int(time.time())}.mp3"
    audio_path = os.path.join(TEMP_DIR, audio_filename)
    
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", "-b:a", "32k",
        audio_path
    ]
    
    try:
        run_command(ffmpeg_cmd, log_func=logger.info)
    except Exception as e:
        raise RuntimeError(f"Erro ao extrair áudio: {e}")
    
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        raise RuntimeError("Arquivo de áudio extraído está vazio.")
    
    words_list = []
    full_text = ""
    
    try:
        # Try Groq API first (has word-level timestamps in verbose_json)
        groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if groq_api_key:
            logger.info("Using Groq Whisper API for word-level transcription...")
            words_list, full_text = _transcribe_groq(audio_path, language, groq_api_key)
        
        # Fallback to local Whisper with word_timestamps=True
        if not words_list:
            logger.info(f"Using local Whisper ({model_size}) with word_timestamps...")
            words_list, full_text = _transcribe_local(audio_path, language, model_size)
    
    finally:
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass
    
    # Calculate total duration from words
    duration = words_list[-1]["end"] if words_list else 0
    
    return {
        "words": words_list,
        "full_text": full_text,
        "language": language,
        "duration": round(duration, 2)
    }


def _transcribe_groq(audio_path: str, language: str, api_key: str) -> tuple:
    """Transcribe using Groq Whisper API with word-level timestamps."""
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
            data = {
                "model": "whisper-large-v3",
                "language": language,
                "response_format": "verbose_json",
                "timestamp_granularities[]": "word"
            }
            response = requests.post(url, headers=headers, files=files, data=data, timeout=120)
        
        if response.status_code == 200:
            res_data = response.json()
            words = []
            
            # Try word-level timestamps first
            if "words" in res_data:
                for w in res_data["words"]:
                    words.append({
                        "word": w.get("word", "").strip(),
                        "start": round(float(w.get("start", 0)), 2),
                        "end": round(float(w.get("end", 0)), 2),
                    })
            
            # Fallback: extract words from segments with interpolated timestamps
            if not words and "segments" in res_data:
                for seg in res_data["segments"]:
                    seg_words = seg.get("text", "").strip().split()
                    seg_start = float(seg.get("start", 0))
                    seg_end = float(seg.get("end", 0))
                    seg_duration = seg_end - seg_start
                    
                    for i, word in enumerate(seg_words):
                        w_start = seg_start + (i / max(len(seg_words), 1)) * seg_duration
                        w_end = seg_start + ((i + 1) / max(len(seg_words), 1)) * seg_duration
                        words.append({
                            "word": word.strip(),
                            "start": round(w_start, 2),
                            "end": round(w_end, 2),
                        })
            
            full_text = res_data.get("text", " ".join(w["word"] for w in words))
            logger.info(f"Groq transcription: {len(words)} words")
            return words, full_text.strip()
        else:
            logger.warning(f"Groq API error {response.status_code}: {response.text}")
            return [], ""
            
    except Exception as e:
        logger.warning(f"Groq transcription failed: {e}")
        return [], ""


def _transcribe_local(audio_path: str, language: str, model_size: str) -> tuple:
    """Transcribe using local faster-whisper with word_timestamps=True."""
    if WhisperModel is None:
        raise RuntimeError("faster-whisper not installed.")
    
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments_gen, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=5,
        word_timestamps=True
    )
    
    words = []
    full_text_parts = []
    
    for segment in segments_gen:
        full_text_parts.append(segment.text.strip())
        
        if segment.words:
            for w in segment.words:
                words.append({
                    "word": w.word.strip(),
                    "start": round(w.start, 2),
                    "end": round(w.end, 2),
                })
        else:
            # Fallback: split segment text and interpolate
            seg_words = segment.text.strip().split()
            seg_duration = segment.end - segment.start
            for i, word in enumerate(seg_words):
                w_start = segment.start + (i / max(len(seg_words), 1)) * seg_duration
                w_end = segment.start + ((i + 1) / max(len(seg_words), 1)) * seg_duration
                words.append({
                    "word": word.strip(),
                    "start": round(w_start, 2),
                    "end": round(w_end, 2),
                })
    
    full_text = " ".join(full_text_parts)
    logger.info(f"Local transcription: {len(words)} words")
    return words, full_text.strip()
