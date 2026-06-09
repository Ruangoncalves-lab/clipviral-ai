'use client';

import { useState } from 'react';
import { supabase } from '../lib/supabaseClient';

interface UploadVideoProps {
  onUploadSuccess: (videoId: string) => void;
}

const LAYOUT_OPTIONS = [
  {
    value: 'fit',
    label: 'Fit com Blur',
    description: 'Vídeo centralizado com fundo desfocado',
    icon: '🖼️',
  },
  {
    value: 'auto',
    label: 'Auto Reframe (IA)',
    description: 'Enquadramento automático no rosto do falante',
    icon: '🤖',
  },
  {
    value: 'split',
    label: 'Split-Screen Podcast',
    description: 'Dois falantes empilhados verticalmente',
    icon: '🎙️',
  },
];

export default function UploadVideo({ onUploadSuccess }: UploadVideoProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [layoutMode, setLayoutMode] = useState('fit');
  const [audioLanguage, setAudioLanguage] = useState('pt');

  // YouTube URL states
  const [inputMode, setInputMode] = useState<'file' | 'youtube'>('file');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [ytInfo, setYtInfo] = useState<{ title: string; duration: number; channel: string; thumbnail: string } | null>(null);
  const [ytLoading, setYtLoading] = useState(false);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErrorMsg('');
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setProgress(0);
    setErrorMsg('');
    setStatusText('Autenticando...');

    try {
      // 1. Get current session
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();
      if (sessionError || !session) {
        throw new Error('Você precisa estar logado para fazer upload de vídeos.');
      }

      const user_id = session.user.id;
      // Generate a client-side random UUID for the video
      const video_id = crypto.randomUUID();

      setStatusText('Solicitando link de upload seguro...');
      
      // 2. Fetch presigned URL from backend
      const presignedRes = await fetch(`${backendUrl}/api/storage/presigned-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id,
          video_id,
          filename: file.name,
          content_type: file.type || 'video/mp4',
        }),
      });

      if (!presignedRes.ok) {
        const errText = await presignedRes.text();
        throw new Error(`Erro ao obter URL presignada: ${errText}`);
      }

      const { upload_url, storage_path } = await presignedRes.json();

      setStatusText('Enviando vídeo diretamente para o armazenamento...');

      // 3. Upload file directly to R2 using XMLHttpRequest to track progress
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', upload_url);
        xhr.setRequestHeader('Content-Type', file.type || 'video/mp4');

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentage = Math.round((event.loaded / event.total) * 100);
            setProgress(percentage);
          }
        };

        xhr.onload = () => {
          if (xhr.status === 200 || xhr.status === 201) {
            resolve();
          } else {
            reject(new Error(`Falha no upload para o R2. Status: ${xhr.status}`));
          }
        };

        xhr.onerror = () => reject(new Error('Erro de conexão durante o upload.'));
        xhr.send(file);
      });

      setStatusText('Salvando registro no banco de dados...');

      // 4. Create record in public.videos table
      const { error: insertError } = await supabase.from('videos').insert({
        id: video_id,
        user_id,
        name: file.name,
        storage_path,
        duration: 0.0, // Calculated by backend later
        status: 'pending',
      });

      if (insertError) {
        throw insertError;
      }

      setStatusText('Disparando processamento de cortes...');

      // 5. Trigger async processing job on FastAPI backend
      const processRes = await fetch(`${backendUrl}/api/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id,
          user_id,
          storage_path,
          use_gemini: true,
          model_size: 'base',
          num_clips: 5,
          min_duration: 25.0,
          max_duration: 120.0,
          generate_subs: true,
          convert_vertical: true,
          add_title: true,
          layout_mode: layoutMode,
          supabase_url: process.env.NEXT_PUBLIC_SUPABASE_URL || '',
          supabase_key: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
        }),
      });

      if (!processRes.ok) {
        const errText = await processRes.text();
        throw new Error(`Falha ao iniciar processador de vídeo: ${errText}`);
      }

      setStatusText('Upload e disparo concluídos!');
      onUploadSuccess(video_id);
    } catch (err: any) {
      setErrorMsg(err.message || 'Erro inesperado durante o upload.');
      setStatusText('');
    } finally {
      setUploading(false);
    }
  };

  // YouTube URL metadata fetch
  const handleYoutubeUrlChange = async (url: string) => {
    setYoutubeUrl(url);
    setYtInfo(null);
    setErrorMsg('');

    // Only fetch info if URL looks like YouTube
    const ytRegex = /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
    if (!ytRegex.test(url.trim())) return;

    setYtLoading(true);
    try {
      const res = await fetch(`${backendUrl}/api/youtube/info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'URL inválida' }));
        throw new Error(err.detail || 'Erro ao buscar info');
      }
      const data = await res.json();
      setYtInfo({ title: data.title, duration: data.duration, channel: data.channel, thumbnail: data.thumbnail });
    } catch (err: any) {
      setErrorMsg(err.message || 'Erro ao verificar URL do YouTube.');
    } finally {
      setYtLoading(false);
    }
  };

  const handleYoutubeImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!youtubeUrl.trim()) return;

    setUploading(true);
    setProgress(0);
    setErrorMsg('');
    setStatusText('Autenticando...');

    try {
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();
      if (sessionError || !session) throw new Error('Você precisa estar logado.');

      setStatusText('Iniciando importação do YouTube...');
      setProgress(30);

      const res = await fetch(`${backendUrl}/api/youtube/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          youtube_url: youtubeUrl.trim(),
          user_id: session.user.id,
          use_gemini: true,
          model_size: 'base',
          num_clips: 5,
          min_duration: 25.0,
          max_duration: 120.0,
          generate_subs: true,
          convert_vertical: true,
          add_title: true,
          layout_mode: layoutMode,
          supabase_url: process.env.NEXT_PUBLIC_SUPABASE_URL || '',
          supabase_key: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText);
      }

      setProgress(100);
      setStatusText('Importação iniciada! O vídeo aparecerá em Meus Vídeos.');
      onUploadSuccess('');
    } catch (err: any) {
      setErrorMsg(err.message || 'Erro ao importar do YouTube.');
      setStatusText('');
    } finally {
      setUploading(false);
    }
  };

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="w-full max-w-xl mx-auto p-6 rounded-xl border border-zinc-800 bg-zinc-900/50 backdrop-blur-md text-zinc-100 shadow-xl">
      <h3 className="text-xl font-bold mb-4 bg-gradient-to-r from-violet-400 to-fuchsia-500 bg-clip-text text-transparent">
        Fazer Upload de Vídeo
      </h3>

      {/* Input Mode Toggle */}
      <div className="flex mb-5 rounded-lg bg-zinc-950 border border-zinc-800 p-1">
        <button
          type="button"
          onClick={() => { setInputMode('file'); setErrorMsg(''); }}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-md text-sm font-semibold transition-all ${
            inputMode === 'file'
              ? 'bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white shadow-md shadow-violet-500/20'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          Arquivo
        </button>
        <button
          type="button"
          onClick={() => { setInputMode('youtube'); setErrorMsg(''); }}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-md text-sm font-semibold transition-all ${
            inputMode === 'youtube'
              ? 'bg-gradient-to-r from-red-600 to-red-500 text-white shadow-md shadow-red-500/20'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
          </svg>
          YouTube URL
        </button>
      </div>

      {errorMsg && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
          {errorMsg}
        </div>
      )}

      {/* FILE UPLOAD MODE */}
      {inputMode === 'file' && (
        <form onSubmit={handleUpload} className="space-y-6">
          <div className="flex flex-col items-center justify-center border-2 border-dashed border-zinc-800 rounded-lg p-6 bg-zinc-950/50 hover:bg-zinc-950 hover:border-violet-500/50 transition-colors cursor-pointer relative group">
            <input
              type="file"
              accept="video/*"
              onChange={handleFileChange}
              disabled={uploading}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="text-center space-y-2 pointer-events-none">
              <svg
                className="mx-auto h-12 w-12 text-zinc-500 group-hover:text-violet-400 transition-colors"
                stroke="currentColor"
                fill="none"
                viewBox="0 0 48 48"
              >
                <path
                  d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <p className="text-sm font-medium text-zinc-300">
                {file ? file.name : 'Selecione ou arraste um arquivo de vídeo'}
              </p>
              <p className="text-xs text-zinc-500">MP4, MOV, MKV de até 1 hora</p>
            </div>
          </div>

          {file && !uploading && (
            <div className="flex items-center justify-between text-sm bg-zinc-950 p-3 rounded-lg border border-zinc-800">
              <span className="truncate max-w-[70%] font-medium">{file.name}</span>
              <span className="text-zinc-400">{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
            </div>
          )}

          {/* Audio Language */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-zinc-300">🌐 Idioma do Áudio</label>
            <div className="flex gap-2">
              {[{ code: 'pt', flag: '🇧🇷', label: 'Português' }, { code: 'en', flag: '🇺🇸', label: 'English' }, { code: 'es', flag: '🇪🇸', label: 'Español' }].map(lang => (
                <button key={lang.code} type="button" onClick={() => setAudioLanguage(lang.code)} disabled={uploading}
                  className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border text-sm font-semibold transition-all ${audioLanguage === lang.code ? 'border-violet-500 bg-violet-500/10 text-violet-300' : 'border-zinc-800 bg-zinc-950/50 text-zinc-400 hover:border-zinc-700'} disabled:opacity-50`}
                >
                  <span>{lang.flag}</span><span className="text-xs">{lang.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* AI Layout Mode Selection */}
          <div className="space-y-3">
            <label className="block text-sm font-semibold text-zinc-300">
              🎬 Modo de Enquadramento
            </label>
            <div className="grid gap-2">
              {LAYOUT_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setLayoutMode(option.value)}
                  disabled={uploading}
                  className={`flex items-start gap-3 w-full text-left px-4 py-3 rounded-lg border transition-all duration-200 ${
                    layoutMode === option.value
                      ? 'border-violet-500 bg-violet-500/10 shadow-lg shadow-violet-500/10'
                      : 'border-zinc-800 bg-zinc-950/50 hover:border-zinc-700 hover:bg-zinc-950'
                  } disabled:opacity-50`}
                >
                  <span className="text-xl mt-0.5">{option.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-semibold ${
                        layoutMode === option.value ? 'text-violet-300' : 'text-zinc-200'
                      }`}>
                        {option.label}
                      </span>
                      {layoutMode === option.value && (
                        <span className="flex h-2 w-2 rounded-full bg-violet-400 animate-pulse" />
                      )}
                    </div>
                    <p className="text-xs text-zinc-500 mt-0.5">{option.description}</p>
                  </div>
                  <div className={`mt-1 h-4 w-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                    layoutMode === option.value
                      ? 'border-violet-400 bg-violet-500'
                      : 'border-zinc-600'
                  }`}>
                    {layoutMode === option.value && (
                      <div className="h-1.5 w-1.5 rounded-full bg-white" />
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {uploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-violet-400 font-semibold">{statusText}</span>
                <span className="font-semibold">{progress}%</span>
              </div>
              <div className="w-full bg-zinc-800 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-violet-500 to-fuchsia-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={!file || uploading}
            className="w-full py-3 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 font-semibold hover:from-violet-500 hover:to-fuchsia-500 disabled:opacity-50 transition-all shadow-lg shadow-violet-500/20"
          >
            {uploading ? 'Processando...' : 'Iniciar Processamento'}
          </button>
        </form>
      )}

      {/* YOUTUBE URL MODE */}
      {inputMode === 'youtube' && (
        <form onSubmit={handleYoutubeImport} className="space-y-6">
          {/* URL Input */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-zinc-300">
              🔗 Cole a URL do YouTube
            </label>
            <div className="relative">
              <input
                type="url"
                value={youtubeUrl}
                onChange={(e) => handleYoutubeUrlChange(e.target.value)}
                disabled={uploading}
                placeholder="https://youtube.com/watch?v=..."
                className="w-full px-4 py-3 rounded-lg bg-zinc-950 border border-zinc-800 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-red-500/50 focus:outline-none focus:ring-1 focus:ring-red-500/30 disabled:opacity-50 transition-colors pr-10"
              />
              {ytLoading && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <div className="w-4 h-4 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
                </div>
              )}
            </div>
            <p className="text-[10px] text-zinc-500">Suporta: youtube.com, youtu.be, shorts</p>
          </div>

          {/* YouTube Video Preview Card */}
          {ytInfo && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 overflow-hidden">
              {ytInfo.thumbnail && (
                <div className="relative h-36 bg-black">
                  <img 
                    src={ytInfo.thumbnail} 
                    alt={ytInfo.title}
                    className="w-full h-full object-cover opacity-80"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-transparent to-transparent" />
                  <div className="absolute bottom-2 right-2 px-2 py-1 rounded bg-black/70 text-[10px] font-bold text-white">
                    {formatDuration(ytInfo.duration)}
                  </div>
                </div>
              )}
              <div className="p-3.5 space-y-1">
                <h4 className="text-sm font-bold text-zinc-100 leading-snug line-clamp-2">{ytInfo.title}</h4>
                <p className="text-[11px] text-zinc-500">{ytInfo.channel} • {formatDuration(ytInfo.duration)}</p>
                <div className="flex items-center gap-1.5 pt-1">
                  <span className="px-2 py-0.5 text-[9px] font-bold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    ✓ Pronto para importar
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* AI Layout Mode Selection */}
          <div className="space-y-3">
            <label className="block text-sm font-semibold text-zinc-300">
              🎬 Modo de Enquadramento
            </label>
            <div className="grid gap-2">
              {LAYOUT_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setLayoutMode(option.value)}
                  disabled={uploading}
                  className={`flex items-start gap-3 w-full text-left px-4 py-3 rounded-lg border transition-all duration-200 ${
                    layoutMode === option.value
                      ? 'border-violet-500 bg-violet-500/10 shadow-lg shadow-violet-500/10'
                      : 'border-zinc-800 bg-zinc-950/50 hover:border-zinc-700 hover:bg-zinc-950'
                  } disabled:opacity-50`}
                >
                  <span className="text-xl mt-0.5">{option.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-semibold ${
                        layoutMode === option.value ? 'text-violet-300' : 'text-zinc-200'
                      }`}>
                        {option.label}
                      </span>
                      {layoutMode === option.value && (
                        <span className="flex h-2 w-2 rounded-full bg-violet-400 animate-pulse" />
                      )}
                    </div>
                    <p className="text-xs text-zinc-500 mt-0.5">{option.description}</p>
                  </div>
                  <div className={`mt-1 h-4 w-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                    layoutMode === option.value
                      ? 'border-violet-400 bg-violet-500'
                      : 'border-zinc-600'
                  }`}>
                    {layoutMode === option.value && (
                      <div className="h-1.5 w-1.5 rounded-full bg-white" />
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {uploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-red-400 font-semibold">{statusText}</span>
                <span className="font-semibold">{progress}%</span>
              </div>
              <div className="w-full bg-zinc-800 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-red-500 to-red-400 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={!youtubeUrl.trim() || uploading}
            className="w-full py-3 rounded-lg bg-gradient-to-r from-red-600 to-red-500 font-semibold hover:from-red-500 hover:to-red-400 disabled:opacity-50 transition-all shadow-lg shadow-red-500/20 flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
            </svg>
            {uploading ? 'Importando do YouTube...' : 'Importar e Processar'}
          </button>
        </form>
      )}
    </div>
  );
}
