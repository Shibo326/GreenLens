import { useEffect, useState } from "react";
import { NavigationBar } from "../components/NavigationBar";
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
  PanelLeft,
  X,
  Leaf,
} from "lucide-react";
import { getDemoData } from "../../lib/api";
import { motion } from "framer-motion";
import type { Analysis, PreSeededMessage, UploadedDocument } from "../../lib/types";
import { GreenwashScoreGauge } from "../components/GreenwashScoreGauge";
import { ClaimVsRealityRow } from "../components/ClaimVsRealityRow";

// ─── Offline fallback data (mirrors backend/routers/demo.py DEMO_DATA) ─────────
const FALLBACK_DOCUMENTS: UploadedDocument[] = [
  { id: "doc-1", filename: "EcoTech_SustainabilityReport_2025.pdf", fileType: "pdf", fileSize: 3456789, processingStatus: "completed", uploadedAt: "2025-11-15T10:00:00.000Z" },
  { id: "doc-2", filename: "EcoTech_PackagingClaims_Q4Campaign.pdf", fileType: "pdf", fileSize: 1234567, processingStatus: "completed", uploadedAt: "2025-11-15T10:00:00.000Z" },
];

const FALLBACK_ANALYSIS: Analysis = {
  analyzedAt: "2025-11-15T10:30:00.000Z",
  greenwashScore: 24,
  executiveSummary:
    "GreenLens analysis of EcoTech Corporation's sustainability report and marketing materials reveals significant greenwashing across multiple claims. The company's 'carbon neutral' marketing implies zero total emissions, but their report confirms only Scope 1 emissions (3.9% of total footprint) are offset. Marketing materials claim '100% recycled packaging' while the sustainability report confirms only the outer box (45% by weight) uses recycled content — inner trays, plastic wrap, and blister packs are virgin materials. The '15% water reduction' claim omits that water-intensive processes were relocated to Mexico, increasing total usage by 8%. These discrepancies represent HIGH-severity greenwashing that would likely attract regulatory scrutiny under FTC Green Guides and the EU Green Claims Directive.",
  risks: [
    {
      id: "r1",
      level: "HIGH",
      description:
        "Marketing claims 'zero carbon footprint' and 'ZERO emissions' but only Scope 1 (17,400 tCO2e = 3.9% of total 448,400 tCO2e) is offset. Unqualified 'carbon neutral' claims covering less than 4% of actual emissions violate FTC Green Guides Section 260.5.",
      sourceDocument: "EcoTech_PackagingClaims_Q4Campaign.pdf",
      category: "Misleading Claims",
    },
    {
      id: "r2",
      level: "HIGH",
      description:
        "'100% recycled packaging' claim is deceptive — sustainability report reveals only the outer box uses recycled content (153g of 340g = 45% by weight). Inner trays are virgin polystyrene, wrap is non-recyclable LDPE, accessories use PVC blister packs.",
      sourceDocument: "EcoTech_SustainabilityReport_2025.pdf",
      category: "Packaging Deception",
    },
    {
      id: "r3",
      level: "HIGH",
      description:
        "Water reduction claim (15%) achieved by relocating processes to Mexico, not by actual conservation. Combined water usage increased 8% YoY. Marketing presents this as a genuine environmental improvement ('every drop counts').",
      sourceDocument: "EcoTech_SustainabilityReport_2025.pdf",
      category: "Hidden Trade-off",
    },
    {
      id: "r4",
      level: "MEDIUM",
      description:
        "'Clean supply chain' and 'all suppliers meet rigorous standards' claims contradicted by report data: only 30% of suppliers audited, 6 found non-compliant with wastewater standards, 3 using banned substances, and 33 suppliers never audited.",
      sourceDocument: "EcoTech_SustainabilityReport_2025.pdf",
      category: "Unverified Claims",
    },
    {
      id: "r5",
      level: "MEDIUM",
      description:
        "'Eco-friendly manufacturing' and 'sustainable manufacturing' used without definition or certification. ISO 14001 covers Austin facility only. No cradle-to-cradle, B Corp, or equivalent whole-company environmental certification exists.",
      sourceDocument: "EcoTech_PackagingClaims_Q4Campaign.pdf",
      category: "Vague Claims",
    },
    {
      id: "r6",
      level: "LOW",
      description:
        "Press release states EcoTech is 'one of the first major consumer electronics companies to reach net-zero emissions' — conflating carbon offsetting (credits) with actual emission elimination. This distinction matters for investor and consumer trust.",
      sourceDocument: "EcoTech_PackagingClaims_Q4Campaign.pdf",
      category: "Misleading Framing",
    },
  ],
  comparisonMatrix: [
    {
      field: "Carbon Neutrality Scope",
      values: { "Marketing Claim": "Full carbon neutrality, zero emissions", "Actual (Report)": "Scope 1 only — 3.9% of total footprint" },
      winner: "",
    },
    {
      field: "Recycled Packaging",
      values: { "Marketing Claim": "100% recycled packaging", "Actual (Report)": "45% by weight (outer box only)" },
      winner: "",
    },
    {
      field: "Water Reduction",
      values: { "Marketing Claim": "15% less water, 'every drop counts'", "Actual (Report)": "Relocated to Mexico; total usage up 8%" },
      winner: "",
    },
    {
      field: "Supply Chain Standards",
      values: { "Marketing Claim": "All suppliers meet rigorous standards", "Actual (Report)": "30% audited; 9 non-compliant findings" },
      winner: "",
    },
    {
      field: "Renewable Energy",
      values: { "Marketing Claim": "Implied green/sustainable operations", "Actual (Report)": "12% renewable; 88% fossil grid" },
      winner: "",
    },
  ],
  conflicts: [
    {
      id: "c1",
      type: "Carbon Claim vs. Actual Data",
      severity: "HIGH",
      documentA: {
        name: "EcoTech_PackagingClaims_Q4Campaign.pdf",
        excerpt:
          "We've eliminated our carbon footprint entirely. Every EcoTech product is made with net-zero emissions, meaning you can feel good about your purchase knowing it had zero climate impact.",
      },
      documentB: {
        name: "EcoTech_SustainabilityReport_2025.pdf",
        excerpt:
          "Scope 2 (purchased electricity) and Scope 3 (supply chain, product use, end-of-life) emissions are tracked but not included in our carbon neutrality claim. Total actual footprint: 448,400 tCO2e. Percentage offset: 3.9%.",
      },
      explanation:
        "Marketing claims 'zero climate impact' and 'eliminated carbon footprint entirely' while the sustainability report explicitly states only Scope 1 (3.9% of total emissions) is offset. The remaining 96.1% (430,600 tCO2e) is unaddressed. This is a textbook example of scope manipulation — the most common corporate greenwashing tactic identified by the EU Green Claims Directive.",
      recommendedAction:
        "Immediately qualify all carbon neutrality claims to specify 'Scope 1 only' or face potential FTC enforcement action. Remove unqualified 'zero emissions' language from all marketing channels. Consider ACCC v. Clorox precedent ($5.5M fine for misleading 'eco-friendly' claims).",
    },
    {
      id: "c2",
      type: "Packaging Claim vs. Actual Composition",
      severity: "HIGH",
      documentA: {
        name: "EcoTech_PackagingClaims_Q4Campaign.pdf",
        excerpt:
          "This box? It's made entirely from recycled materials. We've eliminated virgin materials from our packaging supply chain completely.",
      },
      documentB: {
        name: "EcoTech_SustainabilityReport_2025.pdf",
        excerpt:
          "Inner product tray: Virgin polystyrene foam. Plastic wrap: Standard LDPE film (not recyclable). Accessories packaging: PVC blister packs. Recycled content by weight: 45% (outer box only = 153g of 340g).",
      },
      explanation:
        "The '100% recycled' claim applies only to the outer shipping box but is presented as covering all packaging. The sustainability report reveals 55% of packaging weight consists of virgin polystyrene, non-recyclable LDPE, and PVC — materials with significant environmental impact that directly contradict the 'eliminated virgin materials' claim.",
      recommendedAction:
        "Revise packaging claims to specify 'outer box made from 100% recycled cardboard' and disclose that inner packaging uses virgin materials. Under FTC Green Guides Section 260.13, unqualified '100% recycled' claims must apply to the entire product or package, not just one component.",
    },
    {
      id: "c3",
      type: "Supply Chain Claim vs. Audit Reality",
      severity: "MEDIUM",
      documentA: {
        name: "EcoTech_PackagingClaims_Q4Campaign.pdf",
        excerpt:
          "We work closely with all our suppliers to reduce environmental impact. All suppliers sign our environmental code of conduct and undergo regular audits.",
      },
      documentB: {
        name: "EcoTech_SustainabilityReport_2025.pdf",
        excerpt:
          "Environmental audits conducted on suppliers representing 30% of procurement spend. 14 of 47 suppliers audited. 6 found non-compliant with wastewater standards. 3 identified as using banned substances. 33 suppliers not yet audited.",
      },
      explanation:
        "Marketing implies all 47 suppliers undergo environmental audits, but only 14 (30%) have been audited. Of those audited, 64% (9 of 14) had compliance failures. The claim of 'rigorous standards' is undermined by the fact that 70% of the supply chain has never been assessed.",
      recommendedAction:
        "Remove 'all suppliers' language and replace with factual '30% of suppliers audited to date, with a target of 100% by [year]'. Disclose non-compliance findings and remediation status per GRI Standards 308 (Supplier Environmental Assessment).",
    },
  ],
  recommendation: {
    title: "High Greenwashing Risk — Immediate Claim Revision Required",
    summary:
      "EcoTech's marketing materials contain multiple HIGH-severity greenwashing violations that directly contradict their own sustainability report data. The gap between claims and evidence is substantial and systemic, not incidental. Regulatory action is likely if these claims reach enforcement bodies.",
    nextSteps: [
      "Immediately qualify carbon neutrality claims to 'Scope 1 only (3.9% of total footprint)' across all channels",
      "Revise packaging claims to disclose actual recycled content by weight (45%) and virgin materials used",
      "Remove unqualified absolute claims ('zero emissions', 'entirely recycled', 'all suppliers') from all marketing",
      "Engage external legal review of all environmental marketing against FTC Green Guides and EU Green Claims Directive",
      "Develop a substantiation file for each environmental claim with supporting third-party evidence",
    ],
    confidence: 0.92,
  },
  suggestedQuestions: [
    "What percentage of EcoTech's total emissions are actually offset?",
    "How does the '100% recycled packaging' claim hold up against the actual packaging composition?",
    "What are the regulatory risks of EcoTech's current carbon neutrality marketing?",
    "Which specific claims would trigger FTC or EU Green Claims Directive enforcement?",
    "How does the water reduction claim mask the actual increase in total water usage?",
    "What would EcoTech need to do to make their sustainability claims substantiatable?",
  ],
};

