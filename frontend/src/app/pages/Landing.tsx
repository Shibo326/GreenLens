import { useRef, useState, useEffect, type DragEvent } from "react";
import { useNavigate } from "react-router";
import { NavigationBar } from "../components/NavigationBar";
import { PrimaryButton, GhostButton } from "../components/Buttons";
import { DocumentStack } from "../components/DocumentStack";
import { ClaimDissection } from "../components/ClaimDissection";
import {
  Upload,
  Camera,
  Cpu,
  Leaf,
  CheckCircle,
  Loader,
  RefreshCw,
  Search,
  BarChart3,
  ExternalLink,
  Globe,
} from "lucide-react";
import { Link } from "react-router";
import { uploadDocuments, analyzeDocuments, warmupServer, fetchNews, scanUrl } from "../../lib/api";
import type { NewsArticle } from "../../lib/api";
import type { QuickScanResponse } from "../../lib/types";
import { toast } from "sonner";
import { useAppDispatch } from "../../lib/store";
import { motion, AnimatePresence } from "framer-motion";
import { QuickScanPanel } from "../components/QuickScanPanel";
import { OnboardingOverlay } from "../components/OnboardingOverlay";

const LOADING_STAGES = [
  { label: "Extracting text", icon: "??" },
  { label: "Embedding claims", icon: "?" },
  { label: "AI analysis (5 parallel checks)", icon: "??" },
  { label: "Detecting contradictions", icon: "??" },
  { label: "Building greenwash report", icon: "??" },
];

const SLOW_MESSAGES = [
  { afterSeconds: 20, message: "Server is warming up  hang tight..." },
  { afterSeconds: 40, message: "Still running  GreenLens AI is analyzing your claims..." },
  { afterSeconds: 70, message: "Almost there  large documents take a bit longer..." },
  { afterSeconds: 100, message: "Due to high demand, the server is warming up. Please retry  it should work on the next attempt!" },
];

