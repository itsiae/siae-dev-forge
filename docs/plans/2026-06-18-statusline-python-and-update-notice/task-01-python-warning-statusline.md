# Task 01 — Feature 1: avviso python3 mancante (statusline)

**Stato:** [PENDING]
**File toccati:** `tests/statusline/test_statusline_python_warning.sh` (nuovo), `statusline/devforge-statusline.sh`
**AC coperti:** 1, 2, 3
**Stima:** Umano ~1 · Augmented ~0.5

## Ciclo TDD

### RED — scrivi il test (deve fallire)

Primo passo operativo: la dir `tests/statusline/` non esiste ancora → creala:
```bash
mkdir -p tests/statusline
```

Crea `tests/statusline/test_statusline_python_warning.sh`. Il test invoca lo script con un
`PATH` che NON contiene `python3` e verifica la presenza del messaggio; poi un caso con
`python3` presente e verifica l'ASSENZA del messaggio.

Tecnica per simulare "python3 assente": creare una dir PATH minimale che contiene solo i
binari necessari (bash, jq se serve, coreutils) ma NON python3. Più robusto: usare una
funzione wrapper non è possibile per `command -v` da subshell, quindi si usa un `PATH`
isolato con symlink solo ai binari richiesti.

```bash
#!/usr/bin/env bash
# Test: statusline mostra avviso quando python3 manca dal PATH (Feature 1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUSLINE="$(cd "$SCRIPT_DIR/../../statusline" && pwd)/devforge-statusline.sh"
PASS=0; FAIL=0

# Costruisce un PATH isolato senza python3, con symlink ai binari realmente usati dallo script
make_path_without_python() {
  local d="$1"; mkdir -p "$d"
  for bin in bash sh env cat cut sed tr grep head printf date git jq mkdir chmod rm dirname basename; do
    local p; p="$(command -v "$bin" 2>/dev/null || true)"
    [ -n "$p" ] && ln -sf "$p" "$d/$bin" 2>/dev/null || true
  done
}

# --- Caso 1: python3 ASSENTE → messaggio presente ---
TMP1="$(mktemp -d)"
make_path_without_python "$TMP1/bin"
OUT1="$(printf '{}' | env -i HOME="$HOME" PATH="$TMP1/bin" bash "$STATUSLINE" 2>/dev/null || true)"
if printf '%s' "$OUT1" | grep -q "python3 assente"; then
  PASS=$((PASS+1)); echo "  PASS  python3 assente → avviso mostrato"
else
  FAIL=$((FAIL+1)); echo "  FAIL  python3 assente → avviso NON mostrato"; printf 'OUT: %s\n' "$OUT1"
fi
rm -rf "$TMP1"

# --- Caso 2: python3 PRESENTE → nessun messaggio ---
OUT2="$(printf '{}' | bash "$STATUSLINE" 2>/dev/null || true)"
if printf '%s' "$OUT2" | grep -q "python3 assente"; then
  FAIL=$((FAIL+1)); echo "  FAIL  python3 presente → avviso mostrato erroneamente"
else
  PASS=$((PASS+1)); echo "  PASS  python3 presente → nessun avviso"
fi

# Nota: l'AC 3 ("nessun errore di script") è verificato implicitamente — entrambe le invocazioni
# usano `|| true` e lo script gira sotto `set -euo pipefail`; un crash produrrebbe output vuoto e
# farebbe fallire le asserzioni sopra. Nessun increment dedicato → totale atteso PASS=2.
echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

Esegui: `bash tests/statusline/test_statusline_python_warning.sh` → DEVE fallire (caso 1 FAIL, messaggio non ancora implementato; atteso PASS=1 FAIL=1).

### GREEN — implementa

In `statusline/devforge-statusline.sh`, nella sezione warning (dopo il blocco `if [ "$CTX_INT" -ge 80 ]`
a riga ~262-264, prima della sezione "Skill checklist"), aggiungi:

```bash
if ! command -v python3 >/dev/null 2>&1; then
  WARN_STR="${WARN_STR:+$WARN_STR }$(printf '%b🐍 python3 assente — installalo per token/telemetria%b' "$YELLOW" "$RESET")"
fi
```

Riesegui il test → DEVE passare (PASS=2, FAIL=0).

### REFACTOR

Nessun refactor previsto: blocco additivo isolato. Verifica solo che il pattern `${WARN_STR:+...}`
sia identico agli altri warning della sezione.

## Criteri di completamento

- [ ] Test `test_statusline_python_warning.sh` esiste e passa (PASS=2, FAIL=0)
- [ ] Caso python3 assente mostra "python3 assente"
- [ ] Caso python3 presente NON mostra il messaggio
- [ ] Script esce senza errore in entrambi i casi
