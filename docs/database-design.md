# Database Design

**Source of truth:** [`client_requirements.md`](./client_requirements.md) (`DATA-*`). Auth-specific entities are elaborated here but their behavioral rules live in [`docs/authentication.md`](./authentication.md).

**Status:** Draft, high-level entity design. `client_requirements.md` explicitly scopes full column-level schema to this document (Section 9), but does not itself specify column types/lengths — those below marked **[Recommendation]** are technical proposals, not client-stated requirements. Database: Supabase-hosted Postgres, ORM: SQLAlchemy, migrations: Alembic (`NFR-002`–`NFR-004`).

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
| answers | The 23 branching answers (`FR-003`). **[Recommendation]**: store as structured JSON (question id → answer) rather than 23 fixed columns, since the literal question set is not yet finalized (see `docs/prd.md` §7) — a fixed-column schema would need a migration every time the question set changes during development. |
| disclaimer_accepted | bool, must be true before submission is accepted (`BR-003`, `FR-004`) |
| submitted_at | |

### 2.5 Photo (`DATA-005`)
| Field | Notes |
|---|---|
| id | |
| user_id | |
| angle | Which of the multi-angle set this is (`FR-005`) |
| storage_reference | Where the file lives — storage mechanism not specified by the client; **[Open Question]** whether photos live in Supabase Storage or elsewhere |
| validation_status | Pass/fail (`BR-005`) |
| validation_result | Structured detail on which check(s) failed, for the rejection-reason UI (`docs/ui-ux-design.md` §3.4) |
| uploaded_at | |

### 2.6 Facial Analysis Result (`DATA-006`)
| Field | Notes |
|---|---|
| id | |
| photo_set_reference | Linked to the Photo set it was derived from |
| measurements | Per-feature landmark/measurement output from MediaPipe/OpenCV (`FR-007`) — **[Recommendation]**: structured JSON keyed by the 11 features in `FR-009`, since measurement schema depends on the CV implementation, not yet built |
| created_at | |

### 2.7 Report (`DATA-007`)
| Field | Notes |
|---|---|
| id | |
| user_id | |
| questionnaire_response_id | |
| analysis_result_id | |
| sections | The 11 feature sections (`FR-009`) each with narrative + before/after framing + summary callout (`FR-010`), plus intro/preamble/limitations/recommendations (`FR-011`) — **[Recommendation]**: structured JSON or a child table per feature section |
| pdf_reference | Generated PDF artifact reference (`FR-013`) |
| publish_state | Phase 1: published-on-generation (`BR-002`); field should still exist (not a hardcoded skip) so Phase 2's Draft/Pending Review/Approved/Published states can be added without a schema rework, consistent with the `role` field's forward-compatibility rationale (`AUTH-009`) |
| created_at | |

### 2.8 Payment (`DATA-008`)
| Field | Notes |
|---|---|
| id | |
| user_id | |
| report_id | |
| stripe_reference | Stripe payment/session identifier |
| status | |
| amount | **Must be a configurable value at the time of charge**, not hardcoded — price itself is open (`OQ-002`) |
| created_at | |

## 3. Deferred to Phase 2 (do not model yet)

Per `client_requirements.md` Section 9: Admin/reviewer accounts, report review history, AI-chat Conversation records, generated Visual Assets (hairstyle/outfit/aging images). Do not add tables for these in Phase 1 — the `role` field (§2.1) and `publish_state` field (§2.7) are the only forward-compatibility accommodations the client asked for.

## 4. Migrations

Alembic (`NFR-003`) manages schema evolution. Because several fields above are intentionally under-specified (questionnaire answer shape, measurement shape, report section shape — all recommended as JSON precisely to avoid migration churn while those are still moving), initial migrations should favor flexible JSON columns for content that is still in flux, and normalize into dedicated columns/tables later only once the shape is stable — this is a **[Recommendation]**, not a client instruction, aimed at reducing migration thrash during a from-scratch build.

## 5. Open Questions

| Item | Status |
|---|---|
| Can a user have multiple reports? | Not stated — **[Open Question]** for `report-generation` module. |
| Photo storage mechanism (Supabase Storage vs. other) | Not stated — **[Open Question]**. |
| Password hashing algorithm | Not stated — **[Recommendation]**, see `docs/security.md` §7. |

## 6. Related Documents

- [`docs/authentication.md`](./authentication.md) — behavior of the User/OTP Record/Refresh Token entities.
- [`docs/api-specification.md`](./api-specification.md) — how endpoints read/write these entities.
- [`docs/security.md`](./security.md) — hashing/storage requirements for sensitive fields.
