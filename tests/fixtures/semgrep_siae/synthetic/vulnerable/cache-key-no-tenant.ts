// OWASP 2026: cache key without tenant prefix → cross-tenant cache poisoning.
declare const redis: { get(k: string): Promise<string>; set(k: string, v: string): Promise<void> };
declare const cache: Map<string, unknown>;
declare const context: { user: { idEmittente: number } };

// VULNERABLE: cache key non include id_emittente → tenant A vede dati cached da tenant B
export async function getReportCached(id: number) {
  const cached = await redis.get(`report:${id}`);  // ❌ no tenant prefix
  if (cached) return JSON.parse(cached);
}

export function getDashboardFromMemory(canaleId: number) {
  return cache.get(`dashboard:${canaleId}`);  // ❌ same anti-pattern
}
