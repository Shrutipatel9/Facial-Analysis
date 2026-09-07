# Business Requirements Document (BRD)

**Source of truth:** [`client_requirements.md`](./client_requirements.md) — this document restates only the business-facing subset of that source (`BC-*`, `BR-*`, `CON-*`, Section 2) in BRD form. If anything here conflicts with `client_requirements.md`, the source document wins.

**Status:** Draft, derived from `client_requirements.md` v1.1 (2026-09-07).

---

## 1. Purpose

Define the business rationale, scope boundaries, stakeholders, and commercial model for the AI Facial Analysis platform, so that product, architecture, and delivery decisions can be checked against a consistent business framing.

## 2. Business Context

- **BC-001/BC-002** — The product automates a service pattern (Qoves.com-style expert cephalometric aesthetic reports) that today depends on manual expert labor. Automating report production with computer vision + AI is the core business lever: it lets a similar product be sold at consumer scale and price point instead of bespoke-expert scale and price.
- **BC-003** — Commercial model: paywalled report. Users complete onboarding and photo upload for free; the AI-generated report is produced but locked until payment.
- **BC-004** — Stakeholders:
  | Role | Party |
  |---|---|
  | Project Sponsor (business decision-maker) | Jay Michaels |
  | Delivery team | Crest Infosystems (Tejash Patel — PM, Jainesh Bhatt — Business Manager) |
- **BC-005** — Post-handoff, the client's own team will continue extending the codebase using AI-assisted ("vibe coding") tools. This is the business reason behind the technical preference (see `docs/architecture.md`) for clean, modular, conventional code over clever/opaque implementations — it is a maintainability requirement with a business cause, not just an engineering preference.
- **BC-006** — Delivery is explicitly phased. This BRD, and every other project document, describes **Phase 1 (build now)** unless a section is explicitly marked Phase 2.

## 3. Scope

### 3.1 Phase 1 — in scope now
Landing page · custom email+password+OTP authentication · 23-question branching onboarding questionnaire with mandatory disclaimer · photo upload with enforced backend validation · from-scratch MediaPipe/OpenCV + OpenAI analysis engine · 11-feature report with PDF export · auto-publish (no review gate) · Stripe one-time payment gating full report access · user dashboard.

See `docs/prd.md` for the functional breakdown and `docs/phase-wise-requirements.md` for how this is sequenced into implementation phases.

### 3.2 Phase 2 — explicitly deferred
Admin panel and full report status workflow (Draft → Pending Review → Approved → Published) · email notifications (SendGrid) · PayPal · Meta Pixel + GTM tracking · AI Visual Features (hairstyle variations, outfit variations, aging simulation) · AI Beauty Assistant chat · formal data-retention/privacy policy.

**Rule for all future work:** do not build anything in §3.2 as part of the current engagement without an explicit scope change from the client.

## 4. Actors

| Actor | Description | Phase |
|---|---|---|
| End User | Signs up/logs in, completes onboarding, uploads photos, pays, views/downloads own report(s). The only functional role in Phase 1. | 1 |
| Admin | Reviews/edits/verifies/publishes AI-generated reports, manages recommendation content. Not built in Phase 1, but the data model reserves a `role` field (`AUTH-009`) so this can be added later without a schema rework. | 2 (data model prepared in Phase 1) |
| Project Sponsor | Jay Michaels — business decision-maker for scope/requirements. | — |
| Delivery team | Crest Infosystems. | — |
| Third-party systems | OpenAI (narrative analysis), MediaPipe/OpenCV (local libraries, not a service), Stripe (payments), a PostgreSQL database (hosting provider TBD, **not** auth — Supabase no longer part of the stack as of v1.2, see `docs/architecture.md` §1), an email-based OTP provider (channel confirmed, specific vendor TBD). | 1 |

## 5. Business Rules

| ID | Rule |
|---|---|
| BR-001 | Full report is inaccessible until payment succeeds. |
| BR-002 | Phase 1 reports auto-publish immediately; no Draft/Pending Review/Approved gate exists until Phase 2. |
| BR-003 | The BDD/informational-only disclaimer checkbox is a hard, non-optional gate before questionnaire submission. |
| BR-004 [Recommendation] | Because Phase 1 has no admin safety net before publishing, the AI pipeline must not run on photos that fail validation — this avoids auto-publishing a low-quality report straight to a paying user. |
| BR-005 | Photo validation is enforced by the backend, not a self-attestation checklist. Recommended checks: exactly one face detected; face occupies a reasonable frame proportion; no obvious occlusion (glasses/hat) over eyes/mouth; minimum resolution; basic brightness/exposure check. Exact thresholds are deliberately deferred to development time (`ASM-002`). |
| BR-006 | Third-party usage costs (OpenAI, Stripe, the PostgreSQL hosting provider once chosen, email/OTP provider) are the client's own responsibility, not included in any development estimate. |
| BR-007 | No committed timeline or re-estimate is being produced; Phase 1 is scoped by feature list, not hours/dollars, until the client asks otherwise. |
| BR-008 | Report content must cover exactly 11 features (`FR-009`) — a fixed structural rule benchmarked against a reference Qoves sample report, not a suggestion. |

## 6. Constraints

| ID | Constraint |
|---|---|
| CON-001 | From-scratch build — no existing codebase/MVP claims apply. |
| CON-002 | No third-party authentication-as-a-service (e.g. Supabase Auth, Auth0, Firebase Auth) may be used as the application's authentication mechanism (generalized in v1.2; Supabase itself is no longer part of the stack in any role). |
| CON-003 | No client-supplied branding/design assets exist yet; the delivery team owns UI/branding decisions for Phase 1 (see `docs/ui-ux-design.md`). |
| CON-004 | Third-party service costs are billed to and owned by the client. |
| CON-005 | No committed delivery timeline or dollar estimate exists, and none has been requested. |
| CON-006 [Recommendation] | Because Phase 1 auto-publishes with no admin safety net, enforced photo validation (`BR-005`) is a harder requirement here than it would be with human review downstream. |
| CON-007 | Hosting platform is explicitly undecided and not currently needed — do not assume any specific host. |

## 7. Success Criteria (Phase 1)

Derived from scope, not separately client-stated as KPIs — treat as **[Assumption]** pending client confirmation:

- A user can complete the full journey in `WF-001` (landing → auth → onboarding → photo upload → AI processing → report → payment → dashboard) without manual intervention.
- Reports consistently cover all 11 required features (`BR-008`).
- No report is generated from photos that fail backend validation (`BR-004`).
- Authentication meets the security posture in `docs/authentication.md` (OTP/token lifetimes, rotation, reuse detection) with no manual/admin exception path.

## 8. Open Business Questions

| ID | Question | Status |
|---|---|---|
| OQ-002 | Report price / pricing model specifics | Explicitly kept open by the client. One-time payment per report (`FR-016`/`ASM-003`) is the working model; price must remain a configurable value, not hardcoded, until resolved. See `docs/prd.md` §Payment and `docs/api-specification.md` §Payment for how this is kept configurable. |

## 9. Related Documents

- [`docs/prd.md`](./prd.md) — functional/product requirements derived from this business scope.
- [`docs/phase-wise-requirements.md`](./phase-wise-requirements.md) — how Phase 1 scope is sequenced into implementation phases.
- [`docs/architecture.md`](./architecture.md) — technical realization of `BC-005`'s maintainability requirement and the third-party integrations in §4.
