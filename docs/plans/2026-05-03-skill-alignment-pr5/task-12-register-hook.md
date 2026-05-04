# Task 12 — Register Hooks in `hooks/hooks.json` (DevForge Pattern)

**Goal:** Registrare i 2 hook PostToolUse (skill-advisory, state-writer) seguendo il pattern reale del repo: `hooks/hooks.json` + invocazione via `run-hook.cmd`.

**File coinvolti:**
- `hooks/hooks.json` (modifica — aggiunge sezione PostToolUse)
- Verifica path: `hooks/skill-advisory` (no .sh) e `hooks/state-writer` (no .sh) — rinomina/wrapper se necessario (vedi Task 10/11)

## Pattern reale del repo

Hook DevForge usano questa struttura:
- File hook in `hooks/<name>` (no estensione)
- Registrazione in `hooks/hooks.json`
- Invocazione: `bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' <name>`
- `${CLAUDE_PLUGIN_ROOT}` viene risolto dal runtime Claude Code

## Step 1 — Verifica file hook senza .sh

Task 10 e Task 11 hanno creato `hooks/skill-advisory.sh` e `hooks/state-writer.sh`. Per coerenza col pattern:

**Opzione A (consigliata)**: rinomina (drop `.sh`)

```bash
git mv hooks/skill-advisory.sh hooks/skill-advisory
git mv hooks/state-writer.sh hooks/state-writer
```

Verifica `run-hook.cmd` esiste e gestisce file senza estensione:

```bash
cat hooks/run-hook.cmd
```

NB: se `run-hook.cmd` aggiunge `.sh` automaticamente, mantieni le estensioni e adatta. Verifica empirica.

**Opzione B (fallback)**: lascia `.sh` ma adatta hooks.json invocazione diretta:

```json
"command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/skill-advisory.sh'"
```

NB: NON allinea col pattern repo. Solo se Opzione A non praticabile.

## Step 2 — Modifica `hooks/hooks.json`

Leggi la struttura attuale:

```bash
python3 -m json.tool hooks/hooks.json | head -100
```

Aggiungi sezione `PostToolUse` (se non esiste) o estendi esistente:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' skill-advisory",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' state-writer",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

NB: il matcher `"Skill"` è il punto di rischio R6 (matcher per skill events potrebbe non esistere). Fallback documentato:

**Fallback se "Skill" non matcha**:

```json
"matcher": ""
```

Match-all PostToolUse, hook fanno early-exit interno se non riconoscono skill (Task 10 helpers ritornano vuoto per skill non in tabella).

## Step 3 — Validazione JSON

```bash
python3 -m json.tool hooks/hooks.json > /dev/null && echo "JSON valid"
```

## Step 4 — Verifica run-hook.cmd

```bash
ls -la hooks/run-hook.cmd
head -30 hooks/run-hook.cmd
```

Verifica che lo script:
- Sia eseguibile
- Trovi `hooks/<name>` (con o senza estensione, dipende dall'implementazione)
- Esegua il file passando stdin (input hook protocol)

Se Task 10/11 hanno usato `.sh` extension e `run-hook.cmd` non lo gestisce, aggiungi compatibilità:

```bash
# Esempio se run-hook.cmd è uno script bash:
# Aggiungere fallback che cerca anche <name>.sh
```

NB: questa modifica è OUT-OF-SCOPE se non necessaria. Verificare empiricamente.

## Step 5 — Test in-session [MANUAL — coordinamento utente]

NON automatizzabile da subagent. Richiede sessione Claude Code separata + osservazione log.

**Procedura per l'utente**:
1. Apri nuova sessione Claude Code in repo
2. Invoca `/siae-devforge:siae-verification` (o trigger via prompt "il fix funziona")
3. Verifica log Claude Code (debug/verbose mode):
   - Hook `skill-advisory` invocato dopo Skill tool
   - Hook `state-writer` invocato (e file `.skill-state` aggiornato dopo brainstorming/tdd)
4. Verifica skill ancora si attiva correttamente (no-block confirmed)

**Esito atteso**:
- Hook gira (entry in log)
- Se `.skill-state` vuoto, additionalContext nudge presente
- Skill funziona normalmente

**Se hook NON triggera**:
- Risk R6 manifestato. Cambia matcher da `"Skill"` a `""` (match-all)
- Re-test
- Se ancora non triggera → escalation utente, considera fallback `UserPromptSubmit` matcher

## Step 6 — Plugin manifest verification

`.claude-plugin/plugin.json` punta già a `hooks/hooks.json` via convention DevForge. Verifica:

```bash
grep -A5 'hooks' .claude-plugin/plugin.json
```

Se necessario, aggiungi reference esplicito ai 2 hook entry nel manifest (verificare schema Claude Code Plugin).

## Step 7 — Commit

```bash
git add hooks/hooks.json hooks/skill-advisory hooks/state-writer 2>/dev/null
git commit -m "feat(hooks): register skill-advisory + state-writer in hooks.json (PostToolUse)

Pattern aligned with DevForge convention: 'bash run-hook.cmd <name>' invocation,
no .sh extension. Matcher 'Skill' (fallback '' se runtime non lo supporta).

Test [MANUAL] richiesto post-task: verificare invocazione hook in nuova sessione
Claude Code. Risk R6 (matcher Skill) ha fallback documentato."
```

## Criteri accettazione

- `hooks/hooks.json` JSON valido con sezione PostToolUse contenente 2 hook
- File `hooks/skill-advisory` e `hooks/state-writer` esistono (con o senza `.sh` a seconda di Opzione A/B)
- `run-hook.cmd` invoca correttamente i 2 hook
- Test [MANUAL] coordinamento utente eseguito ed esito documentato

## NO-REGRESSION

Hooks PostToolUse advisory + non-blocking. Zero impact su skill esistenti. Allinea pattern repo (no `.claude/settings.json` fantasma).

## Risk R6 — fallback decisione

Se test manuale mostra che matcher "Skill" NON triggera l'hook su skill events:
1. Cambia matcher a `""` (match-all)
2. Re-test
3. Se ancora non triggera → fallback escalation utente, considera `UserPromptSubmit` matcher con grep "skill X" pattern (non ideale ma funzionante)
4. Documenta scelta finale in CHANGELOG

## Coordinamento con Task 10 e 11

Questo task DEPENDS DA Task 10 (skill-advisory) e Task 11 (state-writer) DONE. Se i file hanno `.sh` extension:
- Esegui Step 1 Opzione A (rinomina) PRIMA di committare hooks.json
- Update commit di Task 10/11 se necessario (fixup commit)
