"""
copilot_engine.py — AI-powered Conversational Video Editor
Translates natural-language editing commands into FFmpeg operations using Gemini LLM.
"""
import os
import json
import re
import subprocess
import logging
import time

logger = logging.getLogger("copilot_engine")

try:
    import google.generativeai as genai
except ImportError:
    genai = None
    logger.warning("google.generativeai not installed. Copilot AI will not be available.")

from src.config import TEMP_DIR, OUTPUT_DIR, VIDEO_WIDTH, VIDEO_HEIGHT
from src.utils import run_command


# ──────────────────────────────────────────────────────────────
#  SUPPORTED OPERATIONS REGISTRY
# ──────────────────────────────────────────────────────────────

SUPPORTED_OPERATIONS = {
    "zoom": {
        "description": "Apply zoom/crop to a time range",
        "params": ["zoom_factor", "start_time", "end_time"],
        "example": "Dê zoom de 20% no início do vídeo"
    },
    "trim_start": {
        "description": "Cut seconds from the beginning",
        "params": ["seconds"],
        "example": "Corte os primeiros 3 segundos"
    },
    "trim_end": {
        "description": "Cut seconds from the end",
        "params": ["seconds"],
        "example": "Remova os últimos 5 segundos"
    },
    "speed": {
        "description": "Change playback speed",
        "params": ["factor"],
        "example": "Acelere o vídeo em 1.5x"
    },
    "slow_motion": {
        "description": "Apply slow motion effect",
        "params": ["factor"],
        "example": "Coloque em câmera lenta"
    },
    "brightness": {
        "description": "Adjust brightness level",
        "params": ["value"],
        "example": "Aumente o brilho"
    },
    "contrast": {
        "description": "Adjust contrast level",
        "params": ["value"],
        "example": "Mais contraste"
    },
    "saturation": {
        "description": "Adjust color saturation",
        "params": ["value"],
        "example": "Cores mais vibrantes"
    },
    "flip": {
        "description": "Mirror the video horizontally",
        "params": [],
        "example": "Espelhe o vídeo"
    },
    "grayscale": {
        "description": "Convert to black and white",
        "params": [],
        "example": "Coloque em preto e branco"
    },
    "fade_in": {
        "description": "Add fade-in transition at the start",
        "params": ["duration"],
        "example": "Adicione um fade no início"
    },
    "fade_out": {
        "description": "Add fade-out transition at the end",
        "params": ["duration"],
        "example": "Adicione um fade no final"
    },
}


# ──────────────────────────────────────────────────────────────
#  GEMINI LLM — INTERPRET COMMAND
# ──────────────────────────────────────────────────────────────

def interpret_command(user_command: str, clip_duration: float, api_key: str) -> dict:
    """
    Sends the user's natural-language command to Gemini LLM and receives
    a structured JSON describing the FFmpeg operation to apply.
    
    Returns dict: { "operation": str, "params": dict, "description": str }
    """
    if genai is None:
        raise RuntimeError("google.generativeai is not installed.")
    
    if not api_key:
        raise ValueError("Gemini API key is required for the copilot.")
    
    genai.configure(api_key=api_key)
    
    # Build the operations spec for the prompt
    ops_spec = json.dumps(
        {k: {"description": v["description"], "params": v["params"], "example": v["example"]} 
         for k, v in SUPPORTED_OPERATIONS.items()},
        ensure_ascii=False, indent=2
    )
    
    prompt = f"""Você é o motor de edição de vídeo do ClipViral AI. O usuário deu um comando de edição em linguagem natural.
Sua tarefa é traduzir esse comando em UMA operação técnica de edição de vídeo.

CONTEXTO DO CLIP:
- Duração total: {clip_duration:.1f} segundos
- Resolução: {VIDEO_WIDTH}x{VIDEO_HEIGHT} (vertical 9:16)

OPERAÇÕES DISPONÍVEIS:
{ops_spec}

REGRAS:
1. Escolha EXATAMENTE UMA operação da lista acima.
2. Preencha os parâmetros com valores razoáveis baseados no comando do usuário.
3. Se o usuário não especificou um valor, use valores padrão sensatos.
4. Se o comando não corresponde a nenhuma operação, use "operation": "unsupported".

Retorne SOMENTE um JSON válido no formato:
{{
  "operation": "nome_da_operacao",
  "params": {{ ... }},
  "description": "Descrição curta em português do que será feito"
}}

COMANDO DO USUÁRIO: "{user_command}"
"""

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        response_text = response.text.strip()
        # Clean markdown fences if present
        if response_text.startswith("```"):
            response_text = re.sub(r"^```(?:json)?\n", "", response_text)
            response_text = re.sub(r"\n```$", "", response_text)
            response_text = response_text.strip()
        
        result = json.loads(response_text)
        logger.info(f"Copilot interpreted command: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Gemini interpretation failed: {e}")
        raise RuntimeError(f"Erro ao interpretar comando com IA: {e}")


