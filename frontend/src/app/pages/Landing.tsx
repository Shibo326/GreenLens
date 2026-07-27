import { useRef, useState, useEffect, type DragEvent } from "react";
import { useNavigate } from "react-router";
import { NavigationBar } from "../components/NavigationBar";
import { PrimaryButton } from "../components/Buttons";
import { DocumentStack } from "../components/DocumentStack";
import {
  Upload,
  Cpu,
  Sparkles,
  Zap,
  CheckCircle,
  Loader,
  RefreshCw,
} from "lucide-react";
import { Link } from "react-router";
import { uploadDocuments, analyzeDocuments, warmupServer, getBenchmarkSpeedup } from "../../lib/api";
import { toast } from "sonner";
import { useAppDispatch } from "../../lib/store";
import { motion, AnimatePresence } from "framer-motion";
import { QuickScanPanel } from "../components/QuickScanPanel";

const LOADING_STAGES = [
  { label: "Extracting text", icon: "📄" },
  { label: "AMD embeddings", icon: "⚡" },
  { label: "AI analysis (5 parallel calls)", icon: "🧠" },
  { label: "Detecting conflicts", icon: "🔍" },
  { label: "Building report", icon: "📊" },
];

// Dynamic status messages shown during long waits
const SLOW_MESSAGES = [
  { afterSeconds: 20, message: "Server is warming up — hang tight..." },
  { afterSeconds: 40, message: "Still running — AMD MI300X is processing your documents..." },
  { afterSeconds: 70, message: "Almost there — large documents take a bit longer..." },
  { afterSeconds: 100, message: "Due to high demand, the server is warming up to run properly. Please retry your analysis — it should work on the next attempt!" },
];

