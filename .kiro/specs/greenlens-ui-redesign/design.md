# Design Document — Base UI Redesign (Pre-GreenLens, "Clausify" naming)

> **NOTE:** This spec was written and implemented before the rebrand to "GreenLens." It accurately documents the base UI architecture already built into the codebase. See `.kiro/steering/greenlens-design-system.md` for the current GreenLens brand layer on top of this architecture.

## Overview

This document describes the technical design for the complete UI redesign of the Clausify AI frontend. The redesign replaces the existing electric-blue-on-navy aesthetic with a high-contrast, document-centric design system built around a cyan accent (`#00D4FF`), warm paper textures, and editorial typography (Syne + IBM Plex Sans/Mono). All four pages — Landing, Dashboard, Chat, Demo — are in scope. No backend API contracts are changed.

### Goals

- Replace every hardcoded legacy color, font, and spacing value with the new Design_System token set
- Introduce `framer-motion` for the DocumentStack spring animation
- Maintain 100% API surface compatibility — `api.ts`, `types.ts`, and `store.tsx` are read-only
- Achieve a consistent, document-intelligence brand voice across all pages and breakpoints
- Keep all existing TypeScript types, Context+Reducer dispatch patterns, and API call sites intact

### Non-Goals

- Backend changes of any kind
- Adding new routes or page structure beyond what already exists
- Replacing the Context+Reducer store or React Router setup
- Accessibility audit beyond basic semantic HTML (full WCAG validation requires manual testing)

---

## Architecture

The redesign is a pure presentation layer change. The component and page hierarchy stays the same; only styles, JSX markup, and one new component file are added or modified.

```
frontend/
├── index.html                        ← Add Google Fonts <link>
├── src/
│   ├── styles/
│   │   ├── theme.css                 ← Full token replacement
│   │   └── index.css                 ← Updated keyframes (shimmer, borderPulse, voltPulse)
│   └── app/
│       ├── components/
│       │   ├── NavigationBar.tsx     ← Full rewrite
│       │   ├── Buttons.tsx           ← Full rewrite
│       │   ├── Card.tsx              ← Full rewrite
│       │   ├── Badges.tsx            ← Full rewrite
│       │   └── DocumentStack.tsx     ← NEW component (framer-motion)
│       └── pages/
│           ├── Landing.tsx           ← Full rewrite
│           ├── Dashboard.tsx         ← Full rewrite
│           ├── Chat.tsx              ← Full rewrite
│           └── Demo.tsx              ← Full rewrite
```

### Data flow (unchanged)

Pages dispatch Context+Reducer actions (`useAppDispatch`) and call `api.ts` functions exactly as before. The redesign does not touch state management. Props flowing into components remain identical — `AnalyzeResponse`, `DemoResponse`, `ChatResponse` etc. are consumed identically, just rendered differently.

### Dependency addition

`framer-motion` is added to `frontend/package.json`. It is used exclusively in `DocumentStack.tsx`. No other new runtime dependencies are introduced.

---

## Components and Interfaces

### `theme.css` — Design System Token Replacement

The existing token sheet is fully replaced. Legacy tokens (`--accent-blue`, `--bg-primary`, `--bg-secondary`, `--bg-tertiary`, `--border-default`, `--border-active`) are removed. The new canonical token set:

```css
:root {
  /* Core palette */
  --ink:         #0C0E14;
  --paper:       #F2EFE8;
  --lead:        #1A1D27;
  --graphite:    #252836;
  --rule:        #2A2D3E;
  --ash:         #9297A8;
  --ghost:       #4A4F63;

  /* Brand / semantic */
  --amd-signal:  #ED1C24;
  --volt:        #00D4FF;
  --volt-dim:    rgba(0, 212, 255, 0.08);
  --volt-border: rgba(0, 212, 255, 0.20);
  --cleared:     #00C48C;
  --caution:     #F5A623;
  --conflict:    #ED1C24;
  --parchment:   #E8E4DA;
  --stamp-green: #1A4731;
  --error:       #EF4444;

  /* Shape */
  --radius-card: 6px;
  --radius-btn:  8px;
  --radius-badge: 4px;
  --radius-pill: 100px;

  /* Spacing */
  --spacing-unit: 8px;
}
```

