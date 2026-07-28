import { sanitizeText } from "../../lib/sanitize";

interface MarkdownTextProps {
  text: string | undefined | null;
  style?: React.CSSProperties;
  className?: string;
}

/**
 * Try to extract the "answer" field if text appears to be raw JSON.
 * This is a frontend safety net for when the backend fails to parse LLM output properly.
 */
function extractAnswerFromJSON(text: string): string {
  const trimmed = text.trim();
  // Quick check: does it look like raw JSON with an "answer" key?
  if (!trimmed.startsWith("{") || !trimmed.includes('"answer"')) return text;

  // Try regex extraction of the answer field value
  const match = trimmed.match(/"answer"\s*:\s*"((?:[^"\\]|\\.)*)"/);
  if (match && match[1] && match[1].length > 20) {
    // Unescape JSON string escapes
    return match[1]
      .replace(/\\"/g, '"')
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\\\\/g, '\\');
  }

  // If the whole text is raw JSON-like, try JSON.parse as a last resort
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed && typeof parsed === 'object' && typeof parsed.answer === 'string') {
      return parsed.answer;
    }
  } catch {
    // Not valid JSON — fall through
  }

  return text;
}

/**
 * Renders LLM markdown text with bold, italic, bullet points, and line breaks.
 * No external dependencies — handles the subset that Kimi K2.6 / DeepSeek produce.
 */
export function MarkdownText({ text, style, className }: MarkdownTextProps) {
  if (!text) return null;

  // Safety net: if text looks like raw JSON, extract just the answer
  const cleaned = extractAnswerFromJSON(text);
  const clean = sanitizeText(cleaned);

  // Split into paragraphs/lines
  const lines = clean.split('\n');

  const renderInline = (line: string, _key: number) => {
    // Parse **bold** and *italic* inline
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*(.+?)\*\*|\*(.+?)\*)/g;
    let last = 0;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(line)) !== null) {
      if (match.index > last) {
        parts.push(line.slice(last, match.index));
      }
      if (match[0].startsWith('**')) {
        parts.push(<strong key={match.index} style={{ fontWeight: 700, color: "inherit" }}>{match[2]}</strong>);
      } else {
        parts.push(<em key={match.index} style={{ fontStyle: "italic" }}>{match[3]}</em>);
      }
      last = match.index + match[0].length;
    }
    if (last < line.length) {
      parts.push(line.slice(last));
    }

    return parts.length > 0 ? parts : [line];
  };

  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Skip empty lines (add spacing via margin on previous element)
    if (!trimmed) {
      i++;
      continue;
    }

    // Bullet point: - item or * item or • item
    if (/^[-*•]\s+/.test(trimmed)) {
      // Collect consecutive bullet lines into a list
      const bullets: string[] = [];
      while (i < lines.length && /^[-*•]\s+/.test(lines[i].trim())) {
        bullets.push(lines[i].trim().replace(/^[-*•]\s+/, ''));
        i++;
      }
      elements.push(
        <ul key={`ul-${i}`} style={{ paddingLeft: "20px", margin: "6px 0", listStyleType: "disc" }}>
          {bullets.map((b, bi) => (
            <li key={bi} style={{ marginBottom: "4px" }}>
              {renderInline(b, bi)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Numbered list: 1. item
    if (/^\d+\.\s+/.test(trimmed)) {
      const bullets: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        bullets.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
        i++;
      }
      elements.push(
        <ol key={`ol-${i}`} style={{ paddingLeft: "20px", margin: "6px 0" }}>
          {bullets.map((b, bi) => (
            <li key={bi} style={{ marginBottom: "4px" }}>
              {renderInline(b, bi)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // Heading: ### text
    if (/^#{1,3}\s+/.test(trimmed)) {
      const headingText = trimmed.replace(/^#{1,3}\s+/, '');
      elements.push(
        <p key={`h-${i}`} style={{ fontWeight: 700, marginBottom: "4px", marginTop: elements.length > 0 ? "12px" : "0" }}>
          {renderInline(headingText, i)}
        </p>
      );
      i++;
      continue;
    }

    // Regular paragraph line
    elements.push(
      <p key={`p-${i}`} style={{ marginBottom: "6px", lineHeight: 1.7 }}>
        {renderInline(trimmed, i)}
      </p>
    );
    i++;
  }

  return (
    <div
      className={className}
      style={{
        fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
        fontSize: "15px",
        color: "var(--paper)",
        letterSpacing: "-0.01em",
        ...style,
      }}
    >
      {elements}
    </div>
  );
}
