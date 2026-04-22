# Task 06 — Hooks.json registration + run-all.sh integration

**Stato:** [PENDING]
**Stima:** 5 min
**Dipendenze:** Task 01-05

## Goal

Registrare `brainstorming-gate` in `hooks/hooks.json` **dopo** `tdd-gate` sui matcher Edit/Write (ordering: TDD prima → se blocca, enforcement non gira). Aggiungere invocazione in `tests/run-all.sh` per CI integration.

## File coinvolti

- `hooks/hooks.json` (MODIFY)
- `tests/run-all.sh` (MODIFY)

## Step 1 — Modifica `hooks/hooks.json`

Trova il blocco `"matcher": "Edit"` esistente (righe ~58-67 pre-task, contiene solo tdd-gate). Sostituisci:

```json
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' tdd-gate",
            "timeout": 5
          }
        ]
      },
```

con:

```json
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' tdd-gate",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' brainstorming-gate",
            "timeout": 5
          }
        ]
      },
```

Ripeti identica modifica sul blocco `"matcher": "Write"` subito successivo.

## Step 2 — Verifica JSON valido

```bash
python3 -m json.tool hooks/hooks.json > /dev/null && echo "JSON valido"
```

Atteso: `JSON valido`. Se errore di parsing → sistema virgole/parentesi.

## Step 3 — Modifica `tests/run-all.sh`

Apri `tests/run-all.sh` e trova la sezione con `post-commit-pr-lifecycle.test.sh` (aggiunta in PR #212). **Dopo** quel blocco, aggiungi:

```bash
# Test brainstorming-gate progressive enforcement
if bash "${PLUGIN_ROOT}/tests/hooks/brainstorming-gate.test.sh" >/dev/null 2>&1; then
  echo "  PASS  brainstorming-gate: progressive enforcement (nudge/warn/block + bypass + anti-abuse)"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  brainstorming-gate: hook enforcement non funziona"
  telfunc_fail=$((telfunc_fail + 1))
fi
```

## Step 4 — Esecuzione completa test

```bash
bash tests/hooks/brainstorming-gate.test.sh 2>&1 | grep -E "PASS|FAIL" | wc -l
# Atteso: 12 (12 scenari totali)

bash tests/hooks/post-commit-review-sha.test.sh 2>&1 | tail -2
# Atteso: PASS

bash tests/hooks/post-skill-plan-events.test.sh 2>&1 | tail -2
# Atteso: PASS

bash tests/hooks/post-commit-pr-lifecycle.test.sh 2>&1 | grep -c PASS
# Atteso: 8
```

Tutti i test esistenti devono restare verdi. Se uno fallisce, investiga prima di procedere.

## Step 5 — Verifica ordering tdd → brainstorming (assert programmatico)

Sostituisci il check manuale con un assert Python deterministico:

```bash
python3 <<'PYEOF'
import json
hooks = json.load(open('hooks/hooks.json'))['hooks']['PreToolUse']
for entry in hooks:
    if entry.get('matcher') in ('Edit', 'Write'):
        cmds = [h['command'] for h in entry['hooks']]
        tdd_idx = next(i for i, c in enumerate(cmds) if 'tdd-gate' in c)
        brain_idx = next(i for i, c in enumerate(cmds) if 'brainstorming-gate' in c)
        assert tdd_idx < brain_idx, f"ordering errato su {entry['matcher']}: tdd={tdd_idx}, brain={brain_idx}"
        print(f"OK {entry['matcher']}: tdd-gate idx={tdd_idx}, brainstorming-gate idx={brain_idx}")
PYEOF
```

**Output atteso:**

```
OK Edit: tdd-gate idx=0, brainstorming-gate idx=1
OK Write: tdd-gate idx=0, brainstorming-gate idx=1
```

Rationale: Claude Code esegue hook in ordine; se `tdd-gate` emette `decision:"block"`, la catena si ferma e `brainstorming-gate` non gira → evita doppio messaggio. L'assert garantisce l'invariante in CI.

## Step 6 — Commit

```bash
git add hooks/hooks.json tests/run-all.sh
git commit -m "chore(hook): register brainstorming-gate + run-all.sh [T06]"
```

## Definition of Done

- [ ] `hooks/hooks.json` contiene brainstorming-gate dopo tdd-gate su Edit E Write
- [ ] JSON valido (passa `python3 -m json.tool`)
- [ ] `tests/run-all.sh` invoca `brainstorming-gate.test.sh`
- [ ] 12/12 scenari brainstorming-gate passano
- [ ] Test esistenti (sha, plan-events, pr-lifecycle) restano verdi
- [ ] Ordering tdd-gate → brainstorming-gate verificato
- [ ] Commit creato

## Post-task — Push + PR

Dopo Task 06 DONE, push branch + crea PR:

```bash
git push -u origin feat/brainstorming-enforcement-progressive
gh pr create --base main \
  --title "feat(hook): brainstorming-gate progressive enforcement (adoption 3.3% → 50%+)" \
  --body-file /tmp/pr-body-enforcement.md
```

Body PR (scrivere in `/tmp/pr-body-enforcement.md` prima):
- Problema: 3.3% adoption (CSV 2026-04-22)
- Soluzione: progressive friction (nudge N=1 → warn N=2-3 → block N≥4) + bypass + anti-abuse
- Rollout: W1 opt-in (`DEVFORGE_ENFORCEMENT_STRICT=1`), W2 default-on (`DEVFORGE_ENFORCEMENT_OFF=1` escape)
- 6 eventi telemetria nuovi per Control Tower
- 12/12 test PASS