Tailwind-mapped aliases (`--background`, `--foreground`, `--primary`, `--card`, etc.) are updated to point at the new tokens so existing Tailwind utility classes continue to work without modification.

### `index.html` — Google Fonts

A single `<link>` tag is added to `<head>` to load all three typefaces in one request:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
```

### `index.css` — Animation Updates

Three keyframe changes are required:

1. **`shimmer`** — gradient colors change from `#3B7BF6 / #6B9FFF` to `#00D4FF / #66E9FF`
2. **`borderPulse`** — rgba values change from `rgba(59,123,246,...)` to `rgba(0,212,255,...)`
3. **`voltPulse`** (new) — scale + opacity pulse for the Chat avatar ring:
   ```css
   @keyframes voltPulse {
     0%, 100% { transform: scale(1);   opacity: 0.4; }
     50%       { transform: scale(1.08); opacity: 0.8; }
   }
   ```
4. **`.shimmer-bar`** — gradient updated to volt colors
5. **`.scan-line`** — rgba tint updated from blue to volt

### `NavigationBar.tsx`

**Props interface** (unchanged): `{ showDemo?: boolean }`

**Visual changes:**
- Height: `60px` (was 64px)
- Background: `rgba(12, 14, 20, 0.96)` + `backdropFilter: blur(12px)`
- Border bottom: `1px solid var(--rule)`
- Logo: 14×14px `--volt` square with `transform: rotate(45deg)` + "Clausify" in Syne 700 + "AI" in `--volt`
- Nav links: "How it works" text link in IBM Plex Sans 500, `--ash` color
- Right: `GhostButton` "Try Demo" + `AMDBadge`
- Mobile (<768px): hide nav links and "Try Demo", show logo + AMD badge only

**AMDBadge** (exported from same file): unchanged logic, IBM Plex Sans 500 replaces Inter.

### `Buttons.tsx`

**`PrimaryButton`**:
- `background: var(--volt)`, `color: var(--ink)` — dark text on cyan (critical change from old light text)
- `borderRadius: var(--radius-btn)` (8px)
- Hover: `filter: brightness(1.1)` (replaces color swap)
- Disabled: `background: var(--graphite)`, `color: var(--ghost)`, `opacity: 0.5`

**`GhostButton`**:
- `border: 1px solid var(--rule)`, `color: var(--ash)`
- Hover: `borderColor: var(--volt-border)`, `color: var(--paper)`
- `borderRadius: var(--radius-btn)` (8px)

### `Card.tsx`

```tsx
// background: var(--lead)   #1A1D27
// border: 1px solid var(--rule)  #2A2D3E
// borderRadius: var(--radius-card)  6px
// hover: borderColor → var(--volt-border), translateY(-2px)
//        boxShadow → 0 8px 32px rgba(0,212,255,0.08)
```

The `className` prop changes from `rounded-xl` to `rounded` (controlled by `--radius-card` token).

### `Badges.tsx`

**`RiskBadge`** color map:
| Level  | Background                    | Border                           | Text           |
|--------|-------------------------------|----------------------------------|----------------|
| HIGH   | `rgba(237, 28, 36, 0.12)`     | `rgba(237, 28, 36, 0.25)`        | `--amd-signal` |
| MEDIUM | `rgba(245, 166, 35, 0.12)`    | `rgba(245, 166, 35, 0.25)`       | `--caution`    |
| LOW    | `rgba(0, 196, 140, 0.12)`     | `rgba(0, 196, 140, 0.25)`        | `--cleared`    |

Font: IBM Plex Sans 600 (replaces Inter).

