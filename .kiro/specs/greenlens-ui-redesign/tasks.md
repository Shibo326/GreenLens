# Implementation Plan: Base UI Redesign (Pre-GreenLens, already implemented)

> **NOTE:** All tasks below are marked complete (`[x]`) and describe work already implemented under the "Clausify" name before the GreenLens rebrand. Kept for historical/implementation reference. New GreenLens-specific work is tracked in `.kiro/specs/greenlens-pivot/tasks.md`.

## Overview

This plan implements the full UI redesign of the Clausify AI frontend, replacing the existing electric-blue-on-navy aesthetic with a high-contrast, document-centric design system built around a cyan accent (`#00D4FF`), warm paper textures, and editorial typography (Syne + IBM Plex Sans/Mono). Implementation proceeds in dependency order: foundation (fonts, tokens, keyframes) → shared components → pages → verification.

**DO NOT MODIFY:** `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`, `frontend/src/lib/store.tsx`

## Tasks

- [x] 1. Foundation: Install dependency, load fonts, replace tokens, update keyframes
  - [x] 1.1 Install framer-motion and add Google Fonts to index.html
    - Run `npm install framer-motion` in `frontend/` (note: `motion` package already exists but framer-motion is needed for `AnimatePresence` and spring physics)
    - Add Google Fonts `<link>` tags to `frontend/index.html` `<head>` for Syne (700, 800), IBM Plex Sans (400, 500, 600), and IBM Plex Mono (400, 500, 600) with preconnect hints
    - _Requirements: 1.6, 17.1, 17.2_

  - [x] 1.2 Replace all design tokens in theme.css
    - Replace the full `:root` block in `frontend/src/styles/theme.css` with the new Design_System tokens: `--ink`, `--paper`, `--lead`, `--graphite`, `--rule`, `--ash`, `--ghost`, `--amd-signal`, `--volt`, `--volt-dim`, `--volt-border`, `--cleared`, `--caution`, `--conflict`, `--parchment`, `--stamp-green`, `--error`
    - Add shape tokens: `--radius-card: 6px`, `--radius-btn: 8px`, `--radius-badge: 4px`, `--radius-pill: 100px`
    - Add spacing token: `--spacing-unit: 8px`
    - Update all Tailwind-mapped aliases (`--background`, `--foreground`, `--primary`, `--card`, `--border`, etc.) to point at new tokens so existing Tailwind utility classes continue to work
    - Remove legacy tokens: `--accent-blue`, `--bg-primary`, `--bg-secondary`, `--bg-tertiary`, `--border-default`, `--border-active`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9_

  - [x] 1.3 Update keyframes and animation utilities in index.css
    - Update `shimmer` keyframe gradient colors from `#3B7BF6 / #6B9FFF` to `#00D4FF / #66E9FF`
    - Update `borderPulse` keyframe rgba values from `rgba(59, 123, 246, ...)` to `rgba(0, 212, 255, ...)`
    - Add new `voltPulse` keyframe: `0%, 100% { transform: scale(1); opacity: 0.4; } 50% { transform: scale(1.08); opacity: 0.8; }`
    - Update `.shimmer-bar` gradient to volt colors
    - Update `.scan-line` rgba tint from blue to volt
    - _Requirements: 1.7, 6.5, 12.2_

