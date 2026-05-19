// SAFE: TTL 60s (raccomandazione ADR-008).
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

declare const s3: S3Client;

export async function makeUrlSafe(key: string): Promise<string> {
  return getSignedUrl(s3, new GetObjectCommand({ Bucket: "b", Key: key }), { expiresIn: 60 });
}
