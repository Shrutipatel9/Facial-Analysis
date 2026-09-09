# Database Design

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`DATA-*`). Auth-specific entities are elaborated here but their behavioral rules live in [`docs/authentication.md`](./authentication.md).

**Status:** Draft, high-level entity design. `client_requirements.md` explicitly scopes full column-level schema to this document (Section 9), but does not itself specify column types/lengths — those below marked **[Recommendation]** are technical proposals, not client-stated requirements. Database: vendor-neutral PostgreSQL, ORM: SQLAlchemy, migrations: Alembic (`NFR-002`–`NFR-004`; v1.2 had superseded these from Supabase Postgres/SQLAlchemy/Alembic to Prisma-based tooling under a since-reverted single-app consolidation — v1.3 reverts the ORM/migrations back to SQLAlchemy/Alembic; the Supabase→vendor-neutral-Postgres change from v1.2 stands).

---

## 1. Entity Overview

```
User ──1───* OTP Record
User ──1───* Refresh Token / Session Record
User ──1───* Questionnaire Response
User ──1───* Photo
User ──1───* Report
User ──1───* Payment

Questionnaire Response ──1───* Report   (a report is generated from one questionnaire response)
Photo (set) ──1───1 Facial Analysis Result ──1───1 Report
Report ──1───* Payment                  (payment gates access to a specific report)
```

Exact cardinalities (e.g. whether a user can have multiple in-flight reports) are **[Assumption]** pending confirmation — `client_requirements.md` does not state whether a user may request more than one report. Treat as **[Open Question]** for the `report-generation` module.

## 2. Entities

### 2.1 User (`DATA-001`)
| Field | Type (recommendation) | Notes |
|---|---|---|
| id | UUID / PK | |
| email | string, unique | |
| password_hash | string | Never plaintext — see `docs/security.md` §2 |
| full_name | string, nullable | **Added v1.13** — captured at signup (`RegisterRequest.full_name`), used for the dashboard's "Welcome back" greeting (`FR-017`). Nullable only for accounts created before this field existed; every new signup always provides one. Not independently editable post-signup — see `ASM-009`'s revision. |
| verification_status | enum/bool | Unverified until OTP-confirmed signup (`WF-002`) |
| role | string/enum | Phase 1: only `"user"` populated (`AUTH-009`) — reserved for Phase 2 `"admin"` |
| created_at / updated_at | timestamp | |

### 2.2 OTP Record (`DATA-002`)
| Field | Notes |
|---|---|
| id | PK |
| user_id (or pending-signup reference) | Linked to a user, or a pending signup that has no confirmed User row yet — signup's Step 1 creates a "pending/unverified user record" per `WF-002`, so this may reference that pending User row rather than a separate table. **[Recommendation]**: use the pending User row directly rather than a separate pending-signup entity, to avoid a parallel identity model. |
| otp_hash | Hashed value, never plaintext (`AUTH-011`) |
| purpose | `signup` \| `login` |
| expiry | 10 minutes from issuance (`AUTH-011`) |
| attempt_count | Resets per new OTP; lockout after 5 (`AUTH-011`) |
| consumed | bool |
| created_at | Also anchors the 60s resend cooldown (`AUTH-011`) |

### 2.3 Refresh Token / Session Record (`DATA-003`)
| Field | Notes |
|---|---|
| id / token_identifier | The record is keyed by an identifier, **never the raw token** (`AUTH-010`) |
| user_id | |
| issued_at / expires_at | 30-day lifetime (`AUTH-012`) |
| revoked | bool — set on logout (`AUTH-010`) or on reuse detection (`AUTH-012`) |
| rotation lineage (e.g. `replaced_by_id` / `family_id`) | Required to detect reuse of an already-rotated-out token and revoke the whole family (`AUTH-012`) |

