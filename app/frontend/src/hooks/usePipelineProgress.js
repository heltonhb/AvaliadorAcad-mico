import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api';

/**
 * Steps do pipeline — exportado pro componente usar na renderização.
 * Centralizado aqui pra evitar duplicação entre hook e UI.
 */
export const PIPELINE_STEPS = [
  { id: 'preflight', label: 'Verificação OCR', group: 'pre' },
  { id: 'create_notebook', label: 'Criando notebook', group: 'pre' },
  { id: 'configure_persona', label: 'Configurando persona', group: 'pre' },
  { id: 'add_source', label: 'Adicionando PDF', group: 'pre' },
  { id: 'wait_index', label: 'Indexando documento', group: 'pre' },
  { id: 'initial_slides', label: 'Slides iniciais', group: 'pre' },
  { id: 'module_00', label: '00: Estrutura do Documento', group: 'modules' },
  { id: 'module_01', label: '01: Auditoria Metodológica', group: 'modules' },
  { id: 'module_02', label: '02: Auditoria Editorial', group: 'modules', lite_skip: true },
  { id: 'module_03', label: '03: SOTA & Referências', group: 'modules', lite_skip: true },
  { id: 'module_04', label: '04: Gaps Lógicos', group: 'modules' },
  { id: 'module_05', label: '05: Análise de Escrita', group: 'modules' },
  { id: 'module_06', label: '06: Síntese & Parecer', group: 'modules' },
  { id: 'module_07', label: '07: Auditoria Quantitativa', group: 'modules' },
  { id: 'bibliography', label: '08: Auditoria Bibliográfica (Crossref)', group: 'modules' },
  { id: 'csv', label: 'CSV de erros', group: 'post' },
  { id: 'report', label: 'Relatório consolidado', group: 'post' },
  { id: 'artifacts', label: 'Artefatos & Parecer PDF', group: 'post' },
  { id: 'done', label: 'Concluído', group: 'post' },
];

/**
 * usePipelineProgress
 *
 * Gerencia o estado de progresso do pipeline via SSE + polling fallback.
 * Elimina a duplicação de lógica entre EventSource e setInterval.
 *
 * Exported state:   stepStates, logs, running, status
 * Exported actions: start, addLog, reset
 */
export function usePipelineProgress() {
  const [stepStates, setStepStates] = useState({});
  const [logs, setLogs] = useState([]);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState('idle');
  const lastStepIdRef = useRef(null);
  const cleanupRef = useRef(null);

  /* ─── Handler único para dados de SSE e polling ─── */
  const handleProgress = useCallback((p) => {
    setStepStates(prev => {
      const next = { ...prev };

      if (p.current_step) {
        const stepId = p.current_step.step_id;
        const currentIdx = PIPELINE_STEPS.findIndex(s => s.id === stepId);

        // Marca todos os steps ANTERIORES ao current como done
        if (currentIdx > 0) {
          for (let i = 0; i < currentIdx; i++) {
            const sid = PIPELINE_STEPS[i].id;
            if (next[sid] !== 'done') next[sid] = 'done';
          }
        }

        // Marca o step anterior ao current como done (se era running)
        if (lastStepIdRef.current && lastStepIdRef.current !== stepId) {
          if (next[lastStepIdRef.current] === 'running') {
            next[lastStepIdRef.current] = 'done';
          }
        }

        // Só marca como running se ainda NÃO foi concluído
        if (next[stepId] !== 'done') {
          next[stepId] = 'running';
        }
        lastStepIdRef.current = stepId;
      }

      if (p.completed_modules) {
        for (const mod of p.completed_modules) {
          const sid = `module_${mod}`;
          if (next[sid] !== 'done') next[sid] = 'done';
        }
      }

      if (p.running === false) {
        const finalStatus = p.status === 'completed' ? 'done' : 'error';
        if (finalStatus === 'done') {
          for (const s of PIPELINE_STEPS) {
            if (next[s.id] === 'running') next[s.id] = 'done';
          }
        } else {
          PIPELINE_STEPS.forEach(s => {
            if (!next[s.id]) next[s.id] = 'skipped';
          });
        }
      }

      return next;
    });

    if (p.logs && p.logs.length > 0) {
      setLogs(p.logs);
    }

    if (p.running === false) {
      setStatus(p.status === 'completed' ? 'done' : 'error');
      setRunning(false);
    }
  }, []);

  /* ─── Iniciar escuta SSE + polling ─── */
  const start = useCallback(() => {
    setRunning(true);
    setStatus('running');
    setStepStates({});
    setLogs(['🚀 Iniciando pipeline...']);
    lastStepIdRef.current = null;

    let eventSource = null;
    let fallbackInterval = null;
    let fallbackTimeout = null;
    let stopped = false;

    const stop = () => {
      if (stopped) return;
      stopped = true;
      eventSource?.close();
      clearInterval(fallbackInterval);
      clearTimeout(fallbackTimeout);
    };

    /* Tenta SSE primeiro */
    const trySse = () => {
      try {
        const baseUrl = window.location.origin;
        eventSource = new EventSource(`${baseUrl}/api/pipeline/progress/stream`);

        eventSource.addEventListener('progress', (ev) => {
          if (stopped) return;
          try { handleProgress(JSON.parse(ev.data)); } catch { /* ignore */ }
        });

        eventSource.onmessage = (ev) => {
          if (stopped) return;
          try { handleProgress(JSON.parse(ev.data)); } catch { /* ignore */ }
        };

        eventSource.addEventListener('done', (ev) => {
          if (stopped) return;
          try { handleProgress(JSON.parse(ev.data)); } catch { /* ignore */ }
          eventSource?.close();
          eventSource = null;
        });

        eventSource.onerror = () => {
          if (stopped) return;
          eventSource?.close();
          eventSource = null;
          startPolling();
        };

        return true;
      } catch {
        return false;
      }
    };

    /* Fallback polling */
    const startPolling = () => {
      setLogs(prev => [...prev, 'ℹ️ Stream não disponível, usando polling...']);
      fallbackInterval = setInterval(async () => {
        if (stopped) return;
        try {
          const p = await api.pipelineProgress();
          handleProgress(p);
          if (p.running === false) clearInterval(fallbackInterval);
        } catch { /* ignore */ }
      }, 3000);
    };

    if (!trySse()) {
      startPolling();
    }

    // Timeout de segurança (2h)
    fallbackTimeout = setTimeout(stop, 7200000);

    cleanupRef.current = stop;
  }, [handleProgress]);

  /* ─── Adicionar linha ao log (usado antes do start) ─── */
  const addLog = useCallback((msg) => {
    setLogs(prev => [...prev, msg]);
  }, []);

  /* ─── Reset completo ─── */
  const reset = useCallback(() => {
    cleanupRef.current?.();
    setStepStates({});
    setLogs([]);
    setRunning(false);
    setStatus('idle');
    lastStepIdRef.current = null;
    cleanupRef.current = null;
  }, []);

  /* Cleanup no unmount */
  useEffect(() => {
    return () => cleanupRef.current?.();
  }, []);

  return { stepStates, logs, running, status, start, addLog, reset };
}
