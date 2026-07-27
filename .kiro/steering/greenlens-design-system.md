---
inclusion: manual
---

# GreenLens — Design System

> Reference with `#greenlens-design-system`. Builds on top of the base UI token *architecture* originally spec'd before the GreenLens rebrand (`.kiro/specs/greenlens-ui-redesign/design.md`) — same structure (ink/lead/graphite/rule/ash/ghost + accent + paper), just re-themed from the old cyan accent to green/sustainability, and re-purposed severity semantics. Typography stays Syne + IBM Plex Sans + IBM Plex Mono for consistency with work already done — only colors and copy change. This is the **current, authoritative** color spec for GreenLens.

## Why These Colors (Research-Backed)

- Dark mode remains the dominant pattern for tech/climate apps in 2025-2026 — reduces eye strain, saves battery, reads as "serious tool" not "consumer toy" ([source](https://beetroot.co/greentech/top-design-trends-shaping-green-tech-and-clean-energy-mobile-apps/)).
- Earthy/natural greens are trending through 2025-2026 as a direct response to sustainability-focused design demand ([source](https://themewagon.com/blog/emerging-web-design-trends-color-schemes/)).
- Emerald-family green (`#50C878` family) reads as growth, renewal, and credibility without tipping into neon-gimmick territory ([source](https://www.media.io/colors/emerald-color.html)).
- Reserve a single, vivid accent color and use it sparingly against a near-black base — the same "one strong signal color" principle the base architecture already uses with AMD red as its own reserved signal.

## Core Palette

| Token | Value | Role |
|---|---|---|
| `--ink` | `#0A120E` | Primary background — deep forest-black, not pure black |
| `--lead` | `#131F19` | Card/panel background |
| `--graphite` | `#1C2B23` | Elevated surface / hover state |
| `--rule` | `#24352C` | Borders, dividers |
| `--ash` | `#9BAFA3` | Secondary text (cool sage-grey) |
| `--ghost` | `#4E6157` | Tertiary text / placeholders |
| `--leaf` | `#3DDC84` | **Primary accent** — CTAs, links, focus states, active nav |
| `--leaf-dim` | `rgba(61, 220, 132, 0.08)` | Accent tints (badges, subtle backgrounds) |
| `--leaf-border` | `rgba(61, 220, 132, 0.22)` | Accent borders (focus rings, active chips) |
| `--paper` | `#F3F0E6` | Evidence boxes, document excerpt backgrounds (warm, matches the existing paper concept) |
| `--parchment` | `#E9E4D6` | Chat evidence quote backgrounds |

## Greenwash Severity Palette (replaces HIGH/MEDIUM/LOW risk semantics)

GreenLens keeps the same 3-tier `Risk.level` enum (`HIGH` / `MEDIUM` / `LOW`) at the data layer for zero backend model changes — only the **display label and color mapping** changes:

| Data-layer level | Display label | Color | Hex | Meaning |
|---|---|---|---|---|
| `HIGH` | **MISLEADING** | `--flag-red` | `#F04452` | Direct contradiction between claim and data |
| `MEDIUM` | **VAGUE** | `--flag-amber` | `#F0A937` | Claim has no measurable definition or proof |
| `LOW` | **UNVERIFIED** | `--flag-blue` | `#5FA8D3` | Claim is plausible but lacks third-party verification |

```css
--flag-red:   #F04452;
--flag-amber: #F0A937;
--flag-blue:  #5FA8D3;
--flag-red-dim:   rgba(240, 68, 82, 0.12);
--flag-amber-dim: rgba(240, 169, 55, 0.12);
--flag-blue-dim:  rgba(95, 168, 211, 0.12);
```

## Greenwash Score Gauge (new component — 0-100)

| Range | Band | Color |
|---|---|---|
| 0-30 | Mostly Greenwashing | `--flag-red` |
| 31-60 | Vague / Mixed Signals | `--flag-amber` |
| 61-100 | Credible | `--leaf` |

Gauge is a circular or horizontal bar; large numeral in Syne 800, band label in IBM Plex Sans 600 uppercase beneath it.

## AMD Branding (Kept)

The AMD MI300X performance badge and its reserved red (`#ED1C24`, keep as `--amd-signal`) are **preserved unchanged** — GreenLens still runs on Fireworks AI / AMD MI300X, and that's still a genuine technical differentiator worth keeping visible. It must not be confused with `--flag-red` (MISLEADING) — these are visually similar but semantically distinct, so the AMD badge always pairs with the ⚡ icon and "AMD MI300X" text to disambiguate, exactly like the existing `AMDBadge` component.

## Typography (Unchanged From Base Redesign)

- **Display**: Syne 700/800 — headlines, Greenwash Score numeral, section titles
- **Body**: IBM Plex Sans 400/500/600 — body copy, labels, UI text
- **Mono**: IBM Plex Mono 400/500/600 — evidence quotes, claim excerpts, data values, scores

Reuse the same Google Fonts `<link>` already added to `index.html` for the UI redesign spec — no new font loading needed if that spec has been implemented; otherwise add it as part of the GreenLens tasks.

## Shape & Spacing (Unchanged)

`--radius-card: 6px`, `--radius-btn: 8px`, `--radius-badge: 4px`, `--radius-pill: 100px`, 8px base spacing grid — same as the existing base tokens.

## Component Notes

### `GreenwashScoreGauge` (new component)
- Large numeral (Syne 800, 48-64px) + band label + thin circular/arc progress ring in the band color
- Placed prominently at the top of the Dashboard's `AnalysisCardGrid`, above the four cards

### `GreenwashFlagBadge` (renamed/recolored `RiskBadge`)
- Same component structure as the existing `RiskBadge`, remapped colors per the severity palette above
- Label text: "MISLEADING" / "VAGUE" / "UNVERIFIED" instead of "HIGH" / "MEDIUM" / "LOW"

### `ClaimVsRealityRow` (renamed `ComparisonRow` rendering)
- Two-column layout: "They Say" (marketing claim, `--paper` background) vs "Data Shows" (report/reality, `--parchment` background) — visually distinct from the old vendor-vs-vendor table since there are only ever 2 "columns" (claim vs. reality) instead of N suppliers

### `ContradictionAlert` (renamed `ConflictAlert`)
- Same 4px left-border-accent pattern as `ConflictAlert`, but border color is `--flag-red` instead of `--amd-signal`
- Header label: "CONTRADICTION DETECTED" instead of "CONFLICTS DETECTED"

### Chat — ELI15 Toggle (new)
- Small pill toggle in the chat header: "Expert" / "ELI15" — switches prompt instruction for response complexity
- Active state uses `--leaf-border` outline, same pattern as other active-state chips

### Chat — Snap & Check attach button (new)
- Paperclip icon in the input bar gains a sibling camera icon (`Camera` from lucide-react) — opens native camera on mobile via `<input type="file" accept="image/*" capture="environment">`
- Attached image renders as a small thumbnail chip above the input bar before sending, same visual language as file chips elsewhere in the app

## Color Migration Reference (from the original base tokens, if that redesign spec was applied first)

| Base token | GreenLens token | Old value | New value |
|---|---|---|---|
| `--volt` | `--leaf` | `#00D4FF` | `#3DDC84` |
| `--volt-dim` | `--leaf-dim` | `rgba(0,212,255,0.08)` | `rgba(61,220,132,0.08)` |
| `--volt-border` | `--leaf-border` | `rgba(0,212,255,0.20)` | `rgba(61,220,132,0.22)` |
| `--ink` | `--ink` | `#0C0E14` | `#0A120E` |
| `--lead` | `--lead` | `#1A1D27` | `#131F19` |
| `--graphite` | `--graphite` | `#252836` | `#1C2B23` |
| `--rule` | `--rule` | `#2A2D3E` | `#24352C` |
| `--ash` | `--ash` | `#9297A8` | `#9BAFA3` |
| `--ghost` | `--ghost` | `#4A4F63` | `#4E6157` |
| `--paper` | `--paper` | `#F2EFE8` | `#F3F0E6` |
| `--parchment` | `--parchment` | `#E8E4DA` | `#E9E4D6` |
| `--conflict` / `--amd-signal` (risk-only use) | `--flag-red` | `#ED1C24` | `#F04452` |
| `--caution` | `--flag-amber` | `#F5A623` | `#F0A937` |
| `--cleared` | `--flag-blue` (repurposed — see note) | `#00C48C` | `#5FA8D3` |

**Note on `--cleared`:** the original base tokens used green for "low risk / good." GreenLens can't reuse green for "low severity flag" because green is the *brand* accent (`--leaf`) — using it for the lowest severity flag would visually contradict "credible/good" being green elsewhere (the Score gauge). That's why LOW/UNVERIFIED maps to blue (`--flag-blue`) instead of green. Keep `--amd-signal` (`#ED1C24`) reserved exclusively for the AMD badge, per the original color-constraint rule — do not reuse it for `--flag-red`, which is a distinct, slightly different red (`#F04452`) precisely to avoid that collision.
