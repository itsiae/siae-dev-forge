// SAFE: Zod schema parse runtime validation before access.
import type { APIGatewayProxyEvent } from "aws-lambda";
import { z } from "zod";

const ReportUploadSchema = z.object({
  nomeFile: z.string().min(1).max(255),
  idEmittente: z.number().positive(),
  flagNazionale: z.boolean(),
});

export async function uploadSafe(event: APIGatewayProxyEvent): Promise<void> {
  // SAFE: Zod parse throws on invalid input; runtime validated.
  const body = ReportUploadSchema.parse(JSON.parse(event.body ?? "{}"));
  await saveToDb(body.nomeFile, body.idEmittente);
}

declare function saveToDb(nome: string, id: number): Promise<void>;
