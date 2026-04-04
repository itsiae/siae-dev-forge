# Design: DevForge Infrastructure Hardening

**Data:** 2026-04-02
**Autore:** Lorenzo De Tomasi + DevForge
**Story Points:** 28 SP-Umano / 11 SP-Augmented
**Approccio:** Foundation First — 12 deliverable (D1-D11, con D6b) in PR atomiche ordinate per dipendenza

---

## Contesto

L'infrastruttura DevForge (hook, lib, test) ha accumulato debito tecnico in 10 aree:

1. Stato runtime hardcoded in `~/.claude/` — impedisce CI/sandbox/test ermetici
2. `session-start` monolitico — slow startup, hard to debug
3. `plugin.json` description manuale — drift con realtà (README 30, marketplace 34, plugin.json 35, repo 36)
4. Frontmatter parser regex — fragile su YAML reale
5. Test suite senza livelli — mix statico/ambientale
6. Gate con comportamento fail-open/fail-closed implicito
7. `sub-skill-gate` prerequisiti hardcoded — drift con skill reali
8. `skills-core.js` type/phase da mappe hardcoded — non derivati da frontmatter
9. Plumbing bug: sentinel in CWD (`logger.sh:163`) vs state in `~/.claude` (`devforge-context-always:107`)
10. Session stats imprecise (`devforge-context-always:77` — skills count via `grep -c '.'` su CSV) e JSON parsing grep/sed-based in hook critici

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

### Fix espliciti inclusi nella migrazione

**Bug ALTO 2 — Sentinel piano in CWD:** `logger.sh:166` (`devforge_set_mode`) scrive il sentinel in `$(pwd)/.devforge-active-plan`, ma `devforge-context-always:108` lo cerca in `${STATE_DIR}/.devforge-active-plan`. Fix: `devforge_set_mode()` e `devforge_clear_mode()` usano `${DEVFORGE_STATE_DIR}` invece di `$(pwd)`.

**Bug ALTO 1 — Conteggio skill CSV:** `post-skill:49-51` scrive le skill come CSV su una riga (`a,b,c`), ma `devforge-context-always:77` conta le righe con `grep -c '.'` (sempre 1). Fix: cambiare il formato di `.devforge-session-skills` da CSV inline a **una skill per riga**. Aggiornare `post-skill` per appendere con `echo "$SKILL_NAME" >> file` (con dedup) e `devforge-context-always` per contare con `wc -l`.

**Bug MEDIO 3 — Output sporco con pipefail:** `devforge-context-always:77` usa `cat file | grep -c '.' || echo "0"` che con `set -euo pipefail` produce `0` su riga separata quando il file non esiste. Fix: sostituire con `SKILLS=$(wc -l < "$file" 2>/dev/null || echo "0")` dopo la migrazione a una skill per riga.

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
- `plugin.json`: campo `description` rigenerato automaticamente
- `marketplace.json`: campo `description` rigenerato dallo stesso script (stessa logica, file diverso)
- `README.md`: riga con conteggi skill/hook/comandi rigenerata (regex match + replace sulla riga esistente)
- `version`, `author`, `repository` restano manuali in tutti i file

### File impattati
- Nuovo: `scripts/generate-manifest.js`
- Modificato: `plugin.json` (output)
- Modificato: `.claude-plugin/marketplace.json` (output)
- Modificato: `README.md` (riga conteggi)
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

---

## D7: Trigger strutturati nel frontmatter

### Problema
`skills-core.js:288-298` estrae i trigger dalla `description` con regex. La description mixa scopo e keyword di attivazione in prosa libera. Le mappe `nameTypeMap` (righe 181-201) e `namePhaseMap` (righe 225-255) sono hardcoded: 8 skill mancano da `nameTypeMap`, 12 da `namePhaseMap`.

### Soluzione
Aggiungere 3 campi strutturati al frontmatter YAML di ogni SKILL.md:

