const API_BASE = '/api';

async function request(url, options = {}) {
  const headers = { ...options.headers };
  // For FormData, don't set Content-Type (browser sets multipart boundary)
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  } else if (!headers['Content-Type'] && options.method && options.method !== 'GET') {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${API_BASE}${url}`, { ...options, headers, credentials: 'same-origin' });
  if (res.status === 401) {
    // Redirect to login page on auth failure (except when calling auth/me or auth/login/register)
    if (!url.startsWith('/auth/') && !window.location.pathname.startsWith('/login')) {
      window.location.href = '/login';
    }
    const err = await res.json().catch(() => ({ detail: 'Sessão expirada. Faça login novamente.' }));
    throw new Error(err.detail || 'Não autenticado');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Erro ${res.status}`);
  }
  return res.json();
}

async function requestRaw(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, { ...options, credentials: 'same-origin' });
  return res;
}

export const api = {
  health: () => request('/health'),
  config: () => request('/config'),

  // Auth
  authMe: () => request('/auth/me'),
  authLogin: (email, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  }),
  authRegister: (email, password, name) => request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, name }),
  }),
  authLogout: () => request('/auth/logout', { method: 'POST' }),

  // Upload
  upload: async (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/upload', { method: 'POST', body: form });
  },

  // Reutiliza um upload já existente no servidor pelo path salvo.
  // Não faz re-upload: apenas valida que o arquivo ainda existe e retorna
  // os metadados necessários para iniciar o pipeline.
  uploadFromPath: async (serverPath) => {
    // O path já está no servidor — monta um objeto compatível com o retorno
    // de /api/upload para que o componente possa iniciar o pipeline normalmente.
    const name = serverPath.split('/').pop();
    return {
      filename: name,
      safe_name: name,
      path: serverPath,
      size_mb: null,
      was_compressed: false,
      original_size_mb: null,
    };
  },

  // Pipeline
  startPipeline: ({ file_path, domain = 'cs', mode = 'full', force = false, output_dir }) =>
    request('/pipeline/start', {
      method: 'POST',
      body: JSON.stringify({ file_path, domain, mode, force, output_dir }),
    }),
  pipelineStatus: () => request('/pipeline/status'),
  pipelineProgress: () => request('/pipeline/progress'),

  // Analyses
  analyses: () => request('/analyses'),
  analysesStats: () => request('/analyses/stats'),
  analysis: (id) => request(`/analyses/${encodeURIComponent(id)}`),
  analysisFile: (analysisId, fileName) =>
    request(`/analyses/${encodeURIComponent(analysisId)}/files/${fileName}`),
  deleteAnalysis: (id) =>
    request(`/analyses/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  compareAnalyses: (baseId, targetId) =>
    request(`/analyses/compare?base_id=${encodeURIComponent(baseId)}&target_id=${encodeURIComponent(targetId)}`),

  // Sources
  sources: () => request('/sources'),

  // Browse directories
  browse: (path = '') => request(`/browse?path=${encodeURIComponent(path)}`),
  createFolder: (path) => request('/browse/mkdir', {
    method: 'POST',
    body: JSON.stringify({ path }),
  }),

  // Streaming (SSE)
  pipelineProgressStream: () =>
    requestRaw('/pipeline/progress/stream', {
      headers: { Accept: 'text/event-stream' },
    }),

  // NotebookLM Authentication
  notebooklmAccountInfo: () => request('/notebooklm/account/info'),
  notebooklmAuthStatus: () => request('/notebooklm/auth/status'),

  // Download analysis as ZIP (triggers browser download)
  downloadAnalysisZip: async (analysisId, { cleanup = false } = {}) => {
    const cleanupParam = cleanup ? '?cleanup=true' : '';
    const res = await fetch(`${API_BASE}/analyses/${encodeURIComponent(analysisId)}/download${cleanupParam}`, {
      credentials: 'same-origin',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Erro no download' }));
      throw new Error(err.detail || `Erro ${res.status}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${analysisId}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};
