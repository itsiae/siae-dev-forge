/** Genera due fixture per file ??-heavy: minimal (rami fallback) + full (rami value). */
export function buildFixtures<T extends Record<string, unknown>>(
  fullShape: T,
): { minimal: Partial<T>; full: T } {
  return { minimal: {}, full: fullShape }
}
