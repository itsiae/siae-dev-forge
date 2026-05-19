# SIAE Custom Semgrep Rules — Manifest (documentazione, NON Semgrep config)

> **NOTA tecnica**: questo file è documentale. Il runner DevForge passa l'intera
> directory `rules/semgrep/siae/` come `--config` a Semgrep (auto-discovery
> ricorsivo dei `*.yaml` con schema `rules: [{id, pattern, ...}]`).
> Vedi `lib/review_evidence/runners/semgrep.py` (`_SIAE_RULES_DIR`).

## Wave 1 — pentest 2026-05-18 broadcasting (rule attive)

| Famiglia | Path | CWE | Severity |
|---|---|---|---|
| F1 Formula Injection | `formula-injection/ts-csv-concat.yaml` | CWE-1236 | WARNING |
| F2 IDOR/Tenant DAO | `authz-tenant/ts-dao-missing-tenant.yaml` | CWE-639 | WARNING |
| F4 Soft-delete view-only | `soft-delete/sql-view-only-filter.yaml` | CWE-639 | WARNING |
| F6 Query-param tenant | `authz-tenant/ts-query-param-tenant-override.yaml` | CWE-639 | WARNING |
| F26 JWT localStorage | `jwt/ts-jwt-localstorage.yaml` | CWE-1004, CWE-79 | WARNING |

## Wave 2 — follow-up (placeholder paths)

- `formula-injection/ts-csv-rfc4180.yaml`
- `formula-injection/ts-csv-frontend-makecsv.yaml`
- `log-pii/ts-logger-body-taint.yaml`
- `presigned-url/ts-s3-presigned-ttl-too-long.yaml`
- `presigned-url/ts-s3-presigned-in-response.yaml`
- `input-validation/ts-cast-bypass-zod.yaml`

## Wave 3 — cross-stack (placeholder paths)

- `authz-tenant/java-jpa-tenant.yaml` (Spring Data JPA)
- `presigned-url/py-boto3-presigned.yaml` (Python boto3)
- `xss-supplement/angular-bypass-security-trust.yaml` (Angular)

## Convenzione naming

```
siae.<family>.<lang>.<short-name>
```

Vedi `README.md` per severity policy, suppression workflow, limiti tecnici.

## Riferimenti

- Design parent: `docs/plans/2026-05-18-security-hook-vulnerability-prevention-design.md` (v2.1)
- Pentest: `pentest-broadcasting/PENTEST_REPORT.md` (2026-05-18)
