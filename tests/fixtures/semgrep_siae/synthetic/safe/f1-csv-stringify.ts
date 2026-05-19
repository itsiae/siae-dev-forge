// SAFE counterpart to f1-csv-concat.ts: uses csv-stringify + cell sanitizer.

interface Report {
  nomeFile: string;
  nomeReport: string;
  emittente: string;
}

declare const db: { query(sql: string): Promise<Report[]> };
declare function uploadStringToS3(bucket: string, key: string, body: string): Promise<void>;
declare function stringify(records: unknown[][], options?: unknown): string;

function sanitizeCsvCell(v: unknown): string {
  const s = v == null ? "" : String(v);
  return /^[=+\-@\t\r]/.test(s) ? `'${s}` : s;
}

// SAFE: cells passed through csv-stringify with custom sanitizer cast.
export async function exportReportsSafe(): Promise<void> {
  const reports: Report[] = await db.query(
    "SELECT nomeFile, nomeReport, emittente FROM report"
  );
  const headers = ["nomeFile", "nomeReport", "emittente"];
  const csv = stringify(
    [headers, ...reports.map((r) => [r.nomeFile, r.nomeReport, r.emittente])],
    { quoted: true, cast: { string: sanitizeCsvCell } }
  );
  await uploadStringToS3("export-bucket", "report.csv", csv);
}
