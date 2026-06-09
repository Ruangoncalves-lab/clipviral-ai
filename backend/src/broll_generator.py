"""
broll_generator.py — AI-powered B-Roll suggestion engine.
Analyzes video transcripts and generates contextual visual suggestions
using Gemini LLM instead of generic stock footage.
"""
import os
import json
import re
import logging

logger = logging.getLogger("broll_generator")

try:
    import google.generativeai as genai
except ImportError:
    genai = None
    logger.warning("google.generativeai not installed. B-Roll suggestions will not be available.")


# ──────────────────────────────────────────────────────────────
#  B-ROLL CATEGORIES
# ──────────────────────────────────────────────────────────────

BROLL_CATEGORIES = {
    "illustration": "Ilustração conceitual para explicar uma ideia abstrata",
    "data_viz": "Gráfico ou visualização de dados para reforçar um argumento",
    "scene": "Cena cinematográfica para criar atmosfera emocional",
    "object": "Objeto ou produto em close-up para detalhar algo mencionado",
    "environment": "Ambiente ou cenário que contextualiza o tema discutido",
    "metaphor": "Metáfora visual que reforça o ponto do locutor",
    "text_overlay": "Texto ou tipografia animada para enfatizar uma frase-chave",
}


# ──────────────────────────────────────────────────────────────
#  TRANSCRIPT ANALYSIS + SUGGESTION GENERATION
# ──────────────────────────────────────────────────────────────

def generate_broll_suggestions(
    transcript: str,
    clip_duration: float,
    api_key: str,
    num_suggestions: int = 4
) -> list[dict]:
    """
    Analyzes a clip's transcript and generates contextual B-Roll suggestions.
    
    Args:
        transcript: Full text transcript of the clip
        clip_duration: Duration of the clip in seconds
        api_key: Google Gemini API key
        num_suggestions: Number of B-Roll suggestions to generate
    
    Returns:
        List of dicts with keys:
        - timestamp_start: float (seconds)
        - timestamp_end: float (seconds)
        - category: str (from BROLL_CATEGORIES)
        - visual_description: str (detailed visual description for image generation)
        - reason: str (why this B-Roll enhances the clip)
        - text_context: str (the transcript text at this moment)
    """
    if genai is None:
        raise RuntimeError("google.generativeai is not installed.")
    
    if not api_key:
        raise ValueError("Gemini API key is required for B-Roll generation.")
    
    if not transcript or not transcript.strip():
        return []
    
    genai.configure(api_key=api_key)
    
    categories_spec = json.dumps(
        {k: v for k, v in BROLL_CATEGORIES.items()},
        ensure_ascii=False, indent=2
    )
    
    prompt = f"""Você é um diretor de vídeo profissional especializado em B-Rolls para Reels, TikTok e YouTube Shorts.

Analise a transcrição do clip abaixo e sugira {num_suggestions} inserções de B-Roll contextual que enriquecerão visualmente o vídeo.

TRANSCRIÇÃO DO CLIP:
\"\"\"{transcript}\"\"\"

DURAÇÃO DO CLIP: {clip_duration:.1f} segundos

CATEGORIAS DISPONÍVEIS:
{categories_spec}

REGRAS:
1. Distribua as sugestões ao longo da duração do clip (não concentre tudo no início).
2. Cada B-Roll deve durar entre 2 e 5 segundos.
3. A descrição visual deve ser detalhada o suficiente para gerar uma imagem com IA.
4. Escolha momentos onde o visual reforça o que está sendo dito.
5. Evite B-Rolls genéricos — seja criativo e contextual.
6. Os timestamps devem estar dentro da duração do clip (0 a {clip_duration:.1f}s).

Retorne SOMENTE um array JSON válido no formato:
[
  {{
    "timestamp_start": 3.0,
    "timestamp_end": 6.0,
    "category": "illustration",
    "visual_description": "Descrição visual detalhada da cena/imagem a ser gerada",
    "reason": "Por que este B-Roll melhora o vídeo neste momento",
    "text_context": "Trecho da transcrição que está sendo falado neste momento"
  }}
]

Importante: Responda apenas o array JSON. Não inclua explicação antes ou depois.
"""

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        response_text = response.text.strip()
        if response_text.startswith("```"):
            response_text = re.sub(r"^```(?:json)?\n", "", response_text)
            response_text = re.sub(r"\n```$", "", response_text)
            response_text = response_text.strip()
        
        suggestions = json.loads(response_text)
        
        # Validate and sanitize suggestions
        validated = []
        for s in suggestions:
            ts_start = float(s.get("timestamp_start", 0))
            ts_end = float(s.get("timestamp_end", ts_start + 3))
            
            # Clamp timestamps to clip duration
            ts_start = max(0, min(ts_start, clip_duration - 1))
            ts_end = max(ts_start + 1, min(ts_end, clip_duration))
            
            category = s.get("category", "scene")
            if category not in BROLL_CATEGORIES:
                category = "scene"
            
            validated.append({
                "timestamp_start": round(ts_start, 1),
                "timestamp_end": round(ts_end, 1),
                "category": category,
                "visual_description": str(s.get("visual_description", "Cena contextual genérica")),
                "reason": str(s.get("reason", "Enriquece visualmente o conteúdo")),
                "text_context": str(s.get("text_context", "")),
            })
        
        logger.info(f"Generated {len(validated)} B-Roll suggestions")
        return validated
        
    except Exception as e:
        logger.error(f"B-Roll generation failed: {e}")
        raise RuntimeError(f"Erro ao gerar sugestões de B-Roll: {e}")


