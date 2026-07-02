# Task 13 — Hook convention-injector (moment-injection ibrida)

**Cluster:** A (REQ-DF-01/02/06) · **Dipendenze:** Task 01 (i 3 file canonici devono esistere) + Task 02 (baseline session-start).

**Goal:** Nuovo hook `hooks/convention-injector` che, oltre alla baseline `session-start`, re-inietta **solo la sezione pertinente** di una convenzione ai 3 momenti clou (task/PR di deploy · edit IaC / multi-repo · promozione ambiente), compatta e diff-deduped.

## File coinvolti
- `hooks/convention-injector` (nuovo, bash, eseguibile)
- `hooks/hooks.json` (modifica — registra il nuovo hook su UserPromptSubmit + PreToolUse Bash/Edit/Write)
- `hooks/devforge-context` (lettura — pattern state-hash `:22-43` e byte-budget da riusare)
- `hooks/sport-task-detect` (lettura — pattern detect+inject UserPromptSubmit)
- `skills/using-devforge/reference/siae-environments.md`, `siae-plan-deploy.md`, `siae-multirepo.md` (lettura — sorgenti)
- `tests/hooks/convention-injector.test.sh` (nuovo)

## Step TDD

### Step 1 — Test fallente
Crea `tests/hooks/convention-injector.test.sh`:
```bash
#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK="$ROOT/hooks/convention-injector"
fail=0
emit(){ printf '%s' "$1" | bash "$HOOK" 2>/dev/null; }

# Trigger 1: prompt di deploy -> inietta environments + plan-deploy
OUT=$(emit '{"hook_event_name":"UserPromptSubmit","prompt":"facciamo il deploy in collaudo con terragrunt"}')
echo "$OUT" | grep -qi 'ambient\|stage\|collaudo' || { echo "FAIL: trigger deploy non inietta environments"; fail=1; }

# Trigger 2: edit IaC -> inietta multirepo + environments
OUT=$(emit '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"modules/net/main.tf"}}')
echo "$OUT" | grep -qi 'iac\|bff\|spa\|repo' || { echo "FAIL: trigger IaC non inietta multirepo"; fail=1; }

# Trigger 3: promozione ambiente (git tag) -> inietta plan-deploy
OUT=$(emit '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git tag collaudo && git push origin collaudo"}}')
echo "$OUT" | grep -qi 'gate\|progressione\|certificazione' || { echo "FAIL: trigger promozione non inietta plan-deploy"; fail=1; }

# Non-trigger: prompt irrilevante -> nessuna iniezione (output vuoto o {} )
OUT=$(emit '{"hook_event_name":"UserPromptSubmit","prompt":"come sto oggi"}')
if echo "$OUT" | grep -qi 'ambient\|iac\|gate'; then echo "FAIL: iniezione su prompt irrilevante"; fail=1; else echo "PASS: no-inject su irrilevante"; fi

# Fonte mancante -> marker esplicito
TMP=$(mktemp -d); cp -r "$ROOT/skills/using-devforge/reference" "$TMP/bk"
rm -f "$ROOT/skills/using-devforge/reference/siae-plan-deploy.md"
OUT=$(emit '{"hook_event_name":"UserPromptSubmit","prompt":"deploy release"}')
echo "$OUT" | grep -q 'FONTE NON DISPONIBILE' || { echo "FAIL: nessun marker su fonte mancante"; fail=1; }
cp "$TMP/bk/siae-plan-deploy.md" "$ROOT/skills/using-devforge/reference/" 2>/dev/null; rm -rf "$TMP"

exit $fail
```

