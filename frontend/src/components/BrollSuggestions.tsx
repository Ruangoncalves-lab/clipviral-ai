'use client';

import { useState } from 'react';

interface BrollSuggestion {
  timestamp_start: number;
  timestamp_end: number;
  category: string;
  visual_description: string;
  reason: string;
  text_context: string;
}

interface BrollSuggestionsProps {
  storagePath: string;
  clipDuration: number;
  videoRef: React.RefObject<HTMLVideoElement | null>;
}

const CATEGORY_MAP: Record<string, { label: string; icon: string; color: string; image: string }> = {
  illustration: {
    label: 'Ilustração',
    icon: '🎨',
    color: 'from-pink-500/20 to-rose-500/5 text-pink-400 border-pink-500/30',
    image: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=400&auto=format&fit=crop&q=80',
  },
  data_viz: {
    label: 'Visualização de Dados',
    icon: '📊',
    color: 'from-cyan-500/20 to-blue-500/5 text-cyan-400 border-cyan-500/30',
    image: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&auto=format&fit=crop&q=80',
  },
  scene: {
    label: 'Cena',
    icon: '🎬',
    color: 'from-violet-500/20 to-purple-500/5 text-violet-400 border-violet-500/30',
    image: 'https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=400&auto=format&fit=crop&q=80',
  },
  object: {
    label: 'Objeto/Produto',
    icon: '📦',
    color: 'from-amber-500/20 to-yellow-500/5 text-amber-400 border-amber-500/30',
    image: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&auto=format&fit=crop&q=80',
  },
  environment: {
    label: 'Ambiente',
    icon: '🏢',
    color: 'from-emerald-500/20 to-teal-500/5 text-emerald-400 border-emerald-500/30',
    image: 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=400&auto=format&fit=crop&q=80',
  },
  metaphor: {
    label: 'Metáfora Visual',
    icon: '💡',
    color: 'from-orange-500/20 to-amber-500/5 text-orange-400 border-orange-500/30',
    image: 'https://images.unsplash.com/photo-1519074002996-a69e7ac46a42?w=400&auto=format&fit=crop&q=80',
  },
  text_overlay: {
    label: 'Texto Animado',
    icon: '✍️',
    color: 'from-indigo-500/20 to-blue-500/5 text-indigo-400 border-indigo-500/30',
    image: 'https://images.unsplash.com/photo-1626785774573-4b799315345d?w=400&auto=format&fit=crop&q=80',
  },
};