# ──────────────────────────────────────────────────────────────
#  SIMPLE LOCAL ANALYSIS (FALLBACK WITHOUT GEMINI)
# ──────────────────────────────────────────────────────────────

def generate_simple_suggestions(transcript: str, clip_duration: float) -> list[dict]:
    """
    Generates basic B-Roll suggestions without AI, using keyword detection.
    Used as a fallback when Gemini API is not available.
    """
    if not transcript:
        return []
    
    # Simple keyword-based detection
    keyword_map = {
        "dinheiro": ("object", "Close-up de notas de dinheiro espalhadas sobre uma mesa escura"),
        "crescimento": ("data_viz", "Gráfico de linha ascendente com gradiente verde neon"),
        "tecnologia": ("scene", "Tela de computador com código fluindo em fundo escuro"),
        "negócio": ("environment", "Escritório moderno com janelas panorâmicas ao pôr do sol"),
        "saúde": ("object", "Frutas e alimentos saudáveis em composição artística"),
        "viagem": ("scene", "Vista aérea de uma paisagem tropical com mar cristalino"),
        "educação": ("illustration", "Livros empilhados com uma lâmpada brilhante ao lado"),
        "sucesso": ("metaphor", "Pessoa no topo de uma montanha com os braços abertos ao nascer do sol"),
        "problema": ("illustration", "Peças de quebra-cabeça espalhadas em uma superfície escura"),
        "solução": ("metaphor", "Chave dourada sendo inserida em uma fechadura brilhante"),
        "futuro": ("scene", "Cidade futurista com luzes neon e arranha-céus holográficos"),
        "família": ("scene", "Família reunida em uma sala aconchegante e iluminada"),
    }
    
    words = transcript.lower().split()
    suggestions = []
    segment_duration = clip_duration / max(len(keyword_map), 1)
    
    for i, (keyword, (category, description)) in enumerate(keyword_map.items()):
        if keyword in words and len(suggestions) < 4:
            ts_start = min(i * segment_duration, clip_duration - 4)
            ts_start = max(0, ts_start)
            suggestions.append({
                "timestamp_start": round(ts_start, 1),
                "timestamp_end": round(ts_start + 3, 1),
                "category": category,
                "visual_description": description,
                "reason": f"Reforça visualmente o conceito de '{keyword}' mencionado no vídeo",
                "text_context": keyword,
            })
    
    return suggestions