export default function Landing() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [slowMessage, setSlowMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [benchmarkLabel, setBenchmarkLabel] = useState<string>("AMD MI300X");
  const [benchmarkSub, setBenchmarkSub] = useState<string>("GPU-Accelerated");

  // Warmup backend on page load — prevents Railway cold-start delay when user clicks Analyze
  useEffect(() => {
    warmupServer();
  }, []);

  // Note: We do NOT auto-redirect to dashboard even if session exists,
  // because user may intentionally navigate here to upload more documents
  // (via "← Upload", "Upload More", etc.)

  // Fetch live AMD benchmark on mount (non-blocking, best-effort, cached)
  useEffect(() => {
    const controller = new AbortController();

    getBenchmarkSpeedup(controller.signal)
      .then((ratio) => {
        if (ratio) {
          setBenchmarkLabel(`${ratio.toFixed(1)}×`);
          setBenchmarkSub("Faster on AMD MI300X");
        }
      })
      .catch(() => {
        // Silently fall back to static label — benchmark is optional
      });

    return () => {
      controller.abort();
    };
  }, []);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    addFiles(Array.from(e.dataTransfer.files));
  };
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(Array.from(e.target.files));
      e.target.value = "";
    }
  };

  const addFiles = (incoming: File[]) => {
    setError(null);
    const accepted = incoming.filter((f) => {
      const mime = f.type.toLowerCase();
      const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
      return (
        ["application/pdf", "image/png", "image/jpeg", "image/jpg"].includes(mime) ||
        ["pdf", "png", "jpg", "jpeg"].includes(ext)
      );
    });
    const rejected = incoming.length - accepted.length;
    if (rejected > 0) setError(`${rejected} file(s) skipped — only PDF, PNG, and JPEG are supported.`);
    setFiles((prev) => {
      const combined = [...prev, ...accepted];
      if (combined.length > 10) {
        setError("You can upload up to 10 files at a time.");
        return combined.slice(0, 10);
      }
      return combined;
    });
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Escape key clears file selection
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setFiles([]);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Track the pending sessionId so we can retry analyze without re-uploading
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!files.length && !pendingSessionId) return;
    setError(null);
    setIsLoading(true);
    setElapsedSeconds(0);
    setSlowMessage(null);

    // Only RESET if we're starting fresh (no pending session to recover)
    if (!pendingSessionId) {
      dispatch({ type: "RESET" });
    }
    setLoadingStage(0);

    // Start elapsed timer
    let hasShownTimeoutToast = false;
    const timerInterval = setInterval(() => {
      setElapsedSeconds((prev) => {
        const next = prev + 1;
        // Update slow message based on elapsed time
        const msg = [...SLOW_MESSAGES].reverse().find((m) => next >= m.afterSeconds);
        setSlowMessage(msg?.message ?? null);
        // Show a toast notification at 100 seconds
        if (next === 100 && !hasShownTimeoutToast) {
          hasShownTimeoutToast = true;
          toast.warning(
            "Due to high demand, the server is still warming up. If it doesn't complete soon, please retry — it usually works on the next attempt!",
            { duration: 12000 }
          );
        }
        return next;
      });
    }, 1000);

    const stageTimers = [
      setTimeout(() => setLoadingStage(1), 2000),
      setTimeout(() => setLoadingStage(2), 4000),
      setTimeout(() => setLoadingStage(3), 12000),
      setTimeout(() => setLoadingStage(4), 25000),
    ];

    const toastId = toast.loading('Analyzing documents with AI...');

    const cleanup = () => {
      stageTimers.forEach(clearTimeout);
      clearInterval(timerInterval);
      toast.dismiss(toastId);
    };

    const doAnalyze = async (isRetry = false): Promise<boolean> => {
      try {
        let currentSessionId = pendingSessionId;

        // Only upload if we don't have a pending session already
        if (!currentSessionId) {
          const uploadResult = await uploadDocuments(files);
          stageTimers.forEach(clearTimeout);
          setLoadingStage(2);
          currentSessionId = uploadResult.sessionId;
          dispatch({ type: "SET_SESSION", payload: currentSessionId });
          dispatch({ type: "SET_DOCUMENTS", payload: uploadResult.documents });
          setPendingSessionId(currentSessionId);
        } else {
          stageTimers.forEach(clearTimeout);
          setLoadingStage(2);
          if (isRetry) {
            toast.loading('Reconnected — resuming analysis...', { id: toastId });
          } else {
            toast.loading('Reconnected — resuming analysis...', { id: toastId });
          }
        }

        const analyzeResult = await analyzeDocuments(currentSessionId);
        if (!analyzeResult.analysis) {
          throw new Error("Analysis returned empty — please try again");
        }
        dispatch({ type: "SET_ANALYSIS", payload: analyzeResult.analysis });
        setPendingSessionId(null);
        return true;
      } catch (err) {
        const rawMsg = err instanceof Error ? err.message : "Something went wrong.";
        const lower = rawMsg.toLowerCase();
        const isTimeout = lower.includes("timed out") || lower.includes("timeout");
        const isNetwork = lower.includes("network") || lower.includes("fetch") || lower.includes("failed to fetch");

        // Auto-retry once on timeout/network errors (only on first attempt)
        if (!isRetry && (isTimeout || isNetwork) && pendingSessionId) {
          toast.loading('Connection dropped — auto-retrying...', { id: toastId });
          setSlowMessage("Connection dropped — retrying automatically...");
          await new Promise((r) => setTimeout(r, 3000));
          return doAnalyze(true);
        }
        throw err;
      }
    };

    try {
      const success = await doAnalyze();
      if (success) {
        cleanup();
        setIsLoading(false);
        navigate("/dashboard");
      }
    } catch (err) {
      cleanup();
      const rawMsg = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      const lower = rawMsg.toLowerCase();
      let msg: string;
      let toastMsg: string;

      if (lower.includes("timed out") || lower.includes("timeout")) {
        if (pendingSessionId) {
          msg = "Due to high demand, the server is warming up to run properly. Don't worry — your documents are still uploaded. Click 'Retry Analysis' to try again, it usually works on the next attempt!";
        } else {
          msg = "Due to high demand, the server is warming up to run properly. Click 'Retry Analysis' to try again — it usually works on the next attempt!";
        }
        toastMsg = "Server warming up — click Retry to try again";
      } else if (lower.includes("rate") || lower.includes("429") || lower.includes("quota")) {
        msg = "AI service is busy right now. Please wait 60 seconds and try again.";
        toastMsg = msg;
        setPendingSessionId(null);
      } else if (lower.includes("upload") || lower.includes("413")) {
        msg = "Upload failed — check that your files are valid PDFs or images under 10MB.";
        toastMsg = msg;
        setPendingSessionId(null);
      } else if (lower.includes("network") || lower.includes("fetch") || lower.includes("failed to fetch")) {
        if (pendingSessionId) {
          msg = "Connection dropped — your documents are still on the server. Click 'Retry Analysis' to resume.";
        } else {
          msg = "Connection error — check your internet and try again.";
        }
        toastMsg = "Network error — click Retry to resume";
      } else {
        msg = "Analysis failed. Please try again. If it keeps happening, try with fewer documents.";
        toastMsg = msg;
        setPendingSessionId(null);
      }
      setError(msg);
      setSlowMessage(null);
      toast.error(toastMsg);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--ink)" }}>
      <NavigationBar />

      {/* Hero */}
      <div
        className="flex flex-col items-center text-center px-4 sm:px-6 pt-12 sm:pt-16 md:pt-20 mx-auto animate-fadeIn"
        style={{ maxWidth: "1200px" }}
      >
        {/* Eyebrow + hackathon badge */}
        <div className="flex flex-col md:flex-row items-center md:items-center gap-3 mb-6">
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "11px",
              fontWeight: 500,
              color: "var(--volt)",
              textTransform: "uppercase",
              letterSpacing: "0.12em",
            }}
          >
            GREENWASHING DETECTION PLATFORM
          </span>
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full"
            style={{
              background: "var(--volt-dim)",
              border: "1px solid var(--volt-border)",
            }}
          >
            <Zap size={12} style={{ color: "var(--volt)" }} />
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--paper)" }}>
              AMD Developer Hackathon: ACT II
            </span>
          </div>
        </div>

        {/* Headline */}
        <h1
          className="mb-5 animate-slideUp"
          style={{
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 700,
            fontSize: "clamp(32px, 5.5vw, 56px)",
            lineHeight: 1.14,
            color: "var(--paper)",
            maxWidth: "min(720px, 92vw)",
            position: "relative",
          }}
        >
          {/* Glow behind headline */}
          <span
            aria-hidden="true"
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: "80%",
              height: "120%",
              background: "radial-gradient(ellipse at center, rgba(59,123,246,0.12) 0%, transparent 70%)",
              pointerEvents: "none",
              filter: "blur(40px)",
              zIndex: -1,
            }}
          />
          Every contract tells a story. We read them all{" "}
          <span
            style={{
              textDecoration: "underline",
              textDecorationColor: "var(--leaf)",
              textDecorationThickness: "3px",
              textUnderlineOffset: "4px",
            }}
          >
            for greenwashing
          </span>
          .
        </h1>

        {/* Subheadline */}
        <p
          className="mb-8 animate-slideUp"
          style={{
            animationDelay: "0.08s",
            fontFamily: "'Inter', sans-serif",
            fontWeight: 400,
            fontSize: "clamp(15px, 3.5vw, 18px)",
            lineHeight: 1.6,
            color: "var(--ash)",
            maxWidth: "min(560px, 92vw)",
          }}
        >
          Upload sustainability reports, packaging claims, and marketing copy. 
          Ask anything in plain language. Get evidence-based greenwashing 
          detection in under 60 seconds — powered by AMD Instinct MI300X.
        </p>

        {/* Stats Row */}
        <div
          className="flex items-center justify-center md:justify-start flex-wrap gap-0 mb-10 animate-slideUp"
          style={{ animationDelay: "0.15s" }}
        >
          {[
            { value: "< 60s", label: "Analysis time", color: "var(--paper)" },
            { value: benchmarkLabel, label: benchmarkSub, color: "var(--leaf)" },
            { value: "100%", label: "Claim verification", color: "var(--paper)" },
          ].map((stat, i) => (
            <div key={i} className="flex items-center">
              {i > 0 && (
                <div style={{ width: "1px", height: "40px", background: "var(--rule)", margin: "0 clamp(16px, 3vw, 32px)" }} />
              )}
              <div className="flex flex-col items-center text-center">
                <div style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 700, fontSize: "clamp(24px, 4vw, 32px)", color: stat.color, lineHeight: 1.2 }}>
                  {stat.value}
                </div>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", fontWeight: 500, color: "var(--ash)", textTransform: "uppercase", letterSpacing: "0.06em", marginTop: "4px" }}>
                  {stat.label}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Upload Zone */}
      <div className="flex flex-col items-center px-4 sm:px-6 mb-6 mx-auto" style={{ maxWidth: "1200px" }}>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
          style={{ display: "none" }}
          onChange={handleFileInputChange}
        />

        <div
          className="flex flex-col items-center justify-center w-full animate-slideUp"
          style={{
            maxWidth: "600px",
            minHeight: files.length > 0 ? "auto" : "260px",
            borderRadius: "var(--radius-card)",
            background: isDragging ? "var(--volt-dim)" : "var(--lead)",
            border: `1.5px dashed ${isDragging ? "var(--volt)" : "var(--rule)"}`,
            padding: files.length > 0 ? "24px" : "clamp(24px, 5vw, 40px) clamp(16px, 4vw, 28px)",
            transition: "border-color 0.2s, background 0.3s",
            cursor: isLoading ? "default" : "pointer",
            animationDelay: "0.2s",
            position: "relative",
            overflow: "hidden",
          }}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => { if (!isLoading) fileInputRef.current?.click(); }}
        >
          {/* Scan line effect when dragging */}
          {isDragging && <div className="scan-line" />}

          {files.length === 0 ? (
            <>
              {/* 3 stacked paper shapes */}
              <div className="relative mb-5 flex items-center justify-center" style={{ width: "64px", height: "64px" }}>
                <div style={{ position: "absolute", width: "44px", height: "56px", background: "var(--paper)", borderRadius: "3px", transform: "rotate(-8deg)", top: "4px", left: "6px", boxShadow: "0 2px 6px rgba(0,0,0,0.25)" }} />
                <div style={{ position: "absolute", width: "44px", height: "56px", background: "var(--paper)", borderRadius: "3px", transform: "rotate(5deg)", top: "2px", left: "12px", boxShadow: "0 2px 6px rgba(0,0,0,0.25)" }} />
                <div style={{ position: "absolute", width: "44px", height: "56px", background: "var(--paper)", borderRadius: "3px", transform: "rotate(-2deg)", top: "0px", left: "10px", boxShadow: "0 2px 8px rgba(0,0,0,0.3)" }} />
              </div>

              <h3 className="hidden md:block" style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "clamp(16px, 3vw, 20px)", color: "var(--paper)", marginBottom: "8px", textAlign: "center" }}>
                Drop documents here
              </h3>
              <h3 className="md:hidden" style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: "clamp(16px, 3vw, 20px)", color: "var(--paper)", marginBottom: "8px", textAlign: "center" }}>
                Tap to select
              </h3>

              <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "var(--ghost)", marginBottom: "14px", textAlign: "center" }}>
                PDF · PNG · JPG · JPEG — 2-5 recommended · 10 max
              </p>
              <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--volt)", textDecoration: "underline" }}>
                or browse files
              </span>
            </>
          ) : (
            <div style={{ width: "100%" }} onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--ash)" }}>
                  {files.length} file{files.length !== 1 ? "s" : ""} selected
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                  style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--volt)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}
                >
                  + Add more
                </button>
              </div>

              <DocumentStack files={files} onRemove={removeFile} />
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div
            className="mt-3 w-full animate-slideDown"
            style={{ maxWidth: "600px" }}
          >
            <div
              className="px-4 py-3 rounded-lg"
              style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", fontFamily: "'Inter', sans-serif", fontSize: "14px", color: "var(--error)" }}
            >
              {error}
            </div>
            {/* Retry button — only shown when upload already succeeded */}
            {pendingSessionId && (
              <motion.button
                onClick={handleAnalyze}
                className="mt-3 w-full flex items-center justify-center gap-2"
                style={{
                  height: "48px",
                  borderRadius: "var(--radius-btn)",
                  background: "rgba(245,166,35,0.08)",
                  border: "1px solid rgba(245,166,35,0.4)",
                  cursor: "pointer",
                  fontFamily: "'DM Sans', sans-serif",
                  fontWeight: 700,
                  fontSize: "15px",
                  color: "var(--caution)",
                }}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
              >
                <RefreshCw size={15} />
                Retry Analysis — documents still uploaded
              </motion.button>
            )}
          </div>
        )}

        {/* Slow analysis warning for large batches */}
        {files.length >= 5 && !isLoading && (
          <motion.div
            className="mt-3 w-full flex items-start gap-2 px-4 py-3 rounded-lg animate-slideDown"
            style={{
              maxWidth: "600px",
              background: "rgba(245,166,35,0.07)",
              border: "1px solid rgba(245,166,35,0.25)",
            }}
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <span style={{ fontSize: "14px", flexShrink: 0, marginTop: "1px" }}>⏱️</span>
            <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "13px", lineHeight: 1.5, color: "var(--caution)", margin: 0 }}>
              <strong style={{ fontWeight: 600 }}>{files.length} files detected.</strong>{" "}
              Analysis may take <strong style={{ fontWeight: 600 }}>2–4 minutes</strong> for large batches — the AMD MI300X processes all documents in parallel, but more files means more work.
            </p>
          </motion.div>
        )}

        {/* Analyze button */}
        {files.length > 0 && !isLoading && (
          <motion.div
            className="mt-5 w-full animate-slideUp"
            style={{ maxWidth: "600px" }}
            animate={{ scale: [1, 1.02, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          >
            <PrimaryButton
              onClick={handleAnalyze}
              style={{
                width: "100%",
                height: "56px",
                boxShadow: "0 0 24px rgba(59,123,246,0.35), 0 0 60px rgba(59,123,246,0.12)",
              }}
            >
              <span style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 700, fontSize: "16px" }}>
                Analyze {files.length} Document{files.length !== 1 ? "s" : ""}
              </span>
            </PrimaryButton>
          </motion.div>
        )}

        {/* Loading / processing view */}
        {isLoading && (
          <motion.div
            className="mt-5 flex flex-col items-center gap-5 w-full"
            style={{ maxWidth: "600px" }}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
          >
            <div
              className="w-full rounded-xl p-5"
              style={{
                background: "var(--lead)",
                border: "1px solid var(--volt-border)",
                animation: "borderPulse 2s ease-in-out infinite",
                position: "relative",
                overflow: "hidden",
              }}
            >
              {/* Header with AMD icon + orbiting particles */}
              <div className="flex items-center gap-3 mb-4">
                <div style={{ width: "40px", height: "40px", position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "var(--volt-dim)", display: "flex", alignItems: "center", justifyContent: "center", position: "relative", zIndex: 1 }}>
                    <Loader size={16} style={{ color: "var(--volt)" }} className="animate-spin-slow" />
                  </div>

                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      aria-hidden="true"
                      className="animate-voltPulse"
                      style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--amd-signal)", display: "inline-block", flexShrink: 0 }}
                    />
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "14px", fontWeight: 600, color: "var(--amd-signal)" }}>
                      AMD MI300X Processing
                    </span>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "14px", fontWeight: 600, color: "var(--volt)", marginLeft: "auto" }}>
                      {elapsedSeconds}s
                    </span>
                  </div>
                  <AnimatePresence mode="wait">
                    <motion.span
                      key={loadingStage}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      transition={{ duration: 0.3 }}
                      style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", color: "var(--ghost)", display: "block" }}
                    >
                      {LOADING_STAGES[loadingStage].label}…
                    </motion.span>
                  </AnimatePresence>
                </div>
              </div>

              {/* Premium progress bar */}
              <div style={{ height: "4px", background: "var(--graphite)", borderRadius: "2px", overflow: "hidden", marginBottom: "16px" }}>
                <div
                  className="progress-bar-premium"
                  style={{
                    height: "100%",
                    width: `${((loadingStage + 1) / LOADING_STAGES.length) * 100}%`,
                    transition: "width 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
                  }}
                />
              </div>

              {/* Dynamic slow-connection / status message */}
              {(slowMessage || files.length >= 5) && (
                <AnimatePresence mode="wait">
                  <motion.div
                    key={slowMessage ?? "batch-notice"}
                    className="flex items-center gap-2 mb-3 px-3 py-2 rounded-lg"
                    style={{ background: "rgba(245,166,35,0.07)", border: "1px solid rgba(245,166,35,0.2)" }}
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <span style={{ fontSize: "12px", flexShrink: 0 }}>⏱️</span>
                    <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", color: "var(--caution)", margin: 0 }}>
                      {slowMessage
                        ? slowMessage
                        : `Processing ${files.length} files — this may take a few minutes. Hang tight!`}
                    </p>
                  </motion.div>
                </AnimatePresence>
              )}

              {/* Stage steps with AnimatePresence */}
              <div className="flex flex-wrap gap-x-4 gap-y-2.5 items-center">
                {LOADING_STAGES.map((stage, i) => (
                  <motion.div
                    key={i}
                    className="flex items-center gap-1.5"
                    initial={{ opacity: 0, x: -8 }}
                    animate={{
                      opacity: 1,
                      x: 0,
                      scale: i === loadingStage ? [1, 1.04, 1] : 1,
                    }}
                    transition={{
                      opacity: { duration: 0.3, delay: i * 0.1 },
                      x: { type: "spring", stiffness: 300, damping: 20, delay: i * 0.1 },
                      scale: { duration: 0.6, repeat: i === loadingStage ? Infinity : 0, ease: "easeInOut" },
                    }}
                  >
                    {i < loadingStage ? (
                      <motion.div
                        initial={{ scale: 0.5 }}
                        animate={{ scale: 1 }}
                        transition={{ type: "spring", stiffness: 400, damping: 15 }}
                      >
                        <CheckCircle size={14} style={{ color: "var(--cleared)", flexShrink: 0 }} />
                      </motion.div>
                    ) : i === loadingStage ? (
                      <div
                        style={{
                          width: "14px", height: "14px", borderRadius: "50%",
                          border: "2px solid var(--volt)",
                          borderTopColor: "transparent",
                          flexShrink: 0,
                        }}
                        className="animate-spin-slow"
                      />
                    ) : (
                      <div style={{ width: "14px", height: "14px", borderRadius: "50%", border: "2px solid var(--rule)", flexShrink: 0 }} />
                    )}
                    <span
                      style={{
                        fontFamily: "'Inter', sans-serif",
                        fontSize: "12px",
                        fontWeight: i === loadingStage ? 600 : 400,
                        color: i < loadingStage ? "var(--cleared)" : i === loadingStage ? "var(--paper)" : "var(--ghost)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {stage.label}
                    </span>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* Quick Scan Panel */}
      <div className="flex flex-col items-center px-4 sm:px-6 py-10 mx-auto" style={{ maxWidth: "1200px" }}>
        <div className="flex items-center gap-2 mb-4">
          <div style={{ flex: 1, height: "1px", background: "var(--rule)" }} />
          <span
            style={{
              fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
              fontSize: "11px",
              fontWeight: 600,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--ghost)",
              whiteSpace: "nowrap",
            }}
          >
            OR TRY INSTANT SCAN
          </span>
          <div style={{ flex: 1, height: "1px", background: "var(--rule)" }} />
        </div>
        <QuickScanPanel />
      </div>

      {/* AMD Trust Strip */}
      <div
        className="w-full py-4 flex items-center justify-center gap-2 mt-4"
        style={{ background: "var(--leaf-dim)", borderTop: "1px solid var(--rule)", borderBottom: "1px solid var(--rule)" }}
      >
        <Zap size={14} style={{ color: "var(--ash)" }} />
        <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "clamp(11px, 2vw, 12px)", fontWeight: 500, color: "var(--ash)", textAlign: "center" }}>
          Running on AMD Instinct MI300X · ROCm-powered embeddings · Enterprise-grade inference
        </p>
      </div>

      {/* How It Works */}
      <div id="how-it-works" className="flex flex-col items-center px-4 py-16">
        <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ash)", marginBottom: "10px" }}>
          HOW IT WORKS
        </p>
        <h2 style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "clamp(20px, 4vw, 28px)", fontWeight: 700, color: "var(--paper)", marginBottom: "40px", textAlign: "center" }}>
          From documents to decisions in 3 steps
        </h2>

        <div className="flex flex-col md:flex-row items-stretch w-full gap-5 md:gap-0" style={{ maxWidth: "1040px" }}>
          {[
            { num: "01", Icon: Upload,   title: "Upload Documents",        desc: "Drop your PDFs, contracts, quotations, invoices — any business document" },
            { num: "02", Icon: Cpu,      title: "AMD AI Analyzes",          desc: "Our AMD-powered AI reads all files simultaneously, detects conflicts across documents" },
            { num: "03", Icon: Sparkles, title: "Make Better Decisions",    desc: "Ask questions in plain language. Get evidence-backed answers with exact source citations" },
          ].map(({ num, Icon, title, desc }, idx) => (
            <motion.div
              key={num}
              className="flex flex-1 items-stretch"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.5, delay: idx * 0.15 }}
            >
              {idx > 0 && (
                <div className="hidden md:block self-center" style={{ flex: "0 0 24px", height: "1px", background: "var(--rule)" }} />
              )}
              <div
                className="flex-1 p-6 group"
                style={{
                  background: "var(--lead)",
                  border: "1px solid var(--rule)",
                  borderRadius: "var(--radius-card)",
                  transition: "border-color 0.25s, transform 0.2s, box-shadow 0.25s",
                  position: "relative",
                  overflow: "hidden",
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.borderColor = "var(--volt-border)";
                  e.currentTarget.style.transform = "translateY(-4px)";
                  e.currentTarget.style.boxShadow = "0 12px 40px rgba(59,123,246,0.12)";
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.borderColor = "var(--rule)";
                  e.currentTarget.style.transform = "translateY(0)";
                  e.currentTarget.style.boxShadow = "none";
                }}
              >
                {/* Step number watermark */}
                <span
                  aria-hidden="true"
                  style={{
                    position: "absolute",
                    top: "12px",
                    right: "16px",
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: "48px",
                    fontWeight: 700,
                    color: "rgba(59,123,246,0.06)",
                    lineHeight: 1,
                    pointerEvents: "none",
                  }}
                >
                  {num}
                </span>
                <div
                  style={{
                    width: "44px",
                    height: "44px",
                    borderRadius: "10px",
                    background: "var(--volt-dim)",
                    border: "1px solid var(--volt-border)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: "16px",
                    transition: "background 0.2s, transform 0.2s",
                  }}
                >
                  <Icon size={22} style={{ color: "var(--volt)" }} />
                </div>
                <h3 style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "18px", fontWeight: 600, color: "var(--paper)", marginBottom: "8px" }}>{title}</h3>
                <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "15px", fontWeight: 400, lineHeight: 1.6, color: "var(--ash)" }}>{desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Demo CTA */}
      <div className="flex justify-center px-4 pb-16">
        <div
          className="flex flex-col items-center rounded-2xl px-6 py-8 w-full"
          style={{ maxWidth: "min(600px, 100%)", background: "var(--lead)", border: "1px solid var(--volt-border)" }}
        >
          <h3 style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "clamp(16px, 3vw, 20px)", fontWeight: 600, color: "var(--paper)", marginBottom: "8px", textAlign: "center" }}>
            See it in action — no upload needed
          </h3>
          <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "15px", color: "var(--ash)", marginBottom: "20px", textAlign: "center" }}>
            Try with pre-loaded procurement documents
          </p>
          <Link to="/demo">
            <PrimaryButton>Try Demo</PrimaryButton>
          </Link>
        </div>
      </div>
    </div>
  );
}
