import {
  createContext,
  useContext,
  useReducer,
  type Dispatch,
  type ReactNode,
} from 'react';
import type { Analysis, PersistedChatMessage, UploadedDocument } from './types';

// Max messages to retain in sessionStorage (prevents bloat on long conversations)
const MAX_PERSISTED_MESSAGES = 100;

// The demo session ID used by the backend demo endpoint
export const DEMO_SESSION_ID = 'demo-session-greenlens-ecotech-2025';

const STORAGE_KEY = 'greenlens_session';

// ── State shape ────────────────────────────────────────────────────────────────

export interface AppState {
  sessionId: string | null;
  documents: UploadedDocument[];
  analysis: Analysis | null;
  /** Persisted chat history — survives navigation and page refresh */
  messages: PersistedChatMessage[];
  isLoading: boolean;
  error: string | null;
  isDemo: boolean;
}

const initialState: AppState = {
  sessionId: null,
  documents: [],
  analysis: null,
  messages: [],
  isLoading: false,
  error: null,
  isDemo: false,
};

// ── sessionStorage persistence (clears when browser is closed) ─────────────────

function loadPersistedState(): AppState {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return initialState;
    const saved = JSON.parse(raw) as Partial<AppState>;
    if (!saved.sessionId) return initialState;
    return {
      sessionId: saved.sessionId ?? null,
      documents: saved.documents ?? [],
      analysis: saved.analysis ?? null,
      messages: saved.messages ?? [],
      isLoading: false,
      error: null,
      isDemo: saved.sessionId === DEMO_SESSION_ID,
    };
  } catch {
    return initialState;
  }
}

function persistState(state: AppState): void {
  try {
    if (!state.sessionId) {
      sessionStorage.removeItem(STORAGE_KEY);
      return;
    }
    // Cap messages to last MAX_PERSISTED_MESSAGES to prevent storage bloat
    const messagesToPersist = state.messages.slice(-MAX_PERSISTED_MESSAGES);
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      sessionId: state.sessionId,
      documents: state.documents,
      analysis: state.analysis,
      messages: messagesToPersist,
    }));
  } catch {
    // ignore storage errors
  }
}

// ── Actions ────────────────────────────────────────────────────────────────────

export type AppAction =
  | { type: 'SET_SESSION'; payload: string }
  | { type: 'SET_DOCUMENTS'; payload: UploadedDocument[] }
  | { type: 'SET_ANALYSIS'; payload: Analysis }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'ADD_MESSAGE'; payload: PersistedChatMessage }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'RESET' };

// ── Reducer ────────────────────────────────────────────────────────────────────

function appReducer(state: AppState, action: AppAction): AppState {
  let newState: AppState;

  switch (action.type) {
    case 'SET_SESSION': {
      const isDemo = action.payload === DEMO_SESSION_ID;
      // Clear messages when a new session starts (fresh upload)
      const messagesForNewSession =
        state.sessionId && state.sessionId !== action.payload ? [] : state.messages;
      newState = { ...state, sessionId: action.payload, isDemo, messages: messagesForNewSession };
      break;
    }
    case 'SET_DOCUMENTS':
      newState = { ...state, documents: action.payload };
      break;
    case 'SET_ANALYSIS':
      newState = { ...state, analysis: action.payload };
      break;
    case 'SET_LOADING':
      newState = { ...state, isLoading: action.payload };
      break;
    case 'SET_ERROR':
      newState = { ...state, error: action.payload };
      break;
    case 'ADD_MESSAGE':
      newState = { ...state, messages: [...state.messages, action.payload] };
      break;
    case 'CLEAR_MESSAGES':
      newState = { ...state, messages: [] };
      break;
    case 'RESET':
      newState = { ...initialState };
      break;
    default:
      return state;
  }

  // Persist after every state change
  persistState(newState);
  return newState;
}

// ── Contexts ───────────────────────────────────────────────────────────────────

const AppStateContext = createContext<AppState | null>(null);
const AppDispatchContext = createContext<Dispatch<AppAction> | null>(null);

// ── Provider ───────────────────────────────────────────────────────────────────

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, undefined, loadPersistedState);

  return (
    <AppStateContext.Provider value={state}>
      <AppDispatchContext.Provider value={dispatch}>
        {children}
      </AppDispatchContext.Provider>
    </AppStateContext.Provider>
  );
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

export function useAppState(): AppState {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used inside AppProvider');
  return ctx;
}

export function useAppDispatch(): Dispatch<AppAction> {
  const ctx = useContext(AppDispatchContext);
  if (!ctx) throw new Error('useAppDispatch must be used inside AppProvider');
  return ctx;
}
