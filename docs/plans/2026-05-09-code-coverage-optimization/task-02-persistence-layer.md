# Task 02 — Persistence Layer (P3 + ST7)

**Goal:** Persistere output di tutti gli script in `.code-coverage/*.json` con mtime-based invalidation; introdurre template caching ONCE/session; auto-aggiungere `.code-coverage/` al `.gitignore` del target repo.

**SP:** 1.5 (Augmented)
**Fix IDs covered:** P3 + ST7
**Branch:** `feat/code-coverage-opt-persistence`
**Dipendenze:** task-01 (quick-wins già merged)

---

## File coinvolti

**Modifica**:
- `skills/code-coverage/SKILL.md` (Phase 1: aggiungi redirect JSON; Principle 6: cache template)
- `skills/code-coverage/references/phase-1-discovery.md` (instructions di redirect)
- `skills/code-coverage/references/phase-5-generation.md` (template caching ONCE)

**Creazione**:
- `skills/code-coverage/lib/cache-helper.sh` (~40 LOC bash) — funzioni reusable per mtime check + ensure_gitignore
- `skills/code-coverage/lib/state-schema.json` (~80 LOC) — JSON schema dei file in `.code-coverage/`

---

## Step bite-sized

### Step 1 — Branch + assicurati che task-01 sia merged

```bash
git checkout main && git pull
git log --oneline -5  # verifica che PR1 sia in main
git checkout -b feat/code-coverage-opt-persistence
```

### Step 2 — Crea `lib/cache-helper.sh`

Crea il file con funzioni bash reusable:

```bash
#!/usr/bin/env bash
# cache-helper.sh — utility per persistence layer .code-coverage/
# Source: skills/code-coverage/lib/cache-helper.sh

set -euo pipefail

# Verifica se cache è valida (esiste e mtime > pinnacle file)
# Usage: is_cache_valid <cache-file> <pinnacle-file>
# Returns: 0 (valida) | 1 (mancante o stale)
is_cache_valid() {
  local cache="$1"
  local pinnacle="$2"
  if [ ! -f "$cache" ]; then return 1; fi
  if [ ! -f "$pinnacle" ]; then return 0; fi  # no pinnacle, cache always valid
  local cache_mtime pinnacle_mtime
  cache_mtime=$(stat -f %m "$cache" 2>/dev/null || stat -c %Y "$cache")
  pinnacle_mtime=$(stat -f %m "$pinnacle" 2>/dev/null || stat -c %Y "$pinnacle")
  [ "$cache_mtime" -gt "$pinnacle_mtime" ]
}

# Garantisce che `.code-coverage/` sia in `.gitignore` del target repo
# Usage: ensure_gitignore <target-repo-path>
# Idempotente: skip se già presente
ensure_gitignore() {
  local repo="$1"
  local gitignore="$repo/.gitignore"
  if [ ! -f "$gitignore" ]; then
    echo ".code-coverage/" > "$gitignore"
    echo "Created $gitignore with .code-coverage/ entry"
    return 0
  fi
  if grep -qE '^\.code-coverage/?$' "$gitignore"; then
    return 0  # already present
  fi
  printf '\n# Added by /code-coverage skill\n.code-coverage/\n' >> "$gitignore"
  echo "Appended .code-coverage/ to $gitignore"
}

# Inizializza directory `.code-coverage/` nel target repo
# Usage: init_workdir <target-repo-path>
init_workdir() {
  local repo="$1"
  mkdir -p "$repo/.code-coverage"
  ensure_gitignore "$repo"
  # Inizializza decisions.log se non esiste
  local log="$repo/.code-coverage/decisions.log"
  if [ ! -f "$log" ]; then
    echo "# /code-coverage decisions log — $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$log"
  fi
}

# Append a structured log entry
# Usage: log_decision <target-repo-path> <phase> <decision> <rationale>
log_decision() {
  local repo="$1"
  local phase="$2"
  local decision="$3"
  local rationale="$4"
  local ts
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '%s [%s] %s — %s\n' "$ts" "$phase" "$decision" "$rationale" >> "$repo/.code-coverage/decisions.log"
}
```

