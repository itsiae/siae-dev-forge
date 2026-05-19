// EC-03: numeric values must NOT trigger F1 (numeric pre-filter).
// Reproducing pattern that LOOKS like F1 but with numbers only.

declare function uploadStringToS3(bucket: string, key: string, body: string): Promise<void>;

// SAFE: only numbers — sanitizeCsvCell pre-filter accepts numbers as-is.
export async function exportImportiSafe(): Promise<void> {
  const importi: number[] = [-12.50, -100, 0.5, 42.0];
  const csv = importi.map((i) => String(i)).join("\n");
  await uploadStringToS3("bucket", "importi.csv", csv);
}
