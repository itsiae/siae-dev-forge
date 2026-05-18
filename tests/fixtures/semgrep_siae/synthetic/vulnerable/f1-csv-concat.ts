// Reproduces pattern of PENTEST_REPORT 2026-05-18 F-01 (synthetic minimal repro).
// NO real broadcasting code per ADR-004.

interface Report {
  nomeFile: string;
  nomeReport: string;
  emittente: string;
}

declare const db: { query(sql: string): Promise<Report[]> };
declare function uploadStringToS3(bucket: string, key: string, body: string): Promise<void>;

// VULNERABLE: cells joined naively, no sanitization of leading =/+/-/@
export async function exportReportsVulnerable(): Promise<void> {
  const reports: Report[] = await db.query(
    "SELECT nomeFile, nomeReport, emittente FROM report"
  );
  const headers = ["nomeFile", "nomeReport", "emittente"];
  const rows = reports.map((r) =>
    [r.nomeFile, r.nomeReport, r.emittente].join(",")
  );
  const csv = [headers.join(","), ...rows].join("\n");
  await uploadStringToS3("export-bucket", "report.csv", csv);
}
