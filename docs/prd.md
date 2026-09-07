# Product Requirements Document (PRD)

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`FR-*`, `WF-001`, Section 2). Business rationale lives in [`docs/brd.md`](./brd.md) and is not repeated here. Technical realization lives in [`docs/architecture.md`](./architecture.md), [`docs/api-specification.md`](./api-specification.md), and [`docs/database-design.md`](./database-design.md).

**Status:** Draft, derived from `client_requirements.md` v1.1.

---

## 1. Product Summary

An AI-driven facial aesthetics analysis platform: a user answers a questionnaire, uploads photos, and receives an AI-generated, structured aesthetic report (11 features) after payment. See `docs/brd.md` §2 for why this exists.

## 2. User Roles

Only one functional role exists in Phase 1 (see `docs/brd.md` §4): **End User**. All requirements below describe End User–facing functionality unless noted.

## 3. Functional Requirements by Feature Area

Each area below corresponds to a module in [`docs/phase-wise-requirements.md`](./phase-wise-requirements.md) and a `plans.md` under `D:\zzz\`.

### 3.1 Landing Page
| ID | Requirement |
|---|---|
| FR-001 | Landing page with a clear call-to-action to begin onboarding (which starts with signup). |

### 3.2 Authentication
| ID | Requirement |
|---|---|
| FR-002 | User account creation and login. Full flow spec: [`docs/authentication.md`](./authentication.md). |

### 3.3 Onboarding Questionnaire
| ID | Requirement |
|---|---|
| FR-003 | 23-question branching questionnaire covering medical conditions/medications, self-perceived best feature, comfort with specific recommendation types (e.g. weight loss), frequency of appearance-related thoughts, and similar lifestyle/self-perception questions. |
| FR-004 | Questionnaire must end with a mandatory, checkbox-gated disclaimer (no BDD-related concerns; recommendations are informational only, not medical guidance). Submission is blocked without this checkbox (`BR-003`). |

The exact 23 questions and their branching logic are not enumerated in `client_requirements.md` beyond the categories above — **[Open Question]**: the literal question set/branching tree must be sourced from the client's Qoves onboarding reference material or confirmed with the client before this module's `plans.md` is finalized for implementation.

### 3.4 Photo Upload & Validation
| ID | Requirement |
|---|---|
| FR-005 | Multi-angle photo upload with a 7-point guideline checklist: remove glasses/hat; natural even lighting; plain white background; tie back long hair; remove makeup; avoid neck-covering clothing; no filters. |
| FR-006 | Validation must be enforced by the backend, not just displayed — see `BR-005`/`ASM-002` in `docs/brd.md` for the (deferred-threshold) mechanism. |

### 3.5 Facial Analysis Engine
| ID | Requirement |
|---|---|
| FR-007 | Facial landmark detection and mathematical measurement via MediaPipe + OpenCV, built new. |
| FR-008 | AI-generated narrative explanations and personalized recommendations via OpenAI (Vision/GPT), using **both** CV measurements and questionnaire answers as context. |

### 3.6 Report Generation
| ID | Requirement |
|---|---|
| FR-009 | Report covers exactly 11 features: Hair, Eyebrows, Eyes, Nose, Cheeks, Jaw, Lips, Chin, Skin, Neck, Ears. |
| FR-010 | Each feature section includes a narrative analysis, a before/after or "projected potential" framing, and a short summary callout. |
| FR-011 | The report as a whole includes an introduction, an "Understanding Your Results" preamble, an explicit limitations/disclaimer section, and a closing recommendations section synthesizing all findings. |
| FR-012 | Recommendations span at-home/lifestyle, OTC/skincare-active, and optional in-clinic tiers — always informational, never prescriptive, with "consult a qualified professional" language. |
| FR-013 | Report is exportable as a downloadable PDF, branded with the delivery team's own in-house design (no client branding assets exist yet — `CON-003`). |
| FR-014 | Report auto-publishes and is immediately available — no manual admin review/approval step in Phase 1 (`BR-002`). |

### 3.7 Payment
| ID | Requirement |
|---|---|
| FR-015 | Full report is inaccessible until a successful Stripe payment. A teaser/results page may be shown pre-payment. |
| FR-016 [Recommendation] | One-time payment per report (no subscription, no PayPal in Phase 1). Price point is explicitly open (`OQ-002`) — must be a configurable value. |

### 3.8 User Dashboard
| ID | Requirement |
|---|---|
| FR-017 | Dashboard showing report history/status, report download, payment history, and basic profile management. |

## 4. End-to-End Workflow (WF-001)

```
Landing Page
   │  (CTA → sign up)
   ▼
Authentication (signup or login; see docs/authentication.md)
   │
   ▼
Onboarding: 23-question branching questionnaire → disclaimer checkbox → submit
   │
   ▼
Photo Requirements screen (7-point checklist shown to user)
   │
   ▼
Photo upload (multi-angle) → backend validation → accept / reject with reason
   │
   ▼
AI processing: MediaPipe/OpenCV measurement → OpenAI narrative
   (uses measurements + questionnaire context together, FR-008)
   │
   ▼
Report assembled and auto-published (BR-002)
   │
   ▼
Results page: teaser shown, full report locked (BR-001)
   │
   ▼
Stripe payment → on success, full report unlocked
   │
   ▼
Dashboard: report history/status, PDF download, payment history, profile
```

## 5. Acceptance Criteria (product-level)

These are the product-level conditions that must hold; module-level acceptance criteria live in each module's `plans.md`.

- A user cannot reach the report/payment step without a disclaimer-accepted questionnaire submission (`BR-003`).
- A user cannot pass photo upload with photos that fail backend validation, and no AI processing runs on rejected photos (`BR-004`/`BR-005`).
- Every generated report contains all 11 features in `FR-009`, each with the three sub-elements in `FR-010`.
- A user cannot view the full report body before a successful Stripe payment is recorded (`BR-001`).
- The dashboard reflects report status and payment history accurately after each state transition in the workflow above.

## 6. Explicitly Out of Scope (Phase 1)

Restated from `docs/brd.md` §3.2 for product-scope clarity: admin panel, full report status workflow, email notifications, PayPal, Meta Pixel/GTM, AI Visual Features (hairstyle/outfit/aging), AI Beauty Assistant chat, formal data-retention policy.

## 7. Open Questions Affecting Product Scope

| ID | Question | Impact |
|---|---|---|
| OQ-002 | Report price | Payment UI/API must treat price as configurable, not hardcoded (see `docs/api-specification.md` §Payment). |
| — [new, raised here] | Literal 23-question set and branching tree | Needed before `onboarding-questionnaire` module implementation begins — see §3.3 above. Must be confirmed against the client's Qoves reference material before `D:\zzz\onboarding-questionnaire\plans.md` implementation steps are finalized. |

## 8. Related Documents

- [`docs/brd.md`](./brd.md) — business rationale and scope authority.
- [`docs/ui-ux-design.md`](./ui-ux-design.md) — screens/flows implementing this workflow.
- [`docs/api-specification.md`](./api-specification.md) — endpoints implementing each feature area.
- [`docs/database-design.md`](./database-design.md) — entities backing each feature area.
- [`docs/phase-wise-requirements.md`](./phase-wise-requirements.md) — implementation sequencing.
