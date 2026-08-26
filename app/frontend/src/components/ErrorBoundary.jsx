import { Component } from 'react';

const initialState = { hasError: false, error: null, errorInfo: null };

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = initialState;
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    // Log to console in development
    if (import.meta.env.DEV) {
      console.error('[ErrorBoundary]', error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError) {
      const { error } = this.state;

      // Silenciar erros de rede (API offline, etc) — o Loading/Empty state das páginas cobre isso
      if (error?.message?.includes('Failed to fetch') || error?.message?.includes('NetworkError')) {
        return this.props.children;
      }

      return (
        <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center p-6">
          <div className="glass-card max-w-lg w-full p-8 text-center animate-fade-in">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-rose-500 to-amber-500 flex items-center justify-center text-3xl shadow-lg shadow-rose-500/20">
              ⚠️
            </div>
            <h2 className="text-xl font-bold text-white mb-2">
              Algo deu errado
            </h2>
            <p className="text-gray-400 text-sm mb-6">
              Ocorreu um erro inesperado ao renderizar esta página.
            </p>
            {import.meta.env.DEV && error && (
              <details className="text-left mb-6">
                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300 mb-2">
                  Detalhes do erro (dev)
                </summary>
                <pre className="text-xs text-rose-400 bg-black/30 rounded-lg p-3 overflow-auto max-h-32">
                  {error.stack || error.message}
                </pre>
              </details>
            )}
            <button
              onClick={() => {
                this.setState(initialState);
                window.location.href = '/';
              }}
              className="px-6 py-2.5 bg-indigo-500 hover:bg-indigo-400 text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-indigo-500/20"
            >
              Voltar ao início
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
