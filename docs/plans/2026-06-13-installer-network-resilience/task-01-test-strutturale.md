# Task 01 — Test strutturale `setup_github_network` (TDD red)

**Goal:** test che fallisce finché `install.sh` non ha `setup_github_network`
configurata correttamente e chiamata nel punto giusto.

## File
- Crea: `tests/test_installer_network_resilience.sh`

## Contenuto del test (4 asserzioni)
1. **Esistenza funzione:** `grep -q 'setup_github_network()' install.sh`.
2. **Call site prima di gh auth status:** la riga di chiamata `setup_github_network`
   compare PRIMA della prima occorrenza di `gh auth status` (confronto numeri di
   riga via `grep -n`).
3. **Idempotenza NO_PROXY:** sorgiando la funzione due volte in una subshell con
   `NO_PROXY` preimpostato, `github.com` compare una sola volta (no duplicati).
   Estrarre la funzione via `sed -n '/setup_github_network()/,/^}/p' install.sh`
   ed eseguirla in `bash -c`.
4. **Sintassi:** `bash -n install.sh` esce 0.

## Struttura test (forma attesa)
```bash
#!/usr/bin/env bash
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL="${ROOT}/install.sh"
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
ko(){ echo "  FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

# T1 funzione esiste
grep -q 'setup_github_network()' "$INSTALL" && ok "T1 funzione esiste" || ko "T1" "assente"

# T2 chiamata prima di gh auth status
call_ln=$(grep -n '^\s*setup_github_network\s*$' "$INSTALL" | head -1 | cut -d: -f1)
auth_ln=$(grep -n 'gh auth status' "$INSTALL" | head -1 | cut -d: -f1)
{ [ -n "$call_ln" ] && [ -n "$auth_ln" ] && [ "$call_ln" -lt "$auth_ln" ]; } \
  && ok "T2 chiamata prima di gh auth status" || ko "T2" "call=$call_ln auth=$auth_ln"

# T3 idempotenza NO_PROXY
# NB: la funzione DEVE iniziare con 'setup_github_network()' e terminare con '}'
#     entrambi a colonna 0 (no indent) — vincolo del sed di estrazione (vedi task-02).
fn=$(sed -n '/^setup_github_network()/,/^}/p' "$INSTALL")
out=$(bash -c "
  info(){ :; }
  git(){ :; }   # stub: non toccare git config reale nel test
  $fn
  NO_PROXY=''; no_proxy=''
  setup_github_network; setup_github_network
  echo \"\$NO_PROXY\"
" 2>/dev/null)
# conta 'github.com' come TOKEN virgola-separato (non sottostringa): deve essere 1.
n=$(tr ',' '\n' <<<"$out" | grep -cx 'github\.com')
[ "$n" -eq 1 ] && ok "T3 idempotenza NO_PROXY" || ko "T3" "occorrenze=$n out=$out"

# AC3 (on-VPN invariato) non ha test dedicato: NO_PROXY/no-proxy sono no-op
# innocui on-VPN (github è DIRECT nel PAC). Verifica empirica già fatta (design doc).

# T4 sintassi
bash -n "$INSTALL" && ok "T4 bash -n pulito" || ko "T4" "syntax error"

echo "installer-net: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

## Nota stub
Il test stubba `git()` a no-op nella subshell di T3 per non scrivere git config
globale reale durante il test (T3 verifica solo la logica NO_PROXY).

## Done quando
- `bash tests/test_installer_network_resilience.sh` FALLISCE su T1/T2 (funzione
  non ancora presente) → red confermato. T4 può già passare.
