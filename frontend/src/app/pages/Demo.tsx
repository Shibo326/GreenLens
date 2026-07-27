import { useEffect, useState } from "react";
import { NavigationBar, AMDBadge } from "../components/NavigationBar";
import { Card } from "../components/Card";
import { RiskBadge, EvidenceTag, EvidenceBox } from "../components/Badges";
import { PrimaryButton, GhostButton } from "../components/Buttons";
import { Link } from "react-router";
import {
  Target,
  FileText,
  AlertTriangle,
  Scale,
  Lightbulb,
  ArrowRight,
  Cpu,
  PanelLeft,
  X,
  Zap,
} from "lucide-react";
import { getDemoData } from "../../lib/api";
import { motion } from "framer-motion";
import type { Analysis, PreSeededMessage, UploadedDocument } from "../../lib/types";
import { GreenwashScoreGauge } from "../components/GreenwashScoreGauge";
import { ClaimVsRealityRow } from "../components/ClaimVsRealityRow";

// ─── Offline fallback data ────────────────────────────────────────────────────
const FALLBACK_DOCUMENTS: UploadedDocument[] = [
  { id: "d1", filename: "Demo_Contract_TechCorp.pdf", fileType: "pdf", fileSize: 3800, processingStatus: "completed", uploadedAt: new Date().toISOString() },
  { id: "d2", filename: "Demo_Invoice_TechCorp.pdf", fileType: "pdf", fileSize: 10700, processingStatus: "completed", uploadedAt: new Date().toISOString() },
  { id: "d3", filename: "Demo_Quotation_TechCorp.pdf", fileType: "pdf", fileSize: 5500, processingStatus: "completed", uploadedAt: new Date().toISOString() },
  { id: "d4", filename: "Demo_PurchaseOrder_GlobalDynamics.pdf", fileType: "pdf", fileSize: 6200, processingStatus: "completed", uploadedAt: new Date().toISOString() },
  { id: "d5", filename: "Demo_VendorConfirmation_TechCorp.pdf", fileType: "pdf", fileSize: 7100, processingStatus: "completed", uploadedAt: new Date().toISOString() },
];