# ──────────────────────────────────────────────────────────────
#  FFMPEG — BUILD AND EXECUTE EDIT COMMAND
# ──────────────────────────────────────────────────────────────

def build_ffmpeg_filters(operation: str, params: dict, clip_duration: float) -> dict:
    """
    Translates a structured operation + params into FFmpeg arguments.
    
    Returns dict with keys:
        - "filters": list of filter strings for -filter_complex
        - "input_args": list of extra input arguments (e.g. -ss, -t)
        - "output_args": list of extra output arguments
    """
    filters = []
    input_args = []
    output_args = []
    
    if operation == "zoom":
        factor = float(params.get("zoom_factor", 0.2))
        crop_ratio = max(0.5, 1.0 - factor)
        start_t = float(params.get("start_time", 0))
        end_t = float(params.get("end_time", min(5.0, clip_duration)))
        
        filters.append(
            f"[0:v]split=2[base][zoom_src];"
            f"[zoom_src]crop=iw*{crop_ratio:.2f}:ih*{crop_ratio:.2f}:(iw-ow)/2:(ih-oh)/2,"
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}[zoomed];"
            f"[base][zoomed]overlay=0:0:enable='between(t,{start_t:.2f},{end_t:.2f})'[outv]"
        )
        
    elif operation == "trim_start":
        seconds = float(params.get("seconds", 3))
        seconds = min(seconds, clip_duration - 1)
        input_args.extend(["-ss", f"{seconds:.2f}"])
        
    elif operation == "trim_end":
        seconds = float(params.get("seconds", 5))
        new_duration = max(1.0, clip_duration - seconds)
        input_args.extend(["-t", f"{new_duration:.2f}"])
        
    elif operation == "speed":
        factor = float(params.get("factor", 1.5))
        factor = max(0.5, min(4.0, factor))
        pts_factor = 1.0 / factor
        filters.append(f"[0:v]setpts={pts_factor:.4f}*PTS[outv]")
        # Audio tempo adjustment (atempo only supports 0.5-2.0, chain if needed)
        if factor <= 2.0:
            filters.append(f"[0:a]atempo={factor:.2f}[outa]")
        else:
            # Chain two atempo filters for >2x speed
            filters.append(f"[0:a]atempo=2.0,atempo={factor/2.0:.2f}[outa]")
        
    elif operation == "slow_motion":
        factor = float(params.get("factor", 2.0))
        factor = max(1.0, min(4.0, factor))
        filters.append(f"[0:v]setpts={factor:.2f}*PTS[outv]")
        tempo = 1.0 / factor
        if tempo >= 0.5:
            filters.append(f"[0:a]atempo={tempo:.4f}[outa]")
        else:
            filters.append(f"[0:a]atempo=0.5,atempo={tempo/0.5:.4f}[outa]")
        
    elif operation == "brightness":
        value = float(params.get("value", 0.1))
        value = max(-0.5, min(0.5, value))
        filters.append(f"[0:v]eq=brightness={value:.2f}[outv]")
        
    elif operation == "contrast":
        value = float(params.get("value", 1.3))
        value = max(0.5, min(3.0, value))
        filters.append(f"[0:v]eq=contrast={value:.2f}[outv]")
        
    elif operation == "saturation":
        value = float(params.get("value", 1.5))
        value = max(0.0, min(3.0, value))
        filters.append(f"[0:v]eq=saturation={value:.2f}[outv]")
        
    elif operation == "flip":
        filters.append("[0:v]hflip[outv]")
        
    elif operation == "grayscale":
        filters.append(
            "[0:v]colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3[outv]"
        )
        
    elif operation == "fade_in":
        dur = float(params.get("duration", 1.0))
        dur = max(0.3, min(5.0, dur))
        filters.append(f"[0:v]fade=t=in:st=0:d={dur:.2f}[outv]")
        filters.append(f"[0:a]afade=t=in:ss=0:d={dur:.2f}[outa]")
        
    elif operation == "fade_out":
        dur = float(params.get("duration", 1.0))
        dur = max(0.3, min(5.0, dur))
        fade_start = max(0, clip_duration - dur)
        filters.append(f"[0:v]fade=t=out:st={fade_start:.2f}:d={dur:.2f}[outv]")
        filters.append(f"[0:a]afade=t=out:st={fade_start:.2f}:d={dur:.2f}[outa]")
        
    else:
        raise ValueError(f"Operação não suportada: {operation}")
    
    return {
        "filters": filters,
        "input_args": input_args,
        "output_args": output_args
    }


