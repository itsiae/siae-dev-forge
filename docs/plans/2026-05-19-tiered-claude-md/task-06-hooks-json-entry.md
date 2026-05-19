---
task: 06
title: Aggiornare hooks/hooks.json con entry SessionStart
status: PENDING
estimate_min: 15
type: edit
depends_on: [05]
---

# Task 06 — Aggiornare `hooks/hooks.json`

## Obiettivo

Registrare il nuovo hook `session-start-tiered-advisor` come secondo
SessionStart entry, accanto a quello esistente. Async per non rallentare boot.

## File da modificare

1. `hooks/hooks.json`

## Modifica esatta

**Esistente:**

```json
"SessionStart": [
  {
    "matcher": "startup|resume|clear|compact",
    "hooks": [
      {
        "type": "command",
        "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
        "async": false
      }
    ]
  }
]
```

**Nuovo:**

```json
"SessionStart": [
  {
    "matcher": "startup|resume|clear|compact",
    "hooks": [
      {
        "type": "command",
        "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
        "async": false
      }
    ]
  },
  {
    "matcher": "startup|resume",
    "hooks": [
      {
        "type": "command",
        "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start-tiered-advisor",
        "async": true
      }
    ]
  }
]
```

**Note critiche:**
- Matcher `startup|resume` (NOT `clear|compact` — advisory solo su apertura)
- `async: true` (non blocca boot)
- Passa attraverso `run-hook.cmd` come gli altri hook DevForge

## Criteri di accettazione

1. ✅ `hooks.json` JSON valido (`python3 -m json.tool hooks/hooks.json`)
2. ✅ 2 entry SessionStart distinte (esistente + nuova)
3. ✅ Nuova entry async: true
4. ✅ Matcher senza `clear|compact`

## Test

```bash
python3 -m json.tool hooks/hooks.json > /dev/null
jq '.hooks.SessionStart | length' hooks/hooks.json  # deve essere 2
jq '.hooks.SessionStart[1].hooks[0].async' hooks/hooks.json  # deve essere true
```

## Definition of Done

- JSON valido + 2 SessionStart entry
- Commit: `feat(hooks): registra session-start-tiered-advisor in hooks.json`