const FALLBACK_ANALYSIS: Analysis = {
  analyzedAt: new Date().toISOString(),
  executiveSummary:
    "TechCorp's invoice (INV-2026-0847) charges $112,297.50 against a contracted value of $95,000/yr — a $17,297 overcharge driven by unit price inflation ($525 vs $425 quoted) and removal of the agreed 5% volume discount. The Vendor Confirmation explicitly overrides the Purchase Order's Net 60 payment terms with Net 30, creating a 30-day cash flow exposure of ~$112K. Three compounding risks require immediate action: the contract auto-renews July 17 (39 days away), warranty terms conflict between 24 months (PO) and 12 months (vendor), and jurisdiction clauses are irreconcilable (Texas vs California). Immediate legal review and price reconciliation are required before any payment is processed.",
  risks: [
    {
      id: "r1",
      level: "HIGH",
      description:
        "Invoice overcharge of $13,144.95 (13.2% above PO value): AI License billed at $525/unit vs $425 quoted; 5% volume discount ($4,810) not applied. If paid as invoiced, Global Dynamics overpays by $13,144.95 with no contractual basis for the difference.",
      sourceDocument: "Demo_Invoice_TechCorp.pdf",
      category: "Financial",
    },
    {
      id: "r2",
      level: "HIGH",
      description:
        "Payment terms conflict: PO specifies Net 60; Vendor Confirmation enforces Net 30. Invoice due July 31, 2026. If Net 30 prevails, $112,297.50 is due 30 days earlier than budgeted — a material working capital impact. Late fee disparity (1.5% PO vs 2.5% vendor) compounds exposure.",
      sourceDocument: "Demo_VendorConfirmation_TechCorp.pdf",
      category: "Legal",
    },
    {
      id: "r3",
      level: "HIGH",
      description:
        "Contract auto-renewal deadline is July 17, 2026 — 39 days away. Missing the 60-day notice window locks Global Dynamics into another $95,000 annual term. With unresolved pricing disputes, renewing without renegotiation is financially imprudent.",
      sourceDocument: "Demo_Contract_TechCorp.pdf",
      category: "Strategic",
    },
    {
      id: "r4",
      level: "MEDIUM",
      description:
        "Warranty conflict: PO requires 24 months as condition of award; Vendor Confirmation provides only 12 months standard. TechCorp charges $8,500/year for extended warranty. Accepting delivery without resolving this forfeits $8,500 in contractual protection.",
      sourceDocument: "Demo_PurchaseOrder_GlobalDynamics.pdf",
      category: "Legal",
    },
    {
      id: "r5",
      level: "MEDIUM",
      description:
        "Jurisdiction conflict: PO specifies Texas law and Austin arbitration; Vendor Confirmation specifies California law and San Francisco litigation. In a dispute, choice of law could shift forum costs by $50K–$200K and alter applicable statutes.",
      sourceDocument: "Demo_VendorConfirmation_TechCorp.pdf",
      category: "Legal",
    },
  ],
  comparisonMatrix: [
    {
      field: "AI Platform License Unit Price",
      values: { "Purchase Order (PO)": "$425.00/unit", "Vendor Confirmation": "$525.00/unit" },
      winner: "Purchase Order — $100/unit cheaper, consistent with Quotation QT-2026-0392",
    },
    {
      field: "Total Billed Amount",
      values: { "Purchase Order (PO)": "$99,152.55", "Vendor Confirmation": "$112,297.50" },
      winner: "Purchase Order — $13,144.95 lower; vendor has no contractual basis for higher amount",
    },
    {
      field: "Payment Terms",
      values: { "Purchase Order (PO)": "Net 60 days", "Vendor Confirmation": "Net 30 days" },
      winner: "Purchase Order — 30 extra days of working capital retention",
    },
    {
      field: "Warranty Period",
      values: { "Purchase Order (PO)": "24 months", "Vendor Confirmation": "12 months" },
      winner: "Purchase Order — double the coverage at no additional cost per agreed terms",
    },
    {
      field: "Consulting Rate",
      values: { "Purchase Order (PO)": "$175/hour", "Vendor Confirmation": "$200/hour" },
      winner: "Purchase Order — $25/hr savings = $1,000 on 40-hour engagement",
    },
    {
      field: "Late Payment Penalty",
      values: { "Purchase Order (PO)": "1.5%/month", "Vendor Confirmation": "2.5%/month (compounding)" },
      winner: "Purchase Order — 1% lower penalty, non-compounding",
    },
  ],
  conflicts: [
    {
      id: "c1",
      type: "Unit Price Discrepancy ($100/unit delta)",
      severity: "HIGH",
      documentA: {
        name: "Demo_PurchaseOrder_GlobalDynamics.pdf",
        excerpt: "AI Platform License (Annual) — Enterprise Plus | $425.00 | $45,200.00",
      },
      documentB: {
        name: "Demo_VendorConfirmation_TechCorp.pdf",
        excerpt: "AI Platform License (Annual) — Enterprise Plus | $525.00 | $48,500.00",
      },
      explanation:
        "The PO locks the unit price at $425 based on Quotation QT-2026-0392. The Vendor Confirmation bills $525 and explicitly states this 'supersedes' the quotation. The $100/unit delta generates a $3,300 overcharge on this line alone. TechCorp's claim that the quoted price was 'preliminary' contradicts the quotation's price guarantee clause.",
      recommendedAction:
        "Finance team to formally dispute the unit price variance in writing within 5 business days. Reference Quotation QT-2026-0392 and its price guarantee clause. Withhold payment on the $13,144.95 disputed amount pending written resolution from TechCorp VP Sales.",
    },
    {
      id: "c2",
      type: "Payment Terms Contradiction (Net 60 vs Net 30)",
      severity: "HIGH",
      documentA: {
        name: "Demo_PurchaseOrder_GlobalDynamics.pdf",
        excerpt: "Payment Terms: Net 60 days from invoice receipt date",
      },
      documentB: {
        name: "Demo_VendorConfirmation_TechCorp.pdf",
        excerpt: "Payment Terms: Net 30 days from invoice date — STANDARD TERMS APPLY",
      },
      explanation:
        "PO GD-PROC-2024-11 policy mandates Net 60 for all vendor payments. Vendor Confirmation overrides this with Net 30, making Invoice INV-2026-0847 due July 31 rather than August 30. Paying Net 30 on a $112K invoice represents a 30-day early payment worth approximately $470 in opportunity cost at current rates.",
      recommendedAction:
        "Legal to issue a written notice asserting Net 60 terms per procurement policy GD-PROC-2024-11. Process payment by August 30, 2026. If TechCorp insists on Net 30, escalate to CFO for written approval before any early payment.",
    },
  ],
  recommendation: {
    title: "Dispute Invoice — Withhold $13,144.95 Pending Price Reconciliation",
    summary:
      "The Vendor Confirmation unlawfully overrides three material terms from the Purchase Order: unit price ($100/unit markup), payment terms (Net 30 vs Net 60), and warranty (12 vs 24 months). The $13,144.95 billing gap has no contractual basis. Industry standard in SaaS procurement is to honor the last signed quotation; TechCorp's claim that prices were 'preliminary' is contradicted by QT-2026-0392's explicit price guarantee. Act before July 17 to avoid auto-renewal on disputed terms.",
    nextSteps: [
      "Procurement to send formal price dispute letter citing QT-2026-0392 | Legal team | Within 5 business days",
      "Finance to withhold the $13,144.95 disputed amount from payment | CFO approval required | Before July 31",
      "Legal to send contract non-renewal notice before July 17 deadline | General Counsel | Within 7 days",
      "Schedule renegotiation meeting with TechCorp to align pricing, payment terms, and warranty | Procurement lead | Within 2 weeks",
    ],
    confidence: 0.91,
  },
  suggestedQuestions: [
    "What is the exact dollar amount of the overcharge?",
    "When is the contract auto-renewal deadline?",
    "Which payment terms should we follow?",
    "How does the warranty conflict affect our position?",
    "What should we do before processing payment?",
  ],
};

