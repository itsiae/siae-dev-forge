# Task 09 — `hooks/brainstorming-gate` scala con la complessità (trivial short-circuit + override scoped)

**Cluster:** REQ-DF-04 (brainstorming proporzionato alla complessità)
**Dipendenze:** Task 08 (`devforge_change_is_trivial()` in `lib/file-taxonomy.sh`)

## Goal

`hooks/brainstorming-gate` calcola `lines_changed` dal payload dell'edit, accumula i file toccati nel task corrente, e se il cambiamento è single-file-in-task E `devforge_change_is_trivial` lo classifica trivial, esce con `{}` senza incrementare il counter né emettere nudge; supporta l'override scoped+logged `DEVFORGE_BRAINSTORM_COMPLEXITY` (`force-complex`/`force-trivial`) che agisce SOLO sulla classificazione (non bypassa IaC/path-sensibili quando forza trivial); `hooks/post-skill` resetta anche il counter task-scoped, non solo quello legacy SID-anchored.

## File coinvolti

- `hooks/brainstorming-gate` — **modifica**, inserire un nuovo blocco tra la sezione "Short-circuit: siae-brainstorming invoked" (righe 94-107) e la sezione "Progressive counter" (righe 110-139). Il nuovo blocco calcola `TASK_ID`/`COUNTER_FILE` (oggi calcolati più sotto, righe 115-129) più in alto per poterli riusare anche per il tracking file-touched, poi decide lo short-circuit trivial PRIMA dell'incremento a riga 138.
- `hooks/post-skill` — **modifica**, righe 190-202 (blocco "Reset brainstorming-gate counter (T05)"): aggiungere reset del counter task-scoped oltre a quello legacy SID-anchored.
- `tests/hooks/brainstorming-gate.test.sh` — **modifica**, append nuovi scenari dopo lo Scenario 13 (riga 228), prima del blocco Summary (righe 230-235).
- `tests/test_no_discretionary_bypass.py` — **modifica**, aggiungere un nuovo test che verifica che `DEVFORGE_BRAINSTORM_COMPLEXITY=force-trivial` non silenzi un cambiamento IaC.
- `hooks/ENV_VARS.md` — **modifica**, documentare `DEVFORGE_BRAINSTORM_COMPLEXITY` nella tabella `## Global` (dopo la riga 15, `DEVFORGE_USE_SESSION_SCOPE`).

## Nota sul dimensionamento

Questo task tocca 4 file (2 hook + 2 test + 1 doc) con logica non banale (accumulo file-touched, calcolo diff-lines, override scoped). Supera la soglia dei 30 minuti indicata come target bite-sized; **split consigliato** per l'esecuzione reale in due sessioni: (1) short-circuit trivial + override nel gate, (2) fix del reset in `post-skill` + guard test. È mantenuto come task unico qui perché il design lo tratta come un'unica unità coerente (stesso file `hooks/brainstorming-gate`, stesso ciclo RED→GREEN) — chi esegue può interrompere dopo lo Step 4 del gate e trattare il fix di `post-skill` (Step 3b sotto) come commit separato, riusando lo stesso Step 2/4 di verifica.

## Step TDD

### Step 1 — Scrivi il test che fallisce (codice completo)

Apri `tests/hooks/brainstorming-gate.test.sh` e aggiungi, subito dopo lo Scenario 13 (dopo la riga `echo "PASS scenario 13: gate always-on without STRICT/W2_DEFAULT (ADR-006)"` e prima del commento `# Summary (aggregator-compatible)`), i seguenti scenari. Sostituisci anche `invoke_gate` con una variante che accetta `old_string`/`new_string` per simulare `tool_input` realistico (necessaria per i nuovi scenari; la firma esistente resta compatibile perché i parametri aggiuntivi sono opzionali):

