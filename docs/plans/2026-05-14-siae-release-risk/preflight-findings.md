# Preflight Findings — task-01 siae-release-risk

**Eseguito:** 2026-05-14
**Branch:** `feat/siae-release-risk`
**Working dir:** `/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge`
**Platform:** macOS Darwin 25.4.0 (BSD userland)

## Sommario

- 5/5 API DevForge **CONFERMATE**.
- MCP sport-kg tool schema loadabile (PASS).
- gh CLI v2.88.1 **disponibile**, comandi `pr comment`/`pr view`/`pr review` esposti.
- Tooling Python disponibile via `python3 -m pytest`; `ruff` e `shellcheck` **NON installati globalmente**, da installare prima di task-40 (mitigazione documentata sotto).
- `timeout` / `gtimeout` **MANCANTI** su questa workstation macOS (BSD non li include di default, `coreutils` non installato via brew). Hook task-34 deve implementare fallback `kill -TERM $pid` o richiedere `brew install coreutils` come preflight di workstation.
- Nessun **BLOCKER hard** — tutti i gap sono coperti da install / fallback documentato.

## Tabella check-by-check

| # | Check | Cmd | Atteso | Effettivo | Stato | Note |
|---|---|---|---|---|---|---|
| 1 | `ScoreCard` schema field naming | `grep -A2 "class ScoreCard" lib/review_evidence/schema.py` | fields `security`, `coverage` (NO `_score`) | `security: float`, `coverage: float`, `quality`, `spec_compliance`, `discipline`, `overall` + `weights_used`, `missing_components` (riga 108-121) | PASS | Field naming allineato al design doc (sez. 6 dataclass). Naming non-`_score` confermato. |
| 2 | `baseline_cache` API | `grep -n "def fetch_baseline\|class BaselineCache" lib/review_evidence/baseline_cache.py` | `def fetch_baseline(...) -> Optional[ScoreCard]` + `class BaselineCache` | Riga 93: `def fetch_baseline(repo_full_name: str, main_sha: str) -> Optional[ScoreCard]:` — Riga 219: `class BaselineCache:` | PASS | API signature combacia col design doc Criterion 16. Tipo ritorno `Optional[ScoreCard]` consistente con `regression_delta.py` che task-16 implementera'. |
| 3 | Runner API `pip_audit` / `npm_audit` + `SecurityFindings` | `grep -E "..." runners/*.py scoring.py` | `PipAuditRunner`, `NpmAuditRunner` con `is_applicable(repo_root) -> bool`, `run(repo_root) -> Optional[SecurityFindings]`; `SecurityFindings(critical, high, medium, low)` | `class PipAuditRunner` + `def is_applicable(self, repo_root: Path) -> bool` + `def run(self, repo_root: Path) -> Optional[SecurityFindings]`; idem `NpmAuditRunner`; `SecurityFindings` riga 13 con `critical: int = 0`, `high: int = 0`, `medium: int = 0`, `low: int = 0` | PASS | Reuse Criterion 17 HEAD-only MVP confermato. Nessun rename necessario. |
| 4 | `devforge_log` signature | `sed -n '418,422p' lib/logger.sh` | `# Usage: devforge_log <event_type> <status> [meta_json]` + `devforge_log() {` | Riga 418: `# Usage: devforge_log <event_type> <status> [meta_json]` — riga 419: example — riga 420: `devforge_log() {` — riga 421-422 doc commento zero-loss | PASS | Signature combacia. Activity ledger emit per task-32 SKILL.md usera' template `devforge_log "release_risk_assessed" "success" '{"score":N,"level":"...","service":"..."}'`. |
| 5 | MCP sport-kg tool reachability | `ToolSearch select:mcp__sport-kg__describe_service` | schema loadato | Schema loadato (descrizione completa + parametri `service_name: string` required) | PASS | Tool catalog disponibile in sessione subagent (conferma `feedback_subagent_mcp_tool_loading.md`). task-12 puo' procedere con dispatch reale. |
| 6 | gh CLI availability | `gh --version` + `gh pr --help \| grep comment\|view` | `gh version 2.x.x` + `comment`/`view` esposti | `gh version 2.88.1 (2026-03-12)` — `comment: Add a comment to a pull request`, `view: View a pull request`, `review: Add a review` | PASS | Versione recente (2026-03-12), comandi richiesti da task-34 hook (`gh pr comment`, `gh pr view --json comments` per idempotency) tutti esposti. `gh api repos/...` non eseguito qui ma supportato dalla CLI v2.88+. |
| 6b.1 | pytest | `python3 -m pytest --version` | `pytest 8.x` | `pytest 8.4.2` (via `python3 -m`) | PASS | `pytest` standalone non in PATH; uso `python3 -m pytest` (versione integrata Command Line Tools). Sufficiente per test suite task-05/07/09/11/13/15/17/19/21/23/25/27/29/36. |
| 6b.2 | ruff | `ruff --version` / `python3 -m ruff --version` | `ruff x.y.z` | `command not found` / `No module named ruff` | FAIL (gap installabile) | Rimedio: `python3 -m pip install --user ruff` (oppure `brew install ruff`). Da eseguire **prima di task-40** (lint gate). Non blocca task-04..task-39. |
| 6b.3 | shellcheck | `shellcheck --version` | `ShellCheck x.y.z` | `command not found` | FAIL (gap installabile) | Rimedio: `brew install shellcheck`. Necessario per task-40 (hook PostToolUse Bash gating). Hook task-34 e' Bash → shellcheck obbligatorio prima del merge. Non blocca task-04..task-33. |
| 6b.4 | Python ≥3.11 | `python3 --version` | Python 3.11/3.12/3.13 | `Python 3.9.6` (system, `/usr/bin/python3`) | FAIL (constraint workstation) | Workstation host ha solo Python 3.9.6 system; design doc richiede 3.11+. Mitigazione: il **codice runtime** non usa feature 3.11-only (no `tomllib`, no `Self` type, no `ExceptionGroup` — verificato via grep nelle baseline `lib/review_evidence/`); dataclass + typing standard funzionano su 3.9+. Hook CI (siae-finishing-branch + review-evidence) gira su runner con Python 3.11+. Necessario installare `python@3.11` localmente per test parity (`brew install python@3.11`) — gap **non bloccante** per dev locale, ma raccomandato. |
| 6c | timeout portability (macOS) | `command -v timeout \|\| command -v gtimeout` | `TIMEOUT_AVAILABLE` | `TIMEOUT_MISSING` (nessuno dei due in PATH) | FAIL (rimedio richiesto) | macOS BSD userland non include `timeout(1)`. `gtimeout` arriva con `brew install coreutils` (non installato qui). **Task-34 hook MUST** implementare fallback: detection `if command -v timeout || command -v gtimeout`, altrimenti spawn background + `kill -TERM` dopo sleep N. Riferimento: `feedback_macos_timeout_portability.md` in user memory. Documentare in task-34 README hook. |

