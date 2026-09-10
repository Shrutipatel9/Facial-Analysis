# Cross-Photo Identity Validation — Design Contract

## Document Control

| Field | Value |
|---|---|
| Document name | `photo-identity-validation-spec` |
| Role | Supplementary spec, derived from and subordinate to `client_requirements.md` (the single source of truth). Narrows `BR-005`/`ASM-010` into the exact algorithm/state-management contract for the cross-photo "same person" check, so a future change to this logic can be checked against a written spec instead of re-derived from scratch. |
| Version | 1.1 |
| Status | Active — describes the implementation as it exists today (`v1.20` of `client_requirements.md`) |
| Last updated | 2026-09-10 |
| Related documents | `client_requirements.md` (`FR-006`, `BR-005`, `ASM-010`), `photo_capture_spec.md` (the 3-angle set this operates on), `D:\zzz\photo-upload-validation\plans.md` (implementation history/revision notes) |

---

## 1. The core rule: every validation is computed fresh, from scratch, every time

There is **no persisted validation state** anywhere in this system — no "this photo was previously wrong" flag, no merge of old and new results. Every time the three current photos need to be compared, the full comparison runs again from whatever bytes are *currently* stored for `front`/`right_3q`/`left_3q`, and the result **completely replaces** whatever was shown before.

```
CURRENT 3 IMAGES (front, right_3q, left_3q — whatever is stored right now)
               ↓
        3-WAY VALIDATION (check_photo_set_identity, always fresh)
               ↓
     ┌─────────┼─────────┐
     ↓         ↓         ↓
   FRONT     RIGHT      LEFT
     ↓         ↓         ↓
   VALID/    VALID/    VALID/
   ERROR     ERROR     ERROR
               ↓
     REPLACES old identityCheck entirely (never merged)
               ↓
       UI shows the CURRENT state only
               ↓
     Any error? → Continue disabled, stay here
     No errors? → Continue enabled, proceed
```

This holds regardless of *which* angle was just retaken, or how many times retakes have happened before. A photo that was flagged as wrong two retakes ago carries no memory forward — its current status is whatever the latest 3-way comparison says.

## 2. Where each piece lives

| Concern | Location | Notes |
|---|---|---|
| Stored photo bytes | `Backend/app/models/photo.py` (`Photo`) + `photo_blob.py` (`PhotoBlob`) | One row per `(user_id, angle)`, **upserted in place** on every retake — never a new row, never a duplicate. |
| The comparison itself | `Backend/app/services/photo_validation_service.py::check_photo_set_identity()` | Pure function: takes `{angle: bytes}` for whatever is currently stored, returns a fresh result. No caching, no memory of past calls. |
| The group-matching algorithm | `Backend/app/services/photo_validation_service.py::_determine_mismatched_angles()` | See §3. Pure function over pairwise distances. |
| Result surfaced to the client | `GET /photos/status` (`photo_service.get_identity_check`) | Recomputes `check_photo_set_identity()` on **every single call** — re-loads current bytes, re-runs MediaPipe, re-scores every pair. Nothing is cached between requests. |
| Result held in the frontend | `frontend/src/store/photoStore.ts` (`identityCheck`) | `setStatus()` does a full field replacement (`identityCheck: status.identity_check`), never a merge. `setAnglePhoto()` (the optimistic local update fired the instant any upload completes) immediately resets `identityCheck: null` — a stale result is never left showing while a fresh one is pending. |
| Retake → recheck trigger | `frontend/src/components/photos/PhotoWizard.tsx::handleSubmitAngle` | After **any** successful upload, if the set is complete, it re-fetches `GET /photos/status` and calls `setStatus()` with the fresh result — covers first-time completion and every later replace of any single angle. |
| Error display / Continue gate | `frontend/src/components/photos/PhotoSetCompleteStep.tsx` | Derives `mismatchedAngles` directly from the `identityCheck` prop on every render (`identityCheck?.consistent === false ? identityCheck.mismatched_angles : []`) — there is no local component state that could go stale. Continue is `disabled={mismatchedAngles.length > 0}`. |
| "Already done, skip the screen" auto-redirect | `frontend/src/hooks/usePhotoUploadGuard.ts` | **The one place state WAS being reused incorrectly — see §6.** Decides, once, from the initial page-load fetch only (never from live retake churn), whether to skip the review screen entirely for a user who already has a fully consistent set. Manual "Continue" (PhotoSetCompleteStep) is the only thing that can advance the user during a live session where the set was inconsistent at arrival. |

