---
status: draft
created: 2026-05-12
revised: 2026-05-12 (iter 1 — spec-review fixes)
topic: hooks-json-var-expansion-fix
owner: lodetomasi
priority: medium
sp_human: 1.4
sp_augmented: 0.7
---

# Design — Fix espansione `${CLAUDE_PLUGIN_ROOT}` in `hooks.json`

## Contesto

L'hook `SessionStart:startup` del plugin `siae-devforge@siae-devforge` v1.53.0 fallisce in Claude Code 2.1.139 con:

```
SessionStart:startup hook error
Failed with non-blocking status code: bash:
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd: No such file or directory
```

Effetto: la sessione continua (errore non-bloccante), ma il banner DevForge non viene mostrato, il contesto `using-devforge` non viene iniettato, e le telemetrie session-start non partono.

## Root cause (verificato empiricamente)

In `hooks/hooks.json`, tutte le 22 invocazioni hanno il pattern:

```json
"command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' <script>"
```

I **single quotes** attorno a `${CLAUDE_PLUGIN_ROOT}` impediscono a bash di espandere la variabile. L'hook funziona quindi solo se l'harness Claude Code **pre-sostituisce** `${CLAUDE_PLUGIN_ROOT}` nella stringa **prima** di passarla a bash. Nella versione 2.1.139 questa pre-sostituzione **non avviene** per gli hook plugin (verificato in sessione corrente).

### Evidenze

| Test | Risultato |
|---|---|
| Comando verbatim da `hooks.json` (single-quoted) | ❌ `No such file or directory` |
| Stesso comando con `CLAUDE_PLUGIN_ROOT` esportata | ❌ Single-quotes bloccano espansione |
| Path pre-espanso (`bash /full/path/run-hook.cmd session-start`) | ✅ Banner DevForge emesso, JSON valido |
| File `run-hook.cmd` presente ed eseguibile | ✅ 1460 byte, `rwxr-xr-x` |

Il file `run-hook.cmd` è **integro**: il bug è esclusivamente nel **quoting** del comando JSON.

## Trade-off considerati

| Opzione | Descrizione | Pro | Contro | Esito |
|---|---|---|---|---|
| **A — Double-quote escape JSON** | Sostituire `'…'` → `\"…\"` in 22 comandi | Chirurgico, zero nuove deps, riusa path bash | Funziona solo se harness inietta var in env (gated da T01); **rischio corruzione JSON** se replacement non escape-aware (mitigato in T03 da `json.loads` pre-write) | **Scelta** |
| B — Wrapper fallback | Shim bash che calcola path da `installed_plugins.json` se var vuota | Bulletproof | JSON pesante, deps `jq`, complessità | Piano B documentato (se T01 fallisce) |
| C — Cherry-pick Node launcher da `feat/windows-telemetry-enforcement` | Adottare `run-hook.js` | Chiude anche Windows | Branch parallelo WIP, 29 commit ahead, ha lo stesso bug single-quote | Out of scope |

**Decisione**: Opzione A preceduta da un **pre-test empirico** (T01) che verifica se `CLAUDE_PLUGIN_ROOT` è effettivamente popolata nell'env del processo hook. Se SI, A è sufficiente; se NO, scaliamo a B.

## Decisione architetturale (ADR)

- **ADR-001 — Convenzione quoting**: in `hooks.json` plugin Claude Code, il pattern canonico per riferire env vars iniettate dall'harness è `"\"${VAR}\""` nel JSON source (che equivale al byte-pattern letterale `"${VAR}"` ricevuto da bash). Questo consente espansione bash naturale. Documentato in `hooks/ENV_VARS.md`.
- **ADR-002 — `CLAUDE_PLUGIN_ROOT` è una env var iniettata dall'harness** nel processo hook. Assunto **gated** da T01 (probe empirico). Da NON valorizzare nel plugin.
- **ADR-003 — Coordinamento merge con branch `feat/windows-telemetry-enforcement`**:
  - Branch parallelo verificato: **17** invocazioni (non 22), pattern `node '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.js'` (Node launcher), file target `run-hook.js` (Node, non bash `run-hook.cmd`).
  - Conflitto di merge **certo** sulle 22 righe modificate da questo fix vs le 17 righe modificate dal branch parallelo (porzioni si sovrappongono al 100% perché stesso JSON path `hooks.SessionStart[].hooks[].command`).
  - **Strategia esplicita**: questo fix viene mergiato **prima** del branch `feat/windows-telemetry-enforcement`. Quando il branch parallelo rebaseerà su main, dovrà applicare lo stesso pattern double-quote a tutti i 17+ comandi `node` (regex equivalente, replacement identico modulo launcher). La PR di questo fix deve riferire esplicitamente nel commit message: "When `feat/windows-telemetry-enforcement` rebases, apply identical double-quote escape to its 17 `node` invocations."
  - **Owner coordinamento**: `lodetomasi` (single dev, no team coordination needed; nota su PR description).

