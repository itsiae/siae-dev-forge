// Reproduces PENTEST_REPORT 2026-05-18 F-03 pattern (IDOR/DAO missing tenant).
// NO real broadcasting code per ADR-004.

declare const db: { query(sql: string, args?: unknown[]): Promise<unknown[]> };

// VULNERABLE: query selects by id_file without AND id_emittente filter.
export async function getLogsPathByFileId(id: number): Promise<unknown[]> {
  return db.query("SELECT s3_path FROM file_logs WHERE id_file = $1", [id]);
}

// VULNERABLE: same pattern with id_report.
export async function getReportById(idReport: number): Promise<unknown[]> {
  return db.query("SELECT * FROM report_logico WHERE id_report = $1", [idReport]);
}

// VULNERABLE: camelCase variant.
export async function getCanaleByIdFile(idFile: number): Promise<unknown[]> {
  return db.query("SELECT * FROM canale WHERE idFile = $1", [idFile]);
}