## Gap riepilogo e ownership

| Gap | Bloccante per | Fix proposto | Owner |
|---|---|---|---|
| `ruff` non installato | task-40 (lint gate), CI parity | `python3 -m pip install --user ruff` o `brew install ruff` | Dev workstation pre-task-40 |
| `shellcheck` non installato | task-40 (hook lint), siae-finishing-branch gate | `brew install shellcheck` | Dev workstation pre-task-40 |
| Python 3.9 vs 3.11+ design constraint | Test parity con CI | `brew install python@3.11` + use `python3.11 -m pytest` | Dev workstation pre-task-05 (consigliato, non bloccante) |
| `timeout`/`gtimeout` mancanti | task-34 hook robustezza | Hook implementa fallback `kill -TERM` graceful + suggerisce `brew install coreutils` | task-34 implementer |

## Conclusione

**Verdict:** PASS condizionato.

- API DevForge tutte verificate (5/5).
- MCP sport-kg raggiungibile in sessione.
- gh CLI presente.
- Gap workstation (`ruff`, `shellcheck`, `python@3.11`, `coreutils/gtimeout`) **non bloccanti** per task-03..task-39 (implementazione/test su Python stdlib). **Bloccanti** per task-40 + hook gates pre-PR → installare prima del gate finale.

**Nessun blocker hard** che richieda escalation utente o update design doc. Proseguo con task-02.

## Comandi mitigazione (run pre-task-40)

```bash
# Tooling lint/test
python3 -m pip install --user ruff
brew install shellcheck

# Python 3.11+ parity (opzionale ma raccomandato)
brew install python@3.11

# Timeout portability per hook task-34 (raccomandato)
brew install coreutils  # fornisce gtimeout
```