```yaml
---
name: siae-brainstorming
description: >
  Guida il processo di design da idea a design doc approvato [...]
triggers:
  - feature nuova
  - design
  - come procediamo
  - quale approccio
  - trade-off
  - bug fix
  - refactoring
type: Rigid
sdlc_phase: "2. Design"
---
```

- **`triggers`**: lista YAML di keyword/frasi. Sostituisce il parsing `Trigger:` dalla description.
- **`type`**: `Rigid | Flexible | Auto`. Sostituisce `nameTypeMap`.
- **`sdlc_phase`**: stringa. Sostituisce `namePhaseMap`. Campo già parzialmente supportato da `readPhaseFromFrontmatter()`.

Modifiche a `skills-core.js`:
1. `extractFrontmatter()` estrae anche `triggers`, `type`, `sdlc_phase` (dopo D5/js-yaml questo viene gratis; senza D5, i campi sono parsabili con regex semplice)
2. `inferSkillMeta()` usa i campi frontmatter come source primaria; le mappe hardcoded diventano fallback e poi vengono rimosse
3. Il campo `trigger` nella tabella catalogo diventa `triggers.join(', ')` troncato a 120 char

### File impattati
- 37 `skills/*/SKILL.md` (aggiunta campi frontmatter — meccanico, automabile)
- `lib/skills-core.js` (`extractFrontmatter` + `inferSkillMeta` semplificati, ~70 righe rimosse)

### Dipendenza
Beneficia da D5 (YAML parser). Funziona anche senza.

### Test
```bash
# Verifica che ogni SKILL.md abbia i 3 campi obbligatori
node -e "
const {findSkillsInDir, extractFrontmatter} = require('./lib/skills-core');
const skills = findSkillsInDir('./skills');
const missing = skills.filter(s => {
  const fm = extractFrontmatter(s.filePath);
  return !fm.triggers || !fm.type || !fm.sdlc_phase;
});
if (missing.length) { console.error('Missing fields:', missing.map(s=>s.name)); process.exit(1); }
console.log('All', skills.length, 'skills have structured frontmatter');
"
```

---

## D8: Separare output macchina da output prompt

### Problema
`buildCatalog()` (skills-core.js:307-346) restituisce `.table` con righe Markdown + 8 righe di disambiguazione (329-339). Il CLI entry point (riga 355) stampa tutto su stdout. Il test in `run-all.sh:145` conta `wc -l` sull'intero output → 45 righe invece di 36 skill reali (bug MEDIO 4).

### Soluzione
Aggiungere flag `--format` al CLI entry point:

```javascript
if (require.main === module) {
  const pluginDir = process.argv[2] || path.resolve(__dirname, '..');
  const format = process.argv[3] || 'markdown';
  const catalog = buildCatalog(pluginDir);

  if (format === 'json') {
    const out = catalog.skills.map(s => ({
      name: s.name,
      triggers: s.triggers || [],
      type: s.type,
      phase: s.phase,
    }));
    process.stdout.write(JSON.stringify(out, null, 2) + '\n');
  } else {
    process.stdout.write(catalog.table + '\n');
  }
}
```

### Consumatori
- `session-start:92` e `devforge-reinject:40` → `markdown` (default, invariato)
- `tests/run-all.sh:144` → cambia a `json`, conta con `node -e "...JSON.parse(d).length"`
- Eval/CI futuri → usano `json`

### File impattati
- `lib/skills-core.js` (CLI entry point, ~10 righe)
- `tests/run-all.sh` (1 test, ~5 righe)

### Dipendenza
Nessuna. Parallelizzabile con D7.

---

## D9: Shortlist contestuale in reinject

### Problema
`session-start` inietta l'intero catalogo (37 skill × ~120 char = ~4.5KB) al primo prompt. `devforge-reinject` lo re-inietta ogni 20 messaggi. La maggior parte delle skill non è rilevante per la query corrente.

