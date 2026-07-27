---
inclusion: manual
---

> **RESOLVED — HISTORICAL DOCUMENT.** This analysis led to the decision to pivot into **GreenLens**. "Clausify" below refers to the original enterprise procurement tool this project started as, before the rebrand. The project is now fully GreenLens — see `.kiro/steering/greenlens-master-plan.md` for the current plan. This document is kept as a historical record of the reasoning, not as a description of the current product.

# YFS Build for Good Hackathon — Original Feasibility Analysis (Clausify → GreenLens)

## Hackathon Overview

**Name:** YFS Build for Good — Global AI Hackathon 2026
**Organizer:** Young Founders School (YFS)
**Age Group:** 14–18 years old
**Countries:** Philippines, Singapore, Indonesia, China, Nigeria, India
**Prize:** Top 3 teams fly to Singapore for the YFS Gala 2026

## Innovation Tracks (pick ONE)

1. **AI for Sustainability** — climate, circular economies, environment
2. **AI for Education** — tutor bots, accessibility, skill-building for underserved learners
3. **AI for Inclusion** — accessibility, language, economic participation, mental health

## Judging Rubric (from screenshots — "Build_for_Good - Heera - Judge Sheet")

Each criterion scored 1–10, with weights:

### PROBLEM & IMPACT (30% total)
| # | Criterion | Weight | What judges look for |
|---|-----------|--------|---------------------|
| 1 | Problem Clarity | 10% | Identifies a real, specific challenge in the community or globally |
| 2 | Impact Potential | 10% | Solution could meaningfully improve lives at scale; clear beneficiaries, credible scale, tangible outcomes |
| 3 | Sustainable & Business Model | 10% | Has a viable path to long-term sustainability; plausible revenue or funding model with at least one monetization avenue |

### AI INNOVATION (20% total)
| # | Criterion | Weight | What judges look for |
|---|-----------|--------|---------------------|
| 4 | AI Application | 10% | Thoughtful, appropriate use of AI to address the problem; AI is central to the solution with clear justification |
| 5 | Technical Feasibility | 10% | Prototype or concept is technically sound and buildable; functional prototype demonstrated with clear technical architecture |

### SOLUTION DESIGN (20% total)
| # | Criterion | Weight | What judges look for |
|---|-----------|--------|---------------------|
| 6 | Originality & Creativity | 10% | Unique approach that goes beyond obvious or existing solutions; distinctive angle or combination of ideas |
| 7 | User-Centred Design | 10% | Solution is designed with end-users' needs and context in mind; clear user personas, needs identified, iterative testing |

### BUSINESS & VIABILITY (20% total)
| # | Criterion | Weight | What judges look for |
|---|-----------|--------|---------------------|
| 8 | Go-to-Market Strategy | 10% | Credible plan for reaching users and delivering the solution; defined channels, partnerships, and early adoption plan |
| 9 | Sustainability & Business Model | 10% | Has a viable path to long-term sustainability; well-reasoned model with diversified revenue streams and growth projections |

### PITCH QUALITY (10% total)
| # | Criterion | Weight | What judges look for |
|---|-----------|--------|---------------------|
| 10 | Presentation & Communication | 5% | Clear, confident, and engaging delivery; compelling storytelling, debates, all team members contribute effectively |
| 11 | Q&A Responsiveness | 5% | Team demonstrates deep understanding when questioned; handles tough questions confidently and adapts ideas constructively |

### Grade Bands
- 9.0–10.0 = Outstanding (Grand Finale contender)
- 7.5–8.9 = Excellent (Strong advancement candidate)
- 6.0–7.4 = Proficient (Solid, may advance with top scores in category)
- 4.0–5.9 = Developing (Shows promise, recommend coaching)
- Below 4.0 = Needs Work

## Process
1. Student completes Speedrunning course
2. Student builds the project and/or joins a YFS workshop
3. Student records a Loom video (submission explaining solution)
4. Student submits registration form
5. YFS reviews & shortlists top 5 per country → advance to mentorship

---

## CAN CLAUSIFY BE USED? — ANALYSIS

### Current State of Clausify
- **What it does:** AI document intelligence for enterprise procurement — upload contracts/invoices, detect billing conflicts, risk analysis, comparison matrix, chat copilot, PDF export
- **Tech:** FastAPI + React + Fireworks AI (AMD MI300X) + ChromaDB + RAG pipeline
- **Built for:** AMD Developer Hackathon (lablab.ai) — enterprise B2B focus
- **Live:** Yes, deployed on Railway + Vercel

### Fit Assessment Against YFS Criteria

#### ❌ PROBLEM (Score risk: 4–5/10)
- **Current problem:** Enterprise procurement teams missing billing discrepancies
- **YFS requirement:** Problem affecting COMMUNITY or GLOBAL GOOD (sustainability, education, inclusion)
- **Gap:** Clausify solves a corporate/enterprise problem, not a social impact problem. Judges want to see impact on underserved communities, students, environment, or marginalized groups.

