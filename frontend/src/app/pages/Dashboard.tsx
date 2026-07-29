import { useState, useRef, useEffect } from "react";
import { NavigationBar } from "../components/NavigationBar";
import { Card } from "../components/Card";
import { RiskBadge, EvidenceTag, EvidenceBox } from "../components/Badges";
import { PrimaryButton, GhostButton } from "../components/Buttons";
import { Link, useNavigate } from "react-router";
import {
  ArrowLeft,
  FileText,
  AlertTriangle,
  Scale,
  Lightbulb,
  ChevronDown,
  Leaf,
  PanelLeft,
  X,
  FileDown,
  Globe,
} from "lucide-react";
import { exportReport, analyzeDocuments } from "../../lib/api";
import { toast } from "sonner";
import { useAppState, useAppDispatch } from "../../lib/store";
import { sanitizeText } from "../../lib/sanitize";
import { GreenwashScoreGauge } from "../components/GreenwashScoreGauge";
import { VerdictStamp } from "../components/VerdictStamp";
import { ConfettiEffect } from "../components/ConfettiEffect";
import { ShareCard } from "../components/ShareCard";
import { ClaimVsRealityRow } from "../components/ClaimVsRealityRow";
import { AchievementBadges } from "../components/AchievementBadges";

export default function Dashboard() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { sessionId, documents, analysis } = useAppState();

  const [conflictExpanded, setConflictExpanded] = useState(true); // default open so judges see it
  const [isExporting, setIsExporting] = useState(false);
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [exportDropdownOpen, setExportDropdownOpen] = useState(false);
  const [confirmNewSession, setConfirmNewSession] = useState(false);
  const exportDropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (exportDropdownRef.current && !exportDropdownRef.current.contains(e.target as Node)) {
        setExportDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Cmd/Ctrl+E keyboard shortcut for export
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
        e.preventDefault();
        handleExport('pdf');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [sessionId]);

  const handleExport = async (format: "pdf" | "docx") => {
    if (!sessionId) return;
    setIsExporting(true);
    setExportDropdownOpen(false);
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

  const handleReanalyze = async () => {
    if (!sessionId || isReanalyzing) return;
    setIsReanalyzing(true);
    try {
      const result = await analyzeDocuments(sessionId, true);
      dispatch({ type: "SET_ANALYSIS", payload: result.analysis });
      toast.success("Re-analysis complete!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Re-analysis failed.");
    } finally {
      setIsReanalyzing(false);
    }
  };

  // Redirect to landing if no analysis
  useEffect(() => {
    if (!analysis) {
      navigate("/", { replace: true });
    }
  }, [analysis, navigate]);

  if (!analysis) {
    return null;
  }

  // Ensure all required sub-objects exist (API may return partial data)
  const safeAnalysis = {
    ...analysis,
    risks: analysis.risks || [],
    conflicts: analysis.conflicts || [],
    comparisonMatrix: analysis.comparisonMatrix || [],
    recommendation: analysis.recommendation || { title: "Analysis Complete", summary: "Review the findings below.", nextSteps: [], confidence: 0.5 },
    suggestedQuestions: analysis.suggestedQuestions || [],
  };

  const hasConflicts = safeAnalysis.conflicts.length > 0;

  const SidebarContent = () => (
    <>
      <div className="p-5 flex items-center justify-between">
        <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--ash)" }}>
          Session Documents
        </span>
        <span className="px-2 py-0.5 rounded-full" style={{ background: "var(--graphite)", fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--paper)" }}>
          {documents.length}
        </span>
      </div>

      <div>
        {documents.map((doc) => {
          const isImage = doc.fileType === "image";
          return (
            <div
              key={doc.id}
              className="px-4 py-3 cursor-pointer"
              style={{ borderBottom: "1px solid var(--rule)", borderLeft: "2px solid transparent", transition: "background 0.15s, border-left-color 0.15s" }}
              onMouseOver={(e) => { e.currentTarget.style.background = "var(--graphite)"; e.currentTarget.style.borderLeftColor = "var(--leaf)"; }}
              onMouseOut={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderLeftColor = "transparent"; }}
            >
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center rounded-md shrink-0" style={{ width: "24px", height: "24px", background: isImage ? "var(--flag-blue-dim)" : "var(--leaf-dim)", border: `1px solid ${isImage ? "rgba(95,168,211,0.3)" : "var(--leaf-border)"}` }}>
                  <span style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "9px", fontWeight: 600, color: isImage ? "var(--flag-blue)" : "var(--leaf)" }}>
                    {isImage ? "IMG" : "PDF"}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="truncate" style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--paper)" }}>
                    {doc.filename}
                  </div>
                  <div style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "11px", color: doc.processingStatus === "completed" ? "var(--leaf)" : "var(--flag-amber)" }}>
                    {doc.processingStatus === "completed" ? (isImage ? "Image OCR Complete" : "Processed") : "Processing..."}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ borderTop: "1px solid var(--rule)", marginTop: "16px" }}>
        <div className="p-4 space-y-3">
          <Link to="/" style={{ display: "block" }}>
            <GhostButton style={{ width: "100%", height: "36px" }}>Upload More</GhostButton>
          </Link>
          <div className="text-center">
            {confirmNewSession ? (
              <div className="flex flex-col gap-2 px-1">
                <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", color: "var(--ash)" }}>
                  Are you sure? This clears all analysis.
                </span>
                <div className="flex gap-2 justify-center">
                  <button
                    onClick={() => { dispatch({ type: "RESET" }); navigate("/"); }}
                    style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 600, color: "var(--paper)", background: "var(--flag-red)", border: "none", cursor: "pointer", padding: "4px 10px", borderRadius: "6px" }}
                  >
                    Yes, clear
                  </button>
                  <button
                    onClick={() => setConfirmNewSession(false)}
                    style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)", background: "none", border: "1px solid var(--rule)", cursor: "pointer", padding: "4px 10px", borderRadius: "6px" }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setConfirmNewSession(true)}
                style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)", background: "none", border: "none", cursor: "pointer" }}
              >
                New Session
              </button>
            )}
          </div>
          <div className="flex items-center justify-center gap-1.5 pt-1">
            <Leaf size={12} style={{ color: "var(--leaf)" }} aria-hidden="true" />
            <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "11px", fontWeight: 500, color: "var(--ghost)" }}>
              Powered by GreenLens AI ? AMD MI300X
            </span>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <div className="min-h-screen page-enter" style={{ background: "var(--ink)" }}>
      <NavigationBar showDemo={false} />

      {/* Breadcrumb */}
      <div className="px-4 sm:px-6 md:px-10 py-3" style={{ borderBottom: "1px solid var(--rule)" }}>
        <div className="flex items-center gap-2">
          {/* Mobile sidebar toggle */}
          <button
            className="md:hidden flex items-center justify-center mr-1"
            onClick={() => setSidebarOpen(true)}
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ash)", padding: "4px" }}
          >
            <PanelLeft size={18} />
          </button>
          <Link to="/" className="inline-flex items-center gap-1.5" style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)" }}>
            <ArrowLeft size={13} />Upload
          </Link>
          <span style={{ color: "var(--ghost)" }}>/</span>
          <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--paper)" }}>
            Analysis Dashboard
          </span>
        </div>
      </div>

      <div className="flex relative">
        {/* Desktop Sidebar */}
        <div
          className="hidden md:block shrink-0"
          style={{ width: "260px", minHeight: "calc(100vh - 100px)", background: "var(--lead)", borderRight: "1px solid var(--rule)" }}
        >
          <SidebarContent />
        </div>

        {/* Mobile Sidebar Drawer */}
        {sidebarOpen && (
          <div
            className="md:hidden fixed inset-0 z-50 animate-fadeIn"
            style={{ background: "rgba(0,0,0,0.6)" }}
            onClick={() => setSidebarOpen(false)}
          >
            <div
              className="animate-slideDown"
              style={{ width: "min(300px, 85vw)", height: "100%", background: "var(--lead)", borderRight: "1px solid var(--rule)", overflowY: "auto" }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-4 py-4" style={{ borderBottom: "1px solid var(--rule)" }}>
                <span style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "15px", fontWeight: 700, color: "var(--paper)" }}>Documents</span>
                <button onClick={() => setSidebarOpen(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ash)" }}>
                  <X size={18} />
                </button>
              </div>
              <SidebarContent />
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="flex-1 min-w-0 animate-fadeIn">
          {/* Top Bar */}
          <div
            className="flex flex-wrap items-center justify-between px-4 sm:px-6 md:px-8 py-3 gap-3"
            style={{ background: "var(--ink)", borderBottom: "1px solid var(--rule)", position: "sticky", top: "52px", zIndex: 10 }}
          >
            <div className="flex items-center gap-2 min-w-0">
              <h2 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "clamp(16px, 3vw, 20px)", fontWeight: 700, color: "var(--paper)", whiteSpace: "nowrap" }}>
                Analysis Results
              </h2>
              <span className="hidden sm:inline" style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)" }}>
                Analyzed {safeAnalysis.analyzedAt ? new Date(safeAnalysis.analyzedAt).toLocaleString() : "just now"}
              </span>
              {documents[0]?.uploadedAt && safeAnalysis.analyzedAt && (() => {
                const ms = new Date(safeAnalysis.analyzedAt).getTime() - new Date(documents[0].uploadedAt).getTime();
                if (ms > 0 && ms < 300000) {
                  return (
                    <span
                      className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full"
                      style={{ background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)", fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "11px", fontWeight: 500, color: "var(--leaf)" }}
                    >
                      Analyzed in {(ms / 1000).toFixed(1)}s
                    </span>
                  );
                }
                return null;
              })()}
            </div>
            <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
              <GhostButton small onClick={handleReanalyze} disabled={isReanalyzing}>
                {isReanalyzing ? (
                  <div className="flex items-center gap-1.5">
                    <div className="animate-spin-slow w-3 h-3 rounded-full" style={{ border: "2px solid var(--ghost)", borderTopColor: "var(--leaf)" }} />
                    <span className="hidden sm:inline">Analyzing</span>
                  </div>
                ) : <><span className="hidden sm:inline">Re-analyze</span><span className="sm:hidden">?</span></>}
              </GhostButton>
              <Link to="/chat"><PrimaryButton small><span className="hidden sm:inline">Ask a Question</span><span className="sm:hidden">Chat</span></PrimaryButton></Link>
              {/* Share Report Card */}
              <div className="hidden sm:block">
                <ShareCard
                  score={safeAnalysis.greenwashScore ?? 50}
                  misleadingCount={(safeAnalysis.risks || []).filter(r => r.level?.toUpperCase() === "HIGH").length}
                  vagueCount={(safeAnalysis.risks || []).filter(r => r.level?.toUpperCase() === "MEDIUM").length}
                  unverifiedCount={(safeAnalysis.risks || []).filter(r => r.level?.toUpperCase() === "LOW").length}
                  documentNames={documents.map(d => d.filename)}
                />
              </div>
              {/* Export Dropdown */}
              <div className="relative" ref={exportDropdownRef}>
                <GhostButton small onClick={() => setExportDropdownOpen(!exportDropdownOpen)} disabled={isExporting} title="Export report (Ctrl+E)">
                  <span className="flex items-center gap-1.5">
                    <FileDown size={14} />
                    <span className="hidden sm:inline">{isExporting ? "Exporting..." : "Export"}</span>
                    <ChevronDown size={12} style={{ transform: exportDropdownOpen ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
                  </span>
                </GhostButton>
                {exportDropdownOpen && (
                  <div
                    className="absolute right-0 top-full mt-1 z-50 rounded-lg py-1 animate-fadeIn"
                    style={{
                      background: "var(--lead)",
                      border: "1px solid var(--rule)",
                      boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
                      minWidth: "180px",
                    }}
                  >
                    <button
                      onClick={() => handleExport("pdf")}
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
                        <FileText size={14} style={{ color: "var(--leaf)" }} />
                      </div>
                      <div>
                        <div style={{ fontWeight: 500 }}>Export as PDF</div>
                        <div style={{ fontSize: "11px", color: "var(--ghost)" }}>Professional report format</div>
                      </div>
                    </button>
                    <button
                      onClick={() => handleExport("docx")}
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
                      <div className="flex items-center justify-center rounded" style={{ width: "28px", height: "28px", background: "var(--flag-blue-dim)", border: "1px solid rgba(95,168,211,0.25)" }}>
                        <FileDown size={14} style={{ color: "var(--flag-blue)" }} />
                      </div>
                      <div>
                        <div style={{ fontWeight: 500 }}>Export as DOCX</div>
                        <div style={{ fontSize: "11px", color: "var(--ghost)" }}>Editable Word document</div>
                      </div>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="p-4 sm:p-6 md:p-8 space-y-6">

            {/* Confetti on first load */}
            <ConfettiEffect />

            {/* Key Finding Banner */}
            {analysis && (() => {
              const bannerScore = safeAnalysis.greenwashScore;
              const bannerScoreDisplay = bannerScore != null ? bannerScore : "N/A";
              const bannerBand = bannerScore == null
                ? { label: "Awaiting analysis", color: "var(--ghost)" }
                : bannerScore <= 30
                  ? { label: "Mostly Greenwashing", color: "var(--flag-red)" }
                  : bannerScore <= 60
                    ? { label: "Vague / Mixed Signals", color: "var(--flag-amber)" }
                    : { label: "Credible", color: "var(--leaf)" };
              if (!bannerBand || !bannerBand.label) return null;
              const topRiskRaw = safeAnalysis.risks?.[0]?.description;
              const topRisk = topRiskRaw
                ? (topRiskRaw.split(".")[0] || topRiskRaw).slice(0, 100) + (topRiskRaw.length > 100 ? "?" : "")
                : "See the full breakdown below.";

              return (
                <div
                  id="key-finding-banner"
                  className="rounded-xl"
                  style={{
                    background: "var(--leaf-dim)",
                    border: "1px solid var(--leaf-border)",
                    borderLeft: `4px solid ${bannerBand.color}`,
                    padding: "16px",
                  }}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <p style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--ash)", margin: 0 }}>
                      This analysis scored{" "}
                      <span style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, color: bannerBand.color }}>
                        {bannerScoreDisplay}/100
                      </span>
                      {" ? "}
                      <span style={{ fontWeight: 600, color: bannerBand.color }}>{bannerBand.label}</span>.{" "}
                      <span style={{ color: "var(--ash)" }}>{topRisk}</span>
                    </p>
                    <a
                      href="#contradiction-section"
                      onClick={(e) => {
                        e.preventDefault();
                        const target = document.getElementById("contradiction-section") || document.getElementById("greenwash-flags-section");
                        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
                      }}
                      style={{
                        fontFamily: "'IBM Plex Sans', sans-serif",
                        fontSize: "12px",
                        fontWeight: 500,
                        color: "var(--leaf)",
                        textDecoration: "none",
                        whiteSpace: "nowrap",
                        cursor: "pointer",
                      }}
                    >
                      See details ?
                    </a>
                  </div>
                </div>
              );
            })()}

            {/* Greenwash Score Gauge ? HERO position with Verdict Stamp */}
            <div style={{ position: "relative", maxWidth: "520px", margin: "0 auto" }}>
              <GreenwashScoreGauge score={safeAnalysis.greenwashScore} />
              {safeAnalysis.greenwashScore != null && safeAnalysis.greenwashScore !== undefined && <VerdictStamp score={safeAnalysis.greenwashScore} />}
            </div>

            {/* Achievement Badges */}
            <AchievementBadges
              documentsAnalyzed={documents.length}
              contradictionsFound={(safeAnalysis.conflicts || []).length}
              flagsFound={(safeAnalysis.risks || []).length}
            />
            {hasConflicts && (
              <div id="contradiction-section" className="rounded-lg p-4 animate-slideDown" style={{ background: "var(--flag-red-dim)", border: "1px solid rgba(240,68,82,0.25)", borderLeft: "4px solid var(--flag-red)" }}>
                <div className="flex items-start sm:items-center justify-between gap-3 mb-4 flex-wrap">
                  <div className="flex items-center gap-3 flex-wrap">
                    <AlertTriangle size={20} style={{ color: "var(--flag-red)", flexShrink: 0 }} aria-hidden="true" />
                    <span style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "15px", fontWeight: 700, letterSpacing: "0.02em", textTransform: "uppercase", color: "var(--flag-red)" }}>
                      {"\u26A0\uFE0F"} Contradiction
                    </span>
                    <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", color: "var(--ash)" }}>
                      {(safeAnalysis.conflicts || []).length} contradiction{(safeAnalysis.conflicts || []).length !== 1 ? "s" : ""} found
                    </span>
                  </div>
                  <button
                    onClick={() => setConflictExpanded(!conflictExpanded)}
                    style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--flag-red)", background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", whiteSpace: "nowrap" }}
                  >
                    View Details
                    <ChevronDown size={14} style={{ transform: conflictExpanded ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
                  </button>
                </div>

                {conflictExpanded && (
                  <div style={{ paddingTop: "16px", borderTop: "1px solid rgba(240,68,82,0.15)" }}>
                    {(safeAnalysis.conflicts || []).map((conflict) => (
                      <div key={conflict.id} className="rounded-lg p-4 mb-3" style={{ background: "rgba(240,68,82,0.05)" }}>
                        <div className="flex items-center gap-2 mb-3 flex-wrap">
                          <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--flag-red)", textTransform: "uppercase" }}>
                            {conflict.type}
                          </span>
                          <RiskBadge variant={conflict.severity} />
                        </div>
                        <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(220px, 100%), 1fr))", marginBottom: "12px" }}>
                          {[conflict.documentA, conflict.documentB].map((doc, i) => (
                            <div key={i}>
                              <div className="mb-2"><EvidenceTag filename={doc.name} /></div>
                              <EvidenceBox quote={doc.excerpt} style={{ background: "var(--paper)" }} />
                            </div>
                          ))}
                        </div>
                        <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--ash)" }}>{conflict.recommendedAction}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Analysis Cards Grid 2-column on desktop */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 stagger-in">
              {/* Executive Summary */}
              <Card style={{ display: 'flex', flexDirection: 'column', maxHeight: '420px' }}>
                <div style={{ flexShrink: 0 }}>
                  <div className="flex items-center justify-between mb-3">
                    <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)" }}>Executive Summary</h3>
                    <FileText size={18} style={{ color: "var(--ghost)" }} />
                  </div>
                  <div style={{ height: "1px", background: "var(--rule)", margin: "12px 0" }} />
                </div>
                <div className="card-scroll" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
                  <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontWeight: 400, fontSize: "15px", lineHeight: 1.6, color: "var(--ash)", marginBottom: "16px" }}>
                    {sanitizeText(safeAnalysis.executiveSummary)}
                  </p>
                  <div style={{ borderTop: "1px solid var(--rule)", paddingTop: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <Leaf size={12} style={{ color: "var(--leaf)" }} aria-hidden="true" />
                    <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)" }}>
                      Generated by GreenLens AI
                    </span>
                  </div>
                </div>
              </Card>

              {/* Web Research Context ? real-time online findings */}
              {analysis.webResearchContext && (
                <Card style={{ display: 'flex', flexDirection: 'column', maxHeight: '320px' }}>
                  <div style={{ flexShrink: 0 }}>
                    <div className="flex items-center justify-between mb-3">
                      <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)" }}>Web Research</h3>
                      <Globe size={18} style={{ color: "var(--ghost)" }} />
                    </div>
                    <div style={{ height: "1px", background: "var(--rule)", margin: "12px 0" }} />
                  </div>
                  <div className="card-scroll" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
                    <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)", marginBottom: "8px" }}>
                      Real-time online sources cross-referenced against document claims:
                    </p>
                    <pre style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", lineHeight: 1.5, color: "var(--ash)", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                      {analysis.webResearchContext}
                    </pre>
                  </div>
                </Card>
              )}

              {/* Greenwash Flags */}
              <div id="greenwash-flags-section">
              <Card style={{ display: 'flex', flexDirection: 'column', maxHeight: '420px' }}>
                <div style={{ flexShrink: 0 }}>
                  <div className="flex items-center justify-between mb-3">
                    <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)" }}>Greenwash Flags</h3>
                    <AlertTriangle size={18} style={{ color: "var(--ghost)" }} />
                  </div>
                  <div style={{ height: "1px", background: "var(--rule)", margin: "12px 0" }} />
                </div>
                <div className="card-scroll" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
                  <div className="space-y-3">
                    {(safeAnalysis.risks || []).length === 0 && (
                      <div className="flex flex-col items-center py-6 gap-2">
                        <div style={{ width: "36px", height: "36px", borderRadius: "50%", background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <span style={{ fontSize: "18px" }}>?</span>
                        </div>
                        <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", color: "var(--leaf)", fontWeight: 500 }}>No greenwash flags</p>
                        <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", color: "var(--ghost)", textAlign: "center" }}>GreenLens AI found no greenwashing signals in these claims.</p>
                      </div>
                    )}
                    {(safeAnalysis.risks || []).map((risk) => (
                      <div key={risk.id} className="flex gap-3">
                        <RiskBadge variant={risk.level} />
                        <div className="flex-1 min-w-0">
                          <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "15px", lineHeight: 1.6, color: "var(--paper)", marginBottom: "4px" }}>
                            {sanitizeText(risk.description)}
                          </p>
                          <EvidenceTag filename={risk.sourceDocument} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
              </div>

              {/* Claim vs. Reality */}
              <Card style={{ display: 'flex', flexDirection: 'column', maxHeight: '420px' }}>
                <div style={{ flexShrink: 0 }}>
                  <div className="flex items-center justify-between mb-3">
                    <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)" }}>Claim vs. Reality</h3>
                    <Scale size={18} style={{ color: "var(--ghost)" }} />
                  </div>
                  <div style={{ height: "1px", background: "var(--rule)", margin: "12px 0" }} />
                </div>
                <div className="card-scroll space-y-3" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
                  {(safeAnalysis.comparisonMatrix || []).map((row) => (
                    <ClaimVsRealityRow key={row.field} row={row} />
                  ))}
                </div>
              </Card>

              {/* AI Recommendation ? spans full width */}
              <Card className="md:col-span-2" style={{ display: 'flex', flexDirection: 'column', background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)" }}>
                <div style={{ flexShrink: 0 }}>
                  <div className="flex items-center justify-between mb-3">
                    <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)" }}>What To Do Next</h3>
                    <Lightbulb size={18} style={{ color: "var(--ghost)" }} />
                  </div>
                  <div style={{ height: "1px", background: "var(--leaf-border)", margin: "12px 0" }} />
                </div>
                <div>
                  <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "15px", lineHeight: 1.6, color: "var(--ash)", marginBottom: "12px" }}>
                    Use the <strong style={{ color: "var(--leaf)" }}>Chat Copilot</strong> to ask specific questions about the greenwashing claims in your documents. The AI has already analyzed the content and can provide detailed, evidence-based answers.
                  </p>
                  <div style={{ borderTop: "1px solid var(--leaf-border)", paddingTop: "16px" }}>
                    <Link to="/chat" style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--leaf)", textDecoration: "none" }}>
                      Ask follow-up questions ?
                    </Link>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