### Soluzione
Nuova funzione `matchSkills(query, skills, topN)` in `skills-core.js`:

```javascript
function matchSkills(query, skills, topN = 7) {
  const q = query.toLowerCase();
  const scored = skills.map(s => {
    const triggers = s.triggers || [];
    const hits = triggers.filter(t => q.includes(t.toLowerCase()));
    return { ...s, score: hits.length };
  });
  return scored
    .filter(s => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, topN);
}
```

### Dove si usa
- `devforge-reinject` — invece del catalogo completo, inietta shortlist basata sul messaggio utente (disponibile via stdin in hook UserPromptSubmit)
- `session-start` — continua a iniettare catalogo completo (primo prompt, nessuna query)

### Fallback
Se `matchSkills` ritorna 0 risultati → inietta catalogo completo.

### CLI
```bash
node lib/skills-core.js <plugin-root> shortlist "la mia query"
```

### File impattati
- `lib/skills-core.js` (~15 righe nuova funzione + CLI branch)
- `hooks/devforge-reinject` (usa shortlist)

### Dipendenza
Beneficia da D7 (trigger strutturati). Funziona anche col parsing attuale.

### Rischio
Matching troppo aggressivo potrebbe escludere skill rilevanti. Mitigazione: `topN = 7` conservativo + fallback a catalogo completo. Raffinabile con dati da D10.

---

## D10: Eval come gate CI con soglie

### Problema
`run-trigger-eval.py` e `run-trigger-regression.sh` esistono ma non hanno soglie di accettazione. Non c'è baseline storica. Il runner non fallisce CI.

### Soluzione

**1. Soglie per skill negli eval file (29 file):**
```json
{
  "skill": "siae-brainstorming",
  "threshold": { "precision": 0.8, "recall": 0.9 },
  "queries": [...]
}
```

**2. `run-trigger-regression.sh` diventa gate:**
- Legge `threshold` da ogni eval file
- Confronta risultati vs soglia
- Exit code 1 se qualsiasi skill è sotto soglia
- Report summary in `evals/results/regression-summary.json`

**3. Baseline storica:**
Dopo ogni run, salva risultati in `evals/results/<skill>-<date>.json`. Delta > 10% rispetto all'ultimo risultato = warning.

### File impattati
- `evals/trigger-evals/*.json` (29 file — campo `threshold`)
- `tests/run-trigger-regression.sh` (~20 righe threshold check + summary)
- `tests/run-trigger-eval.py` (~10 righe per leggere/validare threshold)

### Dipendenza
Nessuna. Più utile dopo D7.

---

## D11: Strumentazione mismatch attivazione (ridotta)

### Problema
Non c'è modo di sapere quando una skill viene invocata tardi o quando il catalogo suggerisce skill mai invocate. Il feedback loop per migliorare il triggering è cieco.

### Soluzione (versione pragmatica)

**1. `hooks/post-skill` — aggiungere `message_number` al log:**
```bash
MSG_COUNT=$(cat "${DEVFORGE_STATE_DIR}/.devforge-message-counter" 2>/dev/null || echo "0")
devforge_log "$SKILL_NAME" "skill_invoked" \
  "{\"message_number\":$MSG_COUNT,\"phase\":\"$PHASE\"}"
```

**2. `hooks/stop-gate` — loggare `skill_late_invocation`:**
Skill invocata dopo messaggio 5 → evento `skill_late_invocation` nel JSONL.

### Scope ridotto (no shortlist tracking)
La versione completa (confronto shortlist vs invocazione) richiede che D9 sia stabile e che `devforge-reinject` salvi la shortlist per ogni messaggio. Complessità significativa, rimandata.

### File impattati
- `hooks/post-skill` (~5 righe)
- `hooks/stop-gate` (~10 righe)

### Dipendenza
Nessuna per la versione ridotta. Versione completa dipende da D9.

---

## Decisione architetturale (D7-D11)

