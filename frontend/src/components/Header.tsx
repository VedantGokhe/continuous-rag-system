import { useState, useEffect } from 'react';
import { getStatus, runEvaluation } from '../api';

interface HeaderProps {
  darkMode: boolean;
  onToggleTheme: () => void;
}

export default function Header({ darkMode, onToggleTheme }: HeaderProps) {
  const [status, setStatus] = useState<any>(null);
  const [evalRunning, setEvalRunning] = useState(false);
  const [evalResult, setEvalResult] = useState<any>(null);
  const [showModal, setShowModal] = useState(false);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await getStatus();
        setStatus(data);
      } catch {
        setStatus(null);
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleRunEval = async () => {
    setEvalRunning(true);
    try {
      const res = await runEvaluation();
      setEvalResult(res);
      setShowModal(true);
      setExpandedRow(null);
    } catch (err: any) {
      alert(`Eval failed: ${err.message}`);
    }
    setEvalRunning(false);
  };

  const scoreColor = (val: number, invert = false) => {
    const v = invert ? 1 - val : val;
    if (v >= 0.7) return 'text-emerald-400';
    if (v >= 0.4) return 'text-amber-400';
    return 'text-red-400';
  };

  return (
    <header className="gradient-header px-8 py-4 flex items-center justify-between shadow-lg">
      {/* Left: Logo + Title + Subtitle inline */}
      <div className="flex items-center gap-4">
        <div className="w-11 h-11 rounded-xl gradient-accent flex items-center justify-center shadow-md">
          <span className="text-2xl">🧠</span>
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight leading-tight">
            Continuous-RAG
          </h1>
          <p className="text-sm text-slate-400 font-medium">
            Enterprise Policy Intelligence System
          </p>
        </div>
        {/* Version badge — next to title */}
        <span className="ml-2 px-3 py-1 bg-gradient-to-r from-blue-500/25 to-purple-500/25 text-blue-300 rounded-lg text-sm font-bold border border-blue-500/30">
          v2.0
        </span>
      </div>

      {/* Right: Status indicators + Theme Toggle */}
      <div className="flex items-center gap-3">
        {/* Document count */}
        <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-lg">
          <span className="text-base">📄</span>
          <span className="text-sm font-semibold text-slate-200">
            {status?.total_documents ?? '0'} docs indexed
          </span>
        </div>

        {/* Watcher status */}
        <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-lg">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              status?.watcher === 'active'
                ? 'bg-emerald-400 animate-pulse-dot shadow-[0_0_8px_rgba(52,211,153,0.7)]'
                : 'bg-gray-500'
            }`}
          />
          <span className={`text-sm font-semibold ${
            status?.watcher === 'active' ? 'text-emerald-300' : 'text-gray-500'
          }`}>
            {status?.watcher === 'active' ? 'Live' : 'Offline'}
          </span>
        </div>

        {/* RAG Eval button */}
        <button
          onClick={handleRunEval}
          disabled={evalRunning}
          className="flex items-center gap-2 bg-gradient-to-r from-amber-500/20 to-orange-500/20 px-4 py-2 rounded-lg text-amber-300 text-sm font-bold border border-amber-500/30 hover:from-amber-500/30 hover:to-orange-500/30 transition-all disabled:opacity-50"
        >
          {evalRunning ? (
            <><div className="w-3.5 h-3.5 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" /> Running...</>
          ) : (
            <>🧪 Eval</>
          )}
        </button>

        {/* "View Report" button — only visible after an eval has run */}
        {evalResult && (
          <button
            onClick={() => { setShowModal(true); setExpandedRow(null); }}
            className="flex items-center gap-2 bg-gradient-to-r from-violet-500/20 to-indigo-500/20 px-4 py-2 rounded-lg text-violet-300 text-sm font-bold border border-violet-500/30 hover:from-violet-500/30 hover:to-indigo-500/30 transition-all animate-fade-in"
            title="View last evaluation report"
          >
            📊 Report
          </button>
        )}

        {/* Professional Theme Toggle — pill switch */}
        <div className="flex items-center bg-white/10 rounded-lg p-1">
          <button
            onClick={() => { if (darkMode) onToggleTheme(); }}
            className={`px-4 py-2 rounded-md text-sm font-bold transition-all duration-200 ${
              !darkMode
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Light
          </button>
          <button
            onClick={() => { if (!darkMode) onToggleTheme(); }}
            className={`px-4 py-2 rounded-md text-sm font-bold transition-all duration-200 ${
              darkMode
                ? 'bg-slate-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Dark
          </button>
        </div>
      </div>

      {/* ── Eval Results Modal ── */}
      {showModal && evalResult && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in"
          onClick={() => setShowModal(false)}
        >
          <div
            className="bg-slate-900 rounded-2xl shadow-2xl w-[92vw] max-w-5xl max-h-[88vh] flex flex-col border border-slate-700 animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <div className="flex items-center gap-3">
                <span className="text-xl">🧪</span>
                <div>
                  <h2 className="text-lg font-bold text-white">RAG Evaluation Report</h2>
                  <p className="text-xs text-slate-400">
                    {evalResult.summary?.total_tests} test cases · {evalResult.summary?.judge_model} · avg latency {evalResult.summary?.avg_latency_ms}ms
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center hover:bg-red-900/40 text-slate-400 hover:text-red-400 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Summary Cards */}
            <div className="px-6 py-4 grid grid-cols-4 gap-3 border-b border-slate-800">
              {[
                { label: 'Overall', value: evalResult.summary?.overall_score, color: 'blue' },
                { label: 'Faithfulness', value: evalResult.summary?.avg_faithfulness, color: 'emerald' },
                { label: 'Relevancy', value: evalResult.summary?.avg_relevancy, color: 'purple' },
                { label: 'Hallucination', value: evalResult.summary?.avg_hallucination, color: 'red', invert: true },
              ].map((m) => (
                <div
                  key={m.label}
                  className="rounded-xl p-3 text-center bg-slate-800/60 border border-slate-700"
                >
                  <p className="text-xs font-semibold text-slate-400">{m.label}</p>
                  <p className={`text-2xl font-bold mt-1 ${scoreColor(m.value || 0, m.invert)}`}>
                    {((m.value || 0) * 100).toFixed(0)}%
                  </p>
                </div>
              ))}
            </div>

            {/* Per-test Results Table */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <p className="text-xs text-slate-500 mb-3">
                💡 Click any row to see the <span className="text-violet-400 font-semibold">RAG answer</span> vs the <span className="text-emerald-400 font-semibold">expected answer</span>
              </p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-slate-500 uppercase">
                    <th className="text-left py-2 pr-2">Query</th>
                    <th className="text-center">Faith</th>
                    <th className="text-center">Relev</th>
                    <th className="text-center">Correct</th>
                    <th className="text-center">Halluc</th>
                    <th className="text-center">Source</th>
                    <th className="text-right">Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {evalResult.results?.map((r: any, i: number) => (
                    <>
                      {/* ── Summary Row ── */}
                      <tr
                        key={`row-${i}`}
                        className={`border-t border-slate-800 cursor-pointer transition-colors ${
                          expandedRow === i ? 'bg-slate-800/60' : 'hover:bg-slate-800/40'
                        }`}
                        onClick={() => setExpandedRow(expandedRow === i ? null : i)}
                      >
                        <td className="py-2.5 pr-2 text-slate-300 max-w-xs">
                          <div className="flex items-center gap-2">
                            <span className={`text-xs transition-transform duration-200 ${expandedRow === i ? 'rotate-90' : ''}`}>▶</span>
                            <span className="truncate">{r.query}</span>
                          </div>
                        </td>
                        <td className={`text-center font-bold ${scoreColor(r.scores?.faithfulness)}`}>
                          {(r.scores?.faithfulness * 100).toFixed(0)}%
                        </td>
                        <td className={`text-center font-bold ${scoreColor(r.scores?.relevancy)}`}>
                          {(r.scores?.relevancy * 100).toFixed(0)}%
                        </td>
                        <td className={`text-center font-bold ${scoreColor(r.scores?.correctness)}`}>
                          {(r.scores?.correctness * 100).toFixed(0)}%
                        </td>
                        <td className={`text-center font-bold ${scoreColor(r.scores?.hallucination, true)}`}>
                          {(r.scores?.hallucination * 100).toFixed(0)}%
                        </td>
                        <td className="text-center">
                          {r.correct_source
                            ? <span className="text-emerald-400">✅</span>
                            : <span className="text-red-400">❌</span>}
                        </td>
                        <td className="text-right text-slate-500">{r.latency_ms}ms</td>
                      </tr>

                      {/* ── Expanded Detail Row ── */}
                      {expandedRow === i && (
                        <tr key={`detail-${i}`} className="bg-slate-800/50">
                          <td colSpan={7} className="px-4 pb-4 pt-2">
                            <div className="grid grid-cols-2 gap-3">

                              {/* RAG Answer */}
                              <div className="rounded-xl border border-violet-500/30 bg-violet-900/10 p-3">
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="w-2 h-2 rounded-full bg-violet-400"></span>
                                  <p className="text-xs font-bold text-violet-400 uppercase tracking-wide">RAG System Response</p>
                                </div>
                                <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                                  {r.actual || <span className="italic text-slate-500">No response</span>}
                                </p>
                              </div>

                              {/* Expected Answer */}
                              <div className="rounded-xl border border-emerald-500/30 bg-emerald-900/10 p-3">
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                                  <p className="text-xs font-bold text-emerald-400 uppercase tracking-wide">Expected Correct Answer</p>
                                </div>
                                <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                                  {r.expected}
                                </p>
                              </div>

                            </div>

                            {/* Judge Reasoning */}
                            {r.scores?.reasoning && (
                              <div className="mt-3 rounded-xl border border-amber-500/20 bg-amber-900/10 p-3">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                                  <p className="text-xs font-bold text-amber-400 uppercase tracking-wide">Judge Reasoning</p>
                                </div>
                                <p className="text-xs text-slate-300 leading-relaxed">{r.scores.reasoning}</p>
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