### 2.4 Questionnaire Response (`DATA-004`)
| Field | Notes |
|---|---|
| id | |
| user_id | |
| answers | The 23 branching answers (`FR-003`), keyed by question id per [`docs/onboarding_questionnaire_spec.md`](./onboarding_questionnaire_spec.md) §6: `q1`..`q23`, plus `q9_details`/`q11_details` (optional free-text follow-ups, `[Assumption]` pending client confirmation — see that spec's §5). Stored as `JSONB` (question id → answer; multi-select `q7` → array of strings), not 23+ fixed columns — this was already the recommendation here before the content was finalized, and still applies now: the two remaining `[Assumption]` items could still change the shape slightly, and a fixed-column schema would force a migration for that. An answer submitted for a question that isn't currently visible under its `show_if` condition (e.g. `q19` when `q4` = Feminine) is silently dropped server-side before storage, never persisted — see `Backend/app/services/questionnaire_service.py`. |
| disclaimer_accepted | bool, must be true before submission is accepted (`BR-003`, `FR-004`) — re-validated server-side (`DISCLAIMER_NOT_ACCEPTED` on failure), not just gated client-side |
| submitted_at | |

### 2.5 Photo (`DATA-005`)
Implemented in `photo-upload-validation` (`Backend/app/models/photo.py`). One row per `(user_id, angle)` — `UniqueConstraint`, not one row per upload attempt: a retry upserts the existing row in place (`Backend/app/services/photo_service.py`), matching the module's one-and-done posture (no separate upload-history table).

| Field | Notes |
|---|---|
| id | |
| user_id | FK → `users.id`, `ondelete="CASCADE"`, indexed |
| angle | Which of the multi-angle set this is (`FR-005`). String, validated in code against `REQUIRED_ANGLES` (`Backend/app/services/photo_validation_service.py`) rather than a Postgres enum — same migration-flexibility rationale as `answers` below, since `ASM-005` (3 vs. Qoves' 7 angles) is not yet client-confirmed; see [`docs/photo_capture_spec.md`](./photo_capture_spec.md) §1/§5 |
| capture_method | `"upload"` \| `"camera"` — **[Recommendation, per `docs/photo_capture_spec.md` §4]**: not a client-stated requirement, kept only in case it's useful for analytics/debugging later |
| storage_reference | Where the file lives. **Resolved** (was an Open Question through v1.2): the storage mechanism is a swappable interface (`PhotoStorage` ABC, `Backend/app/services/photo_storage.py`), mirroring `EmailSender`'s pattern. **Default is `DatabasePhotoStorage`** (`PHOTO_STORAGE_PROVIDER=database`) — bytes live in Postgres (`PhotoBlob`, keyed by the same opaque `storage_reference`), not the local filesystem; `LocalDiskPhotoStorage` and a real `S3PhotoStorage` (S3-compatible, incl. non-AWS via `S3_ENDPOINT_URL`) remain available and swappable via config. The default moved off local disk so nothing is written to `Backend/var/photo_storage/` at all (a real problem on read-only/ephemeral container filesystems) and so a photo's bytes are retrievable via `GET /photos/{id}/file` for a persistent frontend preview across a reload — see `docs/api-specification.md` §5. Picking a different vendor later is a new `PhotoStorage` implementation, not a schema or service rewrite. |
| validation_status | `"pending"` \| `"passed"` \| `"failed"` (`BR-005`) |
| validation_result | `JSONB`, always all six checks (not just failures) — `{"checks": [{"check", "passed", "reason"}, ...]}` — see `docs/security.md` §6 for the check list and thresholds. Powers the rejection-reason UI (`docs/ui-ux-design.md` §3.4). |
| uploaded_at | `server_default=now()`, `onupdate=now()` — reflects the latest attempt on a retry, not the first |

**`PhotoBlob`** (`Backend/app/models/photo_blob.py`, used only when `PHOTO_STORAGE_PROVIDER=database`): `id` (the opaque `storage_reference` string, not a FK — `PhotoStorage`'s contract treats it as opaque to callers), `content` (`LargeBinary`), `content_type`, `created_at`, `updated_at`. Deliberately decoupled from the `Photo` model itself so the storage backend stays swappable without touching `Photo`'s own schema.

### 2.6 Facial Analysis Result (`DATA-006`)
Implemented in `facial-analysis-engine` (`Backend/app/models/facial_analysis_result.py`). No DB-level uniqueness on `user_id` -- "one analysis per user, no re-run" (mirrors the questionnaire's/photos' one-and-done posture) is enforced in `Backend/app/services/analysis_service.py` (`AnalysisAlreadyExistsError`), not a DB constraint; a `"failed"` row may be retried (a new row, not an update-in-place).

| Field | Notes |
|---|---|
| id | |
| user_id | FK → `users.id`, `ondelete="CASCADE"`, indexed. Locates the photo set directly (no snapshot/join table needed -- photos are immutable once the set is complete, `PhotoSetAlreadyCompleteError` already blocks further uploads) |
| questionnaire_response_id | FK → `questionnaire_responses.id`, indexed -- which submitted response was actually used, for traceability (`FR-008`'s acceptance criteria wants both inputs provably present) |
| status | `"processing"` \| `"completed"` \| `"failed"` |
| measurements | Per-feature landmark/measurement output from MediaPipe/OpenCV (`FR-007`), `JSONB`, always keyed by all 11 features from `FR-009`/`BR-008`. MediaPipe's Face Landmarker only really covers 7 with real geometry (Eyebrows, Eyes, Nose, Cheeks, Jaw, Lips, Chin); Ears/Skin get simpler heuristics; **Hair and Neck carry no CV geometry at all** (`null`, not omitted) and are covered entirely by the AI narrative call's own visual read of the photos -- a real limitation, documented in `Backend/app/services/facial_measurement_service.py`, not silently glossed over |
| narrative_result | Raw AI output (`FR-008`), `JSONB`, nullable until `status="completed"` -- one entry per feature (narrative + summary-callout draft + recommendation ideas) plus a closing-recommendations draft. `report-generation` (Phase 5) wraps this with intro/preamble/limitations/before-after framing into the client-facing Report; it does not re-call the AI |
| error_message | Nullable, set on `"failed"` -- human-readable, for support/debugging and the frontend's failure state |
| created_at | |
| completed_at | Nullable until done |

**AI vendor (`ASM-006`):** `NFR-008` names OpenAI; this is built against **DeepSeek** instead (delivery-team decision, flagged for client awareness -- see `docs/client_requirements.md` v1.8). DeepSeek's hosted API is OpenAI-Chat-Completions-compatible, so the `openai` SDK is used pointed at a configurable `base_url` (`Backend/app/services/ai_narrative_service.py`) -- switching to real OpenAI later is a config change (`AI_BASE_URL`/`AI_API_KEY`/`AI_MODEL`), not a new implementation. **Multimodal:** the actual photos are sent to the AI (base64), not just derived measurements -- see `docs/security.md` §7.

**Pay-before-analysis (Phase 6, v1.11 revision):** no `FacialAnalysisResult` row is created at all until the user has a succeeded `Payment` (§2.8) -- `analysis_service.trigger_analysis` checks this before writing anything. The trigger itself stays a user-facing "Start Analysis" click (`POST /analysis`), same as before payment gating existed -- only now reachable once payment has already succeeded. `payment_service.handle_webhook_event` deliberately does **not** call `trigger_analysis` itself; it only flips `Payment.status` -- auto-triggering was tried and reverted, since the pipeline can finish in a couple of seconds and made the "analyzing" step invisible to the user. `status`/`measurements`/`narrative_result` are then all populated together in one pass (`analysis_service.run_analysis_pipeline`) -- CV/MediaPipe extraction immediately followed by the DeepSeek narrative call, since both only ever run post-payment now. A narrative-generation failure (the DeepSeek call itself failing, after CV succeeded) still leaves `narrative_result` `null` while `status` stays `"completed"` -- the user already paid and has valid measurements, so a manual pipeline re-invoke is the practical retry path, not a full refund/failure.

### 2.7 Report (`DATA-007`)
| Field | Notes |
|---|---|
| id | |
| user_id | |
| questionnaire_response_id | |
| analysis_result_id | 1:1 with the source `FacialAnalysisResult` -- see "Multiple reports per user" resolution below |
| sections | **Resolved (v1.9)**: single `JSONB` blob (not a child table), assembled by `Backend/app/services/report_assembly_service.py`'s pure `assemble_sections()` from the analysis result's `measurements`/`narrative_result` -- `{intro, understanding_your_results, limitations, features: {<feature>: {narrative, summary_callout, projected_potential, measurement}}, recommendations: {at_home, otc_skincare, in_clinic}, closing_recommendations}`. `intro`/`understanding_your_results`/`limitations` are static branded template copy, not AI-generated -- see `ASM-007` |
| pdf_reference | Generated PDF artifact reference (`FR-013`) -- null until the first `GET /reports/{id}/pdf` call lazily renders and caches it in `ReportPdfBlob` (mirrors `PhotoBlob`'s decoupled-storage shape) |
| publish_state | Phase 1: published-on-generation (`BR-002`); field should still exist (not a hardcoded skip) so Phase 2's Draft/Pending Review/Approved/Published states can be added without a schema rework, consistent with the `role` field's forward-compatibility rationale (`AUTH-009`) |
| created_at | |

**AI-free assembly:** unlike Phase 4, report assembly makes **no AI call** -- it is a synchronous, pure data transform of the already-computed `measurements`/`narrative_result`, so `POST /reports` (idempotent get-or-create, `Backend/app/services/report_service.py`) finishes within the request, no background task/polling needed.

**Recommendation tiering (`ASM-007`):** `FR-012`'s three tiers (at-home/lifestyle, OTC/skincare-active, in-clinic) are produced by a first-pass keyword heuristic (`report_assembly_service.classify_recommendations`) over the existing flat `recommendation_ideas` strings, not a dedicated AI call or a change to Phase 4's prompt -- delivery-team decision, not clinically validated, expect a tuning pass once real report output is reviewed (same posture as the photo-validation thresholds, `ASM-002`).

### 2.8 Payment (`DATA-008`) — **Implemented (Phase 6, v1.11)**
| Field | Notes |
|---|---|
| id | |
| user_id | FK → `users.id`, `ondelete="CASCADE"`, indexed |
| stripe_session_id | Stripe Checkout Session identifier (the `stripe_reference` above) — the webhook's own lookup key, since `handle_webhook_event` trusts only server-set state, never the client redirect |
| status | `"pending"` (row created at checkout-session creation) \| `"succeeded"` (webhook confirmed) \| `"failed"` (webhook reported `payment_intent.payment_failed`/`checkout.session.expired`) — a `"failed"` row does not block a fresh checkout attempt |
| amount_cents | Copied from `REPORT_PRICE_CENTS` **at checkout-creation time**, never re-read live — a mid-flight price change never affects an in-progress payment. Configurable value, not hardcoded, satisfying `FR-016`; the price itself stays open (`OQ-002`) |
| currency | Copied from `REPORT_PRICE_CURRENCY` at the same time |
| created_at | |

**No `report_id` (revised in v1.11):** a `Payment` is always created and resolved *before* any `FacialAnalysisResult` or `Report` exists for the user, so there is nothing to reference at creation time — "has this user paid" is answered by querying for a `status="succeeded"` row scoped to `user_id`. (An earlier version of this table had a `report_id` FK, from a design where payment gated only the report's full content rather than the start of analysis itself — superseded the same day, before ever being deployed.)

**Enforcement point (`BR-001`, v1.11):** `analysis_service.trigger_analysis` raises `PaymentRequiredError` (402) unless a `status="succeeded"` `Payment` row exists for the user — this is the actual gate, checked *before* any `FacialAnalysisResult` row is created, not at report-read time. `report_service` no longer has any payment-awareness at all: a `Report` can only ever be created from an already-`"completed"` analysis, which by construction never exists without a preceding succeeded payment, so `GET /reports/{id}` and `GET /reports/{id}/pdf` are unconditionally full once a report exists.

## 3. Deferred to Phase 2 (do not model yet)

Per `client_requirements.md` Section 9: Admin/reviewer accounts, report review history, AI-chat Conversation records, generated Visual Assets (hairstyle/outfit/aging images). Do not add tables for these in Phase 1 — the `role` field (§2.1) and `publish_state` field (§2.7) are the only forward-compatibility accommodations the client asked for.

## 4. Migrations

Alembic (`NFR-003`) manages schema evolution against the SQLAlchemy models. Because several fields above are intentionally under-specified (questionnaire answer shape, measurement shape, report section shape — all recommended as JSON precisely to avoid migration churn while those are still moving), initial migrations should favor a `JSONB` column type (PostgreSQL's indexed/queryable JSON type, via SQLAlchemy's `JSONB`) for content that is still in flux, and normalize into dedicated models/relations later only once the shape is stable — this is a **[Recommendation]**, not a client instruction, aimed at reducing migration thrash during a from-scratch build. Always review Alembic's autogenerated migration diffs before applying — autogenerate is a starting point, not a guarantee of correctness (e.g. it won't detect some column-type or constraint changes).

## 5. Open Questions

| Item | Status |
|---|---|
| Can a user have multiple reports? | **Resolved (v1.9)** — one report per user, 1:1 with the analysis result, matching this document's own ERD (§1) and Phase 4's "one analysis per user, no re-run" posture. Enforced service-side (`report_service.get_or_create_report`'s get-or-create semantics), not a DB uniqueness constraint — same convention as `FacialAnalysisResult`/`AnalysisAlreadyExistsError`, so a future re-analysis/multiple-reports feature would only need a service-layer change. |
| Photo storage mechanism | **Resolved** — swappable `PhotoStorage` interface, see §2.5 above. |
| Password hashing algorithm | Not stated — **[Recommendation]**, see `docs/security.md` §7. |
| 3-angle default vs. Qoves' 7-pose set (`ASM-005`) | Not yet confirmed by the client — **[Open Question]**, see [`docs/photo_capture_spec.md`](./photo_capture_spec.md) §5. |
| AI vendor: DeepSeek vs. client-stated OpenAI (`ASM-006`) | Not yet confirmed by the client — **[Open Question]**, see §2.6 above. |
| Recommendation tiering heuristic (`ASM-007`) | Not yet confirmed by the client — **[Open Question]**, keyword-based first pass, see §2.7 above. |
| Facial Analysis Result is currently one-per-user (no re-run) | **Resolved** — stays one-per-user; the "multiple reports" question above resolved toward "no," so no revisiting needed. |

## 6. Related Documents

- [`docs/authentication.md`](./authentication.md) — behavior of the User/OTP Record/Refresh Token entities.
- [`docs/api-specification.md`](./api-specification.md) — how endpoints read/write these entities.
- [`docs/security.md`](./security.md) — hashing/storage requirements for sensitive fields.
