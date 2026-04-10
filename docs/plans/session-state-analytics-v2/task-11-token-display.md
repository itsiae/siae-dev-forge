# Task 11 — Statusline + context: token, costo, telemetry status

**Stato:** [PENDING]
**File coinvolti:** `statusline/devforge-statusline.sh` (MODIFICA), `hooks/devforge-context-always` (MODIFICA)
**AC coperti:** AC-16
**Fase:** PR3
**Dipende da:** Task 6, 8

---

## Step 1 — Statusline: token + costo

In `statusline/devforge-statusline.sh`, sezione 3 (dopo SESSION_COMMITS), leggi token stats dalla dir sessione:

```bash
# Token stats from session dir
SESSION_TOKENS=""
SESSION_COST=""
if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -f "${DEVFORGE_SESSION_DIR}/token-stats.json" ] && command -v python3 >/dev/null 2>&1; then
    TDATA=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
t=d.get('total',0)
c=d.get('cost_eur',0)
tok=f'{t/1e6:.1f}M' if t>=1e6 else f'{t/1e3:.0f}K' if t>=1e3 else str(t)
print(f'{tok}\t{c:.2f}')
" "${DEVFORGE_SESSION_DIR}/token-stats.json" 2>/dev/null) || true
    if [ -n "$TDATA" ]; then
        SESSION_TOKENS="$(printf '%s' "$TDATA" | cut -f1)"
        SESSION_COST="$(printf '%s' "$TDATA" | cut -f2)"
    fi
fi
```

In LINE1 (dopo il blocco TDD, prima della chiusura):
```bash
if [ -n "$SESSION_TOKENS" ]; then
    LINE1="${LINE1} | ${SESSION_TOKENS} tok"
    [ -n "$SESSION_COST" ] && [ "$SESSION_COST" != "0.00" ] && LINE1="${LINE1} ~${SESSION_COST}€"
fi
```

## Step 2 — Context: token display

In `hooks/devforge-context-always`, nella sezione Session Stats, dopo aver calcolato STATS_SECTION:

```bash
# Token display from session dir
TOKEN_DISPLAY=""
if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -f "${DEVFORGE_SESSION_DIR}/token-stats.json" ] && command -v python3 >/dev/null 2>&1; then
    TOKEN_DISPLAY=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
t=d.get('total',0)
c=d.get('cost_eur',0)
tok=f'{t/1e6:.1f}M' if t>=1e6 else f'{t/1e3:.0f}K' if t>=1e3 else str(t)
print(f'tokens={tok} | cost={c:.2f}€')
" "${DEVFORGE_SESSION_DIR}/token-stats.json" 2>/dev/null) || true
fi
[ -n "$TOKEN_DISPLAY" ] && STATS_SECTION="${STATS_SECTION} | ${TOKEN_DISPLAY}"
```

## Step 3 — Verifica

```bash
bash -n statusline/devforge-statusline.sh
bash -n hooks/devforge-context-always
```
Output atteso: nessun errore.

Risultato visivo statusline:
```
🔨 DevForge [4. Implementation] | feat/branch | 1.2M tok ~3.52€
```

Risultato DevForge Context:
```
Session: 15min | messaggi=12 | commits=1 | skills=2 | tokens=1.2M | cost=3.52€
```
