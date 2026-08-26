import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Microscope, FileText, Database, Shield, Play,
  BarChart3, PieChart, TrendingUp, Star,
  Terminal, Copy, Check, RefreshCw, CheckCircle2,
  FolderOpen,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart as RePieChart, Pie, Cell, LineChart, Line, CartesianGrid,
} from 'recharts';
import DirectoryPicker from '../components/DirectoryPicker';
import { api } from '../api';

const PIE_COLORS = ['#14b8a6', '#22c55e', '#f59e0b'];

function MetricCard({ icon: Icon, label, value, accent = 'teal', trend }) {
  const accentMap = {
    teal: 'var(--accent)',
    green: 'var(--success)',
    amber: 'var(--warning)',
    rose: 'var(--danger)',
  };
  return (
    <div className="card card-hover-accent p-5">
      <div className="flex items-center gap-3 mb-3">
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center"
          style={{ background: `${accentMap[accent]}15` }}
        >
          <Icon size={18} style={{ color: accentMap[accent] }} />
        </div>
        {trend && (
          <span className={`text-xs font-semibold ${trend.direction === 'up' ? 'text-[var(--success)]' : 'text-[var(--danger)]'}`}>
            {trend.direction === 'up' ? '↑' : '↓'} {trend.value}
          </span>
        )}
      </div>
      <p className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider font-semibold">{label}</p>
      <p className="text-xl font-bold text-[var(--text-primary)] mt-1">{value}</p>
    </div>
  );
}

function ChartCard({ title, icon: Icon, children }) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-4">
        <Icon size={17} className="text-[var(--accent)]" />
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="text-[var(--text-secondary)] mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="font-semibold">
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  );
}