## Componenti

| File | Modifica | Tipo |
|---|---|---|
| `hooks/hooks.json` | 22 sostituzioni JSON-escape-aware: `'${CLAUDE_PLUGIN_ROOT}/...'` → `\"${CLAUDE_PLUGIN_ROOT}/...\"` (byte literal in file = backslash+dquote+`${...}`+/.../+backslash+dquote) | Edit |
| `tests/hooks/hooks-json-var-expansion.test.sh` | Test bash: regex + JSON valid + jq runtime expansion smoke | New (naming `*.test.sh` allineato a 3 test già wired) |
| `tests/run-all.sh` | Aggiungi blocco invocazione nuovo test in posizione coerente (dopo riga 1140, blocco `telfunc_ok` section) | **Obbligatorio** (no auto-discovery — verificato) |
| `hooks/ENV_VARS.md` | Nuova sezione "Plugin root resolution: `CLAUDE_PLUGIN_ROOT`" con 2 esempi (`JSON source` vs `byte literal in file`) | Edit |

## Flusso fix (TDD)

### T01 — Pre-test empirico (spike)

**Goal**: verificare se `CLAUDE_PLUGIN_ROOT` è iniettata nell'env del processo hook da Claude Code 2.1.139.

**Setup (cache-aware)**:
- Il plugin carica `hooks.json` da `~/.claude/plugins/cache/siae-devforge/siae-devforge/1.53.0/hooks/` (separato dal repo — verificato).
- Probe richiede modifica della **cache**, non del repo (memory: `reference_plugin_cache_sync.md`).

**Steps**:
1. Crea `hooks/__probe-env` nel repo:
   ```bash
   #!/usr/bin/env bash
   {
     date -u +%FT%TZ
     echo "CLAUDE_PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT:-<EMPTY>}"
     env | grep -i claude_plugin
   } >> /tmp/devforge-env-probe.log 2>&1
   echo '{}'
   ```
2. Aggiungi entry in `hooks/hooks.json` come `UserPromptSubmit` (1 hook in più, scope minimo):
   ```json
   {"type": "command", "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/__probe-env\"", "timeout": 3}
   ```
3. **Sync cache** (operazione 🟡 MEDIO):
   ```bash
   CACHE=~/.claude/plugins/cache/siae-devforge/siae-devforge/1.53.0
   cp hooks/hooks.json "$CACHE/hooks/hooks.json"
   cp hooks/__probe-env "$CACHE/hooks/__probe-env"
   chmod +x "$CACHE/hooks/__probe-env"
   ```
4. Riavvia Claude Code (nuova sessione, NON resume), invia 1 prompt qualsiasi.
5. Ispeziona `/tmp/devforge-env-probe.log`:
   - **Outcome SI**: file contiene `CLAUDE_PLUGIN_ROOT=/Users/.../1.53.0` → ADR-002 confermato → procedi T02.
   - **Outcome NO**: file contiene `CLAUDE_PLUGIN_ROOT=<EMPTY>` → ADR-002 falsificato → escalation Opzione B (sub-design).

**Cleanup post-probe (obbligatorio prima di T02)**:
```bash
git checkout hooks/hooks.json                      # ripristina repo
rm hooks/__probe-env                                # rimuove probe da repo
cp hooks/hooks.json "$CACHE/hooks/hooks.json"       # ripristina cache
rm -f "$CACHE/hooks/__probe-env"                    # rimuove probe da cache
rm -f /tmp/devforge-env-probe.log                   # logfile
```

T01 è uno **spike** — NON viene committato. Output documentato in commit `chore(spike): probe CLAUDE_PLUGIN_ROOT env injection` solo come testimonianza del log (se interessa), altrimenti scartato.

### T02 — Test RED (`hooks-json-var-expansion.test.sh`)

