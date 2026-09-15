# Milestone 2 — Home Overview & Report Structure Spec

**Purpose:** Implementer-facing checklist for the post-approval UX shown in the MyFace reference video. This does **not** replace [`milestone2_requirements.md`](./milestone2_requirements.md) — it organizes that document’s §2.1 / §2.2 / §3 into a build order for **Home Overview** + **Interactive Report** + **PDF**, and records FaceIQ routing decisions made 2026-09-14.

**Source video:** `C:\Users\ShrutiKamani\Downloads\MyFace - Complete User Flow after report approval.mp4`  
**Source PDF:** `C:\Users\ShrutiKamani\Downloads\MyFace-Protocol-test-1 (3).pdf`  
**Governing SoT:** [`client_requirements.md`](./client_requirements.md) · detail inventory: [`milestone2_requirements.md`](./milestone2_requirements.md)

**Branding:** FaceIQ only. Never copy MyFace name, logo, or verbatim microcopy. Structure and behavior match the reference; visual tokens stay Meridian / FaceIQ (`docs/report_design_spec.md`).

**Version:** 1.0 (2026-09-14)

---

## 0. Information architecture (FaceIQ decision)

| Surface | Role | Route (FaceIQ) | Nav label |
|---|---|---|---|
| **Home Overview** | Post-analysis landing — score, before/potential, priorities, protocol, harmony | **`/` protected home → implement as `/home`** (see §0.1) | Logo click; *not* a “Dashboard” label |
| **Interactive Report** | Left TOC + content panes (intro, assessments, features, protocol) | `/report` | **Report** |
| **AI Visuals** | Hairstyle / Outfit / Aging | `/ai-visuals` | **AI Visuals** |
| **Chat Assistant** | Report-grounded chat | `/chat` | **Chat Assistant** |
| **Settings** | Account / Password / Billing | `/settings` | User menu only |

Persistent header (all post-approval pages): **Logo · Report · AI Visuals · Chat Assistant · PDF (where applicable) · EN (display-only until i18n) · profile pill**. Active item = light brand-tint pill + icon. See screenshots supplied with the video walkthrough.

### 0.1 Routing decision (2026-09-14) — gap to close

- User direction: **do not keep a FaceIQ “Welcome back” dashboard** (summary cards for AI Visuals/Chat). Match the **video’s first post-approval screen** (overview).
- Current code (interim): post-completion landing is `/report`; `/dashboard` hard-redirects to `/report`. That **drops** the Home Overview (§1) as a first screen.
- **Required implementation:** restore Home Overview as the post-completion landing:
  - Preferred route name: **`/home`** (or keep `/dashboard` as route path but **only** render overview content — never the old Welcome UI).
  - `getNextOnboardingStep` after `analysisStatus === "completed"` → **Home Overview route**, not `/report`.
  - Logo → Home Overview.
  - Nav **Report** → `/report` (TOC experience).
  - Legacy `/dashboard` → redirect to Home Overview (not `/report`).

---

## 1. Home Overview — required blocks (video §2.1)

Build as **one scrollable page**. Use real report/analysis data already in `GET /reports/{id}` / assembly (`overall_score`, `feature_scores`, `harmony_chart`, recommendations, facial assessments). Do not invent scores.

### 1.1 Header / actions
- Breadcrumb-style meta: protocol / user display name / date **[Recommendation — layout only]**
- **Download PDF** (primary or outline) — uses existing `GET /reports/{id}/pdf`
- **Share** — if not implemented, omit or disable with no fake behavior **[Assumption: Share not in FaceIQ scope yet; do not ship a dead button]**

### 1.2 Stat row (3 cards)
| Card | Data source |
|---|---|
| **Overall Score** | `sections.overall_score` (e.g. `78 / 100`) |
| **Evaluated** | Count of measured points / metrics already exposed (e.g. `468+ points`) — use existing `evaluatedPointsCount` / equivalent; do not hardcode |
| **Analysis Time** | Derive from analysis timestamps (or report `created_at` delta); never invent “1 day” |

### 1.3 Protocol entry card
- Title like “Protocol #…” / “New protocol” (FaceIQ wording, not MyFace)
- CTA: **View Full Report** → `/report`

### 1.4 Before / Potential pair
- **Before:** user’s validated **front** photo
- **Potential:** whole-face AI “potential” projection  
  - **Status:** reference shows this; FaceIQ today only generates **per-feature** crops (`FR-022`), not a whole-face potential.  
  - **[Decided for implementation]:** if no whole-face asset exists yet, show Before + an honest empty/generating state for Potential — **do not** fake with an unrelated feature crop. Flag whole-face potential as a follow-up (same gap already noted in `milestone2_phase_plan.md` Phase 10).

### 1.5 Priority Features to Improve
Scrollable stack of feature score cards (lowest / priority first). Each card:
- Feature name + score `/100` + short label (e.g. Balanced / Defined)
- Optional 1–3 sub-metrics when available from measurements  
Confirmed reference examples: Nose, Jaw, Neck, Chin, Ears — **use whatever the user’s real lowest scores are**, not a fixed list.

### 1.6 Facial Age
Slider or labeled indicator for facial age if/when backend exposes it.  
**[Gap]:** not confirmed as a first-class FaceIQ API field yet — show only if data exists; otherwise omit (do not hardcode age 28 from the reference demo).

