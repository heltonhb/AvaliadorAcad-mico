import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { BarChart3, FileText, Download, AlertCircle, Play, Eye, Maximize2, Search, Filter, Sparkles, CheckCircle2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from '../api';

export default function Results() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialAnalysis = searchParams.get('analysis');
  const [analyses, setAnalyses] = useState([]);
  const [selectedId, setSelectedId] = useState(initialAnalysis || null);
  const [analysisDetail, setAnalysisDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('reports');

  useEffect(() => {
    api.analyses().then(data => {
      setAnalyses(data);
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedId) {
      api.analysis(selectedId).then(setAnalysisDetail).catch(() => {});
    }
  }, [selectedId]);

  const mdFiles = analysisDetail?.files?.filter(f => f.extension === 'md') || [];
  const presFiles = analysisDetail?.files?.filter(f => ['pdf', 'pptx', 'html'].includes(f.extension)) || [];
  const imgFiles = analysisDetail?.files?.filter(f => ['png', 'jpg', 'jpeg'].includes(f.extension)) || [];
  const csvFiles = analysisDetail?.files?.filter(f => f.extension === 'csv') || [];

  if (loading) {
    return (
      <div className="animate-fade-in space-y-4" aria-busy="true">
        <div className="skeleton skeleton-shimmer h-7 w-48" />
        <div className="skeleton skeleton-shimmer h-11 w-full" />
        <div className="skeleton skeleton-shimmer h-64 w-full" />
      </div>
    );
  }

  if (analyses.length === 0) {
    return (
      <div className="animate-fade-in text-center py-16 sm:py-24">
        <div aria-hidden="true" className="w-18 h-18 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-emerald-400/80 flex items-center justify-center shadow-lg shadow-[rgba(20,184,166,0.15)]">
          <BarChart3 size={32} className="text-[var(--bg-primary)]" />
        </div>

        <h2 className="text-xl sm:text-2xl font-bold text-[var(--text-primary)] mb-2">
          Nenhum resultado ainda
        </h2>
        <p className="text-[var(--text-tertiary)] text-sm max-w-md mx-auto mb-8 leading-relaxed">
          Os resultados das auditorias aparecem aqui. Faça o upload de uma prestação de contas
          para gerar relatórios, apresentações e artefatos automaticamente.
        </p>

        <div className="flex items-center justify-center gap-3">
          <button onClick={() => navigate('/upload')} className="btn-primary">
            + Nova Análise
          </button>
          <button onClick={() => navigate('/')} className="btn-secondary">
            Ir para Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1 flex items-center gap-2">
            <span>📊</span> Resultados da Análise
          </h2>
          <p className="text-sm text-[var(--text-tertiary)]">Visualize relatórios técnicos, apresentações e auditorias</p>
        </div>
        <button
          onClick={() => navigate(`/compare?target=${encodeURIComponent(selectedId || '')}`)}
          className="btn-secondary text-xs flex items-center gap-1.5"
        >
          <span>🔄</span> Comparar com outra versão
        </button>
      </div>

      {/* Analysis Selector */}
      <div className="card p-4">
        <select
          value={selectedId || ''}
          onChange={e => setSelectedId(e.target.value)}
          className="w-full bg-transparent text-[var(--text-primary)] text-sm focus:outline-none cursor-pointer"
          aria-label="Selecionar análise"
        >
          {analyses.map(a => (
            <option key={a.id} value={a.id} className="bg-[var(--bg-surface)]">
              📁 {a.name} · {a.file_count} arquivos · {a.size}
            </option>
          ))}
        </select>
      </div>

      {analysisDetail && (
        <>
          <div className="flex items-center gap-2 text-sm text-[var(--text-tertiary)]">
            <FileText size={14} aria-hidden="true" />
            <span>{analysisDetail.file_count} arquivos gerados · Modificado em {new Date(analysisDetail.modified).toLocaleString('pt-BR')}</span>
          </div>

          {/* Tabs */}
          <div role="tablist" aria-label="Navegação por abas" className="flex gap-1 p-1 rounded-xl bg-[var(--bg-surface)] border border-[var(--border-subtle)]">
            {[
              { key: 'reports', icon: '📄', label: 'Relatórios Técnicos', count: mdFiles.length },
              { key: 'presentations', icon: '📊', label: 'Apresentações & Parecer', count: presFiles.length },
              { key: 'artifacts', icon: '🖼️', label: 'Artefatos Visuais', count: imgFiles.length },
              { key: 'csv', icon: '📋', label: 'Tabela de Erros', count: csvFiles.length },
            ].map(({ key, icon, label, count }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  activeTab === key
                    ? 'bg-[var(--accent-muted)] text-[var(--accent)]'
                    : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
                }`}
                role="tab"
                aria-selected={activeTab === key}
              >
                <span aria-hidden="true">{icon}</span> {label} ({count})
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="card p-6" aria-live="polite">
            {activeTab === 'reports' && (
              <div role="tabpanel" aria-label="Relatórios" className="space-y-4">
                {mdFiles.length > 0 ? (
                  mdFiles.map(f => (
                    <RichReportCard key={f.name} file={f} analysisId={selectedId} />
                  ))
                ) : (
                  <EmptyMessage msg="Nenhum relatório Markdown encontrado." />
                )}
              </div>
            )}

            {activeTab === 'presentations' && (
              <div role="tabpanel" aria-label="Apresentações" className="space-y-6">
                {presFiles.length > 0 ? (
                  <PresentationsTab files={presFiles} selectedId={selectedId} />
                ) : (
                  <EmptyMessage msg="Nenhuma apresentação encontrada." />
                )}
              </div>
            )}

            {activeTab === 'artifacts' && (
              <div role="tabpanel" aria-label="Artefatos">
                {imgFiles.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {imgFiles.map(f => (
                      <div key={f.name} className="card p-3 space-y-2 border border-[var(--border-subtle)]">
                        <div className="overflow-hidden rounded-lg bg-black/40 flex items-center justify-center p-2">
                          <img
                            src={`/api/analyses/${selectedId}/files/${f.name}`}
                            alt={f.name}
                            className="w-full max-h-[480px] object-contain rounded-lg hover:scale-105 transition-transform duration-300"
                          />
                        </div>
                        <div className="flex items-center justify-between pt-1">
                          <span className="text-xs font-semibold text-[var(--text-primary)]">{f.name}</span>
                          <a
                            href={`/api/analyses/${selectedId}/files/${f.name}`}
                            download={f.name}
                            className="btn-ghost text-xs"
                          >
                            <Download size={14} /> Download
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyMessage msg="Nenhum artefato visual encontrado." />
                )}
              </div>
            )}

            {activeTab === 'csv' && (
              <div role="tabpanel" aria-label="CSV">
                {csvFiles.length > 0 ? (
                  <InteractiveCsvViewer file={csvFiles[0]} analysisId={selectedId} />
                ) : (
                  <EmptyMessage msg="Nenhum arquivo CSV de erros encontrado." />
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

/* ===== Rich Markdown Report Card ===== */
function RichReportCard({ file, analysisId }) {
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);

  const loadContent = async () => {
    if (content) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/analyses/${analysisId}/files/${file.name}`);
      const data = await res.json();
      setContent(data.content || 'Sem conteúdo.');
    } catch {
      setContent('Erro ao carregar conteúdo do relatório.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-white/[0.01] overflow-hidden">
      <button
        onClick={() => {
          setOpen(!open);
          if (!open) loadContent();
        }}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-white/[0.02] transition-colors"
        aria-expanded={open}
      >
        <div className="flex items-center gap-3">
          <FileText size={18} className="text-[var(--accent)]" />
          <div>
            <span className="text-sm font-semibold text-[var(--text-primary)] block">{file.name}</span>
            <span className="text-xs text-[var(--text-muted)]">{file.size_formatted}</span>
          </div>
        </div>
        <span className={`text-[var(--text-muted)] transition-transform duration-200 ${open ? 'rotate-180' : ''}`}>▼</span>
      </button>

      {open && (
        <div className="p-5 border-t border-[var(--border-subtle)] bg-[var(--bg-primary)]">
          {loading ? (
            <div className="skeleton skeleton-shimmer h-32 w-full" />
          ) : (
            <div className="prose prose-invert max-w-none text-sm leading-relaxed space-y-3 text-[var(--text-secondary)]">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => <h1 className="text-lg font-bold text-[var(--accent)] border-b border-[var(--border-subtle)] pb-2">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-bold text-[var(--text-primary)] pt-3">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-semibold text-teal-300 pt-2">{children}</h3>,
                  ul: ({ children }) => <ul className="list-disc pl-5 space-y-1 my-2">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1 my-2">{children}</ol>,
                  li: ({ children }) => <li className="text-[var(--text-secondary)]">{children}</li>,
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-3">
                      <table className="min-w-full text-xs border border-[var(--border-subtle)] rounded-lg overflow-hidden">{children}</table>
                    </div>
                  ),
                  thead: ({ children }) => <thead className="bg-[var(--bg-surface)] text-[var(--text-primary)] font-bold">{children}</thead>,
                  th: ({ children }) => <th className="border border-[var(--border-subtle)] px-3 py-2 text-left">{children}</th>,
                  td: ({ children }) => <td className="border border-[var(--border-subtle)] px-3 py-2">{children}</td>,
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-[var(--accent)] bg-[var(--accent-muted)] p-3 rounded-r-lg italic my-2">
                      {children}
                    </blockquote>
                  ),
                  code: ({ inline, children }) => (
                    inline ? (
                      <code className="bg-white/10 px-1.5 py-0.5 rounded text-xs text-amber-300 font-mono">{children}</code>
                    ) : (
                      <pre className="bg-black/60 p-3 rounded-lg overflow-x-auto text-xs text-emerald-400 font-mono my-2">{children}</pre>
                    )
                  ),
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ===== Presentations & Interactive Player Tab ===== */
function PresentationsTab({ files, selectedId }) {
  const [activeHtmlFile, setActiveHtmlFile] = useState(null);

  const htmlFile = files.find(f => f.extension === 'html');
  const officialPdf = files.find(f => f.name === 'parecer_auditoria_oficial.pdf');
  const slidePdfs = files.filter(f => f.name !== 'parecer_auditoria_oficial.pdf');

  return (
    <div className="space-y-6">
      {/* Official Examination Board PDF Highlight */}
      {officialPdf && (
        <div className="p-5 rounded-xl border border-teal-500/30 bg-gradient-to-r from-teal-500/10 via-emerald-500/5 to-transparent flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center font-bold text-xl">
              📑
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="badge badge-teal font-semibold">Oficial da Auditoria</span>
                <span className="text-xs text-[var(--text-muted)]">{officialPdf.size_formatted}</span>
              </div>
              <h3 className="text-base font-bold text-[var(--text-primary)] mt-0.5">Parecer Técnico Oficial em PDF</h3>
              <p className="text-xs text-[var(--text-tertiary)]">Pronto para impressão e apresentação em assembleia</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={`/api/analyses/${selectedId}/files/${officialPdf.name}`}
              target="_blank"
              rel="noreferrer"
              className="btn-secondary text-xs"
            >
              <Eye size={15} /> Visualizar
            </a>
            <a
              href={`/api/analyses/${selectedId}/files/${officialPdf.name}`}
              download={officialPdf.name}
              className="btn-primary text-xs"
            >
              <Download size={15} /> Baixar Parecer
            </a>
          </div>
        </div>
      )}

      {/* Interactive HTML Presentation Viewer */}
      {htmlFile && (
        <div className="card p-5 border-[var(--accent-border)] bg-black/20 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <Play size={18} className="text-[var(--accent)]" />
              <h3 className="text-sm font-bold text-[var(--text-primary)]">Apresentação Animada Interativa (MIRA Engine)</h3>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveHtmlFile(activeHtmlFile ? null : htmlFile.name)}
                className="btn-primary text-xs flex items-center gap-1.5"
              >
                {activeHtmlFile ? 'Fechar Player' : '▶ Executar Player Inline'}
              </button>
              <a
                href={`/api/analyses/${selectedId}/files/${htmlFile.name}`}
                target="_blank"
                rel="noreferrer"
                className="btn-ghost text-xs"
                title="Abrir em nova aba"
              >
                <Maximize2 size={15} /> Tela Cheia
              </a>
            </div>
          </div>

          {activeHtmlFile && (
            <div className="rounded-xl overflow-hidden border border-[var(--border-subtle)] shadow-2xl bg-black animate-fade-in">
              <iframe
                src={`/api/analyses/${selectedId}/files/${htmlFile.name}`}
                title="MIRA Interactive Presentation"
                className="w-full h-[600px] border-0"
                sandbox="allow-scripts allow-same-origin"
              />
            </div>
          )}
        </div>
      )}

      {/* Other presentation files */}
      <div className="space-y-3">
        <h4 className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">Outros Arquivos de Slides</h4>
        {slidePdfs.map(f => (
          <div key={f.name} className="flex items-center justify-between p-4 rounded-xl border border-[var(--border-subtle)] bg-white/[0.01] hover:border-[var(--accent-border)] transition-all">
            <div className="flex items-center gap-3">
              <span className="text-xl">{f.icon}</span>
              <div>
                <p className="text-sm font-semibold text-[var(--text-primary)]">{f.name}</p>
                <p className="text-xs text-[var(--text-tertiary)]">{f.size_formatted}</p>
              </div>
            </div>
            <a
              href={`/api/analyses/${selectedId}/files/${f.name}`}
              download={f.name}
              className="btn-ghost"
              title="Baixar arquivo"
            >
              <Download size={16} />
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ===== Interactive CSV Viewer Tab ===== */
function InteractiveCsvViewer({ file, analysisId }) {
  const [rows, setRows] = useState([]);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('ALL');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/analyses/${analysisId}/files/${file.name}`)
      .then(res => res.json())
      .then(data => {
        setRows(data.rows || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [analysisId, file.name]);

  if (loading) return <div className="skeleton skeleton-shimmer h-48 w-full" />;

  if (!rows || rows.length === 0) {
    return <EmptyMessage msg="Nenhum dado encontrado na tabela de erros." />;
  }

  const headers = rows[0] || [];
  const bodyRows = rows.slice(1);

  const errorTypes = Array.from(new Set(bodyRows.map(r => r[1] || 'Geral'))).filter(Boolean);

  const filtered = bodyRows.filter(row => {
    const textMatch = search ? row.some(cell => String(cell).toLowerCase().includes(search.toLowerCase())) : true;
    const typeMatch = filterType === 'ALL' || (row[1] && row[1].toLowerCase().includes(filterType.toLowerCase()));
    return textMatch && typeMatch;
  });

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-[240px]">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar por seção ou trecho..."
              className="input pl-9 text-xs"
            />
          </div>
          <select
            value={filterType}
            onChange={e => setFilterType(e.target.value)}
            className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-xs text-[var(--text-primary)]"
          >
            <option value="ALL">Todos os Tipos de Erro ({bodyRows.length})</option>
            {errorTypes.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <a
          href={`/api/analyses/${analysisId}/files/${file.name}`}
          download={file.name}
          className="btn-secondary text-xs flex items-center gap-1.5"
        >
          <Download size={14} /> Baixar CSV ({bodyRows.length} linhas)
        </a>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-primary)]">
        <table className="min-w-full text-xs text-left">
          <thead className="bg-[var(--bg-surface)] text-[var(--text-primary)] font-semibold border-b border-[var(--border-subtle)]">
            <tr>
              {headers.map((h, i) => (
                <th key={i} className="px-4 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-subtle)] text-[var(--text-secondary)]">
            {filtered.map((row, idx) => (
              <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                <td className="px-4 py-3 font-semibold text-[var(--text-primary)] whitespace-nowrap">{row[0]}</td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="badge badge-amber text-[10px]">{row[1] || 'Geral'}</span>
                </td>
                <td className="px-4 py-3 text-rose-300 font-mono italic">{row[2]}</td>
                <td className="px-4 py-3 text-emerald-300 font-mono">{row[3]}</td>
                {row.slice(4).map((cell, i) => (
                  <td key={i} className="px-4 py-3">{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EmptyMessage({ msg }) {
  return (
    <div className="text-center py-12">
      <AlertCircle size={28} className="text-[var(--text-muted)] mx-auto mb-3" aria-hidden="true" />
      <p className="text-sm text-[var(--text-tertiary)]">{msg}</p>
    </div>
  );
}
