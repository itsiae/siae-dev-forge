# SIAE Custom Semgrep Rules

Library di regole Semgrep custom per intercettare vulnerability pattern SIAE-domain non coperte dai community rulesets standard. Wave 1 attivo, Wave 2/3 follow-up.

**Design parent**: `docs/plans/2026-05-18-security-hook-vulnerability-prevention-design.md` (v2.1, 3 iter spec-review PASS).

## Naming Convention

Tutte le regole seguono il pattern:

```
siae.<family>.<lang>.<short-name>
```

Esempi:
- `siae.formula-injection.ts.csv-concat-naive`
- `siae.authz-tenant.ts.dao-missing-tenant-filter`
- `siae.soft-delete.sql.view-only-state-filter`
- `siae.jwt.ts.jwt-in-localstorage`

Famiglie attive (cartelle):
- `formula-injection/` — CSV/XLSX Formula Injection (CWE-1236)
- `authz-tenant/` — IDOR / Tenant scoping (CWE-639)
- `soft-delete/` — Soft-delete bypass (CWE-639)
- `presigned-url/` — Wave 2
- `input-validation/` — Wave 2
- `log-pii/` — Wave 2
- `jwt/` — Wave 1 minimal + Wave 2
- `orm-supplement/` — Wave 2
- `ssrf-supplement/` — Wave 2
- `xss-supplement/` — Wave 2/3

## Severity Policy (ADR-005)

| Rule severity | Confidence | Bucket | Effect su PR |
|---|---|---|---|
| ERROR | HIGH | `critical` | **BLOCK_REGRESSION** via review-evidence v2 |
| ERROR | MEDIUM | `high` | warning, no block |
| WARNING | HIGH | `high` | visible report, no block |
| WARNING | MEDIUM/LOW | `medium` | info |
| INFO | * | `low` | educational |

**Regola d'oro**: una rule entra in bucket `critical` (block) SOLO se ha tutti i 5 criteri:
1. `severity: ERROR`
2. `metadata.confidence: HIGH`
3. `metadata.category: security`
4. Fixture vulnerable + safe + allowlist passano `semgrep --test`
5. False positive rate misurato <5% per 30gg via `lib/review_evidence/tools/fp_rate.py` (ADR-005a)

**Default per nuove rule**: `severity: WARNING`. Promotion ERROR avviene per PR dedicata dopo FP measurement (vedi `lib/review_evidence/tools/fp_rate.py`).

## Suppression Workflow

> **⚠️ Wave 1 MVP scope**: solo le modalità **2 (inline `// nosemgrep`)** e
> **3 (annotation domain-specific)** sono operative oggi. La modalità **1
> (`suppressions.yaml` strutturata + PR-gate schema validation)** richiede
> l'implementazione di task-11/12/13 del piano (suppression engine + PR-gate
> validator) — Wave 1 follow-up sessione separata. Il file `suppressions.yaml`
> referenziato sotto è preview del workflow target post-Wave 1 follow-up.

Per sopprimere finding legittimi (audit_log globali, edge case validi):

### 1. Strutturata (preferito) — `suppressions.yaml`

```yaml
suppressions:
  - rule_id: siae.authz-tenant.ts.dao-missing-tenant-filter
    path_glob: "**/dao/audit_log*.ts"
    reason: "Tabella audit globale by-design ARCH-2026-05-12 confermato"
    owner: tuo.email@siae.it
    expires_at: "2026-08-15"  # ≤90gg
```

PR-gate hook valida schema (ADR-009):
- `path_glob` NO catch-all `**`
- `reason` ≥30 char + Jira ref `[A-Z]+-[0-9]+`
- `expires_at` ≤90gg
- `owner` `@siae.it`

### 2. Inline `// nosemgrep` (escape rapido)

```typescript
// nosemgrep: siae.formula-injection.ts.csv-concat-naive reason=false-positive-confirmed expires=2026-08-15
```

Formato STRICT: deve avere `rule-id` + `reason` + `expires`. Limite >3 per file → WARNING.

### 3. Annotation domain-specific (inline contextual)

```typescript
// siae-tenant-safe: tabella audit globale by-design SDLC-1234
db.query('SELECT * FROM audit_log WHERE id_file = $1', [id]);
```

```typescript
// semgrep-siae: cross-tenant-aggregate by-design
db.query('SELECT COUNT(*) FROM eventi GROUP BY tipo_emittente');
```

## Performance Considerations

Riferimento ADR-008.

- **Diff-aware default**: runner usa `--baseline-commit $DEVFORGE_SEMGREP_BASELINE_COMMIT` se env settato → scan solo del diff
- **Mirror vendored locale**: community rulesets in `rules/semgrep/vendored/` per evitare network call hot-path
- **Hard timeout per-file**: 10s (protezione ReDoS)
- **Streaming JSON parser** (ijson): per output Semgrep >50MB
- **Parallel jobs**: `--jobs=$(SEMGREP_JOBS|os.cpu_count())`
- **Benchmark target**: P95 < 90s su monorepo 200k LOC

## Limiti tecnici dichiarati (ADR-007)

Esplicitamente NON coperti da rule SIAE Semgrep CE:

- **F3 Tenant cross-function taint** (es. middleware → handler → DAO): Semgrep CE ha limite cross-function taint analysis. Wave 1 best-effort severity INFO. Roadmap Wave 2 valuta runner Python custom o Semgrep Pro.
- **Drools `.drl` files**: no Drools parser in Semgrep CE. `pr-gate` hook emette WARNING su PR che modifica `*.drl` senza review marker (Form A label `drools-security-reviewed` OR Form B header `// drools-security-reviewed: <Jira> by:<email> on:<date>`).
- **Flutter/Dart mobile**: out-of-scope. Roadmap mobile linter custom.

## Come aggiungere una nuova rule

1. Crea YAML in `rules/semgrep/siae/<family>/<lang>-<short-name>.yaml`
2. Aggiungi path a `registry.yaml`
3. Crea fixture `tests/fixtures/semgrep_siae/synthetic/{vulnerable,safe}/` minimal repro
4. Aggiungi test in `tests/test_semgrep_siae_rules.py::test_<rule>`
5. Default `severity: WARNING` (no block per ADR-005)
6. Documenta in `skills/siae-security/SKILL.md` sezione Rule Reference
7. PR-gate hook richiede CODEOWNERS `@security-team` se la rule ha `severity: ERROR`

## Riferimenti

- Design parent: `docs/plans/2026-05-18-security-hook-vulnerability-prevention-design.md` (v2.1)
- Pentest trigger: `pentest-broadcasting/PENTEST_REPORT.md` (2026-05-18)
- ADR-001..009 nel design
- Semgrep custom rules: https://semgrep.dev/docs/writing-rules/overview
- Semgrep taint mode: https://semgrep.dev/docs/writing-rules/data-flow/taint-mode