### Step 2 — Esegui e verifica FAIL
Run: `bash tests/hooks/convention-injector.test.sh`
Output atteso (pre-impl): `FAIL: trigger deploy non inietta environments` (+ altri), exit 1 (l'hook non esiste ancora).

### Step 3 — Implementa `hooks/convention-injector`
```bash
#!/usr/bin/env bash
# convention-injector — re-inietta la convenzione SIAE pertinente ai momenti clou.
# Baseline = session-start; qui = re-iniezione mirata, compatta, diff-deduped.
set -uo pipefail
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REF="$PLUGIN_ROOT/skills/using-devforge/reference"
PER_SECTION_BYTES=1200
STATE_DIR="${HOME}/.claude"; STATE="$STATE_DIR/.devforge-convention-injected"

INPUT="$(cat)"
EVENT=$(printf '%s' "$INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null)
PROMPT=$(printf '%s' "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

emit_section(){ # $1=file base name  -> compact section or unavailable marker
  local f="$REF/$1"
  if [ ! -f "$f" ]; then echo "[FONTE NON DISPONIBILE: $1 — NON ipotizzare, dichiara l'assenza]"; return; fi
  head -c "$PER_SECTION_BYTES" "$f"
}

WANT=""   # insieme di file da iniettare (dedotto dal trigger)
# Trigger 1: deploy
if printf '%s %s' "$PROMPT" "$CMD" | grep -qiE 'deploy|collaudo|certificazione|terragrunt|make (dev|qa)|git tag|release' \
   || printf '%s' "$CMD" | grep -qE 'gh pr create'; then
  WANT="siae-environments.md siae-plan-deploy.md"
fi
# Trigger 2: edit IaC / multi-repo
if { [ "$TOOL" = "Edit" ] || [ "$TOOL" = "Write" ]; } && printf '%s' "$FILE" | grep -qE '\.(tf|hcl)$'; then
  WANT="$WANT siae-multirepo.md siae-environments.md"
fi
if printf '%s' "$PWD" | grep -qE '\-(iac|bff|spa)(/|$)'; then
  WANT="$WANT siae-multirepo.md"
fi
# Trigger 3: promozione ambiente
if printf '%s' "$CMD" | grep -qE 'git tag (sviluppo|collaudo)'; then
  WANT="$WANT siae-plan-deploy.md"
fi

# nessun trigger -> passthrough
WANT=$(printf '%s\n' $WANT | awk 'NF' | sort -u | tr '\n' ' ')
[ -z "${WANT// }" ] && { echo '{}'; exit 0; }

# dedup: non re-iniettare la stessa combinazione consecutivamente
HASH=$(printf '%s' "$WANT" | shasum 2>/dev/null | cut -d' ' -f1)
mkdir -p "$STATE_DIR"
[ "$(cat "$STATE" 2>/dev/null)" = "$HASH" ] && { echo '{}'; exit 0; }
printf '%s' "$HASH" > "$STATE"

BODY="[SIAE Convenzioni — momento clou]"$'\n'
for s in $WANT; do BODY="$BODY"$'\n'"## $s"$'\n'"$(emit_section "$s")"; done

# emetti additionalContext (UserPromptSubmit) o additional_context (PreToolUse)
if [ "$EVENT" = "UserPromptSubmit" ]; then
  jq -n --arg c "$BODY" '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$c}}'
else
  jq -n --arg c "$BODY" '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$c}}'
fi
```
Rendi eseguibile: `chmod +x hooks/convention-injector`.
Registra in `hooks/hooks.json`: aggiungi `convention-injector` come sibling di `devforge-context` sotto `UserPromptSubmit`, e sotto `PreToolUse` con matcher `Bash|Edit|Write` (timeout 5). Verifica la sintassi JSON con `jq . hooks/hooks.json`.

### Step 4 — Esegui e verifica PASS
Run: `bash tests/hooks/convention-injector.test.sh`
Output atteso: `PASS: no-inject su irrilevante`, nessun FAIL, exit 0.
Run: `jq -e '.hooks.PreToolUse[] | select(.hooks[].command|test("convention-injector"))' hooks/hooks.json >/dev/null && echo OK` → `OK`.
Registra il test in `tests/run-all.sh`.

### Step 5 — Commit
`feat(context): hook convention-injector per re-iniezione convenzioni SIAE ai momenti clou (REQ-DF-01/02/06)`

## Criteri di accettazione
- [ ] Trigger deploy inietta environments+plan-deploy; edit IaC/multi-repo inietta multirepo+environments; promozione inietta plan-deploy.
- [ ] Prompt irrilevante → nessuna iniezione (no bloat gratuito).
- [ ] Dedup via state-hash (no re-iniezione consecutiva identica).
- [ ] Fonte mancante → marker "FONTE NON DISPONIBILE" (coerente con session-start, REQ-01 AC4).
- [ ] Byte-budget `head -c 1200` per sezione; hook registrato in `hooks.json` (JSON valido); test registrato e verde.
