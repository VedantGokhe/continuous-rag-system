/** Types for the Continuous-RAG frontend */

export interface Source {
  filename: string;
  page_num: number;
  version: number;
  confidence: number;
  preview: string;
}

export interface QueryResult {
  answer: string;
  intent: string;
  intent_reasoning: string;
  sources: Source[];
  confidence: number;
  query: string;
  verdict?: string;
  sub_questions?: string[];
  findings?: Finding[];
  conflicts?: Conflict[];
  conditions?: string[];
  change_report?: ChangeReport;
  agent_trace?: string[];
}

export interface Finding {
  source: string;
  finding: string;
  supports_request: boolean;
}

export interface Conflict {
  doc1: string;
  doc2: string;
  description: string;
}

export interface ChangeReport {
  reports?: ChangeEntry[];
  documents?: DocInfo[];
  note?: string;
}

export interface ChangeEntry {
  id: number;
  filename: string;
  old_version: number;
  new_version: number;
  changes: Change[];
  severity: string;
  created_at: string;
}

export interface Change {
  section: string;
  old_value: string;
  new_value: string;
  severity: string;
  affected_parties: string;
}

export interface DocInfo {
  filename: string;
  base_name?: string;
  version: number;
  file_hash?: string;
  chunks?: number;
  indexed_at?: string;
}

export interface StatusResponse {
  status: string;
  watcher: string;
  total_documents: number;
  indexed_files: DocInfo[];
}

export interface SyncResult {
  status: string;
  total_vectors: number;
  files_processed: number;
  added: number;
  updated: number;
  skipped: number;
  removed: number;
  details: SyncDetail[];
}

export interface SyncDetail {
  filename: string;
  action: string;
  version?: number;
  chunks?: number;
  reason?: string;
}

export interface HistoryEntry {
  id: number;
  query: string;
  answer: string;
  intent: string;
  sources: Source[];
  confidence: number;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  result?: QueryResult;
  timestamp: Date;
}
