// SAFE: idEmittente derived from authenticated token (context.user),
// reject request if missing on tenant-scoped role.

interface Filters { idEmittente?: number[] }
declare const filters: Filters;
declare const context: { user: { idEmittente: number | null } };

if (context.user.idEmittente == null) {
  throw new Error("UnauthorizedError: Missing tenant scope on token");
}
filters.idEmittente = [context.user.idEmittente];
