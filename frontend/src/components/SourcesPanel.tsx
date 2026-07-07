import type { QueryResult } from '../types';

interface SourcesPanelProps {
  result: QueryResult | null;
}

export default function SourcesPanel({ result }: SourcesPanelProps) {
  if (!result) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-400 dark:text-slate-400 p-8 transition-colors duration-300">
        <div className="w-16 h-16 rounded-2xl bg-gray-100 dark:bg-slate-800 flex items-center justify-center mb-4">
          <svg className="w-7 h-7 text-gray-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
        </div>
        <p className="text-base font-semibold text-gray-500 dark:text-slate-300">Sources & Details</p>
        <p className="text-sm text-gray-400 dark:text-slate-500 mt-1.5 text-center leading-relaxed">
          Agent pipeline details will appear here after you ask a question
        </p>
      </div>
    );
  }

  const getConfidenceColor = (c: number) => {
    if (c >= 70) return 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800';
    if (c >= 40) return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800';
    return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800';
  };

  return (
    <div className="h-full overflow-y-auto transition-colors duration-300">
      {/* Agent Pipeline Info */}
      <div className="p-4 border-b border-gray-100 dark:border-slate-800">
        <h3 className="text-[11px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
          </svg>
          Agent Pipeline
        </h3>
        
        <div className="bg-gray-50 dark:bg-slate-800/60 rounded-xl p-3 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 dark:text-slate-400 font-medium">Intent</span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
              result.intent === 'question' ? 'bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 border-blue-200 dark:border-blue-800' :
              result.intent === 'compliance' ? 'bg-emerald-50 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800' :
              'bg-amber-50 dark:bg-amber-900/40 text-amber-600 dark:text-amber-300 border-amber-200 dark:border-amber-800'
            }`}>
              {result.intent}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 dark:text-slate-400 font-medium">Source Relevance</span>
            <div className="flex items-center gap-2">
              <div className="w-16 h-1.5 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    result.confidence >= 70 ? 'bg-emerald-500' :
                    result.confidence >= 40 ? 'bg-amber-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(100, result.confidence)}%` }}
                />
              </div>
              <span className={`text-xs font-bold ${
                result.confidence >= 70 ? 'text-emerald-600 dark:text-emerald-400' :
                result.confidence >= 40 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'
              }`}>
                {result.confidence.toFixed(0)}%
              </span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 dark:text-slate-400 font-medium">Answer Quality</span>
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${
              // Fix #20: For compliance with clear verdict → always High
              ((result.verdict && !['ERROR','UNKNOWN'].includes(result.verdict)) ||
               (result.confidence >= 55 && result.answer && !result.answer.includes("don't have enough")))
                ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
                : (result.confidence >= 30)
                ? 'bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800'
                : 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800'
            }`}>
              {((result.verdict && !['ERROR','UNKNOWN'].includes(result.verdict)) ||
                (result.confidence >= 55 && result.answer && !result.answer.includes("don't have enough")))
                ? '✅ High'
                : (result.confidence >= 30)
                ? '⚠️ Medium'
                : '❌ Low'}
            </span>
          </div>
          {result.intent_reasoning && (
            <p className="text-[11px] text-gray-400 dark:text-slate-500 italic leading-relaxed pt-1 border-t border-gray-200 dark:border-slate-700">
              "{result.intent_reasoning}"
            </p>
          )}
        </div>
      </div>

      {/* Compliance Verdict */}
      {result.verdict && (
        <div className="p-4 border-b border-gray-100 dark:border-slate-800 animate-fade-in">
          <h3 className="text-[11px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            Compliance
          </h3>
          
          <div className={`px-4 py-3 rounded-xl text-center font-bold text-sm ${
            result.verdict === 'ALLOWED' ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border-2 border-emerald-200 dark:border-emerald-700' :
            result.verdict === 'DENIED' ? 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-2 border-red-200 dark:border-red-700' :
            result.verdict === 'CONDITIONAL' ? 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-2 border-amber-200 dark:border-amber-700' :
            'bg-gray-50 dark:bg-slate-800 text-gray-700 dark:text-slate-300 border-2 border-gray-200 dark:border-slate-700'
          }`}>
            {result.verdict === 'ALLOWED' ? '✅' : result.verdict === 'DENIED' ? '❌' : '⚠️'} {result.verdict}
          </div>

          {result.findings && result.findings.length > 0 && (
            <div className="mt-3 space-y-1.5">
              <p className="text-[11px] font-semibold text-gray-500 dark:text-slate-400">Findings</p>
              {result.findings.map((f, i) => (
                <div key={i} className="text-xs bg-white dark:bg-slate-800/60 rounded-lg p-2.5 border border-gray-100 dark:border-slate-700 card-hover">
                  <div className="flex items-start gap-1.5">
                    <span className="mt-0.5">{f.supports_request ? '✅' : '❌'}</span>
                    <div>
                      <span className="font-semibold text-gray-700 dark:text-slate-200">{f.source}</span>
                      <p className="text-gray-500 dark:text-slate-400 mt-0.5">{f.finding}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {result.conflicts && result.conflicts.length > 0 && (
            <div className="mt-3 space-y-1.5">
              <p className="text-[11px] font-semibold text-orange-600 dark:text-orange-400 flex items-center gap-1">
                <span>⚠️</span> Conflicts Detected
              </p>
              {result.conflicts.map((c, i) => (
                <div key={i} className="text-xs bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 rounded-lg p-2.5 border border-orange-200 dark:border-orange-800">
                  <span className="font-semibold">{c.doc1}</span> vs <span className="font-semibold">{c.doc2}</span>
                  <p className="mt-0.5 text-orange-600 dark:text-orange-400">{c.description}</p>
                </div>
              ))}
            </div>
          )}

          {result.conditions && result.conditions.length > 0 && (
            <div className="mt-3">
              <p className="text-[11px] font-semibold text-gray-500 dark:text-slate-400 mb-1.5">Conditions</p>
              <ul className="space-y-1">
                {result.conditions.map((cond, i) => (
                  <li key={i} className="text-xs text-gray-600 dark:text-slate-300 flex items-start gap-1.5 bg-white dark:bg-slate-800/60 rounded-lg p-2 border border-gray-100 dark:border-slate-700">
                    <span className="text-blue-500 mt-0.5">→</span> {cond}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Sources */}
      <div className="p-4 border-b border-gray-100 dark:border-slate-800">
        <h3 className="text-[11px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Sources ({result.sources?.length || 0})
        </h3>

        {result.sources && result.sources.length > 0 ? (
          <div className="space-y-2.5">
            {result.sources.map((src, i) => (
              <div
                key={i}
                className="bg-white dark:bg-slate-800/60 rounded-xl p-3 border border-gray-100 dark:border-slate-700 card-hover animate-fade-in"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-gray-700 dark:text-slate-200 flex items-center gap-1.5">
                    <span>📄</span> {src.filename}
                  </span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getConfidenceColor(src.confidence)}`}>
                    {src.confidence?.toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[10px] text-gray-400 dark:text-slate-500 mb-2">
                  <span>Page {src.page_num}</span>
                  <span>•</span>
                  <span>v{src.version}</span>
                </div>
                <p className="text-[11px] text-gray-500 dark:text-slate-400 leading-relaxed bg-gray-50 dark:bg-slate-900/50 rounded-lg p-2">
                  {src.preview}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-400 dark:text-slate-500 italic text-center py-4">No sources available</p>
        )}
      </div>

      {/* Agent Trace */}
      {result.agent_trace && result.agent_trace.length > 0 && (
        <div className="p-4">
          <h3 className="text-[11px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Agent Trace
          </h3>
          <div className="bg-slate-900 rounded-xl p-3 text-[10px] font-mono space-y-1 max-h-52 overflow-y-auto shadow-inner">
            {result.agent_trace.map((step, i) => (
              <div key={i} className="text-slate-400 hover:text-emerald-400 transition-colors flex items-start gap-2">
                <span className="text-slate-600 select-none w-4 text-right flex-shrink-0">{i + 1}</span>
                <span className="text-emerald-500/70">{step}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