const FALLBACK_MESSAGES: PreSeededMessage[] = [
  {
    id: "pm1",
    role: "user",
    content: "Which vendor document should we trust for pricing?",
    timestamp: new Date().toISOString(),
  },
  {
    id: "pm2",
    role: "assistant",
    content:
      "Trust the Purchase Order pricing backed by Quotation QT-2026-0392. The quotation's price guarantee clause locks the AI License at $425/unit. The Vendor Confirmation's claim that this was 'preliminary' is legally weak — the quotation explicitly states prices are guaranteed for 60 days and supersede prior communications. The $525/unit in the Vendor Confirmation represents a 23.5% markup with no contractual basis.",
    timestamp: new Date().toISOString(),
    structuredResponse: {
      answer:
        "Trust the Purchase Order pricing backed by Quotation QT-2026-0392. The quotation's price guarantee clause locks the AI License at $425/unit. The Vendor Confirmation's claim that this was 'preliminary' is legally weak — the quotation explicitly states prices are guaranteed for 60 days and supersede prior communications. The $525/unit in the Vendor Confirmation represents a 23.5% markup with no contractual basis.",
      evidence: [
        {
          quote: "PRICE GUARANTEE: This quotation is valid for 60 days from issue date. Prices are guaranteed and will not increase during the validity period.",
          sourceDocument: "Demo_Quotation_TechCorp.pdf",
          documentType: "pdf",
        },
      ],
      risks: "HIGH: If the Vendor Confirmation's pricing is accepted without dispute, Global Dynamics overpays $13,144.95 with no path to recovery.",
      recommendation: "Procurement to formally reject the Vendor Confirmation pricing and invoke the price guarantee in QT-2026-0392 within 5 business days.",
    },
  },
];