## 3. The group-matching algorithm

`_determine_mismatched_angles(angles, pairwise)` decides which photo(s) are the mismatch. It does **not** pick a fixed "reference" angle and compare everyone else against it — it works out which photos agree with each other from the current pairwise distances, using a **match-count vote**:

1. For each of the 3 photos, count how many of the *other two* it's within `IDENTITY_MISMATCH_THRESHOLD` of (0, 1, or 2 matches).
2. **All three match each other** (every pair ≤ threshold) → consistent, no errors.
3. **Exactly one photo has zero matches** (the other two match each other) → that lone photo is the mismatch. This is the common case and covers every "two agree, one doesn't" scenario, however the group is currently made up — it is **not** anchored to `front` being special.
4. **All three mutually mismatch** (every pair > threshold) → `front` is treated as the kept/reference photo (there is no meaningful way to pick which of the other two is "more wrong" — that would just measure pose geometry, not identity), and **both** other photos are flagged together.
5. **A "hub" photo matches both others, but those two don't match each other** (rare edge case, not in the client's own worked examples but handled for completeness) → resolved to a single flagged angle, with `front` protected from being the answer whenever an alternative exists.

| Scenario | front↔right | front↔left | right↔left | Result |
|---|---|---|---|---|
| All match | ✓ | ✓ | ✓ | consistent, no errors |
| Front+right match, left doesn't | ✓ | ✗ | ✗ | `left` flagged |
| Front+left match, right doesn't | ✗ | ✓ | ✗ | `right` flagged |
| Right+left match, front doesn't | ✗ | ✗ | ✓ | `front` flagged |
| All three different | ✗ | ✗ | ✗ | `right` **and** `left` flagged, front kept |

## 4. Worked examples (from the client-provided spec, verified as passing tests)

These exact scenarios are encoded as regression tests in `Backend/tests/unit/test_photo_validation_service.py::TestExactUserReportedScenarios` — if this algorithm ever regresses, one of these tests fails first.

**Scene 1 → 2 → 3 (sequential retakes):**

| Step | front | right | left | Result |
|---|---|---|---|---|
| Initial | A | B | C | front valid · right ERROR · left ERROR |
| Retake front → B | B | B | C | front valid · right valid · left ERROR |
| Retake left → B | B | B | B | all valid, Continue enabled |

Note step 2: the *previous* right-side error disappears on its own because right now matches the new front — nothing "remembers" that right used to be wrong.

**Flip-flop scenario A** (the reference is not tied to front's original identity):

| Step | front | right | left | Result |
|---|---|---|---|---|
| Initial | A | B | A | front valid · right ERROR · left valid |
| Retake front → B | B | B | A | front valid · right valid · left ERROR |

**Flip-flop scenario B** (a retake of a *different* angle can move the error onto an angle that was never touched):

| Step | front | right | left | Result |
|---|---|---|---|---|
| Initial | A | A | B | front valid · right valid · left ERROR |
| Retake right → B | A | B | B | front **ERROR** · right valid · left valid |

## 5. Explicit non-goals / things this deliberately does NOT do

- Does **not** persist a "this angle is bad" flag anywhere — re-derived every time from current bytes.
- Does **not** compare only the retaken photo against the old result — always re-runs the full 3-way comparison.
- Does **not** treat `front` as a fixed reference except in the one case (§3.4) where there is genuinely no other principled choice.
- Does **not** cache MediaPipe signature results across requests — only the model *object* itself is cached (`@lru_cache` on the landmarker instance), never a computed signature or comparison result.

## 6. The one place this WAS broken: the auto-redirect guard (fixed 2026-09-10, v1.20)

§§1–5 above describe the comparison logic and its own state management, which were already correct as of `v1.18`. But a *separate* piece of frontend state was reusing a stale value incorrectly, and it produced exactly the symptom this spec exists to prevent: **a retake could get the user auto-navigated to `/payment` without the fresh comparison ever actually being checked.**

**Root cause:** `usePhotoUploadGuard.ts` had a reactive `useEffect` that watched the *live* `identityCheck` value and auto-navigated away from `/photos` once it looked "consistent." But `photoStore.setAnglePhoto()` — which fires the instant *any* retake's upload response comes back, before the fresh server re-check even starts — optimistically resets `identityCheck` to `null` (see §2's table). The effect's guard was `if (identityCheck?.consistent === false) return`, and `null?.consistent` is `undefined`, not `false` — so a `null` (meaning "unknown, pending," not "fine") fell through the guard and triggered an immediate redirect, hardcoding `photosIdentityConsistent: true`. In practice: **every retake, while the set was already complete when the page was entered, fired this redirect before the real server verdict came back** — regardless of whether that retake actually fixed anything.

