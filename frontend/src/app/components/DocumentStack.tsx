import { AnimatePresence, motion } from "framer-motion";
import { X, FileText, Image } from "lucide-react";

interface DocumentStackProps {
  files: File[];
  onRemove: (index: number) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileType(type: string): "PDF" | "IMG" {
  return type.toLowerCase() === "application/pdf" ? "PDF" : "IMG";
}

interface PaperCardProps {
  file: File;
  index: number;
  onRemove: (index: number) => void;
}

function PaperCard({ file, index, onRemove }: PaperCardProps) {
  const fileType = getFileType(file.type);

  return (
    <motion.div
      key={`${file.name}-${file.size}-${file.lastModified}`}
      initial={{ opacity: 0, scale: 0.9, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9, y: -10 }}
      transition={{ type: "spring", stiffness: 400, damping: 25, delay: index * 0.05 }}
      style={{ width: "min(200px, calc(50% - 8px))", minWidth: "140px" }}
    >
      <div
        data-testid="paper-card"
        style={{
          background: "rgba(61, 220, 132, 0.04)",
          border: "1px solid rgba(61, 220, 132, 0.15)",
          borderRadius: "12px",
          padding: "14px 16px",
          position: "relative",
          backdropFilter: "blur(4px)",
          transition: "all 0.2s ease",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = "rgba(61, 220, 132, 0.4)";
          e.currentTarget.style.background = "rgba(61, 220, 132, 0.08)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = "rgba(61, 220, 132, 0.15)";
          e.currentTarget.style.background = "rgba(61, 220, 132, 0.04)";
        }}
      >
        {/* Remove button */}
        <button
          type="button"
          aria-label={`Remove ${file.name}`}
          onClick={(e) => {
            e.stopPropagation();
            onRemove(index);
          }}
          style={{
            position: "absolute",
            top: "8px",
            right: "8px",
            width: "22px",
            height: "22px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "6px",
            cursor: "pointer",
            color: "var(--ghost)",
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(240, 68, 82, 0.15)";
            e.currentTarget.style.borderColor = "rgba(240, 68, 82, 0.3)";
            e.currentTarget.style.color = "var(--flag-red)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.05)";
            e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
            e.currentTarget.style.color = "var(--ghost)";
          }}
        >
          <X size={12} />
        </button>

        {/* Icon + file type row */}
        <div className="flex items-center gap-2 mb-2">
          <div style={{
            width: "28px",
            height: "28px",
            borderRadius: "8px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: fileType === "PDF" ? "rgba(240, 68, 82, 0.1)" : "rgba(61, 220, 132, 0.1)",
            border: `1px solid ${fileType === "PDF" ? "rgba(240, 68, 82, 0.2)" : "rgba(61, 220, 132, 0.2)"}`,
          }}>
            {fileType === "PDF" ? (
              <FileText size={14} style={{ color: "var(--flag-red)" }} />
            ) : (
              <Image size={14} style={{ color: "var(--leaf)" }} />
            )}
          </div>
          <span style={{
            fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
            fontSize: "10px",
            fontWeight: 600,
            letterSpacing: "0.05em",
            color: fileType === "PDF" ? "var(--flag-red)" : "var(--leaf)",
            opacity: 0.8,
          }}>
            {fileType}
          </span>
        </div>

        {/* Filename */}
        <div
          style={{
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontSize: "13px",
            fontWeight: 500,
            color: "var(--paper)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            marginBottom: "4px",
            paddingRight: "20px",
          }}
          title={file.name}
        >
          {file.name}
        </div>

        {/* File size */}
        <div
          style={{
            fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
            fontSize: "11px",
            color: "var(--ghost)",
          }}
        >
          {formatBytes(file.size)}
        </div>
      </div>
    </motion.div>
  );
}

export function DocumentStack({ files, onRemove }: DocumentStackProps) {
  return (
    <div className="flex flex-wrap gap-3">
      <AnimatePresence>
        {files.map((file, index) => (
          <PaperCard
            key={`${file.name}-${file.size}-${file.lastModified}`}
            file={file}
            index={index}
            onRemove={onRemove}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}
