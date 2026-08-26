import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { History, Trash2, ExternalLink, AlertCircle, Search, ChevronLeft, ChevronRight, ArrowLeftRight } from 'lucide-react';
import { api } from '../api';
import { useToast } from '../components/Toast';

export default function HistoryPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;
  const load = () => {
    setLoading(true);
    api.analyses().then(data => {
      setAnalyses(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const filtered = analyses.filter(a =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE);
  const pageItems = filtered.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  useEffect(() => { setCurrentPage(1); }, [searchQuery]);

  const handleDelete = async (id) => {
    try {
      await api.deleteAnalysis(id);
      toast('Análise excluída.', 'success', 6000, { label: 'Ok' });
      load();
    } catch (err) {
      toast(err.message, 'error');
    }
  };

  return (
    <div className="animate-fade-in">
      <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1"><span aria-hidden="true">📚</span> Histórico de Análises</h2>

      {/* Search input */}
      {!loading && analyses.length > 0 && (
        <div className="relative mb-5">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Buscar por nome da análise…"
            className="input pl-10"
            aria-label="Buscar análises"
          />
        </div>
      )}

      {loading ? (
        <div className="space-y-3" aria-label="Carregando análises">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="skeleton skeleton-shimmer h-20 w-full" />
          ))}
        </div>
      ) : analyses.length === 0 ? (
        <div className="text-center py-16 sm:py-24 animate-fade-in">
          <div className="w-18 h-18 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-400/80 flex items-center justify-center shadow-lg shadow-[rgba(245,158,11,0.15)]" aria-hidden="true">
            <History size={32} className="text-[var(--bg-primary)]" />
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-[var(--text-primary)] mb-2">
            Nenhum histórico
          </h2>
          <p className="text-[var(--text-tertiary)] text-sm max-w-md mx-auto mb-8 leading-relaxed">
            Suas análises anteriores aparecerão aqui organizadas por data.
            Você poderá revisar relatórios, baixar artefatos e reexecutar análises.
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
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 animate-fade-in">
          <AlertCircle size={28} className="mx-auto mb-4 text-[var(--text-muted)]" aria-hidden="true" />
          <p className="text-[var(--text-secondary)] font-medium">Nenhum resultado para "{searchQuery}"</p>
          <button
            onClick={() => setSearchQuery('')}
            className="btn-ghost mt-4 text-sm"
          >
            Limpar busca
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-3" role="list" aria-label="Lista de análises">
            {pageItems.map((a, idx) => (
              <div
                key={a.id}
                className="card p-5 animate-fade-in"
                style={{ animationDelay: `${idx * 0.05}s` }}
                role="listitem"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg" aria-hidden="true">📁</span>
                      <h3 className="text-sm font-semibold text-[var(--text-primary)] truncate">{a.name}</h3>
                      <span className="text-xs text-[var(--text-muted)]">· {a.modified ? new Date(a.modified).toLocaleString('pt-BR') : ''}</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 text-xs">
                      <span className="badge badge-teal">
                        {a.file_count} arquivos
                      </span>
                      <span className="badge badge-green">
                        {a.size}
                      </span>
                      {a.modules_completed.length > 0 && (
                        <span className="badge badge-amber">
                          {a.modules_completed.length}/7 módulos
                        </span>
                      )}
                    </div>
                    {a.modules_completed.length > 0 && (
                      <div className="mt-2 flex gap-1">
                        {a.modules_completed.map(m => (
                          <span key={m} className="px-1.5 py-0.5 rounded text-[10px] bg-white/[0.03] text-[var(--text-muted)] font-mono">
                            {m}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-1.5 ml-4">
                    <button
                      onClick={() => navigate(`/compare?target=${encodeURIComponent(a.id)}`)}
                      className="btn-ghost"
                      title="Comparar com outra versão"
                      aria-label={`Comparar ${a.name}`}
                    >
                      <ArrowLeftRight size={15} />
                    </button>
                    <button
                      onClick={() => navigate(`/results?analysis=${encodeURIComponent(a.id)}`)}
                      className="btn-ghost"
                      title="Ver resultados"
                      aria-label={`Ver resultados de ${a.name}`}
                    >
                      <ExternalLink size={15} />
                    </button>
                    <button
                      onClick={() => handleDelete(a.id)}
                      className="btn-ghost hover:!text-[var(--danger)]"
                      title="Excluir"
                      aria-label={`Excluir ${a.name}`}
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <nav className="flex items-center justify-center gap-2 mt-6" aria-label="Paginação">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="btn-ghost p-2 disabled:opacity-30 disabled:cursor-not-allowed"
                aria-label="Página anterior"
              >
                <ChevronLeft size={16} />
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                <button
                  key={page}
                  onClick={() => setCurrentPage(page)}
                  className={`w-8 h-8 rounded-lg text-sm font-medium transition-all ${
                    page === currentPage
                      ? 'bg-[var(--accent)] text-[var(--bg-primary)]'
                      : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-white/[0.03]'
                  }`}
                  aria-label={`Página ${page}`}
                  aria-current={page === currentPage ? 'page' : undefined}
                >
                  {page}
                </button>
              ))}
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="btn-ghost p-2 disabled:opacity-30 disabled:cursor-not-allowed"
                aria-label="Próxima página"
              >
                <ChevronRight size={16} />
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}
