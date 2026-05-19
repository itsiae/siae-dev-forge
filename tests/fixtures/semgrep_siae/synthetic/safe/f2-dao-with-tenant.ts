// SAFE: DAO query with AND id_emittente filter derived from token.

declare const db: { query(sql: string, args?: unknown[]): Promise<unknown[]> };

export async function getLogsPathByFileIdSafe(
  id: number,
  tenantId: number,
): Promise<unknown[]> {
  return db.query(
    "SELECT s3_path FROM file_logs WHERE id_file = $1 AND id_emittente = $2",
    [id, tenantId],
  );
}

export async function getReportByIdSafe(
  idReport: number,
  tenantId: number,
): Promise<unknown[]> {
  return db.query(
    "SELECT * FROM report_logico WHERE id_report = $1 AND id_emittente = $2",
    [idReport, tenantId],
  );
}
