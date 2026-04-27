---
task: 07
title: stop-gate → evidence-stop-gate rewrite (ADR-006 + ADR-008)
size: M
blocks: [13]
depends: [02]
---

# Task 7 — stop-gate evidence-based rewrite

Rimuove escape hatch 2-block. Sostituisce check `grep siae-verification in
session-skills` con evidence-based: `verification_run event exit=0` nel task.
Aggiunge escape esplicito `DEVFORGE_FORCE_STOP=1`.

## Change summary

### Rimozioni

1. Rimuovere blocco 2-block escape hatch (linee 194-206 di `hooks/stop-gate`):

   ```bash
   STOP_BLOCK_COUNTER_FILE="${HOME}/.claude/.devforge-stop-block-count"
   STOP_BLOCK_COUNT=$(cat "$STOP_BLOCK_COUNTER_FILE" 2>/dev/null || echo "0")
   STOP_BLOCK_COUNT=$((STOP_BLOCK_COUNT + 1))
   echo "$STOP_BLOCK_COUNT" > "$STOP_BLOCK_COUNTER_FILE"

   if [ "$STOP_BLOCK_COUNT" -ge 2 ]; then
       # Escape hatch: allow stop but log as violation
       devforge_log "stop_gate" "escaped" "..."
       rm -f "$STOP_BLOCK_COUNTER_FILE"
       _devforge_emit_session_end
       exit 0
   fi
   ```

### Additions

1. Escape esplicito:

   ```bash
   if [ "${DEVFORGE_FORCE_STOP:-0}" = "1" ]; then
       # tracked abuse
       FORCE_COUNT_FILE="${HOME}/.claude/.devforge-force-stop-count"
       TODAY=$(date -u +%Y-%m-%d)
       DATA=$(cat "$FORCE_COUNT_FILE" 2>/dev/null || echo "")
       STORED_DATE="${DATA%%|*}"
       STORED_N="${DATA##*|}"
       [ "$STORED_DATE" != "$TODAY" ] || [ -z "$STORED_N" ] && STORED_N=0
       NEW_N=$((STORED_N + 1))
       echo "${TODAY}|${NEW_N}" > "${FORCE_COUNT_FILE}.tmp" && mv "${FORCE_COUNT_FILE}.tmp" "$FORCE_COUNT_FILE"
       if [ "$NEW_N" -ge 3 ]; then
           devforge_log "force_stop_abuse_suspected" "warning" "{\"count_today\":${NEW_N}}"
       fi
       _devforge_emit_session_end
       exit 0
   fi
   ```

2. Evidence-based verification check:

   ```bash
   # Load lib/task-id.sh + lib/evidence-check.sh
   TASK_ID=$(devforge_compute_task_id)

   if [ -n "$TASK_ID" ]; then
       # Task-scoped: check evidence
       if devforge_skill_validated siae-verification "$TASK_ID"; then
           _devforge_emit_session_end
           exit 0
       fi
   elif [ "${DEVFORGE_USE_SESSION_SCOPE:-0}" = "1" ]; then
       # Rollback: legacy behavior
       if echo "$SKILLS_LIST" | grep -qF "siae-verification"; then
           _devforge_emit_session_end
           exit 0
       fi
   fi
   ```

3. Aggiornare messaggio block: rimuovere "(Tentativo X/2 — ...)" menzione.
   Messaggio ora: "BLOCCATO. Invoca siae-verification. Escape esplicito:
   DEVFORGE_FORCE_STOP=1 (tracked)."

### Retrospective gate

Il retrospective block check resta identico (session-scoped ok: retrospective
è per-session not per-task).

## Acceptance

- [ ] Rimosso blocco 2-block escape
- [ ] Aggiunto `DEVFORGE_FORCE_STOP=1` escape esplicito con daily counter + abuse_suspected threshold 3
- [ ] Evidence-based verification check via `devforge_skill_validated`
- [ ] Messaggio block aggiornato (no "Tentativo X/2")
- [ ] Rollback DEVFORGE_USE_SESSION_SCOPE=1 funzionante
- [ ] Test `tests/hooks/test_evidence_stop_gate.sh`:
  - [ ] completion claim + verification event exit=0 → allow
  - [ ] completion claim + no verification → block (no 2-attempt escape)
  - [ ] DEVFORGE_FORCE_STOP=1 → allow + log
  - [ ] DEVFORGE_FORCE_STOP=1 × 3 → abuse_suspected log
  - [ ] verification event exit=1 → block (parziale fail)
  - [ ] rollback env: session-scope behavior preservato

## Out of scope

- Recap 3-line stop → PR #3 (deferred ADR-009)
- Retrospective gate logic → invariato