- [x] 2. Shared Components: NavigationBar, Buttons, Card, Badges, DocumentStack
  - [x] 2.1 Rewrite NavigationBar.tsx with new design system
    - Set height to 60px, background `rgba(12, 14, 20, 0.96)`, `backdropFilter: blur(12px)`, border-bottom `1px solid var(--rule)`
    - Replace logo with: 14×14px cyan square (`--volt`, `transform: rotate(45deg)`) + "Clausify" in Syne 700 + "AI" in Syne 700 colored `--volt`
    - Add "How it works" nav link text in IBM Plex Sans 500, `--ash` color
    - Right side: GhostButton "Try Demo" + AMDBadge
    - Mobile (<768px): hide nav links and "Try Demo", show logo + AMD badge only
    - Update AMDBadge: replace Inter with IBM Plex Sans 500, keep `--amd-signal` color
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 15.1_

  - [x] 2.2 Rewrite Buttons.tsx with new design system
    - `PrimaryButton`: `background: var(--volt)`, `color: var(--ink)` (dark text on cyan), `borderRadius: var(--radius-btn)`, hover: `filter: brightness(1.1)`, disabled: `background: var(--graphite)`, `color: var(--ghost)`, `opacity: 0.5`
    - `GhostButton`: `border: 1px solid var(--rule)`, `color: var(--ash)`, hover: `borderColor: var(--volt-border)`, `color: var(--paper)`, `borderRadius: var(--radius-btn)`
    - Use IBM Plex Sans 500 for button text
    - _Requirements: 1.7, 2.3_

  - [x] 2.3 Rewrite Card.tsx with new design system
    - `background: var(--lead)` (#1A1D27), `border: 1px solid var(--rule)` (#2A2D3E), `borderRadius: var(--radius-card)` (6px)
    - Hover: `borderColor → var(--volt-border)`, `translateY(-2px)`, `boxShadow: 0 8px 32px rgba(0,212,255,0.08)`
    - _Requirements: 9.1_

  - [x] 2.4 Rewrite Badges.tsx and add EvidenceBox component
    - `RiskBadge`: Update color map — HIGH uses `rgba(237, 28, 36, 0.12)` bg + `--amd-signal` text, MEDIUM uses `--caution`, LOW uses `--cleared`; font: IBM Plex Sans 600
    - `EvidenceTag`: `background: var(--graphite)`, `border: 1px solid var(--rule)`, font: IBM Plex Mono, text color: `--ash`
    - Add new `EvidenceBox` export: `background: var(--parchment)` (#E8E4DA), `color: var(--lead)` (#1A1D27 dark text), font: IBM Plex Mono 400, `borderRadius: 4px`, `padding: 12px`
    - _Requirements: 8.3, 9.3, 11.3, 15.1, 15.3, 15.4, 15.5_

  - [x] 2.5 Create new DocumentStack.tsx component with framer-motion
    - Interface: `DocumentStackProps { files: File[]; onRemove: (index: number) => void }`
    - Use `AnimatePresence` for coordinated enter/exit animations
    - Each `PaperCard` is a `motion.div` with spring physics: `initial: { opacity: 0, y: -20 }`, `animate: { opacity: 1, y: 0 }`, `exit: { opacity: 0, y: 20 }`, `transition: { type: 'spring', stiffness: 300, damping: 30 }`
    - Deterministic rotation per card: `((index * 137) % 9) - 4` degrees, memoized with `useMemo`
    - PaperCard visual: `background: #F2EFE8`, `borderRadius: 4px`, `boxShadow: 0 2px 8px rgba(0,0,0,0.18)`
    - Content: file-type pill ("PDF" or "IMG") in IBM Plex Mono, filename in IBM Plex Sans, file size in IBM Plex Mono
    - Remove button: `×` in top-right corner, triggers `onRemove(index)`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 17.3_

- [x] 3. Checkpoint — Verify foundation and components compile
  - Ensure `tsc --noEmit` passes, ask the user if questions arise.

- [x] 4. Pages: Landing page full rewrite
  - [x] 4.1 Rewrite Landing.tsx with new design system
    - Container: `max-width: 1200px`, left-aligned on desktop (`align-items: flex-start`), centered on mobile (<768px)
    - Eyebrow: IBM Plex Mono 11px, `--volt`, uppercase text (no pill border)
    - Headline: Syne 800, `clamp(32px, 5.5vw, 60px)`, `line-height: 1.05`; "at once" wrapped in `<span>` with `textDecoration: underline; textDecorationColor: var(--volt)`
    - Upload zone: 600px max-width, left-aligned; idle state has 3 CSS-only stacked paper shapes; active state renders `<DocumentStack>` component; loading state shows AMD processing view
    - Analyze button: Full width of the upload zone, uses redesigned `PrimaryButton`
    - Stats row: Left-aligned; "5.6×" in `--volt`
    - "How it works": 3 cards with step-connector lines between them
    - Event badge: use `--volt-dim` background and `--volt-border` border
    - Mobile (<768px): center-aligned, upload zone shows "Tap to select"
    - Replace all legacy colors (#3B7BF6→#00D4FF, #080D1A→#0C0E14, #0D1528→#1A1D27, etc.)
    - Replace all font references (DM Sans→Syne, Inter→IBM Plex Sans, JetBrains Mono→IBM Plex Mono)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 6.1, 6.2, 6.3, 6.4, 6.5, 18.1_

- [x] 5. Pages: Dashboard page full rewrite
  - [x] 5.1 Rewrite Dashboard.tsx with new design system
    - Sidebar (260px): `background: var(--lead)`, `borderRight: 1px solid var(--rule)`, document list with PDF stamp in `--conflict` (red) and IMG stamp in `--volt` (cyan), IBM Plex Sans for filenames, IBM Plex Mono for status
    - Bottom sidebar: `GhostButton` "Upload More" + "New Session" text link + `AMDBadge`
    - Sticky top bar: "Analysis Results" in Syne 700, export/report buttons
    - `ConflictAlert`: `borderLeft: 4px solid var(--amd-signal)`, `background: rgba(237,28,36,0.06)`, "CONFLICTS DETECTED" label in IBM Plex Sans 600 uppercase `--amd-signal`, expandable (collapsed by default), `EvidenceBox` per conflict excerpt with `--paper` background and dark text
    - `AnalysisCardGrid` (4 cards): Executive Summary (Syne 700 title, IBM Plex Sans 400 `--ash` body), Risk Analysis (`RiskBadge` per risk), Comparison Matrix (alternating `--lead` / `rgba(37,40,54,0.5)` rows), Recommendation (`--volt-dim` bg, `--volt-border` border, confidence bar)
    - AMD Performance Banner: `--amd-signal` for Cpu icon and AMD label, stat values in IBM Plex Mono 700
    - Mobile (<768px): hide sidebar, show toggle button for drawer
    - Replace all legacy colors and font references throughout
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 15.1, 15.2, 15.3, 15.4, 15.5, 18.2_

- [x] 6. Pages: Chat page full rewrite
  - [x] 6.1 Rewrite Chat.tsx with new design system
    - Left panel (280px desktop): document pills + question chips with `--lead` bg and `--rule` border, hover `--volt-border`, IBM Plex Sans
    - Header: Replace hexagonal AI avatar with document-icon avatar (`FileText` from lucide, 40×40px container, `border: 1px solid rgba(0,212,255,0.4)`, `animation: voltPulse`)
    - User message bubble: `background: var(--graphite)` (#252836), `borderRadius: 12px 12px 4px 12px`
    - AI message bubble: `background: var(--lead)`, `borderLeft: 3px solid var(--volt)`, `borderRadius: 4px 12px 12px 12px`
    - AI sections: ANSWER / EVIDENCE / RISK / RECOMMENDATION labels in IBM Plex Sans 600 uppercase `--ghost`
    - Evidence: use `EvidenceBox` with `--parchment` background (#E8E4DA) and dark text (#1A1D27)
    - Streaming cursor: 2px wide `background: var(--volt)`, `animation: blink`
    - ThinkingAnimation: 3 dots in `--volt`, `boxShadow: 0 0 6px rgba(0,212,255,0.5)`, staggered 0.2s using `pulseDot` keyframe
    - Input bar: `background: var(--lead)`, `borderColor: var(--rule)` → `var(--volt-border)` on focus; Paperclip in `--ghost`; send button `--volt` when active, `--graphite` opacity 0.5 when inactive
    - Mobile (<768px): full height, input bar fixed at bottom, chips scrollable horizontally
    - Replace all legacy colors and font references throughout
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 12.1, 12.2, 12.3, 12.4, 13.1, 13.2, 13.3, 13.4, 13.5, 18.3_

- [x] 7. Pages: Demo page full rewrite
  - [x] 7.1 Rewrite Demo.tsx with new design system
    - Demo banner: `background: rgba(245,166,35,0.08)`, `borderBottom: 1px solid rgba(245,166,35,0.25)`, Target icon + "DEMO MODE" text in `--caution`
    - Same sidebar, AnalysisCardGrid, ConflictAlert layout as Dashboard, populated from `getDemoData()`
    - Chat preview: pre-seeded messages using `EvidenceBox` with `--parchment` background
    - CTA buttons: "Upload Documents" and "Try Full Chat" using redesigned buttons
    - Replace all legacy colors and font references throughout
    - Mobile: single-column layout with drawer toggle
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 18.4_

- [x] 8. Checkpoint — Verify all pages compile and render
  - Ensure `tsc --noEmit` passes and `npm run build` succeeds, ask the user if questions arise.

- [x] 9. Verification and cleanup
  - [x] 9.1 Verify no legacy color/font values remain in source
    - Grep all `.tsx` and `.css` files under `frontend/src/` for legacy hex values: `#3B7BF6`, `#080D1A`, `#0D1528`, `#111E35`, `#1E2D4A`, `#8B9CC8`, `#4A5878`, `#F0F4FF`
    - Grep for legacy font references: `DM Sans`, `Inter,` (with comma to avoid false positives), `JetBrains Mono`
    - Fix any remaining occurrences
    - _Requirements: 1.3, 1.4, 1.5, 1.7, 2.7, 2.8, 2.9_

  - [x] 9.2 Verify API integration preservation
    - Confirm `api.ts`, `types.ts`, and `store.tsx` are unmodified
    - Confirm all pages still import and call the same API functions: `uploadDocuments`, `analyzeDocuments`, `streamChatMessage`, `exportReport`, `getDemoData`, `getSuggestedQuestions`
    - Confirm `sonner` toast error handling is still in place
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 16.8_

  - [x] 9.3 Verify AMD signal color constraint
    - Grep for `#ED1C24` usage — confirm it only appears in: AMDBadge, ConflictAlert borders/labels, HIGH risk badges
    - Confirm standard error states use `#EF4444` (`--error`), not `--amd-signal`
    - _Requirements: 15.1, 15.2_

  - [x]* 9.4 Write property tests for DocumentStack component
    - **Property 1: DocumentStack card count matches file count**
    - **Property 3: DocumentStack removal reduces count by one**
    - **Validates: Requirements 5.1, 5.6**

  - [x]* 9.5 Write property tests for RiskBadge and ConflictAlert
    - **Property 4: ConflictAlert renders iff conflicts exist**
    - **Property 6: RiskBadge color is determined exclusively by risk level**
    - **Validates: Requirements 8.1, 8.2, 9.3, 15.1, 15.3, 15.4, 15.5**

  - [x]* 9.6 Write property tests for EvidenceBox and send button
    - **Property 5: EvidenceBoxes inside ConflictAlert use paper background with dark text**
    - **Property 7: EvidenceBoxes in AI messages use parchment background with dark text**
    - **Property 8: Send button state is determined by input value trimmed emptiness**
    - **Validates: Requirements 8.3, 11.3, 13.3, 13.4**

- [x] 10. Final checkpoint — Ensure all tests pass
  - Ensure `tsc --noEmit` and `npm run build` pass without errors, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- The `motion` package (v12) already exists in package.json; verify it provides `AnimatePresence` and `motion.div` — if not, install `framer-motion` explicitly
- All existing TypeScript types, Context+Reducer dispatch patterns, and API call sites must remain intact
- Color migration map is in the design document for reference during implementation

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5"] },
    { "id": 2, "tasks": ["4.1"] },
    { "id": 3, "tasks": ["5.1", "6.1", "7.1"] },
    { "id": 4, "tasks": ["9.1", "9.2", "9.3"] },
    { "id": 5, "tasks": ["9.4", "9.5", "9.6"] }
  ]
}
```
