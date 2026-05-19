// Allowlist EC-01: tabella audit_log globale by-design — opt-out via annotation.

declare const db: { query(sql: string, args?: unknown[]): Promise<unknown[]> };

export async function getRecentAuditByFileId(idFile: number): Promise<unknown[]> {
  // siae-tenant-safe: tabella audit globale by-design ARCH-2026-05-12
  return db.query("SELECT * FROM audit_log WHERE id_file = $1", [idFile]);
}
