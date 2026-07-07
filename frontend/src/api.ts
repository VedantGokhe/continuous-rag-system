/** API client for the Continuous-RAG backend */

const API_BASE = 'http://127.0.0.1:8000';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

/** Health check */
export const getHealth = () => request<any>('/');

/** Get system status */
export const getStatus = () => request<any>('/status');

/** Upload a PDF document */
export async function uploadDocument(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  return request('/upload', { method: 'POST', body: formData });
}

/** Trigger document sync */
export const syncDocuments = () => request<any>('/sync');

/** Query via agent pipeline (POST with chat history for follow-ups) */
export const queryAgent = (q: string, chatHistory: {role: string, content: string}[] = []) =>
  request<any>('/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ q, chat_history: chatHistory }),
  });

/** Get query history */
export const getHistory = (limit = 50) =>
  request<any>(`/history?limit=${limit}`);

/** Get change reports */
export const getChangeReports = (filename?: string) =>
  request<any>(`/changes${filename ? `?filename=${encodeURIComponent(filename)}` : ''}`);

/** Get full document text for viewer (Fix #11) */
export const getDocumentText = (filename: string) =>
  request<any>(`/document/${encodeURIComponent(filename)}`);

/** Clear ALL data — wipe DB, index, PDFs */
export const clearAll = () =>
  request<any>('/clear', { method: 'POST' });

/** Delete a specific document */
export const deleteDocument = (filename: string) =>
  request<any>(`/document/${encodeURIComponent(filename)}`, { method: 'DELETE' });

/** Run RAG evaluation pipeline */
export const runEvaluation = () => request<any>('/eval');

/** Streaming query via SSE — returns a ReadableStream */
export async function queryAgentStream(
  q: string,
  onToken: (token: string) => void,
  onMeta: (meta: any) => void,
  onDone: () => void,
  onError: (err: string) => void,
  chatHistory: {role: string, content: string}[] = []
) {
  const res = await fetch(`${API_BASE}/query/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ q, chat_history: chatHistory }),
  });
  const reader = res.body?.getReader();
  const decoder = new TextDecoder();
  if (!reader) { onError('No stream available'); return; }

  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'token') onToken(data.content);
          else if (data.type === 'meta') onMeta(data);
          else if (data.type === 'done') onDone();
          else if (data.type === 'error') onError(data.content);
        } catch {}
      }
    }
  }
}
