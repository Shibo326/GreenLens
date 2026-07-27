# Requirements Document

> **NOTE:** This spec was written and implemented before the project's rebrand from "Clausify" to "GreenLens." It accurately describes the base UI architecture (tokens, typography, component structure) as it was built and already exists in the codebase today — do not treat "Clausify" mentions below as inaccurate, they describe real completed work. For the current brand identity on top of this architecture (colors, component labels, copy), see `.kiro/steering/greenlens-design-system.md` and the `.kiro/specs/greenlens-pivot/` spec.

## Introduction

This document specifies requirements for the complete UI redesign of the Clausify AI frontend. The redesign transforms the existing React + TypeScript + Tailwind application from its current electric-blue-on-navy aesthetic into a high-contrast, document-centric design system built around a cyan accent color, physical paper aesthetics, and editorial typography. All four pages (Landing, Dashboard, Chat, Demo) are in scope. Every existing API integration must remain fully functional throughout the redesign.

## Glossary

- **App**: The Clausify AI frontend React + TypeScript + Tailwind application.
- **Design_System**: The new token set defining colors, typography, spacing, and border-radius values specified in this document.
- **Token**: A CSS custom property in `theme.css` that maps a semantic name to a concrete value.
- **Landing_Page**: The upload / hero page at route `/`.
- **Dashboard_Page**: The analysis results page at route `/dashboard`.
- **Chat_Page**: The Decision Copilot chat page at route `/chat`.
- **Demo_Page**: The pre-loaded demo page at route `/demo`.
- **NavigationBar**: The shared sticky top navigation component.
- **DocumentStack**: The framer-motion animated stack of uploaded files rendered as physical paper cards.
- **PaperCard**: An individual card in the DocumentStack with warm off-white background (#F2EFE8), rotation, and file stamp.
- **EvidenceBox**: A paper-colored (#F2EFE8) excerpt container used in conflict alerts and AI responses.
- **ConflictAlert**: The banner that shows detected document conflicts with a REDLINE stamp aesthetic and 4px left border in AMD-signal red.
- **AnalysisCardGrid**: The 2×2 grid of analysis result cards on the Dashboard and Demo pages.
- **ThinkingAnimation**: The sequential cyan dots animation shown while the AI is processing.
- **StreamingCursor**: The blinking cursor appended to streaming token output in Chat.
- **AMD_Badge**: The AMD MI300X performance badge using AMD-signal red.
- **RiskBadge**: A small badge indicating HIGH / MEDIUM / LOW risk level.
- **EvidenceTag**: A monospace chip displaying a source filename.
- **API**: The backend REST and SSE endpoints consumed by the frontend.
- **Volt**: The new primary cyan accent color `#00D4FF`.
- **Ink**: The new primary background color `#0C0E14`.
- **Paper**: The warm off-white document color `#F2EFE8`.
- **Lead**: The card background color `#1A1D27`.
- **Graphite**: The elevated surface / hover state color `#252836`.
- **Rule**: The border / divider color `#2A2D3E`.
- **Ash**: The secondary text color `#9297A8`.
- **Ghost_Color**: The tertiary text / placeholder color `#4A4F63`.
- **AMD_Signal**: The AMD / conflict / critical-risk-only red `#ED1C24`.
- **Cleared**: The success / low-risk green `#00C48C`.
- **Caution**: The medium-risk / warning amber `#F5A623`.
- **Conflict_Color**: The high-risk / conflict red `#ED1C24`.
- **Parchment**: The document excerpt background `#E8E4DA`.
- **Error_Red**: The standard UI error color `#EF4444`, distinct from AMD_Signal.
- **Syne**: The display typeface (700/800 weight) used for headlines, section titles, and stat numbers.
- **IBM_Plex_Sans**: The body typeface (400/500/600 weight) used for body copy and UI labels.
- **IBM_Plex_Mono**: The monospace typeface (400/500/600 weight) used for evidence quotes, filenames, and data values.

---

## Requirements

### Requirement 1: Design System Token Replacement

**User Story:** As a developer, I want all design tokens replaced with the new Design_System values, so that every component automatically inherits the new visual language without per-component overrides.

#### Acceptance Criteria

1. THE App SHALL define CSS custom properties for all Design_System tokens in `theme.css`, including: `--ink`, `--paper`, `--lead`, `--graphite`, `--rule`, `--ash`, `--ghost`, `--amd-signal`, `--volt`, `--volt-dim`, `--volt-border`, `--cleared`, `--caution`, `--conflict`, `--parchment`, `--stamp-green`, and `--error`.
2. THE App SHALL set `--ink: #0C0E14`, `--paper: #F2EFE8`, `--lead: #1A1D27`, `--graphite: #252836`, `--rule: #2A2D3E`, `--ash: #9297A8`, `--ghost: #4A4F63`, `--amd-signal: #ED1C24`, `--volt: #00D4FF`, `--volt-dim: rgba(0, 212, 255, 0.08)`, `--volt-border: rgba(0, 212, 255, 0.20)`, `--cleared: #00C48C`, `--caution: #F5A623`, `--conflict: #ED1C24`, `--parchment: #E8E4DA`, `--stamp-green: #1A4731`, and `--error: #EF4444` as their respective values.
3. THE App SHALL replace the legacy `--accent-blue: #3B7BF6` token with `--volt: #00D4FF` as the primary accent throughout the token sheet.
4. THE App SHALL replace the legacy `--bg-primary: #080D1A` token with `--ink: #0C0E14` as the primary background.
5. THE App SHALL replace the legacy `--bg-secondary: #0D1528` token with `--lead: #1A1D27` as the card background.
6. THE App SHALL load Google Fonts for Syne (weights 700, 800), IBM Plex Sans (weights 400, 500, 600), and IBM Plex Mono (weights 400, 500, 600) via the `fonts.css` or `index.html` file.
7. WHEN any component uses a color that was previously `#3B7BF6`, THE App SHALL render that element in `#00D4FF` (Volt) after the redesign.
8. THE App SHALL define card border-radius as 6px, button border-radius as 8px, badge border-radius as 4px, and file-type pill border-radius as 100px in the Design_System token sheet.
9. THE App SHALL use an 8px base grid for all spacing decisions throughout the redesign.

---

### Requirement 2: Typography System Replacement

**User Story:** As a designer, I want the typographic system replaced with Syne + IBM Plex Sans + IBM Plex Mono, so that the product has a distinct editorial voice that feels like a document intelligence tool rather than a generic SaaS chatbot.

#### Acceptance Criteria

1. THE App SHALL use Syne 700 or 800 for all display headlines, section titles, stat numbers, card titles, and the NavigationBar logo wordmark.
2. THE App SHALL use IBM Plex Sans 400 for body copy and paragraph text.
3. THE App SHALL use IBM Plex Sans 500 for UI labels, nav links, and button text.
4. THE App SHALL use IBM Plex Sans 600 for section labels, caps-style labels, and emphasis text.
5. THE App SHALL use IBM Plex Mono 400 for evidence quotes and document excerpts.
6. THE App SHALL use IBM Plex Mono 500 or 600 for filenames, data values, timestamps, and stat readouts.
7. WHEN any component previously referenced `DM Sans`, THE App SHALL replace that reference with `Syne`.
8. WHEN any component previously referenced `Inter`, THE App SHALL replace that reference with `IBM Plex Sans`.
9. WHEN any component previously referenced `JetBrains Mono`, THE App SHALL replace that reference with `IBM Plex Mono`.

---

### Requirement 3: NavigationBar Redesign

**User Story:** As a user, I want a sticky navigation bar with the new Clausify brand mark and design tokens, so that I always have orientation and access to key navigation actions.

#### Acceptance Criteria

1. THE NavigationBar SHALL render a sticky top bar with background `rgba(12, 14, 20, 0.95)` and a 1px bottom border in `--rule`.
2. THE NavigationBar SHALL display a logo mark consisting of a cyan square (14px, background `--volt`) rotated 45 degrees, the text "Clausify" in Syne 700, and the text "AI" in Syne 700 colored `--volt`.
3. THE NavigationBar SHALL display an AMD_Badge using `--amd-signal` (#ED1C24) for the icon and text color.
4. THE NavigationBar SHALL use IBM Plex Sans 500 for all nav link text.
5. WHEN rendered on a viewport width of 375px, THE NavigationBar SHALL collapse nav links and display only the logo and AMD_Badge.

---

### Requirement 4: Landing Page — Hero Section

**User Story:** As a prospective user, I want an editorially bold landing page with a left-aligned hero on desktop, so that the product feels distinctive and authoritative rather than generic SaaS.

#### Acceptance Criteria

1. THE Landing_Page SHALL render the headline "Every contract tells a story. We read them all at once." using Syne 700 at `clamp(32px, 5.5vw, 60px)`.
2. THE Landing_Page SHALL render the words "at once" with a cyan underline decoration in `--volt`.
3. WHILE the viewport width is greater than or equal to 768px, THE Landing_Page SHALL left-align the hero section text and upload zone, not center them.
4. WHILE the viewport width is less than 768px, THE Landing_Page SHALL center-align the hero section and display "Tap to select" instead of drag-and-drop instructional text in the upload zone.
5. THE Landing_Page SHALL display a stats row containing the values "< 60s", "5.6×", and "100%", where "5.6×" is rendered in `--volt`.
6. THE Landing_Page SHALL display a "How it works" section with 3 steps connected by step-connector lines.
7. THE Landing_Page SHALL display an AMD Hackathon event badge as a pill using `--volt-dim` background and `--volt-border` border.

---

### Requirement 5: Document Stack Animation

**User Story:** As a user, I want uploaded files to animate in as stacked physical paper cards, so that the product reinforces its document-intelligence identity and provides satisfying visual feedback on file selection.

#### Acceptance Criteria

1. WHEN a user selects or drops files onto the Landing_Page upload zone, THE App SHALL render each file as a PaperCard in a DocumentStack.
2. THE App SHALL install and use framer-motion for the DocumentStack spring physics animation.
3. THE DocumentStack SHALL render each PaperCard with background `--paper` (#F2EFE8), a slight random rotation between -4° and +4°, and a drop shadow to suggest physical depth.
4. THE PaperCard SHALL display a file-type stamp badge ("PDF" or "IMG") using IBM Plex Mono, the filename in IBM Plex Sans, and the file size in IBM Plex Mono.
5. THE DocumentStack SHALL use framer-motion spring physics (stiffness and damping) for card entry and removal animations.
6. WHEN a file is removed from the stack, THE App SHALL animate the corresponding PaperCard out with a spring exit transition.

---

### Requirement 6: Landing Page — Processing View

**User Story:** As a user, I want to see an AMD MI300X processing view that replaces the upload zone during analysis, so that I understand what is happening and feel confident in the platform's capabilities.

#### Acceptance Criteria

1. WHEN the App begins uploading and analyzing documents, THE Landing_Page SHALL replace the DocumentStack with a processing view showing AMD MI300X stage labels and a progress bar.
2. THE processing view SHALL use `--volt` for the progress bar fill and spinning loader icon.
3. THE processing view SHALL display at least three named stages: "Extracting text", "AMD embeddings", and "Running analysis".
4. WHEN a stage completes, THE processing view SHALL mark that stage with a completion indicator colored `--cleared`.
5. THE processing view progress bar shimmer animation SHALL use `--volt` and a lighter cyan tint, replacing the legacy blue shimmer.

---

### Requirement 7: Dashboard Page — Layout and Sidebar

**User Story:** As a user, I want a two-column dashboard with a document sidebar and analysis cards, so that I can review results at a glance while maintaining document context.

#### Acceptance Criteria

1. THE Dashboard_Page SHALL render a 260px fixed-width sidebar on the left for viewports ≥ 768px.
2. THE sidebar SHALL list all session documents with file-type stamp badges ("PDF" colored `--conflict` / "IMG" colored `--volt`), filename in IBM Plex Sans, and status in IBM Plex Mono.
3. THE sidebar SHALL render "Upload More" and "New Session" action controls at its bottom.
4. THE sidebar SHALL display the AMD_Badge at its bottom.
5. WHEN the viewport width is less than 768px, THE Dashboard_Page SHALL hide the sidebar and provide a toggle button that opens the sidebar as a slide-in drawer.
6. THE Dashboard_Page main content area SHALL render an AnalysisCardGrid containing: Executive Summary, Risk Analysis, Comparison Matrix, and Recommendation cards.

---

### Requirement 8: Dashboard Page — Conflict Alert

**User Story:** As a procurement professional, I want detected conflicts presented with a physical REDLINE stamp aesthetic, so that critical contract discrepancies immediately demand my attention.

#### Acceptance Criteria

1. WHEN `analysis.conflicts` contains one or more items, THE Dashboard_Page SHALL render a ConflictAlert banner above the AnalysisCardGrid.
2. THE ConflictAlert SHALL have a 4px left border colored `--amd-signal` (#ED1C24) and a paper-tinted background using `rgba(237, 28, 36, 0.06)`.
3. THE ConflictAlert SHALL render each conflicting document excerpt in an EvidenceBox with background `--paper` (#F2EFE8) and dark text, not white text on dark background.
4. THE ConflictAlert SHALL display a "REDLINE" or conflict-type label in IBM Plex Sans 600 uppercase using `--amd-signal`.
5. THE ConflictAlert SHALL be expandable and collapsed by default, with a toggle control.

---

### Requirement 9: Dashboard Page — Analysis Cards

**User Story:** As a user, I want the four analysis cards redesigned with the new Design_System tokens, so that results are readable and visually cohesive with the new brand.

#### Acceptance Criteria

1. THE AnalysisCardGrid SHALL render cards with background `--lead` (#1A1D27), border `--rule` (#2A2D3E), and border-radius 6px.
2. THE Executive_Summary card SHALL display card title in Syne 700 and body copy in IBM Plex Sans 400 colored `--ash`.
3. THE Risk_Analysis card SHALL render HIGH risk badges with background `rgba(237, 28, 36, 0.12)` and text `--amd-signal`, MEDIUM badges with `--caution`, and LOW badges with `--cleared`.
4. THE Comparison_Matrix card SHALL render alternating table rows using `--lead` and `rgba(37, 40, 54, 0.5)` (Graphite tint) to distinguish rows.
5. THE Recommendation card SHALL render with a `--volt-dim` background tint and `--volt-border` border to distinguish it as the primary action card.
6. THE Recommendation card confidence bar SHALL fill with a gradient from `--cleared` to a lighter green tint for high confidence (≥ 0.7), `--caution` for medium (0.4–0.69), and `--error` for low (< 0.4).
7. THE AMD_Performance_Banner above the grid SHALL use `--amd-signal` for the Cpu icon and AMD label, with stat values in IBM Plex Mono 700.

---

### Requirement 10: Chat Page — Layout and Header

**User Story:** As a user, I want the Decision Copilot chat interface redesigned with the new tokens and a document-icon avatar instead of a hexagonal AI avatar, so that the interface reinforces the "analyst, not chatbot" identity.

#### Acceptance Criteria

1. THE Chat_Page SHALL render a 280px left panel on viewports ≥ 768px, listing document pills and quick question chips.
2. THE Chat_Page header SHALL display a document-icon avatar with a cyan pulse ring (border animation using `--volt`), replacing the hexagonal AI avatar.
3. THE Chat_Page header avatar SHALL NOT render a circle avatar or simple round avatar — it SHALL use a document/file icon shape with the cyan pulse ring.
4. THE quick question chips in the left panel SHALL render in IBM Plex Sans with `--lead` background and `--rule` border, with hover state using `--volt-border`.
5. WHEN the viewport is less than 768px, THE Chat_Page SHALL provide a toggle to open the document panel as a drawer, with quick question chips scrollable horizontally.

---

### Requirement 11: Chat Page — AI Message Format

**User Story:** As a user, I want AI messages rendered in a structured four-section format with paper-colored evidence boxes, so that I can immediately orient to the answer, evidence, risk, and recommendation.

#### Acceptance Criteria

1. THE AI message bubble SHALL have a 3px left border colored `--volt` and background `--lead`.
2. THE AI message bubble SHALL render four labeled sections in order: ANSWER, EVIDENCE, RISK, RECOMMENDATION, using IBM Plex Sans 600 uppercase labels colored `--ghost`.
3. THE EVIDENCE section SHALL render each evidence quote in an EvidenceBox with background `--parchment` (#E8E4DA) and text in IBM Plex Mono 400 colored `#1A1D27` (dark text on paper, not light text on dark).
4. THE RISK section SHALL render risk text in `--caution` with an AlertTriangle icon for medium risk, and in `--conflict` for high risk.
5. THE RECOMMENDATION section SHALL render recommendation text in `--cleared` with an arrow icon.
6. THE user message bubble SHALL render with background `--graphite` (#252836).
7. WHEN streaming is active, THE Chat_Page SHALL display the StreamingCursor as a 2px wide blinking vertical bar in `--volt`.

---

### Requirement 12: Chat Page — Thinking Animation

**User Story:** As a user, I want to see a sequential cyan dot animation while the AI is processing, so that I have clear feedback that the system is working.

#### Acceptance Criteria

1. WHEN `isThinking` is true, THE Chat_Page SHALL render the ThinkingAnimation consisting of three dots in sequence.
2. THE ThinkingAnimation dots SHALL be colored `--volt` (#00D4FF).
3. THE ThinkingAnimation dots SHALL animate with a sequential staggered opacity/scale pulse, where each dot's animation is offset by 0.2s from the previous.
4. THE ThinkingAnimation dots SHALL have a subtle glow effect using `--volt-dim` as a box shadow.

---

### Requirement 13: Chat Page — Input Bar

**User Story:** As a user, I want the chat input bar to clearly indicate readiness to submit, with a cyan send button that activates only when there is text.

#### Acceptance Criteria

1. THE Chat_Page input bar SHALL render with background `--lead` (#1A1D27) and border `--rule`, with a focus state that changes the border to `--volt-border`.
2. THE Chat_Page input bar SHALL display a Paperclip icon on the left in `--ghost` color.
3. WHEN `inputValue.trim()` is empty or the chat is processing, THE send button SHALL render with background `--graphite` and opacity 0.5.
4. WHEN `inputValue.trim()` is non-empty and the chat is not processing, THE send button SHALL render with background `--volt` (#00D4FF) and full opacity.
5. THE input placeholder text SHALL be colored `--ghost`.

---

### Requirement 14: Demo Page — Layout and Banner

**User Story:** As a prospective user exploring the demo, I want the Demo page to use the same redesigned Dashboard layout with a prominent amber demo banner, so that the demo experience showcases the redesigned product.

#### Acceptance Criteria

1. THE Demo_Page SHALL render a demo banner with background `rgba(245, 166, 35, 0.08)` (Caution tint) and a 1px bottom border in `rgba(245, 166, 35, 0.25)`.
2. THE Demo_Page demo banner SHALL display a Target icon and label text in `--caution` (#F5A623).
3. THE Demo_Page SHALL use the same sidebar, AnalysisCardGrid, and ConflictAlert layout as the Dashboard_Page, populated with pre-loaded demo data from `getDemoData()`.
4. THE Demo_Page SHALL render a chat preview section at the bottom showing pre-seeded messages, followed by CTA buttons to upload documents or try the full chat.
5. THE Demo_Page chat preview AI messages SHALL use the same EvidenceBox with `--parchment` background as the Chat_Page.

---

### Requirement 15: Color Constraint — AMD Signal Reserved Usage

**User Story:** As a designer, I want the AMD red (#ED1C24) strictly reserved for AMD badges, conflict alerts, and critical/HIGH risks, so that its presence always signals something important and never dilutes through general UI use.

#### Acceptance Criteria

1. THE App SHALL only use `--amd-signal` (#ED1C24) for: AMD_Badge components, ConflictAlert borders and labels, HIGH risk badge backgrounds and text, and critical alert icons.
2. THE App SHALL use `--error` (#EF4444) — not `--amd-signal` — for standard UI error states such as form validation errors, upload errors, and general error messages.
3. WHEN a risk is HIGH level, THE Risk_Analysis card SHALL use `--amd-signal` (#ED1C24) for the badge background tint and label text.
4. WHEN a risk is MEDIUM level, THE Risk_Analysis card SHALL use `--caution` (#F5A623) for the badge.
5. WHEN a risk is LOW level, THE Risk_Analysis card SHALL use `--cleared` (#00C48C) for the badge.

---

### Requirement 16: API Integration Preservation

**User Story:** As a product owner, I want all existing API integrations to remain fully functional after the UI redesign, so that the redesign ships without any regression in backend connectivity.

#### Acceptance Criteria

1. THE App SHALL call `uploadDocuments()` via `POST /api/upload` with a multipart form-data body and handle the `UploadResponse` type without modification.
2. THE App SHALL call `analyzeDocuments()` via `POST /api/analyze` with a JSON body containing `sessionId` and handle the `AnalyzeResponse` type without modification.
3. THE App SHALL call `streamChatMessage()` via `POST /api/chat/stream` using SSE, invoking `onToken`, `onDone`, and `onError` callbacks with the same signatures as before.
4. THE App SHALL call `exportReport()` via `POST /api/report` and trigger a file download of the returned Blob.
5. THE App SHALL call `getDemoData()` via `GET /api/demo` and populate the Demo_Page with the returned `DemoResponse`.
6. THE App SHALL call `getSuggestedQuestions()` via `POST /api/suggest-questions` and populate the Chat_Page quick questions panel.
7. IF any API call returns a non-2xx status, THEN THE App SHALL display a toast notification with the error message using `sonner`.
8. THE App SHALL preserve all existing TypeScript types in `src/lib/types.ts` without modification: `UploadedDocument`, `UploadResponse`, `Risk`, `Conflict`, `ComparisonRow`, `Recommendation`, `Analysis`, `AnalyzeResponse`, `Evidence`, `StructuredAIResponse`, `ChatResponse`, `PreSeededMessage`, and `DemoResponse`.

---

### Requirement 17: Framer Motion Dependency

**User Story:** As a developer, I want framer-motion installed as a project dependency, so that the DocumentStack animation and any other motion primitives can be used reliably.

#### Acceptance Criteria

1. THE App SHALL list `framer-motion` as a dependency in `frontend/package.json` with a pinned or caret-pinned version.
2. WHEN framer-motion is imported in any component, THE App SHALL compile without TypeScript errors.
3. THE DocumentStack component SHALL use `motion.div` from framer-motion with a `spring` transition type for card entry and exit animations.

---

### Requirement 18: Mobile Responsiveness

**User Story:** As a mobile user accessing the platform at 375px viewport width, I want all four pages to remain fully usable, so that I can upload, review analysis, and chat on any device.

#### Acceptance Criteria

1. WHILE the viewport width is less than 768px, THE Landing_Page SHALL display the upload zone with "Tap to select" text and a single-column layout.
2. WHILE the viewport width is less than 768px, THE Dashboard_Page SHALL hide the sidebar and present a toggle button in the breadcrumb row to open it as a bottom sheet or drawer.
3. WHILE the viewport width is less than 768px, THE Chat_Page SHALL occupy the full screen height with the input bar fixed at the bottom and quick question chips scrollable horizontally above the input bar.
4. WHILE the viewport width is less than 768px, THE Demo_Page SHALL collapse into a single-column layout with the document sidebar accessible via a drawer toggle.
5. THE App SHALL use `clamp()` or responsive breakpoint classes for all headline font sizes across all four pages.
