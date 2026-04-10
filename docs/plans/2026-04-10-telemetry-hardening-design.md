# Design: Telemetry Hardening — PR1

**Data:** 2026-04-10
**Autore:** Lorenzo De Tomasi + DevForge AI
**Stato:** Implemented
**SP:** 3 SP-Umano / 1 SP-Augmented
**Approccio scelto:** Fix chirurgici negli hook esistenti

---

## Contesto

La telemetria DevForge (v1.37.1) ha 4 categorie di bug che sporcano i dati:
1. **pr_merged non idempotente** — riloggato ad ogni startup
2. **JSON non escaped** — 11 call su 23 loggano stringhe senza sanitizzazione
3. **session_conflict misclassificato** — loggato come `session_start` con status warning
4. **skill-start stale** — non pulito a inizio sessione

Questi bug rendono inaffidabili le metriche derivate (unique_pr_merged, adoption_by_user,
time_in_skill). Va fixato prima di aggiungere nuove feature (token tracking, analytics-v2).

---

## Fix 1: pr_merged idempotente

**Bug:** `hooks/session-start:184-213` — ad ogni startup, `gh pr list --state merged`
rilogs le stesse PR merge delle ultime 24h. 5 sessioni/giorno = 5x duplicati.

**Fix:** file seen-PRs persistente.

