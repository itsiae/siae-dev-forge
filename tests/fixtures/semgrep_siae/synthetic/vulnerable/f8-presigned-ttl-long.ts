// F8 pentest pattern: AWS SDK v3 getSignedUrl con TTL >60s (CWE-200/CWE-359).
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

declare const s3: S3Client;

export async function makeUrlVulnerable(key: string): Promise<string> {
  // VULNERABLE: TTL 3600s — URL "vendibile" per 1h
  return getSignedUrl(s3, new GetObjectCommand({ Bucket: "b", Key: key }), { expiresIn: 3600 });
}

export async function makeUrlVulnerable2(key: string): Promise<string> {
  // VULNERABLE: TTL 86400s (24h)
  return getSignedUrl(s3, new GetObjectCommand({ Bucket: "b", Key: key }), { expiresIn: 86400 });
}
