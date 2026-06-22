# Task 02 — Registra `SessionEnd` in hooks.json + fix contatori hardcoded

**Goal:** Registrare l'evento `SessionEnd` → `run-hook.cmd session-end` in `hooks.json` e
aggiornare i contatori hardcoded nei test al valore reale misurato in RED.

**File coinvolti:**
- Modifica: `hooks/hooks.json`
- Modifica: `tests/hooks/hooks-json-var-expansion.test.sh` (righe 33, 66)
- Eventuale modifica: `tests/test_count_consistency.py` (se conta gli hook)

**Copre AC:** AC-9. **Dipende da:** Task 01.

> **NOTA BASELINE (drift pre-esistente, verificato 2026-06-19):** il test
> `hooks-json-var-expansion.test.sh` è **già in FAIL ORA**, prima di qualsiasi modifica:
> hardcoda `26` ma `hooks.json` contiene già **28** occorrenze del pattern
> `\"${CLAUDE_PLUGIN_ROOT}` e 28 command. Due hook sono stati aggiunti in passato senza
> allineare il contatore. Questo task quindi **chiude anche un test rotto pre-esistente**.
> Dopo l'aggiunta di `SessionEnd`: il valore diventa **29** (28 + 1). Il valore va sempre
> letto dall'output del test, mai assunto.

---

## Step TDD

### Step 1 — Misura il baseline reale (il test è GIÀ RED)

Run: `bash tests/hooks/hooks-json-var-expansion.test.sh`
Output atteso ATTUALE (pre-modifica): `FAIL[2]: attese 26 occorrenze ... trovate 28`
(drift pre-esistente). Conferma: il baseline reale è **28**, non 26. I due assert hardcodano `26`:
- riga 33: `if [ "$escaped_count" -ne 26 ]`
- riga 66: `if [ "$total" -ne 26 ]`

### Step 2 — Aggiungi `SessionEnd` a `hooks.json`

In `hooks/hooks.json`, aggiungi un blocco evento `SessionEnd` accanto a `Stop`
(stesso pattern di invocazione `run-hook.cmd`):

```json
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-end"
          }
        ]
      }
    ]
```

Verifica validità JSON: `jq . hooks/hooks.json >/dev/null && echo OK`
Output atteso: `OK`

### Step 3 — Esegui e verifica il nuovo conteggio (RED)

Run: `bash tests/hooks/hooks-json-var-expansion.test.sh`
Output atteso: `FAIL[2]: attese 26 occorrenze ... trovate 29` e
`FAIL[4]: attesi 26 commands totali, trovati 29`.

> Il valore reale (**29** = 28 baseline + 1 SessionEnd) va **letto dall'output**, non
> assunto. Se l'output mostra un numero diverso, usa quello.

### Step 4 — Aggiorna i contatori al valore osservato (GREEN)

In `tests/hooks/hooks-json-var-expansion.test.sh` (sostituisci `26` → `29`, valore reale osservato):
- riga 29 (commento): `# Assert 2: 29 occorrenze del byte-pattern escaped-dquote ...`
- riga 33: `if [ "$escaped_count" -ne 29 ]; then`
- riga 34 (messaggio): `attese 29 occorrenze`
- riga 66: `if [ "$total" -ne 29 ]; then`
- riga 67 (messaggio): `attesi 29 commands totali`

Se `tests/test_count_consistency.py` conta gli hook con un valore atteso hardcoded,
aggiorna anche quel valore al numero osservato eseguendo:
`python3 -m pytest tests/test_count_consistency.py -v` e leggendo l'eventuale assert
fallito.

### Step 5 — Esegui e verifica che passa (GREEN)

Run: `bash tests/hooks/hooks-json-var-expansion.test.sh && python3 -m pytest tests/test_count_consistency.py -q`
Output atteso: nessun `FAIL`, exit code 0.

### Step 6 — Commit

```bash
git add hooks/hooks.json tests/hooks/hooks-json-var-expansion.test.sh tests/test_count_consistency.py
git commit -m "feat(hooks): registra evento SessionEnd + allinea contatori test (task-02)"
```

---

## Criteri di accettazione

- [ ] `hooks/hooks.json` contiene il blocco `SessionEnd` → `session-end`, JSON valido (`jq .`).
- [ ] `tests/hooks/hooks-json-var-expansion.test.sh` passa con i contatori aggiornati al
      valore reale osservato (non indovinato) — questo **chiude anche il drift
      pre-esistente** (test era RED a 26 vs 28 reali).
- [ ] `tests/test_count_consistency.py` passa (se conta gli hook).
- [ ] Nessun altro test di count-consistency rotto (verifica in `tests/run-all.sh`).
