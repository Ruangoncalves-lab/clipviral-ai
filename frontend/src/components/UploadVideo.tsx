'use client';

import { useState } from 'react';
import { supabase } from '../lib/supabaseClient';

interface UploadVideoProps {
  onUploadSuccess: (videoId: string) => void;
}

export default function UploadVideo({ onUploadSuccess }: UploadVideoProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

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

  return (
    <div className="w-full max-w-xl mx-auto p-6 rounded-xl border border-zinc-800 bg-zinc-900/50 backdrop-blur-md text-zinc-100 shadow-xl">
      <h3 className="text-xl font-bold mb-4 bg-gradient-to-r from-violet-400 to-fuchsia-500 bg-clip-text text-transparent">
        Fazer Upload de Vídeo
      </h3>

      {errorMsg && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
          {errorMsg}
        </div>
      )}

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
              aria-hidden="true"
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
    </div>
  );
}