Make executable:
```bash
chmod +x skills/code-coverage/lib/cache-helper.sh
```

### Step 3 — Crea `lib/state-schema.json`

Documenta lo schema dei file persisti in `.code-coverage/`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "code-coverage skill persistence state",
  "description": "Schema dei file persisti in .code-coverage/ durante session",
  "type": "object",
  "properties": {
    "stack.json": {
      "description": "Output di detect_stack.py — invalidato da package.json mtime",
      "ref": "scripts/detect_stack.py output contract"
    },
    "size.json": {
      "description": "Output di estimate_size.py --file-list — invalidato da package.json mtime",
      "ref": "scripts/estimate_size.py output contract"
    },
    "env.json": {
      "description": "Output di validate_env.py — invalidato da package.json mtime",
      "ref": "scripts/validate_env.py output contract"
    },
    "batch-plan.json": {
      "description": "Output di plan_batches.py — TTL session",
      "ref": "scripts/plan_batches.py output contract (PR8)"
    },
    "coverage-summary.json": {
      "description": "Output framework --coverage.reporter=json-summary — TTL session",
      "ref": "framework-specific format"
    },
    "coverage-report.json": {
      "description": "Output di parse_coverage.py — TTL session",
      "ref": "scripts/parse_coverage.py output contract (PR3)"
    },
    "failures.json": {
      "description": "Output di categorize_failure.py per Phase 7 — TTL per-iter",
      "ref": "scripts/categorize_failure.py output contract (PR4)"
    },
    "deferred_files.json": {
      "description": "File deferred-by-design da Phase 5 (P2/P3 hit precoce) — escluso da Phase 6→7 gate",
      "type": "object",
      "properties": {
        "deferred": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"}
      }
    },
    "install-log.txt": {
      "description": "Log auto-install in target repo (Phase 4)",
      "type": "string"
    },
    "lockfile.bak": {
      "description": "Snapshot lockfile pre-install per rollback",
      "type": "string"
    },
    "generation-plan.txt": {
      "description": "Lista files da generare in Phase 5 (audit trail)",
      "type": "string"
    },
    "decisions.log": {
      "description": "Log centralizzato decisioni autonome (audit trail)",
      "type": "string"
    }
  },
  "definitions": {
    "session": "Una singola invocazione /code-coverage. Re-invocazione = nuova session = invalida tutto eccetto stack.json/size.json/env.json (mtime check vs package.json)."
  }
}
```

### Step 4 — SKILL.md: aggiungi Principle 7 (cache)

In `skills/code-coverage/SKILL.md` aggiungi nuovo Principle dopo Principle 6:

```
7. **State persistence + cache**. Tutti gli output strutturati delle fasi sono persisti in `.code-coverage/`. File `stack.json`, `size.json`, `env.json` sono cache-friendly: ri-letti da fasi successive solo se mtime > `package.json`/`pom.xml`/`Cargo.toml`/`pyproject.toml`. Template files (`templates/*.template.*`) caricati ONCE per (framework, session) — successivi batch rifiutano re-load. Schema completo: `skills/code-coverage/lib/state-schema.json`.
```

### Step 5 — SKILL.md: aggiungi step di init nella Phase 1

In Phase 1 (riga 67), aggiungi PRIMO step:

```
**Phase 0 (init, before Phase 1)**: source `skills/code-coverage/lib/cache-helper.sh` and run `init_workdir <target_repo>`. This creates `.code-coverage/`, ensures `.gitignore` is updated (idempotent), initializes `decisions.log`.
```

### Step 6 — SKILL.md: redirect JSON in Phase 1

In Phase 1 (riga 69), sostituisci:
```
Run `python3 skills/code-coverage/scripts/detect_stack.py <repo_path>` to produce the stack detection JSON.
```
Con:
```
Run, in parallelo:
  - `python3 skills/code-coverage/scripts/detect_stack.py <repo_path> > <repo_path>/.code-coverage/stack.json`
  - `python3 skills/code-coverage/scripts/estimate_size.py <repo_path> --file-list > <repo_path>/.code-coverage/size.json`
  - `python3 skills/code-coverage/scripts/validate_env.py <repo_path> > <repo_path>/.code-coverage/env.json`