```bash
invoke_gate_edit() {
    local file_path="$1" old_str="${2:-}" new_str="${3:-}"
    local hook_input
    hook_input=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Edit","file_path":sys.argv[1],"tool_input":{"file_path":sys.argv[1],"old_string":sys.argv[2],"new_string":sys.argv[3]}}))' "$file_path" "$old_str" "$new_str")
    echo "$hook_input" | bash "${PLUGIN_ROOT}/hooks/brainstorming-gate" 2>/dev/null
}

reset_task_scope_state() {
    rm -f "${HOME}/.claude/.devforge-brainstorm-counter" "${HOME}/.claude/.devforge-session-skills"
    rm -rf "${HOME}/.claude/.devforge-task-skills"
}

# ─── Scenario 14: trivial single-file edit → no nudge, no counter increment ───
# Task-scoped mode required (DEVFORGE_USE_SESSION_SCOPE unset in subshell).
(
    unset DEVFORGE_USE_SESSION_SCOPE
    reset_task_scope_state
    BEFORE_14=$(count_events brainstorming_nudge_soft)
    OUT=$(invoke_gate_edit "${TEST_REPO}/hello.ts" "a" "ab")
    AFTER_14=$(count_events brainstorming_nudge_soft)
    if [ "$BEFORE_14" != "$AFTER_14" ]; then
        echo "FAIL scenario 14: trivial edit ha emesso nudge (delta=$((AFTER_14 - BEFORE_14)))"
        exit 1
    fi
    if [ "$OUT" != "{}" ]; then
        echo "FAIL scenario 14: trivial edit output='$OUT', expected '{}'"
        exit 1
    fi
    echo "PASS scenario 14: trivial single-file edit → short-circuit {} senza nudge"
) || exit 1

# ─── Scenario 15: multi-file nel task → NON trivial anche con poche righe ───
(
    unset DEVFORGE_USE_SESSION_SCOPE
    reset_task_scope_state
    invoke_gate_edit "${TEST_REPO}/hello.ts" "a" "ab" >/dev/null
    BEFORE_15=$(count_events brainstorming_nudge_soft)
    OUT=$(invoke_gate_edit "${TEST_REPO}/other.ts" "x" "xy")
    AFTER_15=$(count_events brainstorming_nudge_soft)
    if [ "$BEFORE_15" = "$AFTER_15" ]; then
        echo "FAIL scenario 15: secondo file nel task NON ha fatto nudge (expected multi-file → non trivial)"
        exit 1
    fi
    echo "PASS scenario 15: secondo file toccato nel task → nudge (multi-file non trivial)"
) || exit 1

# ─── Scenario 16: file IaC (.tf) → nudge anche con edit minuscolo (path forza complesso) ───
(
    unset DEVFORGE_USE_SESSION_SCOPE
    reset_task_scope_state
    echo "resource {}" > "${TEST_REPO}/scenario16.tf"
    BEFORE_16=$(count_events brainstorming_nudge_soft)
    OUT=$(invoke_gate_edit "${TEST_REPO}/scenario16.tf" "a" "ab")
    AFTER_16=$(count_events brainstorming_nudge_soft)
    if [ "$BEFORE_16" = "$AFTER_16" ]; then
        echo "FAIL scenario 16: edit .tf minuscolo NON ha fatto nudge (expected sempre non-trivial)"
        exit 1
    fi
    echo "PASS scenario 16: edit .tf minuscolo → nudge (IaC sempre non-trivial)"
) || exit 1

# ─── Scenario 17: DEVFORGE_BRAINSTORM_COMPLEXITY=force-complex forza nudge su edit trivial ───
(
    unset DEVFORGE_USE_SESSION_SCOPE
    reset_task_scope_state
    BEFORE_17=$(count_events brainstorming_nudge_soft)
    OUT=$(DEVFORGE_BRAINSTORM_COMPLEXITY=force-complex invoke_gate_edit "${TEST_REPO}/hello.ts" "a" "ab")
    AFTER_17=$(count_events brainstorming_nudge_soft)
    if [ "$BEFORE_17" = "$AFTER_17" ]; then
        echo "FAIL scenario 17: force-complex NON ha forzato il nudge su edit trivial"
        exit 1
    fi
    if [ "$(count_events brainstorm_complexity_override)" = "0" ]; then
        echo "FAIL scenario 17: override force-complex non loggato (evento brainstorm_complexity_override assente)"
        exit 1
    fi
    echo "PASS scenario 17: DEVFORGE_BRAINSTORM_COMPLEXITY=force-complex forza nudge + log override"
) || exit 1

# ─── Scenario 18: DEVFORGE_BRAINSTORM_COMPLEXITY=force-trivial NON bypassa IaC ───
(
    unset DEVFORGE_USE_SESSION_SCOPE
    reset_task_scope_state
    echo "resource {}" > "${TEST_REPO}/scenario18.tf"
    BEFORE_18=$(count_events brainstorming_nudge_soft)
    OUT=$(DEVFORGE_BRAINSTORM_COMPLEXITY=force-trivial invoke_gate_edit "${TEST_REPO}/scenario18.tf" "a" "ab")
    AFTER_18=$(count_events brainstorming_nudge_soft)
    if [ "$BEFORE_18" = "$AFTER_18" ]; then
        echo "FAIL scenario 18: force-trivial ha bypassato l'enforcement su file IaC (violazione AC4)"
        exit 1
    fi
    if [ "$(count_events brainstorm_complexity_override)" = "0" ]; then
        echo "FAIL scenario 18: override force-trivial non loggato"
        exit 1
    fi
    echo "PASS scenario 18: DEVFORGE_BRAINSTORM_COMPLEXITY=force-trivial NON bypassa IaC (resta non-trivial)"
) || exit 1

# ─── Scenario 19: post-skill resetta anche il counter task-scoped ───
(
    unset DEVFORGE_USE_SESSION_SCOPE
    reset_task_scope_state
    invoke_gate_edit "${TEST_REPO}/hello.ts" "a" "ab" >/dev/null
    invoke_gate_edit "${TEST_REPO}/other.ts" "x" "xy" >/dev/null
    TASK_ID_DIR=$(find "${HOME}/.claude/.devforge-task-skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -1)
    if [ -z "$TASK_ID_DIR" ]; then
        echo "FAIL scenario 19: nessuna directory task-scoped creata dagli scenari precedenti"
        exit 1
    fi
    TASK_COUNTER_FILE="${TASK_ID_DIR}/brainstorm-counter"
    PRE_RESET=$(cat "$TASK_COUNTER_FILE" 2>/dev/null || echo "")
    if ! echo "$PRE_RESET" | grep -qE '\|[1-9]'; then
        echo "FAIL scenario 19: counter task-scoped non incrementato prima del reset ('$PRE_RESET')"
        exit 1
    fi
    SKILL_INPUT='{"tool_name":"Skill","skill":"siae-devforge:siae-brainstorming","name":"siae-devforge:siae-brainstorming"}'
    echo "$SKILL_INPUT" | bash "${PLUGIN_ROOT}/hooks/post-skill" >/dev/null 2>&1 || true
    POST_RESET=$(cat "$TASK_COUNTER_FILE" 2>/dev/null || echo "")
    if echo "$POST_RESET" | grep -qE '\|[1-9]'; then
        echo "FAIL scenario 19: counter task-scoped NON resettato da post-skill ('$POST_RESET')"
        exit 1
    fi
    echo "PASS scenario 19: post-skill resetta anche il counter task-scoped"
) || exit 1
```