/* ===== Onboarding Empty State ===== */
function OnboardingEmptyState({ onStart }) {
  const steps = [
    {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
      ),
      title: 'Envie o PDF',
      desc: 'Arraste ou selecione um artigo acadêmico em PDF.',
    },
    {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75" />
        </svg>
      ),
      title: 'Configure',
      desc: 'Escolha o domínio acadêmico e a profundidade da análise.',
    },
    {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z" />
        </svg>
      ),
      title: 'Receba o Parecer',
      desc: 'Relatório detalhado com nota, slides e artefatos visuais.',
    },
  ];

  return (
    <div className="mb-8">
      {/* Main onboarding card */}
      <div className="relative overflow-hidden rounded-2xl border border-[var(--accent-border)] mb-6">
        <div className="absolute inset-0 bg-gradient-to-br from-[rgba(20,184,166,0.06)] via-transparent to-[rgba(52,211,153,0.03)] pointer-events-none" />
        <div className="absolute -top-20 -right-20 w-60 h-60 rounded-full bg-[rgba(20,184,166,0.04)] blur-3xl pointer-events-none" />

        <div className="relative p-8 sm:p-10 text-center">
          <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-emerald-400 flex items-center justify-center shadow-lg shadow-[rgba(20,184,166,0.2)]">
            <Microscope size={30} className="text-[var(--bg-primary)]" />
          </div>

          <h2 className="text-2xl sm:text-3xl font-extrabold text-[var(--text-primary)] mb-3">
            Comece sua primeira análise
          </h2>
          <p className="text-[var(--text-secondary)] text-sm max-w-lg mx-auto mb-8 leading-relaxed">
            Esta ferramenta automatiza a revisão <em>peer-review</em> de artigos acadêmicos usando
            NotebookLM. Em poucos minutos você recebe um parecer completo com 7 módulos de análise
            crítica, apresentações e artefatos visuais.
          </p>

          {/* Steps */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-2xl mx-auto mb-8">
            {steps.map((s, i) => (
              <div key={i} className="text-center">
                <div className="w-11 h-11 mx-auto mb-3 rounded-xl bg-[var(--accent-muted)] border border-[var(--accent-border)] flex items-center justify-center text-[var(--accent)]">
                  {s.icon}
                </div>
                <p className="text-sm font-semibold text-[var(--text-primary)]">{s.title}</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-1">{s.desc}</p>
              </div>
            ))}
          </div>

          <button onClick={onStart} className="btn-primary">
            <Play size={17} />
            Iniciar Nova Análise
          </button>

          <p className="text-xs text-[var(--text-muted)] mt-4">
            Grátis · Semi-automático · Google NotebookLM
          </p>
        </div>
      </div>

      {/* Preview cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { icon: '📄', label: '7 Relatórios', desc: 'Análise módulo a módulo em Markdown' },
          { icon: '📊', label: 'Slides + Infográfico', desc: 'Apresentação completa e resumo visual' },
          { icon: '📋', label: 'CSV de erros', desc: 'Tabela com página, tipo e gravidade' },
        ].map((item, i) => (
          <div key={i} className="card p-4 text-center hover:border-[var(--accent-border)] transition-all">
            <span className="text-2xl mb-2 block" aria-hidden="true">{item.icon}</span>
            <p className="text-sm font-semibold text-[var(--text-primary)]">{item.label}</p>
            <p className="text-xs text-[var(--text-tertiary)] mt-0.5">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [analyses, setAnalyses] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accountInfo, setAccountInfo] = useState({ authenticated: false });
  const [copied, setCopied] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(false);
  const [outputDir, setOutputDir] = useState(() => localStorage.getItem('analisetextos_output_dir') || '');
  const [showDirPicker, setShowDirPicker] = useState(false);
  const navigate = useNavigate();

  const handleSelectOutputDir = (dir) => {
    setOutputDir(dir);
    if (dir) {
      localStorage.setItem('analisetextos_output_dir', dir);
    } else {
      localStorage.removeItem('analisetextos_output_dir');
    }
  };

  const fetchNotebookLMInfo = async () => {
    try {
      const info = await api.notebooklmAccountInfo();
      setAccountInfo(info);
    } catch {
      setAccountInfo({ authenticated: false });
    }
  };

  const handleManualCheck = async () => {
    setCheckingAuth(true);
    await fetchNotebookLMInfo();
    setCheckingAuth(false);
  };

  const handleCopyCommand = (cmd) => {
    navigator.clipboard.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  useEffect(() => {
    Promise.all([
      api.analyses().catch(() => []),
      api.analysesStats().catch(() => null),
      api.notebooklmAccountInfo().catch(() => ({ authenticated: false })),
    ]).then(([a, s, nlm]) => {
      setAnalyses(a);
      setStats(s);
      setAccountInfo(nlm);
      setLoading(false);
    });
  }, []);

  const totalAnalyses = analyses.length;
  const totalFiles = analyses.reduce((s, a) => s + a.file_count, 0);
  const totalSize = analyses.reduce((s, a) => {
    const match = a.size.match(/^([\d.]+)\s*(KB|MB|B)/);
    if (!match) return s;
    const num = parseFloat(match[1]);
    const unit = match[2];
    return s + (unit === 'MB' ? num * 1024 : unit === 'KB' ? num : num / 1024);
  }, 0);

  const pieData = stats
    ? [
        { name: 'Com CSV', value: stats.with_csv, color: PIE_COLORS[0] },
        { name: 'Com Apresentação', value: stats.with_pres - stats.with_csv, color: PIE_COLORS[1] },
        { name: 'Só Markdown', value: stats.total - stats.with_pres, color: PIE_COLORS[2] },
      ].filter(d => d.value > 0)
    : [];

  const loginCmd = `notebooklm login${accountInfo.profile ? ` --profile ${accountInfo.profile}` : ''}`;

  return (
    <div className="animate-fade-in">
      {/* Hero Header */}
      <div className="hero-surface p-6 sm:p-8 mb-8">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_50%,rgba(20,184,166,0.1),transparent_50%)] pointer-events-none" />
        <h1 className="text-2xl sm:text-3xl font-extrabold text-[var(--text-primary)] relative z-10">
          <span aria-hidden="true">🔬</span> Análise Científica com NotebookLM
        </h1>
        <p className="text-[var(--text-secondary)] mt-2 text-sm relative z-10">
          Peer-Review Grade · Q1 / Nature / IEEE · Pre-flight OCR · Checkpoint · Domain Audit
        </p>
      </div>

      {/* NotebookLM Connection Card */}
      {!loading && (
        <div className={`p-5 mb-8 rounded-2xl border transition-all ${
          accountInfo.authenticated
            ? 'border-emerald-500/30 bg-emerald-500/5'
            : 'border-amber-500/30 bg-amber-500/5'
        }`}>
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                accountInfo.authenticated
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-amber-500/20 text-amber-400'
              }`}>
                {accountInfo.authenticated ? <CheckCircle2 size={20} /> : <Terminal size={20} />}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">
                    Motor NotebookLM
                  </h3>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    accountInfo.authenticated
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}>
                    {accountInfo.authenticated ? '● Conectado' : '● Pendente de Autenticação'}
                  </span>
                </div>

                {accountInfo.authenticated ? (
                  <p className="text-xs text-[var(--text-tertiary)] mt-1">
                    Conectado como <strong className="text-emerald-300 font-semibold">{accountInfo.account}</strong> (Perfil: <code className="text-xs text-[var(--text-primary)]">{accountInfo.profile || 'default'}</code>)
                  </p>
                ) : (
                  <p className="text-xs text-[var(--text-tertiary)] mt-1">
                    Para habilitar a análise de PDFs, autentique sua conta Google executando o comando abaixo no terminal do servidor:
                  </p>
                )}
              </div>
            </div>

            <button
              onClick={handleManualCheck}
              disabled={checkingAuth}
              className="btn-secondary text-xs flex items-center gap-1.5 shrink-0 self-end md:self-center"
              title="Checar status da autenticação"
            >
              <RefreshCw size={13} className={checkingAuth ? 'animate-spin' : ''} />
              {checkingAuth ? 'Verificando...' : 'Verificar Conexão'}
            </button>
          </div>

          {/* Terminal Command for Authentication */}
          {!accountInfo.authenticated && (
            <div className="mt-4 pt-4 border-t border-white/5 space-y-3">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                <div className="flex-1 flex items-center bg-black/50 border border-white/10 rounded-xl px-3.5 py-2.5 font-mono text-xs text-amber-300 overflow-x-auto select-all">
                  <span className="text-[var(--text-muted)] mr-2 select-none">$</span>
                  <span className="truncate">{loginCmd}</span>
                </div>
                <button
                  onClick={() => handleCopyCommand(loginCmd)}
                  className="btn-primary text-xs flex items-center justify-center gap-1.5 px-4 py-2.5 shrink-0"
                >
                  {copied ? (
                    <>
                      <Check size={14} className="text-emerald-300" />
                      <span>Copiado!</span>
                    </>
                  ) : (
                    <>
                      <Copy size={14} />
                      <span>Copiar Comando</span>
                    </>
                  )}
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-[11px] text-[var(--text-tertiary)]">
                <div className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-amber-500/20 text-amber-400 font-bold flex items-center justify-center shrink-0 text-[10px]">1</span>
                  <span>Copie o comando acima e rode no terminal da máquina/servidor.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-amber-500/20 text-amber-400 font-bold flex items-center justify-center shrink-0 text-[10px]">2</span>
                  <span>O navegador abrirá para login com sua conta Google.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-amber-500/20 text-amber-400 font-bold flex items-center justify-center shrink-0 text-[10px]">3</span>
                  <span>Clique no botão <strong>Verificar Conexão</strong> para liberar o pipeline.</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Output Directory Card */}
      {!loading && (
        <div className="card p-5 mb-8 border-[var(--border-subtle)] bg-white/[0.02]">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center shrink-0">
                <FolderOpen size={20} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">
                    Pasta de Saída das Análises
                  </h3>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    outputDir
                      ? 'bg-teal-500/20 text-teal-400 border border-teal-500/30'
                      : 'bg-white/10 text-[var(--text-muted)] border border-white/10'
                  }`}>
                    {outputDir ? 'Personalizada' : 'Padrão do Sistema'}
                  </span>
                </div>
                <div className="text-xs text-[var(--text-tertiary)] mt-1 flex flex-wrap items-center gap-1.5">
                  <span>Destino dos relatórios e slides:</span>
                  <code className="text-teal-300 font-mono text-[11px] bg-black/40 px-2 py-0.5 rounded border border-white/5 truncate max-w-md">
                    {outputDir || 'Padrão (~/Arquivos das bancas/[user_id]/peer_review_[artigo])'}
                  </code>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
              {outputDir && (
                <button
                  onClick={() => handleSelectOutputDir('')}
                  className="btn-secondary text-xs"
                  title="Restaurar para pasta padrão"
                >
                  Restaurar Padrão
                </button>
              )}
              <button
                onClick={() => setShowDirPicker(true)}
                className="btn-primary text-xs flex items-center gap-1.5"
              >
                <FolderOpen size={14} />
                {outputDir ? 'Alterar Pasta' : 'Escolher Pasta de Saída'}
              </button>
            </div>
          </div>
        </div>
      )}

      <DirectoryPicker
        isOpen={showDirPicker}
        onClose={() => setShowDirPicker(false)}
        onSelect={handleSelectOutputDir}
        currentValue={outputDir}
      />

      {/* Metrics or Onboarding */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8" aria-busy="true">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton skeleton-shimmer h-[7.5rem]" />
          ))}
        </div>
      ) : totalAnalyses === 0 ? (
        <OnboardingEmptyState onStart={() => navigate('/upload')} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard icon={Microscope} label="Análises" value={`${totalAnalyses} concluídas`} accent="teal" trend={{ value: '+3 esta semana', direction: 'up' }} />
          <MetricCard icon={FileText} label="Arquivos" value={`${totalFiles} gerados`} accent="green" trend={{ value: '+12 hoje', direction: 'up' }} />
          <MetricCard icon={Database} label="Armazenamento" value={`${totalSize.toFixed(1)} KB`} accent="amber" />
          <MetricCard icon={Shield} label="Segurança" value="Shell-safe · JWT Auth" accent="rose" />
        </div>
      )}

      {/* Charts */}
      {stats && stats.total > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">
          <ChartCard title="Análises por mês" icon={BarChart3}>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={stats.timeline}>
                <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" fill="#14b8a6" radius={[3, 3, 0, 0]} name="Análises" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Adoção de artefatos" icon={PieChart}>
            <div className="flex items-center justify-center gap-6">
              <ResponsiveContainer width="45%" height={180}>
                <RePieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={35} outerRadius={60}
                    paddingAngle={3} dataKey="value">
                    {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </RePieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {pieData.map(e => (
                  <div key={e.name} className="flex items-center gap-2 text-xs">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: e.color }} />
                    <span className="text-[var(--text-tertiary)]">{e.name}</span>
                    <span className="text-[var(--text-primary)] font-semibold">{e.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </ChartCard>

          {stats.analyses?.length > 0 && (
            <ChartCard title="Arquivos por análise" icon={TrendingUp}>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={stats.analyses.slice(0, 10)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                  <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis dataKey="name" type="category" tick={{ fill: '#64748b', fontSize: 10 }}
                    width={60} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="files" fill="#22c55e" radius={[0, 3, 3, 0]} name="Arquivos" />
                  <Bar dataKey="modules" fill="#14b8a6" radius={[0, 3, 3, 0]} name="Módulos" />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          )}

          {stats.notas?.length > 1 && (
            <ChartCard title="Notas ao longo do tempo" icon={Star}>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={stats.notas.slice().reverse()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                  <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false}
                    tickLine={false} interval="preserveStartEnd" />
                  <YAxis domain={[0, 10]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="nota" stroke="#f59e0b" strokeWidth={2}
                    dot={{ r: 4, fill: '#f59e0b' }} name="Nota" />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
          )}
        </div>
      )}

      {/* Info Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4"><span aria-hidden="true">🚀</span> Como funciona</h3>
          <div className="space-y-3">
            {[
              { num: 1, text: 'Upload — Envie seu PDF acadêmico', time: '~30s' },
              { num: 2, text: 'Configure — Escolha domínio e modo de análise', time: '~10s' },
              { num: 3, text: 'Execute — Pipeline roda 7 módulos via NotebookLM', time: '15-20min' },
              { num: 4, text: 'Resultados — Relatórios, apresentações, CSV de erros', time: '~1min' },
            ].map(({ num, text, time }) => (
              <div key={num} className="flex items-center gap-3">
                <span className="w-7 h-7 rounded-full bg-[var(--accent)] text-[var(--bg-primary)] text-xs font-bold flex items-center justify-center shrink-0">{num}</span>
                <div className="flex-1">
                  <span className="text-sm text-[var(--text-tertiary)]">{text}</span>
                </div>
                <span className="text-[10px] text-[var(--text-muted)] bg-white/5 px-2 py-0.5 rounded-full">{time}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4"><span aria-hidden="true">📦</span> O que é gerado</h3>
          <div className="space-y-2">
            {[
              { emoji: '📄', label: '7 Relatórios Markdown', desc: 'Estrutura → Metodologia → Auditoria → SOTA → Gaps → Escrita → Parecer' },
              { emoji: '📊', label: 'Apresentações PPTX', desc: 'Completa (6 slides) + Auditoria (4 slides)' },
              { emoji: '🖼️', label: 'Infográfico + Mapa Mental', desc: 'Gerados via NotebookLM artifacts' },
              { emoji: '📋', label: 'CSV de Erros', desc: 'Tabela com página, linha, tipo e gravidade' },
            ].map(({ emoji, label, desc }) => (
              <div key={label} className="p-3 rounded-lg bg-white/[0.02] border border-[var(--border-subtle)] hover:border-[var(--accent-border)] transition-all">
                <p className="text-sm font-semibold text-[var(--text-primary)]"><span aria-hidden="true">{emoji}</span> {label}</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-0.5">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA — only when there's data */}
      {!loading && totalAnalyses > 0 && (
        <div className="text-center">
          <button onClick={() => navigate('/upload')} className="btn-primary">
            <Play size={17} />
            Iniciar Nova Análise
          </button>
        </div>
      )}
    </div>
  );
}
