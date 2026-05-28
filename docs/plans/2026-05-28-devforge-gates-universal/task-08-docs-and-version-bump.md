# Task 08 — Aggiorna `hooks/ENV_VARS.md` + `CHANGELOG.md` + bump v1.69.0

> **REQUIRED SUB-SKILL:** `siae-tdd` (test: grep struttura doc)
> **Dipendenza:** task 1-7 completati

**Goal:** Documentazione aggiornata, versione bumped v1.68.0 → v1.69.0 in entrambi `plugin.json` e `marketplace.json` (memory `project_plugin_version_dual_source`).

**File coinvolti:**
- Modifica: `hooks/ENV_VARS.md` (nuova sezione "Gate Scope")
- Modifica: `CHANGELOG.md` (entry v1.69.0)
- Modifica: `.claude-plugin/plugin.json` (version)
- Modifica: `.claude-plugin/marketplace.json` (version)
- Crea: `tests/docs_and_version.test.sh`

---

## Step 1 — Scrivi il test fallente

Crea `tests/docs_and_version.test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PASS=0
FAIL=0

assert() {
    local desc="$1" cmd="$2"
    if eval "$cmd"; then PASS=$((PASS+1)); printf "  [PASS] %s\n" "$desc"
    else FAIL=$((FAIL+1)); printf "  [FAIL] %s\n" "$desc"; fi
}

# ENV_VARS.md
assert "ENV_VARS has 'Gate Scope' section" \
    "grep -q '^## Gate Scope$' '${REPO_ROOT}/hooks/ENV_VARS.md'"
assert "ENV_VARS documents DEVFORGE_GATE_SCOPE" \
    "grep -q 'DEVFORGE_GATE_SCOPE' '${REPO_ROOT}/hooks/ENV_VARS.md'"
assert "ENV_VARS documents state file path" \
    "grep -q '.devforge-gate-scope' '${REPO_ROOT}/hooks/ENV_VARS.md'"

# CHANGELOG
assert "CHANGELOG has 1.69.0 entry" \
    "grep -q '^## \\[1\\.69\\.0\\]' '${REPO_ROOT}/CHANGELOG.md'"
assert "CHANGELOG entry mentions BREAKING" \
    "grep -A30 '^## \\[1\\.69\\.0\\]' '${REPO_ROOT}/CHANGELOG.md' | grep -q 'BREAKING'"
assert "CHANGELOG entry mentions DEVFORGE_GATE_SCOPE" \
    "grep -A30 '^## \\[1\\.69\\.0\\]' '${REPO_ROOT}/CHANGELOG.md' | grep -q 'DEVFORGE_GATE_SCOPE'"

# Version dual source allineata
PLUGIN_V=$(grep -oE '"version":[[:space:]]*"[^"]*"' "${REPO_ROOT}/.claude-plugin/plugin.json" | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
MARKET_V=$(grep -oE '"version":[[:space:]]*"[^"]*"' "${REPO_ROOT}/.claude-plugin/marketplace.json" | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
assert "plugin.json version = 1.69.0" "[ '$PLUGIN_V' = '1.69.0' ]"
assert "marketplace.json version = 1.69.0" "[ '$MARKET_V' = '1.69.0' ]"
assert "plugin.json == marketplace.json version" "[ '$PLUGIN_V' = '$MARKET_V' ]"

echo
echo "docs_and_version.test.sh — PASS: $PASS / 9 — FAIL: $FAIL / 9"
[ "$FAIL" -eq 0 ] || exit 1
```

## Step 2 — Esegui e verifica che fallisce

```bash
bash tests/docs_and_version.test.sh
```

Atteso: 9 FAIL. Exit 1.

## Step 3 — Implementa gli edit

### 3.1 — `hooks/ENV_VARS.md`

Aggiungi sezione DOPO la sezione "Global" (cerca `## Global` + tabella + righe vuote, inserisci prima della prossima `##`):

