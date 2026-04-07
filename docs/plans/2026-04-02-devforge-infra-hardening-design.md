# Design: DevForge Infrastructure Hardening

**Data:** 2026-04-02
**Autore:** Lorenzo De Tomasi + DevForge
**Story Points:** 8 SP-Umano / 3 SP-Augmented
**Approccio:** Foundation First — 7 deliverable (D1-D6b) in PR atomiche ordinate per dipendenza

---

## Contesto

L'infrastruttura DevForge (hook, lib, test) ha accumulato debito tecnico in 6 aree:

1. Stato runtime hardcoded in `~/.claude/` — impedisce CI/sandbox/test ermetici
2. `session-start` monolitico — slow startup, hard to debug
3. `plugin.json` description manuale — drift con realtà (35 vs 36 skill)
4. Frontmatter parser regex — fragile su YAML reale
5. Test suite senza livelli — mix statico/ambientale
6. Gate con comportamento fail-open/fail-closed implicito

**21 file** accedono a `${HOME}/.claude/.devforge-*` con path hardcoded.

## Decisioni architetturali

| # | Decisione | Alternative scartate | Motivazione |
|---|-----------|---------------------|-------------|
| ADR-1 | `DEVFORGE_STATE_DIR` centralizzato in `lib/logger.sh` | Variabile in ogni hook | Logger è già sourced ovunque, un solo punto di definizione |
| ADR-2 | Split session-start in bootstrap + maintenance async | Hook separati registrati in hooks.json | Un solo hook con subprocess è più semplice e non richiede modifiche a hooks.json |
| ADR-3 | `generate-manifest.js` per plugin.json | Template con sed | JS può leggere skill frontmatter e produrre JSON corretto |
| ADR-4 | `js-yaml` con `package.json` a root | Vendoring, parser custom | Libreria standard, zero dipendenze native, ~30KB |
| ADR-5 | Flag `--fast`/`--integration` in run-all.sh | Suite separate | Un singolo entry point con flag è più discoverable |
| ADR-6 | Gate contract header + helper function | Documentazione esterna | Il contratto vive accanto al codice, parsabile e verificabile |

---

## D1: `DEVFORGE_STATE_DIR` — Isolamento stato runtime

### Problema
21 file accedono a `${HOME}/.claude/.devforge-*` hardcoded. Impossibile testare in isolamento, eseguire in CI, o parallelizzare sessioni.

### Soluzione
Aggiungere in `lib/logger.sh` (prima di qualsiasi uso):
```bash
DEVFORGE_STATE_DIR="${DEVFORGE_STATE_DIR:-${HOME}/.claude}"
```

Ogni hook sostituisce `${HOME}/.claude/.devforge-*` con `${DEVFORGE_STATE_DIR}/.devforge-*`.

### File impattati

| File | Variabili da migrare |
|------|---------------------|
| `lib/logger.sh:6` | `DEVFORGE_SID_FILE`, `DEVFORGE_LOG_FILE` default |
| `hooks/session-start:178,182` | `session-start-ns`, `devforge-user` |
| `hooks/pre-commit:33,37` | `session-skills`, `tool-counter` |
| `hooks/post-skill:25,46` | `skill-start`, `session-skills` |
| `hooks/stop-gate:22,26,43-45` | `session-end-guard`, `skill-start`, `session-start-ns`, `session-commits`, `session-skills` |
| `hooks/tdd-gate:50+` | `session-skills` |
| `hooks/plan-gate:15` | `session-skills` |
| `hooks/sub-skill-gate` | `session-skills` |
| `hooks/devforge-reinject:19` | `message-counter` |
| `hooks/devforge-context-always` | variabili state |
| `hooks/capture-test-result` | variabili state |
| `tests/run-all.sh:386-404` | tutti i riferimenti test |

### Regola
Hook che sourciano `lib/logger.sh` ereditano `DEVFORGE_STATE_DIR` automaticamente. Hook che non lo sourciano definiscono localmente: `DEVFORGE_STATE_DIR="${DEVFORGE_STATE_DIR:-${HOME}/.claude}"`.

### Backward compatibility
100% — il default è identico al comportamento attuale.

### Test
```bash
DEVFORGE_STATE_DIR=/tmp/devforge-test tests/run-all.sh
```

---

## D2: Test ermetici vs ambientali

### Problema
`run-all.sh` mescola test statici (lint, validazione file) con test che mutano stato in `~/.claude/`. Un fallimento ambientale invalida tutta la suite.

### Soluzione (dipende da D1)

