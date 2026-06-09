'use client';

import { useState, useRef, useEffect } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  operation?: string;
  timestamp: Date;
}

interface CopilotChatProps {
  clipId: string;
  userId: string;
  storagePath: string;
  clipDuration: number;
  onVideoUpdate: (newUrl: string) => void;
}

const QUICK_SUGGESTIONS = [
  { label: '🔍 Zoom no início', command: 'Dê zoom de 20% nos primeiros 5 segundos' },
  { label: '⚡ Acelerar 1.5x', command: 'Acelere o vídeo em 1.5x' },
  { label: '🎬 Preto e branco', command: 'Coloque em preto e branco' },
  { label: '✂️ Cortar 3s início', command: 'Corte os primeiros 3 segundos' },
  { label: '🌅 Fade no início', command: 'Adicione um fade suave no início de 1 segundo' },
  { label: '🔄 Espelhar vídeo', command: 'Espelhe o vídeo horizontalmente' },
  { label: '☀️ Mais brilho', command: 'Aumente o brilho do vídeo' },
  { label: '🎨 Cores vibrantes', command: 'Deixe as cores mais vibrantes e saturadas' },
];

export default function CopilotChat({ clipId, userId, storagePath, clipDuration, onVideoUpdate }: CopilotChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'system',
      content: 'Olá! Sou o Copilot Editor do ClipViral AI. Diga-me o que deseja editar neste clip — zoom, corte, velocidade, cores, efeitos e mais. Use linguagem natural!',
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendCommand = async (command: string) => {
    if (!command.trim() || isProcessing) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: command.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsProcessing(true);

    try {
      const res = await fetch(`${backendUrl}/api/copilot/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clip_id: clipId,
          user_id: userId,
          storage_path: storagePath,
          command: command.trim(),
          clip_duration: clipDuration,
          supabase_url: process.env.NEXT_PUBLIC_SUPABASE_URL || '',
          supabase_key: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText);
      }

      const data = await res.json();

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.status === 'success'
          ? `✅ ${data.description}`
          : data.status === 'unsupported'
            ? `⚠️ ${data.description || 'Essa edição não é suportada ainda.'}`
            : `❌ Erro: ${data.description}`,
        operation: data.operation,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMsg]);

      // Update video player if edit was successful
      if (data.status === 'success' && data.edited_url) {
        onVideoUpdate(data.edited_url);
      }

    } catch (err: any) {
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `❌ Erro ao processar: ${err.message || 'Falha na comunicação com o servidor.'}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsProcessing(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendCommand(input);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800/60 bg-zinc-900/20">
        <div className="flex items-center gap-2">
          <span className="text-lg">✨</span>
          <h3 className="font-bold text-sm bg-gradient-to-r from-violet-400 to-fuchsia-500 bg-clip-text text-transparent">
            Copilot Editor
          </h3>
          <span className="ml-auto px-2 py-0.5 text-[10px] font-semibold rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
            IA
          </span>
        </div>
        <p className="text-[10px] text-zinc-500 mt-0.5">Edite seu vídeo com comandos naturais</p>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar min-h-0">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] px-3.5 py-2.5 rounded-xl text-xs leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-violet-600/20 border border-violet-500/30 text-violet-100 rounded-br-sm'
                  : msg.role === 'system'
                    ? 'bg-zinc-800/40 border border-zinc-700/30 text-zinc-300 rounded-bl-sm'
                    : 'bg-zinc-900/60 border border-zinc-800/50 text-zinc-200 rounded-bl-sm'
              }`}
            >
              {msg.role === 'assistant' && msg.operation && msg.operation !== 'unsupported' && (
                <span className="inline-block px-1.5 py-0.5 text-[9px] font-bold rounded bg-violet-500/15 text-violet-400 border border-violet-500/20 mb-1.5 uppercase tracking-wider">
                  {msg.operation}
                </span>
              )}
              <p className="whitespace-pre-wrap">{msg.content}</p>
              <span className="block text-[9px] text-zinc-600 mt-1.5 text-right">
                {msg.timestamp.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isProcessing && (
          <div className="flex justify-start">
            <div className="bg-zinc-900/60 border border-zinc-800/50 px-4 py-3 rounded-xl rounded-bl-sm">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-[10px] text-violet-400 font-medium">IA processando edição...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Suggestions */}
      {!isProcessing && messages.length <= 2 && (
        <div className="px-4 pb-2">
          <p className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mb-2">Sugestões rápidas</p>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_SUGGESTIONS.map((suggestion, i) => (
              <button
                key={i}
                type="button"
                onClick={() => sendCommand(suggestion.command)}
                className="px-2.5 py-1.5 text-[10px] font-medium rounded-lg bg-zinc-900/60 border border-zinc-800 text-zinc-400 hover:text-violet-300 hover:border-violet-500/40 hover:bg-violet-500/5 transition-all duration-200"
              >
                {suggestion.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-zinc-800/60 bg-zinc-950/40">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isProcessing}
            placeholder={isProcessing ? 'Processando...' : 'Ex: "Dê zoom no início"'}
            className="flex-1 px-3.5 py-2.5 text-xs rounded-lg bg-zinc-900/60 border border-zinc-800 text-zinc-100 placeholder:text-zinc-600 focus:border-violet-500/50 focus:outline-none focus:ring-1 focus:ring-violet-500/30 disabled:opacity-50 transition-colors"
          />
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="px-4 py-2.5 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white text-xs font-bold hover:from-violet-500 hover:to-fuchsia-500 disabled:opacity-40 transition-all shadow-md shadow-violet-500/15 flex items-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
            Enviar
          </button>
        </div>
      </form>
    </div>
  );
}
