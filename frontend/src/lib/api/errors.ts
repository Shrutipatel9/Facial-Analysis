export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly retryAfterSeconds?: number

  constructor(status: number, code: string, message: string, retryAfterSeconds?: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.code = code
    this.retryAfterSeconds = retryAfterSeconds
  }
}

/** A fetch that never reached the server -- offline, DNS failure, CORS
 * misconfiguration, etc. Kept distinct from ApiError so the UI can show a
 * "check your connection" message instead of a parsed API error. */
export class NetworkError extends Error {
  constructor(cause: unknown) {
    super("Could not reach the server. Check your connection and try again.")
    this.name = "NetworkError"
    this.cause = cause
  }
}