const FALLBACK_MESSAGES: PreSeededMessage[] = [
  {
    id: "m1",
    role: "user",
    content: "Is EcoTech really carbon neutral?",
    timestamp: "2025-11-15T10:32:00.000Z",
  },
  {
    id: "m2",
    role: "assistant",
    content: "",
    timestamp: "2025-11-15T10:32:02.000Z",
    structuredResponse: {
      answer:
        "No. EcoTech's carbon neutrality claim is severely misleading. Their sustainability report explicitly states that only Scope 1 emissions are offset — that's 17,400 tCO2e out of a total footprint of 448,400 tCO2e. In other words, they've offset 3.9% of their actual carbon footprint and called it 'carbon neutral'. Their marketing says 'zero climate impact' and 'eliminated our carbon footprint entirely' — this is demonstrably false by their own data. Scope 2 (89,000 tCO2e from purchased electricity) and Scope 3 (342,000 tCO2e from supply chain, product use, and end-of-life) are completely unaddressed. Under FTC Green Guides Section 260.5, an unqualified 'carbon neutral' claim must account for all material emission sources unless clearly qualified. EcoTech's claim does neither — it implies total neutrality while covering less than 4% of actual emissions. This is the type of scope manipulation that resulted in regulatory action against Shell, TotalEnergies, and Santos in recent years.",
      evidence: [
        {
          quote: "Total actual footprint: 448,400 tCO2e. Percentage offset: 3.9% (Scope 1 only)",
          sourceDocument: "EcoTech_SustainabilityReport_2025.pdf",
          documentType: "pdf",
        },
        {
          quote: "We've eliminated our carbon footprint entirely. Every EcoTech product is made with net-zero emissions, meaning zero climate impact.",
          sourceDocument: "EcoTech_PackagingClaims_Q4Campaign.pdf",
          documentType: "pdf",
        },
        {
          quote: "Scope 2 and Scope 3 emissions are tracked but not included in our carbon neutrality claim at this time.",
          sourceDocument: "EcoTech_SustainabilityReport_2025.pdf",
          documentType: "pdf",
        },
      ],
      risks:
        "HIGH — Unqualified carbon neutrality claims covering only 3.9% of actual emissions constitute misleading environmental marketing under multiple jurisdictions. FTC Green Guides require material qualification. The EU Green Claims Directive (effective 2026) will make such unsubstantiated claims explicitly illegal. ACCC has fined companies $5.5M+ for similar overstatements.",
      recommendation:
        "Consumers should disregard EcoTech's 'carbon neutral' marketing as materially misleading. The company should immediately qualify all claims to state 'Scope 1 carbon neutral (3.9% of total footprint)' or face regulatory risk. Look for SBTi-validated targets covering all scopes as a credible alternative.",
    },
  },
  {
    id: "m3",
    role: "user",
    content: "What about their recycled packaging claim?",
    timestamp: "2025-11-15T10:34:00.000Z",
  },
  {
    id: "m4",
    role: "assistant",
    content: "",
    timestamp: "2025-11-15T10:34:02.000Z",
    structuredResponse: {
      answer:
        "The '100% recycled packaging' claim is another clear case of deceptive marketing. EcoTech's own sustainability report breaks down packaging composition: the outer shipping box (153g) uses post-consumer recycled cardboard, but the inner product tray is virgin polystyrene foam, the plastic wrap is non-recyclable LDPE film, and accessories come in PVC blister packs. By weight, recycled content accounts for only 45% of total packaging (153g out of 340g). The marketing claim that they've 'eliminated virgin materials from our packaging supply chain completely' is directly contradicted by their own data showing 55% virgin material content. Under FTC Green Guides Section 260.13, an unqualified 'recycled' claim must apply to the entire product. Claiming '100% recycled' when only the outer box qualifies is textbook deception — it's the packaging equivalent of claiming your car is 'electric' because the clock runs on a battery. PVC blister packs are particularly problematic as PVC is considered one of the most environmentally harmful plastics in terms of production and end-of-life toxicity.",
      evidence: [
        {
          quote: "Recycled content by weight: 45% (outer box only = 153g of 340g). Inner product tray: Virgin polystyrene foam. Plastic wrap: Standard LDPE film (not recyclable).",
          sourceDocument: "EcoTech_SustainabilityReport_2025.pdf",
          documentType: "pdf",
        },
        {
          quote: "This box? It's made entirely from recycled materials. We've eliminated virgin materials from our packaging supply chain completely.",
          sourceDocument: "EcoTech_PackagingClaims_Q4Campaign.pdf",
          documentType: "pdf",
        },
      ],
      risks:
        "HIGH — Unqualified '100% recycled' claims that apply only to one component violate FTC Green Guides Section 260.13. The explicit statement about eliminating virgin materials is directly contradicted by reported data (55% virgin content by weight). This creates both regulatory liability and consumer trust risk.",
      recommendation:
        "Consumers should verify what 'recycled packaging' actually means before trusting such claims. Look for specific percentages and which components are covered. EcoTech should revise claims to state 'outer box made from 100% recycled cardboard' and develop a roadmap to eliminate virgin polystyrene, LDPE, and PVC from their packaging entirely.",
    },
  },
];

