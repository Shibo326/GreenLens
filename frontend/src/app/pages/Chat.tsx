import { useEffect, useRef, useState } from "react";
import { NavigationBar } from "../components/NavigationBar";
import { GhostButton } from "../components/Buttons";
import { EvidenceTag, EvidenceBox } from "../components/Badges";
import {
  Send,
  AlertTriangle,
  ArrowRight,
  FileText,
  Sparkles,
  PanelLeft,
  X,
  ArrowLeft,
  Download,
  ChevronDown,
  FileDown,
  Copy,
  Check,
  RotateCcw,
  Camera,
} from "lucide-react";
import { streamChatMessage, getSuggestedQuestions, exportReport, sendVisionMessage } from "../../lib/api";
import { useAppState, useAppDispatch } from "../../lib/store";
import { Link, useNavigate } from "react-router";
import { toast } from "sonner";
import type { StructuredAIResponse } from "../../lib/types";
import { MarkdownText } from "../components/MarkdownText";

const fallbackQuestions = [
  "Is this really carbon neutral?",
  "What's Scope 3 and why does it matter?",
  "Which claims would trigger regulators?",
  "Is the recycled packaging claim legit?",
  "Are these sustainability claims backed by data?",
  "Where's the third-party verification?",
];

interface UserMessage {
  id: string;
  role: "user";
  content: string;
  timestamp: string;
}

interface AssistantMessage {
  id: string;
  role: "assistant";
  structuredResponse: StructuredAIResponse;
  timestamp: string;
}

type ChatMessage = UserMessage | AssistantMessage;