```markdown
## Gate Scope

| Env var | Default | Introduced | Description |
|---|---|---|---|
| `DEVFORGE_GATE_SCOPE` | `universal` | v1.69.0 | Controlla scope dei 5 gate workflow (brainstorming, plan-gate-write, tdd, pr-blind-review, pr-premortem). Valori: `universal` (gate attivo su qualsiasi repo git, **default**) \| `itsiae` (legacy: gate solo su remote `[/:]itsiae/`). Valore non riconosciuto → fail-safe a universal + log `gate_scope_unknown_value`. |

**State file fallback:** `~/.claude/.devforge-gate-scope` — letto dalla lib `lib/scope-check.sh` se l'env var non è propagata al subprocess hook (vedi memory `feedback_env_var_not_propagated_to_hooks`). Contenuto: una singola riga `universal` o `itsiae` (whitespace trimmed).

**Migration v1.68.0 → v1.69.0:** chi vuole preservare il vecchio comportamento itsiae-only:
```bash
echo 'export DEVFORGE_GATE_SCOPE=itsiae' >> ~/.zshrc
# oppure (fallback se env non propaga):
mkdir -p ~/.claude && echo "itsiae" > ~/.claude/.devforge-gate-scope
```
```

### 3.2 — `CHANGELOG.md`

Aggiungi entry DOPO l'header e PRIMA di `## [1.68.0]`:

```markdown
## [1.69.0] — 2026-05-28

### **BREAKING DEFAULT CHANGE**

I 5 gate workflow DevForge (`brainstorming-gate`, `plan-gate-write`, `tdd-gate`, `pr-blind-review-gate`, `pr-premortem-gate`) ora attivano l'enforcement su **qualsiasi repository git per default**, non solo `itsiae/*`.

**Migration path (1 riga):**
```bash
# Se vuoi preservare il vecchio comportamento itsiae-only:
echo 'export DEVFORGE_GATE_SCOPE=itsiae' >> ~/.zshrc
```

### Added
- `lib/scope-check.sh` — shared library `devforge_gate_scope_active()` con priorità env > state file > default
- `DEVFORGE_GATE_SCOPE` env (`universal` default | `itsiae` opt-in legacy)
- State file fallback `~/.claude/.devforge-gate-scope` per Claude Code subprocess env propagation
- Sezione "Scope di attivazione" in `skills/siae-premortem/SKILL.md`
- Sezione "Gate Scope" in `hooks/ENV_VARS.md`
- 53 nuovi test (18 unit lib + 5 × 7 integration gate)

### Changed
- `hooks/pr-premortem-gate`, `hooks/tdd-gate`, `hooks/pr-blind-review-gate`, `hooks/plan-gate-write`, `hooks/brainstorming-gate`: scope check ora delegato a `lib/scope-check.sh`
- `hooks/brainstorming-gate`: riordinati blocchi `source` (`PLUGIN_ROOT` + lib prima del scope-check) e generalizzato commento `non-itsiae-taskable` → `no-task-id`
- `skills/siae-premortem/SKILL.md`: rimossi 2 riferimenti hardcoded a `itsiae/*` in description (L4) e body (L48)

### Fixed
- Premortem gate (v1.68.0) era no-op silenzioso fuori `itsiae/*` nonostante il metodo Klein sia universale per natura
```

### 3.3 — Version bump

In `.claude-plugin/plugin.json`: sostituisci `"version": "1.68.0"` con `"version": "1.69.0"`.

In `.claude-plugin/marketplace.json`: sostituisci `"version": "1.68.0"` con `"version": "1.69.0"`.

## Step 4 — Esegui e verifica che passa

```bash
bash tests/docs_and_version.test.sh
```

Atteso: `PASS: 9 / 9`, exit 0.

## Step 5 — Commit

```bash
git add hooks/ENV_VARS.md CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json tests/docs_and_version.test.sh
git commit -m "docs(release): bump to v1.69.0 with universal gate scope BREAKING default

Documents DEVFORGE_GATE_SCOPE env (universal default, itsiae opt-in legacy)
with 1-line migration path. plugin.json + marketplace.json aligned at 1.69.0.

Co-Authored-By: SIAE DevForge"
```

---

## Criteri di accettazione

- [ ] `bash tests/docs_and_version.test.sh` exit 0 con `PASS: 9 / 9`
- [ ] `plugin.json` e `marketplace.json` entrambi a `1.69.0`
- [ ] `CHANGELOG.md` entry v1.69.0 contiene BREAKING + DEVFORGE_GATE_SCOPE + migration path
- [ ] `hooks/ENV_VARS.md` sezione "Gate Scope" con env var + state file documentati
