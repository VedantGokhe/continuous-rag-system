import { useState, useCallback } from 'react';
import { uploadDocument, syncDocuments, getDocumentText, clearAll, deleteDocument } from '../api';
import type { DocInfo } from '../types';

interface SidebarProps {
  documents: DocInfo[];
  onRefresh: () => void;
}

export default function Sidebar({ documents, onRefresh }: SidebarProps) {
  const [uploading, setUploading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [viewingDoc, setViewingDoc] = useState<{ filename: string; text: string } | null>(null);
  const [loadingDoc, setLoadingDoc] = useState(false);

  const handleViewDoc = async (filename: string) => {
    setLoadingDoc(true);
    try {
      const data = await getDocumentText(filename);
      setViewingDoc({ filename: data.filename, text: data.text });
    } catch (err: any) {
      alert(`Failed to load document: ${err.message}`);
    }
    setLoadingDoc(false);
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files) return;
    setUploading(true);
    setSyncResult(null);
    try {
      for (const file of Array.from(files)) {
        if (file.name.endsWith('.pdf')) {
          await uploadDocument(file);
        }
      }
      setSyncResult(`✓ Uploaded ${files.length} file(s)`);
      setTimeout(onRefresh, 4000);
    } catch (err: any) {
      setSyncResult(`✗ ${err.message}`);
    }
    setUploading(false);
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const result = await syncDocuments();
      setSyncResult(`✓ +${result.added} added, ~${result.updated} updated, -${result.removed} removed`);
      onRefresh();
    } catch (err: any) {
      setSyncResult(`✗ ${err.message}`);
    }
    setSyncing(false);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleUpload(e.dataTransfer.files);
  }, []);

  return (
    <aside className="w-72 bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-slate-800 flex flex-col h-full transition-colors duration-300">
      {/* Upload Zone */}
      <div className="p-4">
        <div
          className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all duration-200 ${
            dragOver
              ? 'border-blue-400 bg-blue-50 dark:bg-blue-950 scale-[1.02]'
              : 'border-gray-300 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50/50 dark:hover:bg-blue-950/30'
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.pdf';
            input.multiple = true;
            input.onchange = (e) => handleUpload((e.target as HTMLInputElement).files);
            input.click();
          }}
        >
          {uploading ? (
            <div className="text-blue-600 dark:text-blue-400 animate-fade-in">
              <div className="w-8 h-8 mx-auto mb-2 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs font-medium">Uploading...</p>
            </div>
          ) : (
            <>
              <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
                <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <p className="text-xs font-medium text-gray-600 dark:text-slate-300">
                Drop PDFs here
              </p>
              <p className="text-[10px] text-gray-400 dark:text-slate-500 mt-0.5">
                or click to browse
              </p>
            </>
          )}
        </div>

        {/* Sync Button */}
        <button
          onClick={handleSync}
          disabled={syncing}
          className="mt-3 w-full py-2.5 px-3 gradient-accent gradient-accent-hover text-white text-sm font-medium rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-md shadow-blue-500/20 transition-all duration-200 hover:shadow-lg hover:shadow-blue-500/30"
        >
          {syncing ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Syncing...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Sync Documents
            </>
          )}
        </button>

        {/* Sync Result */}
        {syncResult && (
          <div className={`mt-2 text-xs p-2.5 rounded-lg animate-fade-in ${
            syncResult.startsWith('✓')
              ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
              : 'bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800'
          }`}>
            {syncResult}
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="px-4">
        <div className="h-px bg-gradient-to-r from-transparent via-gray-200 dark:via-slate-700 to-transparent" />
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold text-gray-500 dark:text-slate-400 uppercase tracking-widest flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Indexed ({documents.length})
          </h3>
          {documents.length > 0 && (
            <button
              onClick={async (e) => {
                e.stopPropagation();
                if (confirm('Clear ALL documents, index, and history?')) {
                  try { await clearAll(); onRefresh(); setSyncResult('✓ All data cleared'); } 
                  catch (err: any) { setSyncResult(`✗ ${err.message}`); }
                }
              }}
              className="text-[10px] px-2 py-1 rounded-md bg-red-50 dark:bg-red-900/20 text-red-500 dark:text-red-400 font-semibold hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors border border-red-200 dark:border-red-800"
              title="Clear all data"
            >
              Clear All
            </button>
          )}
        </div>

        {documents.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-gray-100 dark:bg-slate-800 flex items-center justify-center">
              <span className="text-2xl opacity-50">📭</span>
            </div>
            <p className="text-sm font-medium text-gray-500 dark:text-slate-400">
              No documents indexed yet
            </p>
            <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
              Upload PDFs to get started
            </p>
          </div>
        ) : (
          <ul className="space-y-2">
            {documents.map((doc, i) => (
              <li
                key={i}
                onClick={() => handleViewDoc(doc.filename)}
                className="group p-3 rounded-xl bg-gray-50 dark:bg-slate-800/60 border border-gray-100 dark:border-slate-700 card-hover cursor-pointer animate-fade-in hover:border-blue-300 dark:hover:border-blue-600"
                style={{ animationDelay: `${i * 50}ms` }}
                title="Click to view full document"
              >
                <div className="flex items-start gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-sm">📄</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">
                      {doc.filename}
                    </p>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400 font-medium">
                        v{doc.version}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-50 dark:bg-purple-900/30 text-purple-500 dark:text-purple-400 font-medium">
                        {doc.chunks} chunks
                      </span>
                    </div>
                  </div>
                  {/* Delete button */}
                  <button
                    onClick={async (e) => {
                      e.stopPropagation();
                      if (confirm(`Delete "${doc.filename}"?`)) {
                        try { await deleteDocument(doc.filename); onRefresh(); }
                        catch (err: any) { alert(`Delete failed: ${err.message}`); }
                      }
                    }}
                    className="w-6 h-6 rounded-md flex items-center justify-center text-gray-400 dark:text-slate-600 hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-red-500 dark:hover:text-red-400 transition-colors flex-shrink-0 opacity-0 group-hover:opacity-100"
                    title="Delete this document"
                  >
                    ✕
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-100 dark:border-slate-800">
        <div className="flex flex-wrap items-center justify-center gap-2">
          <span className="text-xs px-2 py-1 rounded-md bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 font-semibold">FAISS</span>
          <span className="text-xs px-2 py-1 rounded-md bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 font-semibold">LangGraph</span>
          <span className="text-xs px-2 py-1 rounded-md bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 font-semibold">Groq</span>
          <span className="text-xs px-2 py-1 rounded-md bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 font-semibold">React</span>
        </div>
      </div>

      {/* Document Viewer Modal (Fix #11) */}
      {viewingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in"
             onClick={() => setViewingDoc(null)}>
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-[90vw] max-w-3xl max-h-[85vh] flex flex-col animate-slide-up"
               onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <span className="text-xl">📄</span>
                <div>
                  <h2 className="text-base font-bold text-gray-800 dark:text-white">{viewingDoc.filename}</h2>
                  <p className="text-xs text-gray-400 dark:text-slate-500">Full document text</p>
                </div>
              </div>
              <button
                onClick={() => setViewingDoc(null)}
                className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-slate-800 flex items-center justify-center hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-500 hover:text-red-600 transition-colors"
              >
                ✕
              </button>
            </div>
            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <pre className="text-sm text-gray-700 dark:text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
                {viewingDoc.text}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Loading overlay for doc viewer */}
      {loadingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-10 h-10 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
    </aside>
  );
}
