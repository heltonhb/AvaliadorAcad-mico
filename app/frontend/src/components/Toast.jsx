import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import { X, CheckCircle, XCircle, Info, AlertTriangle } from 'lucide-react';

const ToastContext = createContext(null);

const ICONS = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
  warning: AlertTriangle,
};

const DURATIONS = {
  success: 4000,
  info: 4000,
  warning: 6000,
  error: 6000,
};

const BORDER_COLORS = {
  success: 'border-emerald-500',
  error: 'border-red-500',
  info: 'border-[var(--accent)]',
  warning: 'border-amber-500',
};

const ICON_COLORS = {
  success: 'text-emerald-400',
  error: 'text-red-400',
  info: 'text-[var(--accent)]',
  warning: 'text-amber-400',
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const idRef = useRef(0);

  const remove = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const toast = useCallback((message, type = 'info', duration, action) => {
    const ms = duration ?? DURATIONS[type] ?? 4000;
    const toastId = ++idRef.current;
    setToasts(prev => [...prev, { id: toastId, message, type, ms, action }]);
    if (ms > 0) {
      setTimeout(() => remove(toastId), ms);
    }
    return toastId;
  }, [remove]);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map(t => {
          const Icon = ICONS[t.type];
          return (
            <div
              key={t.id}
              className={`
                pointer-events-auto animate-slide-in-right
                bg-[var(--bg-surface)] border ${BORDER_COLORS[t.type]}
                rounded-xl shadow-xl p-4 flex items-start gap-3
                transition-all duration-300
              `}>
              <Icon size={20} className={`shrink-0 mt-0.5 ${ICON_COLORS[t.type]}`} />
              <p className="text-sm text-[var(--text-primary)] flex-1 min-w-0">{t.message}</p>
              <div className="flex items-center gap-2 shrink-0">
                {t.action && (
                  <button
                    onClick={() => { t.action.onClick(); remove(t.id); }}
                    className="text-xs font-semibold text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors whitespace-nowrap"
                  >
                    {t.action.label}
                  </button>
                )}
                <button
                  onClick={() => remove(t.id)}
                  className="shrink-0 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
                  aria-label="Fechar"
                >
                  <X size={16} />
                </button>
              </div>
              </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx;
}
