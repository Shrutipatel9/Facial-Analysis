import { create } from "zustand"

import type { PhotoAngleStatus, PhotoOut, PhotoSetStatusResponse } from "@/lib/photos/photoApi"

/**
 * Photo-upload progress (FR-005, FR-006, BR-004). Its own store, same
 * module-boundary convention as questionnaireStore.
 *
 * Deliberately NOT wrapped in `persist`, unlike questionnaireStore: raw
 * File/Blob/camera captures can't survive localStorage serialization, and
 * per-angle status is trivially re-fetchable from GET /photos/status on
 * mount -- there's nothing meaningful to preserve across a reload the way
 * 20 text answers were. Losing wizard step position on an accidental
 * reload is a minor inconvenience (re-pick which angle you were on), not a
 * lost-content problem.
 */
interface PhotoState {
  /** From GET /photos/status -- null until fetched once. */
  angles: PhotoAngleStatus[] | null
  /** From GET /photos/status, or recomputed locally after each upload. */
  completed: boolean | null

  setStatus: (status: PhotoSetStatusResponse) => void
  setAnglePhoto: (angle: string, photo: PhotoOut) => void
  reset: () => void
}

export const usePhotoStore = create<PhotoState>()((set) => ({
  angles: null,
  completed: null,

  setStatus: (status) => set({ angles: status.angles, completed: status.completed }),

  setAnglePhoto: (angle, photo) =>
    set((state) => {
      if (!state.angles) return state
      const angles = state.angles.map((a) => (a.angle === angle ? { ...a, photo } : a))
      return { angles, completed: angles.every((a) => a.photo?.validation_status === "passed") }
    }),

  reset: () => set({ angles: null, completed: null }),
}))
