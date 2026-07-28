import { useState, useRef } from "react";
import { useNavigate } from "react-router";
import {
  Pencil,
  Camera,
  Link as LinkIcon,
  Sparkles,
  Loader,
  AlertTriangle,
  CheckCircle,
  Info,
  Image as ImageIcon,
} from "lucide-react";
import { quickScan, scanUrl, uploadDocuments, analyzeDocuments } from "../../lib/api";
import { useAppDispatch } from "../../lib/store";
import type { QuickScanResponse } from "../../lib/types";

type TabId = "type" | "photo" | "url";

interface TabDef {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const TABS: TabDef[] = [
  { id: "type", label: "Type", icon: <Pencil size={14} /> },
  { id: "photo", label: "Photo", icon: <Camera size={14} /> },
  { id: "url", label: "URL", icon: <LinkIcon size={14} /> },
];

function getConfidenceStyle(confidence: string) {
  switch (confidence) {
    case "HIGH":
      return { color: "var(--leaf)", bg: "var(--leaf-dim)", border: "var(--leaf-border)", icon: <CheckCircle size={14} /> };
    case "MEDIUM":
      return { color: "var(--flag-amber)", bg: "var(--flag-amber-dim)", border: "rgba(240,169,55,0.25)", icon: <AlertTriangle size={14} /> };
    case "LOW":
      return { color: "var(--flag-red)", bg: "var(--flag-red-dim)", border: "rgba(240,68,82,0.25)", icon: <Info size={14} /> };
    default:
      return { color: "var(--ash)", bg: "var(--graphite)", border: "var(--rule)", icon: <Info size={14} /> };
  }
}

function ResultDisplay({ result }: { result: QuickScanResponse }) {
  const conf = getConfidenceStyle(result.confidence);
  return (
    <div className="mt-4 space-y-3 animate-slideUp">
      {/* Verdict */}
      <div
        className="rounded-lg p-4"
        style={{ background: "var(--graphite)", border: "1px solid var(--rule)" }}
      >
        <div
          style={{
            fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
            fontSize: "10px",
            fontWeight: 600,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--ghost)",
            marginBottom: "8px",
          }}
        >
          VERDICT
        </div>
        <p
          style={{
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontSize: "14px",
            lineHeight: 1.6,
            color: "var(--paper)",
            margin: 0,
          }}
        >
          {result.verdict}
        </p>
      </div>

      {/* What to look for */}
      {result.whatToLookFor && result.whatToLookFor.length > 0 && (
        <div
          className="rounded-lg p-4"
          style={{ background: "var(--graphite)", border: "1px solid var(--rule)" }}
        >
          <div
            style={{
              fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
              fontSize: "10px",
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--ghost)",
              marginBottom: "8px",
            }}
          >
            WHAT TO LOOK FOR
          </div>
          <ul className="space-y-1.5" style={{ margin: 0, paddingLeft: "16px" }}>
            {result.whatToLookFor.map((item, i) => (
              <li
                key={i}
                style={{
                  fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                  fontSize: "13px",
                  lineHeight: 1.5,
                  color: "var(--ash)",
                }}
              >
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Confidence badge */}
      {result.confidence && (
        <div
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg"
          style={{
            background: conf.bg,
            border: `1px solid ${conf.border}`,
            color: conf.color,
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontSize: "12px",
            fontWeight: 600,
          }}
        >
          {conf.icon}
          Confidence: {result.confidence}
        </div>
      )}
    </div>
  );
}

export function ClaimChecker() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [activeTab, setActiveTab] = useState<TabId>("type");

  // Type tab state
  const [claim, setClaim] = useState("");
  const [typeLoading, setTypeLoading] = useState(false);
  const [typeResult, setTypeResult] = useState<QuickScanResponse | null>(null);
  const [typeError, setTypeError] = useState<string | null>(null);

  // Photo tab state
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [photoLoading, setPhotoLoading] = useState(false);
  const [photoError, setPhotoError] = useState<string | null>(null);

  // URL tab state
  const [urlInput, setUrlInput] = useState("");
  const [urlLoading, setUrlLoading] = useState(false);
  const [urlResult, setUrlResult] = useState<QuickScanResponse | null>(null);
  const [urlError, setUrlError] = useState<string | null>(null);

  // --- Type tab handlers ---
  const handleTypeScan = async () => {
    const trimmed = claim.trim();
    if (!trimmed || typeLoading) return;
    setTypeLoading(true);
    setTypeError(null);
    setTypeResult(null);
    try {
      const response = await quickScan(trimmed);
      setTypeResult(response);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Quick scan failed.";
      if (msg.toLowerCase().includes("fetch") || msg.toLowerCase().includes("network")) {
        setTypeError("Backend not reachable. Start the backend server or check your connection.");
      } else {
        setTypeError(msg);
      }
    } finally {
      setTypeLoading(false);
    }
  };

  // --- Photo tab handlers ---
  const handleImageSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedImage(file);
    setPhotoError(null);
    const reader = new FileReader();
    reader.onload = (ev) => setImagePreview(ev.target?.result as string);
    reader.readAsDataURL(file);
    e.target.value = "";
  };

  const handlePhotoAnalyze = async () => {
    if (!selectedImage || photoLoading) return;
    setPhotoLoading(true);
    setPhotoError(null);
    try {
      const uploadResult = await uploadDocuments([selectedImage]);
      dispatch({ type: "RESET" });
      dispatch({ type: "SET_SESSION", payload: uploadResult.sessionId });
      dispatch({ type: "SET_DOCUMENTS", payload: uploadResult.documents });
      const analyzeResult = await analyzeDocuments(uploadResult.sessionId);
      if (analyzeResult.analysis) {
        dispatch({ type: "SET_ANALYSIS", payload: analyzeResult.analysis });
      }
      navigate("/dashboard");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Photo analysis failed.";
      if (msg.toLowerCase().includes("fetch") || msg.toLowerCase().includes("network")) {
        setPhotoError("Backend not reachable. Start the backend server or check your connection.");
      } else {
        setPhotoError(msg);
      }
    } finally {
      setPhotoLoading(false);
    }
  };

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    setPhotoError(null);
  };