export default function Chat() {
  const { sessionId, documents, analysis } = useAppState();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [quickQuestions, setQuickQuestions] = useState<string[]>([]);
  const [questionsLoading, setQuestionsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [streamingAnswer, setStreamingAnswer] = useState<string>("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sourceModal, setSourceModal] = useState<{ quote: string; source: string; docType: string } | null>(null);
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [inputShake, setInputShake] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [simplify, setSimplify] = useState(false);
  const [attachedImage, setAttachedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const downloadRef = useRef<HTMLDivElement>(null);
  const streamAbortRef = useRef<(() => void) | null>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  // Cleanup stream on unmount to prevent state updates on unmounted component
  useEffect(() => {
    return () => {
      if (streamAbortRef.current) {
        streamAbortRef.current();
        streamAbortRef.current = null;
      }
    };
  }, []);

  // Close download dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (downloadRef.current && !downloadRef.current.contains(e.target as Node)) {
        setDownloadOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    if (analysis?.suggestedQuestions?.length) {
      setQuickQuestions(analysis.suggestedQuestions);
      return;
    }
    let cancelled = false;
    setQuestionsLoading(true);
    getSuggestedQuestions(sessionId)
      .then((questions) => {
        if (!cancelled) setQuickQuestions(questions.length > 0 ? questions : fallbackQuestions);
      })
      .catch(() => { if (!cancelled) setQuickQuestions(fallbackQuestions); })
      .finally(() => { if (!cancelled) setQuestionsLoading(false); });
    return () => { cancelled = true; };
  }, [sessionId, analysis]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  // Redirect to landing if no session
  useEffect(() => {
    if (!sessionId) {
      navigate("/", { replace: true });
    }
  }, [sessionId, navigate]);

  if (!sessionId) {
    return null;
  }

  const handleSubmit = async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || isThinking || !sessionId) return;

    const userMsg: UserMessage = { id: `u-${Date.now()}`, role: "user", content: trimmed, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setIsThinking(true);
    setStreamingAnswer("");
    setSidebarOpen(false);

    // If image is attached, use vision endpoint instead of streaming
    if (attachedImage) {
      const img = attachedImage;
      setAttachedImage(null);
      setImagePreview(null);
      try {
        const response = await sendVisionMessage(sessionId, img, trimmed);
        const assistantMsg: AssistantMessage = {
          id: response.messageId,
          role: "assistant",
          structuredResponse: response.structuredResponse,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Vision analysis failed.";
        toast.error("Image analysis failed. Please try again.");
        const errMsg: AssistantMessage = {
          id: `err-${Date.now()}`,
          role: "assistant",
          structuredResponse: { answer: errorMessage, evidence: [], risks: "", recommendation: "" },
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        setIsThinking(false);
        inputRef.current?.focus();
      }
      return;
    }

    const historyForAPI = messages.slice(-10).map(m => ({
      role: m.role as 'user' | 'assistant',
      content: m.role === 'user'
        ? (m as UserMessage).content
        : (m as AssistantMessage).structuredResponse.answer,
    }));

    let accumulated = "";

    try {
      setIsStreaming(true);
      setIsThinking(false);

      const { abort } = streamChatMessage(
        sessionId,
        trimmed,
        historyForAPI,
        (token) => {
          accumulated += token;
          // If the stream starts with JSON structure, try to extract just the answer text
          const trimmedAccum = accumulated.trim();
          if (trimmedAccum.startsWith('{"answer"') || trimmedAccum.startsWith('{ "answer"')) {
            // Show just the answer content portion while streaming
            const answerStart = trimmedAccum.indexOf('"answer"');
            if (answerStart >= 0) {
              const colonPos = trimmedAccum.indexOf(':', answerStart + 8);
              if (colonPos >= 0) {
                const quoteStart = trimmedAccum.indexOf('"', colonPos + 1);
                if (quoteStart >= 0) {
                  // Extract from after the opening quote of the answer value
                  let answerContent = trimmedAccum.slice(quoteStart + 1);
                  // Remove trailing quote and everything after if present
                  const endQuote = answerContent.search(/(?<!\\)"/);
                  if (endQuote >= 0) {
                    answerContent = answerContent.slice(0, endQuote);
                  }
                  // Unescape
                  answerContent = answerContent.replace(/\\"/g, '"').replace(/\\n/g, '\n');
                  setStreamingAnswer(answerContent);
                  return;
                }
              }
            }
          }
          setStreamingAnswer(accumulated);
        },
        (response) => {
          setIsStreaming(false);
          setStreamingAnswer("");
          // Safety: clean the answer field if it contains raw JSON
          const sr = response.structuredResponse;
          if (sr.answer && sr.answer.trim().startsWith("{") && sr.answer.includes('"answer"')) {
            try {
              const parsed = JSON.parse(sr.answer.trim());
              if (parsed && typeof parsed.answer === "string") {
                sr.answer = parsed.answer;
              }
            } catch {
              // Try regex extraction
              const match = sr.answer.match(/"answer"\s*:\s*"((?:[^"\\]|\\.)*)"/);
              if (match && match[1] && match[1].length > 20) {
                sr.answer = match[1].replace(/\\"/g, '"').replace(/\\n/g, '\n').replace(/\\t/g, '\t');
              }
            }
          }
          const assistantMsg: AssistantMessage = {
            id: response.messageId,
            role: "assistant",
            structuredResponse: sr,
            timestamp: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMsg]);
        },
        (error) => {
          setIsStreaming(false);
          setStreamingAnswer("");
          // Show error inline in chat — no toast needed (avoids double notification)
          const errMsg: AssistantMessage = {
            id: `err-${Date.now()}`,
            role: "assistant",
            structuredResponse: {
              answer: error.toLowerCase().includes("session not found")
                ? "Your session has expired. Please re-upload your documents."
                : error,
              evidence: [],
              risks: "",
              recommendation: error.toLowerCase().includes("session not found")
                ? "Navigate to the home page to start a new session."
                : "",
            },
            timestamp: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, errMsg]);
        },
      );
      streamAbortRef.current = abort;
    } catch (err) {
      setIsStreaming(false);
      setStreamingAnswer("");
      const errorMessage = err instanceof Error ? err.message : "Something went wrong.";
      const errMsg: AssistantMessage = {
        id: `err-${Date.now()}`,
        role: "assistant",
        structuredResponse: {
          answer: errorMessage,
          evidence: [],
          risks: "",
          recommendation: "",
        },
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsThinking(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!inputValue.trim()) {
        // Shake the input for visual feedback
        setInputShake(true);
        setTimeout(() => setInputShake(false), 500);
        return;
      }
      void handleSubmit(inputValue);
    }
  };

  const handleExportChat = () => {
    if (!messages.length) return;
    const lines: string[] = [`GreenLens AI — Chat Export\n${new Date().toLocaleString()}\n${'='.repeat(60)}\n`];
    for (const msg of messages) {
      if (msg.role === 'user') {
        lines.push(`[You]\n${msg.content}\n`);
      } else {
        const sr = msg.structuredResponse;
        lines.push(`[GreenLens AI]\n${sr.answer}`);
        if (sr.evidence.length) {
          lines.push(`\nEvidence:`);
          sr.evidence.forEach(ev => lines.push(`  • "${ev.quote}" — ${ev.sourceDocument}`));
        }
        if (sr.risks) lines.push(`\nRisk: ${sr.risks}`);
        if (sr.recommendation) lines.push(`\nRecommendation: ${sr.recommendation}`);
        lines.push('');
      }
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `greenlens-chat-${new Date().toISOString().slice(0,10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportReport = async (format: "pdf" | "docx") => {
    if (!sessionId) return;
    setIsExporting(true);
    setDownloadOpen(false);
    try {
      const blob = await exportReport(sessionId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `greenlens-report.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} report downloaded!`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Export failed.";
      toast.error(`Export failed: ${msg}`);
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownloadChat = () => {
    handleExportChat();
    setDownloadOpen(false);
    toast.success("Chat exported!");
  };

  const handleNewSession = async () => {
    try {
      dispatch({ type: "RESET" });
      navigate("/");
      toast.success("Session cleared — upload new documents to start fresh.");
    } catch {
      toast.error("Failed to reset session.");
    }
  };

  const docCount = documents.length;

  const SidebarContent = () => (
    <>
      <div className="p-4">
        <h3 style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", fontWeight: 500, color: "var(--ghost)", marginBottom: "12px" }}>
          Active Documents
        </h3>
        <div className="space-y-2">
          {documents.map((doc) => {
            const isImage = doc.fileType === "image";
            return (
              <div
                key={doc.id}
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg"
                style={{ background: "var(--graphite)", border: "1px solid var(--rule)" }}
              >
                <span
                  aria-hidden="true"
                  style={{ width: "6px", height: "6px", borderRadius: "50%", background: isImage ? "var(--leaf)" : "var(--flag-blue)", flexShrink: 0 }}
                />
                <span
                  className="truncate"
                  style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", fontWeight: 500, color: "var(--ash)" }}
                >
                  {doc.filename}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ height: "1px", background: "var(--rule)", margin: "8px 0" }} />

      <div className="px-4 pb-4">
        <div className="mb-3 flex items-center gap-2" style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--ghost)", textTransform: "uppercase" }}>
          <Sparkles size={12} style={{ color: "var(--ghost)" }} />
          QUICK QUESTIONS
        </div>
        <div className="flex flex-col gap-2">
          {questionsLoading ? (
            <div className="flex items-center gap-2 px-3 py-2">
              <div className="animate-dot-1 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
              <div className="animate-dot-2 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
              <div className="animate-dot-3 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
              <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", color: "var(--ghost)" }}>Generating…</span>
            </div>
          ) : (
            quickQuestions.map((q, idx) => (
              <button
                key={idx}
                className="w-full px-3 py-2 rounded-lg border text-left transition-all"
                style={{ background: "var(--lead)", borderColor: "var(--rule)", borderRadius: "var(--radius-btn)", fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontWeight: 400, fontSize: "13px", color: "var(--ash)", cursor: "pointer" }}
                onMouseOver={(e) => { e.currentTarget.style.borderColor = "var(--leaf-border)"; e.currentTarget.style.color = "var(--paper)"; e.currentTarget.style.background = "var(--leaf-dim)"; }}
                onMouseOut={(e) => { e.currentTarget.style.borderColor = "var(--rule)"; e.currentTarget.style.color = "var(--ash)"; e.currentTarget.style.background = "var(--lead)"; }}
                onClick={() => { void handleSubmit(q); }}
                disabled={isThinking || isStreaming}
              >
                {q}
              </button>
            ))
          )}
        </div>
      </div>
    </>
  );

  return (
    <div className="flex flex-col page-enter" style={{ height: "100dvh", background: "var(--ink)" }}>
      <NavigationBar showDemo={false} />

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop left panel */}
        <div
          className="hidden md:flex flex-col shrink-0"
          style={{ width: "260px", background: "var(--lead)", borderRight: "1px solid var(--rule)", overflowY: "auto" }}
        >
          <SidebarContent />
        </div>

        {/* Mobile sidebar drawer */}
        {sidebarOpen && (
          <div className="md:hidden fixed inset-0 z-50 animate-fadeIn" style={{ background: "rgba(0,0,0,0.6)" }} onClick={() => setSidebarOpen(false)}>
            <div
              className="animate-slideDown"
              style={{ width: "min(300px, 85vw)", height: "100%", background: "var(--lead)", borderRight: "1px solid var(--rule)", overflowY: "auto" }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-4 py-4" style={{ borderBottom: "1px solid var(--rule)" }}>
                <span style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "15px", fontWeight: 700, color: "var(--paper)" }}>Documents & Questions</span>
                <button onClick={() => setSidebarOpen(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ash)" }}>
                  <X size={18} />
                </button>
              </div>
              <SidebarContent />
            </div>
          </div>
        )}

        {/* Main chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Chat Header */}
          <div
            className="flex items-center justify-between px-4 sm:px-6 shrink-0"
            style={{ background: "var(--lead)", borderBottom: "1px solid var(--rule)", height: "60px" }}
          >
            <div className="flex items-center gap-3">
              {/* Mobile sidebar toggle */}
              <button
                className="md:hidden flex items-center justify-center"
                onClick={() => setSidebarOpen(true)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ash)", padding: "4px", marginRight: "4px" }}
              >
                <PanelLeft size={18} />
              </button>

              {/* Back to Analysis button */}
              <Link
                to="/dashboard"
                className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg"
                style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)", border: "1px solid var(--rule)", textDecoration: "none", transition: "all 0.15s" }}
                onMouseOver={(e) => { e.currentTarget.style.borderColor = "var(--leaf-border)"; e.currentTarget.style.color = "var(--paper)"; }}
                onMouseOut={(e) => { e.currentTarget.style.borderColor = "var(--rule)"; e.currentTarget.style.color = "var(--ghost)"; }}
              >
                <ArrowLeft size={13} />
                Analysis
              </Link>

              {/* Document-icon avatar with pulse ring */}
              <div className="relative shrink-0" style={{ width: "40px", height: "40px" }}>
                <div
                  aria-hidden="true"
                  className="animate-voltPulse"
                  style={{ position: "absolute", top: "-4px", left: "-4px", right: "-4px", bottom: "-4px", borderRadius: "10px", border: "1px solid rgba(61, 220, 132, 0.4)", pointerEvents: "none" }}
                />
                <div
                  style={{ width: "40px", height: "40px", borderRadius: "8px", background: "var(--graphite)", border: "1px solid var(--rule)", display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}
                >
                  <FileText size={18} style={{ color: "var(--leaf)" }} />
                </div>
              </div>

              <div className="flex flex-col min-w-0">
                <div style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "15px", fontWeight: 700, color: "var(--paper)" }}>
                  GreenLens Copilot
                </div>
                <div className="flex items-center gap-2">
                  <span style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "11px", fontWeight: 500, color: "var(--leaf)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "200px" }}>
                    {docCount} doc{docCount !== 1 ? "s" : ""} · greenwashing analysis ready
                  </span>
                  {isThinking && (
                    <div className="flex items-center gap-1">
                      <div className="animate-dot-1 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                      <div className="animate-dot-2 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                      <div className="animate-dot-3 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* ELI15 Toggle */}
              <div
                className="hidden sm:flex items-center rounded-full p-0.5"
                style={{ background: "var(--graphite)", border: "1px solid var(--rule)" }}
              >
                <button
                  onClick={() => setSimplify(false)}
                  className="px-3 py-1 rounded-full"
                  style={{
                    background: !simplify ? "var(--leaf-dim)" : "transparent",
                    border: !simplify ? "1px solid var(--leaf-border)" : "1px solid transparent",
                    fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                    fontSize: "11px",
                    fontWeight: 600,
                    color: !simplify ? "var(--leaf)" : "var(--ghost)",
                    cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                >
                  Expert
                </button>
                <button
                  onClick={() => setSimplify(true)}
                  className="px-3 py-1 rounded-full"
                  style={{
                    background: simplify ? "var(--leaf-dim)" : "transparent",
                    border: simplify ? "1px solid var(--leaf-border)" : "1px solid transparent",
                    fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                    fontSize: "11px",
                    fontWeight: 600,
                    color: simplify ? "var(--leaf)" : "var(--ghost)",
                    cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                >
                  ELI15
                </button>
              </div>
              {/* Download dropdown */}
              <div className="relative" ref={downloadRef}>
                <GhostButton small onClick={() => setDownloadOpen(!downloadOpen)} disabled={isExporting}>
                  <Download size={14} />
                  <span className="hidden sm:inline">{isExporting ? "Exporting…" : "Download"}</span>
                  <ChevronDown size={12} style={{ transform: downloadOpen ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
                </GhostButton>
                {downloadOpen && (
                  <div
                    className="absolute right-0 top-full mt-1 z-50 rounded-lg py-1 animate-fadeIn"
                    style={{
                      background: "var(--lead)",
                      border: "1px solid var(--rule)",
                      boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
                      minWidth: "200px",
                    }}
                  >
                    <button
                      onClick={handleDownloadChat}
                      disabled={!messages.length}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-left"
                      style={{
                        background: "none",
                        border: "none",
                        cursor: messages.length ? "pointer" : "not-allowed",
                        fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                        fontSize: "13px",
                        color: messages.length ? "var(--paper)" : "var(--ghost)",
                        transition: "background 0.15s",
                        opacity: messages.length ? 1 : 0.5,
                      }}
                      onMouseOver={(e) => { if (messages.length) e.currentTarget.style.background = "var(--graphite)"; }}
                      onMouseOut={(e) => { e.currentTarget.style.background = "none"; }}
                    >
                      <div className="flex items-center justify-center rounded" style={{ width: "28px", height: "28px", background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)" }}>
                        <FileText size={14} style={{ color: "var(--leaf)" }} />
                      </div>
                      <div>
                        <div style={{ fontWeight: 500 }}>Export Chat</div>
                        <div style={{ fontSize: "11px", color: "var(--ghost)" }}>Download conversation as .txt</div>
                      </div>
                    </button>
                    <div style={{ height: "1px", background: "var(--rule)", margin: "2px 8px" }} />
                    <button
                      onClick={() => handleExportReport("pdf")}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-left"
                      style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                        fontSize: "13px",
                        color: "var(--paper)",
                        transition: "background 0.15s",
                      }}
                      onMouseOver={(e) => { e.currentTarget.style.background = "var(--graphite)"; }}
                      onMouseOut={(e) => { e.currentTarget.style.background = "none"; }}
                    >
                      <div className="flex items-center justify-center rounded" style={{ width: "28px", height: "28px", background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)" }}>
                        <FileDown size={14} style={{ color: "var(--leaf)" }} />
                      </div>
                      <div>
                        <div style={{ fontWeight: 500 }}>Analysis as PDF</div>
                        <div style={{ fontSize: "11px", color: "var(--ghost)" }}>Full report with findings</div>
                      </div>
                    </button>
                    <button
                      onClick={() => handleExportReport("docx")}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-left"
                      style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                        fontSize: "13px",
                        color: "var(--paper)",
                        transition: "background 0.15s",
                      }}
                      onMouseOver={(e) => { e.currentTarget.style.background = "var(--graphite)"; }}
                      onMouseOut={(e) => { e.currentTarget.style.background = "none"; }}
                    >
                      <div className="flex items-center justify-center rounded" style={{ width: "28px", height: "28px", background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)" }}>
                        <FileDown size={14} style={{ color: "var(--leaf)" }} />
                      </div>
                      <div>
                        <div style={{ fontWeight: 500 }}>Analysis as DOCX</div>
                        <div style={{ fontSize: "11px", color: "var(--ghost)" }}>Editable Word document</div>
                      </div>
                    </button>
                  </div>
                )}
              </div>

              {/* Mobile back button */}
              <Link to="/dashboard" className="sm:hidden">
                <GhostButton small>
                  <ArrowLeft size={14} />
                </GhostButton>
              </Link>

              {/* New Session button */}
              <GhostButton small onClick={() => { void handleNewSession(); }} title="Clear session and upload new documents">
                <RotateCcw size={14} />
                <span className="hidden sm:inline">New Session</span>
              </GhostButton>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5" style={{ background: "var(--ink)" }}>
            {/* Empty state — show inline suggested questions */}
            {messages.length === 0 && !isThinking && !isStreaming && (
              <div className="flex flex-col items-center justify-center h-full py-8 animate-fadeIn">
                <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "16px" }}>
                  <Sparkles size={22} style={{ color: "var(--leaf)" }} />
                </div>
                <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)", marginBottom: "6px", textAlign: "center" }}>
                  Ask GreenLens anything about the greenwashing analysis
                </p>
                <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", color: "var(--ghost)", marginBottom: "24px", textAlign: "center" }}>
                  {documents.length} document{documents.length !== 1 ? "s" : ""} loaded · greenwashing detection ready
                </p>
                {/* Inline suggested questions grid */}
                {quickQuestions.length > 0 && (
                  <div className="w-full grid gap-2" style={{ maxWidth: "560px", gridTemplateColumns: "repeat(auto-fit, minmax(min(220px, 100%), 1fr))" }}>
                    {quickQuestions.slice(0, 6).map((q, idx) => (
                      <button
                        key={idx}
                        className="px-4 py-3 rounded-xl text-left"
                        style={{ background: "var(--lead)", border: "1px solid var(--rule)", fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", color: "var(--ash)", cursor: "pointer", transition: "all 0.15s", lineHeight: 1.4 }}
                        onMouseOver={(e) => { e.currentTarget.style.borderColor = "var(--leaf-border)"; e.currentTarget.style.color = "var(--paper)"; e.currentTarget.style.background = "var(--leaf-dim)"; }}
                        onMouseOut={(e) => { e.currentTarget.style.borderColor = "var(--rule)"; e.currentTarget.style.color = "var(--ash)"; e.currentTarget.style.background = "var(--lead)"; }}
                        onClick={() => void handleSubmit(q)}
                      >
                        <ArrowRight size={12} style={{ color: "var(--leaf)", marginRight: "6px", display: "inline", flexShrink: 0 }} />
                        {q}
                      </button>
                    ))}
                  </div>
                )}
                {questionsLoading && (
                  <div className="flex items-center gap-2 mt-4">
                    <div className="animate-dot-1 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                    <div className="animate-dot-2 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                    <div className="animate-dot-3 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                    <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", color: "var(--ghost)" }}>Generating questions…</span>
                  </div>
                )}
              </div>
            )}
            {messages.map((msg) => {
              if (msg.role === "user") {
                return (
                  <div key={msg.id} className="flex justify-end animate-slideUp">
                    <div style={{ maxWidth: "min(520px, 85vw)" }}>
                      <div className="px-5 py-3" style={{ background: "var(--graphite)", borderRadius: "20px 20px 4px 20px" }}>
                        <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "15px", lineHeight: 1.6, color: "var(--paper)" }}>
                          {msg.content}
                        </p>
                      </div>
                      <div className="text-right mt-1">
                        <span style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "11px", color: "var(--ghost)" }}>
                          {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              }

              const sr = msg.structuredResponse;
              return (
                <div key={msg.id} className="flex justify-start animate-slideUp">
                  <div style={{ maxWidth: "min(720px, 95vw)", width: "100%" }}>
                    <div className="p-4 sm:p-5" style={{ background: "var(--lead)", borderLeft: "3px solid var(--leaf)", borderRadius: "4px 20px 20px 20px" }}>
                      {/* ANSWER */}
                      <div className="mb-4">
                        <div className="flex items-center gap-2 mb-3">
                          <div className="flex items-center gap-1.5">
                            <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--leaf)", boxShadow: "0 0 6px rgba(61, 220, 132, 0.4)" }} />
                            <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--leaf)", textTransform: "uppercase" }}>ANSWER</span>
                          </div>
                          <div style={{ flex: 1, height: "1px", background: "var(--rule)" }} />
                        </div>
                        <MarkdownText text={sr.answer} style={{ fontSize: "15px", lineHeight: 1.7 }} />
                        <div className="flex justify-end mt-2">
                          <button
                            onClick={() => {
                              void navigator.clipboard.writeText(sr.answer).then(() => {
                                setCopiedId(msg.id);
                                setTimeout(() => setCopiedId(null), 2000);
                              });
                            }}
                            className="flex items-center gap-1"
                            style={{ background: "none", border: "none", cursor: "pointer", fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "11px", color: copiedId === msg.id ? "var(--leaf)" : "var(--ghost)", padding: "2px 6px", borderRadius: "4px", transition: "color 0.15s" }}
                            onMouseOver={(e) => { if (copiedId !== msg.id) e.currentTarget.style.color = "var(--ash)"; }}
                            onMouseOut={(e) => { if (copiedId !== msg.id) e.currentTarget.style.color = "var(--ghost)"; }}
                          >
                            {copiedId === msg.id ? <><Check size={11} />&nbsp;Copied</> : <><Copy size={11} />&nbsp;Copy</>}
                          </button>
                        </div>
                      </div>

                      {/* EVIDENCE */}
                      {sr.evidence.length > 0 && (
                        <div className="mb-4">
                          <div className="flex items-center gap-1.5 mb-2">
                            <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--leaf)" }} />
                            <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--leaf)", textTransform: "uppercase" }}>EVIDENCE</span>
                          </div>
                          <div className="space-y-2">
                            {sr.evidence.map((ev, i) => (
                              <div
                                key={i}
                                style={{ cursor: "pointer", transition: "all 0.15s" }}
                                onClick={() => setSourceModal({ quote: ev.quote, source: ev.sourceDocument, docType: ev.documentType })}
                                onMouseOver={(e) => { e.currentTarget.style.transform = "translateX(2px)"; e.currentTarget.style.opacity = "0.85"; }}
                                onMouseOut={(e) => { e.currentTarget.style.transform = "translateX(0)"; e.currentTarget.style.opacity = "1"; }}
                                title="Click to view source"
                              >
                                <EvidenceBox quote={ev.quote} style={{ marginBottom: "6px" }} />
                                <div className="flex items-center justify-between">
                                  <EvidenceTag filename={ev.sourceDocument} />
                                  <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "10px", color: "var(--leaf)", fontWeight: 500 }}>View source →</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* RISK */}
                      {sr.risks && (
                        <div className="mb-4">
                          <div className="flex items-center gap-1.5 mb-2">
                            <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--flag-red)" }} />
                            <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--flag-red)", textTransform: "uppercase" }}>RISK</span>
                          </div>
                          <div className="flex items-start gap-2 rounded-lg" style={{ background: "var(--flag-red-dim)", border: "1px solid rgba(240, 68, 82, 0.22)", padding: "12px", borderLeft: "2px solid var(--flag-red)" }}>
                            <AlertTriangle size={14} style={{ color: "var(--flag-red)", marginTop: "3px", flexShrink: 0 }} />
                            <MarkdownText text={sr.risks} style={{ fontSize: "14px", lineHeight: 1.6, opacity: 0.9 }} />
                          </div>
                        </div>
                      )}

                      {/* RECOMMENDATION */}
                      {sr.recommendation && (
                        <div>
                          <div className="flex items-center gap-1.5 mb-2">
                            <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--leaf)" }} />
                            <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--leaf)", textTransform: "uppercase" }}>RECOMMENDATION</span>
                          </div>
                          <div className="flex items-start gap-2 rounded-lg" style={{ background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)", padding: "12px", borderLeft: "2px solid var(--leaf)" }}>
                            <ArrowRight size={14} style={{ color: "var(--leaf)", marginTop: "3px", flexShrink: 0 }} />
                            <MarkdownText text={sr.recommendation} style={{ fontSize: "14px", fontWeight: 500, lineHeight: 1.6 }} />
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Timestamp */}
                    <div className="flex items-center gap-3 mt-1.5 px-1">
                      <span style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "11px", color: "var(--ghost)" }}>
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Streaming answer bubble */}
            {isStreaming && (
              <div className="flex justify-start animate-slideUp">
                <div style={{ maxWidth: "min(720px, 95vw)", width: "100%" }}>
                  <div className="rounded-2xl p-4 sm:p-5" style={{ background: "var(--lead)", border: "1px solid var(--rule)", borderLeft: "3px solid var(--leaf)", borderRadius: "4px 16px 16px 16px" }}>
                    <div className="mb-2 flex items-center gap-2">
                      <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--leaf)", textTransform: "uppercase" }}>
                        {streamingAnswer ? "ANSWER" : "THINKING"}
                      </span>
                      <div style={{ flex: 1, height: "1px", background: "var(--rule)" }} />
                      <div className="flex items-center gap-1">
                        <div className="animate-dot-1 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                        <div className="animate-dot-2 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                        <div className="animate-dot-3 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                      </div>
                    </div>
                    {streamingAnswer ? (
                      <div style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "15px", lineHeight: 1.7, color: "var(--paper)" }}>
                        <MarkdownText text={streamingAnswer} />
                        <span
                          style={{
                            display: "inline-block",
                            width: "2px",
                            height: "1em",
                            background: "var(--leaf)",
                            marginLeft: "2px",
                            verticalAlign: "text-bottom",
                            animation: "blink 1s step-end infinite",
                          }}
                        />
                      </div>
                    ) : (
                      <div className="flex items-center gap-3 py-2">
                        <div style={{ width: "16px", height: "16px", borderRadius: "50%", border: "2px solid var(--leaf)", borderTopColor: "transparent", animation: "spin 0.8s linear infinite" }} />
                        <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", color: "var(--ash)", fontStyle: "italic" }}>
                          Analyzing documents and reasoning...
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Thinking indicator */}
            {isThinking && (
              <div className="flex justify-start animate-slideUp">
                <div className="px-4 py-4 rounded-2xl" style={{ background: "var(--lead)", border: "1px solid var(--rule)", borderLeft: "3px solid var(--leaf)", borderRadius: "4px 16px 16px 16px" }}>
                  <div className="flex items-center gap-3">
                    <div className="animate-dot-1 w-2 h-2 rounded-full" style={{ background: "var(--leaf)", boxShadow: "0 0 6px rgba(61, 220, 132, 0.5)" }} />
                    <div className="animate-dot-2 w-2 h-2 rounded-full" style={{ background: "var(--leaf)", boxShadow: "0 0 6px rgba(61, 220, 132, 0.5)" }} />
                    <div className="animate-dot-3 w-2 h-2 rounded-full" style={{ background: "var(--leaf)", boxShadow: "0 0 6px rgba(61, 220, 132, 0.5)" }} />
                    <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", color: "var(--ghost)" }}>GreenLens AI is thinking…</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input */}
          <div className="px-4 sm:px-6 py-4 shrink-0 safe-bottom" style={{ background: "var(--lead)", borderTop: "1px solid var(--rule)" }}>
            {/* Image preview chip */}
            {attachedImage && imagePreview && (
              <div className="flex items-center gap-2 mb-2 px-1">
                <div
                  className="relative inline-flex items-center gap-2 px-2 py-1.5 rounded-lg"
                  style={{ background: "var(--graphite)", border: "1px solid var(--leaf-border)" }}
                >
                  <img
                    src={imagePreview}
                    alt="Attached"
                    style={{ width: "32px", height: "32px", borderRadius: "4px", objectFit: "cover" }}
                  />
                  <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", color: "var(--ash)", maxWidth: "120px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {attachedImage.name}
                  </span>
                  <button
                    onClick={() => { setAttachedImage(null); setImagePreview(null); }}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ghost)", padding: "2px" }}
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>
            )}

            {/* Hidden image input */}
            <input
              ref={imageInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              style={{ display: "none" }}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  setAttachedImage(file);
                  const reader = new FileReader();
                  reader.onload = () => setImagePreview(reader.result as string);
                  reader.readAsDataURL(file);
                }
                e.target.value = "";
              }}
            />
            {/* Mobile: quick questions scrollable horizontally above input */}
            <div className="md:hidden overflow-x-auto no-scrollbar flex items-center gap-2 mb-3">
              {questionsLoading ? (
                <div className="flex items-center gap-2 px-1 shrink-0">
                  <div className="animate-dot-1 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                  <div className="animate-dot-2 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                  <div className="animate-dot-3 w-1.5 h-1.5 rounded-full" style={{ background: "var(--leaf)" }} />
                </div>
              ) : (
                quickQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    className="shrink-0 whitespace-nowrap px-3 py-2 rounded-lg border transition-all"
                    style={{ background: "var(--lead)", borderColor: "var(--rule)", borderRadius: "var(--radius-btn)", fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontWeight: 400, fontSize: "13px", color: "var(--ash)", cursor: "pointer" }}
                    onClick={() => { void handleSubmit(q); }}
                    disabled={isThinking || isStreaming}
                  >
                    {q}
                  </button>
                ))
              )}
            </div>

            <div
              className="flex items-center gap-3 px-5 rounded-full"
              style={{ background: "var(--lead)", border: `1px solid ${inputShake ? "var(--flag-red)" : "var(--rule)"}`, minHeight: "48px", transition: "border-color 0.2s, box-shadow 0.2s", animation: inputShake ? "shake 0.4s ease" : "none", boxShadow: "0 2px 12px rgba(0,0,0,0.15)" }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--leaf-border)"; e.currentTarget.style.boxShadow = "0 2px 20px rgba(61, 220, 132, 0.08)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--rule)"; e.currentTarget.style.boxShadow = "0 2px 12px rgba(0,0,0,0.15)"; }}
            >
              <input
                ref={inputRef}
                type="text"
                placeholder="Ask about these sustainability claims…"
                className="flex-1 bg-transparent border-none outline-none placeholder-ghost"
                style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "15px", color: "var(--paper)", minWidth: 0 }}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isThinking || isStreaming}
              />
              {/* Camera / Snap & Check button */}
              <button
                className="flex items-center justify-center rounded-full shrink-0"
                style={{ width: "32px", height: "32px", background: "transparent", border: "none", cursor: "pointer", color: "var(--ghost)", transition: "color 0.15s" }}
                onClick={() => imageInputRef.current?.click()}
                onMouseOver={(e) => { e.currentTarget.style.color = "var(--leaf)"; }}
                onMouseOut={(e) => { e.currentTarget.style.color = "var(--ghost)"; }}
                title="Snap & Check — attach image for analysis"
              >
                <Camera size={18} />
              </button>
              <button
                className="flex items-center justify-center rounded-full shrink-0"
                style={{ width: "36px", height: "36px", background: isThinking || isStreaming || !inputValue.trim() ? "var(--graphite)" : "var(--leaf)", border: "none", cursor: isThinking || isStreaming || !inputValue.trim() ? "not-allowed" : "pointer", transition: "background 0.2s, opacity 0.2s", opacity: isThinking || isStreaming || !inputValue.trim() ? 0.5 : 1 }}
                onClick={() => void handleSubmit(inputValue)}
                disabled={isThinking || isStreaming || !inputValue.trim()}
              >
                <Send size={16} style={{ color: isThinking || isStreaming || !inputValue.trim() ? "var(--ghost)" : "var(--ink)" }} />
              </button>
            </div>
            <div className="text-center mt-2">
              <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "11px", fontWeight: 500, color: "var(--ghost)" }}>
                GreenLens answers from your documents + real-time web research
              </span>
            </div>
          </div>
        </div>
      </div>
      {/* Source Viewer Modal */}
      {sourceModal && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center animate-fadeIn"
          style={{ background: "rgba(0,0,0,0.7)", padding: "0 16px 16px 16px" }}
          onClick={() => setSourceModal(null)}
        >
          <div
            className="w-full rounded-t-2xl sm:rounded-2xl p-5 animate-slideUp"
            style={{
              maxWidth: "560px",
              background: "var(--lead)",
              border: "1px solid var(--leaf-border)",
              boxShadow: "0 0 40px rgba(61, 220, 132, 0.12)",
              maxHeight: "80vh",
              overflowY: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div
                  style={{
                    width: "8px", height: "8px", borderRadius: "50%",
                    background: sourceModal.docType === "image" ? "var(--leaf)" : "var(--flag-blue)",
                  }}
                />
                <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", fontWeight: 600, color: "var(--ash)" }}>
                  {sourceModal.source}
                </span>
              </div>
              <button
                onClick={() => setSourceModal(null)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ghost)", display: "flex", alignItems: "center" }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Label */}
            <div style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "10px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ghost)", marginBottom: "8px" }}>
              DOCUMENT EXCERPT
            </div>

            {/* Quote */}
            <EvidenceBox
              quote={sourceModal.quote}
              style={{ fontSize: "14px", lineHeight: 1.7, borderLeft: "3px solid var(--leaf)" }}
            />

            <div className="mt-4 flex justify-end">
              <button
                onClick={() => setSourceModal(null)}
                style={{
                  fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", fontWeight: 500,
                  color: "var(--leaf)", background: "none", border: "none", cursor: "pointer",
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