#### ✅ AI APPLICATION (Score potential: 8–9/10)
- RAG pipeline, parallel LLM calls, conflict detection, chat copilot — strong AI usage
- AI is clearly central to the solution, not a gimmick

#### ✅ TECHNICAL FEASIBILITY (Score potential: 8–9/10)
- Working prototype live on the internet
- Clear architecture, well-documented

#### ⚠️ ORIGINALITY (Score risk: 5–6/10)
- Document analysis tools exist (ChatPDF, etc.)
- The cross-document conflict detection angle is unique, but the enterprise framing reduces "wow factor" for social impact judges

#### ❌ USER-CENTRED DESIGN (Score risk: 4–5/10)
- Designed for procurement professionals, not for the target users YFS cares about (students, underserved communities, environment)

#### ❌ GO-TO-MARKET (Score risk: 3–4/10)
- No plan to reach underserved communities
- Enterprise SaaS doesn't align with social good distribution

#### ❌ SUSTAINABILITY MODEL for social impact (Score risk: 4/10)
- Revenue model is B2B SaaS — doesn't address social sustainability

---

## VERDICT: CAN WE USE CLAUSIFY AS-IS?

### 🔴 NO — Not in its current form.

Clausify is an **enterprise tool** built for the AMD hackathon. The YFS hackathon explicitly requires projects that serve **social good** in one of three tracks: Sustainability, Education, or Inclusion.

### 🟡 YES — IF we REPURPOSE/PIVOT the same tech stack.

The underlying technology (RAG pipeline, document analysis, conflict detection, AI chat) is EXCELLENT and can be repurposed. Here are pivot ideas:

---

## PIVOT OPTIONS (using the same codebase)

### Option A: "AI for Education" Track — CONTRACT LITERACY FOR STUDENTS
**Concept:** Help Filipino students/young workers understand employment contracts, rental agreements, and loan documents before signing them. Detect predatory clauses, unfair terms, and hidden fees.
- **Problem:** Many young workers (18–22) sign contracts they don't understand → labor exploitation, predatory lending
- **Impact:** Protects vulnerable first-time workers from unfair contracts
- **Reuse:** 90% of Clausify's backend (document upload, analysis, conflict detection, chat copilot)
- **Change:** Rebrand, new prompts focused on "is this contract fair?", target user = young worker not procurement team

### Option B: "AI for Inclusion" Track — LEGAL DOCUMENT ACCESSIBILITY
**Concept:** Make legal/government documents accessible to people with low literacy or non-English speakers. Upload any document → get plain-language summary in Filipino/local language.
- **Problem:** Government forms, contracts, legal notices are incomprehensible to many
- **Impact:** Economic inclusion, prevents exploitation of low-literacy populations
- **Reuse:** 80% of backend (upload, parsing, LLM analysis, chat)
- **Change:** Add translation, simplification prompts, mobile-first redesign

### Option C: "AI for Sustainability" Track — GREENWASHING DETECTOR
**Concept:** Upload corporate sustainability reports and ESG claims → AI detects inconsistencies, vague promises, and greenwashing between what companies say and what data shows.
- **Problem:** Companies make false environmental claims; consumers/investors can't verify
- **Impact:** Holds corporations accountable, enables informed environmental decisions
- **Reuse:** 85% of backend (conflict detection = greenwashing detection, document comparison)
- **Change:** Rebrand, sustainability-focused prompts, different sample documents

### Option D: "AI for Education" Track — SCHOLARSHIP/APPLICATION REVIEWER
**Concept:** Help Filipino students review and improve their scholarship applications, college essays, and grant proposals by comparing against successful templates.
- **Problem:** Students from underserved schools don't have mentors to review applications
- **Impact:** Levels the playing field for scholarship access
- **Reuse:** 70% of backend (document analysis, recommendations, chat copilot)
- **Change:** New prompts, comparison against templates not between user docs

---

## RECOMMENDED PIVOT: Option A (Contract Literacy)

**Why:** Closest to current Clausify functionality. Minimal code changes. Strong problem statement for Philippines context. Clear social impact. Easy to demo.

**Changes needed:**
1. Rebrand: "Clausify" → new name (e.g., "FairSign", "KontraCheck", "SafeContract")
2. New prompts: shift from "procurement analysis" to "is this contract fair for a young worker?"
3. New landing page copy: target young workers, not enterprise teams
4. Sample documents: employment contracts, rental agreements (not invoices)
5. New risk categories: "predatory clause", "missing rights", "unfair termination" instead of "billing discrepancy"
6. Add: plain-language explanation feature ("explain this clause like I'm 16")
7. Pitch framing: social impact story, not B2B SaaS

**Timeline:** 3–5 days to pivot with existing codebase.

---

## SUBMISSION REQUIREMENTS
- Loom video explaining the solution
- Registration form submission
- Project must fit one of the 3 tracks
- Deadline: Project submissions by June 30 (workshops April–June)
- Judging: June 15–30

## KEY DATES
- Workshops: April 1 – June 30
- Submission: April 1 – June 30
- Judging: June 15 – June 30
- Mentorship (if shortlisted): July 1 – August 15
- Grand Finale: September 5 (Singapore)