def execute_edit(input_path: str, output_path: str, operation: str, params: dict, clip_duration: float):
    """
    Applies a single edit operation to a video file using FFmpeg.
    """
    ffmpeg_config = build_ffmpeg_filters(operation, params, clip_duration)
    
    cmd = ["ffmpeg", "-y"]
    
    # Input args (e.g. -ss for trim)
    cmd.extend(ffmpeg_config["input_args"])
    cmd.extend(["-i", input_path])
    
    filters = ffmpeg_config["filters"]
    has_video_out = any("[outv]" in f for f in filters)
    has_audio_out = any("[outa]" in f for f in filters)
    
    if filters:
        filter_str = ";".join(filters)
        cmd.extend(["-filter_complex", filter_str])
        
        if has_video_out:
            cmd.extend(["-map", "[outv]"])
        else:
            cmd.extend(["-map", "0:v"])
            
        if has_audio_out:
            cmd.extend(["-map", "[outa]"])
        else:
            cmd.extend(["-map", "0:a?"])
    else:
        cmd.extend(["-map", "0:v", "-map", "0:a?"])
    
    cmd.extend(ffmpeg_config["output_args"])
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ])
    
    logger.info(f"Copilot FFmpeg command: {' '.join(cmd)}")
    
    try:
        run_command(cmd, log_func=logger.info)
        logger.info(f"Copilot edit completed: {output_path}")
    except Exception as e:
        logger.error(f"Copilot FFmpeg failed: {e}")
        raise RuntimeError(f"Erro na renderização do copilot: {e}")


# ──────────────────────────────────────────────────────────────
#  MAIN ORCHESTRATOR
# ──────────────────────────────────────────────────────────────

def interpret_and_apply(
    user_command: str,
    input_path: str,
    clip_duration: float,
    api_key: str,
    output_dir: str = None
) -> dict:
    """
    Full pipeline: interpret user command → build FFmpeg → execute → return result.
    
    Returns dict:
        {
            "output_path": str,
            "operation": str,
            "description": str,
            "success": bool
        }
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Interpret command with Gemini
    interpretation = interpret_command(user_command, clip_duration, api_key)
    
    operation = interpretation.get("operation", "unsupported")
    params = interpretation.get("params", {})
    description = interpretation.get("description", "Edição aplicada.")
    
    if operation == "unsupported":
        return {
            "output_path": None,
            "operation": "unsupported",
            "description": description or "Desculpe, não consigo executar esse tipo de edição ainda.",
            "success": False
        }
    
    # 2. Generate output path
    timestamp = int(time.time())
    output_filename = f"copilot_{timestamp}_{operation}.mp4"
    output_path = os.path.join(output_dir, output_filename)
    
    # 3. Execute the edit
    try:
        execute_edit(input_path, output_path, operation, params, clip_duration)
    except Exception as e:
        return {
            "output_path": None,
            "operation": operation,
            "description": f"Erro ao aplicar edição: {e}",
            "success": False
        }
    
    return {
        "output_path": output_path,
        "operation": operation,
        "description": description,
        "success": True
    }
