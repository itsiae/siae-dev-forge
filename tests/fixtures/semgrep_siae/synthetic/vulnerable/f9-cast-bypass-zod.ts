// F9 pentest pattern: `as unknown as <Type>` cast bypass Zod validation (CWE-20).
import type { APIGatewayProxyEvent } from "aws-lambda";

interface ReportUploadReq {
  nomeFile: string;
  idEmittente: number;
  flagNazionale: boolean;
}

// VULNERABLE: cast TS bypass type checking; runtime value non validato (Zod missing).
export async function uploadVulnerable(event: APIGatewayProxyEvent): Promise<void> {
  const body = event.body as unknown as ReportUploadReq;  // ❌ Cast bypass
  await saveToDb(body.nomeFile, body.idEmittente);
}

declare function saveToDb(nome: string, id: number): Promise<void>;
