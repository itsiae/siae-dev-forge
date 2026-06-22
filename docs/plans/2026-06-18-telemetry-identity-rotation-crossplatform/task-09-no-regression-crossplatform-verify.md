# Task 09 — Harness verifica cross-platform committato + no-regression (gate finale)

**AC:** AC5, AC6, AC7 (tutti) · **File:** `tests/zero-loss/integration/test_crossplatform_no_degradation.sh`, `tests/run-all.sh` (wiring — BLOCK-5: il runner è `run-all.sh`, NON `run-all-tests.sh`)

## Obiettivo

Consolidare la verifica empirica eseguita in sessione in un test committato e ripetibile che
dimostra **no-degradation su Mac e Windows in parallelo**, e collegare i 5 nuovi test alla suite.

## RED — test che fallisce

Crea `tests/zero-loss/integration/test_crossplatform_no_degradation.sh` basato sull'harness di
sessione (profili: macOS=python3 presente; Windows=python3+flock mascherati, node presente). Per
ogni profilo asserisci:
- durabilità: N/N righe sotto concorrenza (25);
- integrità: 0 righe malformate (validatore python3, meta statico `{"k":"v"}` — NIENTE quoting di shell);
- attribuzione: N event_id unici (Capability D);
- identità: `auth_email` SSO risolto + i 6 nuovi campi presenti nel bundle;
- invio segnali: zero-loss su endpoint down (batch preservato, exit 0);
- rotazione: `archived_files >= 1` su entrambi i profili (Capability B).
- Atteso PRE-implementazione: FAIL su rotazione (Win) ed event_id; PASS dopo task-01..08.

Nota lezioni di sessione: pre-crea `.devforge-session-id`; usa path reali (repo con spazi);
meta statico per evitare falsi positivi di JSON-malformed.

## GREEN — implementazione

Adatta l'harness validato in sessione come test committato, parametrizzando `PLUGIN_ROOT` sul repo
(NON hardcodare il path utente). Aggiungi al runner `tests/run-all.sh`:
- i 5 nuovi test unit: `test_logger_event_id_concurrency.sh`, `test_logger_identity_signals.sh`,
  `test_logger_rotation_crosstier.sh`, `test_batch_global_archives.sh`, `test_logger_crlf_cursor.sh`;
- il test integration: `test_crossplatform_no_degradation.sh`;
- **WARN-16**: wira anche `tests/test_telemetry_fixes.sh` e `tests/test_telemetry_flush_storm.sh`,
  oggi NON presenti in `run-all.sh` (verificato con grep: 0 occorrenze) — vanno aggiunti alla suite.
- Verifica che `run-all.sh` scansioni `tests/zero-loss/integration/*.sh` (oggi contiene solo
  `test_lambda_handler.py`); se scansiona solo `.py`, aggiungi esplicitamente il nuovo `.sh`.
Aggiorna il count atteso no-regression se il runner lo verifica.

## REFACTOR

Rimuovi gli script temporanei `/tmp/devforge_verify*.sh`. Verifica che il runner non aborti su
macOS (memory: full-suite locale può abortire su `Library/Caches` — escludi path problematici).

## Verifica / Done

- `bash tests/zero-loss/integration/test_crossplatform_no_degradation.sh` PASS (entrambi i profili).
- Suite completa zero-loss/telemetria verde (no-regression, tutti i test pre-esistenti + 6 nuovi).
- Marca `[DONE]`. Handoff a `siae-finishing-branch` per PR.