export default function Landing() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

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
  const handleCameraInputChange = (e: React.ChangeEvent<HTMLInputElement>) => { if (e.target.files) { addFiles(Array.from(e.target.files)); e.target.value = ""; } };

  const addFiles = (incoming: File[]) => {
    setError(null);
    const accepted = incoming.filter((f) => {
      const mime = f.type.toLowerCase();
      const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
      return (["application/pdf", "image/png", "image/jpeg", "image/jpg"].includes(mime) || ["pdf", "png", "jpg", "jpeg"].includes(ext));
    });
    const rejected = incoming.length - accepted.length;
    if (rejected > 0) setError(`${rejected} file(s) skipped  only PDF, PNG, and JPEG are supported.`);
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

  // Greenwashing News state
  const [newsArticles, setNewsArticles] = useState<NewsArticle[]>([]);
  const [newsLoading, setNewsLoading] = useState(true);
  const [newsError, setNewsError] = useState(false);

  // URL Scanner state
  const [urlInput, setUrlInput] = useState("");
  const [urlLoading, setUrlLoading] = useState(false);
  const [urlResult, setUrlResult] = useState<QuickScanResponse | null>(null);
  const [urlError, setUrlError] = useState<string | null>(null);

  const handleUrlScan = async () => {
    const trimmed = urlInput.trim();
    if (!trimmed || urlLoading) return;
    setUrlLoading(true);
    setUrlError(null);
    setUrlResult(null);
    try {
      const response = await scanUrl(trimmed);
      setUrlResult(response);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "URL scan failed.";
      if (msg.toLowerCase().includes("fetch") || msg.toLowerCase().includes("network")) {
        setUrlError("Backend not reachable. Start the backend server or check your connection.");
      } else {
        setUrlError(msg);
      }
    } finally {
      setUrlLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchNews();
        if (!cancelled) {
          setNewsArticles(data.articles.slice(0, 6));
          setNewsLoading(false);
        }
      } catch {
        if (!cancelled) {
          setNewsError(true);
          setNewsLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
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
          toast.loading('Reconnected resuming analysis...', { id: toastId });
        }
        const analyzeResult = await analyzeDocuments(currentSessionId);
        if (!analyzeResult.analysis) { throw new Error("Analysis returned empty please try again"); }
        dispatch({ type: "SET_ANALYSIS", payload: analyzeResult.analysis });
        setPendingSessionId(null);
        return true;
      } catch (err) {
        const rawMsg = err instanceof Error ? err.message : "Something went wrong.";
        const lower = rawMsg.toLowerCase();
        const isTimeout = lower.includes("timed out") || lower.includes("timeout");
        const isNetwork = lower.includes("network") || lower.includes("fetch") || lower.includes("failed to fetch");
        if (!isRetry && (isTimeout || isNetwork) && pendingSessionId) {
          toast.loading('Connection dropped — retrying automatically...', { id: toastId });
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
        toastMsg = "Server warming up  click Retry to try again";
      } else if (lower.includes("rate") || lower.includes("429") || lower.includes("quota")) {
        msg = "AI service is busy right now. Please wait 60 seconds and try again.";
        toastMsg = msg; setPendingSessionId(null);
      } else if (lower.includes("upload") || lower.includes("413")) {
        msg = "Upload failed  check that your files are valid PDFs or images under 10MB.";
        toastMsg = msg; setPendingSessionId(null);
      } else if (lower.includes("network") || lower.includes("fetch") || lower.includes("failed to fetch")) {
        msg = pendingSessionId
          ? "Connection dropped your documents are still on the server. Click 'Retry Analysis' to resume."
          : "Connection error  check your internet and try again.";
        toastMsg = "Network error  click Retry to resume";
      } else {
        msg = "Analysis failed. Please try again. If it keeps happening, try with fewer documents.";
        toastMsg = msg; setPendingSessionId(null);
      }
      setError(msg); setSlowMessage(null); toast.error(toastMsg); setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen page-enter" style={{ background: "var(--ink)" }}>
      <OnboardingOverlay />
      <NavigationBar />

      {/* Hero Section */}
      <section
        className="flex flex-col items-center justify-center text-center px-4 sm:px-6 mx-auto relative"
        style={{ minHeight: "70vh", maxWidth: "1200px", paddingTop: "60px", paddingBottom: "40px" }}
      >
        {/* === ANIMATED BACKGROUND === */}
        {/* Grid pattern */}
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: `linear-gradient(rgba(61, 220, 132, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(61, 220, 132, 0.03) 1px, transparent 1px)`,
            backgroundSize: "60px 60px",
            maskImage: "radial-gradient(ellipse at center, black 30%, transparent 70%)",
            WebkitMaskImage: "radial-gradient(ellipse at center, black 30%, transparent 70%)",
            pointerEvents: "none",
            zIndex: 0,
          }}
        />



        {/* Top gradient fade */}
        <div aria-hidden="true" style={{
          position: "absolute", top: 0, left: 0, right: 0, height: "200px",
          background: "linear-gradient(180deg, var(--ink) 0%, transparent 100%)",
          pointerEvents: "none", zIndex: 0,
        }} />



        {/* Eyebrow */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mb-3"
          style={{
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontSize: "clamp(12px, 2vw, 13px)",
            fontWeight: 600,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "var(--leaf)",
            position: "relative",
            zIndex: 1,
          }}
        >
          GREENWASHING DETECTION PLATFORM
        </motion.p>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="mb-6"
          style={{
            fontFamily: "'Syne', 'DM Sans', sans-serif",
            fontWeight: 800,
            fontSize: "clamp(42px, 7vw, 76px)",
            lineHeight: 1.05,
            color: "var(--paper)",
            maxWidth: "min(800px, 92vw)",
            position: "relative",
            zIndex: 1,
            letterSpacing: "-0.03em",
          }}
        >
          See through the{" "}
          <span
            style={{
              background: "linear-gradient(135deg, var(--leaf) 0%, #6ee7a8 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            greenwash
          </span>
          .
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="mb-10"
          style={{
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontWeight: 400,
            fontSize: "clamp(16px, 3vw, 19px)",
            lineHeight: 1.7,
            color: "var(--ash)",
            maxWidth: "min(560px, 92vw)",
            position: "relative",
            zIndex: 1,
          }}
        >
          Upload sustainability reports, packaging claims, and marketing materials.
          Ask anything in plain language. Get evidence-based greenwashing verdicts in under 90 seconds.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.65 }}
          className="flex flex-col sm:flex-row items-center gap-4 mb-8"
          style={{ position: "relative", zIndex: 1 }}
        >
          {/* Desktop order: Upload first, Quick Scan second */}
          <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }} className="hidden md:block">
            <PrimaryButton
              onClick={() => fileInputRef.current?.click()}
              style={{
                height: "52px",
                padding: "14px 32px",
                fontSize: "15px",
                fontWeight: 600,
                boxShadow: "0 0 20px rgba(61, 220, 132, 0.3), 0 4px 12px rgba(0,0,0,0.3)",
                animation: "pulseGlow 2.5s ease-in-out infinite",
              }}
            >
              <Upload size={16} />
              Upload Documents
            </PrimaryButton>
          </motion.div>
          <a href="#quick-scan" className="hidden md:block">
            <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
              <GhostButton style={{ height: "52px", padding: "14px 32px", fontSize: "15px", fontWeight: 600, borderColor: "var(--leaf-border)" }}>
                <Search size={16} />
                Try Quick Scan
              </GhostButton>
            </motion.div>
          </a>

          {/* Mobile order: Scan a Label first, Upload Documents second */}
          <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }} className="md:hidden">
            <PrimaryButton
              onClick={() => cameraInputRef.current?.click()}
              style={{
                height: "52px",
                padding: "14px 32px",
                fontSize: "15px",
                fontWeight: 600,
                boxShadow: "0 0 20px rgba(61, 220, 132, 0.3), 0 4px 12px rgba(0,0,0,0.3)",
                animation: "pulseGlow 2.5s ease-in-out infinite",
              }}
            >
              <Camera size={16} />
              Scan a Label 📸
            </PrimaryButton>
          </motion.div>
          <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }} className="md:hidden">
            <GhostButton
              onClick={() => fileInputRef.current?.click()}
              style={{ height: "52px", padding: "14px 32px", fontSize: "15px", fontWeight: 600, borderColor: "var(--leaf-border)" }}
            >
              <Upload size={16} />
              Upload Documents
            </GhostButton>
          </motion.div>
        </motion.div>
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
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          style={{ display: "none" }}
          onChange={handleCameraInputChange}
          aria-label="Take a photo of a label"
        />

        <div
          className="flex flex-col items-center justify-center w-full animate-slideUp"
          style={{
            maxWidth: "640px",
            minHeight: files.length > 0 ? "auto" : "220px",
            borderRadius: "16px",
            background: isDragging ? "rgba(61, 220, 132, 0.05)" : "rgba(10, 20, 15, 0.6)",
            border: `2px dashed ${isDragging ? "var(--leaf)" : "rgba(61, 220, 132, 0.2)"}`,
            padding: files.length > 0 ? "24px" : "clamp(24px, 5vw, 48px) clamp(16px, 4vw, 32px)",
            transition: "all 0.3s ease",
            backdropFilter: "blur(8px)",
            boxShadow: isDragging ? "0 0 30px rgba(61, 220, 132, 0.15), inset 0 0 30px rgba(61, 220, 132, 0.05)" : "0 4px 24px rgba(0,0,0,0.2)",
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
              <h3 className="hidden md:block" style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontWeight: 700, fontSize: "18px", color: "var(--paper)", marginBottom: "8px", textAlign: "center" }}>
                Drop documents here
              </h3>
              <h3 className="md:hidden" style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontWeight: 600, fontSize: "18px", color: "var(--paper)", marginBottom: "8px", textAlign: "center" }}>
                Tap to select files
              </h3>
              <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", color: "var(--ghost)", marginBottom: "12px", textAlign: "center" }}>
                Try with pre-loaded sample documents  no upload needed
              </p>
              <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--leaf)" }}>
                or browse files
              </span>
            </>
          ) : (
            <div style={{ width: "100%" }} onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--ash)" }}>
                  {files.length} file{files.length !== 1 ? "s" : ""} selected
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                  style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--leaf)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}
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
            <div className="px-4 py-3 rounded-lg" style={{ background: "var(--flag-red-dim)", border: "1px solid rgba(240,68,82,0.25)", fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", color: "var(--flag-red)" }}>
              {error}
            </div>
            {pendingSessionId && (
              <motion.button
                onClick={handleAnalyze}
                className="mt-3 w-full flex items-center justify-center gap-2"
                style={{ height: "48px", borderRadius: "var(--radius-btn)", background: "rgba(240,169,55,0.08)", border: "1px solid rgba(240,169,55,0.4)", cursor: "pointer", fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontWeight: 600, fontSize: "15px", color: "var(--flag-amber)" }}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
              >
                <RefreshCw size={15} />
                Retry Analysis  documents still uploaded
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
            <span style={{ fontSize: "14px", flexShrink: 0, marginTop: "1px" }}>??</span>
            <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", lineHeight: 1.5, color: "var(--flag-amber)", margin: 0 }}>
              <strong>{files.length} files detected.</strong> Analysis may take 24 minutes for large batches.
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
                    <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", fontWeight: 600, color: "var(--leaf)" }}>GreenLens AI Processing</span>
                    <span style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "13px", fontWeight: 600, color: "var(--ash)", marginLeft: "auto" }}>{elapsedSeconds}s</span>
                  </div>
                  <AnimatePresence mode="wait">
                    <motion.span key={loadingStage} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.3 }} style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", color: "var(--ghost)", display: "block" }}>
                      {LOADING_STAGES[loadingStage].label}
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
                    <span style={{ fontSize: "12px", flexShrink: 0 }}>??</span>
                    <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", color: "var(--flag-amber)", margin: 0 }}>{slowMessage || `Processing ${files.length} files  hang tight!`}</p>
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
                    <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: i === loadingStage ? 600 : 400, color: i < loadingStage ? "var(--leaf)" : i === loadingStage ? "var(--paper)" : "var(--ghost)", whiteSpace: "nowrap" }}>
                      {stage.label}
                    </span>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </section>

      {/* Quick Scan Panel styled as prominent search bar */}
      <section id="quick-scan" className="flex flex-col items-center px-4 sm:px-6 py-12 mx-auto" style={{ maxWidth: "1200px" }}>
        <div className="flex items-center gap-3 mb-6" style={{ width: "100%", maxWidth: "640px" }}>
          <div style={{ flex: 1, height: "1px", background: "var(--rule)" }} />
          <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--ghost)", whiteSpace: "nowrap" }}>
            or try instant scan
          </span>
          <div style={{ flex: 1, height: "1px", background: "var(--rule)" }} />
        </div>
        <QuickScanPanel />

        {/* URL Scanner — compact alternative entry point */}
        <div
          className="mt-6 rounded-xl p-4"
          style={{
            background: "var(--lead)",
            border: "1px solid var(--rule)",
            maxWidth: "600px",
            width: "100%",
          }}
        >
          <div className="flex items-center gap-2 mb-3">
            <Globe size={14} style={{ color: "var(--ghost)" }} />
            <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 600, color: "var(--ghost)", letterSpacing: "0.04em", textTransform: "uppercase" }}>
              or paste a URL
            </span>
          </div>
          <div className="flex gap-2">
            <input
              type="url"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://company.com/sustainability"
              className="flex-1 rounded-lg px-4 py-2.5"
              style={{
                background: "var(--graphite)",
                border: "1px solid var(--rule)",
                color: "var(--paper)",
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "14px",
                outline: "none",
                transition: "border-color 0.2s",
                minWidth: 0,
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--leaf-border)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--rule)"; }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void handleUrlScan();
                }
              }}
              disabled={urlLoading}
            />
            <button
              onClick={() => void handleUrlScan()}
              disabled={!urlInput.trim() || urlLoading}
              className="flex items-center gap-2 rounded-lg px-4"
              style={{
                height: "42px",
                background: !urlInput.trim() || urlLoading ? "var(--graphite)" : "transparent",
                border: `1px solid ${!urlInput.trim() || urlLoading ? "var(--rule)" : "var(--leaf-border)"}`,
                color: !urlInput.trim() || urlLoading ? "var(--ghost)" : "var(--leaf)",
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "13px",
                fontWeight: 600,
                cursor: !urlInput.trim() || urlLoading ? "not-allowed" : "pointer",
                transition: "all 0.2s",
                opacity: !urlInput.trim() || urlLoading ? 0.6 : 1,
                whiteSpace: "nowrap",
              }}
            >
              {urlLoading ? (
                <>
                  <Loader size={14} className="animate-spin-slow" />
                  Scanning...
                </>
              ) : (
                <>
                  <Globe size={14} />
                  Scan URL
                </>
              )}
            </button>
          </div>

          {/* URL Error */}
          {urlError && (
            <div
              className="mt-3 px-4 py-3 rounded-lg"
              style={{
                background: "var(--flag-red-dim)",
                border: "1px solid rgba(240,68,82,0.25)",
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "13px",
                color: "var(--flag-red)",
              }}
            >
              {urlError}
            </div>
          )}

          {/* URL Result */}
          {urlResult && (
            <div className="mt-4 space-y-3 animate-slideUp">
              <div className="rounded-lg p-4" style={{ background: "var(--graphite)", border: "1px solid var(--rule)" }}>
                <div style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "10px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ghost)", marginBottom: "8px" }}>
                  VERDICT
                </div>
                <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--paper)", margin: 0 }}>
                  {urlResult.verdict}
                </p>
              </div>
              {urlResult.whatToLookFor && urlResult.whatToLookFor.length > 0 && (
                <div className="rounded-lg p-4" style={{ background: "var(--graphite)", border: "1px solid var(--rule)" }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "10px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ghost)", marginBottom: "8px" }}>
                    WHAT TO LOOK FOR
                  </div>
                  <ul className="space-y-1.5" style={{ margin: 0, paddingLeft: "16px" }}>
                    {urlResult.whatToLookFor.map((item, i) => (
                      <li key={i} style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", lineHeight: 1.5, color: "var(--ash)" }}>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {urlResult.confidence && (
                <div
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg"
                  style={{
                    background: urlResult.confidence === "HIGH" ? "var(--leaf-dim)" : urlResult.confidence === "MEDIUM" ? "var(--flag-amber-dim)" : "var(--flag-red-dim)",
                    border: `1px solid ${urlResult.confidence === "HIGH" ? "var(--leaf-border)" : urlResult.confidence === "MEDIUM" ? "rgba(240,169,55,0.25)" : "rgba(240,68,82,0.25)"}`,
                    color: urlResult.confidence === "HIGH" ? "var(--leaf)" : urlResult.confidence === "MEDIUM" ? "var(--flag-amber)" : "var(--flag-red)",
                    fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                    fontSize: "12px",
                    fontWeight: 600,
                  }}
                >
                  <CheckCircle size={14} />
                  Confidence: {urlResult.confidence}
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Stats Divider — moved from hero for cleaner layout */}
      <section className="flex flex-col items-center px-4 sm:px-6 pt-8 pb-4 mx-auto" style={{ maxWidth: "1200px" }}>
        <div style={{ width: "100%", maxWidth: "640px", height: "1px", background: "linear-gradient(90deg, transparent, var(--rule), transparent)", marginBottom: "32px" }} />
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
          className="flex items-center gap-8 sm:gap-12"
        >
          {[
            { value: "< 90s", label: "Analysis time", color: "var(--paper)" },
            { value: "0-100", label: "Greenwash Score", color: "var(--leaf)" },
            { value: "100%", label: "Evidence-based", color: "var(--paper)" },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              className="flex flex-col items-center"
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <span style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "clamp(24px, 4vw, 36px)", fontWeight: 800, color: stat.color, letterSpacing: "-0.02em" }}>
                {stat.value}
              </span>
              <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)", marginTop: "4px" }}>
                {stat.label}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="flex flex-col items-center px-4 py-20">
        <div className="section-header mb-3">
          <span style={{ fontSize: "clamp(12px, 2vw, 13px)", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--leaf)", fontFamily: "'IBM Plex Sans', 'Inter', sans-serif" }}>
            How it works
          </span>
        </div>
        <h2
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
        </h2>

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
              <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--ash)", margin: 0 }}>{desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Greenwashing News */}
      <section className="flex flex-col items-center px-4 sm:px-6 py-20 mx-auto" style={{ maxWidth: "1200px" }}>
        <div className="section-header mb-3">
          <span style={{ fontSize: "clamp(12px, 2vw, 13px)", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--leaf)", fontFamily: "'IBM Plex Sans', 'Inter', sans-serif" }}>
            Stay informed
          </span>
        </div>
        <h2
          style={{
            fontFamily: "'Syne', 'DM Sans', sans-serif",
            fontSize: "clamp(24px, 4vw, 32px)",
            fontWeight: 700,
            color: "var(--paper)",
            marginBottom: "12px",
            textAlign: "center",
          }}
        >
          Latest Greenwashing News
        </h2>
        <p
          style={{
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontSize: "15px",
            color: "var(--ash)",
            marginBottom: "48px",
            textAlign: "center",
            maxWidth: "560px",
          }}
        >
          Stay informed with real enforcement actions and regulatory updates
        </p>

        {newsLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 w-full" style={{ maxWidth: "1040px" }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="glass-card p-5"
                style={{ borderLeft: "3px solid var(--rule)", animation: "pulse 1.5s ease-in-out infinite", animationDelay: `${i * 0.1}s` }}
              >
                <div style={{ width: "72px", height: "16px", borderRadius: "8px", background: "var(--graphite)", marginBottom: "12px" }} />
                <div style={{ width: "85%", height: "18px", borderRadius: "4px", background: "var(--graphite)", marginBottom: "10px" }} />
                <div style={{ width: "100%", height: "14px", borderRadius: "4px", background: "var(--graphite)", marginBottom: "6px" }} />
                <div style={{ width: "60%", height: "14px", borderRadius: "4px", background: "var(--graphite)", marginBottom: "16px" }} />
                <div style={{ width: "100px", height: "12px", borderRadius: "4px", background: "var(--graphite)" }} />
              </div>
            ))}
          </div>
        )}

        {newsError && !newsLoading && (
          <div
            className="glass-card px-6 py-8 w-full flex flex-col items-center"
            style={{ maxWidth: "480px", border: "1px solid var(--rule)" }}
          >
            <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", color: "var(--ghost)", textAlign: "center", margin: 0 }}>
              Unable to load news
            </p>
          </div>
        )}

        {!newsLoading && !newsError && newsArticles.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 w-full" style={{ maxWidth: "1040px" }}>
            {newsArticles.map((article, idx) => {
              const categoryColors: Record<string, { border: string; bg: string; text: string }> = {
                enforcement: { border: "var(--flag-red)", bg: "var(--flag-red-dim)", text: "var(--flag-red)" },
                regulation: { border: "var(--flag-amber)", bg: "var(--flag-amber-dim)", text: "var(--flag-amber)" },
                greenwashing: { border: "var(--leaf)", bg: "var(--leaf-dim)", text: "var(--leaf)" },
              };
              const colors = categoryColors[article.category] ?? categoryColors.greenwashing;
              const sourceDomain = (() => {
                try { return new URL(article.url).hostname.replace("www.", ""); } catch { return article.source; }
              })();

              return (
                <motion.div
                  key={idx}
                  className="glass-card hover-lift"
                  style={{ border: "1px solid var(--rule)", borderLeft: `3px solid ${colors.border}`, overflow: "hidden" }}
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ duration: 0.4, delay: idx * 0.08 }}
                >
                  {/* Thumbnail image */}
                  <a href={article.url} target="_blank" rel="noopener noreferrer" style={{ display: "block", position: "relative", height: "140px", overflow: "hidden" }}>
                    <img
                      src={`https://picsum.photos/seed/${encodeURIComponent(article.title.slice(0, 20))}/600/280`}
                      alt=""
                      loading="lazy"
                      style={{ width: "100%", height: "100%", objectFit: "cover", filter: "brightness(0.4) saturate(0.7)", transition: "filter 0.3s ease" }}
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                    <div style={{ position: "absolute", inset: 0, background: `linear-gradient(135deg, ${colors.bg} 0%, transparent 60%)`, pointerEvents: "none" }} />
                    <div style={{ position: "absolute", bottom: "12px", left: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <img
                        src={`https://www.google.com/s2/favicons?domain=${article.source}&sz=32`}
                        alt=""
                        width={20}
                        height={20}
                        style={{ borderRadius: "4px", border: "1px solid rgba(255,255,255,0.2)" }}
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                      />
                      <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "11px", fontWeight: 600, color: "rgba(255,255,255,0.85)" }}>{article.source}</span>
                    </div>
                  </a>

                  <div style={{ padding: "16px 20px 20px" }}>
                  {/* Category badge */}
                  <span
                    style={{
                      display: "inline-block",
                      fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                      fontSize: "11px",
                      fontWeight: 600,
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                      color: colors.text,
                      background: colors.bg,
                      padding: "3px 8px",
                      borderRadius: "6px",
                      marginBottom: "12px",
                    }}
                  >
                    {article.category}
                  </span>

                  {/* Title */}
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Read article: ${article.title}`}
                    style={{
                      display: "block",
                      fontFamily: "'Syne', 'DM Sans', sans-serif",
                      fontSize: "15px",
                      fontWeight: 700,
                      color: "var(--paper)",
                      textDecoration: "none",
                      marginBottom: "8px",
                      lineHeight: 1.4,
                    }}
                  >
                    {article.title}
                  </a>

                  {/* Snippet */}
                  <p
                    style={{
                      fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                      fontSize: "13px",
                      lineHeight: 1.5,
                      color: "var(--ash)",
                      margin: "0 0 14px 0",
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}
                  >
                    {article.snippet}
                  </p>

                  {/* Source + View Source link */}
                  <div className="flex items-center justify-between">
                    <span
                      style={{
                        fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                        fontSize: "12px",
                        color: "var(--ghost)",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <img
                        src={`https://www.google.com/s2/favicons?domain=${sourceDomain}&sz=32`}
                        alt={sourceDomain}
                        width={16}
                        height={16}
                        style={{ borderRadius: "3px", opacity: 0.85 }}
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                      />
                      {sourceDomain}
                      <ExternalLink size={10} style={{ color: "var(--ghost)" }} aria-hidden="true" />
                    </span>
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`View source for: ${article.title}`}
                      style={{
                        fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                        fontSize: "12px",
                        fontWeight: 500,
                        color: "var(--leaf)",
                        textDecoration: "none",
                        display: "flex",
                        alignItems: "center",
                        gap: "3px",
                      }}
                    >
                      View Source <span aria-hidden="true">→</span>
                    </a>
                  </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </section>

      {/* Live Claim Dissection Demo */}
      <section className="flex flex-col items-center px-4 pb-16">
        <div className="section-header mb-3">
          <span style={{ fontSize: "clamp(12px, 2vw, 13px)", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--leaf)", fontFamily: "'Inter', sans-serif" }}>
            Live Demo
          </span>
        </div>
        <h2
          style={{
            fontFamily: "'DM Sans', sans-serif",
            fontSize: "clamp(20px, 3.5vw, 28px)",
            fontWeight: 700,
            color: "var(--paper)",
            marginBottom: "32px",
            textAlign: "center",
          }}
        >
          Watch AI dissect greenwashing in real time
        </h2>
        <ClaimDissection />
      </section>

      {/* Demo CTA */}
      <section className="flex justify-center px-4 pb-20">
        <div
          className="flex flex-col items-center glass-card px-8 py-10 w-full"
          style={{ maxWidth: "min(600px, 100%)", border: "1px solid var(--leaf-border)" }}
        >
          <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "clamp(18px, 3vw, 22px)", fontWeight: 700, color: "var(--paper)", marginBottom: "8px", textAlign: "center" }}>
            See it in action
          </h3>
          <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "15px", color: "var(--ash)", marginBottom: "24px", textAlign: "center" }}>
            Try with pre-loaded sample documents  no upload needed
          </p>
          <Link to="/demo">
            <PrimaryButton style={{ padding: "14px 32px", fontSize: "15px", fontWeight: 600 }}>Try Demo</PrimaryButton>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer
        className="w-full py-5 flex flex-col items-center gap-2"
        style={{ borderTop: "1px solid var(--rule)" }}
      >
        <div className="flex items-center gap-2">
          <Leaf size={12} style={{ color: "var(--leaf)" }} aria-hidden="true" />
          <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ash)", textAlign: "center", margin: 0 }}>
            GreenLens  AI-powered greenwashing detection
          </p>
        </div>
        <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "11px", fontWeight: 400, color: "var(--ghost)", textAlign: "center", margin: 0 }}>
          Powered by AMD MI300X  Built for YFS Build for Good Hackathon
        </p>
      </footer>
    </div>
  );
}