```bash
#!/usr/bin/env bash
# tests/hooks/hooks-json-var-expansion.test.sh
set -euo pipefail
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOKS_JSON="${PLUGIN_ROOT}/hooks/hooks.json"

# Pre-flight: jq disponibile?
command -v jq >/dev/null || { echo "FAIL: jq non disponibile"; exit 1; }

# Assert 1: zero occorrenze del pattern single-quoted '${CLAUDE_PLUGIN_ROOT}
single_count=$(grep -cF "'\${CLAUDE_PLUGIN_ROOT}" "$HOOKS_JSON" || true)
[ "$single_count" -eq 0 ] || {
  echo "FAIL: hooks.json contiene $single_count single-quoted \${CLAUDE_PLUGIN_ROOT}"
  grep -nF "'\${CLAUDE_PLUGIN_ROOT}" "$HOOKS_JSON" || true
  exit 1
}

# Assert 2: 22 occorrenze del byte-pattern escaped-dquote \"${CLAUDE_PLUGIN_ROOT}
# (Letterale nel file: backslash + dquote + $ + { + CLAUDE_PLUGIN_ROOT + } )
escaped_count=$(grep -cF '\"${CLAUDE_PLUGIN_ROOT}' "$HOOKS_JSON" || true)
[ "$escaped_count" -eq 22 ] || {
  echo "FAIL: attese 22 occorrenze escaped-dquote, trovate $escaped_count"
  exit 1
}

# Assert 3: JSON valido
jq . "$HOOKS_JSON" >/dev/null || { echo "FAIL: JSON invalido"; exit 1; }

# Assert 4 (smoke runtime): jq -r estrae OGNI command e bash lo espande correttamente
total=0; failed=0
while IFS= read -r cmd; do
  total=$((total+1))
  expanded=$(CLAUDE_PLUGIN_ROOT=/tmp/probe-root bash -c "echo $cmd")
  case "$expanded" in
    *"/tmp/probe-root/hooks/"*) ;;
    *) echo "FAIL[$total]: $cmd → $expanded"; failed=$((failed+1));;
  esac
done < <(jq -r '.hooks | to_entries[] | .value[] | .hooks[]? | .command' "$HOOKS_JSON")
[ "$failed" -eq 0 ] || { echo "FAIL: $failed/$total hooks non si espandono"; exit 1; }
[ "$total" -eq 22 ] || { echo "FAIL: attese 22 commands, trovate $total"; exit 1; }

echo "PASS: hooks.json var expansion conforme (22 hooks, JSON valid, runtime expansion OK)"
```

Run pre-fix → RED (Assert 1 trova 22 hit, Assert 2 trova 0).

### T03 — Fix + GREEN + docs

**Fix `hooks/hooks.json` (escape-aware)**:

```bash
python3 - <<'PY'
import json, re, pathlib
p = pathlib.Path("hooks/hooks.json")
text = p.read_text()
# Replacement: single-quoted '${CLAUDE_PLUGIN_ROOT}/hooks/X' → escaped-dquote \"${CLAUDE_PLUGIN_ROOT}/hooks/X\"
# r'\\"\1\\"' produce nel file letterale:  \  "  (capture)  \  "
new = re.sub(r"'(\$\{CLAUDE_PLUGIN_ROOT}/hooks/[^']+)'", r'\\"\1\\"', text)
assert text != new, "no replacement done"
# Validate BEFORE write — protegge da corruzione
json.loads(new)
p.write_text(new)
print("done")
PY
```

Verifica dry-run (test in fase di design, prima del commit):
- ✅ JSON VALID after replacement (verificato)
- ✅ single-quoted remaining: 0
- ✅ escaped-dquote count: 22
- ✅ sample line: `"command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",`

**Wire test in `tests/run-all.sh`** (dopo riga 1140, blocco telfunc):

```bash
# Test hooks.json variable expansion (fix: CLAUDE_PLUGIN_ROOT single-quote bug)
if bash "${PLUGIN_ROOT}/tests/hooks/hooks-json-var-expansion.test.sh" >/dev/null 2>&1; then
  echo "  PASS  hooks.json: \${CLAUDE_PLUGIN_ROOT} expansion (22 commands, runtime smoke)"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  hooks.json: \${CLAUDE_PLUGIN_ROOT} single-quote bug presente o JSON invalido"
  telfunc_fail=$((telfunc_fail + 1))
fi
```

**Aggiunge sezione a `hooks/ENV_VARS.md`** (in fondo al file):

