export interface UploadedDocument {
  id: string;
  filename: string;
  fileType: string;
  fileSize: number;
  uploadedAt: string;
  processingStatus: string;
}

export interface UploadResponse {
  sessionId: string;
  documents: UploadedDocument[];
  message: string;
}

export interface Risk {
  id: string;
  level: 'HIGH' | 'MEDIUM' | 'LOW';
  description: string;
  sourceDocument: string;
  category: string;
}

export interface Conflict {
  id: string;
  type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  documentA: { name: string; excerpt: string };
  documentB: { name: string; excerpt: string };
  explanation: string;
  recommendedAction: string;
}

export interface ComparisonRow {
  field: string;
  values: Record<string, string>;
  winner: string;
}

export interface Recommendation {
  title: string;
  summary: string;
  nextSteps: string[];
  confidence: number;
}

export interface Analysis {
  analyzedAt: string;
  executiveSummary: string;
  risks: Risk[];
  comparisonMatrix: ComparisonRow[];
  conflicts: Conflict[];
  recommendation: Recommendation;
  suggestedQuestions?: string[];
  greenwashScore?: number;
  webResearchContext?: string;
}

export interface AnalyzeResponse {
  sessionId: string;
  status: string;
  analysis: Analysis;
}

export interface Evidence {
  quote: string;
  sourceDocument: string;
  documentType: string;
}

export interface StructuredAIResponse {
  answer: string;
  evidence: Evidence[];
  risks: string;
  recommendation: string;
}

export interface ChatResponse {
  messageId: string;
  role: string;
  structuredResponse: StructuredAIResponse;
  processingTimeMs: number;
}

export interface PreSeededMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  structuredResponse?: StructuredAIResponse;
}

// ── Persisted chat message types ──────────────────────────────────────────────
// These mirror the local types in Chat.tsx but are exported so they can be
// stored in AppState and persisted to localStorage.

export interface UserChatMessage {
  id: string;
  role: 'user';
  content: string;
  timestamp: string;
}

export interface AssistantChatMessage {
  id: string;
  role: 'assistant';
  structuredResponse: StructuredAIResponse;
  timestamp: string;
}

export type PersistedChatMessage = UserChatMessage | AssistantChatMessage;

export interface DemoResponse {
  sessionId: string;
  documents: UploadedDocument[];
  analysis: Analysis;
  preSeededMessages: PreSeededMessage[];
}

export interface QuickScanResponse {
  verdict: string;
  whatToLookFor: string[];
  confidence: 'LOW' | 'MEDIUM' | 'HIGH';
}
