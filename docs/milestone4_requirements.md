# Milestone 4 Requirements — Report Intelligence Upgrades + Content Hub

**Source of truth:** [`client_requirements.md`](./client_requirements.md) remains the single project source of truth. This document is a subordinate addendum, same relationship [`milestone3_requirements.md`](./milestone3_requirements.md) has to it.

**Status:** Draft — feature set proposed by the delivery team, scoped with the user via `AskUserQuestion` on 2026-09-22, pending implementation.

**Version:** 1.0 (2026-09-22).

**"Milestone 4" naming:** continues the naming pattern established by Milestones 2/3 — **no corresponding numbered phase in `client_requirements.md`**, not yet client-scoped. Every requirement below is labeled **[Recommendation]**, same posture as Milestone 3.

---

## 1. Source Material

Three research passes on 2026-09-22: (a) a re-read of this project's own current-scope docs (`client_requirements.md` v1.27, `CLAUDE.md`, all prior milestone docs) to avoid re-proposing anything already built or already decided against; (b) a re-mining of `https://www.qoves.com/` (already the reference site for Milestone 3) specifically for anything not already covered by Milestones 2–3; (c) a broader scan of other real AI beauty/skin-analysis products (Perfect Corp/YouCam, Haut.AI, TroveSkin, Miiskin, L'Oréal's Beauty Genius) for ideas outside the one reference site already used.

**Branding/fabrication note (same posture as Milestone 3):** every requirement below describes behavior/structure to draw inspiration from, never literal copying of a competitor's branding, copy, or unverifiable statistics.

**One correction made during this document's own drafting, not silently absorbed:** the originally-proposed "persistent chat memory across sessions" (from the L'Oréal Beauty Genius comparison) was investigated and found to already be fully built — `chat_service.stream_reply` already sends the complete prior conversation history to the model on every reply, not just the current turn (`Backend/app/services/chat_service.py:185-229`). `FR-030` below targets the real adjacent gap (unbounded context growth for a long-lived conversation) instead.

## 2. What Was Found — Candidate Inventory

### 2.1 Already deferred, explicitly excluded from this milestone
Admin panel, full report review workflow, real email-notification vendor, Meta Pixel/GTM, formal data-retention/privacy policy (`client_requirements.md` §12, unchanged through v1.27) — these were deferred by explicit client decision, not oversight. Not included below; would need the client's own fresh sign-off.