Cache check (skip esecuzione se valida): per ogni file, run `is_cache_valid <cache-file> <repo_path>/package.json` (sourcing cache-helper.sh). Se exit 0, skip script execution e leggi cache esistente. Pinnacle file: `package.json` per JS/TS, `pyproject.toml` per Python, `pom.xml` per Maven, `build.gradle` per Gradle, `Cargo.toml` per Rust, `pubspec.yaml` per Flutter, `go.mod` per Go.

Output: i 3 file JSON in `.code-coverage/`. Read solo il subset di campi necessari per la fase corrente.
```

### Step 7 — phase-1-discovery.md: aggiungi instructions persistence

In `phase-1-discovery.md` aggiungi nuova sezione dopo l'intro:

```markdown
## Persistence layer

Tutti gli output di Phase 1 sono persisti in `.code-coverage/`:
- `stack.json` — output di `detect_stack.py`
- `size.json` — output di `estimate_size.py --file-list`
- `env.json` — output di `validate_env.py`

Per ogni script, prima di eseguire:
1. Source `skills/code-coverage/lib/cache-helper.sh`
2. `is_cache_valid .code-coverage/<file>.json <repo>/package.json` (o equivalente per stack)
3. Se exit 0: leggi cache esistente, NON eseguire script.
4. Se exit 1: esegui script e redirect output a `.code-coverage/<file>.json`.

Le 3 invocazioni script sono indipendenti — possono girare in parallelo via:
```bash
(detect_stack.py <repo> > .code-coverage/stack.json &) ; \
(estimate_size.py <repo> --file-list > .code-coverage/size.json &) ; \
(validate_env.py <repo> > .code-coverage/env.json &) ; \
wait
```
```

### Step 8 — phase-5-generation.md: template caching ONCE

Aggiungi nuova sub-section "Template caching" dopo Pre-Generation Checklist:

```markdown
### Template caching policy

Per ogni framework selezionato (es. `vitest`, `pytest`, `junit5`):
1. **PRIMO batch**: leggi `skills/code-coverage/templates/<framework>.template.*` UNA volta. Salva contenuto in variabile di sessione `_TEMPLATE_<FRAMEWORK>` (es. `_TEMPLATE_VITEST`).
2. **BATCH SUCCESSIVI** nella stessa session: NON ri-leggere il template file. Riusa la variabile cached.
3. Cache invalidata solo da nuova invocazione skill.

Razionale: per MEDIUM repo con 10 batch, ri-lettura template = ~3-9 KB × 10 = ~30-90 KB di token sprecati.
```

### Step 9 — Test smoke `cache-helper.sh`

Test `is_cache_valid`:
```bash
mkdir -p /tmp/test-cache
echo '{"k":"v"}' > /tmp/test-cache/cache.json
echo '{"deps":{}}' > /tmp/test-cache/package.json
sleep 1
touch /tmp/test-cache/cache.json  # rendi cache più recente di pinnacle
source skills/code-coverage/lib/cache-helper.sh
is_cache_valid /tmp/test-cache/cache.json /tmp/test-cache/package.json
echo "Exit (cache valida): $?"
# Output atteso: Exit (cache valida): 0

touch /tmp/test-cache/package.json  # rendi pinnacle più recente
is_cache_valid /tmp/test-cache/cache.json /tmp/test-cache/package.json
echo "Exit (cache stale): $?"
# Output atteso: Exit (cache stale): 1
```

Test `ensure_gitignore`:
```bash
rm -rf /tmp/test-gi && mkdir /tmp/test-gi
source skills/code-coverage/lib/cache-helper.sh
ensure_gitignore /tmp/test-gi
cat /tmp/test-gi/.gitignore
# Output atteso: .code-coverage/

