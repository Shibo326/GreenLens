import { motion } from "framer-motion";
import { FileText, AlertTriangle, Search, Shield, Sparkles } from "lucide-react";

interface AchievementBadgesProps {
  documentsAnalyzed: number;
  contradictionsFound: number;
  flagsFound: number;
}

interface Badge {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  earned: boolean;
}

export function AchievementBadges({ documentsAnalyzed, contradictionsFound, flagsFound }: AchievementBadgesProps) {
  const badges: Badge[] = [
    {
      id: "first-scan",
      label: "First Scan",
      description: "Analyzed your first document",
      icon: <FileText size={14} />,
      color: "var(--leaf)",
      earned: documentsAnalyzed >= 1,
    },
    {
      id: "contradiction-hunter",
      label: "Contradiction Hunter",
      description: "Found a greenwashing contradiction",
      icon: <AlertTriangle size={14} />,
      color: "var(--flag-red)",
      earned: contradictionsFound >= 1,
    },
    {
      id: "detective-mode",
      label: "Detective Mode",
      description: "5+ greenwash flags detected",
      icon: <Search size={14} />,
      color: "var(--flag-amber)",
      earned: flagsFound >= 5,
    },
    {
      id: "watchdog",
      label: "Watchdog",
      description: "3+ contradictions exposed",
      icon: <Shield size={14} />,
      color: "var(--flag-blue)",
      earned: contradictionsFound >= 3,
    },
    {
      id: "deep-dive",
      label: "Deep Dive",
      description: "Analyzed 3+ documents in one session",
      icon: <Sparkles size={14} />,
      color: "var(--leaf)",
      earned: documentsAnalyzed >= 3,
    },
  ];

  const earnedBadges = badges.filter((b) => b.earned);
  if (earnedBadges.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {earnedBadges.map((badge, i) => (
        <motion.div
          key={badge.id}
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 20, delay: i * 0.1 }}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full"
          style={{
            background: `${badge.color}12`,
            border: `1px solid ${badge.color}33`,
            cursor: "default",
          }}
          title={badge.description}
        >
          <span style={{ color: badge.color, display: "flex" }}>{badge.icon}</span>
          <span
            style={{
              fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
              fontSize: "11px",
              fontWeight: 600,
              color: badge.color,
              whiteSpace: "nowrap",
            }}
          >
            {badge.label}
          </span>
        </motion.div>
      ))}
    </div>
  );
}