export default function BrollSuggestions({ storagePath, clipDuration, videoRef }: BrollSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<BrollSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [imageGenerating, setImageGenerating] = useState<Record<number, boolean>>({});
  const [generatedImages, setGeneratedImages] = useState<Record<number, string>>({});

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';

  const handleGenerateBrolls = async () => {
    setLoading(true);
    setError('');
    setSuggestions([]);

    try {
      // 1. Fetch transcript first to get full text
      const transcriptRes = await fetch(`${backendUrl}/api/transcript/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          storage_path: storagePath,
          language: 'pt',
        }),
      });

      if (!transcriptRes.ok) {
        throw new Error('Falha ao obter transcrição do vídeo para o B-Roll.');
      }

      const transcriptData = await transcriptRes.json();
      const text = transcriptData.full_text || '';

      if (!text.trim()) {
        throw new Error('O vídeo possui uma transcrição vazia para gerar B-Rolls.');
      }

      // 2. Fetch B-roll suggestions
      const brollRes = await fetch(`${backendUrl}/api/broll/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: text,
          clip_duration: clipDuration,
          num_suggestions: 4,
        }),
      });

      if (!brollRes.ok) {
        throw new Error('Falha na geração de B-Rolls no backend.');
      }

      const brollData = await brollRes.json();
      setSuggestions(brollData.suggestions || []);
    } catch (err: any) {
      setError(err.message || 'Erro ao gerar sugestões de B-Roll.');
    } finally {
      setLoading(false);
    }
  };

  const handleSeek = (start: number) => {
    if (videoRef?.current) {
      videoRef.current.currentTime = start;
      videoRef.current.play();
    }
  };

  const handleGenerateImage = (index: number, category: string) => {
    setImageGenerating((prev) => ({ ...prev, [index]: true }));

    // Simulate diffusion model generation
    setTimeout(() => {
      const categoryConfig = CATEGORY_MAP[category] || CATEGORY_MAP.scene;
      setGeneratedImages((prev) => ({ ...prev, [index]: categoryConfig.image }));
      setImageGenerating((prev) => ({ ...prev, [index]: false }));
    }, 2500);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800/60 bg-zinc-900/20">
        <div className="flex items-center gap-2">
          <span className="text-lg">🎬</span>
          <h3 className="font-bold text-sm bg-gradient-to-r from-violet-400 to-indigo-500 bg-clip-text text-transparent">
            Diretor de B-Rolls IA
          </h3>
          <span className="ml-auto px-2 py-0.5 text-[10px] font-semibold rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
            Smart Visuals
          </span>
        </div>
        <p className="text-[10px] text-zinc-500 mt-0.5">Substitua trechos ou adicione ilustrações conceituais</p>
      </div>

      {/* Main Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 custom-scrollbar">
        {loading && (
          <div className="flex flex-col items-center justify-center h-full gap-3 py-10">
            <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-violet-400 font-semibold">Analisando transcrição e gerando B-Rolls...</p>
            <p className="text-[10px] text-zinc-600">Modelos locais/Gemini sendo executados</p>
          </div>
        )}

        {error && (
          <div className="p-3.5 rounded-lg border border-red-500/30 bg-red-500/10 text-xs text-red-400">
            ⚠️ {error}
          </div>
        )}

        {!loading && !error && suggestions.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12 space-y-4">
            <div className="w-16 h-16 rounded-full bg-violet-600/10 flex items-center justify-center border border-violet-500/20 text-violet-400 text-3xl animate-pulse">
              ✨
            </div>
            <div className="space-y-1">
              <h4 className="font-bold text-sm text-zinc-200">B-Rolls Inteligentes</h4>
              <p className="text-xs text-zinc-500 max-w-[260px] mx-auto leading-relaxed">
                Analise a fala deste corte para sugerir ilustrações conceituais perfeitas em momentos cruciais.
              </p>
            </div>
            <button
              onClick={handleGenerateBrolls}
              className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-bold text-xs hover:from-violet-500 hover:to-indigo-500 transition-all shadow-md shadow-violet-500/20"
            >
              Gerar Sugestões de B-Roll
            </button>
          </div>
        )}

        {/* Suggestions List */}
        {!loading && suggestions.length > 0 && (
          <div className="space-y-3">
            {suggestions.map((s, idx) => {
              const cat = CATEGORY_MAP[s.category] || CATEGORY_MAP.scene;
              const isGenerating = imageGenerating[idx];
              const hasImage = generatedImages[idx];

              return (
                <div
                  key={idx}
                  className="rounded-xl border border-zinc-800 bg-zinc-900/10 glass-panel overflow-hidden transition-all hover:border-zinc-700/50"
                >
                  <div className="p-3.5 space-y-2">
                    {/* Top Row: category and timer */}
                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-0.5 rounded-md text-[9px] font-bold border bg-gradient-to-r ${cat.color}`}>
                        {cat.icon} {cat.label}
                      </span>
                      <button
                        onClick={() => handleSeek(s.timestamp_start)}
                        className="px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] font-semibold text-zinc-400 hover:text-violet-400 transition-colors flex items-center gap-1"
                      >
                        ⏱️ {formatTime(s.timestamp_start)} - {formatTime(s.timestamp_end)}
                      </button>
                    </div>

                    {/* Text context & Description */}
                    <div className="space-y-1.5">
                      <p className="text-zinc-500 text-[10px] italic leading-tight">
                        &ldquo;{s.text_context}&rdquo;
                      </p>
                      <h5 className="text-xs font-semibold text-zinc-200 leading-snug">
                        {s.visual_description}
                      </h5>
                      <p className="text-[10px] text-zinc-400 leading-relaxed">
                        {s.reason}
                      </p>
                    </div>

                    {/* Interactive Image Panel */}
                    <div className="pt-2">
                      {isGenerating ? (
                        <div className="h-28 rounded-lg bg-zinc-950 border border-zinc-800 flex flex-col items-center justify-center gap-2 overflow-hidden relative">
                          <div className="absolute inset-0 bg-violet-600/5 animate-pulse" />
                          <div className="w-5 h-5 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
                          <span className="text-[9px] font-bold text-violet-400 uppercase tracking-widest animate-pulse">
                            Difundindo Imagem...
                          </span>
                        </div>
                      ) : hasImage ? (
                        <div className="relative h-28 rounded-lg overflow-hidden border border-zinc-800 bg-black group">
                          <img
                            src={hasImage}
                            alt={s.visual_description}
                            className="w-full h-full object-cover opacity-80 transition-transform duration-300 group-hover:scale-105"
                          />
                          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-transparent" />
                          <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between">
                            <span className="text-[9px] text-zinc-400 truncate max-w-[70%]">
                              {s.visual_description}
                            </span>
                            <button
                              onClick={() => handleGenerateImage(idx, s.category)}
                              className="px-2 py-0.5 rounded bg-black/60 hover:bg-black/95 text-[9px] font-bold border border-zinc-800 text-zinc-300 hover:text-white"
                            >
                              Regerar
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleGenerateImage(idx, s.category)}
                          className="w-full py-2 rounded-lg bg-zinc-950 hover:bg-zinc-900 border border-zinc-800 hover:border-violet-500/30 text-[10px] font-bold text-zinc-400 hover:text-violet-300 transition-all flex items-center justify-center gap-1.5"
                        >
                          🎨 Gerar Imagem com IA
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
