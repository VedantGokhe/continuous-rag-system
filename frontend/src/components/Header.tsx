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
          onClick={async () => {
            setEvalRunning(true);
            try {
              const res = await runEvaluation();
              setEvalResult(res);
            } catch (err: any) {
              alert(`Eval failed: ${err.message}`);
            }
            setEvalRunning(false);
          }}
          disabled={evalRunning}
          className="flex items-center gap-2 bg-gradient-to-r from-amber-500/20 to-orange-500/20 px-4 py-2 rounded-lg text-amber-300 text-sm font-bold border border-amber-500/30 hover:from-amber-500/30 hover:to-orange-500/30 transition-all disabled:opacity-50"
        >
          {evalRunning ? (
            <><div className="w-3.5 h-3.5 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" /> Running...</>
          ) : (
            <>🧪 Eval</>
          )}
        </button>

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

      {/* Eval Results Modal */}
      {evalResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in" onClick={() => setEvalResult(null)}>
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-[90vw] max-w-4xl max-h-[85vh] flex flex-col animate-slide-up" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <span className="text-xl">🧪</span>
                <div>
                  <h2 className="text-lg font-bold text-gray-800 dark:text-white">RAG Evaluation Report</h2>
                  <p className="text-xs text-gray-400">{evalResult.summary?.total_tests} test cases evaluated</p>
                </div>
              </div>
              <button onClick={() => setEvalResult(null)} className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-slate-800 flex items-center justify-center hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-500 hover:text-red-600 transition-colors">✕</button>
            </div>

            {/* Summary Cards */}
            <div className="px-6 py-4 grid grid-cols-4 gap-3 border-b border-gray-100 dark:border-slate-800">
              {[
                { label: 'Overall', value: evalResult.summary?.overall_score, color: 'blue' },
                { label: 'Faithfulness', value: evalResult.summary?.avg_faithfulness, color: 'emerald' },
                { label: 'Relevancy', value: evalResult.summary?.avg_relevancy, color: 'purple' },
                { label: 'Hallucination', value: evalResult.summary?.avg_hallucination, color: 'red', invert: true },
              ].map((m) => (
                <div key={m.label} className={`rounded-xl p-3 text-center bg-${m.color}-50 dark:bg-${m.color}-900/20 border border-${m.color}-200 dark:border-${m.color}-800`}>
                  <p className="text-xs font-semibold text-gray-500 dark:text-slate-400">{m.label}</p>
                  <p className={`text-2xl font-bold mt-1 ${
                    (m.invert ? (1 - (m.value || 0)) : (m.value || 0)) >= 0.7 ? 'text-emerald-600 dark:text-emerald-400' :
                    (m.invert ? (1 - (m.value || 0)) : (m.value || 0)) >= 0.4 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'
                  }`}>
                    {((m.value || 0) * 100).toFixed(0)}%
                  </p>
                </div>
              ))}
            </div>

            {/* Per-test Results */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-400 dark:text-slate-500 uppercase">
                    <th className="text-left py-2">Query</th>
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
                    <tr key={i} className="border-t border-gray-100 dark:border-slate-800">
                      <td className="py-2 text-gray-700 dark:text-slate-300 max-w-xs truncate">{r.query}</td>
                      <td className="text-center font-bold text-emerald-600 dark:text-emerald-400">{(r.scores?.faithfulness * 100).toFixed(0)}%</td>
                      <td className="text-center font-bold text-purple-600 dark:text-purple-400">{(r.scores?.relevancy * 100).toFixed(0)}%</td>
                      <td className="text-center font-bold text-blue-600 dark:text-blue-400">{(r.scores?.correctness * 100).toFixed(0)}%</td>
                      <td className={`text-center font-bold ${r.scores?.hallucination <= 0.2 ? 'text-emerald-600' : 'text-red-600'}`}>{(r.scores?.hallucination * 100).toFixed(0)}%</td>
                      <td className="text-center">{r.correct_source ? '✅' : '❌'}</td>
                      <td className="text-right text-gray-400 dark:text-slate-500">{r.latency_ms}ms</td>
                    </tr>
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
