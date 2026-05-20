---
name: forge-evidence
description: Pre-compute deterministic quality signals (coverage, lint, complexity, CI SARIF, spec-drift) for the current SHA. Run on-demand prior to code review.
allowed-tools: Bash, Read
---

# /forge-evidence — Review Evidence on-demand

Pre-calcola in modo deterministico i segnali di qualità per il SHA corrente
e li scrive in `.claude/review-evidence/<sha>.json`. Gli agent `code-reviewer`
e `spec-reviewer` consumano l'evidence come ground truth (Step 0.5
evidence-loading) anziché ricalcolare soggettivamente.

## Cosa fa

1. Detect SHA corrente via `git rev-parse HEAD`
2. Detect stack (Java/TypeScript/Python/HCL) via `lib/review_evidence/registry.py`
3. Esegue per ogni stack rilevato: coverage, lint, complessità
4. Fetcha artefatti SARIF dalla CI (se completed runs presenti su questo SHA)
5. Calcola spec-drift contro il design doc più recente in `docs/plans/`
6. Scrive `.claude/review-evidence/<sha>.json` (schema v1)
7. Stampa riepilogo human-readable con verdict + block_reasons

## Quando usarlo

- **Prima di lanciare** `code-reviewer` o `spec-reviewer`: l'evidence diventa pre-loaded
- **Dopo** che la CI ha completato gli artefatti SARIF (vedi lifecycle sotto)
- **Debugging:** verifica perché il pr-gate ha bloccato

## CI quality reports lifecycle

I CI quality reports (Qodana / SonarQube / CodeQL / qualsiasi tool che emetta
SARIF) girano POST-push. Conseguenza:

| Momento | Stato `ci_quality.available` |
|---|---|
| Primo `gh pr create` su un nuovo SHA | `false` — CI non ancora girata |
| Push + ~5-10 min (attesa CI) | `false` finché workflow non completa |
| Dopo che il workflow CI è completato | `true` — artefatti SARIF fetcheabili |
| `gh pr edit` (any) successivo | l'hook ri-attiva e fetcha SARIF |

**Pattern raccomandato:**

```bash
# 1. Apri PR (locale-only signals)
gh pr create --draft

# 2. Aspetta CI
gh pr checks --watch

# 3. Re-attiva hook con edit per pickup SARIF
gh pr edit --add-label review-ready
```

## Uso

```bash
# On-demand compute (sync)
bash hooks/review-evidence

# View evidence
cat .claude/review-evidence/$(git rev-parse HEAD).json | jq
```

## Override soglie

```bash
export DEVFORGE_EVIDENCE_MIN_COVERAGE=75
export DEVFORGE_EVIDENCE_MAX_LINT_ERRORS=3
export DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL=high  # critical|high|off
export DEVFORGE_EVIDENCE_DESIGN_DOC=docs/plans/my-design.md
bash hooks/review-evidence
```

## Bypass

```bash
# Primary (state file — affidabile in subprocess hook)
export DEVFORGE_SKIP_EVIDENCE=1 (breakglass session-scoped)

# Secondary (env var — fallback)
export DEVFORGE_SKIP_EVIDENCE=1
```

Il bypass è tracked: `evidence_bypass_abuse_suspected` viene loggato se usato
>= 5 volte/giorno (cfr. pattern DEVFORGE_SKIP_* esistenti).

## Output di esempio

```
review-evidence abc12345: coverage=78.5%, lint_errors=3, complexity_max=12, block=false. File: .claude/review-evidence/abc12345....json
```

Block:

```
review-evidence abc12345: BLOCK
Reasons: coverage_below_threshold:55<60, lint_errors:5>0
Override: export DEVFORGE_SKIP_EVIDENCE=1 (breakglass session-scoped)
File: .claude/review-evidence/abc12345....json
```