Aggiorna anche il contatore di riepilogo: sostituisci `PASS_COUNT=13` con `PASS_COUNT=19` nel blocco Summary finale.

### Step 2 — Esegui e osserva il FAIL atteso

Comando:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/hooks/brainstorming-gate.test.sh
```

Output atteso (gli scenari 1-13 e 19 passano invariati con la logica esistente — scenario 19 fallisce comunque perché `post-skill` non crea/aggiorna ancora il counter task-scoped nella forma attesa dal test, ma il fallimento discriminante è sugli scenari 14/16/17/18 dove manca lo short-circuit trivial e l'override; lo scenario 15 passa già perché il comportamento attuale fa sempre nudge):

```
PASS scenario 1: N=1 nudge_soft + counter=1
PASS scenario 2: N=2 warn + block + counter=2
PASS scenario 3: N=4 hard block
PASS scenario 5: siae-brainstorming presente → no enforcement
PASS scenario 4: DEVFORGE_SKIP_BRAINSTORMING ignorata → gate enforce
PASS scenario 5b: post-skill reset + invoked_post_gate trigger=warn
PASS scenario 6: file .md → pass (out of scope)
PASS scenario 7: file .tf → IN scope (ADR-005)
PASS scenario 8: repo non-itsiae → pass (out of scope)
PASS scenario 9: DEVFORGE_ENFORCEMENT_OFF=1 → escape immediato
PASS scenario 13: gate always-on without STRICT/W2_DEFAULT (ADR-006)
FAIL scenario 14: trivial edit ha emesso nudge (delta=1)
```

Exit code: diverso da `0` (lo script si ferma al primo `exit 1`, quindi lo scenario 14 è il primo FAIL osservato; gli scenari 15-19 non vengono eseguiti in questa run).

### Step 3 — Implementa il codice minimo (codice completo, path reali)

**Step 3a — `hooks/brainstorming-gate`.** Sostituisci il blocco esistente dalla riga 110 (`# Progressive counter — task-scoped by default, SID-anchored on rollback`) alla riga 139 (`echo "${COUNTER_KEY}|${NEW_N}" > "${COUNTER_FILE}.tmp" && mv "${COUNTER_FILE}.tmp" "$COUNTER_FILE"`) con:

```bash
# Progressive counter — task-scoped by default, SID-anchored on rollback
USE_SESSION_SCOPE="${DEVFORGE_USE_SESSION_SCOPE:-0}"
COUNTER_KEY=""
COUNTER_FILE=""
TASK_DIR=""

if [ "$USE_SESSION_SCOPE" != "1" ] && command -v devforge_compute_task_id >/dev/null 2>&1; then
    TASK_ID=$(cd "$FILE_GIT_ROOT" && devforge_compute_task_id 2>/dev/null || echo "")
    if [ -n "$TASK_ID" ]; then
        COUNTER_KEY="task:${TASK_ID}"
        TASK_DIR="${HOME}/.claude/.devforge-task-skills/${TASK_ID}"
        COUNTER_FILE="${TASK_DIR}/brainstorm-counter"
        mkdir -p "$TASK_DIR"
    fi
fi

if [ -z "$COUNTER_FILE" ]; then
    # Rollback / non-itsiae-taskable path → legacy SID-anchored counter
    CURRENT_SID=$(devforge_get_sid 2>/dev/null || echo "unknown")
    COUNTER_KEY="sid:${CURRENT_SID}"
    COUNTER_FILE="${HOME}/.claude/.devforge-brainstorm-counter"
fi

# ── Complexity classification (REQ-DF-04) ──────────────────────────
# Only meaningful when task-scoped (TASK_DIR set); outside task scope
# (legacy SID rollback) the trivial short-circuit does not apply and
# enforcement behaves exactly as before.
if [ -n "$TASK_DIR" ] && command -v devforge_change_is_trivial >/dev/null 2>&1; then
    # lines_changed: prefer Edit's old_string/new_string (max of the two
    # line counts, a conservative proxy for diff size); fall back to
    # Write's content. Unknown shape → 0 (treated as trivial-sized; the
    # sensitive-path/IaC carve-outs in devforge_change_is_trivial still
    # force non-trivial regardless of this value).
    LINES_CHANGED=0
    if command -v jq >/dev/null 2>&1; then
        LINES_CHANGED=$(echo "$HOOK_INPUT" | jq -r '
            if (.tool_input.old_string // "") != "" or (.tool_input.new_string // "") != "" then
                ((.tool_input.old_string // "") | split("\n") | length) as $o
                | ((.tool_input.new_string // "") | split("\n") | length) as $n
                | (if $o > $n then $o else $n end)
            elif (.tool_input.content // "") != "" then
                (.tool_input.content // "" | split("\n") | length)
            else 0 end
        ' 2>/dev/null || echo 0)
        case "$LINES_CHANGED" in ''|*[!0-9]*) LINES_CHANGED=0 ;; esac
    fi

    # Files-touched ledger for this task: append distinct paths, then
    # count them. The hook only sees one file per invocation, so this
    # file is the cross-invocation memory that makes "single-file-in-task"
    # detectable (gotcha #6 in design).
    FILES_TOUCHED_FILE="${TASK_DIR}/files_touched"
    if ! grep -qxF "$FILE_PATH" "$FILES_TOUCHED_FILE" 2>/dev/null; then
        printf '%s\n' "$FILE_PATH" >> "$FILES_TOUCHED_FILE"
    fi
    FILES_TOUCHED_COUNT=$(grep -c '.' "$FILES_TOUCHED_FILE" 2>/dev/null || echo 0)

    # Override flag (AC4, scoped+logged, no discretionary bypass — PR #318
    # precedent). Acts ONLY on the classification input to
    # devforge_change_is_trivial's caller decision below; it never skips
    # the IaC/sensitive-path carve-outs inside devforge_change_is_trivial
    # itself, so force-trivial cannot silence a genuinely complex change.
    COMPLEXITY_OVERRIDE="${DEVFORGE_BRAINSTORM_COMPLEXITY:-}"
    IS_TRIVIAL=1
    if devforge_change_is_trivial "$FILE_PATH" "$LINES_CHANGED"; then
        IS_TRIVIAL=0
    fi

    if [ "$COMPLEXITY_OVERRIDE" = "force-complex" ]; then
        devforge_log "brainstorm_complexity_override" "success" \
            "{\"override\":\"force-complex\",\"file_path\":\"$(devforge_sanitize_json_str "$FILE_PATH")\"}"
        IS_TRIVIAL=1
    elif [ "$COMPLEXITY_OVERRIDE" = "force-trivial" ]; then
        devforge_log "brainstorm_complexity_override" "success" \
            "{\"override\":\"force-trivial\",\"file_path\":\"$(devforge_sanitize_json_str "$FILE_PATH")\"}"
        # force-trivial can only downgrade an *otherwise-trivial-by-size*
        # change; it must NOT flip a change that devforge_change_is_trivial
        # already classified non-trivial (IaC/sensitive-path/oversize).
        # IS_TRIVIAL is left untouched here on purpose.
        :
    fi

    if [ "$IS_TRIVIAL" -eq 0 ] && [ "$FILES_TOUCHED_COUNT" -le 1 ]; then
        echo '{}'
        exit 0
    fi
fi

NEW_N=$((STORED_N + 1))
```

