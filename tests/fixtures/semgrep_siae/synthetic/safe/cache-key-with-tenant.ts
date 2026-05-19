// SAFE: cache key include id_emittente prefix → isolamento cross-tenant.
declare const redis: { get(k: string): Promise<string> };
declare const context: { user: { idEmittente: number } };

export async function getReportCached(id: number) {
  // SAFE: tenant prefix
  const cached = await redis.get(`tenant:${context.user.idEmittente}:report:${id}`);
  if (cached) return JSON.parse(cached);
}