1. In cima a `run-all.sh`, se `DEVFORGE_STATE_DIR` non è settato, crea tmpdir:
```bash
if [ -z "${DEVFORGE_STATE_DIR:-}" ]; then
    export DEVFORGE_STATE_DIR=$(mktemp -d)
    CLEANUP_STATE_DIR=1
fi
```

2. Flag `--fast` — solo test statici (validazione skill, frontmatter, naming, hook syntax). Zero I/O su state dir. Target: <5 secondi.

3. Flag `--integration` (default) — tutto, inclusi test che invocano hook. Usa `DEVFORGE_STATE_DIR` per isolamento.

4. Cleanup a fine suite se `CLEANUP_STATE_DIR=1`.

### File impattati
- `tests/run-all.sh` (flag parsing + tmpdir logic)
- Eventuali `tests/*.test.sh` che scrivono state

---

## D3: Split `session-start`

### Problema
`session-start` esegue 6 responsabilità in sequenza, di cui solo una è critica per il primo prompt.

| Fase | Cosa fa | Blocca startup? | Critica? |
|------|---------|-----------------|----------|
| A | Statusline install | Sì (~200ms) | No |
| B | MCP setup | No (già async) | No |
| C | Banner stderr | Sì (trascurabile) | Cosmetico |
| D | Version check + auto-update | Sì (~1-3s) | No |
| E | Context injection | Sì | **Sì** — ragion d'essere |
| F | Telemetria, PR merge detect | Sì (~500ms) | No |

### Soluzione

**`session-start` (bootstrap minimo, sincrono):**
- C: Banner stderr
- E: Context injection (skill catalog, using-devforge, branching check)
- Output JSON `additional_context`

**`session-maintenance` (nuovo script, async):**
- A: Statusline install
- B: MCP setup (spostato qui)
- D: Version check + auto-update
- F: Telemetria, session-start-ns, devforge-user, PR merge detection

Ultima riga di `session-start`:
```bash
bash "${PLUGIN_ROOT}/hooks/session-maintenance" &
```

### Rischio e mitigazione
Se `session-maintenance` fallisce silenziosamente, telemetria e update check si perdono. Mitigazione: log errori in `${DEVFORGE_STATE_DIR}/devforge-maintenance.log`.

### File impattati
- `hooks/session-start` (ridotto a ~60 righe)
- Nuovo: `hooks/session-maintenance` (~120 righe, estratte da session-start)

---

## D4: Manifest generato

### Problema
`plugin.json` description dice "35 skill" ma ne esistono 36. Aggiornamento manuale, soggetto a drift.

### Soluzione
Nuovo script `scripts/generate-manifest.js`:

1. Conta directory in `skills/` → skill count
2. Conta hook attivi da `hooks/hooks.json` → hook count
3. Conta directory in `commands/` → command count
4. Legge agent count da plugin.json (campo manuale)
5. Rigenera campo `description` in `plugin.json` con conteggi reali

### Quando eseguirlo
- Pre-commit: se file in `skills/`, `hooks/`, `commands/` sono staged → rigenera e restage `plugin.json`
- CI: check che `plugin.json` sia allineato (fail se dirty dopo generate)

### Scope
Solo `description` viene rigenerata. `version`, `author`, `repository` restano manuali.

### File impattati
- Nuovo: `scripts/generate-manifest.js`
- Modificato: `plugin.json` (output)
- Modificato: `hooks/pre-commit` (opzionale auto-run)

---

## D5: YAML parser per frontmatter

### Problema
`lib/skills-core.js:35-74` usa regex per parsare frontmatter. Fragile su valori con `:`, stringhe quotate, frontmatter con nuovi campi.

### Soluzione (beneficia da D4)
Sostituire parser regex con `js-yaml`:

```javascript
const yaml = require('js-yaml');

function extractFrontmatter(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;
  try {
    return yaml.load(match[1]);
  } catch { return null; }
}
```

### Dipendenza
- `package.json` minimal a root con `js-yaml` come unica dipendenza
- Verificare `.gitignore` per `node_modules/`

### File impattati
- Nuovo: `package.json` (minimal, root)
- Modificato: `lib/skills-core.js` (extractFrontmatter semplificato)

---

## D6: Gate fail-open/fail-closed espliciti

### Problema
I gate hook non dichiarano il comportamento quando manca contesto. Il comportamento è implicito nella logica dei branch.

### Soluzione

**1. Header strutturato in ogni gate:**
```bash
# ─── GATE CONTRACT ───
# Behavior:  fail-open | fail-closed
# Requires:  SESSION_SKILLS_FILE (state), PLUGIN_ROOT (env)
# Reads:     ${DEVFORGE_STATE_DIR}/.devforge-session-skills
# On-missing: proceed silently (fail-open)
# ─────────────────────
```