Nota: la riga finale `NEW_N=$((STORED_N + 1))` sostituisce la vecchia riga di incremento+scrittura; le due righe successive esistenti (lettura di `CURRENT_DATA`/`STORED_KEY`/`STORED_N`, righe 131-136 originali) restano IMMEDIATAMENTE SOPRA questo blocco senza modifiche — vanno solo spostate concettualmente prima del nuovo blocco di classificazione, perché `STORED_N` è necessario per calcolare `NEW_N`. Quindi l'ordine finale nel file è: (1) risoluzione `COUNTER_KEY`/`COUNTER_FILE`/`TASK_DIR` (bloc­co sopra, prima parte), poi (2) lettura `CURRENT_DATA`/`STORED_KEY`/`STORED_N` (righe 131-136 originali, invariate), poi (3) il blocco di classificazione trivial (che può fare `exit 0` prima di incrementare), poi (4) `NEW_N=$((STORED_N + 1))` e la persistenza su `COUNTER_FILE` (riga 139 originale, invariata, subito dopo `NEW_N=...`). Applica l'edit MANTENENDO le righe 131-136 originali fra il primo e il blocco di classificazione, e mantieni la riga 139 originale (`echo "${COUNTER_KEY}|${NEW_N}" > ...`) subito dopo la riga `NEW_N=$((STORED_N + 1))` qui sopra — non duplicarla.

