import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeftRight, TrendingUp, TrendingDown, CheckCircle2, AlertTriangle, FileText, Sparkles, BookOpen } from 'lucide-react';
import { api } from '../api';

export default function ComparePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [analyses, setAnalyses] = useState([]);
  const [baseId, setBaseId] = useState(searchParams.get('base') || '');
  const [targetId, setTargetId] = useState(searchParams.get('target') || '');
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.analyses().then(data => {
      setAnalyses(data);
      if (data.length >= 2) {
        if (!baseId) setBaseId(data[1].id);
        if (!targetId) setTargetId(data[0].id);
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (baseId && targetId && baseId !== targetId) {
      setLoading(true);
      setError(null);
      api.compareAnalyses(baseId, targetId)
        .then(res => {
          setComparison(res);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message);
          setLoading(false);
        });
    } else if (baseId && targetId && baseId === targetId) {
      setError('Selecione duas análises diferentes para comparar.');
      setComparison(null);
    }
  }, [baseId, targetId]);

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1 flex items-center gap-2">
          <ArrowLeftRight className="text-[var(--accent)]" size={22} />
          Comparativo de Períodos (P1 vs. P2)
        </h2>
        <p className="text-sm text-[var(--text-tertiary)]">
          Compare a evolução entre períodos de prestação de contas do mesmo condomínio.
        </p>
      </div>

      {/* Selectors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card p-4">
          <label className="block text-xs font-semibold text-[var(--text-tertiary)] uppercase mb-2">
            1️⃣ Período Base (ex: P1 / 1º Semestre)
          </label>
          <select
            value={baseId}
            onChange={e => setBaseId(e.target.value)}
            className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
          >
            <option value="">Selecione uma análise...</option>
            {analyses.map(a => (
              <option key={`base-${a.id}`} value={a.id}>
                {a.name} ({a.modified ? new Date(a.modified).toLocaleDateString('pt-BR') : ''})
              </option>
            ))}
          </select>
        </div>

        <div className="card p-4">
          <label className="block text-xs font-semibold text-[var(--text-tertiary)] uppercase mb-2">
            2️⃣ Período Comparado (ex: P2 / 2º Semestre)
          </label>
          <select
            value={targetId}
            onChange={e => setTargetId(e.target.value)}
            className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
          >
            <option value="">Selecione uma análise...</option>
            {analyses.map(a => (
              <option key={`target-${a.id}`} value={a.id}>
                {a.name} ({a.modified ? new Date(a.modified).toLocaleDateString('pt-BR') : ''})
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm flex items-center gap-2">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="space-y-4">
          <div className="skeleton skeleton-shimmer h-24 w-full" />
          <div className="skeleton skeleton-shimmer h-64 w-full" />
        </div>
      )}

      {comparison && !loading && (
        <div className="space-y-6 animate-fade-in">
          {/* Executive Delta Card */}
          <div className="card p-6 border-l-4 border-l-[var(--accent)] bg-gradient-to-r from-teal-500/5 to-transparent">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
              <div>
                <span className="text-xs font-bold text-[var(--accent)] uppercase tracking-wider">Resumo Executivo da Evolução</span>
                <h3 className="text-lg font-bold text-[var(--text-primary)] mt-0.5">
                  {comparison.base.name} ➔ {comparison.target.name}
                </h3>
              </div>
              <div className="flex items-center gap-3">
                {comparison.comparison.delta_nota !== null && (
                  <div className={`px-3 py-1.5 rounded-xl text-sm font-bold flex items-center gap-1.5 ${
                    comparison.comparison.delta_nota >= 0
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                      : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                  }`}>
                    {comparison.comparison.delta_nota >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                    <span>{comparison.comparison.delta_nota >= 0 ? `+${comparison.comparison.delta_nota}` : comparison.comparison.delta_nota} pts</span>
                  </div>
                )}
                {comparison.comparison.delta_erros !== 0 && (
                  <div className={`px-3 py-1.5 rounded-xl text-xs font-bold ${
                    comparison.comparison.delta_erros < 0
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}>
                    {comparison.comparison.delta_erros < 0 ? `${comparison.comparison.delta_erros} erros corrigidos` : `+${comparison.comparison.delta_erros} erros`}
                  </div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-[var(--border-subtle)]">
              <div>
                <p className="text-xs text-[var(--text-tertiary)]">Nota Final</p>
                <p className="text-lg font-bold text-[var(--text-primary)]">
                  {comparison.base.nota !== null ? `${comparison.base.nota}/10` : 'N/D'} ➔{' '}
                  <span className="text-[var(--accent)]">
                    {comparison.target.nota !== null ? `${comparison.target.nota}/10` : 'N/D'}
                  </span>
                </p>
              </div>
              <div>
                <p className="text-xs text-[var(--text-tertiary)]">Decisão Editorial</p>
                <p className="text-sm font-semibold text-[var(--text-primary)]">
                  {comparison.base.decisao} ➔ <span className="text-emerald-400">{comparison.target.decisao}</span>
                </p>
              </div>
              <div>
                <p className="text-xs text-[var(--text-tertiary)]">Erros Textuais (CSV)</p>
                <p className="text-lg font-bold text-[var(--text-primary)]">
                  {comparison.base.erros_count} ➔ {comparison.target.erros_count}
                </p>
              </div>
            </div>
          </div>

          {/* Side by side comparison cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Base Card */}
            <div className="card p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)]">
                <div>
                  <span className="text-xs text-[var(--text-muted)] font-mono">VERSÃO BASE (V1)</span>
                  <h4 className="text-base font-bold text-[var(--text-primary)]">{comparison.base.name}</h4>
                </div>
                <span className="text-xl font-extrabold text-[var(--text-secondary)]">
                  {comparison.base.nota !== null ? `${comparison.base.nota}` : 'N/D'}
                </span>
              </div>

              <div>
                <p className="text-xs font-semibold text-[var(--text-tertiary)] uppercase mb-2">Pontos Fortes</p>
                {comparison.base.fortes?.length > 0 ? (
                  <ul className="space-y-1.5 text-xs text-[var(--text-secondary)]">
                    {comparison.base.fortes.map((f, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-[var(--text-muted)]">Nenhum registrado.</p>
                )}
              </div>

              <div>
                <p className="text-xs font-semibold text-[var(--text-tertiary)] uppercase mb-2">Fragilidades</p>
                {comparison.base.fragilidades?.length > 0 ? (
                  <ul className="space-y-1.5 text-xs text-[var(--text-secondary)]">
                    {comparison.base.fragilidades.map((f, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <AlertTriangle size={14} className="text-rose-400 shrink-0 mt-0.5" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-[var(--text-muted)]">Nenhuma registrada.</p>
                )}
              </div>
            </div>

            {/* Target Card */}
            <div className="card p-5 space-y-4 border-[var(--accent-border)] bg-white/[0.01]">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)]">
                <div>
                  <span className="text-xs text-[var(--accent)] font-mono">VERSÃO ATUALIZADA (V2)</span>
                  <h4 className="text-base font-bold text-[var(--text-primary)]">{comparison.target.name}</h4>
                </div>
                <span className="text-xl font-extrabold text-[var(--accent)]">
                  {comparison.target.nota !== null ? `${comparison.target.nota}` : 'N/D'}
                </span>
              </div>

              <div>
                <p className="text-xs font-semibold text-[var(--text-tertiary)] uppercase mb-2">Pontos Fortes</p>
                {comparison.target.fortes?.length > 0 ? (
                  <ul className="space-y-1.5 text-xs text-[var(--text-secondary)]">
                    {comparison.target.fortes.map((f, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-[var(--text-muted)]">Nenhum registrado.</p>
                )}
              </div>

              <div>
                <p className="text-xs font-semibold text-[var(--text-tertiary)] uppercase mb-2">Fragilidades</p>
                {comparison.target.fragilidades?.length > 0 ? (
                  <ul className="space-y-1.5 text-xs text-[var(--text-secondary)]">
                    {comparison.target.fragilidades.map((f, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <AlertTriangle size={14} className="text-rose-400 shrink-0 mt-0.5" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-[var(--text-muted)]">Nenhuma registrada.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
