import { useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";

interface DocumentStackProps {
  files: File[];
  onRemove: (index: number) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileStamp(type: string): "PDF" | "IMG" {
  return type.toLowerCase() === "application/pdf" ? "PDF" : "IMG";
}

interface PaperCardProps {
  file: File;
  index: number;
  onRemove: (index: number) => void;
}

function PaperCard({ file, index, onRemove }: PaperCardProps) {
  // Deterministic "random" rotation per card based on index, in range [-4, +4] degrees.
  const rotation = useMemo(() => ((index * 137) % 9) - 4, [index]);

  const stamp = getFileStamp(file.type);
  const stampStyle =
    stamp === "PDF"
      ? { background: "var(--flag-red-dim)", border: "1px solid rgba(240, 68, 82, 0.25)", color: "var(--flag-red)" }
      : { background: "var(--leaf-dim)", border: "1px solid var(--leaf-border)", color: "var(--leaf)" };

  return (
    <motion.div
      key={`${file.name}-${file.size}-${file.lastModified}`}
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      style={{ width: "min(220px, calc(50% - 8px))", minWidth: "140px" }}
    >
      {/* Static rotation lives on this inner wrapper so it can coexist with
          framer-motion's own transform (opacity/y) on the outer motion.div. */}
      <div
        data-testid="paper-card"
        style={{
          transform: `rotate(${rotation}deg)`,
          background: "#F2EFE8",
          borderRadius: "4px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.18)",
          padding: "14px",
          position: "relative",
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
            width: "20px",
            height: "20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "none",
            border: "none",
            borderRadius: "50%",
            cursor: "pointer",
            color: "#6B6F5E",
          }}
        >
          <X size={13} />
        </button>

        {/* File-type stamp badge */}
        <span
          className="inline-flex items-center"
          style={{
            ...stampStyle,
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "10px",
            fontWeight: 600,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            padding: "2px 6px",
            borderRadius: "100px",
            marginBottom: "10px",
          }}
        >
          {stamp}
        </span>

        {/* Filename */}
        <div
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "13px",
            fontWeight: 500,
            color: "#0C0E14",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            marginBottom: "4px",
            paddingRight: "16px",
          }}
          title={file.name}
        >
          {file.name}
        </div>

        {/* File size */}
        <div
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "11px",
            color: "#6B6F5E",
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