// GreenLens loading screen with premium animations
function DemoLoader() {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--ink)" }}>
      <NavigationBar showDemo={false} />
      <div className="flex-1 flex items-center justify-center px-4">
        <div
          className="flex flex-col items-center gap-6 animate-fadeIn"
          style={{
            background: "var(--lead)",
            border: "1px solid var(--leaf-border)",
            borderRadius: "16px",
            padding: "clamp(24px, 6vw, 48px) clamp(24px, 8vw, 64px)",
            maxWidth: "400px",
            width: "100%",
            boxShadow: "0 0 40px rgba(61,220,132,0.08)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Scan line effect */}
          <div className="scan-line" />

          {/* GreenLens logo area with conic-gradient spinner ring */}
          <div style={{ position: "relative" }}>
            <div style={{ width: "64px", height: "64px", borderRadius: "16px", background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)", display: "flex", alignItems: "center", justifyContent: "center", position: "relative", zIndex: 1 }}>
              <Leaf size={28} style={{ color: "var(--leaf)" }} />
            </div>
            {/* Animated rotating border */}
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2.5, repeat: Infinity, ease: "linear" }}
              style={{
                position: "absolute",
                inset: "-6px",
                borderRadius: "20px",
                background: "conic-gradient(from 0deg, transparent 0%, rgba(61,220,132,0.6) 25%, transparent 50%)",
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
                backgroundImage: "conic-gradient(from 0deg, transparent 60%, rgba(61,220,132,0.7) 80%, transparent 100%)",
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
              style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)", marginBottom: "6px" }}
            >
              Loading Demo
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", color: "var(--ghost)" }}
            >
              Loading GreenLens analysis…
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
                  background: "var(--leaf)",
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
              onMouseOver={(e) => { e.currentTarget.style.background = "var(--graphite)"; e.currentTarget.style.borderLeftColor = "var(--leaf)"; }}
              onMouseOut={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderLeftColor = "transparent"; }}
            >
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center rounded-md shrink-0" style={{ width: "24px", height: "24px", background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)" }}>
                  <span style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "9px", fontWeight: 600, color: "var(--leaf)" }}>
                    {isImage ? "IMG" : "PDF"}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="truncate" style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", fontWeight: 500, color: "var(--paper)" }}>{doc.filename}</div>
                  <div style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "11px", color: "var(--leaf)" }}>
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
        </div>
      </div>
    </>
  );

  return (
    <div className="min-h-screen page-enter" style={{ background: "var(--ink)" }}>
      <NavigationBar showDemo={false} />

      {/* Demo Banner */}
      <div
        className="flex flex-wrap items-center justify-between px-4 sm:px-8 py-3 gap-3"
        style={{ background: "var(--flag-amber-dim)", borderBottom: "1px solid rgba(240,169,55,0.25)" }}
      >
        <div className="flex items-center gap-2">
          <Target size={15} style={{ color: "var(--flag-amber)", flexShrink: 0 }} />
          <span style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace", fontSize: "13px", fontWeight: 600, color: "var(--flag-amber)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Demo Mode
          </span>
          <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", fontWeight: 500, color: "var(--flag-amber)" }}>
            — Pre-loaded sample sustainability claims
          </span>
        </div>
        <Link to="/" style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "13px", fontWeight: 500, color: "var(--leaf)", textDecoration: "none", whiteSpace: "nowrap" }}>
          Try with your own →
        </Link>
      </div>

      <div className="flex relative">
        {/* Desktop sidebar */}
        <div
          className="hidden md:block shrink-0"
          style={{ width: "300px", minHeight: "calc(100vh - 112px)", background: "var(--lead)", borderRight: "1px solid var(--rule)" }}
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
                <h2 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "clamp(16px, 3vw, 20px)", fontWeight: 700, color: "var(--paper)" }}>
                  Sample Greenwashing Analysis
                </h2>
                <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)" }}>
                  {documents.length} documents · Demo data
                </span>
              </div>
            </div>
          </div>

          <div className="p-4 sm:p-6 md:p-8 space-y-5">
            {/* Guided Tour Intro */}
            <div className="rounded-xl p-5" style={{ background: "linear-gradient(135deg, rgba(61,220,132,0.06) 0%, rgba(61,220,132,0.03) 100%)", border: "1px solid var(--leaf-border)" }}>
              <div className="flex items-start gap-3">
                <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Lightbulb size={18} style={{ color: "var(--leaf)" }} />
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "16px", fontWeight: 700, color: "var(--paper)", marginBottom: "6px" }}>
                    What you're seeing
                  </h3>
                  <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--ash)", margin: 0 }}>
                    This demo shows a complete greenwashing analysis of {documents.length} sample sustainability documents — cross-referencing marketing claims against reported data. 
                    Below you'll see: <strong style={{ color: "var(--paper)" }}>cross-document contradiction detection</strong>, an <strong style={{ color: "var(--paper)" }}>executive summary</strong>, <strong style={{ color: "var(--paper)" }}>greenwash flag assessment</strong> with severity ratings, 
                    a <strong style={{ color: "var(--paper)" }}>claim vs. reality comparison</strong>, and an <strong style={{ color: "var(--paper)" }}>AI recommendation</strong> with actionable next steps. 
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
                  <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", color: "var(--ash)" }}>
                    Cross-Document Contradiction Detection — automatically finds claims that contradict the reported data
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

                <div style={{ paddingTop: "16px", borderTop: "1px solid rgba(240,68,82,0.15)" }}>
                  <div className="rounded-lg p-4" style={{ background: "rgba(240,68,82,0.04)" }}>
                    <div className="flex items-center gap-2 mb-3 flex-wrap">
                      <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--flag-red)", textTransform: "uppercase" }}>
                        {primaryConflict.type}
                      </span>
                      <RiskBadge variant={primaryConflict.severity} />
                    </div>
                    <div className="grid gap-3 mb-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(200px, 100%), 1fr))" }}>
                      {[primaryConflict.documentA, primaryConflict.documentB].map((doc, i) => (
                        <div key={i} className="rounded-lg p-3" style={{ background: "rgba(240,68,82,0.06)", border: "1px solid rgba(240,68,82,0.15)" }}>
                          <div className="mb-2"><EvidenceTag filename={doc.name} /></div>
                          <EvidenceBox quote={doc.excerpt} style={{ background: "var(--paper)" }} />
                        </div>
                      ))}
                    </div>
                    <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--ash)" }}>{primaryConflict.recommendedAction}</p>
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
                <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", color: "var(--ash)" }}>
                  AI-Generated Analysis — executive summary, greenwash scoring, claim vs. reality comparison, and recommendation
                </span>
              </div>
            {/* Greenwash Score Gauge */}
            <GreenwashScoreGauge score={analysis.greenwashScore} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
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
                <div style={{ borderTop: "1px solid var(--rule)", paddingTop: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                  <Leaf size={12} style={{ color: "var(--ghost)" }} />
                  <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", fontWeight: 500, color: "var(--ghost)" }}>Generated by GreenLens AI</span>
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
                <span style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "12px", color: "var(--ash)" }}>
                  AI Chat Copilot — ask follow-up questions in plain language, get answers grounded in the documents
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
                                  borderLeft: "3px solid var(--leaf)",
                                  maxWidth: "min(500px, 100%)",
                                  padding: "12px",
                                }
                          }
                        >
                          <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--paper)" }}>
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
                        <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", color: "var(--paper)" }}>Is EcoTech really carbon neutral?</p>
                      </div>
                    </div>
                    <div className="flex justify-start">
                      <div className="rounded-xl p-3" style={{ background: "var(--lead)", border: "1px solid var(--rule)", borderLeft: "3px solid var(--leaf)", maxWidth: "min(500px, 100%)" }}>
                        <p style={{ fontFamily: "'IBM Plex Sans', 'Inter', sans-serif", fontSize: "14px", lineHeight: 1.6, color: "var(--paper)" }}>
                          {analysis.recommendation.summary}
                        </p>
                      </div>
                    </div>
                  </>
                )}
              </div>

              <div className="rounded-lg p-4 sm:p-5" style={{ background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)" }}>
                <h4 style={{ fontFamily: "'Syne', 'DM Sans', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--paper)", marginBottom: "14px" }}>
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
