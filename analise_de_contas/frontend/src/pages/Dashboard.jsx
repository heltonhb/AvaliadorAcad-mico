import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2, FileText, Database, Shield, Play,
  BarChart3, PieChart, TrendingUp, Star,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart as RePieChart, Pie, Cell, LineChart, Line, CartesianGrid,
} from 'recharts';
import { api } from '../api';

const PIE_COLORS = ['#14b8a6', '#22c55e', '#f59e0b'];

function MetricCard({ icon: Icon, label, value, accent = 'teal' }) {
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
      desc: 'Arraste ou selecione uma prestação de contas em PDF.',
    },
    {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75" />
        </svg>
      ),
      title: 'Configure',
      desc: 'Escolha o tipo de condomínio e a profundidade da auditoria.',
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
            <Building2 size={30} className="text-[var(--bg-primary)]" />
          </div>

          <h2 className="text-2xl sm:text-3xl font-extrabold text-[var(--text-primary)] mb-3">
            Comece sua primeira análise
          </h2>
          <p className="text-[var(--text-secondary)] text-sm max-w-lg mx-auto mb-8 leading-relaxed">
            Esta ferramenta automatiza a auditoria de contas condominiais usando
            NotebookLM. Em poucos minutos você recebe um parecer completo com 8 módulos de análise
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
          { icon: '📄', label: '8 Relatórios', desc: 'Análise módulo a módulo em Markdown' },
          { icon: '📊', label: 'Slides + Infográfico', desc: 'Apresentação completa e resumo visual' },
          { icon: '📋', label: 'CSV de inconsistências', desc: 'Tabela com seção, tipo e gravidade' },
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
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      api.analyses().catch(() => []),
      api.analysesStats().catch(() => null),
    ]).then(([a, s]) => {
      setAnalyses(a);
      setStats(s);
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

  return (
    <div className="animate-fade-in">
      {/* Hero Header */}
      <div className="hero-surface p-6 sm:p-8 mb-8">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_50%,rgba(20,184,166,0.1),transparent_50%)] pointer-events-none" />
        <h1 className="text-2xl sm:text-3xl font-extrabold text-[var(--text-primary)] relative z-10">
          <span aria-hidden="true">🏢</span> Auditoria de Contas Condominiais
        </h1>
        <p className="text-[var(--text-secondary)] mt-2 text-sm relative z-10">
          Lei 4.591/64 · Pre-flight OCR · Checkpoint · Auditoria Financeira · Parecer Oficial
        </p>
      </div>

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
          <MetricCard icon={Building2} label="Auditorias" value={`${totalAnalyses} concluídas`} accent="teal" />
          <MetricCard icon={FileText} label="Arquivos" value={`${totalFiles} gerados`} accent="green" />
          <MetricCard icon={Database} label="Armazenamento" value={`${totalSize.toFixed(1)} KB`} accent="amber" />
          <MetricCard icon={Shield} label="Segurança" value="Shell-safe · Auth" accent="rose" />
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
              { num: 1, text: 'Upload — Envie sua prestação de contas em PDF' },
              { num: 2, text: 'Configure — Escolha tipo de condomínio e modo' },
              { num: 3, text: 'Execute — Pipeline roda 8 módulos via NotebookLM' },
              { num: 4, text: 'Resultados — Relatórios, apresentações, CSV de inconsistências' },
            ].map(({ num, text }) => (
              <div key={num} className="flex items-center gap-3">
                <span className="w-7 h-7 rounded-full bg-[var(--accent)] text-[var(--bg-primary)] text-xs font-bold flex items-center justify-center shrink-0">{num}</span>
                <span className="text-sm text-[var(--text-tertiary)]">{text}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4"><span aria-hidden="true">📦</span> O que é gerado</h3>
          <div className="space-y-2">
            {[
              { emoji: '📄', label: '8 Relatórios Markdown', desc: 'Estrutura → Receitas → Legal → Despesas → Consistência → Qualidade → Parecer → Quantitativo' },
              { emoji: '📊', label: 'Apresentações PPTX', desc: 'Completa + Auditoria (15 slides para assembleia)' },
              { emoji: '🖼️', label: 'Infográfico + HTML Animado', desc: 'Gerados via NotebookLM artifacts' },
              { emoji: '📋', label: 'CSV de Inconsistências', desc: 'Tabela com seção, linha, tipo e gravidade' },
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
