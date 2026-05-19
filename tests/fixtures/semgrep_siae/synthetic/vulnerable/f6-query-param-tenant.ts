// Reproduces PENTEST_REPORT 2026-05-18 F-06 pattern (query-param tenant override).
// NO real broadcasting code per ADR-004.

interface Filters { idEmittente?: number[] }
declare const filters: Filters;
declare const req: { query: { idEmittente?: string } };

// VULNERABLE: idEmittente assigned from req.query without token override.
filters.idEmittente = req.query.idEmittente ? [Number(req.query.idEmittente)] : undefined;