**`EvidenceTag`**:
- `background: var(--graphite)`, `border: 1px solid var(--rule)`
- Font: IBM Plex Mono (replaces JetBrains Mono)
- Text color: `var(--ash)`

**`EvidenceBox`** (new exported component from `Badges.tsx`):
```tsx
// Used in ConflictAlert and AI chat messages
// background: var(--parchment)  #E8E4DA — warm off-white
// color: var(--lead)  #1A1D27 — dark text
// font: IBM Plex Mono 400
// borderRadius: 4px, padding: 12px
```

### `DocumentStack.tsx` (NEW)

```tsx
interface DocumentStackProps {
  files: File[];
  onRemove: (index: number) => void;
}
```

Architecture:
- `AnimatePresence` wraps all cards for coordinated enter/exit
- Each `PaperCard` is a `motion.div` with:
  - `initial: { opacity: 0, y: -20 }`
  - `animate: { opacity: 1, y: 0 }`
  - `exit: { opacity: 0, y: 20 }`
  - `transition: { type: 'spring', stiffness: 300, damping: 30 }`
- Rotation is seeded with `useMemo` per file index to avoid re-randomizing on re-render:
  ```ts
  const rotation = useMemo(() =>
    ((index * 137) % 9) - 4,   // deterministic "random" in [-4, +4]
  [index]);
  ```
- PaperCard visual: `background: #F2EFE8`, `borderRadius: 4px`, `boxShadow: 0 2px 8px rgba(0,0,0,0.18)`, `transform: rotate({rotation}deg)`
- Content: file-type pill ("PDF" or "IMG") in IBM Plex Mono, filename in IBM Plex Sans, file size in IBM Plex Mono
- Remove button: `×` in top-right corner, triggers `onRemove(index)`

### Landing Page (`Landing.tsx`)

Key structural changes:
- **Container**: `max-width: 1200px`, left-aligned on desktop (`align-items: flex-start`), centered on mobile
- **Eyebrow**: IBM Plex Mono 11px, `--volt`, uppercase text (no pill border)
- **Headline**: Syne 800, `clamp(32px, 5.5vw, 60px)`, `line-height: 1.05`; "at once" wrapped in `<span>` with `textDecoration: underline; textDecorationColor: var(--volt)`
- **Upload zone**: 600px max-width, left-aligned; idle state has 3 CSS-only stacked paper shapes; active state renders `<DocumentStack>` component; loading state shows AMD processing view
- **Analyze button**: Full width of the upload zone, uses redesigned `PrimaryButton`
- **Stats row**: Left-aligned; "5.6×" in `--volt`
- **How it works**: 3 cards with step-connector lines between them, tightly spaced

Mobile (<768px): center-aligned, upload zone shows "Tap to select" text.

### Dashboard Page (`Dashboard.tsx`)

Layout: `display: flex`, `height: 100dvh` or full scroll.
- **Sidebar** (260px, `background: var(--lead)`, `borderRight: 1px solid var(--rule)`):
  - Document list: PDF stamp in `--conflict` (red), IMG stamp in `--volt` (cyan)
  - Bottom: `GhostButton` "Upload More" + "New Analysis" text link + `AMDBadge`
- **Main area**:
  - Sticky top bar: "Analysis Results" in Syne 700 + export/report buttons
  - `ConflictAlert` when `analysis.conflicts.length > 0`
  - `AnalysisCardGrid`: 2-column responsive grid

**ConflictAlert** structure:
```tsx
// Container: borderLeft: '4px solid var(--amd-signal)', background: 'rgba(237,28,36,0.06)'
// Header: "CONFLICTS DETECTED" in IBM Plex Sans 600 uppercase, --amd-signal
// Body: expandable, EvidenceBox per conflict excerpt
// Default: collapsed
```