### 1.7 Treatment Protocol panel
Phases **01 / 02 / 03** (or however many tiers we have) with:
- Phase title (e.g. foundation / topicals)
- Duration line when available
- Bullet recommendations from `sections.recommendations` (`at_home` / `otc_skincare` / `in_clinic` — map into phases without inventing clinical claims)

### 1.8 Harmony Profile & Overview (below fold)
- Radar / spider chart — **six axes:** Harmony, Symmetry, Smoothness, Jawline, Skin, Volume (`sections.harmony_chart`)
- Short **Overview** narrative paragraph (from report intro / closing synthesis — reuse existing copy fields, do not invent)
- **Feature Evaluation** table: Zone | Finding | Reference (derive from feature scores + summary callouts)

---

## 2. Interactive Report (`/report`) — TOC & content (video §2.2)

Left TOC drives the main pane. Groups and required content:

### 2.1 Introduction
| Item | Content |
|---|---|
| Introduction | Cephalometric / measurement framing, how to read the report |
| Disclaimer | Informational-only, no medical advice (`FR-004` / existing limitations copy) |

Also surface (or link) **Understanding Your Results** principles if not a separate TOC item — PDF has a dedicated page; interactive report may fold into Introduction.

### 2.2 Facial Assessments (`FR-018`)
| Assessment | Required UI |
|---|---|
| **Dimorphism** | Overview: title, score `/100`, label, Hyper Feminine ↔ Hyper Masculine slider, top drivers explanation; then **per-feature** grid (slider + score + citation) |
| **Prototypicality** | Score, label, Distinctive ↔ Highly Typical slider, shape-analysis wireframe |
| **Proportions** | Score, label, Facial Thirds on photo (Lower / Middle / Upper + ratios) |
| **Symmetry** | Annotated photo (axis + landmarks), score, classification, Asymmetric ↔ Symmetric slider, Regional Balance bars |
| **Face Shape** | **Not shown in video** — build as single-overview page like Prototypicality/Symmetry; flag as unverified vs reference |

### 2.3 Features Analysis (`FR-018` + `FR-022`)
**FaceIQ feature set stays at 11** (`BR-008` + `BR-011`): Hair, Eyebrows, Eyes, Nose, Cheeks, Jaw, Lips *(Smile folds into Lips)*, Chin, Skin, Neck, Ears.  
Do **not** add Smile as a 12th nav item.

**Each feature page pattern:**
1. Feature crop / hero image  
2. “Summary of your {feature}” + one-line description  
3. 2×2 metric cards (named attributes)  
4. Larger detail card (named ratio + value + min/max slider)  
5. Optional “All metrics” table  
6. **BEFORE / AFTER** image slot (`FR-022`) — use generated feature visual when `visual_status === generated`

### 2.4 Protocol (report TOC)
Present treatment phases consistent with Home Overview §1.7.  
**Not opened in the video** — reuse Dashboard/Home protocol content; do not claim pixel-perfect match to an unseen Report Protocol screen.

---

## 3. PDF export structure (reference PDF §3)

Keep FaceIQ’s existing 11-feature PDF contract (`FR-013`). Required sections:

1. Cover / overview (score, evaluated, analysis time, priorities, before/potential if available, facial age if available, harmony radar, overview text, feature table, protocol phases)  
2. Disclaimer / privacy framing  
3. Introduction + TOC  
4. Understanding the Results  
5. Protocol overview (“organised around 11 key features”)  
6. **One page per feature** (11) — narrative recommendations, BEFORE/AFTER, tier label, feature summary  
7. Closing recommendations  

No Smile page in PDF.

---

## 4. What already exists vs what to implement

| Area | Backend / data | UI vs video |
|---|---|---|
| Facial assessments + scores + harmony | Mostly done (Phase 10) | Report TOC exists; polish to match §2 |
| Per-feature BEFORE/AFTER | Phase 10 / `FR-022` | Ensure every feature page shows slot + states |
| Home Overview (§1) | Data largely available | **Missing as first landing** — primary build target |
| Whole-face Potential image | Not generated today | Empty/honest state until scoped |
| Facial Age figure | Unclear / missing field | Omit until data exists |
| Workspace navbar | Partial (AppNavbar) | Align active states, PDF on overview+report |
| AI Visuals / Chat | Phase 11–12 | Out of scope for this home/report pass except nav links |

---

## 5. Acceptance checklist (Home + Report)

- [ ] After analysis completes, user lands on **Home Overview**, not Welcome dashboard and not straight into a random TOC section.  
- [ ] Logo → Home Overview; **Report** nav → `/report`.  
- [ ] Overview shows real Overall Score, Evaluated, Analysis Time, Priority Features, Protocol, Harmony (6 axes).  
- [ ] View Full Report / Report nav opens TOC report with Introduction, 5 Facial Assessments, 11 Features (+ before/after), Protocol.  
- [ ] No MyFace branding; no invented scores; no Smile as 12th feature.  
- [ ] PDF still downloads and includes 11 features + disclaimer.  
- [ ] Toast / ConfirmDialog conventions (`BR-009` / `BR-010`) preserved.

---

## 6. Related docs

- [`milestone2_requirements.md`](./milestone2_requirements.md) — full video/PDF inventory + `FR-018`–`FR-022`  
- [`milestone2_phase_plan.md`](./milestone2_phase_plan.md) — Phases 10–13  
- [`report_design_spec.md`](./report_design_spec.md) / [`report_template.md`](./report_template.md) — Meridian tokens & PDF rules  
- [`ui-ux-design.md`](./ui-ux-design.md) §3.7 — screen notes (updated for Home Overview)
