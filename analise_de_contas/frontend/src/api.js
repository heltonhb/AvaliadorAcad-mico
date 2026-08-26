const API_BASE = '/api';

// API Key — configurada via VITE_API_KEY no .env ou variável de ambiente do Vite
const API_KEY = import.meta.env.VITE_API_KEY || '';

function authHeaders(extra = {}) {
  const headers = { ...extra };
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }
  return headers;
}

async function request(url, options = {}) {
  // Em requisições com FormData, NÃO setamos Content-Type (browser boundary)
  const headers = authHeaders({ ...options.headers });
  // Remove Content-Type se for FormData (browser precisa setar multipart com boundary)
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  } else if (!headers['Content-Type'] && options.method && options.method !== 'GET') {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${API_BASE}${url}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Erro ${res.status}`);
  }
  return res.json();
}

// Helper para respostas que não precisam virar JSON antes (SSE etc.)
async function requestRaw(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, { ...options, headers: authHeaders(options.headers || {}) });
  return res;
}

export const api = {
  health: () => request('/health'),
  config: () => request('/config'),

  // Upload (FormData → X-API-Key é injetado automaticamente via authHeaders)
  upload: async (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/upload', { method: 'POST', body: form });
  },

  // Pipeline
  startPipeline: ({ file_path, domain = 'res', mode = 'full', force = false, output_dir }) =>
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

  // Streaming (SSE) — retorna Response cru para o caller ler linha a linha
  pipelineProgressStream: () =>
    requestRaw('/pipeline/progress/stream', {
      headers: { Accept: 'text/event-stream' },
    }),
};