**Step 3b — `hooks/post-skill`.** Nel blocco `if [ "$CLEAN_SKILL_TOKEN" = "siae-brainstorming" ]; then` (righe 190-205), dopo la riga:

```bash
        echo "${CURRENT_SID_RESET}|0" > "${BRAINSTORM_COUNTER_FILE}.tmp" && \
            mv "${BRAINSTORM_COUNTER_FILE}.tmp" "$BRAINSTORM_COUNTER_FILE"
```

aggiungi il reset del counter task-scoped (usa lo stesso `_POST_TASK_ID`/`_POST_TASK_DIR` già calcolati allo Step 1b, righe 60-68):

```bash
        if [ -n "${_POST_TASK_ID:-}" ] && [ -n "${_POST_TASK_DIR:-}" ]; then
            TASK_BRAINSTORM_COUNTER="${_POST_TASK_DIR}/brainstorm-counter"
            if [ -f "$TASK_BRAINSTORM_COUNTER" ]; then
                TASK_PRE_RESET_DATA=$(cat "$TASK_BRAINSTORM_COUNTER" 2>/dev/null || echo "")
                TASK_PRE_RESET_KEY="${TASK_PRE_RESET_DATA%%|*}"
                echo "${TASK_PRE_RESET_KEY}|0" > "${TASK_BRAINSTORM_COUNTER}.tmp" && \
                    mv "${TASK_BRAINSTORM_COUNTER}.tmp" "$TASK_BRAINSTORM_COUNTER"
            fi
        fi
```

### Step 4 — Esegui e osserva il PASS atteso

Comando:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/hooks/brainstorming-gate.test.sh
```

Output atteso:

```
PASS scenario 1: N=1 nudge_soft + counter=1
PASS scenario 2: N=2 warn + block + counter=2
PASS scenario 3: N=4 hard block
PASS scenario 5: siae-brainstorming presente → no enforcement
PASS scenario 4: DEVFORGE_SKIP_BRAINSTORMING ignorata → gate enforce
PASS scenario 5b: post-skill reset + invoked_post_gate trigger=warn
PASS scenario 6: file .md → pass (out of scope)
PASS scenario 7: file .tf → IN scope (ADR-005)
PASS scenario 8: repo non-itsiae → pass (out of scope)
PASS scenario 9: DEVFORGE_ENFORCEMENT_OFF=1 → escape immediato
PASS scenario 13: gate always-on without STRICT/W2_DEFAULT (ADR-006)
PASS scenario 14: trivial single-file edit → short-circuit {} senza nudge
PASS scenario 15: secondo file toccato nel task → nudge (multi-file non trivial)
PASS scenario 16: edit .tf minuscolo → nudge (IaC sempre non-trivial)
PASS scenario 17: DEVFORGE_BRAINSTORM_COMPLEXITY=force-complex forza nudge + log override
PASS scenario 18: DEVFORGE_BRAINSTORM_COMPLEXITY=force-trivial NON bypassa IaC (resta non-trivial)
PASS scenario 19: post-skill resetta anche il counter task-scoped
Total: 19 — PASS: 19 — FAIL: 0
ALL SCENARIOS OK
```

Exit code: `0`.

Poi aggiungi il guard test in `tests/test_no_discretionary_bypass.py`. Apri il file ed estendi la lista `REMOVED` — NO, `DEVFORGE_BRAINSTORM_COMPLEXITY` è un flag nuovo e legittimo (non uno skip rimosso), quindi va in un test dedicato, non nella lista `REMOVED`. Aggiungi in coda al file (dopo `test_break_glass_regex_still_documented`, riga 68-69):

```python
def test_brainstorm_complexity_flag_cannot_bypass_iac():
    """DEVFORGE_BRAINSTORM_COMPLEXITY agisce solo sulla classificazione:
    force-trivial non deve silenziare un file IaC (.tf/.hcl), che resta
    sempre non-trivial nella libreria pura (Task 08). Guard statica: il
    gate deve loggare l'override (osservabilita') e la libreria non deve
    esporre un modo per disattivare il carve-out IaC via env var.
    """
    lib_taxonomy = (REPO / "lib" / "file-taxonomy.sh").read_text()
    assert "devforge_change_is_trivial" in lib_taxonomy, \
        "devforge_change_is_trivial mancante in lib/file-taxonomy.sh (Task 08 non applicato)"
    # Il carve-out IaC (*.tf|*.hcl -> return 1) non deve essere condizionato
    # da DEVFORGE_BRAINSTORM_COMPLEXITY dentro la funzione pura: la env var
    # va letta SOLO nel hook (brainstorming-gate), mai in file-taxonomy.sh.
    assert "DEVFORGE_BRAINSTORM_COMPLEXITY" not in lib_taxonomy, \
        "DEVFORGE_BRAINSTORM_COMPLEXITY non deve comparire nella libreria pura: " \
        "l'override va gestito solo nel hook, altrimenti force-trivial rischia di " \
        "bypassare il carve-out IaC/path-sensibile"

    gate = (REPO / "hooks" / "brainstorming-gate").read_text()
    assert "DEVFORGE_BRAINSTORM_COMPLEXITY" in gate, \
        "il hook non legge il flag di override della complessita'"
    assert "brainstorm_complexity_override" in gate, \
        "l'uso del flag non e' loggato (manca l'evento brainstorm_complexity_override)"
