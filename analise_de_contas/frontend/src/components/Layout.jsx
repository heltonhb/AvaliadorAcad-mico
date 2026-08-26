import { useState, useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Building2, Upload, BarChart3, History, ArrowLeftRight, Menu, X } from 'lucide-react';
import { api } from '../api';

const navItems = [
  { path: '/', label: 'Dashboard', icon: Building2 },
  { path: '/upload', label: 'Upload', icon: Upload },
  { path: '/results', label: 'Resultados', icon: BarChart3 },
  { path: '/compare', label: 'Comparar V1/V2', icon: ArrowLeftRight },
  { path: '/history', label: 'Histórico', icon: History },
];

export default function Layout({ children }) {
  const location = useLocation();
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const check = async () => {
      try {
        const s = await api.pipelineStatus();
        setPipelineRunning(s.running);
        // Se não há pipeline rodando, para o polling
        if (!s.running && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } catch { /* ignore */ }
    };

    check();
    // Só inicia novo intervalo se não houver um ativo
    if (!intervalRef.current) {
      intervalRef.current = setInterval(check, 5000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-[var(--bg-primary)]">
      {/* Overlay escuro (mobile) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        id="sidebar"
        className={`
          fixed lg:static inset-y-0 left-0 z-30 w-64 bg-[var(--bg-surface)] border-r border-[var(--border-subtle)]
          flex flex-col transition-transform duration-200 ease-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Logo + Fechar (mobile) */}
        <div className="p-4 sm:p-5 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <div
              className="w-9 h-9 rounded-lg bg-[var(--accent)] flex items-center justify-center text-sm font-bold text-[var(--bg-primary)] shrink-0"
              aria-hidden="true"
            >
              🏢
            </div>
            <div className="min-w-0">
              <h1 className="text-sm font-bold text-[var(--text-primary)] truncate">Análise de Contas</h1>
              <p className="text-[10px] text-[var(--text-tertiary)] truncate">Auditoria Condominial v7.0</p>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="btn-ghost lg:hidden shrink-0"
            aria-label="Fechar menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 sm:p-4 space-y-0.5 overflow-y-auto" aria-label="Navegação principal">
          {navItems.map(({ path, label, icon: Icon }) => {
            const isActive = location.pathname === path;
            return (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-[var(--accent-muted)] text-[var(--accent)]'
                    : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-white/[0.02]'
                }`}
              >
                <Icon size={17} className="shrink-0" />
                <span className="truncate">{label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Pipeline Status */}
        <div className="p-3 sm:p-4 border-t border-[var(--border-subtle)]">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${
                pipelineRunning
                  ? 'bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.5)]'
                  : 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]'
              }`}
              aria-hidden="true"
            />
            <span className="text-xs text-[var(--text-tertiary)] truncate">
              {pipelineRunning ? 'Pipeline em execução' : 'Pipeline ocioso'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 min-w-0 overflow-auto" role="main">
        {/* Top bar (mobile): hamburger + título */}
        <div className="sticky top-0 z-10 lg:hidden bg-[var(--bg-primary)]/95 backdrop-blur-md border-b border-[var(--border-subtle)]">
          <div className="flex items-center gap-3 px-4 h-14">
            <button
              onClick={() => setSidebarOpen(true)}
              className="btn-ghost -ml-2"
              aria-label="Abrir menu"
              aria-expanded={sidebarOpen}
              aria-controls="sidebar"
            >
              <Menu size={20} />
            </button>
            <span className="text-sm font-semibold text-[var(--text-primary)] truncate">
              <span aria-hidden="true">🏢</span> Análise de Contas
            </span>
            {/* Status dot mobile */}
            <span
              className={`ml-auto w-2 h-2 rounded-full shrink-0 ${
                pipelineRunning
                  ? 'bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.5)]'
                  : 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]'
              }`}
              aria-hidden="true"
            />
          </div>
        </div>

        <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
