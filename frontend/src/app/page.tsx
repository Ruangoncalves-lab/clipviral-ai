'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '../lib/supabaseClient';
import UploadVideo from '../components/UploadVideo';
import CopilotChat from '../components/CopilotChat';
import InteractiveTranscript from '../components/InteractiveTranscript';
import BrollSuggestions from '../components/BrollSuggestions';

interface Profile {
  subtitle_font_size: number;
  subtitle_font_color: string;
  subtitle_font_style: string;
  credits: number;
}

interface Video {
  id: string;
  name: string;
  status: string;
  duration: number;
  error_message: string | null;
  created_at: string;
}

interface Clip {
  id: string;
  video_id: string;
  title: string;
  hook: string;
  reason: string;
  content_type: string;
  score: number;
  start_time: number;
  end_time: number;
  duration: number;
  storage_path: string;
}

interface ScheduledPost {
  id: string;
  user_id: string;
  clip_id: string;
  provider: string;
  title: string;
  description: string | null;
  scheduled_time: string;
  status: string;
  error_message: string | null;
}

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<Profile>({
    subtitle_font_size: 24,
    subtitle_font_color: '#FFFFFF',
    subtitle_font_style: 'outline',
    credits: 0,
  });

  const [videos, setVideos] = useState<Video[]>([]);
  const [clips, setClips] = useState<Clip[]>([]);
  const [updatingProfile, setUpdatingProfile] = useState(false);
  const [profileSuccessMsg, setProfileSuccessMsg] = useState('');
  const [activeTab, setActiveTab] = useState<'create' | 'videos' | 'calendar' | 'brandkit' | 'integrations' | 'billing'>('create');
  const [playingClip, setPlayingClip] = useState<Clip | null>(null);
  
  // Social and scheduling states
  const [connectedAccounts, setConnectedAccounts] = useState<any[]>([]);
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledPost[]>([]);
  const [schedulingClip, setSchedulingClip] = useState<Clip | null>(null);
  const [scheduleTitle, setScheduleTitle] = useState('');
  const [scheduleDescription, setScheduleDescription] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');
  const [scheduleProvider, setScheduleProvider] = useState('youtube');
  const [schedulingLoading, setSchedulingLoading] = useState(false);

  // Billing states
  const [checkoutPackage, setCheckoutPackage] = useState<{ name: string; credits: number; price: string } | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  // Copilot states
  const [editedVideoUrl, setEditedVideoUrl] = useState<string | null>(null);
  const [rightPanelTab, setRightPanelTab] = useState<'copilot' | 'transcript' | 'brolls'>('copilot');
  const videoPlayerRef = useRef<HTMLVideoElement>(null);

  const fetchSocialAccounts = async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from('social_accounts')
        .select('*')
        .eq('user_id', userId);
      if (!error && data) {
        setConnectedAccounts(data);
      }
    } catch (err) {
      console.error('Error fetching social accounts:', err);
    }
  };

  const fetchScheduledPosts = async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from('scheduled_posts')
        .select('*')
        .eq('user_id', userId)
        .order('scheduled_time', { ascending: true });
      if (!error && data) {
        setScheduledPosts(data);
      }
    } catch (err) {
      console.error('Error fetching scheduled posts:', err);
    }
  };

  const handleConnectSocial = (provider: string) => {
    if (!user) return;
    const width = 500;
    const height = 600;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
    
    window.open(
      `${backendUrl}/api/auth/social/connect/${provider}?user_id=${user.id}&supabase_url=${encodeURIComponent(supabaseUrl)}&supabase_key=${encodeURIComponent(supabaseKey)}`,
      `Conectar ${provider}`,
      `width=${width},height=${height},left=${left},top=${top}`
    );
  };

  const handleDisconnectSocial = async (provider: string) => {
    if (!user) return;
    const { error } = await supabase
      .from('social_accounts')
      .delete()
      .eq('user_id', user.id)
      .eq('provider', provider);
    if (!error) {
      setConnectedAccounts(prev => prev.filter(acc => acc.provider !== provider));
    } else {
      alert(`Erro ao desconectar: ${error.message}`);
    }
  };

  const handleSchedulePost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !schedulingClip) return;
    setSchedulingLoading(true);

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
      const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
      const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

      const res = await fetch(`${backendUrl}/api/schedule`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          clip_id: schedulingClip.id,
          provider: scheduleProvider,
          title: scheduleTitle,
          description: scheduleDescription,
          scheduled_time: new Date(scheduleTime).toISOString(),
          supabase_url: supabaseUrl,
          supabase_key: supabaseKey
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
      }

      alert('Post agendado com sucesso!');
      setSchedulingClip(null);
      setScheduleTitle('');
      setScheduleDescription('');
      setScheduleTime('');
      await fetchScheduledPosts(user.id);
    } catch (err: any) {
      alert(`Erro ao agendar: ${err.message || err}`);
    } finally {
      setSchedulingLoading(false);
    }
  };

  const handleMockPurchase = async () => {
    if (!user || !checkoutPackage) return;
    setCheckoutLoading(true);
    try {
      const { error } = await supabase.rpc('rpc_add_credits', {
        p_user_id: user.id,
        p_amount: checkoutPackage.credits
      });
      if (error) throw error;
      alert(`Upgrade concluído! ${checkoutPackage.credits} créditos foram adicionados à sua conta.`);
      await fetchProfile(user.id);
      setCheckoutPackage(null);
    } catch (err: any) {
      alert(`Erro no checkout mockado: ${err.message || err}`);
    } finally {
      setCheckoutLoading(false);
    }
  };

  const fetchProfile = async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('subtitle_font_size, subtitle_font_color, subtitle_font_style, credits')
        .eq('id', userId)
        .single();
      
      if (data) {
        setProfile(data as Profile);
      }
    } catch (err) {
      console.error('Error fetching profile:', err);
    }
  };

  const fetchData = async (userId: string) => {
    try {
      const { data: videosData, error: videosErr } = await supabase
        .from('videos')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false });

      if (videosErr) throw videosErr;
      setVideos(videosData || []);

      const { data: clipsData, error: clipsErr } = await supabase
        .from('clips')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false });

      if (clipsErr) throw clipsErr;
      setClips(clipsData || []);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    }
  };

  // Listen to popup callback messages
  useEffect(() => {
    const handleAuthMessage = (event: MessageEvent) => {
      if (event.data === 'social_connected' && user) {
        fetchSocialAccounts(user.id);
      }
    };
    window.addEventListener('message', handleAuthMessage);
    return () => window.removeEventListener('message', handleAuthMessage);
  }, [user]);

  const handleDownloadReport = (video: Video, videoClips: Clip[]) => {
    const reportData = {
      videoName: video.name,
      processedAt: new Date(video.created_at).toLocaleString('pt-BR'),
      totalClips: videoClips.length,
      clips: videoClips.map((c, i) => ({
        index: i + 1,
        title: c.title,
        score: c.score,
        hook: c.hook,
        reason: c.reason,
        contentType: c.content_type,
        durationSeconds: c.duration,
        timestamps: `${formatDuration(c.start_time)} - ${formatDuration(c.end_time)}`
      }))
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `relatorio_cortes_${video.name.toLowerCase().replace(/[^a-z0-9]+/g, '_')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Authenticate user
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession();
        if (error || !session) {
          router.push('/login');
          return;
        }
        setUser(session.user);
        await fetchProfile(session.user.id);
        await fetchData(session.user.id);
        await fetchSocialAccounts(session.user.id);
        await fetchScheduledPosts(session.user.id);
      } catch (err) {
        console.error(err);
        router.push('/login');
      } finally {
        setLoading(false);
      }
    };
    checkAuth();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event: any, session: any) => {
      if (event === 'SIGNED_OUT') {
        router.push('/login');
      } else if (session) {
        setUser(session.user);
        await fetchProfile(session.user.id);
        await fetchData(session.user.id);
        await fetchSocialAccounts(session.user.id);
        await fetchScheduledPosts(session.user.id);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [router]);

  // Periodic polling for videos status while there is any processing/pending video
  useEffect(() => {
    if (!user) return;
    const hasActiveJobs = videos.some(v => v.status === 'pending' || v.status === 'processing');
    if (!hasActiveJobs) return;

    const interval = setInterval(() => {
      fetchData(user.id);
    }, 5000);

    return () => clearInterval(interval);
  }, [videos, user]);



  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setUpdatingProfile(true);
    setProfileSuccessMsg('');

    try {
      const { error } = await supabase
        .from('profiles')
        .update({
          subtitle_font_size: profile.subtitle_font_size,
          subtitle_font_color: profile.subtitle_font_color,
          subtitle_font_style: profile.subtitle_font_style,
        })
        .eq('id', user.id);

      if (error) throw error;
      setProfileSuccessMsg('Preferências do Brand Kit salvas com sucesso!');
      setTimeout(() => setProfileSuccessMsg(''), 5000);
    } catch (err: any) {
      alert(`Erro ao salvar preferências: ${err.message || err}`);
    } finally {
      setUpdatingProfile(false);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push('/login');
  };

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Calendar rendering computations
  const getDaysInMonth = (year: number, month: number) => new Date(year, month + 1, 0).getDate();
  const getFirstDayOfMonth = (year: number, month: number) => new Date(year, month, 1).getDay();

  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth();
  const daysInMonth = getDaysInMonth(currentYear, currentMonth);
  const firstDayIndex = getFirstDayOfMonth(currentYear, currentMonth);

  const monthNames = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
  ];

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-100">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-4 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-zinc-400 font-medium">Carregando ClipViral AI...</p>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans flex flex-row">
      
      {/* 1. Sidebar Panel */}
      <aside className="w-64 border-r border-zinc-800 bg-zinc-900/30 backdrop-blur-lg flex flex-col justify-between h-screen sticky top-0 z-40">
        <div className="flex flex-col flex-1">
          {/* Logo Section */}
          <div className="p-6 flex items-center space-x-3 border-b border-zinc-900">
            <div className="bg-gradient-to-tr from-violet-600 to-fuchsia-600 w-9 h-9 rounded-xl flex items-center justify-center shadow-lg shadow-violet-500/20">
              <span className="font-extrabold text-white text-base">C</span>
            </div>
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-violet-400 to-fuchsia-500 bg-clip-text text-transparent">
              ClipViral AI
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5 flex-1">
            <button
              onClick={() => setActiveTab('create')}
              className={`w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                activeTab === 'create'
                  ? 'sidebar-link-active'
                  : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-100'
              }`}
            >
              <svg className="w-4 h-4 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Criar Novo Vídeo</span>
            </button>

            <button
              onClick={() => setActiveTab('videos')}
              className={`w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                activeTab === 'videos'
                  ? 'sidebar-link-active'
                  : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-100'
              }`}
            >
              <svg className="w-4 h-4 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <span>Meus Vídeos</span>
            </button>

            <button
              onClick={() => setActiveTab('calendar')}
              className={`w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                activeTab === 'calendar'
                  ? 'sidebar-link-active'
                  : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-100'
              }`}
            >
              <svg className="w-4 h-4 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span>Calendário Editorial</span>
            </button>

            <button
              onClick={() => setActiveTab('brandkit')}
              className={`w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                activeTab === 'brandkit'
                  ? 'sidebar-link-active'
                  : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-100'
              }`}
            >
              <svg className="w-4 h-4 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
              </svg>
              <span>Brand Kit (Estilos)</span>
            </button>

            <button
              onClick={() => setActiveTab('integrations')}
              className={`w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                activeTab === 'integrations'
                  ? 'sidebar-link-active'
                  : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-100'
              }`}
            >
              <svg className="w-4 h-4 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              <span>Integrações</span>
            </button>

            <button
              onClick={() => setActiveTab('billing')}
              className={`w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                activeTab === 'billing'
                  ? 'sidebar-link-active'
                  : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-100'
              }`}
            >
              <svg className="w-4 h-4 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
              <span>Faturamento</span>
            </button>
          </nav>
        </div>

        {/* User Profile Footer */}
        <div className="p-4 border-t border-zinc-900 bg-zinc-950/20 space-y-3">
          <div className="text-left space-y-0.5">
            <p className="text-xs text-zinc-500 font-medium truncate" title={user.email}>{user.email}</p>
            <p className="text-xs font-semibold bg-gradient-to-r from-violet-400 to-fuchsia-500 bg-clip-text text-transparent">
              {profile.credits} Créditos Restantes
            </p>
          </div>
          <button
            onClick={handleSignOut}
            className="w-full py-2 text-xs font-bold rounded-lg border border-zinc-800 bg-zinc-900/50 hover:bg-zinc-800 hover:text-white transition-colors"
          >
            Sair
          </button>
        </div>
      </aside>

      {/* 2. Main Workspace Content Area */}
      <main className="flex-1 min-h-screen p-8 lg:p-12 overflow-y-auto max-w-6xl mx-auto flex flex-col justify-start">
        
        {/* Header Title with Reload action */}
        <div className="flex items-center justify-between border-b border-zinc-800 pb-5 mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-zinc-100 uppercase">
              {activeTab === 'create' && 'Criar Novo Vídeo'}
              {activeTab === 'videos' && 'Meus Vídeos Processados'}
              {activeTab === 'calendar' && `Calendário Editorial • ${monthNames[currentMonth]} ${currentYear}`}
              {activeTab === 'brandkit' && 'Brand Kit (Legendas da Marca)'}
              {activeTab === 'integrations' && 'Integrações de Redes Sociais'}
              {activeTab === 'billing' && 'Faturamento e Assinaturas'}
            </h1>
            <p className="text-xs text-zinc-500 mt-1">
              {activeTab === 'create' && 'Faça upload de vídeos longos para gerar cortes virais dinâmicos.'}
              {activeTab === 'videos' && 'Gerencie seus vídeos e visualize os melhores momentos extraídos por IA.'}
              {activeTab === 'calendar' && 'Monitore a grade de agendamento de posts e publicações nas suas redes.'}
              {activeTab === 'brandkit' && 'Customize o estilo padrão do karaoke das legendas geradas automaticamente.'}
              {activeTab === 'integrations' && 'Conecte suas contas de publicação automática para Shorts, TikTok e Reels.'}
              {activeTab === 'billing' && 'Gerencie créditos de renderização e faça upgrade do seu plano.'}
            </p>
          </div>

          <button
            onClick={() => {
              fetchData(user.id);
              fetchSocialAccounts(user.id);
              fetchScheduledPosts(user.id);
            }}
            className="p-2 rounded-lg border border-zinc-800 bg-zinc-900/40 hover:bg-zinc-800/80 text-zinc-400 hover:text-white transition-colors"
            title="Recarregar dados"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H12v9" />
            </svg>
          </button>
        </div>

        {/* 3. Render Tab Panels */}
        
        {/* Tab 1: Create Video */}
        {activeTab === 'create' && (
          <div className="space-y-6 max-w-xl mx-auto w-full animate-fadeIn">
            <div className="glass-panel p-6 rounded-2xl border border-zinc-800 shadow-xl space-y-6">
              <h3 className="text-lg font-bold text-zinc-200">Upload de Vídeo</h3>
              <UploadVideo onUploadSuccess={() => {
                fetchData(user.id);
                setActiveTab('videos');
              }} />
            </div>
          </div>
        )}

        {/* Tab 2: Videos Grid */}
        {activeTab === 'videos' && (
          <div className="space-y-6 animate-fadeIn">
            {videos.length === 0 ? (
              <div className="text-center py-20 border border-zinc-800 rounded-2xl bg-zinc-900/10 glass-panel">
                <svg className="w-12 h-12 text-zinc-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
                </svg>
                <h3 className="text-lg font-bold text-zinc-400">Nenhum vídeo processado</h3>
                <p className="text-zinc-600 text-sm mt-1 max-w-sm mx-auto">
                  Vá na aba <strong>Criar Novo Vídeo</strong> e faça o upload do seu primeiro arquivo longo.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {videos.map((video) => {
                  const videoClips = clips.filter((c) => c.video_id === video.id);
                  return (
                    <div key={video.id} className="rounded-2xl border border-zinc-800 bg-zinc-900/10 glass-panel overflow-hidden shadow-lg">
                      
                      {/* Video Header bar */}
                      <div className="p-5 bg-zinc-900/20 border-b border-zinc-800/60 flex flex-wrap items-center justify-between gap-4">
                        <div>
                          <h4 className="font-bold text-base text-zinc-100">{video.name}</h4>
                          <p className="text-xs text-zinc-500">
                            Processado em: {new Date(video.created_at).toLocaleString('pt-BR')}
                            {video.duration > 0 && ` • Duração: ${formatDuration(video.duration)}`}
                          </p>
                        </div>
                        
                        <div className="flex items-center space-x-3">
                          {video.status === 'completed' && (
                            <button
                              onClick={() => handleDownloadReport(video, videoClips)}
                              className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white transition-colors flex items-center space-x-2"
                            >
                              <svg className="w-3.5 h-3.5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                              <span>Exportar Relatório</span>
                            </button>
                          )}

                          {video.status === 'pending' && (
                            <span className="px-3.5 py-1.5 text-xs font-semibold rounded-full border border-yellow-500/20 bg-yellow-500/10 text-yellow-500 flex items-center space-x-1 animate-pulse">
                              <span>Pendente na fila</span>
                            </span>
                          )}
                          {video.status === 'processing' && (
                            <span className="px-3.5 py-1.5 text-xs font-semibold rounded-full border border-violet-500/20 bg-violet-500/10 text-violet-400 flex items-center space-x-2">
                              <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-ping"></span>
                              <span>IA selecionando cortes...</span>
                            </span>
                          )}
                          {video.status === 'completed' && (
                            <span className="px-3.5 py-1.5 text-xs font-semibold rounded-full border border-emerald-500/20 bg-emerald-500/10 text-emerald-400">
                              Concluído ({videoClips.length} cortes)
                            </span>
                          )}
                          {video.status === 'failed' && (
                            <span className="px-3.5 py-1.5 text-xs font-semibold rounded-full border border-red-500/20 bg-red-500/10 text-red-400" title={video.error_message || ''}>
                              Erro
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Video error if failed */}
                      {video.status === 'failed' && video.error_message && (
                        <div className="p-5 border-b border-zinc-800/60 bg-red-500/5 text-sm text-red-400/80">
                          <strong>Erro:</strong> {video.error_message}
                        </div>
                      )}

                      {/* Video clips grid lists */}
                      {video.status === 'completed' && (
                        <div className="p-5 space-y-4">
                          <h5 className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Cortes Recomendados</h5>
                          
                          {videoClips.length === 0 ? (
                            <p className="text-sm text-zinc-500 py-2">Nenhum corte gerado para este vídeo.</p>
                          ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              {videoClips.map((clip) => (
                                <div key={clip.id} className="rounded-xl border border-zinc-800/60 bg-zinc-950/80 p-4 flex flex-col justify-between hover:border-zinc-700/80 transition-colors">
                                  <div>
                                    <div className="flex justify-between items-start mb-2">
                                      <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-zinc-800 text-zinc-400 uppercase">
                                        {clip.content_type}
                                      </span>
                                      <span className={`px-2 py-0.5 text-[10px] font-extrabold rounded ${
                                        clip.score >= 80 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                        clip.score >= 60 ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' :
                                        'bg-zinc-800 text-zinc-400'
                                      }`}>
                                        Score: {clip.score}
                                      </span>
                                    </div>
                                    <h6 className="font-bold text-sm text-zinc-200 mb-1 leading-snug truncate">
                                      {clip.title}
                                    </h6>
                                    <p className="text-xs text-violet-400 font-medium mb-2 truncate">
                                      Hook: &ldquo;{clip.hook}&rdquo;
                                    </p>
                                    <p className="text-xs text-zinc-500 leading-relaxed mb-3 line-clamp-2">
                                      {clip.reason}
                                    </p>
                                    <div className="text-[11px] text-zinc-600 mb-4 font-mono">
                                      Tempo: {formatDuration(clip.start_time)}s - {formatDuration(clip.end_time)}s ({formatDuration(clip.duration)}s)
                                    </div>
                                  </div>

                                  <div className="pt-3 border-t border-zinc-900 space-y-2">
                                    <div className="grid grid-cols-2 gap-2">
                                      <button
                                        onClick={() => setPlayingClip(clip)}
                                        className="inline-flex items-center justify-center px-3 py-2 text-xs font-semibold rounded-lg bg-violet-600 hover:bg-violet-500 text-white transition-all cursor-pointer shadow-md shadow-violet-500/10"
                                      >
                                        Visualizar
                                      </button>
                                      <a
                                        href={clip.storage_path ? `https://pub-cf69eb74b3d74c0c80ee91f24d3101aa.r2.dev/${clip.storage_path}` : '#'}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="inline-flex items-center justify-center px-3 py-2 text-xs font-semibold rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-white transition-all"
                                      >
                                        Baixar (MP4)
                                      </a>
                                    </div>
                                    
                                    <button
                                      onClick={() => {
                                        setSchedulingClip(clip);
                                        setScheduleTitle(clip.title);
                                        setScheduleDescription(clip.reason);
                                        if (connectedAccounts.length > 0) {
                                          setScheduleProvider(connectedAccounts[0].provider);
                                        } else {
                                          setScheduleProvider('youtube');
                                        }
                                      }}
                                      className="inline-flex w-full items-center justify-center px-3 py-2 text-xs font-semibold rounded-lg bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-400 hover:text-white transition-all cursor-pointer"
                                    >
                                      <svg className="w-3.5 h-3.5 mr-1.5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                      </svg>
                                      Agendar Post
                                    </button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                      
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Calendar View */}
        {activeTab === 'calendar' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="bg-zinc-900/10 glass-panel p-6 rounded-2xl border border-zinc-800 shadow-xl space-y-6">
              
              {/* Header calendar info */}
              <div className="flex justify-between items-center">
                <h3 className="font-bold text-lg text-zinc-200">Agendador Social</h3>
                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-violet-500/10 text-violet-400 border border-violet-500/20">
                  {scheduledPosts.length} posts agendados no mês
                </span>
              </div>

              {/* Day header */}
              <div className="grid grid-cols-7 text-center text-xs font-bold text-zinc-500 uppercase tracking-wider pb-2 border-b border-zinc-800">
                <div>Dom</div>
                <div>Seg</div>
                <div>Ter</div>
                <div>Qua</div>
                <div>Qui</div>
                <div>Sex</div>
                <div>Sáb</div>
              </div>

              {/* Grid Cells */}
              <div className="calendar-grid">
                {/* Empty cells before month start */}
                {Array.from({ length: firstDayIndex }).map((_, i) => (
                  <div key={`empty-${i}`} className="calendar-cell-empty" />
                ))}

                {/* Days cells */}
                {Array.from({ length: daysInMonth }).map((_, i) => {
                  const day = i + 1;
                  const dayPosts = scheduledPosts.filter(post => {
                    const postDate = new Date(post.scheduled_time);
                    return postDate.getFullYear() === currentYear &&
                           postDate.getMonth() === currentMonth &&
                           postDate.getDate() === day;
                  });

                  return (
                    <div key={`day-${day}`} className="calendar-cell">
                      <div className="font-semibold text-xs text-zinc-400 self-end">{day}</div>
                      
                      <div className="flex flex-col space-y-1 mt-1 w-full overflow-hidden">
                        {dayPosts.map((post) => (
                          <div 
                            key={post.id} 
                            className={`px-1.5 py-0.5 rounded text-[9px] font-medium truncate flex items-center space-x-1 ${
                              post.status === 'posted' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                              post.status === 'failed' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                              post.status === 'publishing' ? 'bg-violet-500/10 text-violet-400 border border-violet-500/20 animate-pulse' :
                              'bg-zinc-800 text-zinc-300'
                            }`}
                            title={`${post.provider.toUpperCase()}: ${post.title} (${post.status})`}
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                            <span className="truncate">{post.title}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>

            </div>
          </div>
        )}

        {/* Tab 4: Brand Kit Styling */}
        {activeTab === 'brandkit' && (
          <div className="space-y-6 max-w-xl mx-auto w-full animate-fadeIn">
            <div className="bg-zinc-900/10 glass-panel p-6 rounded-2xl border border-zinc-800 shadow-xl space-y-6">
              
              <div>
                <h3 className="text-lg font-bold text-zinc-200">Estilos de Legenda do Brand Kit</h3>
                <p className="text-xs text-zinc-500 mt-1">Defina fontes e karaoke padrão para manter a identidade visual da sua marca nos cortes.</p>
              </div>

              {profileSuccessMsg && (
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-400">
                  {profileSuccessMsg}
                </div>
              )}

              <form onSubmit={handleUpdateProfile} className="space-y-5">
                <div>
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                    Tamanho da Fonte (px)
                  </label>
                  <input
                    type="number"
                    min="14"
                    max="64"
                    value={profile.subtitle_font_size}
                    onChange={(e) => setProfile({ ...profile, subtitle_font_size: parseInt(e.target.value) || 24 })}
                    className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3.5 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                    Cor Principal das Letras
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="color"
                      value={profile.subtitle_font_color}
                      onChange={(e) => setProfile({ ...profile, subtitle_font_color: e.target.value })}
                      className="w-10 h-10 rounded border border-zinc-800 bg-zinc-950 cursor-pointer"
                    />
                    <input
                      type="text"
                      value={profile.subtitle_font_color.toUpperCase()}
                      onChange={(e) => setProfile({ ...profile, subtitle_font_color: e.target.value })}
                      className="flex-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3.5 py-2 text-sm uppercase focus:border-violet-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                    Estilo de Fundo do Karaoke
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setProfile({ ...profile, subtitle_font_style: 'outline' })}
                      className={`py-2.5 text-sm font-semibold rounded-lg border transition-all ${
                        profile.subtitle_font_style === 'outline'
                          ? 'border-violet-500 bg-violet-500/10 text-violet-400'
                          : 'border-zinc-800 bg-zinc-950 text-zinc-400'
                      }`}
                    >
                      Contorno (Outline)
                    </button>
                    <button
                      type="button"
                      onClick={() => setProfile({ ...profile, subtitle_font_style: 'box' })}
                      className={`py-2.5 text-sm font-semibold rounded-lg border transition-all ${
                        profile.subtitle_font_style === 'box'
                          ? 'border-violet-500 bg-violet-500/10 text-violet-400'
                          : 'border-zinc-800 bg-zinc-950 text-zinc-400'
                      }`}
                    >
                      Caixa Cheia (Box)
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={updatingProfile}
                  className="w-full py-3 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 font-semibold hover:from-violet-500 hover:to-fuchsia-500 disabled:opacity-50 transition-all text-sm shadow-lg shadow-violet-500/15"
                >
                  {updatingProfile ? 'Salvando preferências...' : 'Salvar Preferências'}
                </button>
              </form>

            </div>
          </div>
        )}

        {/* Tab 5: Social Connections */}
        {activeTab === 'integrations' && (
          <div className="space-y-6 max-w-xl mx-auto w-full animate-fadeIn">
            <div className="bg-zinc-900/10 glass-panel p-6 rounded-2xl border border-zinc-800 shadow-xl space-y-6">
              
              <div>
                <h3 className="text-lg font-bold text-zinc-200">Conexões de Contas sociais</h3>
                <p className="text-xs text-zinc-500 mt-1">Conecte seus perfis oficiais para publicar automaticamente no formato vertical (9:16).</p>
              </div>

              <div className="space-y-4">
                {/* YouTube */}
                {(() => {
                  const isConnected = connectedAccounts.some(acc => acc.provider === 'youtube');
                  const account = connectedAccounts.find(acc => acc.provider === 'youtube');
                  return (
                    <div className="flex items-center justify-between p-4 rounded-xl border border-zinc-800 bg-zinc-950/40">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 rounded-lg bg-red-600/10 flex items-center justify-center border border-red-500/20 text-red-500">
                          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M23.498 6.163a3.003 3.003 0 0 0-2.11-2.11C19.517 3.545 12 3.545 12 3.545s-7.517 0-9.388.508a3.003 3.003 0 0 0-2.11 2.11C0 8.033 0 12 0 12s0 3.967.502 5.837a3.003 3.003 0 0 0 2.11 2.11c1.871.508 9.388.508 9.388.508s7.517 0 9.388-.508a3.003 3.003 0 0 0 2.11-2.11C24 15.967 24 12 24 12s0-3.967-.502-5.837zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                          </svg>
                        </div>
                        <div>
                          <h4 className="font-bold text-sm text-zinc-200">YouTube Shorts</h4>
                          <p className="text-xs text-zinc-500">{isConnected && account ? `Conectado como: ${account.account_name}` : 'Não conectado'}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => isConnected ? handleDisconnectSocial('youtube') : handleConnectSocial('youtube')}
                        className={`px-4 py-2 text-xs font-semibold rounded-lg border transition-all ${
                          isConnected 
                            ? 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20' 
                            : 'bg-violet-600 hover:bg-violet-500 border-transparent text-white'
                        }`}
                      >
                        {isConnected ? 'Desconectar' : 'Conectar'}
                      </button>
                    </div>
                  );
                })()}

                {/* TikTok */}
                {(() => {
                  const isConnected = connectedAccounts.some(acc => acc.provider === 'tiktok');
                  const account = connectedAccounts.find(acc => acc.provider === 'tiktok');
                  return (
                    <div className="flex items-center justify-between p-4 rounded-xl border border-zinc-800 bg-zinc-950/40">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 rounded-lg bg-zinc-100/10 flex items-center justify-center border border-zinc-100/20 text-zinc-100">
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.17-2.89-.74-3.99-1.72-.08-.07-.15-.15-.24-.22v6.2c.1 4.55-3.37 8.68-7.92 9.17-5.18.57-9.94-3.14-10.22-8.32C-.27 10.26 3.65 5.5 8.81 5.11c1.23-.1 2.47.04 3.66.45V9.7c-.88-.41-1.89-.52-2.83-.28-2.22.55-3.69 2.87-3.23 5.12.35 1.71 1.83 3 3.58 3 2.11-.06 3.73-1.89 3.62-4v-13.5c-.03-.01-.06-.02-.09-.02z"/>
                          </svg>
                        </div>
                        <div>
                          <h4 className="font-bold text-sm text-zinc-200">TikTok</h4>
                          <p className="text-xs text-zinc-500">{isConnected && account ? `Conectado como: ${account.account_name}` : 'Não conectado'}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => isConnected ? handleDisconnectSocial('tiktok') : handleConnectSocial('tiktok')}
                        className={`px-4 py-2 text-xs font-semibold rounded-lg border transition-all ${
                          isConnected 
                            ? 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20' 
                            : 'bg-violet-600 hover:bg-violet-500 border-transparent text-white'
                        }`}
                      >
                        {isConnected ? 'Desconectar' : 'Conectar'}
                      </button>
                    </div>
                  );
                })()}

                {/* Instagram */}
                {(() => {
                  const isConnected = connectedAccounts.some(acc => acc.provider === 'instagram');
                  const account = connectedAccounts.find(acc => acc.provider === 'instagram');
                  return (
                    <div className="flex items-center justify-between p-4 rounded-xl border border-zinc-800 bg-zinc-950/40">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 rounded-lg bg-pink-600/10 flex items-center justify-center border border-pink-500/20 text-pink-500">
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.051.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/>
                          </svg>
                        </div>
                        <div>
                          <h4 className="font-bold text-sm text-zinc-200">Instagram Reels</h4>
                          <p className="text-xs text-zinc-500">{isConnected && account ? `Conectado como: ${account.account_name}` : 'Não conectado'}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => isConnected ? handleDisconnectSocial('instagram') : handleConnectSocial('instagram')}
                        className={`px-4 py-2 text-xs font-semibold rounded-lg border transition-all ${
                          isConnected 
                            ? 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20' 
                            : 'bg-violet-600 hover:bg-violet-500 border-transparent text-white'
                        }`}
                      >
                        {isConnected ? 'Desconectar' : 'Conectar'}
                      </button>
                    </div>
                  );
                })()}
              </div>

            </div>
          </div>
        )}

        {/* Tab 6: Billing & Stripe Checkout */}
        {activeTab === 'billing' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="bg-zinc-900/10 glass-panel p-6 rounded-2xl border border-zinc-800 shadow-xl space-y-6">
              
              <div>
                <h3 className="text-lg font-bold text-zinc-200">Planos e Créditos de Processamento</h3>
                <p className="text-xs text-zinc-500 mt-1">Escolha o plano ideal e pague com segurança via Stripe.</p>
              </div>

              {/* Active Plan info */}
              <div className="p-4 rounded-xl border border-violet-500/20 bg-violet-500/5 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-bold text-violet-400 uppercase tracking-widest bg-violet-500/10 px-2 py-0.5 rounded border border-violet-500/10">Plano Atual</span>
                  <h4 className="font-bold text-base text-zinc-200 mt-1.5">Free Trial (Acesso Gratuito)</h4>
                  <p className="text-xs text-zinc-500 mt-0.5">Faça upgrade para desbloquear recursos premium.</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-extrabold text-white">{profile.credits}</p>
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">Créditos Restantes</p>
                </div>
              </div>

              {/* Package Tiers list */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
                {[
                  { id: 'starter', name: 'Starter Pack', credits: 10, price: 'Grátis', desc: 'Ideal para testar a plataforma.', features: ['10 créditos', 'Legendas automáticas', 'Exportação 720p'], popular: false },
                  { id: 'creator', name: 'Creator Pro', credits: 100, price: 'R$ 49,90', desc: 'Para criadores de conteúdo profissionais.', features: ['100 créditos', 'Processamento prioritário', 'Brand Kit', '1080p', 'Copilot IA'], popular: true },
                  { id: 'agency', name: 'Agency Prime', credits: 500, price: 'R$ 149,90', desc: 'Agências e equipes de conteúdo.', features: ['500 créditos', 'Multi-contas (5)', '4K', 'API Access', 'Suporte VIP', 'B-Rolls IA'], popular: false }
                ].map((pkg, idx) => (
                  <div key={idx} className={`relative p-5 rounded-xl border flex flex-col justify-between transition-all ${pkg.popular ? 'border-violet-500/50 bg-violet-500/5 shadow-xl shadow-violet-500/10' : 'border-zinc-800 bg-zinc-950 hover:border-zinc-700'}`}>
                    {pkg.popular && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-600 text-[9px] font-bold text-white uppercase tracking-wider">
                        Mais Popular
                      </div>
                    )}
                    <div>
                      <h4 className="font-bold text-sm text-zinc-300">{pkg.name}</h4>
                      <p className="text-2xl font-extrabold text-white mt-2">{pkg.price}</p>
                      <p className="text-[10px] text-violet-400 font-semibold mt-1">+{pkg.credits} Créditos de Vídeo</p>
                      <p className="text-xs text-zinc-500 mt-3 leading-relaxed">{pkg.desc}</p>
                      <ul className="mt-3 space-y-1.5">
                        {pkg.features.map((f, fi) => (
                          <li key={fi} className="text-[11px] text-zinc-400 flex items-center gap-2">
                            <svg className="w-3 h-3 text-emerald-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                            {f}
                          </li>
                        ))}
                      </ul>
                    </div>
                    
                    <button
                      onClick={async () => {
                        setCheckoutLoading(true);
                        try {
                          const { data: { session } } = await supabase.auth.getSession();
                          if (!session) throw new Error('Login required');
                          
                          const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'}/api/stripe/checkout`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                              plan_id: pkg.id,
                              user_id: session.user.id,
                              user_email: session.user.email || '',
                              success_url: window.location.origin + '?checkout=success',
                              cancel_url: window.location.origin + '?checkout=cancelled',
                            }),
                          });
                          const data = await res.json();
                          
                          if (data.free) {
                            alert(`✅ ${pkg.credits} créditos adicionados!`);
                          } else if (data.checkout_url) {
                            window.open(data.checkout_url, '_blank');
                          }
                        } catch (err: any) {
                          alert(err.message || 'Erro ao iniciar checkout');
                        } finally {
                          setCheckoutLoading(false);
                        }
                      }}
                      disabled={checkoutLoading}
                      className={`mt-6 w-full py-2.5 text-xs font-bold rounded-lg transition-all disabled:opacity-40 ${
                        pkg.popular
                          ? 'bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white shadow-md shadow-violet-500/20 hover:from-violet-500 hover:to-fuchsia-500'
                          : 'bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white border border-zinc-800'
                      }`}
                    >
                      {checkoutLoading ? 'Processando...' : pkg.price === 'Grátis' ? 'Ativar Grátis' : `Assinar ${pkg.name}`}
                    </button>
                  </div>
                ))}
              </div>

              {/* Stripe Trust Badge */}
              <div className="flex items-center justify-center gap-3 pt-2">
                <span className="text-[10px] text-zinc-600">Pagamentos processados com segurança por</span>
                <span className="text-xs font-bold text-zinc-500">Stripe</span>
                <svg className="w-4 h-4 text-zinc-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>

            </div>
          </div>
        )}

      </main>

      {/* 4. Modals Overlays */}

      {/* Video Preview Modal — Side-by-Side with Copilot Chat */}
      {playingClip && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-lg transition-opacity duration-300 animate-fadeIn"
          onClick={() => { setPlayingClip(null); setEditedVideoUrl(null); }}
        >
          <div 
            className="relative w-full max-w-5xl h-[85vh] rounded-2xl overflow-hidden border border-zinc-800 bg-zinc-950 shadow-2xl flex flex-row animate-scaleUp"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Left Side — Video Player */}
            <div className="flex-1 flex flex-col min-w-0 border-r border-zinc-800/60">
              {/* Header */}
              <div className="w-full flex items-center justify-between px-5 py-3 border-b border-zinc-800/60 bg-zinc-900/20">
                <div className="truncate max-w-[70%]">
                  <h3 className="font-bold text-sm text-zinc-100 truncate">{playingClip.title}</h3>
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">{playingClip.content_type} • Score: {playingClip.score} • {formatDuration(playingClip.duration)}</p>
                </div>
                <div className="flex items-center gap-2">
                  {editedVideoUrl && (
                    <button
                      onClick={() => setEditedVideoUrl(null)}
                      className="px-3 py-1.5 text-[10px] font-bold rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-700 transition-colors flex items-center gap-1.5"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                      </svg>
                      Desfazer
                    </button>
                  )}
                  <button 
                    onClick={() => { setPlayingClip(null); setEditedVideoUrl(null); }}
                    className="p-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-white transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Player */}
              <div className="flex-1 flex items-center justify-center bg-black p-4 min-h-0">
                <div className="relative h-full aspect-[9/16] max-h-full bg-black rounded-xl overflow-hidden border border-zinc-900">
                  <video 
                    ref={videoPlayerRef}
                    key={editedVideoUrl || playingClip.storage_path}
                    src={editedVideoUrl || `https://pub-cf69eb74b3d74c0c80ee91f24d3101aa.r2.dev/${playingClip.storage_path}`} 
                    controls 
                    autoPlay 
                    className="w-full h-full object-contain"
                  />
                  {editedVideoUrl && (
                    <div className="absolute top-2 left-2 px-2 py-1 rounded-md bg-violet-600/80 text-[9px] font-bold text-white uppercase tracking-wider backdrop-blur-sm">
                      ✨ Editado pelo Copilot
                    </div>
                  )}
                </div>
              </div>

              {/* Hook info */}
              <div className="px-5 py-3 border-t border-zinc-800/60 bg-zinc-900/20">
                <p className="text-violet-400 font-semibold text-xs">&ldquo;{playingClip.hook}&rdquo;</p>
                <p className="text-zinc-500 text-[10px] leading-relaxed mt-1 line-clamp-2">{playingClip.reason}</p>
              </div>
            </div>

            {/* Right Side — Tabbed Panel */}
            <div className="w-[380px] flex-shrink-0 flex flex-col bg-zinc-950/80">
              {/* Tab Toggle */}
              <div className="flex border-b border-zinc-800/60">
                <button
                  type="button"
                  onClick={() => setRightPanelTab('copilot')}
                  className={`flex-1 py-2.5 text-[11px] font-bold transition-all ${rightPanelTab === 'copilot' ? 'text-violet-400 border-b-2 border-violet-500 bg-violet-500/5' : 'text-zinc-500 hover:text-zinc-300'}`}
                >
                  ✨ Copilot
                </button>
                <button
                  type="button"
                  onClick={() => setRightPanelTab('transcript')}
                  className={`flex-1 py-2.5 text-[11px] font-bold transition-all ${rightPanelTab === 'transcript' ? 'text-amber-400 border-b-2 border-amber-500 bg-amber-500/5' : 'text-zinc-500 hover:text-zinc-300'}`}
                >
                  📝 Transcrição
                </button>
                <button
                  type="button"
                  onClick={() => setRightPanelTab('brolls')}
                  className={`flex-1 py-2.5 text-[11px] font-bold transition-all ${rightPanelTab === 'brolls' ? 'text-indigo-400 border-b-2 border-indigo-500 bg-indigo-500/5' : 'text-zinc-500 hover:text-zinc-300'}`}
                >
                  🎬 B-Rolls
                </button>
              </div>

              {/* Panel Content */}
              <div className="flex-1 min-h-0">
                {rightPanelTab === 'copilot' ? (
                  <CopilotChat
                    clipId={playingClip.id}
                    userId={user.id}
                    storagePath={playingClip.storage_path}
                    clipDuration={playingClip.duration}
                    onVideoUpdate={(newUrl) => setEditedVideoUrl(newUrl)}
                  />
                ) : rightPanelTab === 'transcript' ? (
                  <InteractiveTranscript
                    storagePath={playingClip.storage_path}
                    videoRef={videoPlayerRef}
                  />
                ) : (
                  <BrollSuggestions
                    storagePath={playingClip.storage_path}
                    clipDuration={playingClip.duration}
                    videoRef={videoPlayerRef}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Scheduling Post Modal */}
      {schedulingClip && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md transition-opacity duration-300 animate-fadeIn"
          onClick={() => setSchedulingClip(null)}
        >
          <form 
            onSubmit={handleSchedulePost}
            className="relative w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl flex flex-col space-y-4 animate-scaleUp"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-zinc-900 pb-3">
              <div>
                <h3 className="font-bold text-base text-zinc-100">Agendar Publicação</h3>
                <p className="text-xs text-zinc-500">Configure a publicação para suas redes conectadas</p>
              </div>
              <button 
                type="button"
                onClick={() => setSchedulingClip(null)}
                className="p-1 rounded-lg bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-400 hover:text-white transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Rede Social Destino
              </label>
              {connectedAccounts.length === 0 ? (
                <div className="p-3 text-xs rounded-lg border border-red-500/20 bg-red-500/10 text-red-400">
                  Nenhuma conta conectada. Por favor, conecte uma conta na aba <strong>Integrações</strong> antes de agendar.
                </div>
              ) : (
                <select
                  value={scheduleProvider}
                  onChange={(e) => setScheduleProvider(e.target.value)}
                  className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3.5 py-2.5 text-sm focus:border-violet-500 focus:outline-none text-zinc-200"
                >
                  {connectedAccounts.map((acc) => (
                    <option key={acc.id} value={acc.provider}>
                      {acc.provider.toUpperCase()} - {acc.account_name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Título do Vídeo
              </label>
              <input
                type="text"
                required
                value={scheduleTitle}
                onChange={(e) => setScheduleTitle(e.target.value)}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3.5 py-2.5 text-sm focus:border-violet-500 focus:outline-none text-zinc-100"
                placeholder="Ex: Segredo dos Vídeos Virais"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Legenda do Post
              </label>
              <textarea
                value={scheduleDescription}
                onChange={(e) => setScheduleDescription(e.target.value)}
                rows={3}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3.5 py-2.5 text-sm focus:border-violet-500 focus:outline-none text-zinc-100 resize-none"
                placeholder="Insira as hashtags e descrição..."
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Data e Hora
              </label>
              <input
                type="datetime-local"
                required
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3.5 py-2.5 text-sm focus:border-violet-500 focus:outline-none text-zinc-100"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={schedulingLoading || connectedAccounts.length === 0}
                className="w-full py-3 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 font-semibold hover:from-violet-500 hover:to-fuchsia-500 disabled:opacity-50 transition-all text-sm shadow-md"
              >
                {schedulingLoading ? 'Agendando...' : 'Confirmar Agendamento'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Mock Upgrade Checkout Modal */}
      {checkoutPackage && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md transition-opacity duration-300 animate-fadeIn"
          onClick={() => setCheckoutPackage(null)}
        >
          <div 
            className="relative w-full max-w-sm rounded-2xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl flex flex-col space-y-4 animate-scaleUp"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-zinc-900 pb-3">
              <div>
                <h3 className="font-bold text-base text-zinc-100">Confirmar Upgrade</h3>
                <p className="text-xs text-zinc-500">Checkout mockado do ClipViral AI</p>
              </div>
              <button 
                type="button"
                onClick={() => setCheckoutPackage(null)}
                className="p-1 rounded-lg bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-400 hover:text-white transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/40 text-center space-y-2">
              <h4 className="font-extrabold text-sm text-zinc-300 uppercase tracking-widest">{checkoutPackage.name}</h4>
              <p className="text-3xl font-extrabold text-white">{checkoutPackage.price}</p>
              <p className="text-xs text-violet-400 font-semibold">Adiciona {checkoutPackage.credits} créditos na sua conta</p>
            </div>

            <div className="text-xs text-zinc-500 leading-relaxed text-center">
              Como este é um ambiente de testes, o pagamento é simulado e nenhuma cobrança real será efetuada. Os créditos serão inseridos instantaneamente em seu perfil.
            </div>

            <button
              onClick={handleMockPurchase}
              disabled={checkoutLoading}
              className="w-full py-3 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 font-semibold hover:from-violet-500 hover:to-fuchsia-500 disabled:opacity-50 transition-all text-sm shadow-md"
            >
              {checkoutLoading ? 'Processando pagamento...' : 'Confirmar Pagamento'}
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