- File: `~/.claude/.devforge-seen-pr-merges`
- Formato: una riga per PR vista, `{repo}#{pr_number}`
- Prima di loggare `pr_merged`, controlla: `grep -qF "${GH_REPO}#${PR_NUMBER}" "$SEEN_FILE"`
- Se match, skip. Se no, logga e appendi.
- Max 200 righe (tail -200 dopo ogni append) — previene crescita infinita.
- Cleanup: `session-start` non cancella il file (serve cross-sessione per l'idempotenza).

**Punto di innesto:** `hooks/session-start`, dentro il loop `while IFS= read -r pr` (linea 196),
prima della chiamata `devforge_log "pr_merged"` (linea 212).

```bash
SEEN_FILE="${HOME}/.claude/.devforge-seen-pr-merges"
touch "$SEEN_FILE"
if grep -qF "${GH_REPO}#${PR_NUMBER}" "$SEEN_FILE" 2>/dev/null; then
    continue  # already logged
fi
# ... existing log call ...
echo "${GH_REPO}#${PR_NUMBER}" >> "$SEEN_FILE"
# Keep file bounded
tail -200 "$SEEN_FILE" > "${SEEN_FILE}.tmp" && mv "${SEEN_FILE}.tmp" "$SEEN_FILE"
```

---

## Fix 2: JSON escaping — audit completo

**Bug:** 11 call su 23 loggano stringhe senza `devforge_sanitize_json_str`.
La funzione esiste in `lib/logger.sh` (linea 93) ed è già usata in 9 call.

**Elenco completo delle call da fixare:**

| # | Hook | Linea | Variabili non sanitizzate |
|---|------|-------|--------------------------|
| 1 | `pre-commit` | 70 | `TOOL_COMMAND` |
| 2 | `pre-commit` | 104 | `CURRENT_BRANCH` |
| 3 | `pre-commit` | 178 | `TOOL_COMMAND` |
| 4 | `pr-gate` | 30 | `TOOL_COMMAND` |
| 5 | `sub-skill-gate` | 90 | `SKILL_NAME`, `MISSING_PREREQS` |
| 6 | `tdd-gate` | 80 | `FILE_PATH` |
| 7 | `tdd-gate` | 100 | `FILE_PATH` |
| 8 | `session-start` | 175 | `$(pwd)`, `PLUGIN_VERSION` |
| 9 | `session-start` | 254 | `${sentinel}` |
| 10 | `user-prompt-context` | 54 | `mode_name` |
| 11 | `user-prompt-context` | 63 | `mode_name` |

**Pattern di fix (identico per tutti):**

```bash
# PRIMA (bug)
devforge_log "event" "status" "{\"field\":\"${UNSAFE_VAR}\"}"

# DOPO (fix)
SAFE_VAR=$(devforge_sanitize_json_str "$UNSAFE_VAR")
devforge_log "event" "status" "{\"field\":\"${SAFE_VAR}\"}"
```

**Prerequisito:** ogni hook che usa `devforge_sanitize_json_str` deve aver fatto
`source "${PLUGIN_ROOT}/lib/logger.sh"`. Verificare che il source sia presente
in ogni hook fixato (pre-commit, pr-gate, sub-skill-gate, tdd-gate già lo hanno
perché usano `devforge_log`).

---

## Fix 3: session_conflict event type

**Bug:** `hooks/session-start:226` — sessioni concorrenti loggata come `session_start`
con status `warning`, inquinando il conteggio `session_start`.

**Fix:**

Da:
```bash
devforge_log "session_start" "warning" "{\"reason\":\"concurrent_session_detected\",\"old_pid\":${OLD_PID},\"new_pid\":${CURRENT_PID}}"
```

A:
```bash
devforge_log "session_conflict" "warning" "{\"reason\":\"concurrent_session_detected\",\"old_pid\":${OLD_PID},\"new_pid\":${CURRENT_PID}}"
```

**Impatto:** query Athena/report che filtrano per `event=session_start` non includeranno
più i warning di concorrenza. Le query esistenti che contano sessioni uniche diventano
più accurate.

---

## Fix 4: Cleanup skill-start a inizio sessione

**Bug:** `hooks/post-skill:24` scrive `.devforge-skill-start` per il timestamp chaining.
Ma `hooks/session-start` non lo pulisce. Se la sessione precedente è crashata senza
passare per `stop-gate`, la nuova sessione eredita un skill-start stale, e il primo
`skill_completed` avrà una duration_ms di ore/giorni.

**Fix:** aggiungere in `hooks/session-start`, nel blocco cleanup (dopo linea 245):

```bash
rm -f "${HOME}/.claude/.devforge-skill-start"
```

---

## Gestione errori e edge case

| Edge case | Gestione |
|-----------|----------|
| seen-pr-merges file non esiste | `touch` lo crea. `grep -qF` ritorna false = non visto. |
| Branch name con caratteri speciali | `devforge_sanitize_json_str` li escapa. |
| File path con `"` o newline | `devforge_sanitize_json_str` li escapa. |
| `$(pwd)` su path iCloud con `~` | `devforge_sanitize_json_str` escapa `~`. |
| Vecchi eventi con `session_start/warning` | Restano nel JSONL storico. Non serve migrazione. |
| `session_conflict` non riconosciuto da Lambda | Lambda accetta qualsiasi event type (schema libero in `meta`). |

---

## Testing

| Test | Cosa verifica |
|------|--------------|
| `test_pr_merged_idempotent` | Seconda sessione non rilogs stesse PR |
| `test_json_escape_command` | Branch con `"` non rompe il JSON |
| `test_json_escape_filepath` | File path con spazi/quote escapato |
| `test_session_conflict_event` | Concorrenza logga `session_conflict`, non `session_start` |
| `test_skill_start_cleanup` | Dopo session-start, `.devforge-skill-start` non esiste |
| `test_seen_file_bounded` | File seen-pr-merges non supera 200 righe |

---

## Criteri di Accettazione

| # | Criterio |
|---|----------|
| AC-1 | `pr_merged` emesso una sola volta per PR, anche con sessioni multiple |
| AC-2 | Tutte le 23 call `devforge_log` producono JSON valido (verificabile con `jq`) |
| AC-3 | Sessione concorrente logga `session_conflict`, non `session_start` |
| AC-4 | `.devforge-skill-start` pulito a inizio sessione |
| AC-5 | File `~/.claude/.devforge-seen-pr-merges` non supera 200 righe |
| AC-6 | Nessun hook bloccato o rallentato dai fix (timeout invariati) |
| AC-7 | Backward compatible: vecchi eventi nel JSONL non invalidati |

---

## File da modificare

| File | Fix applicati |
|------|--------------|
| `hooks/session-start` | Fix 1 (pr_merged idempotente), Fix 3 (session_conflict), Fix 4 (cleanup skill-start), Fix 2 (escape pwd, sentinel) |
| `hooks/pre-commit` | Fix 2 (escape TOOL_COMMAND, CURRENT_BRANCH) |
| `hooks/pr-gate` | Fix 2 (escape TOOL_COMMAND) |
| `hooks/sub-skill-gate` | Fix 2 (escape SKILL_NAME, MISSING_PREREQS) |
| `hooks/tdd-gate` | Fix 2 (escape FILE_PATH) |
| `hooks/user-prompt-context` | Fix 2 (escape mode_name) |

---

## Trade-off

| Decisione | Alternativa scartata | Motivo |
|-----------|---------------------|--------|
| seen-file persistente | Dedup lato server | Zero infra change, il file è locale e leggero |
| tail -200 per bounding | Timestamp-based cleanup | Più semplice, 200 PR copre ~2 mesi |
| session_conflict nuovo event | Flag in meta | Event type separato è più pulito per le query |
| Sanitize tutte le 11 call | Solo quelle "a rischio" | Costo zero, previene future regressioni |