  // --- URL tab handlers ---
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

  return (
    <div
      className="rounded-xl"
      style={{
        background: "var(--lead)",
        border: "1px solid var(--rule)",
        maxWidth: "640px",
        width: "100%",
        padding: "24px",
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "10px",
            background: "var(--leaf-dim)",
            border: "1px solid var(--leaf-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <Sparkles size={16} style={{ color: "var(--leaf)" }} />
        </div>
        <div>
          <h3
            style={{
              fontFamily: "'Syne', 'DM Sans', sans-serif",
              fontSize: "18px",
              fontWeight: 700,
              color: "var(--paper)",
              margin: 0,
            }}
          >
            Check a Claim
          </h3>
          <p
            style={{
              fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
              fontSize: "13px",
              color: "var(--ghost)",
              margin: 0,
            }}
          >
            No upload needed — instant verdict
          </p>
        </div>
      </div>

      {/* Tab bar */}
      <div
        className="flex gap-2 mb-5"
        style={{ overflowX: "auto", WebkitOverflowScrolling: "touch", scrollbarWidth: "none" }}
        role="tablist"
        aria-label="Claim check method"
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              aria-controls={`panel-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-2 rounded-full px-4 py-2 transition-all"
              style={{
                background: isActive ? "var(--leaf-dim)" : "var(--graphite)",
                border: `1px solid ${isActive ? "var(--leaf-border)" : "var(--rule)"}`,
                color: isActive ? "var(--leaf)" : "var(--ash)",
                fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.borderColor = "var(--leaf-border)";
                  e.currentTarget.style.color = "var(--paper)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.borderColor = "var(--rule)";
                  e.currentTarget.style.color = "var(--ash)";
                }
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab panels */}
      {/* Type tab */}
      {activeTab === "type" && (
        <div id="panel-type" role="tabpanel" aria-labelledby="tab-type">
          <textarea
            value={claim}
            onChange={(e) => setClaim(e.target.value)}
            placeholder={`e.g. "Our packaging is 100% carbon neutral by 2025"`}
            rows={3}
            className="w-full rounded-lg px-4 py-3 mb-3"
            style={{
              background: "var(--graphite)",
              border: "1px solid var(--rule)",
              color: "var(--paper)",
              fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
              fontSize: "14px",
              lineHeight: 1.5,
              resize: "none",
              outline: "none",
              transition: "border-color 0.2s",
            }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "var(--leaf-border)"; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = "var(--rule)"; }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleTypeScan();
              }
            }}
            disabled={typeLoading}
          />
          <button
            onClick={() => void handleTypeScan()}
            disabled={!claim.trim() || typeLoading}
            className="w-full flex items-center justify-center gap-2 rounded-lg"
            style={{
              height: "40px",
              background: !claim.trim() || typeLoading ? "var(--graphite)" : "var(--leaf)",
              border: "none",
              color: !claim.trim() || typeLoading ? "var(--ghost)" : "var(--ink)",
              fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
              fontSize: "14px",
              fontWeight: 600,
              cursor: !claim.trim() || typeLoading ? "not-allowed" : "pointer",
              transition: "background 0.2s, opacity 0.2s",
              opacity: !claim.trim() || typeLoading ? 0.6 : 1,
              borderRadius: "var(--radius-btn, 8px)",
            }}
          >
            {typeLoading ? (
              <>
                <Loader size={14} className="animate-spin-slow" />
                Scanning...
              </>
            ) : (
              <>
                <Sparkles size={14} />
                Scan Claim
              </>
            )}
          </button>

          {typeError && (
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
              {typeError}
            </div>
          )}

          {typeResult && <ResultDisplay result={typeResult} />}
        </div>
      )}

      {/* Photo tab */}
      {activeTab === "photo" && (
        <div id="panel-photo" role="tabpanel" aria-labelledby="tab-photo">
          <input
            ref={cameraRef}
            type="file"
            accept="image/*"
            capture="environment"
            style={{ display: "none" }}
            onChange={handleImageSelected}
            aria-label="Take a photo or select an image"
          />
          <input
            ref={galleryRef}
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={handleImageSelected}
            aria-label="Choose image from gallery"
          />

          {!selectedImage ? (
            <div className="flex flex-col gap-3">
              <button
                onClick={() => cameraRef.current?.click()}
                className="w-full flex flex-col items-center justify-center gap-3 rounded-lg"
                style={{
                  minHeight: "120px",
                  background: "var(--graphite)",
                  border: "2px dashed var(--rule)",
                  cursor: "pointer",
                  transition: "all 0.2s",
                  padding: "20px",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--leaf-border)";
                  e.currentTarget.style.background = "rgba(61,220,132,0.04)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--rule)";
                  e.currentTarget.style.background = "var(--graphite)";
                }}
              >
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    borderRadius: "12px",
                    background: "var(--leaf-dim)",
                    border: "1px solid var(--leaf-border)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Camera size={22} style={{ color: "var(--leaf)" }} />
                </div>
                <span
                  style={{
                    fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                    fontSize: "14px",
                    fontWeight: 600,
                    color: "var(--paper)",
                  }}
                >
                  📸 Take a Photo
                </span>
                <span
                  style={{
                    fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                    fontSize: "12px",
                    color: "var(--ghost)",
                    textAlign: "center",
                  }}
                >
                  Point your camera at any product label or packaging claim
                </span>
              </button>

              <button
                onClick={() => galleryRef.current?.click()}
                className="w-full flex items-center justify-center gap-2 rounded-lg"
                style={{
                  height: "48px",
                  background: "var(--graphite)",
                  border: "1px solid var(--rule)",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--leaf-border)";
                  e.currentTarget.style.background = "rgba(61,220,132,0.04)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--rule)";
                  e.currentTarget.style.background = "var(--graphite)";
                }}
              >
                <ImageIcon size={16} style={{ color: "var(--leaf)" }} />
                <span
                  style={{
                    fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                    fontSize: "13px",
                    fontWeight: 500,
                    color: "var(--paper)",
                  }}
                >
                  Open Gallery
                </span>
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Image preview */}
              <div className="relative rounded-lg overflow-hidden" style={{ border: "1px solid var(--rule)" }}>
                <img
                  src={imagePreview ?? ""}
                  alt="Selected product label"
                  style={{
                    width: "100%",
                    maxHeight: "200px",
                    objectFit: "cover",
                    display: "block",
                  }}
                />
                <button
                  onClick={clearImage}
                  style={{
                    position: "absolute",
                    top: "8px",
                    right: "8px",
                    width: "28px",
                    height: "28px",
                    borderRadius: "50%",
                    background: "rgba(10,18,14,0.8)",
                    border: "1px solid var(--rule)",
                    color: "var(--ash)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "14px",
                  }}
                  aria-label="Remove selected image"
                >
                  ✕
                </button>
              </div>
              <p
                style={{
                  fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                  fontSize: "12px",
                  color: "var(--ash)",
                  margin: 0,
                }}
              >
                {selectedImage.name}
              </p>

              {/* Analyze button */}
              <button
                onClick={() => void handlePhotoAnalyze()}
                disabled={photoLoading}
                className="w-full flex items-center justify-center gap-2 rounded-lg"
                style={{
                  height: "40px",
                  background: photoLoading ? "var(--graphite)" : "var(--leaf)",
                  border: "none",
                  color: photoLoading ? "var(--ghost)" : "var(--ink)",
                  fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                  fontSize: "14px",
                  fontWeight: 600,
                  cursor: photoLoading ? "not-allowed" : "pointer",
                  transition: "background 0.2s, opacity 0.2s",
                  opacity: photoLoading ? 0.6 : 1,
                  borderRadius: "var(--radius-btn, 8px)",
                }}
              >
                {photoLoading ? (
                  <>
                    <Loader size={14} className="animate-spin-slow" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Camera size={14} />
                    Analyze Label
                  </>
                )}
              </button>

              {photoError && (
                <div
                  className="px-4 py-3 rounded-lg"
                  style={{
                    background: "var(--flag-red-dim)",
                    border: "1px solid rgba(240,68,82,0.25)",
                    fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                    fontSize: "13px",
                    color: "var(--flag-red)",
                  }}
                >
                  {photoError}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* URL tab */}
      {activeTab === "url" && (
        <div id="panel-url" role="tabpanel" aria-labelledby="tab-url">
          <input
            type="url"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://company.com/sustainability"
            className="w-full rounded-lg px-4 py-3 mb-3"
            style={{
              background: "var(--graphite)",
              border: "1px solid var(--rule)",
              color: "var(--paper)",
              fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
              fontSize: "14px",
              outline: "none",
              transition: "border-color 0.2s",
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
            className="w-full flex items-center justify-center gap-2 rounded-lg"
            style={{
              height: "40px",
              background: !urlInput.trim() || urlLoading ? "var(--graphite)" : "var(--leaf)",
              border: "none",
              color: !urlInput.trim() || urlLoading ? "var(--ghost)" : "var(--ink)",
              fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
              fontSize: "14px",
              fontWeight: 600,
              cursor: !urlInput.trim() || urlLoading ? "not-allowed" : "pointer",
              transition: "background 0.2s, opacity 0.2s",
              opacity: !urlInput.trim() || urlLoading ? 0.6 : 1,
              borderRadius: "var(--radius-btn, 8px)",
            }}
          >
            {urlLoading ? (
              <>
                <Loader size={14} className="animate-spin-slow" />
                Scanning...
              </>
            ) : (
              <>
                <LinkIcon size={14} />
                Scan URL
              </>
            )}
          </button>

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

          {urlResult && <ResultDisplay result={urlResult} />}
        </div>
      )}
    </div>
  );
}