```

Comando:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && python3 -m pytest tests/test_no_discretionary_bypass.py -v
```

Output atteso:

```
tests/test_no_discretionary_bypass.py::test_removed_vars_absent_from_functional_code PASSED
tests/test_no_discretionary_bypass.py::test_removed_vars_absent_from_env_vars_doc PASSED
tests/test_no_discretionary_bypass.py::test_toolfail_breakglass_documented PASSED
tests/test_no_discretionary_bypass.py::test_killswitches_preserved_in_code PASSED
tests/test_no_discretionary_bypass.py::test_break_glass_regex_still_documented PASSED
tests/test_no_discretionary_bypass.py::test_brainstorm_complexity_flag_cannot_bypass_iac PASSED

====== 6 passed in 0.XXs ======
```

Infine, documenta il flag in `hooks/ENV_VARS.md`. Nella tabella `## Global` (righe 12-15), aggiungi una riga dopo `DEVFORGE_USE_SESSION_SCOPE`:

```markdown
| `DEVFORGE_BRAINSTORM_COMPLEXITY` | (unset) | v1.9x (REQ-DF-04) | Override *scoped+logged* della classificazione trivial/complesso in `brainstorming-gate`. Valori: `force-complex` (forza nudge anche su edit trivial), `force-trivial` (declassa un edit altrimenti trivial-per-dimensione). **Non** bypassa i carve-out IaC (`.tf`/`.hcl`)/path-sensibili (`hooks/`, `lib/*gate*`, `lib/review_evidence/`)/multi-file: quelli restano sempre "complesso" indipendentemente dal flag. Ogni uso è loggato via evento `brainstorm_complexity_override`. |
```

Verifica di non-regressione sulla suite hook aggregata:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/hooks/brainstorming-gate.test.sh && bash tests/hooks/post-skill.test.sh 2>/dev/null || echo "post-skill.test.sh non presente — skip (verificare nome reale prima del commit)"
```

Se `tests/hooks/post-skill.test.sh` esiste, deve restare verde (0 regressioni sullo scenario 5b che già copre il reset legacy).

### Step 5 — Commit

```bash
git add hooks/brainstorming-gate hooks/post-skill hooks/ENV_VARS.md tests/hooks/brainstorming-gate.test.sh tests/test_no_discretionary_bypass.py
git commit -m "feat(brainstorming-gate): scale enforcement with change complexity

Short-circuit to {} (no nudge, no counter increment) when a task-scoped
edit is single-file AND devforge_change_is_trivial() classifies it
trivial (non-IaC, within DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES, non
sensitive path). lines_changed is derived from Edit's old_string/
new_string or Write's content; files-touched are accumulated per task
in ~/.claude/.devforge-task-skills/<task_id>/files_touched across
invocations, since the hook only sees one file per call.

Add DEVFORGE_BRAINSTORM_COMPLEXITY (force-complex|force-trivial), a
scoped+logged override of the classification only: force-trivial
cannot silence an independently-complex change (IaC/sensitive-path/
multi-file stay complex), preserving the no-discretionary-bypass
invariant (precedent: PR #318).

Fix post-skill to also reset the task-scoped brainstorm-counter on
siae-brainstorming invocation, not only the legacy SID-anchored one
(REQ-DF-04 design gotcha #2)."
```

## Criteri di accettazione

- [ ] `hooks/brainstorming-gate` legge `DEVFORGE_BRAINSTORM_COMPLEXITY` PRIMA dell'incremento del counter e logga sempre l'uso via `devforge_log "brainstorm_complexity_override" ...` quando il flag è settato a `force-complex` o `force-trivial` (AC4 design).
- [ ] `force-trivial` NON bypassa un cambiamento classificato non-trivial da `devforge_change_is_trivial` per motivi diversi dalla sola dimensione (IaC `.tf`/`.hcl`, path sensibile `hooks/`/`lib/*gate*`/`lib/review_evidence/`, multi-file) — verificato dallo Scenario 18 e dal guard test Python.
- [ ] `hooks/brainstorming-gate` accumula i file toccati nel task corrente in `~/.claude/.devforge-task-skills/<task_id>/files_touched` (append distinct, cross-invocazione) e calcola `lines_changed` da `tool_input.old_string`/`tool_input.new_string` (Edit) o `tool_input.content` (Write).
- [ ] Se il cambiamento è single-file-in-task E `devforge_change_is_trivial` ritorna trivial (e nessun override lo complica), il gate esce con `echo '{}'` **senza** incrementare il counter e **senza** emettere `brainstorming_nudge_soft`/`brainstorming_gate_warn`/`brainstorming_gate_blocked` (AC1 design, Scenario 14).
- [ ] Un secondo file toccato nello stesso task fa tornare il gate al comportamento pieno (nudge) anche se le righe cambiate sono poche (AC2 design, Scenario 15).
- [ ] Un file `.tf`/`.hcl` fa sempre nudge indipendentemente dalla dimensione dell'edit (Scenario 16).
- [ ] `hooks/post-skill` resetta sia il counter legacy SID-anchored (`~/.claude/.devforge-brainstorm-counter`, comportamento preesistente, Scenario 5b) sia il counter task-scoped (`~/.claude/.devforge-task-skills/<task_id>/brainstorm-counter`, Scenario 19 — fix del bug noto, design gotcha #2).
- [ ] `tests/hooks/brainstorming-gate.test.sh` esce con codice `0`, 19/19 PASS.
- [ ] `python3 -m pytest tests/test_no_discretionary_bypass.py -v` esce verde, incluso il nuovo `test_brainstorm_complexity_flag_cannot_bypass_iac`.
- [ ] `DEVFORGE_BRAINSTORM_COMPLEXITY` documentato in `hooks/ENV_VARS.md` (tabella `## Global`), coerente con lo stile delle righe esistenti (`DEVFORGE_ENFORCEMENT_OFF`, `DEVFORGE_USE_SESSION_SCOPE`).
- [ ] Zero placeholder; nessuna variabile d'ambiente di skip discrezionale reintrodotta (la lista `REMOVED` in `tests/test_no_discretionary_bypass.py` resta invariata e verde).
