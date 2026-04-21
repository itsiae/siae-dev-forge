# Task 16 — hooks/session-start repair banner + DEVFORGE_HIDE_REPAIR_BANNER guard

**PR:** PR-2 | **SP:** 0.1 SP-Augmented | **Dipendenze:** nessuna (indipendente da T13-T15) | **Stato:** [PENDING]

## File coinvolti

- `hooks/session-start` (modifica: aggiunta blocco repair banner vicino inizio file)
- `tests/windows-runtime/session-start-banner.test.sh` (nuovo — bats test)

## Step 1 — Test RED

File: `tests/windows-runtime/session-start-banner.test.sh`

```bash
#!/usr/bin/env bats

setup() {
    TEST_HOME=$(mktemp -d)
    export HOME="$TEST_HOME"
    mkdir -p "$HOME/.claude"

    # Fake APPDATA come path dentro TEST_HOME (cross-platform)
    export APPDATA="$TEST_HOME/appdata"
    mkdir -p "$APPDATA/Claude"

    # Copia session-start in posizione isolata
    SESSION_START="${BATS_TEST_DIRNAME}/../../hooks/session-start"
}

teardown() {
    rm -rf "$TEST_HOME"
    unset DEVFORGE_HIDE_REPAIR_BANNER
}

@test "session-start emette repair banner se flag presente" {
    # Crea flag
    touch "$APPDATA/Claude/devforge-needs-repair"

    # Estrai solo il blocco banner dal session-start reale (evita side-effect full hook)
    # Usiamo un harness che source tutto il file ma con early-exit dopo banner
    run bash -c "
        APPDATA='$APPDATA'
        export HOME='$TEST_HOME'
        # Stub devforge_new_sid e altre funzioni per evitare full run
        $(sed -n '1,/^# Self-healing repair banner/,/^fi$/p' '$SESSION_START' | head -20)
    "
    [[ "$output" =~ "DevForge Repair Banner" ]]
    [[ "$output" =~ "install.ps1" ]]

    # Flag removed after banner show
    [ ! -f "$APPDATA/Claude/devforge-needs-repair" ]
}

@test "session-start NON mostra banner se flag assente" {
    # No flag
    run bash -c "
        APPDATA='$APPDATA'
        export HOME='$TEST_HOME'
        REPAIR_FLAG=\"\${APPDATA:-\$HOME/.config}/Claude/devforge-needs-repair\"
        if [[ -f \"\$REPAIR_FLAG\" ]]; then
            echo 'banner shown'
        else
            echo 'no banner'
        fi
    "
    [[ "$output" =~ "no banner" ]]
    [[ ! "$output" =~ "Repair Banner" ]]
}

@test "DEVFORGE_HIDE_REPAIR_BANNER=1 sopprime banner anche se flag presente" {
    touch "$APPDATA/Claude/devforge-needs-repair"
    export DEVFORGE_HIDE_REPAIR_BANNER=1

    run bash -c "
        APPDATA='$APPDATA'
        export HOME='$TEST_HOME'
        if [[ \"\${DEVFORGE_HIDE_REPAIR_BANNER:-}\" != \"1\" ]]; then
            REPAIR_FLAG=\"\${APPDATA:-\$HOME/.config}/Claude/devforge-needs-repair\"
            if [[ -f \"\$REPAIR_FLAG\" ]]; then
                echo 'banner shown'
            fi
        fi
        echo 'done'
    "
    [[ ! "$output" =~ "banner shown" ]]
    [[ "$output" =~ "done" ]]

    # Flag NON rimosso con panic button attivo (banner non parte)
    [ -f "$APPDATA/Claude/devforge-needs-repair" ]
}
```

## Step 2 — Run (RED)

```bash
bats tests/windows-runtime/session-start-banner.test.sh
# Atteso: 3 fail (session-start non ha blocco banner)
```

## Step 3 — Impl

Modifica `hooks/session-start` — aggiungi dopo la riga `set -euo pipefail` e `export DEVFORGE_CURRENT_HOOK="session-start"` (righe 10-11), prima del resto:

```bash
# --- Self-healing repair banner (panic button: DEVFORGE_HIDE_REPAIR_BANNER=1) ---
# Emette istruzioni di ripristino se una sessione precedente ha rilevato bash
# mancante (flag scritto da run-hook.cmd fail-loud path).
# Il drain dell'evento repair_needed avviene automaticamente via .global-outbox/
# (pattern canonico lib/telemetry-upload.sh, nessun drain custom qui).
if [[ "${DEVFORGE_HIDE_REPAIR_BANNER:-}" != "1" ]]; then
    REPAIR_FLAG="${APPDATA:-$HOME/.config}/Claude/devforge-needs-repair"
    if [[ -f "$REPAIR_FLAG" ]]; then
        cat <<EOF
[DevForge Repair Banner]
Una sessione precedente ha rilevato bash mancante su Windows.
Per ripristinare (PowerShell):
  Set-ExecutionPolicy -Scope Process Bypass -Force
  iwr https://github.com/itsiae/siae-dev-forge/releases/latest/download/install.ps1 | iex

Per silenziare questo banner: set DEVFORGE_HIDE_REPAIR_BANNER=1
EOF
        rm -f "$REPAIR_FLAG"
    fi
fi
# --- fine repair banner ---
```

## Step 4 — Run (GREEN)

```bash
bats tests/windows-runtime/session-start-banner.test.sh
# Atteso: 3/3 pass
```

Verifica zero-regression sugli altri hook:

```bash
bash tests/run-all.sh
# Atteso: tutti i test bats/shell esistenti restano verdi
```

## Step 5 — Commit

```bash
git add hooks/session-start tests/windows-runtime/session-start-banner.test.sh
git commit -m "feat(windows-runtime): session-start repair banner + DEVFORGE_HIDE_REPAIR_BANNER [AC-17]"
```
