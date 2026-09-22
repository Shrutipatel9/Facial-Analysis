# Milestone 4 — Phase Plan

**Source of truth:** [`milestone4_requirements.md`](./milestone4_requirements.md) (the detailed requirements this plan sequences), itself subordinate to [`client_requirements.md`](./client_requirements.md). This document does the same job for Milestone 4 that [`milestone3_phase_plan.md`](./milestone3_phase_plan.md) did for Milestone 3 — it continues that document's Implementation Phase numbering (which Milestone 3.1 already continued through Phase 25), not client delivery Phase numbering.

**Naming disambiguation:** "Milestone 4" is **not yet a numbered client delivery phase** — same posture as Milestones 3 and 3.1. Every phase below sequences `milestone4_requirements.md`'s `[Recommendation]`-labeled proposal; treat as provisional until that document's Open Items (`OI-5`, `OI-6`) are resolved. Implementation Phases below continue numbering as **26–28**.

**Status:** Draft roadmap. Nothing in this plan is implemented yet. Per-module `plans.md` files created once each module's implementation actually starts.

**Version:** 1.0 (2026-09-22).

---

## Phase Overview & Module Map

| Implementation Phase | Name | Module(s) | `plans.md` location (once started) |
|---|---|---|---|
| 26 | AI-Classified Recommendation Tiering | `recommendation-tiering` | `D:\zzz\recommendation-tiering\plans.md` |
| 27 | Chat Conversation Compaction | `chat-compaction` | `D:\zzz\chat-compaction\plans.md` |
| 28 | Content/Education Hub | `insights-hub` | `D:\zzz\insights-hub\plans.md` |

**Dependency chain:**

```
Milestone 3.1 (Phases 20-25, production hardening, complete)
        │
        ├──► Phase 26 (Recommendation Tiering)   ── independent; extends the
        │                                             existing Milestone 3 protocol fields
        │
        ├──► Phase 27 (Chat Compaction)           ── independent; extends the
        │                                             existing Milestone 2 chat feature
        │
        └──► Phase 28 (Insights Hub)              ── independent, content-only,
                                                        can run in parallel with anything
```

Suggested default order: **26 → 27 → 28**, i.e. the zero-new-cost backend change first, then the low-cost backend change, then the content-only frontend work last (easiest to hand to a different contributor or defer without blocking the other two). All three are genuinely independent — any order works.

---

## Phase 26 — AI-Classified Recommendation Tiering

**Objective:** Replace the keyword-heuristic at-home/OTC/in-clinic classification with a real AI-classified field, per `FR-029`.

- **Scope:** Add a `"tier"` field (exactly one of `"at_home"`/`"otc_skincare"`/`"in_clinic"`, or JSON `null` if uncertain) to the `recommendation_ideas` object shape in `ai_narrative_service.py`'s system prompt — same closed-vocabulary/null-if-uncertain posture already used for `difficulty`/`category`/`risk_level`. Extend `_sanitize_recommendation_ideas` to validate it the same way. Update `report_assembly_service.py`'s `classify_recommendations`/`feature_recommendation_tier` to read `idea.get("tier")` first, falling back to the existing keyword heuristic (`_IN_CLINIC_KEYWORDS`/`_OTC_KEYWORDS`/`_classify_one`) only when the field is absent.
- **Modules/features included:** `recommendation-tiering`.
- **Functional requirements:** `FR-029`.
- **Technical requirements:** No new AI vendor/call — one additional field on the existing narrative-generation structured output. No new CV work.
- **Dependencies:** Milestone 3 Phase 16 (`protocol-enrichment`) — extends the same `recommendation_ideas` object that phase introduced (`cost`/`cadence`/`difficulty`/`category`/`risk_level`/`product_or_method`).
- **API requirements:** No new endpoint — the existing report payload's recommendation objects gain the field already exposed today, no schema-breaking change.
- **Database requirements:** None — `narrative_result` is JSONB; the new key just appears in freshly-generated reports. No migration.
- **UI/UX requirements:** None required — the tier bucketing already drives existing UI (protocol tier grouping); this only changes how the bucket is *decided*, not how it's rendered.
- **Security considerations:** None beyond existing narrative-generation posture.
- **Testing requirements:** Fully covered by the existing mocked pattern (`ai_recorder`) — a synthetic completion response with `tier` set exercises the new path; the many existing fixtures with no `tier` key prove the keyword fallback still works unchanged. Zero real API calls needed.
- **Acceptance criteria:** A synthetic AI response with `tier: "in_clinic"` lands in the `in_clinic` bucket without the keyword heuristic running; a response with no `tier` key still classifies correctly via the existing fallback (regression-proof for every already-persisted report, which will never have this field).
- **Prerequisites:** None blocking. Lowest-risk, most self-contained phase in this plan — good candidate to build first.
- **Expected deliverables:** Updated system prompt + sanitization + tier-bucketing fallback logic; `D:\zzz\recommendation-tiering\plans.md` executed.
- **Potential risks:** Low. The only real risk is the model misclassifying an edge-case recommendation — mitigated by keeping the keyword heuristic as a permanent fallback, not a temporary bridge to delete later.
- **Open questions:** None blocking.

