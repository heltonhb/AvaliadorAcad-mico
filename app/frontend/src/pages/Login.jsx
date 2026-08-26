import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Microscope, LogIn, UserPlus, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isRegister) {
        await register(email, password, name);
      } else {
        await login(email, password);
      }
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-emerald-400 flex items-center justify-center shadow-lg shadow-[rgba(20,184,166,0.25)]">
            <Microscope size={30} className="text-[var(--bg-primary)]" />
          </div>
          <h1 className="text-2xl font-extrabold text-[var(--text-primary)]">
            Análise Científica
          </h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">
            Peer-Review Grade · v6.0 · NotebookLM
          </p>
        </div>

        {/* Form Card */}
        <div className="card p-6 sm:p-8">
          <h2 className="text-lg font-bold text-[var(--text-primary)] mb-6">
            {isRegister ? 'Criar Conta' : 'Entrar'}
          </h2>

          {error && (
            <div className="flex items-center gap-2 p-3 mb-4 rounded-lg bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)]">
              <AlertCircle size={16} className="text-[var(--danger)] shrink-0" />
              <p className="text-sm text-[var(--danger)]">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="text-xs text-[var(--text-tertiary)] block mb-1.5 font-medium">Nome</label>
                <input
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="Seu nome completo"
                  required
                  className="input w-full"
                  autoComplete="name"
                />
              </div>
            )}

            <div>
              <label className="text-xs text-[var(--text-tertiary)] block mb-1.5 font-medium">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                className="input w-full"
                autoComplete="email"
              />
            </div>

            <div>
              <label className="text-xs text-[var(--text-tertiary)] block mb-1.5 font-medium">Senha</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                minLength={6}
                className="input w-full"
                autoComplete={isRegister ? 'new-password' : 'current-password'}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center"
            >
              {loading ? (
                <Loader2 size={17} className="animate-spin" />
              ) : isRegister ? (
                <><UserPlus size={17} /> Criar Conta</>
              ) : (
                <><LogIn size={17} /> Entrar</>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => { setIsRegister(!isRegister); setError(''); }}
              className="text-sm text-[var(--accent)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
            >
              {isRegister ? 'Já tem conta? Entrar' : 'Não tem conta? Criar conta'}
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-[var(--text-muted)] mt-6">
          🔒 Sessão segura com JWT httpOnly
        </p>
      </div>
    </div>
  );
}
