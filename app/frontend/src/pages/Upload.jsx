import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Upload as UploadIcon, FileText, Play, CheckCircle, XCircle, Loader2,
  ArrowLeft, SkipForward, Clock, FolderOpen, History, File, ChevronDown,
  ChevronRight, Zap, Timer, AlertTriangle, CheckCircle2, Rocket, Download
} from 'lucide-react';
import DirectoryPicker from '../components/DirectoryPicker';
import { api } from '../api';
import { usePipelineProgress, PIPELINE_STEPS } from '../hooks/usePipelineProgress';
import { useToast } from '../components/Toast';

/* ═══════════════════════════════════════════════════════════════
   STEP GROUP DEFINITIONS
   ═══════════════════════════════════════════════════════════════ */
const STEP_GROUPS = [
  {
    key: 'pre',
    label: 'Pré-processamento',
    icon: Zap,
    color: 'amber',
    description: 'Configuração e indexamento do documento',
  },
  {
    key: 'modules',
    label: 'Módulos de Análise',
    icon: FileText,
    color: 'accent',
    description: '8 módulos de auditoria peer-review',
  },
  {
    key: 'post',
    label: 'Geração de Artefatos',
    icon: Rocket,
    color: 'green',
    description: 'Relatórios, CSV, PDF e apresentações',
  },
];

/* ═══════════════════════════════════════════════════════════════
   ELAPSED TIME HOOK
   ═══════════════════════════════════════════════════════════════ */
