import { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';
import SourcesPanel from './components/SourcesPanel';
import { getStatus } from './api';
import type { QueryResult, DocInfo } from './types';

export default function App() {
  const [documents, setDocuments] = useState<DocInfo[]>([]);
  const [currentResult, setCurrentResult] = useState<QueryResult | null>(null);
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('theme') === 'dark';
  });

  // Apply dark class to <html>
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  const refreshDocuments = useCallback(async () => {
    try {
      const status = await getStatus();
      setDocuments(status.indexed_files || []);
    } catch {
      // Backend might not be running yet
    }
  }, []);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-slate-950 transition-colors duration-300">
      {/* Top Header */}
      <Header darkMode={darkMode} onToggleTheme={() => setDarkMode(!darkMode)} />

      {/* Main 3-Panel Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Sidebar */}
        <Sidebar documents={documents} onRefresh={refreshDocuments} />

        {/* Center: Chat */}
        <main className="flex-1">
          <ChatPanel onResult={setCurrentResult} />
        </main>

        {/* Right: Sources */}
        <aside className="w-80 bg-white dark:bg-slate-900 border-l border-gray-200 dark:border-slate-800 hidden lg:block transition-colors duration-300">
          <SourcesPanel result={currentResult} />
        </aside>
      </div>
    </div>
  );
}