## Phase 27 — Chat Conversation Compaction

**Objective:** Bound a long-lived conversation's growing token/context cost, per `FR-030`.

- **Scope:** Add `Conversation.summary: str | None` (migration, additive/nullable). Add a `_maybe_compact(conversation, messages)` step in `chat_service.py`, run before building the prompt: if message count exceeds a configurable threshold, summarize everything except the most recent N messages via one focused AI call (a short "summarize this conversation for future context" prompt, not the full narrative-generation prompt), store the result on `Conversation.summary`. `_build_system_prompt` gains an optional "prior conversation summary: ..." clause when set. `get_history`/the frontend's message list are unaffected — DB rows are never deleted, only excluded from what's sent to the model going forward.
- **Modules/features included:** `chat-compaction`.
- **Functional requirements:** `FR-030`.
- **Technical requirements:** Reuses the existing chat model/client (`ASM-006`'s provider pattern) for the summarization call — no new vendor. New `Settings` field for the threshold (`chat_compaction_threshold_messages` or similar), matching this project's existing "put tunables in Settings" convention.
- **Dependencies:** Milestone 2 Phase 12 (`chat-assistant`) — extends its existing `stream_reply`/`_build_system_prompt`/`Conversation` model, does not replace them.
- **API requirements:** No new endpoint. `POST /chat/messages` behavior is unchanged from the caller's perspective — compaction is an internal implementation detail of building the prompt.
- **Database requirements:** One additive, nullable column on `Conversation` — no backfill needed (existing conversations simply have `summary=None` until they first cross the threshold).
- **UI/UX requirements:** None required — invisible by design, same posture as Milestone 3.1's reconciler. The user's own message history view never changes.
- **Security considerations:** The summarization prompt must not leak medical-condition/medication/allergy answers into the stored summary any more than the existing chat system prompt already avoids referencing them (`ai_narrative_service.py`'s existing "never reference the user's answers about medical conditions... for cosmetic commentary" rule — the summarization prompt should carry the same instruction).
- **Testing requirements:** `ai_recorder`'s existing call-count tracking covers this directly — seed a conversation past the threshold, assert exactly one extra (compaction) call fires, then assert a subsequent turn's prompt sent to the mock includes the stored summary. Zero real API calls needed to build or verify.
- **Acceptance criteria:** A conversation under the threshold behaves identically to today (no compaction call, full history sent). A conversation over the threshold triggers exactly one compaction call, after which subsequent turns send `[summary] + [recent N messages]`, not the full history.
- **Prerequisites:** `OI-5` (exact threshold/summary-length defaults) — proposed defaults in `milestone4_requirements.md` are reasonable starting points, not required to be finalized before implementation starts (low-risk to tune after shipping).
- **Expected deliverables:** `Conversation.summary` column + migration, `_maybe_compact` + prompt changes, new `Settings` field; `D:\zzz\chat-compaction\plans.md` executed.
- **Potential risks:** This is the one phase in this milestone that makes real, occasional new AI calls in production (not zero-cost like Phase 26) — flagged plainly in the requirements doc. Given the chat feature is a bounded, post-report conversation (not open-ended), most users likely never cross the threshold in normal use.
- **Open questions:** `OI-5` (threshold tuning) — see above.

## Phase 28 — Content/Education Hub

**Objective:** A public `/insights` section of short, first-party educational articles, per `FR-031`.

- **Scope:** New `frontend/src/lib/insights/articles.ts` (an `ARTICLES: {slug, title, category, excerpt}[]` const array, matching this codebase's existing hardcoded-content-array convention). New `frontend/src/app/insights/page.tsx` (index/grid, category-filterable). Each article gets its own static route — `frontend/src/app/insights/<slug>/page.tsx` — real JSX prose wrapped in a new shared `InsightsArticleLayout` component. `frontend/src/app/sitemap.ts` extended to map over the same `ARTICLES` array. A nav entry added to `LandingPage.tsx`'s currently-minimal header.
- **Modules/features included:** `insights-hub`.
- **Functional requirements:** `FR-031`.
- **Technical requirements:** No new dependency — no MDX/CMS exists in this codebase today and none is introduced; content is hand-written JSX per article, matching `LandingPage.tsx`/`BenefitsSection.tsx`'s existing pattern. Static folder-per-article routing, not a dynamic `[slug]` catch-all (avoids needing a slug→content lookup registry).
- **Dependencies:** None blocking — reuses only already-shipped conventions (Milestone 3.1 Phase 24's `sitemap.ts`, Milestone 3 Phase 19's `BenefitsSection.tsx` no-fabrication content discipline).
- **API requirements:** None — pure static frontend content, no backend involvement.
- **Database requirements:** None.
- **UI/UX requirements:** Must stay within the existing design system (Tailwind tokens, `Logo`/`Button` components, `motion/react` fade-up conventions already used on the landing page) — a premium, on-brand reading experience, not a bare markdown dump. Category filtering on the index page; a consistent article-page layout (breadcrumb back to `/insights`, a CTA back to the product at the end of each article).
- **Security considerations:** None — public, static, no user input, no auth surface touched.
- **Testing requirements:** `tsc --noEmit` + `eslint` + `npm run build` (this repo's established frontend verification, no test framework exists and none is being added). Visual check via browser against the user's own running dev server, same non-disruptive approach as Phase 24.
- **Acceptance criteria:** `/insights` renders an index of articles; each article route renders real, on-brand content; `sitemap.xml` includes every article URL; `robots.txt` needs no change (already allows all non-auth public paths by default).
- **Prerequisites:** `OI-6` (which articles to write first) — proposed default in `milestone4_requirements.md` is 4–6 articles covering what the product already computes plus general aesthetics concepts; exact titles are an editorial call, not a blocking engineering question.
- **Expected deliverables:** `/insights` index + N article pages, sitemap entries, landing-page nav entry; `D:\zzz\insights-hub\plans.md` executed.
- **Potential risks:** Content-accuracy/liability risk if scope creeps into clinical/procedure content or competitor comparisons — both explicitly excluded in `milestone4_requirements.md` §4's Explicit Non-Goals. Stay disciplined to product-grounded/general-concept content only.
- **Open questions:** `OI-6` (article list/count) — see above.

---

## Related Documents

- [`milestone4_requirements.md`](./milestone4_requirements.md) — the detailed requirements this plan sequences.
- [`milestone3_phase_plan.md`](./milestone3_phase_plan.md) — Phase 16's `recommendation_ideas` object shape, which Phase 26 extends.
- [`milestone2_phase_plan.md`](./milestone2_phase_plan.md) — Phase 12's `chat-assistant` module, which Phase 27 extends.
- [`milestone3.1_phase_plan.md`](./milestone3.1_phase_plan.md) — the production-hardening milestone immediately preceding this one; Implementation Phase numbering continues from its Phase 25.
