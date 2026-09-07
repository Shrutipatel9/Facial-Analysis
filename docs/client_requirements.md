# Client Requirements — AI Facial Analysis Platform

## Document Control

| Field | Value |
|---|---|
| Document name | `client_requirements` |
| Role | **Single source of truth** for the entire project. All other project documents (`PRD.md`, `BRD.md`, `ARCHITECTURE.md`, `TECHNICAL_DESIGN.md`, `API_SPECIFICATION.md`, `DATABASE_DESIGN.md`, `UI_UX_REQUIREMENTS.md`, `AUTHENTICATION.md`, `SECURITY.md`, `TESTING.md`, `DEPLOYMENT.md`, and any future specialized doc) must be derived from and validated against this document, not the other way around. |
| Version | 1.2 |
| Status | Draft — active project, expected to evolve |
| Last updated | 2026-09-07 |
| Supersedes | v1.1 of this document. v1.1 superseded v1.0, which superseded the two earlier "Developer Project Overview" drafts. |
| Sources this document is built from | `Discussion.docx`, `AI Facial Analysis_Proposal.docx`, `AI Facial Analysis Proposal.docx.pdf`, `Estimation.xlsx`, `protocol_report (3).pdf`, `Qoves Onboarding.mp4`, `Screenshot 2026-06-12 at 10.51.25.png` (original requirement materials) + direct client decisions given in conversation on 2026-09-07 (Phase 1 scope decisions, custom-authentication + Redux + documentation-hierarchy requirements, the v1.1 answers resolving most of v1.0's open questions, and the v1.2 tech-stack revision). |

### Change log
- **v1.2 (2026-09-07):** Client-requested tech-stack revision, applied across the stack requirements only — no business/functional/auth-flow requirement changed. Backend framework changed from Python + FastAPI to **TypeScript + Next.js**; because Next.js is a full-stack framework, the frontend is consolidated into the same Next.js application rather than remaining a separate Vite + React app (see `NFR-005` note) — this is a delivery-team interpretation of a brief client instruction ("use typescript and nextjs in backend"), flagged in `ASM-004` for client confirmation. Database changed from Supabase-hosted Postgres to a vendor-neutral **PostgreSQL** requirement (`NFR-002`) — Supabase is no longer part of the stack in any role, which also retires `CON-002`'s Supabase-specific wording (generalized instead, see `CON-002`). ORM changed from SQLAlchemy to **Prisma** (`NFR-004`); migrations changed from Alembic to **Prisma Migrate** (`NFR-003`) — both are delivery-team choices consistent with the new TypeScript stack, not separately client-specified. Frontend state management changed from Redux/Redux Toolkit to **Zustand** (`NFR-006`, `FE-001`, `FE-002`) per client instruction to use "another [library] for store management according to Next.js" — the same layering contract and Redux-not-`localStorage` token-storage decision (`ASM-001`) carry over unchanged, only the library name changes.
- **v1.1 (2026-09-07):** Resolved 8 of the 9 open questions from v1.0 — see Section 14 for the full resolution table. Key changes: authentication flow is now fully specified (email + password, then OTP, for both signup and login); frontend framework confirmed as React + Vite (**superseded in v1.2**); ORM confirmed as SQLAlchemy (**superseded in v1.2**); OTP delivery channel confirmed as email; refresh-token storage confirmed as the Redux store (**library superseded in v1.2 — see Zustand**, storage location/rationale unchanged); OTP/token lifetime values decided (client delegated this to the delivery team "considering security"); hosting decision explicitly deferred (not needed right now); photo-validation thresholds explicitly deferred to development time. Only report pricing (OQ-002) remains genuinely open, at the client's request.
- **v1.0 (2026-09-07):** Initial source-of-truth document, consolidating all original requirement materials plus the client's Phase 1 scope decisions and custom-authentication/Redux/documentation-hierarchy requirements.

### How to use this document
1. Read and understand this document fully before creating or updating any derived document (`PRD.md`, `ARCHITECTURE.md`, etc.).
2. Do not invent requirements not supported here — anything not explicitly stated by the client is labeled **[Recommendation]**, **[Assumption]**, or **[Decided by delivery team]** below, and must stay labeled that way if it's carried into a derived document.
3. Keep derived documents consistent with this source. If a derived document would conflict with something here, that conflict must be surfaced, not silently resolved.
4. When this document changes, re-check every derived document that references the changed requirement ID(s) (see the Traceability Map, Section 13). No derived documents exist yet as of v1.1 — once created, they should be checked against this change log on every future update.
5. Keep business, product, technical, architecture, security, and implementation concerns in separate sections/documents — this file mixes them only because it is the intentionally comprehensive source; derived documents should not.

### Requirement ID legend
`BC-*` Business Context · `FR-*` Functional Requirement · `AUTH-*` Authentication/Authorization · `FE-*` Frontend requirement · `NFR-*` Non-functional/Technical · `BR-*` Business Rule · `WF-*` Workflow · `DATA-*` Data entity · `CON-*` Constraint · `ASM-*` Assumption/Recommendation (not client-stated) · `OQ-*` Open question

---

## 1. Business Context (`BC-*`)

- **BC-001** [Client-stated] The product is an AI-driven facial aesthetics analysis platform, conceptually similar to Qoves.com — an existing real-world service that produces expert, cephalometric-based "aesthetic protocol" reports for clients.
- **BC-002** [Client-stated] The business problem being solved: Qoves-style services depend on human experts manually producing each report, which is slow and expensive. This platform automates that process with computer vision + AI so a similar product can be sold at consumer scale and price point.
- **BC-003** [Client-stated] The commercial model is a paywalled report: a user completes onboarding and photo upload, an AI-generated report is produced, and the user must pay to unlock/view the full report.
- **BC-004** [Client-stated] Project Sponsor: Jay Michaels (paying client). Delivery team: Crest Infosystems (Tejash Patel — PM, Jainesh Bhatt — Business Manager).
- **BC-005** [Client-stated] The client wants to be able to keep extending this codebase with their own team after delivery, using AI-assisted ("vibe coding") development tools — this drives a preference for clean, modular, well-documented code over clever/opaque implementations.
- **BC-006** [Client-stated] The project is explicitly being delivered in phases. Phase 1 is the current, scoped build; several features are deliberately deferred to a later phase (see Section 2 and Section 12).

---

## 2. Project Scope

### 2.1 Phase 1 — build now
- Landing page (marketing entry point).
- Custom backend-controlled user authentication: email + password + OTP, for both signup and login (see Section 5 — this replaces the earlier plan to use Supabase Auth directly).
- Onboarding questionnaire (23 questions, branching logic, ends in a mandatory disclaimer).
- Photo upload with guideline checklist UI **and** enforced backend validation (exact thresholds decided during development, see ASM-002).
- AI facial analysis engine (MediaPipe + OpenCV for measurement, OpenAI for narrative), built from scratch.
- Report generation (11-feature structured report, PDF export).
- Auto-publish of the generated report (no manual review gate in Phase 1).
- Payment (Stripe, one-time payment per report) gating full report access. Exact price still open (OQ-002).
- User dashboard (report history/status, download, payment history, profile).

### 2.2 Phase 2 — explicitly deferred, do not build now
- Admin panel and the full report status workflow: Draft → Pending Review → Approved → Published.
- Email notifications (SendGrid).
- PayPal as a second payment method.
- Meta Pixel + Google Tag Manager tracking.
- AI Visual Features: 5 AI-generated hairstyle variations, 5 AI-generated outfit variations, 3-image aging simulation (Now / +10 yrs / +20 yrs).
- AI Beauty Assistant — a ChatGPT-based chat where the user asks questions about their own report.
- Formal data-retention/privacy policy definition.

---

## 3. Actors & Roles (`BC-*` / `AUTH-*`)

- **End User** — signs up/logs in, completes onboarding, uploads photos, pays, views/downloads their own report(s). Phase 1's only functional role.
- **Admin** — Phase 2 only. Will review, edit, verify, and publish AI-generated reports, and manage recommendation content. Not built in Phase 1, but the data model must not preclude adding this role later (see AUTH-009).
- **Project Sponsor** — Jay Michaels; the business decision-maker for scope and requirements.
- **Delivery team** — Crest Infosystems.
- **System/third-party actors** — OpenAI (Vision/GPT for narrative analysis), MediaPipe/OpenCV (local CV libraries, not third-party services), Stripe (payments), a PostgreSQL database (hosting provider not yet decided, see `NFR-010`; **not** Supabase as of v1.2, and never used for authentication regardless of hosting provider — see Section 5), an email-based OTP delivery provider (channel confirmed as email; specific provider e.g. SendGrid/SES/Postmark still to be chosen during development).

---

## 4. Functional Requirements (`FR-*`)

| ID | Requirement | Source |
|---|---|---|
| FR-001 | Landing page with a clear call-to-action to begin onboarding. | Client-stated |
| FR-002 | User account creation and login (see Section 5 for the full authentication spec). | Client-stated |
| FR-003 | 23-question onboarding questionnaire with branching logic, covering medical conditions/medications, self-perceived best feature, comfort with specific recommendation types (e.g. weight loss), frequency of appearance-related thoughts, and similar lifestyle/self-perception questions. | Client-stated (from Qoves onboarding reference) |
| FR-004 | The questionnaire must end with a mandatory, checkbox-gated disclaimer: user confirms no Body Dysmorphic Disorder–related concerns and understands recommendations are informational only, not medical guidance. The questionnaire cannot be submitted without this being checked. | Client-stated (from Qoves onboarding reference) |
| FR-005 | Photo upload supporting multiple angles, presented alongside a 7-point guideline checklist: remove glasses/hat; use natural, even lighting; use a plain white background; tie back long hair; remove makeup; avoid neck-covering clothing; do not use filters. | Client-stated (from Qoves onboarding reference) |
| FR-006 | Photo validation must be **enforced**, not just displayed as a checklist — see BR-005 and ASM-002 for the enforcement approach (exact thresholds decided during development). | Client-stated |
| FR-007 | Facial landmark detection and mathematical measurement performed via MediaPipe + OpenCV, built new (no existing engine to reuse). | Client-stated |
| FR-008 | AI-generated narrative explanations and personalized recommendations produced via OpenAI (Vision/GPT), using both the CV measurements **and** the questionnaire answers as context — not photo analysis alone. | Client-stated |
| FR-009 | Generated report must cover exactly 11 facial features: Hair, Eyebrows, Eyes, Nose, Cheeks, Jaw, Lips, Chin, Skin, Neck, Ears. | Client-stated (from Qoves sample report) |
| FR-010 | Each feature section includes: a narrative analysis, a before/after or "projected potential" framing, and a short summary callout. | Client-stated (from Qoves sample report) |
| FR-011 | The report as a whole includes an introduction, an "Understanding Your Results" preamble, an explicit limitations/disclaimer section, and a closing recommendations section synthesizing all findings. | Client-stated (from Qoves sample report) |
| FR-012 | Recommendations must span at-home/lifestyle, OTC/skincare-active, and optional in-clinic tiers, always framed as informational and never prescriptive, with "consult a qualified professional" language. | Client-stated (from Qoves sample report) |
| FR-013 | Report is exportable as a downloadable PDF, branded with the team's own in-house design (no client-supplied branding assets exist yet). | Client-stated |
| FR-014 | In Phase 1, the generated report auto-publishes and is immediately available to the user — no manual admin review/approval step exists yet. | Client-stated |
| FR-015 | The full report is inaccessible until the user completes a successful payment (Stripe). A teaser/results page may be shown pre-payment. | Client-stated |
| FR-016 | One-time payment per report is the recommended model (no subscription, no PayPal in Phase 1). | Recommendation — price point explicitly still open, see OQ-002 |
| FR-017 | User dashboard showing report history/status, report download, payment history, and basic profile management. | Client-stated |

---

## 5. Authentication & Authorization Requirements (`AUTH-*` / `FE-*`)

This section reflects a **direct client decision that overrides the earlier recommendation to use Supabase Auth**. As of v1.2, Supabase is no longer part of the stack in any role (see `NFR-002`) — the constraint below is generalized to any third-party auth-as-a-service, not specific to Supabase. As of v1.1, the authentication flow itself is fully specified (see WF-002).

### 5.1 Backend authentication requirements
| ID | Requirement | Source |
|---|---|---|
| AUTH-001 | Authentication must be a custom, backend-controlled flow. Do **not** use Supabase Auth, Auth0, Firebase Auth, or any third-party auth-as-a-service as the application's direct authentication mechanism. | Client-stated |
| AUTH-002 | JWT-based authentication using an access token + refresh token pair. | Client-stated |
| AUTH-003 | Both **signup** and **login** follow the same two-step shape: (1) email + password submitted first; (2) once that step succeeds, an OTP is sent and must be verified; only after OTP verification does signup/login complete and tokens get issued. OTP is a mandatory second step in both flows, not an alternative to the password step. | Client-stated (confirmed v1.1) — see WF-002 for the full flow |
| AUTH-004 | Secure token generation, validation, refresh, and expiration handling, fully owned by the backend. | Client-stated |
| AUTH-005 | Backend APIs are solely responsible for authentication and authorization — no delegation to a third-party identity provider. | Client-stated |
| AUTH-006 | The system must properly handle: login, OTP verification, logout, token refresh, and session expiry as distinct, well-defined flows. | Client-stated |
| AUTH-007 | Protected API routes/endpoints must validate the JWT access token before allowing access. | Client-stated |
| AUTH-008 | Role/permission handling must exist where required. | Client-stated |
| AUTH-009 | The user data model must carry a `role` field (Phase 1: only `"user"` populated) so an `"admin"` role can be introduced in Phase 2 without a schema rework. | Recommendation, consistent with the Phase 2 admin-panel plan (Section 2.2) |
| AUTH-010 | Refresh tokens must be revocable server-side (a store of issued/rotated refresh tokens, keyed by a token identifier, not the raw token) so logout and session-expiry actually invalidate a session, not just let a client discard a token it still holds. | Decided by delivery team, client instruction: "decide by yourself considering security" (resolves former OQ-003, in part) |
| AUTH-011 | OTP security parameters: **10-minute expiry**, **60-second resend cooldown**, **5 failed attempts** before a **15-minute lockout**, OTP value stored **hashed**, never in plaintext. | Decided by delivery team, client instruction: "decide by yourself considering security" (resolves former OQ-003) |
| AUTH-012 | Token lifetimes: **access token — 15 minutes**; **refresh token — 30 days**, rotated on every use, with reuse detection (if a already-rotated-out refresh token is presented again, the entire token family is revoked and the user is forced to re-authenticate, since this indicates possible theft). | Decided by delivery team, client instruction: "decide by yourself considering security" (resolves former OQ-003) |

### 5.2 Frontend token management requirements
| ID | Requirement | Source |
|---|---|---|
| FE-001 | Authentication state managed via **Zustand** (superseded in v1.2 — was Redux / Redux Toolkit). | Client-stated (v1.2) |
| FE-002 | The authenticated user's token/session information (access token **and** refresh token) is stored in the Zustand auth store (superseded in v1.2 — was the Redux store; storage location/rationale is otherwise unchanged). Explicitly **not** `localStorage` — confirmed directly by the client. See ASM-001 for the residual security note this still carries. | Client-stated (confirmed v1.1, library superseded v1.2, resolves former OQ-009) |
| FE-003 | Authentication state and token handling must be centralized (a single auth store/service), not duplicated across components. | Client-stated |
| FE-004 | The access token must be automatically attached to authenticated API requests (e.g., via a centralized API client/interceptor). | Client-stated |
| FE-005 | Token expiration must be handled automatically using the refresh-token flow — an expired access token should trigger a silent refresh-and-retry, transparent to the UI, where possible. | Client-stated |
| FE-006 | When the session becomes invalid (refresh fails, token revoked, etc.), the app must clear authentication state and redirect the user to log in again. | Client-stated |
| FE-007 | Authentication logic must be kept separate from UI components — UI components should never talk to auth APIs or handle tokens directly. | Client-stated |

### 5.3 Required architectural separation
The client has specified this exact layering, and it must be preserved in any derived architecture/technical-design document:

```
UI → Zustand Auth Store → API Client → Backend Auth APIs → JWT/OTP Services
```

(Superseded in v1.2 — the store layer was previously named "Redux Auth Store"; the contract itself — single source of truth, no direct UI-to-API/token access, centralized API client — is unchanged, only the library changed from Redux to Zustand.)

- **UI** — presentational components; no direct API or token access.
- **Zustand Auth Store** — single source of truth for auth state (user, both tokens, auth status) on the frontend; the confirmed storage location for tokens (FE-002).
- **API Client** — centralized HTTP client that reads tokens from the Zustand store, attaches them to requests, and handles refresh-on-401.
- **Backend Auth APIs** — Next.js Route Handlers (TypeScript) for register (email+password → OTP), login (email+password → OTP), OTP verify, refresh, logout, and protected-route middleware/helpers for JWT validation. (Superseded in v1.2 — previously FastAPI endpoints.)
- **JWT/OTP Services** — backend-internal services for token issuance/validation and OTP generation/verification (email delivery), decoupled from the route handlers themselves.

---

## 6. Non-Functional / Technical Expectations (`NFR-*`)

| ID | Requirement | Source |
|---|---|---|
| NFR-001 | Backend: **TypeScript + Next.js** (superseded in v1.2 — was Python + FastAPI). | Client-stated (v1.2) |
| NFR-002 | Database: **PostgreSQL**, vendor-neutral (superseded in v1.2 — was Supabase-hosted Postgres specifically; Supabase is no longer part of the stack in any role, including as auth — see `CON-002`). Hosting provider for the Postgres instance remains undecided, consistent with `NFR-010`. | Client-stated (v1.2) |
| NFR-003 | Database migrations: **Prisma Migrate** (superseded in v1.2 — was Alembic; changed as a consequence of the ORM change below, not separately client-specified). | Decided by delivery team (v1.2), consistent with `NFR-004` |
| NFR-004 | ORM: **Prisma** (superseded in v1.2 — was SQLAlchemy; SQLAlchemy is Python-only and cannot run on the new TypeScript backend). | Decided by delivery team (v1.2), consequence of `NFR-001` |
| NFR-005 | Frontend framework: **Next.js** (superseded in v1.2 — was React + Vite as a separate app, confirmed in v1.1; consolidated into the same Next.js application introduced by `NFR-001` since Next.js is a full-stack framework). This consolidation is a delivery-team interpretation of the client's brief instruction, not explicitly confirmed — see `ASM-004`. | Client-stated (v1.2, backend framework); delivery-team interpretation (frontend consolidation) — see `ASM-004` |
| NFR-006 | Frontend state management: **Zustand**, at minimum for authentication state (Section 5.2) (superseded in v1.2 — was Redux / Redux Toolkit). Client instruction: use "another [library] for store management according to Next.js." | Client-stated (v1.2) |
| NFR-007 | Facial analysis engine: MediaPipe + OpenCV, built from scratch. | Client-stated |
| NFR-008 | AI narrative/recommendation generation: OpenAI (Vision + GPT). | Client-stated |
| NFR-009 | Payments: Stripe in Phase 1; PayPal deferred to Phase 2. | Client-stated |
| NFR-010 | Hosting: explicitly **not decided right now** — the client confirmed there is no current need to settle on a hosting platform. The earlier assumption of Replit (from the original pre-negotiation materials) is no longer treated as active; hosting is an open item to revisit later, not a blocker today. | Client-confirmed (v1.1, resolves former OQ-007 by deferring it) |
| NFR-011 | Code must be clean, modular, and well-documented to support the client's own team continuing development post-handoff. | Client-stated |
| NFR-012 | OTP delivery channel: **email**, confirmed. Specific provider (e.g. SendGrid, AWS SES, Postmark) still to be picked during development — not a blocking decision. | Client-confirmed channel (v1.1, resolves former OQ-004); provider selection delegated to dev team |

---

## 7. Business Rules (`BR-*`)

- **BR-001** [Client-stated] The full report is inaccessible until payment succeeds.
- **BR-002** [Client-stated] In Phase 1, a generated report auto-publishes immediately — there is no Draft/Pending Review/Approved gate. That workflow returns in Phase 2 once the Admin panel exists.
- **BR-003** [Client-stated] The BDD/informational-only disclaimer checkbox is a hard, non-optional gate before questionnaire submission.
- **BR-004** [Recommendation] Because Phase 1 has no admin safety net before publishing, the AI pipeline should not run — and no report should be generated — from photos that fail validation (BR-005), to avoid auto-publishing a low-quality report straight to a paying user.
- **BR-005** [Client-stated + delegated mechanism] Photo validation must be enforced by the backend, not left as a self-attestation checklist. Recommended checks: exactly one face detected; face occupies a reasonable proportion of the frame; no obvious occlusion over eyes/mouth (glasses/hat); minimum resolution; basic brightness/exposure check. The client confirmed exact thresholds should be decided during development (ASM-002), not specified up front.
- **BR-006** [Client-stated] Third-party usage costs (OpenAI, Stripe, the PostgreSQL hosting provider once chosen, and the email/OTP delivery provider) are the client's own responsibility, not included in any development estimate. (Supabase-specific wording removed in v1.2 — see `NFR-002`.)
- **BR-007** [Client-stated] No committed timeline or re-estimate is being produced at this stage; Phase 1 is scoped by feature list (Sections 2 and 4), not by hours or dollars, until the client asks otherwise.
- **BR-008** [Client-stated] Report content must reflect exactly 11 features (see FR-009) — this is a fixed structural rule, not a suggestion, derived directly from the reference Qoves sample report the client benchmarked their own draft report against.

---

## 8. Workflows (`WF-*`)

### WF-001 — End-to-end user journey (Phase 1)
1. Landing page → sign up / log in.
2. Onboarding: 23-question branching questionnaire → BDD/informational-only disclaimer checkbox → submit.
3. Photo Requirements confirmation screen (7-point checklist shown to user).
4. Photo upload (multi-angle) → backend validation (BR-005) → accept or reject with reason.
5. AI processing: MediaPipe/OpenCV landmark & measurement extraction → OpenAI narrative generation using measurements + questionnaire context.
6. Report assembled and auto-published (BR-002).
7. Results page shown with a teaser; full report locked (BR-001).
8. Stripe payment → on success, full report unlocked.
9. Dashboard: report history/status, PDF download, payment history, profile.

### WF-002 — Authentication flow (confirmed, v1.1)
Both **signup** and **login** follow the identical two-step shape:

1. **Step 1 — Email + password.**
   - *Signup:* user submits email + password → backend validates the email isn't already registered, hashes the password, creates a pending/unverified user record.
   - *Login:* user submits email + password → backend validates the credentials against the stored hash.
   - In both cases, on success the backend does **not** yet issue tokens — it proceeds to Step 2.
2. **Step 2 — OTP verification.** Backend generates an OTP, stores it hashed with an expiry (AUTH-011), and emails it to the user (NFR-012). The user submits the OTP.
   - Backend validates the submitted OTP against the stored hash and expiry, and against the attempt/lockout limits in AUTH-011.
   - On success: for signup, the account is marked verified; for login, the session is confirmed. Either way, the backend now issues a JWT access token + refresh token pair (AUTH-002, AUTH-012) and the flow completes as a successful signup or login.
   - On failure: an attempt counter increments; after 5 failed attempts, a 15-minute lockout applies (AUTH-011) before another OTP can be requested.
3. **Authenticated requests:** frontend API client attaches the access token to each request (FE-004); backend validates the JWT on protected routes (AUTH-007).
4. **Token refresh:** when the access token expires (15 minutes, AUTH-012), the frontend calls the refresh endpoint with the refresh token → backend validates it against its revocation store (AUTH-010), issues a new access token and rotates the refresh token → frontend updates the Zustand auth store transparently (FE-005). If the presented refresh token was already rotated out (reuse), the whole token family is revoked and the user must log in again.
5. **Logout:** frontend calls a logout endpoint → backend revokes the refresh token server-side (AUTH-010) → frontend clears the Zustand auth store (FE-006).
6. **Session expiry / invalid session:** if a refresh attempt fails (expired, revoked, or reused/rotated-out refresh token), the backend returns an auth error → frontend clears the Zustand auth store and redirects to login (FE-006).

---

## 9. Data Entities (`DATA-*`, high-level — full schema belongs in `DATABASE_DESIGN.md`)

- **DATA-001 User** — email, hashed password, verification status, `role` (AUTH-009), timestamps.
- **DATA-002 OTP Record** — linked to a user (or a pending signup), hashed OTP value, purpose (signup/login), expiry, attempt count, consumed flag.
- **DATA-003 Refresh Token / Session Record** — token identifier (not the raw token), user reference, issued/expiry timestamps, revoked flag, rotation lineage (for reuse detection per AUTH-012).
- **DATA-004 Questionnaire Response** — the 23 branching answers, linked to a user.
- **DATA-005 Photo** — per-angle uploads, validation status/results (BR-005).
- **DATA-006 Facial Analysis Result** — per-feature landmark/measurement output from MediaPipe/OpenCV, linked to a photo set.
- **DATA-007 Report** — the 11 feature sections (FR-009), generated PDF artifact reference, publish state (Phase 1: published-on-generation per BR-002), linked to a user, questionnaire response, and analysis result.
- **DATA-008 Payment** — Stripe payment/session identifier, status, amount, linked user/report.
- **Deferred to Phase 2:** Admin/reviewer accounts, report review history, AI-chat Conversation records, generated Visual Assets (hairstyle/outfit/aging images).

---

## 10. Constraints (`CON-*`)

- **CON-001** [Client-stated] No existing codebase exists — this is a from-scratch build; nothing from the original pre-negotiation "existing MVP" claims applies.
- **CON-002** [Client-stated, generalized in v1.2] No third-party authentication-as-a-service (e.g. Supabase Auth, Auth0, Firebase Auth) may be used as the application's authentication mechanism. (Prior to v1.2 this was worded Supabase-specifically, since Supabase was the database vendor at the time; Supabase is no longer part of the stack in any role as of v1.2 — see `NFR-002` — but the underlying rule is unchanged and generalizes to any such vendor.)
- **CON-003** [Client-stated] No client-supplied branding/design assets exist yet for Phase 1 — the team owns UI/branding decisions for now.
- **CON-004** [Client-stated] Third-party service costs (OpenAI, Stripe, the PostgreSQL hosting provider once chosen, email/OTP provider) are billed to and owned by the client, not bundled into any dev estimate. (Supabase-specific wording removed in v1.2 — see `NFR-002`.)
- **CON-005** [Client-stated] No committed delivery timeline or dollar estimate exists at this stage, and none has been requested.
- **CON-006** [Recommendation] Because Phase 1 auto-publishes reports with no admin safety net, the enforced photo-validation step (BR-005) is a harder requirement here than it would be in a workflow with human review downstream.
- **CON-007** [Client-stated] Hosting platform is explicitly undecided and not currently needed — do not assume Replit or any other specific host without a future decision.

---

## 11. Assumptions & Recommendations Not Yet Confirmed by the Client (`ASM-*`)

These are flagged separately per the documentation rules — they must stay visibly labeled as non-client-stated in any derived document until confirmed. As of v1.1, most former assumptions were resolved into confirmed requirements (see the Section 14 resolution table); the two below remain genuinely open or partially open.

- **ASM-001 — Client-side (Zustand) token storage, residual XSS note.** The client has now explicitly confirmed (FE-002) that both the access token and refresh token are stored in a client-side JS store, not `localStorage` — originally specified as Redux, the library itself was superseded by Zustand in v1.2 (the storage-location decision and its rationale are unchanged). This avoids the specific risk of a token persisting across sessions/tabs in generic browser storage that many XSS payloads scrape by default. It does **not** fully eliminate XSS exposure in principle — any script running in the page's own JS context can, in theory, still reach in-memory store state. This is now a settled implementation decision, not an open question, but it is worth documenting explicitly in `SECURITY.md` as an accepted trade-off, with standard XSS hardening (CSP, output encoding, dependency hygiene) treated as the actual mitigation layer.
- **ASM-002 — Photo validation rule set.** The specific automated checks in BR-005 are this document's recommendation; the client confirmed the exact thresholds should be finalized during development rather than specified now. Should be documented in `TECHNICAL_DESIGN.md`/`TESTING.md` once implemented.
- **ASM-003 — Payment model.** One-time payment per report (FR-016) is a recommendation; pricing itself remains explicitly open (OQ-002).
- **ASM-004 — Next.js consolidation (v1.2).** The client's v1.2 instruction was "use typescript and nextjs in backend." Because Next.js is a full-stack React framework (it does not exist as a backend-only tool the way FastAPI does), the delivery team has interpreted this as consolidating the previously-separate React + Vite frontend into the same Next.js application, rather than running Next.js purely as an API server behind an unchanged standalone Vite frontend. This interpretation is **not explicitly confirmed by the client** and should be verified at the next opportunity. If the client actually intended to keep a separate Vite frontend calling a Next.js-only API backend, `NFR-005` and every derived document's architecture/folder-structure content built on this assumption will need to be revised.

---

## 12. Out of Scope for Phase 1

Restated from Section 2.2 for clarity when this document is used to scope a sprint or derived PRD: Admin panel, full report status workflow (Draft/Pending Review/Approved/Published), email notifications, PayPal, Meta Pixel/GTM tracking, AI Visual Features (hairstyle/outfit/aging generation), AI Beauty Assistant chat, formal data-retention/privacy policy.

---

## 13. Traceability Map — how this document feeds derived documents

| Derived document | Primary requirement IDs to draw from |
|---|---|
| `PRD.md` | `FR-*`, `WF-001`, Section 2 (scope) |
| `BRD.md` | `BC-*`, `BR-*`, Section 2 (scope), `CON-*` |
| `ARCHITECTURE.md` | `NFR-*`, Section 5.3 (layering), `WF-002` |
| `TECHNICAL_DESIGN.md` | `NFR-*`, `AUTH-*`, `FE-*`, `ASM-*` |
| `API_SPECIFICATION.md` | `AUTH-001`–`AUTH-012`, `WF-002` (endpoint sequence), `FR-*` (endpoints implied by each functional requirement) |
| `DATABASE_DESIGN.md` | `DATA-*` |
| `UI_UX_REQUIREMENTS.md` | `FR-003`–`FR-005`, `FE-*`, Qoves reference materials |
| `AUTHENTICATION.md` | `AUTH-*`, `FE-*`, `WF-002`, `ASM-001` |
| `SECURITY.md` | `AUTH-010`–`AUTH-012`, `ASM-001`, `BR-005`/`CON-006` |
| `TESTING.md` | Every `FR-*`/`AUTH-*`/`BR-*` should map to at least one test case when this doc is written |
| `DEPLOYMENT.md` | `NFR-010`/`CON-007` (hosting, currently undecided), `CON-002` (no third-party auth-as-a-service), `NFR-001`–`NFR-003` |

Any derived document should cite requirement IDs from this table so a later change here can be traced forward to what it affects.

---

## 14. Open Questions (`OQ-*`)

### Resolved in v1.1
| ID | Original question | Resolution |
|---|---|---|
| OQ-001 | Login mechanism shape (password vs. OTP-only vs. both) | **Resolved** — both signup and login use email + password first, then a mandatory OTP verification step, then completion. See AUTH-003, WF-002. |
| OQ-003 | Exact token/OTP lifetimes and thresholds | **Resolved** — client delegated this to the delivery team "considering security"; concrete values set in AUTH-010/011/012. |
| OQ-004 | OTP delivery channel/provider | **Resolved (channel)** — email confirmed. Specific provider still to be picked during development (not blocking). See NFR-012. |
| OQ-005 | ORM confirmation | **Resolved (v1.1), superseded (v1.2)** — SQLAlchemy confirmed in v1.1, replaced by Prisma in v1.2 as a consequence of the TypeScript backend change. See NFR-004. |
| OQ-006 | Frontend framework | **Resolved (v1.1), superseded (v1.2)** — React + Vite confirmed in v1.1, consolidated into Next.js in v1.2. See NFR-005, ASM-004. |
| OQ-007 | Hosting reconfirmation | **Resolved by deferral** — client confirmed no hosting decision is needed right now. See NFR-010, CON-007. |
| OQ-008 | Exact automated photo-validation thresholds | **Resolved by deferral** — client confirmed these should be decided during development. See ASM-002. |
| OQ-009 | Refresh token storage (client-side store vs. `httpOnly` cookie) | **Resolved** — client confirmed a client-side store (originally Redux, superseded by Zustand in v1.2 — see NFR-006), explicitly not `localStorage`. See FE-002, ASM-001. |

### Still open
| ID | Question | Status |
|---|---|---|
| OQ-002 | Report price / pricing model specifics | **Explicitly kept open by the client** ("keep this open question currently"). FR-016/ASM-003 (one-time payment per report) stands as the working model; the price itself should remain a configurable value, not hardcoded, until this is resolved. |

---

### Summary
This document is the authoritative, single source of truth for the AI Facial Analysis platform. Phase 1 delivers: a from-scratch build with custom backend-controlled authentication (email + password, then mandatory OTP verification, for both signup and login; JWT access + refresh tokens with rotation and reuse detection; Zustand-managed frontend auth state — explicitly not `localStorage`; and a strict UI → Zustand Auth Store → API Client → Backend Auth APIs → JWT/OTP Services layering), a 23-question onboarding flow, enforced photo validation (thresholds to be finalized during development), a MediaPipe/OpenCV + OpenAI facial analysis pipeline, an 11-feature auto-published report with PDF export, Stripe-gated payment, and a basic user dashboard, on a single TypeScript + Next.js full-stack application (frontend and backend consolidated, see `ASM-004`) with Prisma/Prisma Migrate over a vendor-neutral PostgreSQL database. Admin functionality, the full report review workflow, email/PayPal/tracking, and AI visual/chat features are explicitly Phase 2. As of v1.2, only report pricing (OQ-002) remains open at the client's explicit request, and the Next.js frontend/backend consolidation reading (`ASM-004`) awaits explicit client confirmation; hosting and a few implementation-level thresholds are deferred (not blocking) rather than open.
