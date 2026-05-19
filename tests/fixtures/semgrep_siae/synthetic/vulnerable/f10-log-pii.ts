// F10 pentest pattern: logger con event.body/req.body untrusted → PII leak (CWE-532).

declare const logger: { debug: Function; info: Function; warn: Function; error: Function };
declare const event: { body: unknown };
declare const req: { body: unknown; params: unknown };

export function handlerVulnerable() {
  // VULNERABLE: event.body in log → PII leak CloudWatch (CWE-532)
  logger.debug({ body: event.body });
  logger.info("upload received", req.body);
  logger.error(`failed for input ${JSON.stringify(req.params)}`);
}
