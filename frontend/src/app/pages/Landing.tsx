import { useRef, useState, useEffect, type DragEvent } from "react";
import { useNavigate } from "react-router";
import { NavigationBar } from "../components/NavigationBar";
import { PrimaryButton, GhostButton } from "../components/Buttons";
import { DocumentStack } from "../components/DocumentStack";
import {
  Upload,
  Cpu,
  Leaf,
  CheckCircle,
  Loader,
  RefreshCw,
  Search,
  BarChart3,
} from "lucide-react";
import { Link } from "react-router";
import { uploadDocuments, analyzeDocuments, warmupServer } from "../../lib/api";
import { toast } from "sonner";
import { useAppDispatch } from "../../lib/store";
import { motion, AnimatePresence } from "framer-motion";
import { QuickScanPanel } from "../components/QuickScanPanel";

const LOADING_STAGES = [
  { label: "Extracting text", icon: "📄" },
  { label: "Embedding claims", icon: "⚡" },
  { label: "AI analysis (5 parallel checks)", icon: "🧠" },
  { label: "Detecting contradictions", icon: "🔍" },
  { label: "Building greenwash report", icon: "📊" },
];

const SLOW_MESSAGES = [
  { afterSeconds: 20, message: "Server is warming up — hang tight..." },
  { afterSeconds: 40, message: "Still running — GreenLens AI is analyzing your claims..." },
  { afterSeconds: 70, message: "Almost there — large documents take a bit longer..." },
  { afterSeconds: 100, message: "Due to high demand, the server is warming up. Please retry — it should work on the next attempt!" },
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

  useEffect(() => { warmupServer(); }, []);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); };
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); };
  const handleDrop = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); addFiles(Array.from(e.dataTransfer.files)); };
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => { if (e.target.files) { addFiles(Array.from(e.target.files)); e.target.value = ""; } };

  const addFiles = (incoming: File[]) => {
    setError(null);
    const accepted = incoming.filter((f) => {
      const mime = f.type.toLowerCase();
      const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
      return (["application/pdf", "image/png", "image/jpeg", "image/jpg"].includes(mime) || ["pdf", "png", "jpg", "jpeg"].includes(ext));
    });
    const rejected = incoming.length - accepted.length;
    if (rejected > 0) setError(`${rejected} file(s) skipped — only PDF, PNG, and JPEG are supported.`);
    setFiles((prev) => {
      const combined = [...prev, ...accepted];
      if (combined.length > 10) { setError("You can upload up to 10 files at a time."); return combined.slice(0, 10); }
      return combined;
    });
  };

  const removeFile = (index: number) => { setFiles((prev) => prev.filter((_, i) => i !== index)); };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => { if (e.key === 'Escape') { setFiles([]); } };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!files.length && !pendingSessionId) return;
    setError(null);
    setIsLoading(true);
    setElapsedSeconds(0);
    setSlowMessage(null);
    if (!pendingSessionId) { dispatch({ type: "RESET" }); }
    setLoadingStage(0);

    let hasShownTimeoutToast = false;
    const timerInterval = setInterval(() => {
      setElapsedSeconds((prev) => {
        const next = prev + 1;
        const msg = [...SLOW_MESSAGES].reverse().find((m) => next >= m.afterSeconds);
        setSlowMessage(msg?.message ?? null);
        if (next === 100 && !hasShownTimeoutToast) {
          hasShownTimeoutToast = true;
          toast.warning("Due to high demand, the server is still warming up. If it doesn't complete soon, please retry.", { duration: 12000 });
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

    const cleanup = () => { stageTimers.forEach(clearTimeout); clearInterval(timerInterval); toast.dismiss(toastId); };

    const doAnalyze = async (isRetry = false): Promise<boolean> => {
      try {
        let currentSessionId = pendingSessionId;
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
          toast.loading('Reconnected — resuming analysis...', { id: toastId });
        }
        const analyzeResult = await analyzeDocuments(currentSessionId);
        if (!analyzeResult.analysis) { throw new Error("Analysis returned empty — please try again"); }
        dispatch({ type: "SET_ANALYSIS", payload: analyzeResult.analysis });
        setPendingSessionId(null);
        return true;
      } catch (err) {
        const rawMsg = err instanceof Error ? err.message : "Something went wrong.";
        const lower = rawMsg.toLowerCase();
        const isTimeout = lower.includes("timed out") || lower.includes("timeout");
        const isNetwork = lower.includes("network") || lower.includes("fetch") || lower.includes("failed to fetch");
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
      if (success) { cleanup(); setIsLoading(false); navigate("/dashboard"); }
    } catch (err) {
      cleanup();
      const rawMsg = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      const lower = rawMsg.toLowerCase();
      let msg: string;
      let toastMsg: string;
      if (lower.includes("timed out") || lower.includes("timeout")) {
        msg = pendingSessionId
          ? "Server is warming up. Your documents are still uploaded. Click 'Retry Analysis' to try again!"
          : "Server is warming up. Click 'Retry Analysis' to try again!";
        toastMsg = "Server warming up — click Retry to try again";
      } else if (lower.includes("rate") || lower.includes("429") || lower.includes("quota")) {
        msg = "AI service is busy right now. Please wait 60 seconds and try again.";
        toastMsg = msg; setPendingSessionId(null);
      } else if (lower.includes("upload") || lower.includes("413")) {
        msg = "Upload failed — check that your files are valid PDFs or images under 10MB.";
        toastMsg = msg; setPendingSessionId(null);
      } else if (lower.includes("network") || lower.includes("fetch") || lower.includes("failed to fetch")) {
        msg = pendingSessionId
          ? "Connection dropped — your documents are still on the server. Click 'Retry Analysis' to resume."
          : "Connection error — check your internet and try again.";
        toastMsg = "Network error — click Retry to resume";
      } else {
        msg = "Analysis failed. Please try again. If it keeps happening, try with fewer documents.";
        toastMsg = msg; setPendingSessionId(null);
      }
      setError(msg); setSlowMessage(null); toast.error(toastMsg); setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen page-enter" style={{ background: "var(--ink)" }}>
      <NavigationBar />

      {/* Hero Section */}
      <section
        className="flex flex-col items-center justify-center text-center px-4 sm:px-6 mx-auto relative"
        style={{ minHeight: "70vh", maxWidth: "1200px", paddingTop: "60px", paddingBottom: "40px" }}
      >
        {/* Subtle gradient mesh background */}
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            top: "10%",
            left: "50%",
            transform: "translateX(-50%)",
            width: "80%",
            height: "60%",
            background: "radial-gradient(ellipse at center, rgba(61, 220, 132, 0.03) 0%, transparent 70%)",
            pointerEvents: "none",
            filter: "blur(60px)",
            zIndex: 0,
          }}
        />

        {/* Headline */}
        {/* Pill badge */}
        <div
          className="mb-6 animate-slideUp flex items-center gap-2 px-4 py-1.5 rounded-full"
          style={{
            background: "var(--leaf-dim)",
            border: "1px solid var(--leaf-border)",
            position: "relative",
            zIndex: 1,
          }}
        >
          <Leaf size={14} style={{ color: "var(--leaf)" }} />
          <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "13px", fontWeight: 600, color: "var(--leaf)" }}>
            YFS Build for Good 2026
          </span>
        </div>

        {/* Eyebrow */}
        <p
          className="mb-3 animate-slideUp"
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "clamp(12px, 2vw, 13px)",
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--leaf)",
            position: "relative",
            zIndex: 1,
          }}
        >
          GREENWASHING DETECTION PLATFORM
        </p>

        {/* Headline */}
        <h1
          className="mb-6 animate-slideUp"
          style={{
            fontFamily: "'Syne', 'DM Sans', sans-serif",
            fontWeight: 800,
            fontSize: "clamp(40px, 7vw, 72px)",
            lineHeight: 1.08,
            color: "var(--paper)",
            maxWidth: "min(800px, 92vw)",
            position: "relative",
            zIndex: 1,
            letterSpacing: "-0.02em",
          }}
        >
          See through the{" "}
          <span
            style={{
              textDecoration: "underline",
              textDecorationColor: "var(--leaf)",
              textDecorationThickness: "4px",
              textUnderlineOffset: "6px",
            }}
          >
            greenwash
          </span>
          .
        </h1>

        {/* Subheadline */}
        <p
          className="mb-10 animate-slideUp"
          style={{
            animationDelay: "0.08s",
            fontFamily: "'Inter', sans-serif",
            fontWeight: 400,
            fontSize: "clamp(16px, 3vw, 20px)",
            lineHeight: 1.6,
            color: "var(--ash)",
            maxWidth: "min(560px, 92vw)",
            position: "relative",
            zIndex: 1,
          }}
        >
          Upload sustainability reports, packaging claims, and marketing materials.
          Ask anything in plain language. Get evidence-based greenwashing verdicts in under 90 seconds.
        </p>

        {/* CTA Buttons */}
        <div
          className="flex flex-col sm:flex-row items-center gap-4 mb-8 animate-slideUp"
          style={{ animationDelay: "0.15s", position: "relative", zIndex: 1 }}
        >
          <PrimaryButton
            onClick={() => fileInputRef.current?.click()}
            style={{ height: "48px", padding: "12px 28px", fontSize: "15px" }}
          >
            <Upload size={16} />
            Upload Documents
          </PrimaryButton>
          <a href="#quick-scan">
            <GhostButton style={{ height: "48px", padding: "12px 28px", fontSize: "15px", borderColor: "var(--leaf-border)" }}>
              <Search size={16} />
              Try Quick Scan
            </GhostButton>
          </a>
        </div>

        {/* Stats Row */}
        <div
          className="flex items-center gap-8 sm:gap-12 mb-12 animate-slideUp"
          style={{ animationDelay: "0.22s", position: "relative", zIndex: 1 }}
        >
          {[
            { value: "< 90s", label: "Analysis time", color: "var(--paper)" },
            { value: "0-100", label: "Greenwash Score", color: "var(--leaf)" },
            { value: "100%", label: "Evidence-based", color: "var(--paper)" },
          ].map((stat) => (
            <div key={stat.label} className="flex flex-col items-center">
              <span style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "clamp(22px, 4vw, 32px)", fontWeight: 800, color: stat.color }}>
                {stat.value}
              </span>
              <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)", marginTop: "4px" }}>
                {stat.label}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Upload Zone */}
      <section className="flex flex-col items-center px-4 sm:px-6 mb-8 mx-auto" style={{ maxWidth: "1200px" }}>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
          style={{ display: "none" }}
          onChange={handleFileInputChange}
          aria-label="Select files to upload"
        />

        <div
          className="flex flex-col items-center justify-center w-full animate-slideUp"
          style={{
            maxWidth: "640px",
            minHeight: files.length > 0 ? "auto" : "220px",
            borderRadius: "12px",
            background: isDragging ? "var(--leaf-dim)" : "var(--lead)",
            border: `2px dashed ${isDragging ? "var(--leaf)" : "var(--rule)"}`,
            padding: files.length > 0 ? "24px" : "clamp(24px, 5vw, 48px) clamp(16px, 4vw, 32px)",
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
          role="button"
          aria-label="Drop zone for document upload"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInputRef.current?.click(); } }}
        >
          {isDragging && <div className="scan-line" />}

          {files.length === 0 ? (
            <>
              <Upload size={32} style={{ color: "var(--leaf)", marginBottom: "16px" }} aria-hidden="true" />
              <h3 className="hidden md:block" style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontWeight: 600, fontSize: "18px", color: "var(--paper)", marginBottom: "8px", textAlign: "center" }}>
                Drop documents here
              </h3>
              <h3 className="md:hidden" style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontWeight: 600, fontSize: "18px", color: "var(--paper)", marginBottom: "8px", textAlign: "center" }}>
                Tap to select files
              </h3>
              <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "13px", color: "var(--ghost)", marginBottom: "12px", textAlign: "center" }}>
                PDF · PNG · JPG — 2-5 recommended · 10 max
              </p>
              <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--leaf)" }}>
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
                  style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--leaf)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}
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
          <div className="mt-3 w-full animate-slideDown" style={{ maxWidth: "640px" }} role="alert">
            <div className="px-4 py-3 rounded-lg" style={{ background: "var(--flag-red-dim)", border: "1px solid rgba(240,68,82,0.25)", fontFamily: "'Inter', sans-serif", fontSize: "14px", color: "var(--flag-red)" }}>
              {error}
            </div>
            {pendingSessionId && (
              <motion.button
                onClick={handleAnalyze}
                className="mt-3 w-full flex items-center justify-center gap-2"
                style={{ height: "48px", borderRadius: "var(--radius-btn)", background: "rgba(240,169,55,0.08)", border: "1px solid rgba(240,169,55,0.4)", cursor: "pointer", fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: "15px", color: "var(--flag-amber)" }}
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

        {/* Slow analysis warning */}
        {files.length >= 5 && !isLoading && (
          <motion.div
            className="mt-3 w-full flex items-start gap-2 px-4 py-3 rounded-lg"
            style={{ maxWidth: "640px", background: "var(--flag-amber-dim)", border: "1px solid rgba(240,169,55,0.25)" }}
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <span style={{ fontSize: "14px", flexShrink: 0, marginTop: "1px" }}>⏱️</span>
            <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "13px", lineHeight: 1.5, color: "var(--flag-amber)", margin: 0 }}>
              <strong>{files.length} files detected.</strong> Analysis may take 2–4 minutes for large batches.
            </p>
          </motion.div>
        )}

        {/* Analyze button */}
        {files.length > 0 && !isLoading && (
          <motion.div className="mt-5 w-full" style={{ maxWidth: "640px" }} animate={{ scale: [1, 1.01, 1] }} transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}>
            <PrimaryButton onClick={handleAnalyze} style={{ width: "100%", height: "52px", fontSize: "16px", fontWeight: 700 }}>
              Analyze {files.length} Document{files.length !== 1 ? "s" : ""}
            </PrimaryButton>
          </motion.div>
        )}

        {/* Loading state */}
        {isLoading && (
          <motion.div
            className="mt-5 flex flex-col items-center gap-5 w-full"
            style={{ maxWidth: "640px" }}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
          >
            <div className="w-full rounded-xl p-5 glass-card" style={{ border: "1px solid var(--leaf-border)", position: "relative", overflow: "hidden" }}>
              <div className="flex items-center gap-3 mb-4">
                <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "var(--leaf-dim)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Loader size={16} style={{ color: "var(--leaf)" }} className="animate-spin-slow" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span aria-hidden="true" className="animate-voltPulse" style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--leaf)", display: "inline-block" }} />
                    <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", fontWeight: 600, color: "var(--leaf)" }}>GreenLens AI Processing</span>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "13px", fontWeight: 600, color: "var(--ash)", marginLeft: "auto" }}>{elapsedSeconds}s</span>
                  </div>
                  <AnimatePresence mode="wait">
                    <motion.span key={loadingStage} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.3 }} style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", color: "var(--ghost)", display: "block" }}>
                      {LOADING_STAGES[loadingStage].label}…
                    </motion.span>
                  </AnimatePresence>
                </div>
              </div>

              {/* Progress bar */}
              <div style={{ height: "3px", background: "var(--graphite)", borderRadius: "2px", overflow: "hidden", marginBottom: "16px" }}>
                <div className="progress-bar-premium" style={{ height: "100%", width: `${((loadingStage + 1) / LOADING_STAGES.length) * 100}%`, transition: "width 0.6s cubic-bezier(0.4, 0, 0.2, 1)" }} />
              </div>

              {/* Slow message */}
              {(slowMessage || files.length >= 5) && (
                <AnimatePresence mode="wait">
                  <motion.div key={slowMessage ?? "batch"} className="flex items-center gap-2 mb-3 px-3 py-2 rounded-lg" style={{ background: "var(--flag-amber-dim)", border: "1px solid rgba(240,169,55,0.2)" }} initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
                    <span style={{ fontSize: "12px", flexShrink: 0 }}>⏱️</span>
                    <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", color: "var(--flag-amber)", margin: 0 }}>{slowMessage || `Processing ${files.length} files — hang tight!`}</p>
                  </motion.div>
                </AnimatePresence>
              )}

              {/* Stage steps */}
              <div className="flex flex-wrap gap-x-4 gap-y-2.5 items-center" role="status" aria-live="polite">
                {LOADING_STAGES.map((stage, i) => (
                  <motion.div key={i} className="flex items-center gap-1.5" initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0, scale: i === loadingStage ? [1, 1.04, 1] : 1 }} transition={{ opacity: { duration: 0.3, delay: i * 0.1 }, x: { type: "spring", stiffness: 300, damping: 20, delay: i * 0.1 }, scale: { duration: 0.6, repeat: i === loadingStage ? Infinity : 0, ease: "easeInOut" } }}>
                    {i < loadingStage ? (
                      <CheckCircle size={14} style={{ color: "var(--leaf)", flexShrink: 0 }} />
                    ) : i === loadingStage ? (
                      <div style={{ width: "14px", height: "14px", borderRadius: "50%", border: "2px solid var(--leaf)", borderTopColor: "transparent", flexShrink: 0 }} className="animate-spin-slow" />
                    ) : (
                      <div style={{ width: "14px", height: "14px", borderRadius: "50%", border: "2px solid var(--rule)", flexShrink: 0 }} />
                    )}
                    <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", fontWeight: i === loadingStage ? 600 : 400, color: i < loadingStage ? "var(--leaf)" : i === loadingStage ? "var(--paper)" : "var(--ghost)", whiteSpace: "nowrap" }}>
                      {stage.label}
                    </span>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </section>

      {/* Quick Scan Panel — styled as prominent search bar */}
      <section id="quick-scan" className="flex flex-col items-center px-4 sm:px-6 py-12 mx-auto" style={{ maxWidth: "1200px" }}>
        <div className="flex items-center gap-3 mb-6" style={{ width: "100%", maxWidth: "640px" }}>
          <div style={{ flex: 1, height: "1px", background: "var(--rule)" }} />
          <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--ghost)", whiteSpace: "nowrap" }}>
            or try instant scan
          </span>
          <div style={{ flex: 1, height: "1px", background: "var(--rule)" }} />
        </div>
        <QuickScanPanel />
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="flex flex-col items-center px-4 py-20">
        <h2
          className="section-header mb-3"
          style={{ fontSize: "clamp(12px, 2vw, 13px)", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--leaf)", fontFamily: "'Inter', sans-serif" }}
        >
          How it works
        </h2>
        <p
          style={{
            fontFamily: "'Syne', 'DM Sans', sans-serif",
            fontSize: "clamp(24px, 4vw, 32px)",
            fontWeight: 700,
            color: "var(--paper)",
            marginBottom: "48px",
            textAlign: "center",
          }}
        >
          Three steps to clarity
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full" style={{ maxWidth: "1040px" }}>
          {[
            { Icon: Upload, title: "Upload", desc: "Drop sustainability reports, packaging claims, or marketing copy" },
            { Icon: Cpu, title: "Analyze", desc: "AI reads all documents simultaneously, cross-referencing claims against data" },
            { Icon: BarChart3, title: "Report", desc: "Get a credibility score, flagged claims, and evidence-backed recommendations" },
          ].map(({ Icon, title, desc }, idx) => (
            <motion.div
              key={title}
              className="glass-card hover-lift p-6"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.5, delay: idx * 0.12 }}
            >
              <div
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "10px",
                  background: "var(--leaf-dim)",
                  border: "1px solid var(--leaf-border)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "16px",
                }}
              >
                <Icon size={22} style={{ color: "var(--leaf)" }} aria-hidden="true" />
              </div>
              <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)", marginBottom: "8px" }}>{title}</h3>
              <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--ash)", margin: 0 }}>{desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Demo CTA */}
      <section className="flex justify-center px-4 pb-16">
        <div
          className="flex flex-col items-center glass-card px-6 py-8 w-full"
          style={{ maxWidth: "min(600px, 100%)", border: "1px solid var(--leaf-border)" }}
        >
          <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "clamp(18px, 3vw, 22px)", fontWeight: 700, color: "var(--paper)", marginBottom: "8px", textAlign: "center" }}>
            See it in action
          </h3>
          <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "15px", color: "var(--ash)", marginBottom: "20px", textAlign: "center" }}>
            Try with pre-loaded sample documents — no upload needed
          </p>
          <Link to="/demo">
            <PrimaryButton>Try Demo</PrimaryButton>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer
        className="w-full py-4 flex items-center justify-center gap-2"
        style={{ borderTop: "1px solid var(--rule)" }}
      >
        <Leaf size={12} style={{ color: "var(--ghost)" }} aria-hidden="true" />
        <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "11px", fontWeight: 500, color: "var(--ghost)", textAlign: "center", margin: 0 }}>
          GreenLens · AI-powered greenwashing detection
        </p>
      </footer>
    </div>
  );
}
