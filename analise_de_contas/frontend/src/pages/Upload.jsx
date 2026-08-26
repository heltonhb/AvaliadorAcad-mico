import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Upload as UploadIcon, FileText, Play, CheckCircle, XCircle, Loader2, ArrowLeft, SkipForward, Clock, FolderOpen } from 'lucide-react';
import DirectoryPicker from '../components/DirectoryPicker';
import { api } from '../api';
import { usePipelineProgress, PIPELINE_STEPS } from '../hooks/usePipelineProgress';
import { useToast } from '../components/Toast';


export default function UploadPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [config, setConfig] = useState(null);
  const [file, setFile] = useState(null);
  const [uploaded, setUploaded] = useState(null);
  const [domain, setDomain] = useState('res');
  const [mode, setMode] = useState('full');
  const [force, setForce] = useState(false);
  const [outputDir, setOutputDir] = useState('');
  const [pipelineId, setPipelineId] = useState(null);
  const [status, setStatus] = useState('idle');
  const logEndRef = useRef(null);
  const [startError, setStartError] = useState(null);
  const [showDirPicker, setShowDirPicker] = useState(false);
  const progress = usePipelineProgress();
  const toast = useToast();

  useEffect(() => {
    api.config().then(setConfig).catch(() => {});
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [progress.logs]);

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
    } catch (err) {
      toast(err.message, 'error');
      setStatus('idle');
    }
  }, []);

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
      progress.start();
    } catch (err) {
      setStartError(err.message);
    }
  };

  return (
    <div className="animate-fade-in">
      <button
        onClick={() => navigate('/')}
        className="btn-ghost mb-4"
      >
        <ArrowLeft size={16} aria-hidden="true" /> Voltar
      </button>

      <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">📄 Nova Auditoria Condominial</h2>
      <p className="text-sm text-[var(--text-tertiary)] mb-8">Envie uma prestação de contas em PDF para auditoria completa</p>

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
                  Prestação de contas em PDF · Máximo: {config?.max_upload_mb || 500} MB {config?.compress_threshold_mb ? `(otimização automática acima de ${config.compress_threshold_mb} MB)` : ''}
                </p>
              </div>
            </div>
          </label>
        ) : (
          <div className="flex items-center gap-4 p-4 rounded-xl bg-[var(--success-muted)] border border-[rgba(34,197,94,0.2)]">
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

      {/* Configuration */}
      {status === 'uploaded' && (
        <div className="card p-6 mb-6 animate-fade-in">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">⚙️ Configuração da Análise</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs text-[var(--text-tertiary)] block mb-1.5 font-medium">🎯 Tipo de Condomínio</label>
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
        <div className="card p-6 animate-fade-in">
          <div className="flex items-center gap-3 mb-4">
            <Loader2 size={18} className="text-[var(--warning)] animate-spin" aria-hidden="true" />
            <span className="text-[var(--warning)] font-semibold text-sm">Pipeline em execução</span>
          </div>

          {/* Step Tracker */}
          <div className="mb-5 space-y-0.5">
            {PIPELINE_STEPS.filter(s => mode === 'full' || !s.lite_skip).map((step) => {
              const state = progress.stepStates[step.id] || 'pending';
              const isRunning = state === 'running';
              return (
                <div key={step.id} className={`flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm transition-all ${
                  isRunning ? 'bg-[var(--accent-muted)]' : ''
                }`}>
                  {state === 'done' && <CheckCircle size={15} className="text-[var(--success)] shrink-0" aria-hidden="true" />}
                  {state === 'running' && <Loader2 size={15} className="text-[var(--warning)] animate-spin shrink-0" aria-hidden="true" />}
                  {state === 'error' && <XCircle size={15} className="text-[var(--danger)] shrink-0" aria-hidden="true" />}
                  {state === 'skipped' && <SkipForward size={15} className="text-[var(--text-muted)] shrink-0" aria-hidden="true" />}
                  {state === 'pending' && <Clock size={15} className="text-[var(--text-muted)] shrink-0" aria-hidden="true" />}
                  <span className={`${
                    state === 'done' ? 'text-[var(--success)]' :
                    state === 'running' ? 'text-[var(--warning)] font-medium' :
                    state === 'error' ? 'text-[var(--danger)]' :
                    state === 'skipped' ? 'text-[var(--text-muted)]' :
                    'text-[var(--text-muted)]'
                  }`}>
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Logs */}
          <div className="bg-[var(--bg-primary)] rounded-xl p-4 max-h-48 overflow-y-auto text-xs font-mono text-[var(--text-tertiary)]" role="log" aria-live="polite">
            {progress.logs.map((line, i) => (
              <div key={i} className={
                line.startsWith('✅') ? 'text-[var(--success)]' :
                line.startsWith('❌') ? 'text-[var(--danger)]' :
                line.startsWith('⚠️') ? 'text-[var(--warning)]' : ''
              }>
                {line}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      )}

      {progress.status === 'done' && (
        <div className="card p-6 animate-fade-in border-[var(--success-muted)]">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle size={22} className="text-[var(--success)]" aria-hidden="true" />
            <span className="text-[var(--success)] font-bold text-lg">Análise concluída!</span>
          </div>
          <button
            onClick={() => navigate('/results')}
            className="btn-primary btn-full"
          >
            Ver Resultados
          </button>
        </div>
      )}

      {progress.status === 'error' && (
        <div className="card p-6 animate-fade-in border-[var(--danger-muted)]">
          <div className="flex items-center gap-3 mb-4">
            <XCircle size={22} className="text-[var(--danger)]" aria-hidden="true" />
            <span className="text-[var(--danger)] font-bold text-lg">Erro na execução</span>
          </div>
          <div className="bg-[var(--bg-primary)] rounded-xl p-4 max-h-40 overflow-y-auto text-xs font-mono text-[var(--text-tertiary)]" role="log" aria-live="polite">
            {progress.logs.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