**2. Helper in `lib/logger.sh`:**
```bash
devforge_gate_check_state() {
    local file="$1" gate_name="$2" behavior="$3"
    if [ ! -f "$file" ]; then
        if [ "$behavior" = "fail-closed" ]; then
            devforge_log "$gate_name" "blocked" "{\"reason\":\"state_file_missing\",\"file\":\"$file\"}"
            return 1
        fi
        return 0
    fi
    cat "$file"
}
```

**3. Classificazione per hook:**

| Hook | Attuale | Proposta | Motivazione |
|------|---------|----------|-------------|
| `pre-commit` (git commit) | fail-open implicito | **fail-closed** | commit senza workflow = violazione SDLC |
| `pre-commit` (checkout -b) | fail-open implicito | **fail-open esplicito** | creare branch senza JIRA è legittimo |
| `tdd-gate` | fail-open su path vuoto | **fail-open esplicito** | nessun path = non è file edit |
| `plan-gate` | fail-open implicito | **fail-closed** | plan mode senza brainstorming = violazione |
| `sub-skill-gate` | fail-open implicito | **fail-closed** | prerequisiti non verificabili = blocca |
| `stop-gate` (verification) | fail-open implicito | **fail-open esplicito** | telemetria persa accettabile, bloccare stop no |

### Rischio
Cambiare gate da fail-open a fail-closed potrebbe bloccare utenti in scenari legittimi. Solo `pre-commit` (commit), `plan-gate` e `sub-skill-gate` diventano fail-closed.

### File impattati
- `lib/logger.sh` (nuovo helper)
- 6-8 hook gate (header + refactor a helper)

---

## D6b: TDD gate context-aware per IaC/config

### Problema (bug di allineamento)
`tdd-gate:37` tratta `.tf` e `.hcl` come codice produzione → richiede ciclo TDD completo.
Ma `skills/siae-tdd/SKILL.md:94` dice: "Config pura (.env, .yml, **terraform vars**) → NO — validate/plan basta".

Risultato: il gate blocca file IaC puri (es. `security-groups.tf` con solo resource declarations) chiedendo un test fallente, anche se la policy della skill prevede eccezione.

### Soluzione
Aggiungere un bypass in `tdd-gate`, dopo il check estensione e prima del check `SESSION_SKILLS`, per file IaC "config pura":

```bash
# IaC config-only files: bypass TDD per SKILL.md:94
# "Config pura (.env, .yml, terraform vars) → NO — validate/plan basta"
IAC_CONFIG_BYPASS="\.tfvars$|\.auto\.tfvars$|variables\.tf$|terraform\.tfvars$"
if echo "$FILE_PATH" | grep -qE "$IAC_CONFIG_BYPASS"; then
    echo '{}'
    exit 0
fi
```

### Confine
- **Bypass TDD:** `.tfvars`, `variables.tf`, `terraform.auto.tfvars` (pura dichiarazione di valori)
- **Richiede TDD:** `main.tf`, `*.tf` con risorse/moduli (contengono logica infrastrutturale)

### Rischio
Minimo — i file bypassati sono dichiarativi per definizione. Se un team mette logica in `variables.tf`, il rischio è accettabile perché `terraform validate` e `terraform plan` coprono la validazione.

### File impattati
- `hooks/tdd-gate` (aggiunta pattern bypass)
- `tests/run-all.sh` (nuovo test case per bypass IaC)

---

## Ordine di esecuzione

```
D1 (STATE_DIR) ──→ D2 (test split)
                ──→ D3 (split session-start)
                ──→ D4 (manifest) ──→ D5 (YAML parser)
                ──→ D6 (gate espliciti)
```

D1 è prerequisito per D2. D4 beneficia D5. D3, D6 e D6b sono indipendenti. D6b può essere implementato insieme a D6 nella stessa PR.

## Criteri di accettazione

1. `DEVFORGE_STATE_DIR=/tmp/x tests/run-all.sh` passa senza toccare `~/.claude/`
2. `tests/run-all.sh --fast` completa in <5s con solo test statici
3. `session-start` completa in <1s (no network call sincrono)
4. `node scripts/generate-manifest.js && git diff plugin.json` → nessun diff
5. `lib/skills-core.js` parsa correttamente frontmatter con `:` nei valori
6. Ogni gate hook ha un GATE CONTRACT header e usa `devforge_gate_check_state`
7. Zero regressioni sulla test suite esistente
8. `tdd-gate` bypassa `.tfvars` e `variables.tf` senza richiedere ciclo TDD (allineamento con SKILL.md:94)
