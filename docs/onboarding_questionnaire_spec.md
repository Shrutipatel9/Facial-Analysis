# Onboarding Questionnaire Specification

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`FR-003`, `FR-004`, `BR-003`, `WF-001` step 2). Literal question content sourced from the client's own reference material, `Qoves Onboarding.mp4` (a screen recording of the live Qoves.com onboarding flow) — question order confirmed via the on-screen "N / 23" progress counter present on every question screen. This document resolves the open item previously flagged in [`docs/prd.md`](./prd.md) §7, [`docs/ui-ux-design.md`](./ui-ux-design.md) §5, and [`docs/phase-wise-requirements.md`](./phase-wise-requirements.md) (Phase 2 blocking prerequisite).

**Status:** Draft — sourced directly from client reference material, not invented. Two items remain open and need explicit client confirmation before this is treated as final (see §5).

---

## 1. Overview

The onboarding questionnaire is a fixed-length, 23-question flow completed after signup and before photo upload (`WF-001` step 2). It ends in a mandatory, checkbox-gated disclaimer (`FR-004`, `BR-003`) that must be re-validated server-side, not just gated client-side. One question (`Q19`) is conditionally shown based on an earlier answer — see §3.

## 2. The 23 Questions

| # | Question | Type | Options / Notes |
|---|---|---|---|
| 1 | What is your occupation? | Free text | e.g. "Entrepreneur" |
| 2 | How often do you smoke? | Single select | Never / Rarely / Sometimes / Often / Daily |
| 3 | How often do you drink? | Single select | Never / Rarely / Sometimes / Often / Daily |
| 4 | Would you rather look more masculine or more feminine? | Single select | Masculine / Feminine / No Preference |
| 5 | Have you had any non-surgical aesthetic treatments before? | Yes/No | |
| 6 | We're strictly non-surgical, but for accuracy, have you ever undergone facial cosmetic surgery? | Yes/No | |
| 7 | Please select all treatment types you are comfortable undergoing: | Multi-select | Injectables (minimally invasive) — Botox, Dermal Fillers, Fat-Dissolving Injections; Non-invasive treatments — Laser, IPL/LED, Ultrasound, Radiofrequency Treatments; Invasive treatments — Microneedling, Endo-Lift, Collagen-Stimulating Procedures; Semi-permanent enhancements — Microblading, Lip Blush, Tattoo-Based Treatments |
| 8 | Do you have any medical conditions (e.g. autoimmune disorders, diabetes)? | Yes/No | |
| 9 | Are you taking any medications (prescription or over-the-counter)? | Yes/No (+ free text?) | See §5 — likely branches to a list on "Yes" |
| 10 | Have you used retinoids (e.g. Isotretinoin / Accutane) in the past 6–12 months? | Yes/No | |
| 11 | Do you have any allergies (especially to skincare ingredients, lidocaine, latex, dyes)? | Yes/No (+ free text?) | See §5 — likely branches to a list on "Yes" |
| 12 | Any active infections, cold sores, or skin conditions (e.g. Rosacea, Eczema, Psoriasis)? | Yes/No | |
| 13 | Are you prone to hyperpigmentation? | Yes/No | |
| 14 | What feature do you like the most about your face? | Free text | e.g. "My eye color" |
| 15 | What feature do you dislike the most about your face? | Free text | e.g. "Eyebrows" |
| 16 | Are there any celebrities' facial aesthetics that you'd like to look like? | Free text | e.g. "Chris Brown" |
| 17 | Are you comfortable with weight loss recommendations? | Yes/No | |
| 18 | What is your goal? | Single select | Refine and enhance my facial aesthetic / Significantly transform my facial aesthetic / Undecided |
| 19 | Can you grow a full beard? | Yes/No | **Conditional** — see §3 |
| 20 | How much distress does your current facial aesthetic cause you? | Single select | No distress at all / Minor distress / Moderate distress / Extreme distress and affects my day to day |
| 21 | How often do you think about your appearance? | Single select | Rarely (a few times a week or less) / Occasionally (once a day) / Frequently (multiple times a day) / Very often (most of the day) / Constantly (it's always on my mind) |
| 22 | What motivated you to sign up for FaceIQ? | Free text | e.g. "Just curious" |
| 23 | Anything else you think we should know? | Free text | Same screen carries the disclaimer gate — see §4 |

## 3. Branching Logic

Only one conditional branch was observed in the reference material: **Q19 ("Can you grow a full beard?")** appeared only in a session where **Q4 was answered "Masculine."** The working assumption is:

- Q4 = Masculine or No Preference → Q19 shown
- Q4 = Feminine → Q19 skipped

This is inferred from a single recorded pass, not exhaustively verified against all three branches — confirm with the client or by re-testing the live Qoves flow before final implementation. All other 22 questions appeared identically regardless of prior answers.

## 4. Disclaimer Gate (`FR-004`, `BR-003`)

Appears on the same screen as Q23. Exact wording:

> "I hereby confirm that I do not have any concerns related to Body Dysmorphic Disorder or other conditions affecting my perception of my appearance. I understand that treatment recommendations are purely for informational reasons and not medical guidance. Any implementation of treatments is at my own discretion."

A single checkbox; the Submit button is disabled until checked. Per `BR-003`, this must be a hard gate re-validated server-side on `POST /questionnaire/responses` (`docs/api-specification.md` §4) — client-side gating alone is insufficient.

## 5. Open Items Requiring Client Confirmation

| Item | Detail |
|---|---|
| Q9 / Q11 follow-up shape | Both rendered their answer as a plain "No" rather than a visible Yes/No control in the captured frames, suggesting a Yes/No question that reveals a free-text (or list) follow-up when answered "Yes" (e.g. "please list your medications" / "please list your allergies"). Not confirmed — affects the `Questionnaire Response` JSON shape in `docs/database-design.md` §2.4. |
| Q19 branching condition | Confirm whether it's strictly Q4-driven, and what the exact condition is (Masculine only, or Masculine + No Preference). |

## 6. Data Shape Recommendation

Consistent with `docs/database-design.md` §2.4's existing recommendation, store responses as structured JSON keyed by question number (`{"q1": "Entrepreneur", "q2": "Never", ...}`) rather than 23 fixed columns, since Q9/Q11's exact shape is still open and a fixed-column schema would force a migration once confirmed.

## 7. Related Documents

- [`client_requirements.md`](./client_requirements.md) — `FR-003`, `FR-004`, `BR-003`.
- [`docs/prd.md`](./prd.md) §3.3 — functional requirement this spec fulfills.
- [`docs/ui-ux-design.md`](./ui-ux-design.md) §3.3 — screen-level notes this spec resolves.
- [`docs/database-design.md`](./database-design.md) §2.4 — `Questionnaire Response` entity.
- [`docs/api-specification.md`](./api-specification.md) §4 — `POST /questionnaire/responses` server-side validation.
- [`docs/phase-wise-requirements.md`](./phase-wise-requirements.md) — Phase 2 (`onboarding-questionnaire` module).