**AnalysisCardGrid** (four `Card` instances):
1. Executive Summary: Syne 700 title, IBM Plex Sans 400 body in `--ash`
2. Risk Analysis: `RiskBadge` per risk item; HIGH→`--amd-signal`, MEDIUM→`--caution`, LOW→`--cleared`
3. Comparison Matrix: alternating row backgrounds `--lead` / `rgba(37,40,54,0.5)`
4. Recommendation: `--volt-dim` background tint, `--volt-border` border; confidence bar gradient

### Chat Page (`Chat.tsx`)

Layout: `height: 100dvh`, flex column.
- **Left panel** (280px desktop, drawer on mobile): document pills + question chips
  - Chips: `background: var(--lead)`, `border: 1px solid var(--rule)`, hover `--volt-border`
- **Header**: document-icon avatar (`FileText` from lucide, 40×40px container, `border: 1px solid rgba(0,212,255,0.4)`, animated with `voltPulse` keyframe)
- **Message bubbles**:
  - User: `background: var(--graphite)`, `borderRadius: 12px 12px 4px 12px`
  - AI: `background: var(--lead)`, `borderLeft: 3px solid var(--volt)`, `borderRadius: 4px 12px 12px 12px`
  - AI sections: ANSWER / EVIDENCE / RISK / RECOMMENDATION labels in IBM Plex Sans 600 uppercase `--ghost`
  - Evidence: `EvidenceBox` with `--parchment` background
  - Streaming cursor: 2px wide `background: var(--volt)`, `animation: blink`
- **ThinkingAnimation**: 3 dots, `background: var(--volt)`, `boxShadow: 0 0 6px rgba(0,212,255,0.5)`, staggered 0.2s offsets using existing `pulseDot` keyframe
- **Input bar**: `background: var(--lead)`, `borderColor: var(--rule)` → `var(--volt-border)` on focus; send button `--volt` when active, `--graphite` opacity 0.5 when inactive

### Demo Page (`Demo.tsx`)

Identical layout structure to Dashboard. Additions:
- **Demo banner** at top: `background: rgba(245,166,35,0.08)`, `borderBottom: 1px solid rgba(245,166,35,0.25)`, `Target` icon + "DEMO MODE" text in `--caution`
- Same sidebar, AnalysisCardGrid, ConflictAlert as Dashboard, populated from `getDemoData()`
- Chat preview section at bottom with pre-seeded messages using `EvidenceBox` with `--parchment`
- CTA buttons: "Upload Documents" and "Try Full Chat"

---

## Data Models

No data model changes. All types in `src/lib/types.ts` are preserved verbatim:

```
UploadedDocument, UploadResponse, Risk, Conflict, ComparisonRow,
Recommendation, Analysis, AnalyzeResponse, Evidence,
StructuredAIResponse, ChatResponse, PreSeededMessage, DemoResponse
```

The `DocumentStack` component accepts `File[]` (browser-native File API) and `onRemove: (index: number) => void` — both are standard types requiring no new declarations.

### Color migration map (implementation reference)

| Legacy value | New value | Token |
|---|---|---|
| `#3B7BF6` | `#00D4FF` | `--volt` |
| `#080D1A` | `#0C0E14` | `--ink` |
| `#0D1528` | `#1A1D27` | `--lead` |
| `#111E35` | `#252836` | `--graphite` |
| `#1E2D4A` | `#2A2D3E` | `--rule` |
| `#8B9CC8` | `#9297A8` | `--ash` |
| `#4A5878` | `#4A4F63` | `--ghost` |
| `#F0F4FF` | `#F2EFE8` | `--paper` |
| `#10B981` | `#00C48C` | `--cleared` |
| `#F59E0B` | `#F5A623` | `--caution` |
| `DM Sans` | `Syne` | display font |
| `Inter` | `IBM Plex Sans` | body font |
| `JetBrains Mono` | `IBM Plex Mono` | mono font |

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

This feature is a UI redesign primarily involving CSS tokens, typography, and layout. The majority of acceptance criteria are static configuration checks (SMOKE) or specific rendering assertions (EXAMPLE) that do not benefit from property-based testing. However, several acceptance criteria involve parameterized rendering logic that does vary meaningfully with input — specifically the DocumentStack component and the risk/conflict display logic. Property-based tests are appropriate for these.

