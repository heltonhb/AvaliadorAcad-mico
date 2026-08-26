import { useState, useEffect, useCallback } from 'react';
import { Folder, FolderOpen, ChevronRight, ArrowLeft, X, Check, Home, FolderPlus, Loader2 } from 'lucide-react';
import { api } from '../api';

/**
 * DirectoryPicker — Modal visual para escolher diretório de saída.
 *
 * Props:
 *   isOpen       — boolean, controla visibilidade
 *   onClose      — callback ao fechar sem selecionar
 *   onSelect     — callback(path: string) ao selecionar diretório
 *   currentValue — string, caminho atualmente selecionado (highlight)
 */
export default function DirectoryPicker({ isOpen, onClose, onSelect, currentValue }) {
  const [currentPath, setCurrentPath] = useState('');
  const [directories, setDirectories] = useState([]);
  const [parentPath, setParentPath] = useState(null);
  const [currentName, setCurrentName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newFolderName, setNewFolderName] = useState('');
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [breadcrumbs, setBreadcrumbs] = useState([]);

  const browse = useCallback(async (path = '') => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.browse(path);
      const current = data.current || data.path || '';
      setCurrentPath(current);
      setCurrentName(data.name || '');
      setDirectories(data.directories || []);
      setParentPath(data.parent || null);

      // Build breadcrumbs from current path
      if (current) {
        const parts = current.split('/').filter(Boolean);
        const crumbs = [];
        for (let i = 0; i < parts.length; i++) {
          crumbs.push({
            name: parts[i],
            path: '/' + parts.slice(0, i + 1).join('/'),
          });
        }
        setBreadcrumbs(crumbs);
      } else {
        setBreadcrumbs([]);
      }
    } catch (err) {
      setError(err.message || 'Erro ao navegar diretórios');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      browse(currentValue || '');
    }
  }, [isOpen, browse, currentValue]);

  const handleSelect = () => {
    onSelect(currentPath);
    onClose();
  };

  const handleCreateFolder = async () => {
    const trimmed = newFolderName.trim();
    if (!trimmed) return;
    const newPath = currentPath ? `${currentPath.replace(/\/+$/, '')}/${trimmed}` : trimmed;
    try {
      if (api.createFolder) {
        await api.createFolder(newPath);
      }
      setShowNewFolder(false);
      setNewFolderName('');
      await browse(newPath);
    } catch (err) {
      setError(err.message || 'Erro ao criar pasta');
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="dir-picker-backdrop"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="dir-picker-modal">
        {/* Header */}
        <div className="dir-picker-header">
          <div className="dir-picker-header-left">
            <div className="dir-picker-icon-wrap">
              <FolderOpen size={20} className="text-[var(--accent)]" />
            </div>
            <div>
              <h3 className="dir-picker-title">Escolher Diretório</h3>
              <p className="dir-picker-subtitle">Selecione onde salvar os resultados</p>
            </div>
          </div>
          <button onClick={onClose} className="dir-picker-close-btn">
            <X size={18} />
          </button>
        </div>

        {/* Breadcrumbs */}
        <div className="dir-picker-breadcrumbs">
          <button
            onClick={() => browse('')}
            className="dir-picker-breadcrumb-btn"
            title="Raiz"
          >
            <Home size={14} />
          </button>
          {breadcrumbs.slice(-4).map((crumb, i) => (
            <span key={crumb.path} className="dir-picker-breadcrumb-item">
              <ChevronRight size={12} className="text-[var(--text-muted)]" />
              <button
                onClick={() => browse(crumb.path)}
                className={`dir-picker-breadcrumb-btn ${
                  i === breadcrumbs.slice(-4).length - 1 ? 'active' : ''
                }`}
              >
                {crumb.name}
              </button>
            </span>
          ))}
        </div>

        {/* Current path display */}
        <div className="dir-picker-current-path">
          <code>{currentPath}</code>
        </div>

        {/* Directory list */}
        <div className="dir-picker-list">
          {loading ? (
            <div className="dir-picker-loading">
              <Loader2 size={24} className="animate-spin text-[var(--accent)]" />
              <span>Carregando...</span>
            </div>
          ) : error ? (
            <div className="dir-picker-error">
              <span>❌ {error}</span>
              <button onClick={() => browse('')} className="dir-picker-retry-btn">
                Voltar ao início
              </button>
            </div>
          ) : (
            <>
              {/* Parent directory */}
              {parentPath && (
                <button
                  onClick={() => browse(parentPath)}
                  className="dir-picker-dir-item dir-picker-parent-item"
                >
                  <div className="dir-picker-dir-icon parent">
                    <ArrowLeft size={16} />
                  </div>
                  <span className="dir-picker-dir-name">.. (voltar)</span>
                </button>
              )}

              {/* Subdirectories */}
              {directories.length === 0 && !parentPath ? (
                <div className="dir-picker-empty">
                  <Folder size={32} className="text-[var(--text-muted)]" />
                  <p>Nenhum subdiretório encontrado</p>
                </div>
              ) : (
                directories.map((dir) => (
                  <button
                    key={dir.path}
                    onClick={() => browse(dir.path)}
                    className={`dir-picker-dir-item ${
                      dir.path === currentValue ? 'selected' : ''
                    }`}
                  >
                    <div className="dir-picker-dir-icon">
                      <Folder size={16} />
                    </div>
                    <span className="dir-picker-dir-name">{dir.name}</span>
                    {dir.has_children && (
                      <ChevronRight size={14} className="dir-picker-dir-arrow" />
                    )}
                  </button>
                ))
              )}
            </>
          )}
        </div>

        {/* New folder inline */}
        {showNewFolder && (
          <div className="dir-picker-new-folder animate-fade-in">
            <FolderPlus size={16} className="text-[var(--accent)] shrink-0" />
            <input
              type="text"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateFolder()}
              placeholder="Nome da nova pasta..."
              className="dir-picker-new-folder-input"
              autoFocus
            />
            <button onClick={handleCreateFolder} className="dir-picker-new-folder-ok">
              <Check size={14} />
            </button>
            <button
              onClick={() => { setShowNewFolder(false); setNewFolderName(''); }}
              className="dir-picker-new-folder-cancel"
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Footer */}
        <div className="dir-picker-footer">
          <button
            onClick={() => setShowNewFolder(true)}
            className="btn-secondary dir-picker-footer-btn"
            disabled={showNewFolder}
          >
            <FolderPlus size={15} />
            Nova Pasta
          </button>
          <div className="dir-picker-footer-actions">
            <button onClick={onClose} className="btn-secondary dir-picker-footer-btn">
              Cancelar
            </button>
            <button onClick={handleSelect} className="btn-primary dir-picker-footer-btn">
              <Check size={15} />
              Selecionar
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