**Why this wasn't caught in the v1.19 audit:** that audit traced the comparison algorithm and the store's replace-not-merge behavior correctly, but never inspected `usePhotoUploadGuard.ts`'s own redirect effect as a *consumer* of the (transiently null) `identityCheck` value. The live-testing done for v1.18 happened to retake photos that genuinely fixed the mismatch, so the premature redirect's outcome was indistinguishable from the correct outcome — the bug was only exposed by testing a retake that did *not* fully fix things (see the worked example below).

**Fix:** the "already done, skip the review screen" decision is now made exactly once, from the *initial* page-load fetch's own result (captured in a `wasConsistentOnFetch` ref, same pattern as the pre-existing `wasCompletedOnFetch` ref) — never from the live, retake-mutable `identityCheck` store value. A retake during the session can no longer re-trigger this effect at all (it has no dependency on `identityCheck`); only a fresh mount (full reload / new visit) re-evaluates it. The user reaching "no errors" via retakes now **always** requires clicking Continue themselves — matching this spec's own mental model diagram in §1, which was always describing a button, not automatic navigation.

**Regression coverage:** this is frontend state-management timing, not an algorithm this repo's Python test suite touches — there is no automated regression test for it (this project has no frontend unit/integration test suite; `tsc`/`eslint`/manual-and-live-Chrome-testing is the established convention here, per `CLAUDE.md`'s testing approach for the frontend). It was live-verified in Chrome instead: retook the flagged angle with an image that changed *which* angle was wrong (not consistent) → confirmed no redirect happened and the new error displayed correctly; retook the remaining two angles to reach genuine consistency → confirmed the page stayed put with Continue enabled until manually clicked; then broke consistency again via a change made **outside the browser session** (simulating another device/tab) and did a fresh full-page navigation to `/photos` → confirmed the error appeared freshly recomputed, proving reload-driven re-comparison has no caching gap either. If this hook is touched again, re-verify by hand with the same three checks — there's no `npm test` safety net for it.

## 7. If this needs to change

- Changing the threshold: `IDENTITY_MISMATCH_THRESHOLD` in `photo_validation_service.py`, calibrated empirically per its own docstring — re-run the calibration against real fixtures, don't just pick a new number.
- Changing which angle(s) get flagged in a tie: edit `_determine_mismatched_angles()` only — `check_photo_set_identity()` and everything above it in the stack (routers, frontend) is agnostic to how ties are broken, it just renders whatever `mismatched_angles` comes back.
- Adding a 4th+ angle: `_determine_mismatched_angles()`'s match-count logic generalizes past 3 photos, but the "all mutually mismatch → front is reference" fallback and the hub-tie branch were only reasoned about and tested for exactly 3 — re-verify both before assuming they generalize.
- Any change here should keep (or extend) the `TestExactUserReportedScenarios` test class as the executable version of this document.
- Touching `usePhotoUploadGuard.ts`, or any other guard that reads `identityCheck`: re-read §6 first. The specific failure mode to avoid is any redirect/navigation decision keyed off the *live* `identityCheck` store value rather than a value captured once at a well-defined point (e.g. "as of page arrival") — `identityCheck === null` is not the same as "consistent," it can also mean "a retake just happened and the real answer hasn't come back yet."
