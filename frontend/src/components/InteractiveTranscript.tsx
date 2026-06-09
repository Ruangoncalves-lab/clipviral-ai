'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

interface Word {
  word: string;
  start: number;
  end: number;
}

interface InteractiveTranscriptProps {
  storagePath: string;
  videoRef: React.RefObject<HTMLVideoElement | null>;
}

export default function InteractiveTranscript({ storagePath, videoRef }: InteractiveTranscriptProps) {
  const [words, setWords] = useState<Word[]>([]);
  const [fullText, setFullText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeIndex, setActiveIndex] = useState(-1);
  const [language, setLanguage] = useState('pt');
  const containerRef = useRef<HTMLDivElement>(null);
  const activeWordRef = useRef<HTMLSpanElement>(null);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';

  // Fetch transcript on mount or language change
  const fetchTranscript = useCallback(async () => {
    setLoading(true);
    setError('');
    setWords([]);

    try {
      const res = await fetch(`${backendUrl}/api/transcript/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          storage_path: storagePath,
          language,
        }),
      });

      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setWords(data.words || []);
      setFullText(data.full_text || '');
    } catch (err: any) {
      setError(err.message || 'Erro ao gerar transcrição.');
    } finally {
      setLoading(false);
    }
  }, [storagePath, language, backendUrl]);

  useEffect(() => {
    if (storagePath) {
      fetchTranscript();
    }
  }, [storagePath, fetchTranscript]);

  // Sync with video timeupdate
  useEffect(() => {
    const video = videoRef?.current;
    if (!video || words.length === 0) return;

    const handleTimeUpdate = () => {
      const currentTime = video.currentTime;
      const idx = words.findIndex(
        (w) => currentTime >= w.start && currentTime < w.end
      );
      if (idx !== activeIndex) {
        setActiveIndex(idx);
      }
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => video.removeEventListener('timeupdate', handleTimeUpdate);
  }, [videoRef, words, activeIndex]);

  // Auto-scroll to active word
  useEffect(() => {
    if (activeWordRef.current && containerRef.current) {
      const container = containerRef.current;
      const word = activeWordRef.current;
      const containerRect = container.getBoundingClientRect();
      const wordRect = word.getBoundingClientRect();

      if (wordRect.top < containerRect.top || wordRect.bottom > containerRect.bottom) {
        word.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [activeIndex]);

  // Click word -> seek video
  const handleWordClick = (word: Word) => {
    if (videoRef?.current) {
      videoRef.current.currentTime = word.start;
      videoRef.current.play();
    }
  };

  // Export transcript
  const exportTranscript = (format: 'txt' | 'srt') => {
    let content = '';
    const filename = `transcript.${format}`;

    if (format === 'txt') {
      content = fullText || words.map(w => w.word).join(' ');
    } else if (format === 'srt') {
      words.forEach((w, i) => {
        const startTime = formatSRTTime(w.start);
        const endTime = formatSRTTime(w.end);
        content += `${i + 1}\n${startTime} --> ${endTime}\n${w.word}\n\n`;
      });
    }

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatSRTTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.round((seconds % 1) * 1000);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
  };

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec < 10 ? '0' : ''}${sec}`;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800/60 bg-zinc-900/20">
        <div className="flex items-center gap-2">
          <span className="text-lg">📝</span>
          <h3 className="font-bold text-sm bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
            Transcrição Interativa
          </h3>
          <span className="ml-auto px-2 py-0.5 text-[10px] font-semibold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
            {words.length} palavras
          </span>
        </div>

        {/* Language Selector */}
        <div className="flex items-center gap-1.5 mt-2">
          {[
            { code: 'pt', flag: '🇧🇷', label: 'PT' },
            { code: 'en', flag: '🇺🇸', label: 'EN' },
            { code: 'es', flag: '🇪🇸', label: 'ES' },
          ].map(lang => (
            <button
              key={lang.code}
              type="button"
              onClick={() => setLanguage(lang.code)}
              className={`px-2.5 py-1 text-[10px] font-bold rounded-md transition-all ${
                language === lang.code
                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                  : 'bg-zinc-900 text-zinc-500 border border-zinc-800 hover:text-zinc-300'
              }`}
            >
              {lang.flag} {lang.label}
            </button>
          ))}
          <button
            type="button"
            onClick={fetchTranscript}
            disabled={loading}
            className="ml-auto px-2 py-1 text-[10px] font-bold rounded-md bg-zinc-900 text-zinc-500 border border-zinc-800 hover:text-amber-400 hover:border-amber-500/30 transition-colors disabled:opacity-40"
          >
            {loading ? '⏳' : '🔄'} Recarregar
          </button>
        </div>
      </div>

      {/* Words Area */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 min-h-0 custom-scrollbar"
      >
        {loading && (
          <div className="flex flex-col items-center justify-center h-full gap-3">
            <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-amber-400 font-semibold">Gerando transcrição word-level...</p>
            <p className="text-[10px] text-zinc-600">Isso pode levar alguns segundos</p>
          </div>
        )}

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
            {error}
          </div>
        )}

        {!loading && !error && words.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-center">
            <span className="text-3xl">🎙️</span>
            <p className="text-sm text-zinc-400">Nenhuma transcrição disponível</p>
            <p className="text-[10px] text-zinc-600">Clique em "Recarregar" para gerar</p>
          </div>
        )}

        {/* Interactive Words */}
        {words.length > 0 && (
          <div className="flex flex-wrap gap-[3px] leading-relaxed">
            {words.map((word, i) => (
              <span
                key={`${word.start}-${i}`}
                ref={i === activeIndex ? activeWordRef : null}
                onClick={() => handleWordClick(word)}
                title={`${formatTime(word.start)} → ${formatTime(word.end)}`}
                className={`inline-block px-1 py-0.5 rounded cursor-pointer transition-all duration-150 text-xs ${
                  i === activeIndex
                    ? 'bg-amber-500/25 text-amber-200 font-bold scale-110 shadow-sm shadow-amber-500/20'
                    : i < activeIndex
                      ? 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/60'
                      : 'text-zinc-300 hover:text-white hover:bg-zinc-800/60'
                }`}
              >
                {word.word}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Export Footer */}
      {words.length > 0 && (
        <div className="px-4 py-3 border-t border-zinc-800/60 bg-zinc-950/40">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">Exportar:</span>
            <button
              type="button"
              onClick={() => exportTranscript('txt')}
              className="px-3 py-1.5 text-[10px] font-bold rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-700 transition-colors"
            >
              📄 TXT
            </button>
            <button
              type="button"
              onClick={() => exportTranscript('srt')}
              className="px-3 py-1.5 text-[10px] font-bold rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-700 transition-colors"
            >
              🎬 SRT
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