### 2.2 Also considered, explicitly excluded from this milestone (user decision, 2026-09-22)
- **Pricing/monetization model** — qoves.com runs a $150/yr membership plus separate à-la-carte report tiers (Preliminary/Comprehensive/Hairline Design/Style Lookbook/etc.), addressing this project's own still-open `OQ-002`. Excluded this round. **Flagged specifically:** qoves' "book a new analysis at half price from the dashboard" mechanic is adjacent to the `FR-026` progress-tracking feature the client explicitly had removed 2026-09-18 — any future pricing work touching multiple-reports-per-user needs fresh client confirmation, not a silent reintroduction.
- **Photo/measurement quality upgrades** — pre-capture image-quality gating (Haut.AI's LIQA — guides the user to a good photo before upload) and revisiting the 3-vs-7 photo angle question (already open as `ASM-005`/`OQ-010`). Excluded this round.

### 2.3 Selected for this milestone
- **Recommendation tiering upgrade** — `report_assembly_service.py`'s at-home/OTC/in-clinic classification is a keyword heuristic (`_IN_CLINIC_KEYWORDS`/`_OTC_KEYWORDS`), not AI-based, and was never client-confirmed as final (`ASM-007`/`OQ-012`, already open). Upgrading it to a real AI-classified field is a zero-new-cost addition to the existing narrative-generation call.
- **Chat conversation compaction** — the real gap adjacent to the (already-built) persistent-history finding above: nothing bounds a long-lived conversation's growing context size/token cost.
- **Content/education hub** — qoves.com's "Insights" section (Facial Measurements/Concerns/Procedures/Attraction Science/Comparisons categories) is a genuinely uncovered feature area — an educational content library, distinct from the product's report/chat/payment surfaces.

## 3. Functional Requirements — Milestone 4 (`FR-029`–`FR-031`)

| ID | Requirement | Source |
|---|---|---|
| **FR-029** | **AI-classified recommendation tiering.** Add a `tier` field (`at_home`/`otc_skincare`/`in_clinic`, closed vocabulary, JSON-null if uncertain) to the existing `recommendation_ideas` structured output (`ai_narrative_service.py`'s narrative-generation call — no new AI request). `report_assembly_service.py`'s tier-bucketing reads this field first, falling back to the existing keyword heuristic only when absent (required for every already-persisted report, which will never have this field — no backfill migration, same posture as every other Milestone-3-era additive field). | [Recommendation] (addresses already-open `ASM-007`/`OQ-012`) |
| **FR-030** | **Chat conversation compaction.** When a conversation's message history exceeds a configurable threshold, summarize the older portion into a running summary stored on the `Conversation` row, and send `[system prompt + summary] + [recent N raw messages]` to the model instead of the full unbounded history. The user's own message history view is unaffected (DB rows never deleted, only excluded from what's sent to the model going forward). This introduces occasional new AI calls (one per compaction event, only for conversations that actually get long) — not zero-cost, unlike `FR-029`. | [Recommendation] (real gap found during this document's own research — see §1) |
| **FR-031** | **Content/education hub.** A public `/insights` section of short, first-party, product-grounded educational articles (what a harmony score means, what symmetry/prototypicality/dimorphism are, how to get the best analysis photos, general uncontroversial facial-aesthetics concepts). Content-only, no new backend. Explicitly excludes procedure/treatment content (Botox, fillers, surgery — real clinical-accuracy/liability surface with no review process in this codebase) and competitor-comparison pages (qoves.com's "Comparisons" category — not this codebase's claim to make). | [Recommendation] (from qoves.com's Insights section, 2026-09-22) |

## 4. Explicit Non-Goals (do not build without a separate decision)

- **Do not build clinical/procedure-explainer content** for `FR-031` (Botox, fillers, surgery, or any treatment-efficacy claim) — real medical-accuracy risk this project has no clinical review process for. Stick to explaining what the product itself computes, or general uncontroversial aesthetics concepts.
- **Do not fabricate competitor-comparison content** for `FR-031` — qoves.com's own "Comparisons" category is explicitly not being replicated.
- **Do not silently reintroduce multiple-analyses-per-user** via `FR-029`/`FR-030`/`FR-031` — none of the three touch that decision, and none should; the reverted `FR-026` stays reverted absent a fresh client ask.
- **Do not treat `FR-030`'s compaction threshold/summary-length defaults as final** — see `OI-5` below.

## 5. Open Items Requiring Sign-Off (`OI-*`, restarting per-document per this project's own convention)

- **OI-5 — `FR-030`'s exact compaction threshold and how much history to summarize vs. keep raw.** Proposed default: summarize once a conversation exceeds ~30 messages, keep the most recent messages raw. Not client-facing, low-risk to tune later, but stated here as genuinely undecided rather than silently picked.
- **OI-6 — `FR-031`'s initial article list and count.** Proposed: 4–6 articles for v1 (enough to feel real, not a placeholder), covering what the product already computes plus general aesthetics concepts. Exact titles/topics are an editorial call, not a blocking engineering question.

## 6. Related Documents

- [`milestone4_phase_plan.md`](./milestone4_phase_plan.md) — sequences `FR-029`–`FR-031` into Implementation Phases 26–28.
- [`milestone3_requirements.md`](./milestone3_requirements.md) / [`milestone3_phase_plan.md`](./milestone3_phase_plan.md) — `FR-025`'s recommendation-idea structured fields (`cost`/`cadence`/`difficulty`/`category`/`risk_level`/`product_or_method`) are what `FR-029`'s `tier` field extends.
- [`milestone3.1_phase_plan.md`](./milestone3.1_phase_plan.md) — the production-hardening milestone immediately preceding this one; Implementation Phase numbering continues from its Phase 25.