| # | Decisione | Alternative scartate | Motivazione |
|---|-----------|---------------------|-------------|
| ADR-7 | Trigger/type/phase nel frontmatter di ogni SKILL.md | Registry centralizzato, ibrido | Colocation: ogni skill dichiara il suo contratto. Il registry crea drift — esattamente il problema che stiamo risolvendo |
| ADR-8 | Flag `--format json` in CLI skills-core.js | Funzione separata, file separato | Minima superficie, stesso entry point, backward compatible |
| ADR-9 | Shortlist solo in reinject, catalogo completo in session-start | Shortlist ovunque | Il primo prompt non ha query, serve catalogo completo per discovery |
| ADR-10 | Soglie nel JSON eval stesso | File soglie separato | Colocation: soglia vive accanto alle query che la testano |
| ADR-11 | Solo late-invocation logging (no shortlist tracking) | Tracking completo shortlist vs invocazione | Complessità sproporzionata finché D9 non è stabile |

---

## Ordine di esecuzione (completo D1-D11)

```
D1 (STATE_DIR) ──→ D2 (test split)
                ──→ D3 (split session-start)
                ──→ D4 (manifest) ──→ D5 (YAML parser) ──→ D7 (frontmatter)
                ──→ D6 (gate espliciti)
D8 (output separato) ──→ [indipendente, parallelizzabile con D7]
D7 (frontmatter)     ──→ D9 (shortlist)
D10 (eval gate)      ──→ [indipendente]
D11 (strumentazione) ──→ [indipendente]
```

D1 è prerequisito per D2. D4 beneficia D5. D5 beneficia D7. D8 è indipendente da D7 (parallelizzabili). D9 beneficia da D7. D10 e D11 sono indipendenti e parallelizzabili.

## Criteri di accettazione

### Infrastruttura (D1-D6b)
1. `DEVFORGE_STATE_DIR=/tmp/x tests/run-all.sh` passa senza toccare `~/.claude/`
2. `tests/run-all.sh --fast` completa in <5s con solo test statici
3. `session-start` completa in <1s (no network call sincrono)
4. `node scripts/generate-manifest.js && git diff plugin.json README.md marketplace.json` → nessun diff
5. `lib/skills-core.js` parsa correttamente frontmatter con `:` nei valori
6. Ogni gate hook ha un GATE CONTRACT header e usa `devforge_gate_check_state`
7. Zero regressioni sulla test suite esistente
8. `tdd-gate` bypassa `.tfvars` e `variables.tf` senza richiedere ciclo TDD (allineamento con SKILL.md:94)
9. `.devforge-session-skills` usa formato una-skill-per-riga (non CSV inline) e `devforge-context-always` conta con `wc -l` (fix bug ALTO 1)
10. `devforge_set_mode()` scrive sentinel in `${DEVFORGE_STATE_DIR}`, non in `$(pwd)` (fix bug ALTO 2)
11. `devforge-context-always` non produce output sporco quando `.devforge-session-skills` non esiste (fix bug MEDIO 3)

### Triggering (D7-D11)
12. Tutte le 37 SKILL.md hanno `triggers`, `type`, `sdlc_phase` nel frontmatter
13. `nameTypeMap` e `namePhaseMap` rimossi da `skills-core.js`
14. `node lib/skills-core.js <root> json | jq length` restituisce il numero esatto di skill (no disambiguazione)
15. `tests/run-all.sh` usa output JSON per conteggio catalogo (fix bug MEDIO 4)
16. `devforge-reinject` inietta shortlist (max 7 skill) invece di catalogo completo
17. Ogni eval file in `evals/trigger-evals/` ha campo `threshold`
18. `run-trigger-regression.sh` esce con codice 1 se una skill è sotto soglia
19. `post-skill` logga `message_number` in ogni evento `skill_invoked`

### Stima complessiva
**Story Points: 28 SP-Umano / 11 SP-Augmented**
