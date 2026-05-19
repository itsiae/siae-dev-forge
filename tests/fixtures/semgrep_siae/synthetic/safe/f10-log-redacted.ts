// SAFE: logger con metadata sanitizzato, no PII direct.
declare const logger: { debug: Function; info: Function };
declare const event: { body: { idEmittente: number } };

export function handlerSafe() {
  // SAFE: log solo ID tenant (no body diretto)
  logger.debug({ tenant_id: event.body.idEmittente, action: "upload" });
  logger.info("upload processed", { count: 1 });
}