function useElapsedTime(running) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(null);

  useEffect(() => {
    if (running && !startRef.current) {
      startRef.current = Date.now();
    }
    if (!running) {
      startRef.current = null;
      setElapsed(0);
      return;
    }
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [running]);

  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/* ═══════════════════════════════════════════════════════════════
   PROGRESS BAR COMPONENT
   ═══════════════════════════════════════════════════════════════ */
function ProgressBar({ stepStates, mode }) {
  const steps = PIPELINE_STEPS.filter(s => mode === 'full' || !s.lite_skip);
  const done = steps.filter(s => stepStates[s.id] === 'done').length;
  const total = steps.length;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-[var(--text-secondary)]">
          Progresso Geral
        </span>
        <span className="text-xs font-bold text-[var(--accent)]">
          {done}/{total} etapas · {pct}%
        </span>
      </div>
      <div className="h-2.5 bg-[var(--bg-primary)] rounded-full overflow-hidden border border-[var(--border-subtle)]">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${pct}%`,
            background: 'linear-gradient(90deg, var(--accent), #2dd4bf, var(--success))',
            boxShadow: '0 0 12px rgba(20, 184, 166, 0.4)',
          }}
        />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   STEP GROUP COLLAPSIBLE
   ═══════════════════════════════════════════════════════════════ */
function StepGroup({ group, steps, stepStates, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const Icon = group.icon;

  const doneCount = steps.filter(s => stepStates[s.id] === 'done').length;
  const isComplete = doneCount === steps.length && steps.length > 0;
  const hasRunning = steps.some(s => stepStates[s.id] === 'running');

  const colorMap = {
    amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', dot: 'bg-amber-400' },
    accent: { bg: 'bg-[var(--accent-muted)]', border: 'border-[var(--accent-border)]', text: 'text-[var(--accent)]', dot: 'bg-[var(--accent)]' },
    green: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  };
  const c = colorMap[group.color] || colorMap.accent;

  return (
    <div className={`rounded-xl border transition-all duration-300 ${
      hasRunning ? `${c.border} ${c.bg}` : 'border-[var(--border-subtle)] bg-white/[0.01]'
    }`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 text-left"
        aria-expanded={open}
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${c.bg} border ${c.border}`}>
            <Icon size={16} className={c.text} />
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--text-primary)]">{group.label}</p>
            <p className="text-[11px] text-[var(--text-muted)]">{group.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {isComplete ? (
            <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/15 px-2 py-0.5 rounded-full">
              <CheckCircle2 size={11} /> Concluído
            </span>
          ) : (
            <span className="text-[10px] font-semibold text-[var(--text-muted)] bg-white/5 px-2 py-0.5 rounded-full">
              {doneCount}/{steps.length}
            </span>
          )}
          {open ? (
            <ChevronDown size={16} className="text-[var(--text-muted)]" />
          ) : (
            <ChevronRight size={16} className="text-[var(--text-muted)]" />
          )}
        </div>
      </button>

      {open && (
        <div className="px-4 pb-3 space-y-0.5 animate-fade-in">
          {steps.map(step => {
            const state = stepStates[step.id] || 'pending';
            return (
              <StepRow key={step.id} step={step} state={state} />
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   INDIVIDUAL STEP ROW
   ═══════════════════════════════════════════════════════════════ */
function StepRow({ step, state }) {
  const stateConfig = {
    done: { icon: CheckCircle, color: 'text-[var(--success)]', bg: 'bg-emerald-500/5' },
    running: { icon: Loader2, color: 'text-amber-400', bg: 'bg-amber-500/10', animate: true },
    error: { icon: XCircle, color: 'text-[var(--danger)]', bg: 'bg-red-500/10' },
    skipped: { icon: SkipForward, color: 'text-[var(--text-muted)]', bg: '' },
    pending: { icon: Clock, color: 'text-[var(--text-muted)]', bg: '' },
  };
  const cfg = stateConfig[state] || stateConfig.pending;
  const Icon = cfg.icon;

  return (
    <div className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-300 ${
      state === 'running' ? cfg.bg : ''
    }`}>
      <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
        state === 'done' ? 'bg-emerald-500/20' :
        state === 'running' ? 'bg-amber-500/20' :
        state === 'error' ? 'bg-red-500/20' : 'bg-white/5'
      }`}>
        <Icon
          size={14}
          className={`${cfg.color} ${cfg.animate ? 'animate-spin' : ''}`}
        />
      </div>
      <div className="flex-1 min-w-0">
        <span className={`text-sm ${
          state === 'done' ? 'text-emerald-300' :
          state === 'running' ? 'text-amber-300 font-semibold' :
          state === 'error' ? 'text-[var(--danger)]' :
          'text-[var(--text-muted)]'
        }`}>
          {step.label}
        </span>
        {state === 'running' && (
          <span className="ml-2 text-[10px] text-amber-400/70 animate-pulse">executando...</span>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   PIPELINE RUNNING VIEW (main component)
   ═══════════════════════════════════════════════════════════════ */
function PipelineRunningView({ progress, mode, logEndRef }) {
  const elapsed = useElapsedTime(true);

  const groups = STEP_GROUPS.map(g => ({
    ...g,
    steps: PIPELINE_STEPS.filter(s => s.group === g.key && (mode === 'full' || !s.lite_skip)),
  }));

  return (
    <div className="card p-6 animate-fade-in border-amber-500/20 bg-gradient-to-br from-amber-500/5 to-transparent">
      {/* Header with timer */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Loader2 size={20} className="text-amber-400 animate-spin" />
            <div className="absolute inset-0 rounded-full bg-amber-400/20 animate-ping" />
          </div>
          <div>
            <span className="text-sm font-bold text-amber-300">Pipeline em Execução</span>
            <p className="text-[11px] text-[var(--text-muted)]">Análise científica em andamento...</p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-black/30 rounded-lg border border-white/5">
          <Timer size={14} className="text-amber-400" />
          <span className="text-sm font-mono font-bold text-amber-300">{elapsed}</span>
        </div>
      </div>

      {/* Progress Bar */}
      <ProgressBar stepStates={progress.stepStates} mode={mode} />

      {/* Step Groups */}
      <div className="space-y-3 mb-5">
        {groups.map((group, i) => (
          <StepGroup
            key={group.key}
            group={group}
            steps={group.steps}
            stepStates={progress.stepStates}
            defaultOpen={group.steps.some(s => progress.stepStates[s.id] === 'running') || i === 0}
          />
        ))}
      </div>

      {/* Logs Terminal */}
      <div className="rounded-xl overflow-hidden border border-[var(--border-subtle)]">
        <div className="flex items-center justify-between px-4 py-2 bg-black/40 border-b border-[var(--border-subtle)]">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
            </div>
            <span className="text-[10px] text-[var(--text-muted)] font-mono ml-2">pipeline.log</span>
          </div>
          <span className="text-[10px] text-[var(--text-muted)]">{progress.logs.length} linhas</span>
        </div>
        <div
          className="bg-[var(--bg-primary)] p-4 max-h-56 overflow-y-auto text-xs font-mono leading-relaxed"
          role="log"
          aria-live="polite"
        >
          {progress.logs.map((line, i) => (
            <div
              key={i}
              className={`py-0.5 ${
                line.startsWith('✅') ? 'text-emerald-400' :
                line.startsWith('❌') ? 'text-red-400' :
                line.startsWith('⚠️') ? 'text-amber-400' :
                line.startsWith('🚀') ? 'text-[var(--accent)] font-semibold' :
                line.startsWith('ℹ️') ? 'text-[var(--text-muted)]' :
                'text-[var(--text-tertiary)]'
              }`}
            >
              {line}
            </div>
          ))}
          <div ref={logEndRef} className="h-1" />
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   PIPELINE DONE VIEW
   ═══════════════════════════════════════════════════════════════ */
function PipelineDoneView({ onResults, analysisId, autoDownloading }) {
  const [showConfetti, setShowConfetti] = useState(true);
  const [manualDownloading, setManualDownloading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    const t = setTimeout(() => setShowConfetti(false), 3000);
    return () => clearTimeout(t);
  }, []);

  const handleManualDownload = async () => {
    if (!analysisId) return;
    setManualDownloading(true);
    try {
      await api.downloadAnalysisZip(analysisId);
      toast('✅ Download concluído!', 'success');
    } catch (err) {
      toast(`Erro no download: ${err.message}`, 'error');
    } finally {
      setManualDownloading(false);
    }
  };

  return (
    <div className="card p-8 animate-fade-in border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 via-teal-500/5 to-transparent text-center relative overflow-hidden">
      {/* Confetti dots */}
      {showConfetti && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          {[...Array(20)].map((_, i) => (
            <div
              key={i}
              className="absolute w-2 h-2 rounded-full animate-bounce"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                backgroundColor: ['#14b8a6', '#22c55e', '#f59e0b', '#3b82f6', '#ec4899'][i % 5],
                animationDelay: `${Math.random() * 0.5}s`,
                animationDuration: `${0.5 + Math.random() * 0.5}s`,
                opacity: 0.7,
              }}
            />
          ))}
        </div>
      )}

      <div className="relative z-10">
        <div className="w-20 h-20 mx-auto mb-5 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
          <CheckCircle2 size={40} className="text-white" />
        </div>

        <h3 className="text-2xl font-extrabold text-[var(--text-primary)] mb-2">
          Análise Concluída! 🎉
        </h3>
        <p className="text-sm text-[var(--text-secondary)] mb-2 max-w-md mx-auto">
          Todos os módulos foram executados com sucesso. Seus relatórios, apresentações e artefatos
          estão prontos para visualização.
        </p>

        {/* Download status */}
        {autoDownloading && (
          <div className="flex items-center justify-center gap-2 text-xs text-teal-400 mb-4">
            <Loader2 size={14} className="animate-spin" />
            Baixando artefatos para seu computador...
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <button onClick={onResults} className="btn-primary px-8">
            <Rocket size={17} />
            Ver Resultados
          </button>
          {analysisId && (
            <button
              onClick={handleManualDownload}
              disabled={manualDownloading}
              className="btn-secondary"
            >
              {manualDownloading ? <Loader2 size={17} className="animate-spin" /> : <Download size={17} />}
              {manualDownloading ? 'Baixando...' : 'Baixar ZIP'}
            </button>
          )}
          <button onClick={() => window.location.reload()} className="btn-secondary">
            Nova Análise
          </button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   PIPELINE ERROR VIEW
   ═══════════════════════════════════════════════════════════════ */
function PipelineErrorView({ logs }) {
  return (
    <div className="card p-6 animate-fade-in border-red-500/30 bg-gradient-to-br from-red-500/10 to-transparent">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
          <AlertTriangle size={20} className="text-red-400" />
        </div>
        <div>
          <span className="text-sm font-bold text-red-400">Erro na Execução</span>
          <p className="text-[11px] text-[var(--text-muted)]">O pipeline encontrou um problema</p>
        </div>
      </div>

      <div className="bg-[var(--bg-primary)] rounded-xl p-4 max-h-40 overflow-y-auto text-xs font-mono text-[var(--text-tertiary)] border border-red-500/10">
        {logs.map((line, i) => (
          <div key={i} className={
            line.startsWith('❌') ? 'text-red-400' :
            line.startsWith('⚠️') ? 'text-amber-400' : ''
          }>
            {line}
          </div>
        ))}
      </div>

      <button
        onClick={() => window.location.reload()}
        className="btn-secondary w-full mt-4 justify-center"
      >
        Tentar Novamente
      </button>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   MAIN UPLOAD PAGE
   ═══════════════════════════════════════════════════════════════ */
export default function UploadPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [config, setConfig] = useState(null);
  const [file, setFile] = useState(null);
  const [uploaded, setUploaded] = useState(null);
  const [domain, setDomain] = useState('cs');
  const [mode, setMode] = useState('full');
  const [force, setForce] = useState(false);
  const [outputDir, setOutputDir] = useState(() => localStorage.getItem('analisetextos_output_dir') || '');
  const [pipelineId, setPipelineId] = useState(null);
  const [analysisId, setAnalysisId] = useState(null);
  const [autoDownloading, setAutoDownloading] = useState(false);
  const [status, setStatus] = useState('idle');
  const logEndRef = useRef(null);
  const [startError, setStartError] = useState(null);
  const [showDirPicker, setShowDirPicker] = useState(false);
  const [recentUploads, setRecentUploads] = useState(() => {
    const saved = localStorage.getItem('analisetextos_recent_uploads');
    return saved ? JSON.parse(saved) : [];
  });
  const progress = usePipelineProgress();
  const toast = useToast();

  useEffect(() => {
    api.config().then(setConfig).catch(() => {});
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [progress.logs]);

  // Auto-download ZIP quando pipeline concluir com sucesso
  useEffect(() => {
    if (progress.status === 'done' && analysisId && !autoDownloading) {
      setAutoDownloading(true);
      toast('📦 Baixando artefatos automaticamente...', 'info');
      api.downloadAnalysisZip(analysisId)
        .then(() => {
          toast('✅ Artefatos baixados com sucesso!', 'success');
        })
        .catch((err) => {
          console.error('Auto-download failed:', err);
          toast('⚠️ Download automático falhou. Use o botão manual na página de resultados.', 'warning');
        });
    }
  }, [progress.status, analysisId, autoDownloading, toast]);

  const handleFileDrop = useCallback(async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      toast('Apenas arquivos PDF (.pdf) são aceitos.', 'warning');
      return;
    }
    setFile(f);
    setStatus('uploading');
    try {
      const result = await api.upload(f);
      setUploaded(result);
      setStatus('uploaded');
      const newRecent = {
        name: result.filename,
        path: result.path,
        size: result.size_mb,
        timestamp: Date.now(),
      };
      const updatedRecent = [newRecent, ...recentUploads.filter(r => r.path !== result.path)].slice(0, 5);
      setRecentUploads(updatedRecent);
      localStorage.setItem('analisetextos_recent_uploads', JSON.stringify(updatedRecent));
    } catch (err) {
      toast(err.message, 'error');
      setStatus('idle');
    }
  }, [recentUploads]);

  const handleStart = async () => {
    if (!uploaded) return;
    setStartError(null);
    try {
      const data = await api.startPipeline({
        file_path: uploaded.path,
        domain,
        mode,
        force,
        output_dir: outputDir || undefined,
      });
      setPipelineId(data.pipeline_id);
      // Extrair analysis_id do output_dir (ex: ".../peer_review_meu_artigo" → "peer_review_meu_artigo")
      if (data.output_dir) {
        const parts = data.output_dir.replace(/\/+$/, '').split('/');
        setAnalysisId(parts[parts.length - 1]);
      }
      progress.start();
    } catch (err) {
      setStartError(err.message);
    }
  };

  const estimatedTime = mode === 'full' ? '15-20 min' : '8-12 min';

  return (
    <div className="animate-fade-in">
      <button
        onClick={() => navigate('/')}
        className="btn-ghost mb-4"
      >
        <ArrowLeft size={16} aria-hidden="true" /> Voltar
      </button>

      <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">📄 Nova Análise Peer-Review</h2>
      <p className="text-sm text-[var(--text-tertiary)] mb-8">Envie um PDF acadêmico para análise completa</p>

      {/* Upload Area */}
      <div className="card p-6 sm:p-8 mb-6 text-center">
        {status === 'idle' || status === 'uploading' ? (
          <label className="cursor-pointer block">
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileDrop}
              className="hidden"
              disabled={status === 'uploading'}
            />
            <div className="flex flex-col items-center gap-3 py-8">
              <div className="w-14 h-14 rounded-xl bg-[var(--accent-muted)] border border-[var(--accent-border)] flex items-center justify-center">
                <UploadIcon size={26} className="text-[var(--accent)]" aria-hidden="true" />
              </div>
              <div>
                <p className="text-[var(--text-primary)] font-semibold">
                  {status === 'uploading' ? 'Enviando e validando PDF...' : 'Arraste ou clique para selecionar um PDF'}
                </p>
                <p className="text-xs text-[var(--text-tertiary)] mt-1">
                  PDF acadêmico · Máximo: {config?.max_upload_mb || 500} MB {config?.compress_threshold_mb ? `(otimização automática acima de ${config.compress_threshold_mb} MB)` : ''}
                </p>
              </div>
            </div>
            {status === 'idle' && recentUploads.length > 0 && (
              <div className="mt-4 pt-4 border-t border-[var(--border-subtle)]">
                <p className="text-xs text-[var(--text-muted)] mb-3 flex items-center gap-1.5">
                  <History size={12} /> Uploads recentes
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {recentUploads.slice(0, 3).map((upload, i) => (
                    <button
                      key={i}
                      onClick={async () => {
                        setFile({ name: upload.name });
                        setStatus('uploading');
                        try {
                          const result = await api.uploadFromPath(upload.path);
                          setUploaded(result);
                          setStatus('uploaded');
                        } catch (err) {
                          toast('Erro ao reenviar arquivo.', 'error');
                          setStatus('idle');
                        }
                      }}
                      className="flex items-center gap-2 px-3 py-2 bg-white/[0.03] hover:bg-white/[0.06] rounded-lg border border-[var(--border-subtle)] hover:border-[var(--accent-border)] transition-all"
                    >
                      <File size={14} className="text-[var(--accent)]" />
                      <span className="text-xs text-[var(--text-secondary)] truncate max-w-[120px]">{upload.name}</span>
                      <span className="text-[10px] text-[var(--text-muted)]">{upload.size} MB</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </label>
        ) : (
          <div className="flex flex-col sm:flex-row items-center gap-4 p-4 rounded-xl bg-[var(--success-muted)] border border-[rgba(34,197,94,0.2)]">
            <div className="flex items-center gap-4">
              <CheckCircle size={22} className="text-[var(--success)] shrink-0" aria-hidden="true" />
              <div className="text-left">
                <p className="text-[var(--success)] font-semibold text-sm">{uploaded?.filename}</p>
                <p className="text-xs text-[var(--text-tertiary)]">
                  {uploaded?.size_mb} MB · PDF válido
                  {uploaded?.was_compressed && (
                    <span className="ml-2 inline-flex items-center text-[var(--accent)] font-medium">
                      ⚡ (Otimizado de {uploaded?.original_size_mb} MB via Ghostscript)
                    </span>
                  )}
                </p>
              </div>
            </div>
            {status === 'uploaded' && (
              <button
                onClick={() => { setFile(null); setUploaded(null); setStatus('idle'); }}
                className="ml-auto text-xs text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
              >
                Remover
              </button>
            )}
          </div>
        )}
      </div>

      {/* Estimated Time */}
      {status === 'uploaded' && (
        <div className="flex items-center gap-2 text-xs text-[var(--text-tertiary)] mb-4">
          <Clock size={14} />
          <span>Tempo estimado: <strong className="text-[var(--text-secondary)]">~{estimatedTime}</strong> para modo {mode === 'full' ? 'Full' : 'Lite'}</span>
        </div>
      )}

      {/* Configuration */}
      {status === 'uploaded' && (
        <div className="card p-6 mb-6 animate-fade-in">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">⚙️ Configuração da Análise</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs text-[var(--text-tertiary)] block mb-1.5 font-medium">🎯 Domínio</label>
              <select
                value={domain}
                onChange={e => setDomain(e.target.value)}
                className="select"
              >
                {config?.domains && Object.entries(config.domains).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-[var(--text-tertiary)] block mb-1.5 font-medium">⚙️ Modo</label>
              <div className="toggle-group">
                {['full', 'lite'].map((m) => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    className={`toggle-option ${mode === m ? 'active' : ''}`}
                    aria-pressed={mode === m}
                  >
                    {m === 'full' ? '📋 Full (7 módulos)' : '⚡ Lite (5 módulos)'}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center pt-5">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={force}
                  onChange={e => setForce(e.target.checked)}
                  className="w-4 h-4 rounded accent-[var(--accent)]"
                />
                <span className="text-sm text-[var(--text-tertiary)]">🔄 Forçar re-execução</span>
              </label>
            </div>
          </div>
          <div className="mt-4">
            <label className="text-xs text-[var(--text-tertiary)] block mb-1.5 font-medium">📁 Diretório de saída</label>
            <div className="flex gap-2 items-center">
              <button
                onClick={() => setShowDirPicker(true)}
                className="btn-secondary flex-1 justify-start gap-2"
                style={{ padding: '0.5rem 0.75rem' }}
              >
                <FolderOpen size={16} className="text-[var(--accent)] shrink-0" aria-hidden="true" />
                <span className={`truncate text-left ${outputDir ? 'text-[var(--text-primary)]' : 'text-[var(--text-muted)]'}`}>
                  {outputDir
                    ? outputDir.split('/').slice(-2).join('/')
                    : uploaded
                      ? `Padrão: peer_review_${uploaded.safe_name}`
                      : 'Escolher diretório...'}
                </span>
              </button>
              {outputDir && (
                <button
                  onClick={() => setOutputDir('')}
                  className="btn-secondary text-xs"
                  title="Usar diretório padrão"
                  aria-label="Usar diretório padrão"
                >
                  Limpar
                </button>
              )}
            </div>
            {outputDir && (
              <p className="text-[11px] text-[var(--text-muted)] mt-1.5 flex items-center gap-1">
                <span className="text-[var(--accent)]">📂</span>
                <code className="text-[var(--text-tertiary)] truncate">{outputDir}</code>
              </p>
            )}
            {!outputDir && (
              <p className="text-[11px] text-[var(--text-muted)] mt-1">Clique para escolher ou deixe em branco para o padrão</p>
            )}
          </div>
          <DirectoryPicker
            isOpen={showDirPicker}
            onClose={() => setShowDirPicker(false)}
            onSelect={(path) => setOutputDir(path)}
            currentValue={outputDir}
          />
        </div>
      )}

      {/* Start Error */}
      {startError && (
        <div className="card p-4 mb-4 border-[var(--danger-muted)] animate-fade-in">
          <div className="flex items-center gap-2">
            <XCircle size={18} className="text-[var(--danger)] shrink-0" aria-hidden="true" />
            <p className="text-[var(--danger)] text-sm font-medium">{startError}</p>
          </div>
        </div>
      )}

      {/* Start Button */}
      {status === 'uploaded' && !progress.running && (
        <button
          onClick={handleStart}
          className="btn-primary btn-full"
        >
          <Play size={17} aria-hidden="true" />
          Iniciar Análise
        </button>
      )}

      {/* Running Status */}
      {progress.status === 'running' && (
        <PipelineRunningView progress={progress} mode={mode} logEndRef={logEndRef} />
      )}

      {progress.status === 'done' && (
        <PipelineDoneView
          onResults={() => navigate(analysisId ? `/results?analysis=${encodeURIComponent(analysisId)}` : '/results')}
          analysisId={analysisId}
          autoDownloading={autoDownloading}
        />
      )}

      {progress.status === 'error' && (
        <PipelineErrorView logs={progress.logs} />
      )}
    </div>
  );
}