// AMD-branded loading screen with premium animations
function DemoLoader() {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--ink)" }}>
      <NavigationBar showDemo={false} />
      <div className="flex-1 flex items-center justify-center px-4">
        <div
          className="flex flex-col items-center gap-6 animate-fadeIn"
          style={{
            background: "var(--lead)",
            border: "1px solid var(--volt-border)",
            borderRadius: "16px",
            padding: "clamp(24px, 6vw, 48px) clamp(24px, 8vw, 64px)",
            maxWidth: "400px",
            width: "100%",
            boxShadow: "0 0 40px rgba(59,123,246,0.08)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Scan line effect */}
          <div className="scan-line" />

          {/* AMD logo area with conic-gradient spinner ring */}
          <div style={{ position: "relative" }}>
            <div style={{ width: "64px", height: "64px", borderRadius: "16px", background: "rgba(237,28,36,0.1)", border: "1px solid rgba(237,28,36,0.25)", display: "flex", alignItems: "center", justifyContent: "center", position: "relative", zIndex: 1 }}>
              <Zap size={28} style={{ color: "var(--amd-signal)" }} />
            </div>
            {/* Animated rotating border */}
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2.5, repeat: Infinity, ease: "linear" }}
              style={{
                position: "absolute",
                inset: "-6px",
                borderRadius: "20px",
                background: "conic-gradient(from 0deg, transparent 0%, rgba(237,28,36,0.6) 25%, transparent 50%)",
                zIndex: 0,
              }}
            />
            <div
              style={{
                position: "absolute",
                inset: "-5px",
                borderRadius: "19px",
                background: "var(--lead)",
                zIndex: 0,
              }}
            />
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2.5, repeat: Infinity, ease: "linear" }}
              style={{
                position: "absolute",
                inset: "-6px",
                borderRadius: "20px",
                border: "2px solid transparent",
                backgroundImage: "conic-gradient(from 0deg, transparent 60%, rgba(237,28,36,0.7) 80%, transparent 100%)",
                backgroundOrigin: "border-box",
                backgroundClip: "border-box",
                WebkitMask: "linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)",
                WebkitMaskComposite: "xor",
                maskComposite: "exclude",
                padding: "2px",
                zIndex: 0,
              }}
            />
          </div>

          {/* Staggered text reveal */}
          <div className="text-center">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)", marginBottom: "6px" }}
            >
              Loading Demo
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "13px", color: "var(--ghost)" }}
            >
              Initializing AMD MI300X inference…
            </motion.div>
          </div>

          {/* Wave-style animated dots */}
          <div className="flex items-center gap-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="wave-dot"
                style={{
                  width: "10px",
                  height: "10px",
                  borderRadius: "50%",
                  background: "var(--volt)",
                  animationDelay: `${i * 0.15}s`,
                }}
              />
            ))}
          </div>

          {/* Progress bar */}
          <div style={{ width: "100%", height: "3px", background: "var(--rule)", borderRadius: "2px", overflow: "hidden" }}>
            <div className="shimmer-bar" style={{ height: "100%", borderRadius: "2px", width: "65%" }} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Demo() {
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [preSeededMessages, setPreSeededMessages] = useState<PreSeededMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    getDemoData()
      .then((data) => { setDocuments(data.documents); setAnalysis(data.analysis); setPreSeededMessages(data.preSeededMessages ?? []); })
      .catch(() => {
        console.info("[Demo] Backend unavailable — using offline fallback");
        setDocuments(FALLBACK_DOCUMENTS);
        setAnalysis(FALLBACK_ANALYSIS);
        setPreSeededMessages(FALLBACK_MESSAGES);
      })
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <DemoLoader />;

  if (!analysis) {
    return (
      <div className="min-h-screen" style={{ background: "var(--ink)" }}>
        <NavigationBar showDemo={false} />
        <div className="flex flex-col items-center pt-24 gap-4 px-4 animate-fadeIn">
          <div className="px-5 py-4 rounded-lg w-full" style={{ maxWidth: "480px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", fontFamily: "'Inter', sans-serif", fontSize: "14px", color: "var(--error)" }}>
            Demo data unavailable.
          </div>
          <Link to="/"><PrimaryButton>Upload your own documents</PrimaryButton></Link>
        </div>
      </div>
    );
  }

  const hasConflicts = analysis.conflicts.length > 0;
  const primaryConflict = analysis.conflicts[0];

  const SidebarContent = () => (
    <>
      <div className="p-5 flex items-center justify-between">
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--ash)" }}>Demo Documents</span>
        <span className="px-2 py-0.5 rounded-full" style={{ background: "var(--graphite)", fontFamily: "'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--paper)" }}>
          {documents.length}
        </span>
      </div>

      <div>
        {documents.map((doc) => {
          const isImage = doc.fileType === "image";
          return (
            <div
              key={doc.id}
              className="px-4 py-3"
              style={{ borderBottom: "1px solid rgba(42,45,62,0.5)", borderLeft: "2px solid transparent", transition: "background 0.15s, border-left-color 0.15s", cursor: "default" }}
              onMouseOver={(e) => { e.currentTarget.style.background = "var(--graphite)"; e.currentTarget.style.borderLeftColor = "var(--volt)"; }}
              onMouseOut={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderLeftColor = "transparent"; }}
            >
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center rounded-md shrink-0" style={{ width: "24px", height: "24px", background: isImage ? "rgba(59,123,246,0.1)" : "rgba(237,28,36,0.1)", border: `1px solid ${isImage ? "rgba(59,123,246,0.3)" : "rgba(237,28,36,0.3)"}` }}>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "9px", fontWeight: 600, color: isImage ? "var(--volt)" : "var(--conflict)" }}>
                    {isImage ? "IMG" : "PDF"}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="truncate" style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--paper)" }}>{doc.filename}</div>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "var(--cleared)" }}>
                    {isImage ? "Image · OCR Complete" : "Processed"}
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
            <PrimaryButton style={{ width: "100%" }}>Upload Your Documents</PrimaryButton>
          </Link>
          <div className="flex justify-center pt-1"><AMDBadge /></div>
        </div>
      </div>
    </>
  );

  return (
    <div className="min-h-screen animate-fadeIn" style={{ background: "var(--ink)" }}>
      <NavigationBar showDemo={false} />

      {/* Demo Banner */}
      <div
        className="flex flex-wrap items-center justify-between px-4 sm:px-8 py-3 gap-3"
        style={{ background: "rgba(245,166,35,0.08)", borderBottom: "1px solid rgba(245,166,35,0.25)" }}
      >
        <div className="flex items-center gap-2">
          <Target size={15} style={{ color: "var(--caution)", flexShrink: 0 }} />
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "13px", fontWeight: 600, color: "var(--caution)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Demo Mode
          </span>
          <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "13px", fontWeight: 500, color: "var(--caution)" }}>
            — Pre-loaded sample procurement documents
          </span>
        </div>
        <Link to="/" style={{ fontFamily: "'Inter', sans-serif", fontSize: "13px", fontWeight: 500, color: "var(--volt)", textDecoration: "none", whiteSpace: "nowrap" }}>
          Try with your own →
        </Link>
      </div>

      <div className="flex relative">
        {/* Desktop sidebar */}
        <div
          className="hidden md:block shrink-0"
          style={{ width: "300px", minHeight: "calc(100vh - 120px)", background: "var(--lead)", borderRight: "1px solid var(--rule)" }}
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
                <span style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "15px", fontWeight: 700, color: "var(--paper)" }}>Demo Documents</span>
                <button onClick={() => setSidebarOpen(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ash)" }}>
                  <X size={18} />
                </button>
              </div>
              <SidebarContent />
            </div>
          </div>
        )}

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* Sub-header */}
          <div
            className="flex flex-wrap items-center justify-between px-4 sm:px-8 py-4 gap-3"
            style={{ borderBottom: "1px solid var(--rule)" }}
          >
            <div className="flex items-center gap-3">
              {/* Mobile sidebar toggle */}
              <button
                className="md:hidden flex items-center justify-center"
                onClick={() => setSidebarOpen(true)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ash)", padding: "4px" }}
              >
                <PanelLeft size={18} />
              </button>
              <div>
                <h2 style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "clamp(16px, 3vw, 20px)", fontWeight: 700, color: "var(--paper)" }}>
                  Sample Procurement Analysis
                </h2>
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)" }}>
                  {documents.length} documents · Demo data
                </span>
              </div>
            </div>
            <AMDBadge />
          </div>

          <div className="p-4 sm:p-6 md:p-8 space-y-5">
            {/* Guided Tour Intro */}
            <div className="rounded-xl p-5" style={{ background: "linear-gradient(135deg, rgba(59,123,246,0.06) 0%, rgba(0,212,255,0.04) 100%)", border: "1px solid var(--volt-border)" }}>
              <div className="flex items-start gap-3">
                <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: "var(--volt-dim)", border: "1px solid var(--volt-border)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Lightbulb size={18} style={{ color: "var(--volt)" }} />
                </div>
                <div>
                  <h3 style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "16px", fontWeight: 700, color: "var(--paper)", marginBottom: "6px" }}>
                    What you're seeing
                  </h3>
                  <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--ash)", margin: 0 }}>
                    This demo shows a complete AI analysis of {documents.length} sample procurement documents — processed in under 90 seconds using AMD Instinct MI300X. 
                    Below you'll see: <strong style={{ color: "var(--paper)" }}>cross-document conflict detection</strong>, an <strong style={{ color: "var(--paper)" }}>executive summary</strong>, <strong style={{ color: "var(--paper)" }}>risk assessment</strong> with severity ratings, 
                    a <strong style={{ color: "var(--paper)" }}>side-by-side comparison matrix</strong>, and an <strong style={{ color: "var(--paper)" }}>AI recommendation</strong> with actionable next steps. 
                    Scroll down to see the AI chat copilot in action.
                  </p>
                </div>
              </div>
            </div>

            {/* Conflict Alert */}
            {hasConflicts && primaryConflict && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "10px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ghost)", background: "var(--graphite)", padding: "3px 8px", borderRadius: "4px" }}>
                    FEATURE 1
                  </span>
                  <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", color: "var(--ash)" }}>
                    Cross-Document Conflict Detection — automatically finds contradictions between documents
                  </span>
                </div>
                <div className="rounded-lg p-4 animate-slideDown" style={{ background: "var(--flag-red-dim)", border: "1px solid rgba(240,68,82,0.25)", borderLeft: "4px solid var(--flag-red)" }}>
                <div className="flex items-center gap-3 mb-4 flex-wrap">
                  <AlertTriangle size={20} style={{ color: "var(--flag-red)", flexShrink: 0 }} />
                  <span style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "16px", fontWeight: 700, color: "var(--flag-red)" }}>Contradiction Detected</span>
                  <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", color: "var(--ash)" }}>
                    {analysis.conflicts.length} critical contradiction{analysis.conflicts.length !== 1 ? "s" : ""} found
                  </span>
                </div>

                <div style={{ paddingTop: "16px", borderTop: "1px solid rgba(237,28,36,0.15)" }}>
                  <div className="rounded-lg p-4" style={{ background: "rgba(237,28,36,0.04)" }}>
                    <div className="flex items-center gap-2 mb-3 flex-wrap">
                      <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--amd-signal)", textTransform: "uppercase" }}>
                        {primaryConflict.type}
                      </span>
                      <RiskBadge variant={primaryConflict.severity} />
                    </div>
                    <div className="grid gap-3 mb-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(200px, 100%), 1fr))" }}>
                      {[primaryConflict.documentA, primaryConflict.documentB].map((doc, i) => (
                        <div key={i} className="rounded-lg p-3" style={{ background: "rgba(237,28,36,0.06)", border: "1px solid rgba(237,28,36,0.15)" }}>
                          <div className="mb-2"><EvidenceTag filename={doc.name} /></div>
                          <EvidenceBox quote={doc.excerpt} style={{ background: "var(--paper)" }} />
                        </div>
                      ))}
                    </div>
                    <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--ash)" }}>{primaryConflict.recommendedAction}</p>
                  </div>
                </div>
              </div>
              </div>
            )}

            {/* Analysis Cards */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "10px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ghost)", background: "var(--graphite)", padding: "3px 8px", borderRadius: "4px" }}>
                  FEATURE 2-5
                </span>
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", color: "var(--ash)" }}>
                  AI-Generated Analysis — executive summary, risk scoring, document comparison, and recommendation
                </span>
              </div>
            {/* Greenwash Score Gauge */}
            <GreenwashScoreGauge score={analysis.greenwashScore} />

            <div className="grid gap-4 sm:gap-5" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(300px, 100%), 1fr))" }}>
              {/* Executive Summary */}
              <Card>
                <div className="flex items-center justify-between mb-3">
                  <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)" }}>Executive Summary</h3>
                  <FileText size={18} style={{ color: "var(--ghost)" }} />
                </div>
                <div style={{ height: "1px", background: "var(--rule)", margin: "12px 0" }} />
                <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "15px", lineHeight: 1.6, color: "var(--ash)", marginBottom: "16px" }}>
                  {analysis.executiveSummary}
                </p>
                <div style={{ borderTop: "1px solid var(--rule)", paddingTop: "12px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
                  <div className="flex items-center gap-1.5">
                    <Cpu size={12} style={{ color: "var(--ghost)" }} />
                    <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)" }}>Generated by AMD Llama 3.2 Vision</span>
                  </div>
                  <AMDBadge />
                </div>
              </Card>

              {/* Risk Analysis */}
              <Card>
                <div className="flex items-center justify-between mb-3">
                  <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)" }}>Risk Analysis</h3>
                  <AlertTriangle size={18} style={{ color: "var(--ghost)" }} />
                </div>
                <div style={{ height: "1px", background: "var(--rule)", margin: "12px 0" }} />
                <div className="space-y-3">
                  {analysis.risks.map((risk) => (
                    <div key={risk.id} className="flex gap-3">
                      <RiskBadge variant={risk.level} />
                      <div className="flex-1 min-w-0">
                        <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "15px", lineHeight: 1.6, color: "var(--paper)", marginBottom: "4px" }}>{risk.description}</p>
                        <EvidenceTag filename={risk.sourceDocument} />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Claim vs. Reality */}
              <Card>
                <div className="flex items-center justify-between mb-3">
                  <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)" }}>Claim vs. Reality</h3>
                  <Scale size={18} style={{ color: "var(--ghost)" }} />
                </div>
                <div style={{ height: "1px", background: "var(--rule)", margin: "12px 0" }} />
                <div className="space-y-3">
                  {analysis.comparisonMatrix.map((row) => (
                    <ClaimVsRealityRow key={row.field} row={row} />
                  ))}
                </div>
              </Card>

              {/* AI Recommendation */}
              <Card style={{ background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)" }}>
                <div className="flex items-center justify-between mb-3">
                  <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)" }}>AI Recommendation</h3>
                  <Lightbulb size={18} style={{ color: "var(--ghost)" }} />
                </div>
                <div style={{ height: "1px", background: "var(--leaf-border)", margin: "12px 0" }} />
                <div className="inline-block px-4 py-2 rounded-full mb-4" style={{ background: "rgba(61,220,132,0.12)", border: "1px solid rgba(61,220,132,0.25)" }}>
                  <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--leaf)" }}>{analysis.recommendation.title}</span>
                </div>
                <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "15px", lineHeight: 1.6, color: "var(--ash)" }}>{analysis.recommendation.summary}</p>
              </Card>
            </div>
            </div>

            {/* Chat Preview + CTA */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "10px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ghost)", background: "var(--graphite)", padding: "3px 8px", borderRadius: "4px" }}>
                  FEATURE 6
                </span>
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", color: "var(--ash)" }}>
                  AI Chat Copilot — ask follow-up questions in plain language, get answers grounded in your documents
                </span>
              </div>
            <div className="rounded-xl p-5 sm:p-6" style={{ background: "var(--lead)", border: "1px solid var(--rule)" }}>
              <div className="flex items-center gap-3 mb-5">
                <div style={{ width: "40px", height: "40px", flexShrink: 0, borderRadius: "10px", background: "var(--graphite)", border: "1px solid rgba(61,220,132,0.4)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <FileText size={18} style={{ color: "var(--leaf)" }} />
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)" }}>GreenLens Copilot Preview</h3>
                  <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", color: "var(--ash)" }}>See how the AI detects greenwashing patterns</p>
                </div>
              </div>

              <div className="space-y-3 mb-5">
                {preSeededMessages.length > 0 ? (
                  preSeededMessages.map((msg) => {
                    const isUser = msg.role === "user";
                    const displayText = isUser
                      ? msg.content
                      : (msg.structuredResponse?.answer ?? msg.content);
                    return (
                      <div key={msg.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                        <div
                          className="rounded-xl px-3 py-2"
                          style={
                            isUser
                              ? { background: "var(--graphite)", maxWidth: "min(400px, 90%)" }
                              : {
                                  background: "var(--lead)",
                                  border: "1px solid var(--rule)",
                                  borderLeft: "3px solid var(--volt)",
                                  maxWidth: "min(500px, 100%)",
                                  padding: "12px",
                                }
                          }
                        >
                          <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--paper)" }}>
                            {displayText}
                          </p>
                          {!isUser && msg.structuredResponse?.evidence && msg.structuredResponse.evidence.length > 0 && (
                            <div className="mt-2 space-y-1.5">
                              {msg.structuredResponse.evidence.map((ev, i) => (
                                <EvidenceBox key={i} quote={ev.quote} />
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <>
                    <div className="flex justify-end">
                      <div className="rounded-xl px-3 py-2" style={{ background: "var(--graphite)", maxWidth: "min(400px, 90%)" }}>
                        <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", color: "var(--paper)" }}>Which supplier is cheapest?</p>
                      </div>
                    </div>
                    <div className="flex justify-start">
                      <div className="rounded-xl p-3" style={{ background: "var(--lead)", border: "1px solid var(--rule)", borderLeft: "3px solid var(--volt)", maxWidth: "min(500px, 100%)" }}>
                        <p style={{ fontFamily: "'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--paper)" }}>
                          {(() => {
                            const priceRow = analysis.comparisonMatrix.find((r) => r.field.toLowerCase().includes("price"));
                            if (!priceRow) return analysis.recommendation.summary;
                            return `${priceRow.winner} is the most competitive at ${priceRow.values[priceRow.winner]} total value.`;
                          })()}
                        </p>
                      </div>
                    </div>
                  </>
                )}
              </div>

              <div className="rounded-lg p-4 sm:p-5" style={{ background: "var(--volt-dim)", border: "1px solid var(--volt-border)" }}>
                <h4 style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)", marginBottom: "14px" }}>
                  Ready to analyze your own documents?
                </h4>
                <div className="flex flex-wrap gap-3">
                  <Link to="/"><PrimaryButton>Upload Documents</PrimaryButton></Link>
                  <Link to="/">
                    <GhostButton>
                      <div className="flex items-center gap-1.5">Try With Your Documents <ArrowRight size={14} /></div>
                    </GhostButton>
                  </Link>
                </div>
              </div>
            </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
