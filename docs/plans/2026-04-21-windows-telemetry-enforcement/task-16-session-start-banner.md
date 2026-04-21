# Task 16 — Repair banner + DEVFORGE_HIDE_REPAIR_BANNER guard

**PR:** PR-2 | **SP:** 0.1 SP-Augmented | **Dipendenze:** nessuna (indipendente da T13-T15) | **Stato:** [PENDING]

## File coinvolti

- `hooks/lib/repair-banner.sh` (nuovo — logica banner isolata, testabile, sourced da session-start)
- `hooks/session-start` (modifica: source del file sopra)
- `tests/windows-runtime/repair-banner.test.sh` (nuovo — bats che testa direttamente repair-banner.sh)

## Scelta architetturale (BLOCK-3 plan-reviewer fix)

Il banner era originariamente inline in `session-start` ma il test bats non poteva isolarlo senza sed parsing fragile (2 `fi` nidificati, sed `-n` con 2 address range non standard). Estraggo in file sourced dedicato — SRP rispettato, test deterministico senza fragilità.

## Step 1 — Test RED

File: `tests/windows-runtime/repair-banner.test.sh`

```bash
#!/usr/bin/env bats

setup() {
    TEST_HOME=$(mktemp -d)
    export HOME="$TEST_HOME"
    export APPDATA="$TEST_HOME/appdata"
    mkdir -p "$APPDATA/Claude"

    BANNER_LIB="${BATS_TEST_DIRNAME}/../../hooks/lib/repair-banner.sh"
}

teardown() {
    rm -rf "$TEST_HOME"
    unset DEVFORGE_HIDE_REPAIR_BANNER
}

@test "repair-banner.sh emette banner se flag devforge-needs-repair presente" {
    touch "$APPDATA/Claude/devforge-needs-repair"

    run bash -c "source '$BANNER_LIB'; devforge_show_repair_banner_if_needed"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "DevForge Repair Banner" ]]
    [[ "$output" =~ "install.ps1" ]]
    [[ "$output" =~ "DEVFORGE_HIDE_REPAIR_BANNER" ]]

    # Flag rimosso dopo emissione banner
    [ ! -f "$APPDATA/Claude/devforge-needs-repair" ]
}

@test "repair-banner.sh no-op se flag assente" {
    run bash -c "source '$BANNER_LIB'; devforge_show_repair_banner_if_needed"

    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "Repair Banner" ]]
}

@test "DEVFORGE_HIDE_REPAIR_BANNER=1 sopprime banner E preserva flag" {
    touch "$APPDATA/Claude/devforge-needs-repair"
    export DEVFORGE_HIDE_REPAIR_BANNER=1

    run bash -c "export DEVFORGE_HIDE_REPAIR_BANNER=1; source '$BANNER_LIB'; devforge_show_repair_banner_if_needed"

    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "Repair Banner" ]]

    # Flag NON rimosso — panic button preserva stato per quando l'utente ripara
    [ -f "$APPDATA/Claude/devforge-needs-repair" ]
}

@test "repair-banner fallback a \$HOME/.config se APPDATA non settato" {
    unset APPDATA
    mkdir -p "$HOME/.config/Claude"
    touch "$HOME/.config/Claude/devforge-needs-repair"

    run bash -c "unset APPDATA; source '$BANNER_LIB'; devforge_show_repair_banner_if_needed"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "DevForge Repair Banner" ]]
    [ ! -f "$HOME/.config/Claude/devforge-needs-repair" ]
}

@test "session-start source repair-banner.sh" {
    SESSION_START="${BATS_TEST_DIRNAME}/../../hooks/session-start"
    run grep -E "source.*repair-banner\.sh|\. .*repair-banner\.sh" "$SESSION_START"
    [ "$status" -eq 0 ]
}
```

## Step 2 — Run (RED)

```bash
bats tests/windows-runtime/repair-banner.test.sh
# Atteso: 5 fail (lib non esiste, session-start non la sourcia)
```

## Step 3 — Impl

### 3a. Nuovo file `hooks/lib/repair-banner.sh`

```bash
#!/usr/bin/env bash
# hooks/lib/repair-banner.sh — Self-healing repair banner per Windows Telemetry Enforcement.
#
# Funzione sourced da session-start. Se una sessione precedente ha rilevato
# bash mancante (flag scritto da run-hook.cmd fail-loud), mostra istruzioni
# di ripristino all'utente via stderr + emette context per il model.
#
# Panic button: DEVFORGE_HIDE_REPAIR_BANNER=1 sopprime il banner E preserva
# il flag (stato broken rimane visibile per riparazione futura).
#
# Drain dell'evento repair_needed: automatico via .global-outbox/ (pattern
# canonico lib/telemetry-upload.sh — nessun drain custom qui).

devforge_show_repair_banner_if_needed() {
    # Panic button check
    if [[ "${DEVFORGE_HIDE_REPAIR_BANNER:-}" == "1" ]]; then
        return 0
    fi

    # Resolve flag path (APPDATA su Windows+GitBash, fallback XDG_CONFIG_HOME-like)
    local repair_flag="${APPDATA:-$HOME/.config}/Claude/devforge-needs-repair"

    if [[ ! -f "$repair_flag" ]]; then
        return 0
    fi

    cat <<EOF
[DevForge Repair Banner]
Una sessione precedente ha rilevato bash mancante su Windows.
Per ripristinare (PowerShell):
  Set-ExecutionPolicy -Scope Process Bypass -Force
  iwr https://github.com/itsiae/siae-dev-forge/releases/latest/download/install.ps1 | iex

Per silenziare questo banner: set DEVFORGE_HIDE_REPAIR_BANNER=1
EOF

    rm -f "$repair_flag"
}
```

### 3b. Modifica `hooks/session-start`

Aggiungi dopo la riga `export DEVFORGE_CURRENT_HOOK="session-start"` (riga 11), prima di `SCRIPT_DIR=`:

```bash
# --- Self-healing repair banner (Windows enforcement PR-2) -------------------
# Sourcing file dedicato per isolamento + testabilità (plan-reviewer BLOCK-3 fix).
# Plugin root non ancora risolto — calcolo SCRIPT_DIR inline per trovare lib/.
_DEVFORGE_HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# shellcheck source=lib/repair-banner.sh
if [[ -f "${_DEVFORGE_HOOK_DIR}/lib/repair-banner.sh" ]]; then
    source "${_DEVFORGE_HOOK_DIR}/lib/repair-banner.sh"
    devforge_show_repair_banner_if_needed 2>&1 || true
fi
unset _DEVFORGE_HOOK_DIR
# --- fine repair banner ------------------------------------------------------
```

## Step 4 — Run (GREEN)

```bash
bats tests/windows-runtime/repair-banner.test.sh
# Atteso: 5/5 pass

# Zero-regression guards
bash tests/run-all.sh
# Atteso: tutti i test esistenti restano verdi
```

## Step 5 — Commit

```bash
git add hooks/lib/repair-banner.sh hooks/session-start tests/windows-runtime/repair-banner.test.sh
git commit -m "feat(windows-runtime): repair-banner.sh isolato + session-start source [AC-17]"
```
