# Task 01 — Pre-flight infra check

**Stato:** [PENDING]
**SP:** 1.5 Human / 0.5 Augmented
**Dipendenze:** nessuna (primo task)

## Goal

Verificare che l'infrastruttura DevForge richiesta dal design sia disponibile prima di iniziare implementazione: schema `BaselineCache`, runner `pip_audit`/`npm_audit`, MCP sport-kg connectivity, API `devforge_log`.

## File coinvolti

- Read: `lib/review_evidence/baseline_cache.py` (verifica API `fetch_baseline`)
- Read: `lib/review_evidence/schema.py` (verifica `ScoreCard.security: float`, `.coverage: float`)
- Read: `lib/review_evidence/runners/pip_audit.py`, `npm_audit.py` (verifica `is_applicable`, `run` signature)
- Read: `lib/review_evidence/scoring.py` (verifica `SecurityFindings` schema)
- Read: `lib/logger.sh` (verifica `devforge_log <event> <status> [meta]` signature riga 420)

## Step

### Step 1 — Verifica ScoreCard schema

Run:
```bash
grep -A2 "class ScoreCard" "lib/review_evidence/schema.py"
```
Output atteso (riga ~110-122):
```python
@dataclass
class ScoreCard:
    security: float  # NOT security_score
    coverage: float  # NOT coverage_score
    ...
```
Se field naming è `security_score`/`coverage_score` invece di `security`/`coverage` → BLOCKED, aggiorna design doc + propaga grep.

### Step 2 — Verifica baseline_cache API

Run:
```bash
grep -n "def fetch_baseline\|class BaselineCache" "lib/review_evidence/baseline_cache.py"
```
Output atteso:
```
93:def fetch_baseline(repo_full_name: str, main_sha: str) -> Optional[ScoreCard]:
219:class BaselineCache:
```

### Step 3 — Verifica runner API

Run:
```bash
grep -E "def is_applicable|def run|class.+AuditRunner|class SecurityFindings" lib/review_evidence/runners/pip_audit.py lib/review_evidence/runners/npm_audit.py lib/review_evidence/scoring.py
```
Output atteso: `PipAuditRunner`, `NpmAuditRunner` con `is_applicable(repo_root) -> bool`, `run(repo_root) -> Optional[SecurityFindings]`. `SecurityFindings` con `critical: int, high: int, medium: int, low: int`.

### Step 4 — Verifica devforge_log signature

Run:
```bash
sed -n '418,422p' lib/logger.sh
```
Output atteso:
```
# Usage: devforge_log <event_type> <status> [meta_json]
# Example: devforge_log "session_start" "success" '{"project_dir":"/path"}'
devforge_log() {
```

### Step 5 — Verifica MCP sport-kg reachability

Run:
```bash
echo "Verify MCP sport-kg tools availability in current session via ToolSearch"
```
Action: dispatch a quick ToolSearch query `select:mcp__sport-kg__describe_service` per loadare schema. Se non disponibile → documenta in task-12 fallback richiesto.

### Step 6 — Verifica gh CLI availability

Run:
```bash
gh --version
gh pr --help | grep -E "comment|view" | head -5
```
Output atteso: `gh version 2.x.x` + comandi `gh pr comment`, `gh pr view --json comments` disponibili. Se `gh api repos/...` non funzionale → fallback documentato.

### Step 6b — Verifica tooling Python/lint

Run:
```bash
pytest --version
ruff --version
shellcheck --version
python3 --version | grep -E "3\.(11|12|13)"  # min 3.11
```
Output atteso: tutti presenti. Se ruff/shellcheck mancanti → install (`pip install ruff`, `brew install shellcheck`) o documenta gap in preflight-findings.md.

### Step 6c — Verifica timeout portability (macOS)

Run:
```bash
command -v timeout || command -v gtimeout && echo "TIMEOUT_AVAILABLE" || echo "TIMEOUT_MISSING"
```
Output atteso: `TIMEOUT_AVAILABLE` su Linux dev workstation; macOS BSD ha `gtimeout` solo se `brew install coreutils`. Hook task-34 implementa fallback graceful, ma documentare in preflight-findings.md.

### Step 7 — Documenta findings

Scrivi `docs/plans/2026-05-14-siae-release-risk/preflight-findings.md` con tabella check-by-check (PASS/FAIL + note). Commit.

## Criteri di accettazione

- [ ] Tutte le 5 API DevForge confermate (ScoreCard, baseline_cache, runners, devforge_log, SecurityFindings)
- [ ] MCP sport-kg tool schema caricato in sessione (oppure documentato gap)
- [ ] `gh` CLI disponibile + comandi `comment`/`view` funzionanti
- [ ] `preflight-findings.md` committato in `docs/plans/2026-05-14-siae-release-risk/`
- [ ] Nessun blocker rilevato (altrimenti BLOCKED + escalation utente)