ensure_gitignore /tmp/test-gi  # idempotente
cat /tmp/test-gi/.gitignore | wc -l
# Output atteso: 1 (non duplica)
```

Test `init_workdir`:
```bash
rm -rf /tmp/test-init && mkdir /tmp/test-init
source skills/code-coverage/lib/cache-helper.sh
init_workdir /tmp/test-init
ls -la /tmp/test-init/.code-coverage/
# Output atteso: directory esiste con decisions.log
test -f /tmp/test-init/.gitignore && echo "gitignore created"
# Output atteso: gitignore created
```

### Step 10 — Spec-reviewer

Lancia spec-reviewer su PR diff. Risolvi BLOCK/WARN.

### Step 11 — Commit + PR

```bash
git add skills/code-coverage/SKILL.md \
        skills/code-coverage/references/phase-1-discovery.md \
        skills/code-coverage/references/phase-5-generation.md \
        skills/code-coverage/lib/cache-helper.sh \
        skills/code-coverage/lib/state-schema.json
git commit -m "feat(code-coverage): persistence layer + template caching (P3, ST7)

P3: redirect JSON in .code-coverage/{stack,size,env}.json con mtime check
ST7: cross-session resume tramite cache-helper.sh
Template caching ONCE per (framework, session) in Phase 5
ensure_gitignore idempotente per .code-coverage/ in target repo
state-schema.json documenta tutti i file persisti

Refs design doc 2026-05-09-code-coverage-optimization-design.md §2.3, PR2.

Co-Authored-By: SIAE DevForge"

git push -u origin feat/code-coverage-opt-persistence
gh pr create --title "feat(code-coverage): persistence layer + template caching (P3, ST7)" --body "$(cat <<'EOF'
## Summary
- Persistence di stack/size/env in `.code-coverage/*.json` con mtime-based invalidation
- Template caching ONCE per (framework, session)
- Auto-aggiunta `.code-coverage/` al `.gitignore` target (idempotente)
- `state-schema.json` documenta gli artefatti persistiti

Refs: docs/plans/2026-05-09-code-coverage-optimization-design.md PR2

## Test plan
- [x] `is_cache_valid` valido / stale
- [x] `ensure_gitignore` idempotente
- [x] `init_workdir` crea directory + decisions.log
- [ ] Run /code-coverage 2 volte di seguito su benchmark MEDIUM, verifica seconda esecuzione skip script (cache hit)
- [ ] Spec-reviewer PASS

Co-Authored-By: SIAE DevForge
EOF
)"
```

---

## Acceptance criteria

- [ ] `lib/cache-helper.sh` esiste con 4 funzioni: `is_cache_valid`, `ensure_gitignore`, `init_workdir`, `log_decision`
- [ ] `lib/state-schema.json` documenta tutti i 12 artefatti `.code-coverage/`
- [ ] SKILL.md contiene Principle 7 (state persistence + cache)
- [ ] Phase 1 redirect JSON in `.code-coverage/` con cache check
- [ ] phase-5-generation.md contiene Template caching policy
- [ ] Smoke test cache-helper.sh tutti pass
- [ ] PR aperta, spec-reviewer PASS
- [ ] Su benchmark MEDIUM: seconda invocazione `/code-coverage` skippa execution script (verificabile in `decisions.log`)

## Note operative

- Tutti i file shell sono Bash + `stat -f` (macOS) / `stat -c` (linux) per portabilità
- Nessun nuovo Python script: questa PR è solo persistence/cache infra
- Test su `cache-helper.sh` sono inline (smoke); test framework completo è out-of-scope (followup post-PR8)
- Funzione `log_decision` verrà usata da tutte le fasi successive per audit trail
