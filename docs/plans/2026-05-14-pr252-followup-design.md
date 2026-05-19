# Design — PR #252 Follow-up Drift Fix

**Data:** 2026-05-14
**Complessita:** BASSA
**Owner:** lorenzo.detomasi@siae.it
**SP:** Augmented 0.5 (~15 min)

## Contesto

Smoke test post-merge PR #252 (siae-release-risk) ha trovato 2 drift residui:

1. **Test count drift** — `tests/hooks/hooks-json-var-expansion.test.sh` hardcoda `24` in 3 punti (line 32 escaped-dquote count, line 65 total commands count, line 70 echo PASS message). Ma `hooks/hooks.json` ora contiene 25 hooks dopo l'aggiunta di `pr-release-gate` in task-35. Risultato: `test_existing_hook_test_passes[hooks-json-var-expansion.test.sh]` fallisce in main.

2. **Doc forge-score CLI bug** — `commands/forge-score.md:39` documenta `python3 -m lib.review_evidence.cli score` ma `lib/review_evidence/cli.py` **non esiste**. Lo scoring esiste come API Python (`score_security/quality/coverage/spec/discipline + compute_overall` in `lib/review_evidence/scoring.py`) ma manca CLI entrypoint.

## Decisione

Micro-PR meccanico:

| File | Cambio |
|---|---|
| `tests/hooks/hooks-json-var-expansion.test.sh` | `24` → `25` in linee 32, 65, 70 |
| `commands/forge-score.md` | Sostituisci sezione "Uso" rimuovendo ref a `lib.review_evidence.cli`; documenta API Python diretta come metodo corrente; aggiungi note che il CLI subcommand sara' aggiunto in una future iteration |

**Non in scope:** creare `lib/review_evidence/cli.py`. Decisione utente 2026-05-14: meglio aggiornare doc a realta' che aggiungere feature work non richiesta.

## Acceptance Criteria

- **AC1:** `python3 -m pytest tests/ -q --ignore-glob="tests/*2.py"` esce con `385 passed` (era 381 passed + 1 failed + 4 deselected)
- **AC2:** `bash tests/hooks/hooks-json-var-expansion.test.sh` exit 0 standalone
- **AC3:** `grep -c "lib.review_evidence.cli" commands/forge-score.md` ritorna 0
- **AC4:** `commands/forge-score.md` include esempio Python funzionante con import + chiamata `compute_overall`
- **AC5:** Branch `fix/pr252-followup-drift` su main, PR aperta, no CI failure

## Trade-off (single approccio)

Nessun trade-off significativo: count drift ha solo un fix sensato (allinea numero); doc update ha gia' avuto disambig utente (no cli.py).

## Spec-review

SKIP-LOW-COMPLEXITY · motivo: 2 file, 4 cambi puntuali, AC misurabili via grep+pytest.
