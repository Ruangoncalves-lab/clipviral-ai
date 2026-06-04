import os
import json
import re
import google.generativeai as genai

def analyze_candidates_with_gemini(candidates, api_key):
    """
    Sends candidate segments to Google Gemini API for scoring and formatting.
    
    Parameters:
      candidates (list): Candidates list containing 'id', 'text', 'start', 'end', 'duration'.
      api_key (str): Google Gemini API Key.
      
    Returns:
      list: List of evaluated candidates matching the selector requirements, or None if failed.
    """
    if not api_key:
        print("Gemini API Key is empty. Skipping Gemini analysis.")
        return None
        
    try:
        # Configure Gemini API
        genai.configure(api_key=api_key)
        
        # Prepare the list for prompt to keep tokens low
        prompt_candidates = []
        for c in candidates:
            prompt_candidates.append({
                "id": c["id"],
                "duration_seconds": round(c["duration"], 1),
                "text": c["text"]
            })
            
        prompt = (
            "Você é um especialista em cortes virais para Reels, TikTok e Shorts.\n"
            "Avalie os trechos de vídeo (candidatos) abaixo e dê uma nota de 0 a 100 com base no seu potencial de viralização.\n\n"
            "Critérios de avaliação:\n"
            "- Gancho inicial forte nos primeiros 3 segundos.\n"
            "- Curiosidade, clareza, emoção ou utilidade prática.\n"
            "- Se o trecho funciona sozinho (tem começo, meio e fim coerentes).\n"
            "- Presença de frases marcantes ou quebras de expectativa.\n\n"
            "Responda EXCLUSIVAMENTE em formato JSON. O retorno deve ser um array contendo objetos no seguinte formato:\n"
            "[\n"
            "  {\n"
            "    \"candidate_id\": \"id_do_candidato\",\n"
            "    \"score\": 85,\n"
            "    \"title\": \"TÍTULO DO VÍDEO EM CAIXA ALTA (MÁXIMO 8 PALAVRAS)\",\n"
            "    \"hook\": \"Frase curta de gancho ou impacto inicial\",\n"
            "    \"reason\": \"Resumo do porquê esse corte é ideal e como prende a atenção\",\n"
            "    \"content_type\": \"educacional, polêmico, emocional, venda, storytelling, tutorial ou curiosidade\"\n"
            "  }\n"
            "]\n\n"
            "Importante: Responda apenas o array JSON válido. Não inclua nenhuma explicação antes ou depois do JSON.\n\n"
            "Candidatos a avaliar:\n"
        )
        
        full_prompt = prompt + json.dumps(prompt_candidates, ensure_ascii=False, indent=2)
        
        print("Sending request to Gemini API (gemini-1.5-flash)...")
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        response = model.generate_content(
            full_prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Clean up any potential markdown formatting in response text
        response_text = response.text.strip()
        if response_text.startswith("```"):
            response_text = re.sub(r"^```(?:json)?\n", "", response_text)
            response_text = re.sub(r"\n```$", "", response_text)
            response_text = response_text.strip()
            
        data = json.loads(response_text)
        
        # Build map of candidate id -> analysis
        analysis_map = {}
        for item in data:
            c_id = item.get("candidate_id")
            if c_id:
                analysis_map[c_id] = item
                
        # Merge back with original candidates
        evaluated_candidates = []
        for cand in candidates:
            c_id = cand["id"]
            if c_id in analysis_map:
                analysis = analysis_map[c_id]
                score = int(analysis.get("score", 50))
                title = str(analysis.get("title", "ESSA DICA MUDA TUDO")).upper()
                # Enforce maximum 8 words for titles
                title_words = title.split()
                if len(title_words) > 8:
                    title = " ".join(title_words[:8])
                    
                evaluated_candidates.append({
                    "id": cand["id"],
                    "start": cand["start"],
                    "end": cand["end"],
                    "duration": round(cand["duration"], 2),
                    "score": score,
                    "title": title,
                    "hook": analysis.get("hook", "Gancho inicial de impacto."),
                    "reason": analysis.get("reason", "Boa estrutura com início direto."),
                    "content_type": analysis.get("content_type", "educacional")
                })
            else:
                # If Gemini missed a candidate, keep it with default scoring
                evaluated_candidates.append({
                    "id": cand["id"],
                    "start": cand["start"],
                    "end": cand["end"],
                    "duration": round(cand["duration"], 2),
                    "score": 30, # Default low score since it wasn't picked
                    "title": "CORTAR VÍDEO",
                    "hook": "Corte gerado automaticamente.",
                    "reason": "Sem análise detalhada.",
                    "content_type": "educacional"
                })
                
        return evaluated_candidates
        
    except Exception as e:
        print(f"Gemini API analysis failed: {e}. Fallback to rule analyzer will be used.")
        return None
