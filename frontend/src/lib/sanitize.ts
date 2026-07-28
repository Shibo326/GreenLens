/**
 * Sanitize text from LLM responses that may contain Unicode characters
 * which render as black boxes/squares in web fonts.
 */
export function sanitizeText(text: string | undefined | null): string {
  if (!text) return '';
  return text
    // Fix corrupted CO₂ characters (LLM subscript-2 sometimes corrupts to U+FFFD)
    .replace(/CO\uFFFDe/g, 'CO₂e')
    .replace(/tCO\uFFFDe/g, 'tCO₂e')
    // Remove remaining U+FFFD replacement characters
    .replace(/\uFFFD/g, '')
    // Uncommon hyphens → regular hyphen
    .replace(/\u2010/g, '-')
    .replace(/\u2011/g, '-')
    .replace(/\u2012/g, '-')
    .replace(/\u2212/g, '-')
    // Remove invisible/zero-width characters
    .replace(/\u00AD/g, '')
    .replace(/\u200B/g, '')
    .replace(/\u200C/g, '')
    .replace(/\u200D/g, '')
    .replace(/\uFEFF/g, '')
    // Smart quotes → regular quotes
    .replace(/\u2018/g, "'")
    .replace(/\u2019/g, "'")
    .replace(/\u201C/g, '"')
    .replace(/\u201D/g, '"')
    // Horizontal bar → em-dash
    .replace(/\u2015/g, '—');
}

/**
 * Strip markdown syntax from text for plain-text contexts (copy, export).
 */
export function stripMarkdown(text: string | undefined | null): string {
  if (!text) return '';
  return sanitizeText(text)
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^[-*]\s+/gm, '• ');
}
