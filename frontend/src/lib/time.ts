/** Plain utility module (not a component/hook) for impure time
 * computations -- React Compiler's purity analysis flags Date.now() calls
 * made directly inside component/hook bodies, even from event handlers. */

export function msFromNowSeconds(seconds: number): number {
  return Date.now() + seconds * 1000
}

export function pastTimestamp(): number {
  return Date.now() - 1
}
