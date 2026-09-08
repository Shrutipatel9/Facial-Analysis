# Photo Capture Requirements — Angle Set, Requirements Screen & Upload/Camera Flow

## Document Control

| Field | Value |
|---|---|
| Document name | `photo-capture-requirements` |
| Role | Supplementary spec, derived from and subordinate to `client_requirements.md` (the single source of truth). Narrows `FR-005` / `FR-006` / `BR-005` into an implementable photo-capture flow. Should be folded into `UI_UX_REQUIREMENTS.md` and `DATABASE_DESIGN.md` once those documents exist. |
| Version | 1.0 |
| Status | Draft — contains one team decision not yet confirmed by the client (see ASM-004 below); flag for sign-off before treating the angle set as final |
| Last updated | 2026-09-08 |
| Related documents | `client_requirements.md` (FR-005, FR-006, BR-005, ASM-002, DATA-005), `onboarding-questionnaire-extracted.md` (Qoves' own 7-pose reference and 9-item per-photo checklist), `Developer_Project_Overview.md` §3/§6 |

---

## 1. Decision: 3-angle default, not Qoves' 7-pose set (`ASM-004`)

**ASM-004** [Recommendation — not yet confirmed by the client] Phase 1 requests **3 photo angles** as the default capture set, not the 7 poses shown in the client's own Qoves reference video (`onboarding-questionnaire-extracted.md` → "Required Photo Poses"):

| Angle | Instruction shown to user |
|---|---|
| Front | Face the camera head-on with a neutral expression. |
| Left 3/4 | Turn the head to show the left side at roughly a 45° angle. |
| Right 3/4 | Turn the head to show the right side at roughly a 45° angle. |

This is the common minimum convention for this class of facial-analysis app and is enough for MediaPipe/OpenCV to derive the core symmetry, proportion, and profile measurements the report needs (`FR-007`). It intentionally drops Qoves' additional Left/Right full-profile, Frontal Smiling, and Top-of-Head poses to reduce upload friction — those remain available as a later addition, not a removed capability.

**Why this needs client sign-off:** `FR-005`/`FR-006` are client-stated and sourced word-for-word from the Qoves reference material, and the project's documentation rule is that nothing gets invented beyond what's on screen without being labeled a recommendation. The 7-pose set is what the client's own reference product uses, so shipping fewer poses is a scope decision, not a pure implementation detail — note it in the next client check-in alongside `OQ-002`.

**Implementation constraint:** the angle set must be a small, swappable constant (a single list/enum, not scattered magic numbers) — e.g. a `REQUIRED_ANGLES` config value consumed by the upload UI, the per-angle capture step, and the `Photo.angle` column/enum (`DATA-005`) — so moving from 3 angles back to Qoves' 7, or to any other count, is a config change, not a rearchitecture. This should be documented as an explicit extension point in `TECHNICAL_DESIGN.md` when that document exists.

```
# example shape only — not prescribing a language/framework
REQUIRED_ANGLES = ["front", "left_3q", "right_3q"]
```

---

## 2. Flow order

The photo-capture step of `WF-001` (step 3–4) is broken into two screens, run in this order:

1. **Photo Requirements confirmation screen** (`FR-005`, already specified) — the 7-point guideline checklist (remove glasses/hat; natural even lighting; plain white background; hair tied back; no makeup; no neck-covering clothing; no filters), each item paired with a before/after image as in the Qoves reference. The user must review this once, before any capture UI is shown. This screen does not change based on `ASM-004` — the guideline checklist applies to every angle regardless of how many are requested.
2. **Per-angle capture screen(s)** — one step per entry in `REQUIRED_ANGLES` (3 steps under the ASM-004 default), each offering the user a choice of input method before that angle counts as complete:
   - **Upload from device** — file picker / drag-and-drop, accepting the same file types as the reference flow (`.JPG .PNG .DNG .HEIC`).
   - **Use camera** — live in-browser/in-app camera capture, with an on-screen guide overlay for the current angle (e.g., a faint outline for "front," "turn left," "turn right") and a shutter action, then a review/retake step before accepting the shot.
   Both paths converge on the same client-side preview + "retake or continue" step, and both submit through the same backend validation path (`BR-005`) — the input method must not affect what gets validated or stored.

Per-angle progress should be shown (e.g., "1 of 3 photos"), mirroring the "0/9" style progress indicator from the Qoves reference, but counted against `REQUIRED_ANGLES` rather than a fixed 7.

---

## 3. Per-photo capture guidance

Reuse the client's own reference checklist (`onboarding-questionnaire-extracted.md` → "Per-Photo Capture Checklist") as the on-screen guidance shown during capture, since it is more specific and testable than the general BR-005 checks and comes directly from the client's benchmark product:

1. Look straight at the camera (or at the angle indicated for this step)
2. Maintain a neutral expression
3. Remove hair and obstructions from the face
4. Photo taken from an arm's length away
5. Only one head should be visible in the image
6. The head and neck are not cropped out
7. Keep camera focused and not blurry
8. Ensure consistent, even lighting
9. Ensure a plain, clear background

These are UI-facing guidance only; the actual enforcement remains the backend validation defined in `BR-005`/`ASM-002` (exactly one face detected, reasonable frame proportion, no occlusion over eyes/mouth, minimum resolution, basic brightness/exposure) — this list should be the starting point when those thresholds are finalized during development, as `onboarding-questionnaire-extracted.md` already recommends.

---

## 4. Data model note

`DATA-005 Photo` (`client_requirements.md` §9) should constrain its `angle` field to the values in `REQUIRED_ANGLES` (an enum/lookup, not free text), plus a `capture_method` field (`upload` / `camera`) if the team wants to distinguish the two paths in analytics or debugging later — this is a suggestion, not a client-stated requirement, and can be dropped if not useful.

---

## 5. Open item

Add to the open-questions tracking alongside `OQ-002`: **confirm the 3-angle default (ASM-004) with the client**, or get explicit sign-off to diverge from the 7-pose Qoves reference. Until confirmed, treat `REQUIRED_ANGLES` as the working default, not a locked decision.
