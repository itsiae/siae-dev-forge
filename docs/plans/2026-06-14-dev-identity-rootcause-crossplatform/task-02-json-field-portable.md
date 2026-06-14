# Task 02 — F2a: helper devforge_json_field (node→python3→degraded)

**Stato:** PENDING
**Dipende da:** task-00 (decisione node-first)
**File:** `lib/logger.sh`, `tests/zero-loss/unit/test_json_field_portable.sh` (nuovo)

## Obiettivo
Estrarre un campo JSON in modo portabile (Windows senza python3), con degrado osservabile.

## Approccio TDD
### RED — `tests/zero-loss/unit/test_json_field_portable.sh`
Crea un `.claude.json` fittizio con `oauthAccount.emailAddress` noto; sorcia `lib/logger.sh`; verifica:
1. con node+python3 disponibili → `devforge_json_field "$f" oauthAccount.emailAddress` = email attesa
2. con `python3` mascherato dal PATH → stesso risultato via node
3. con `node` mascherato dal PATH → stesso risultato via python3
4. con entrambi mascherati → stringa vuota
5. nel caso 4 viene emesso un evento `telemetry_degraded` con `meta.reason="no_json_interpreter"`

### GREEN — aggiungere in `lib/logger.sh`
```bash
# Portable JSON field reader: node first (Claude Code runs on Node), python3 fallback.
# Empty string + observable telemetry_degraded if no interpreter. Never aborts.
# NB: solo campi STRINGA — il path python3 converte il valore 0 in stringa vuota (operatore `or`).
devforge_json_field() {
    local file="$1" path="$2" out=""
    [ -f "$file" ] || { printf ''; return 0; }
    if command -v node >/dev/null 2>&1; then
        out=$(node -e 'try{const fs=require("fs");const d=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));const v=process.argv[2].split(".").reduce((o,k)=>(o&&o[k]!=null)?o[k]:"",d);process.stdout.write(String(v||""))}catch(e){process.exit(3)}' "$file" "$path" 2>/dev/null) && { printf '%s' "$out"; return 0; }
    fi
    if command -v python3 >/dev/null 2>&1; then
        out=$(python3 -c 'import json,sys,functools
d=json.load(open(sys.argv[1]))
v=functools.reduce(lambda o,k:(o.get(k,"") if isinstance(o,dict) else ""),sys.argv[2].split("."),d)
sys.stdout.write(str(v or ""))' "$file" "$path" 2>/dev/null) && { printf '%s' "$out"; return 0; }
    fi
    devforge_log "telemetry_degraded" "warning" '{"reason":"no_json_interpreter"}' 2>/dev/null || true
    printf ''
}
```

## Anti-ricorsione
`devforge_log` legge l'identità dalle env var pinnate (`DEVFORGE_AUTH_EMAIL`), NON da
`devforge_json_field` → l'emissione di `telemetry_degraded` non rientra nella funzione.

## Criteri di accettazione (design AC 3)
Casi 1-5 verdi.

## No-regression
Funzione nuova, additiva. Nessuna chiamata esistente modificata qui (vedi task-03).
