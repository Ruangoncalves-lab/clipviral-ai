import re
from src.utils import format_duration

# Keywords for viral hooks and positive scoring
VIRAL_KEYWORDS = [
    "você sabia", "presta atenção", "olha isso", "ninguém te conta", "o maior erro",
    "o segredo", "a verdade é", "o problema é", "não faça isso", "você está errando",
    "como fazer", "passo a passo", "cuidado", "isso muda tudo", "o que ninguém percebe",
    "a maioria das pessoas", "resultado", "dinheiro", "venda", "lucro", "prejuízo",
    "oportunidade", "simples", "rápido", "urgente", "importante", "viral", "algoritmo",
    "atenção", "retenção", "estratégia", "método", "fórmula"
]

# Filler words to penalize
FILLER_WORDS = ["ééé", "tipo", "né", "hã", "hum", "ah", "eh"]

# Catchy title templates
TITLE_TEMPLATES = [
    "O ERRO QUE TRAVA SEUS RESULTADOS",
    "NINGUÉM TE CONTA ISSO",
    "COMO FAZER DO JEITO CERTO",
    "VOCÊ ESTÁ PERDENDO DINHEIRO",
    "A VERDADE SOBRE ISSO",
    "PARE DE FAZER ISSO",
    "ESSA DICA MUDA TUDO",
    "O SEGREDO DA RETENÇÃO",
    "ISSO MUDA TUDO"
]

def analyze_candidates_locally(candidates):
    """
    Evaluate and score candidate clips locally using rule-based metrics.
    
    Parameters:
      candidates (list): A list of candidate dicts, each with 'id', 'start', 'end', 'duration', 'text'.
      
    Returns:
      list: Evaluated candidates with scores, titles, hooks, reasons, and content types.
    """
    evaluated_list = []
    
    for cand in candidates:
        text_lower = cand["text"].lower()
        score = 50 # Start with baseline score
        
        # 1. Check for viral keywords
        matched_keywords = []
        for kw in VIRAL_KEYWORDS:
            if kw in text_lower:
                score += 8
                matched_keywords.append(kw)
                
        # 2. Check for sentence structure (questions and emotion)
        if "?" in cand["text"]:
            score += 12
        if "!" in cand["text"]:
            score += 6
            
        # 3. Penalize filler words
        filler_count = 0
        for filler in FILLER_WORDS:
            # Match whole words to avoid sub-word matching
            pattern = r'\b' + re.escape(filler) + r'\b'
            matches = re.findall(pattern, text_lower)
            filler_count += len(matches)
            
        score -= min(15, filler_count * 3) # Max 15 points penalty
        
        # 4. Score based on ideal duration (ideal vertical videos are 30-60s)
        duration = cand["duration"]
        if 30 <= duration <= 60:
            score += 15
        elif 25 <= duration < 30:
            score += 5
        elif 60 < duration <= 90:
            score += 5
        elif duration > 90:
            score -= 5 # Slightly penalize very long cuts as they have lower completion rates
            
        # Clamp score to [10, 95] to keep it realistic
        final_score = max(10, min(95, score))
        
        # 5. Generate a high-impact title
        title = generate_viral_title(cand["text"], matched_keywords)
        
        # 6. Extract hook (first sentence or first 6-8 words)
        hook = extract_hook(cand["text"])
        
        # 7. Infer content type
        content_type = infer_content_type(text_lower, matched_keywords)
        
        # 8. Create reason
        duration_formatted = format_duration(duration)
        if matched_keywords:
            reason = f"Corte de {duration_formatted} com excelente gancho e gatilhos de atenção: '{', '.join(matched_keywords[:3])}'."
        else:
            reason = f"Corte estruturado de {duration_formatted} com bom fluxo de fala e fechamento claro."
            
        evaluated_list.append({
            "id": cand["id"],
            "start": cand["start"],
            "end": cand["end"],
            "duration": round(duration, 2),
            "score": int(final_score),
            "title": title,
            "hook": hook,
            "reason": reason,
            "content_type": content_type
        })
        
    return evaluated_list

def generate_viral_title(text, keywords):
    """Generate a capitalized title of maximum 8 words."""
    # If we have keywords, try to pick an matching template
    if keywords:
        kw = keywords[0]
        if kw in ["dinheiro", "venda", "lucro", "prejuízo"]:
            return "VOCÊ ESTÁ PERDENDO DINHEIRO"
        if kw in ["erro", "você está errando"]:
            return "O ERRO QUE TRAVA SEUS RESULTADOS"
        if kw in ["segredo", "ninguém te conta"]:
            return "NINGUÉM TE CONTA ISSO"
        if kw in ["como fazer", "passo a passo"]:
            return "COMO FAZER DO JEITO CERTO"
            
    # Otherwise, grab first sentence or first 5-6 words and capitalize
    cleaned = re.sub(r'[^\w\s]', '', text).strip()
    words = cleaned.split()
    if words:
        title_words = words[:min(6, len(words))]
        title = " ".join(title_words).upper()
        if len(words) > 6:
            title += "..."
        return title
        
    return "ESSA DICA MUDA TUDO"

def extract_hook(text):
    """Extract hook (first sentence or first few words)."""
    sentences = re.split(r'[.!?]+', text)
    if sentences and sentences[0].strip():
        first_sent = sentences[0].strip()
        words = first_sent.split()
        if len(words) > 10:
            return " ".join(words[:10]) + "..."
        return first_sent
        
    words = text.split()
    if words:
        return " ".join(words[:8]) + "..."
    return "Atenção a este trecho!"

def infer_content_type(text_lower, keywords):
    """Infers content type based on vocabulary."""
    combined_words = " ".join(keywords) + " " + text_lower
    
    if any(w in combined_words for w in ["como fazer", "passo a passo", "tutorial", "método", "fórmula"]):
        return "tutorial"
    if any(w in combined_words for w in ["dinheiro", "venda", "lucro", "prejuízo", "comprar", "negócio"]):
        return "venda"
    if any(w in combined_words for w in ["você sabia", "segredo", "curiosidade", "descobri", "sabia"]):
        return "curiosidade"
    if any(w in combined_words for w in ["problema", "erro", "errando", "polêmica", "mentira"]):
        return "polêmico"
    if any(w in combined_words for w in ["sinto", "história", "vida", "emocional", "sonho", "triste"]):
        return "storytelling"
        
    return "educacional"
