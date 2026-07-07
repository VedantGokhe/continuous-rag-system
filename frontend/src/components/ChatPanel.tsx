import { useState, useRef, useEffect } from 'react';
import { queryAgent } from '../api';
import type { ChatMessage, QueryResult } from '../types';

/** Simple markdown-to-HTML renderer for LLM output (Fix #8) */
function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')          // **bold**
    .replace(/\*(.*?)\*/g, '<em>$1</em>')                       // *italic*
    .replace(/^- (.*)/gm, '<li>$1</li>')                        // - list items
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul class="list-disc pl-4 my-1">$&</ul>') // wrap in <ul>
    .replace(/\n{2,}/g, '<br/><br/>')                            // paragraph breaks
    .replace(/\n/g, '<br/>');                                    // line breaks
}

interface ChatPanelProps {
  onResult: (result: QueryResult | null) => void;
}

export default function ChatPanel({ onResult }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const q = input.trim();
    if (!q || loading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: q,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    onResult(null);

    const history = messages.slice(-6).map(m => ({
      role: m.role,
      content: m.content.slice(0, 300),
    }));

    try {
      const result = await queryAgent(q, history);
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.answer,
        result,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMsg]);
      onResult(result);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${err.message}`,
        timestamp: new Date(),
      }]);
    }
    setLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getIntentBadge = (intent: string) => {
    const badges: Record<string, { label: string; color: string; icon: string }> = {
      question: { label: 'Q&A', color: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800', icon: '📋' },
      compliance: { label: 'Compliance', color: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800', icon: '✅' },
      what_changed: { label: 'Changes', color: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800', icon: '📊' },
    };
    const badge = badges[intent] || { label: intent, color: 'bg-gray-100 text-gray-600 border-gray-200', icon: '❓' };
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${badge.color}`}>
        <span>{badge.icon}</span> {badge.label}
      </span>
    );
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-b from-gray-50 to-gray-100/50 dark:from-slate-950 dark:to-slate-900 transition-colors duration-300">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full animate-fade-in">
            {/* Hero Icon */}
            <div className="w-20 h-20 rounded-2xl gradient-accent flex items-center justify-center shadow-lg shadow-blue-500/20 mb-5">
              <span className="text-3xl">🧠</span>
            </div>
            
            <h2 className="text-xl font-bold text-gray-800 dark:text-white">
              Ask anything about your documents
            </h2>
            <p className="text-sm text-gray-500 dark:text-slate-400 mt-1.5 max-w-md text-center">
              The AI agent automatically routes your query to the right specialist — Q&A, Compliance, or Change Analysis
            </p>

            {/* Example Queries */}
            <div className="mt-8 space-y-2.5 w-full max-w-lg">
              <p className="text-[11px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-widest text-center mb-3">
                Try asking
              </p>
              {[
                { q: 'What is the leave policy?', icon: '📋', tag: 'Q&A' },
                { q: 'Can I work remotely from another country?', icon: '✅', tag: 'Compliance' },
                { q: 'What changed in the latest policy update?', icon: '📊', tag: 'Changes' },
              ].map((example) => (
                <button
                  key={example.q}
                  onClick={() => setInput(example.q)}
                  className="w-full flex items-center gap-3 px-4 py-3.5 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-md hover:shadow-blue-500/5 text-gray-600 dark:text-slate-300 text-left transition-all duration-200 card-hover group"
                >
                  <span className="text-lg group-hover:scale-110 transition-transform">{example.icon}</span>
                  <span className="flex-1 text-sm">{example.q}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-slate-400 font-medium group-hover:bg-blue-50 dark:group-hover:bg-blue-900/30 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors">
                    {example.tag}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
            onClick={() => { if (msg.result) onResult(msg.result); }}
          >
            <div className={`max-w-[75%] px-4 py-3 cursor-pointer ${
              msg.role === 'user'
                ? 'bubble-user'
                : 'bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-2xl rounded-bl-sm shadow-sm hover:shadow-md transition-shadow'
            }`}>
              {/* Intent badge */}
              {msg.role === 'assistant' && msg.result && (
                <div className="flex items-center gap-2 mb-2.5">
                  {getIntentBadge(msg.result.intent)}
                  <span className="text-[11px] text-gray-400 dark:text-slate-500 font-medium">
                    {msg.result.confidence.toFixed(0)}% confident
                  </span>
                </div>
              )}

              {/* Verdict */}
              {msg.result?.verdict && (
                <div className={`mb-3 px-3 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 ${
                  msg.result.verdict === 'ALLOWED' ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800' :
                  msg.result.verdict === 'DENIED' ? 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800' :
                  'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                }`}>
                  <span>{msg.result.verdict === 'ALLOWED' ? '✅' : msg.result.verdict === 'DENIED' ? '❌' : '⚠️'}</span>
                  Verdict: {msg.result.verdict}
                </div>
              )}

              {/* Content — rendered as Markdown (Fix #8) */}
              <div
                className="answer-content text-sm leading-relaxed text-gray-800 dark:text-slate-200"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
              />

              {/* Sources indicator */}
              {msg.result?.sources && msg.result.sources.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-gray-100 dark:border-slate-700 flex items-center gap-1.5">
                  <svg className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                  <span className="text-[11px] text-gray-400 dark:text-slate-500 font-medium">
                    {msg.result.sources.length} source(s) — see details →
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading */}
        {loading && (
          <div className="flex justify-start animate-fade-in">
            <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-sm text-gray-500 dark:text-slate-400">Agent thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 dark:border-slate-800 p-4 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm transition-colors duration-300">
        <div className="flex items-end gap-3 max-w-3xl mx-auto">
          <div className="flex-1">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about company policies..."
              rows={1}
              className="w-full resize-none border border-gray-300 dark:border-slate-700 rounded-xl px-4 py-3 text-sm input-focus bg-white dark:bg-slate-800 dark:text-white shadow-sm transition-colors duration-200"
            />
          </div>
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-5 py-3 gradient-accent gradient-accent-hover text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed text-sm font-semibold shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 transition-all duration-200"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>

        {/* BIGGER Auto-routes footer */}
        <div className="mt-3 flex items-center justify-center gap-3">
          <span className="text-sm font-semibold text-gray-500 dark:text-slate-400">
            Auto-routes:
          </span>
          <div className="flex items-center gap-2">
            <span className="text-sm px-2.5 py-1 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-semibold border border-blue-200 dark:border-blue-800">
              📋 Q&A
            </span>
            <span className="text-gray-300 dark:text-slate-600">·</span>
            <span className="text-sm px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 font-semibold border border-emerald-200 dark:border-emerald-800">
              ✅ Compliance
            </span>
            <span className="text-gray-300 dark:text-slate-600">·</span>
            <span className="text-sm px-2.5 py-1 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 font-semibold border border-amber-200 dark:border-amber-800">
              📊 Changes
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