```markdown
## Plugin root resolution

| Env var | Source | Description |
|---|---|---|
| `CLAUDE_PLUGIN_ROOT` | Iniettata da Claude Code nell'env del processo hook | Path assoluto della directory installata del plugin (es. `~/.claude/plugins/cache/siae-devforge/siae-devforge/1.53.0`). |

### Convenzione quoting in `hooks.json`

**Nel JSON source** (sorgente con escape):
```json
"command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start"
```

**Byte literal nel file** (quello che si legge con cat):
```
"command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start"
```

**Stringa ricevuta da bash dopo parse JSON da harness**:
```
bash "${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" session-start
```

Le double-quotes (escaped come `\"` in JSON) sono **necessarie** per consentire a bash di espandere `${CLAUDE_PLUGIN_ROOT}` iniettata dall'harness. Single quotes bloccherebbero l'espansione → hook non parte (`No such file or directory`).
```

Run `tests/hooks/hooks-json-var-expansion.test.sh` → GREEN. Run `tests/run-all.sh` → suite complessiva PASS.

## Gestione errori

| Errore | Mitigazione |
|---|---|
| Path con spazi su Windows | Double-quote protegge automaticamente |
| Path con `$` letterale | Improbabile (cache path SIAE); Assert 4 smoke usa `/tmp/probe-root` controlled |
| `CLAUDE_PLUGIN_ROOT` non in env del processo hook | T01 lo rileva → escalation Opzione B (sub-design) |
| Regressione su altri hooks | Assert 1+2 coprono TUTTE le 22 occorrenze (count check stretto) |
| `hooks.json` JSON-invalido dopo sed | `json.loads(new)` pre-write in T03 + Assert 3 (`jq .`) post-fix |
| **Corruzione JSON da sostituzione non escape-aware** | Replacement Python testato in dry-run; output VALID prima del write |
| Branch parallelo `feat/windows-telemetry-enforcement` rebase | Strategia ADR-003: questo fix mergia prima; quel branch applica identico pattern ai suoi 17 comandi `node` al rebase |
| `jq` non disponibile su macOS | Pre-flight check `command -v jq` in T02; jq 1.7+ è preinstallato su macOS 11+ (verificato) |

## Criteri di accettazione

- [ ] `hooks/hooks.json`: 0 occorrenze byte-pattern `'\${CLAUDE_PLUGIN_ROOT}` (single-quoted)
- [ ] `hooks/hooks.json`: 22 occorrenze byte-pattern `\"${CLAUDE_PLUGIN_ROOT}` (backslash + dquote + `${...}`)
- [ ] `jq . hooks/hooks.json` exit 0
- [ ] **AC runtime**: per ogni hook command estratto via `jq -r .hooks.<event>[].hooks[].command`, l'espressione `bash -c "echo $cmd"` con `CLAUDE_PLUGIN_ROOT=/tmp/probe` produce path che contiene `/tmp/probe/hooks/`
- [ ] `tests/hooks/hooks-json-var-expansion.test.sh` PASS (4 assert)
- [ ] `tests/run-all.sh` complessivo PASS (no regressioni; wire dopo riga 1140)
- [ ] `hooks/ENV_VARS.md`: nuova sezione "Plugin root resolution" con esempi JSON source vs byte literal vs bash receive
- [ ] Verifica empirica post-merge: `SessionStart:startup` di una nuova sessione (post version bump + reinstall) **non** emette `No such file or directory`
- [ ] PR su `fix/hooks-var-expansion` da `main`, commit `fix(hooks): use double-quotes for ${CLAUDE_PLUGIN_ROOT} expansion`
- [ ] Commit message include nota merge coordination (vedi ADR-003) per il branch parallelo

## Out of scope

- Migrazione a Node launcher (`run-hook.js`) — work-in-progress su `feat/windows-telemetry-enforcement`
- Windows enforcement / install.ps1
- Auto-detect / fallback path resolution se var vuota (Piano B = Opzione B, riapri sub-design se T01 fallisce)
- Auto-discovery in `tests/run-all.sh` (manca, ma è scope separato)

## Rischio

🟡 **MEDIO**. Modifica file di config bootstrap del plugin — impatto su tutti gli utenti dopo bump versione. Mitigato da:
- Pre-test T01 (gate empirico ADR-002)
- Replacement escape-aware verificato in dry-run
- `json.loads` pre-write blocca corruzione
- Test runtime con `jq -r` valida valore reale (non solo regex byte-level)
- Suite completa `run-all.sh` cattura regressioni cross-hook

Rischio sale a 🔴 ALTO **solo se** sostituzione non escape-aware (BLOCK-4 mitigato in T03).

## Stima

| Task | SP-U | SP-A |
|---|---|---|
| T01 Pre-test spike (incl. sync cache + cleanup) | 0.4 | 0.2 |
| T02 Test RED (con 4 assert + jq pre-flight) | 0.5 | 0.3 |
| T03 Fix + GREEN + run-all wire + ENV_VARS.md | 0.5 | 0.2 |
| **Totale** | **1.4** | **0.7** |

Pacchetto: 1 PR, 2 commit (T02 test, T03 fix+wire+docs; T01 scartato come spike).

## Note implementative

- Branch da creare: `fix/hooks-var-expansion` da `main` (NOT da `feat/wiki-deep-builder-design`)
- Commit conventional: `fix(hooks):` (root-cause fix, no breaking change esterno)
- PR description deve citare ADR-003 con istruzione esplicita per il rebase di `feat/windows-telemetry-enforcement`