The following properties are identified after prework analysis and redundancy reflection:

---

### Property 1: DocumentStack card count matches file count

*For any* non-empty array of `File` objects passed to `DocumentStack`, the number of rendered `PaperCard` elements SHALL equal the length of the files array.

**Validates: Requirements 5.1**

---

### Property 2: PaperCard correctness for any file

*For any* `File` object rendered as a `PaperCard`, the card SHALL have `background: #F2EFE8` (--paper), a rotation value between -4° and +4° inclusive, a visible drop shadow, the correct file-type stamp ("PDF" or "IMG"), the filename, and the formatted file size.

**Validates: Requirements 5.3, 5.4**

---

### Property 3: DocumentStack removal reduces count by one

*For any* `DocumentStack` with N ≥ 1 cards, calling `onRemove` with any valid index `i` (0 ≤ i < N) SHALL result in the DocumentStack rendering exactly N-1 cards after the removal.

**Validates: Requirements 5.6**

---

### Property 4: ConflictAlert renders iff conflicts exist

*For any* `analysis` object, the `ConflictAlert` component SHALL render if and only if `analysis.conflicts.length > 0`. When rendered, the container SHALL have a 4px left border in `--amd-signal` (#ED1C24) and a background tinted with `rgba(237, 28, 36, 0.06)`. When not rendered, no ConflictAlert element SHALL appear in the DOM.

**Validates: Requirements 8.1, 8.2**

---

### Property 5: EvidenceBoxes inside ConflictAlert use paper background with dark text

*For any* `Conflict` object with non-empty `documentA.excerpt` and `documentB.excerpt`, the `EvidenceBox` elements rendered inside `ConflictAlert` SHALL have `background: #F2EFE8` (--paper) and text color `#1A1D27` (--lead, dark text on light background — NOT light text on dark).

**Validates: Requirements 8.3**

---

### Property 6: RiskBadge color is determined exclusively by risk level

*For any* `Risk` object, the `RiskBadge` SHALL use `--amd-signal` (#ED1C24) for HIGH level, `--caution` (#F5A623) for MEDIUM level, and `--cleared` (#00C48C) for LOW level — and SHALL NOT use any other color for the badge text or border regardless of other fields on the risk object.

**Validates: Requirements 9.3, 15.1, 15.3, 15.4, 15.5**

---

### Property 7: EvidenceBoxes in AI messages use parchment background with dark text

*For any* `StructuredAIResponse` with one or more `evidence` items, each `EvidenceBox` rendered in the AI message bubble SHALL have `background: #E8E4DA` (--parchment) and text color `#1A1D27` (dark text — NOT white text on dark background).

**Validates: Requirements 11.3**

---

### Property 8: Send button state is determined by input value trimmed emptiness

*For any* string value in the chat input field, the send button SHALL render with `background: var(--volt)` (#00D4FF) and full opacity when `value.trim().length > 0`, and SHALL render with `background: var(--graphite)` (#252836) and opacity 0.5 when `value.trim().length === 0`.

**Validates: Requirements 13.3, 13.4**

---

## Error Handling

### API errors (preserved behavior)

All API error handling is unchanged. When any API call returns a non-2xx status, the existing `try/catch` blocks propagate the error message to a `toast.error()` call via `sonner`. The redesign updates the visual style of any inline error banners to use `--error` (#EF4444) rather than `--amd-signal` (#ED1C24), enforcing the color constraint in Requirement 15.2.

### File validation errors

The Landing page file-type and file-count validation logic is unchanged. Error banners use `--error` styling.

### `framer-motion` import errors

If `framer-motion` is not installed, `DocumentStack.tsx` will fail to compile. The fix is `npm install framer-motion` in `frontend/`. The package is pinned with a caret in `package.json` (e.g., `"framer-motion": "^11.0.0"`).

### Color constraint enforcement

`--amd-signal` is only used in: `AMDBadge`, `ConflictAlert` border/labels, and HIGH-level `RiskBadge`. All other error states use `--error`. This is enforced by design in the new component implementations; no runtime guard is needed.

### Font loading fallbacks

Each `font-family` declaration includes system fallbacks:
- `'Syne', sans-serif`
- `'IBM Plex Sans', sans-serif`
- `'IBM Plex Mono', monospace`

If Google Fonts fails to load, the page degrades gracefully to system fonts.

---

## Testing Strategy

### PBT applicability assessment

This feature is primarily a UI redesign. Most acceptance criteria are not amenable to property-based testing:
- Token/CSS configuration checks → SMOKE tests (grep/snapshot)
- Font usage checks → SMOKE tests (grep .tsx files)
- Layout and rendering at specific viewports → EXAMPLE-based component tests
- API integration preservation → INTEGRATION tests (existing backend test suite)

However, the DocumentStack animation component and the conditional rendering of risk/conflict UI elements **do** involve parameterized logic where input variation reveals correctness failures. Property-based tests are appropriate for these 8 properties above.

**Chosen PBT library**: `fast-check` (TypeScript-native, works with Vitest)

### Unit tests (example-based)

Focus areas:
- `NavigationBar`: renders logo mark correctly, collapses at 375px viewport
- `PrimaryButton`: dark text (`--ink`) on volt background; disabled state shows graphite
- `GhostButton`: correct border/color, hover state transitions
- `RiskBadge`: renders correct icon and label for each level
- `EvidenceTag`: renders filename with IBM Plex Mono
- `ConflictAlert`: collapsed by default, expands on toggle click
- `ThinkingAnimation`: three dots present, correct class names
- `StreamingCursor`: renders 2px wide blink element when active
- `AMDBadge`: uses `--amd-signal` exclusively

### Property-based tests

Each test uses `fast-check` with a minimum of 100 iterations and is tagged with a comment referencing the design property:

```ts
// Feature: clausify-ui-redesign, Property 1: DocumentStack card count matches file count
test.prop([fc.array(fc.record({ name: fc.string(), size: fc.integer() }), { minLength: 1 })])(
  'DocumentStack renders N cards for N files',
  (files) => { ... }
);
```

Tag format: `Feature: clausify-ui-redesign, Property {N}: {property_text}`

Property tests to implement:
1. DocumentStack card count (Property 1) — `fc.array(fileArb, { minLength: 1 })`
2. PaperCard correctness (Property 2) — `fc.record({ name, size, type })`
3. DocumentStack removal (Property 3) — `fc.array(fileArb, { minLength: 1 })` + `fc.nat()`
4. ConflictAlert conditional render (Property 4) — `fc.array(conflictArb)` for both empty and non-empty
5. EvidenceBox paper background in ConflictAlert (Property 5) — `fc.array(conflictArb, { minLength: 1 })`
6. RiskBadge color by level (Property 6) — `fc.constantFrom('HIGH', 'MEDIUM', 'LOW')`
7. EvidenceBox parchment background in AI messages (Property 7) — `fc.array(evidenceArb, { minLength: 1 })`
8. Send button state by input value (Property 8) — `fc.string()`

### Integration / smoke tests

- `theme.css` contains all required custom property names (grep/snapshot)
- No file in `src/` contains legacy hex values `#3B7BF6`, `#080D1A`, `#0D1528`, `#111E35`, `#1E2D4A`, `DM Sans`, `Inter,`, `JetBrains Mono`
- `framer-motion` appears in `package.json` dependencies
- TypeScript compilation (`tsc --noEmit`) passes without errors
- API integration smoke: existing backend test suite in `backend/tests/` continues to pass

### Testing configuration

- Vitest + `@testing-library/react` for component rendering
- `fast-check` for property generation
- Each property test configured for 100+ iterations (fast-check default is 100)
- Test files co-located alongside components in `src/app/components/__tests__/`
