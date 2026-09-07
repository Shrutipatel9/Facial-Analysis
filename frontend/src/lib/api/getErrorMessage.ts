import { ApiError, NetworkError } from "./errors"

/**
 * Maps a caught error to user-facing copy. Kept centralized so every form
 * surfaces API/network failures consistently (docs/ui-ux-design.md).
 */
export function getErrorMessage(err: unknown): string {
  if (err instanceof NetworkError) {
    const hint =
      process.env.NODE_ENV !== "production" ? " (Is the backend running? Check NEXT_PUBLIC_API_URL and CORS.)" : ""
    return err.message + hint
  }
  if (err instanceof ApiError) {
    return err.message
  }
  return "Something went wrong. Please try again."
}
