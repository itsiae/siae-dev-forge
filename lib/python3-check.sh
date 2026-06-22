#!/usr/bin/env bash
# python3-check.sh — banner esplicito quando python3 manca (P-banner).
# ─────────────────────────────────────────────────────────────────
# Source-only library: nessun side-effect al load.
#
# devforge_python3_banner stampa un banner multilinea ESPLICITO se python3 NON è
# installato, altrimenti niente (stringa vuota). La telemetria DevForge (token,
# attribuzione, KPI, durabilità zero-loss) degrada senza python3 → l'utente DEVE
# vederlo. Questo è solo un AVVISO (non blocca operazioni).
#
# Usa esclusivamente builtin (command, printf) → funziona anche con PATH vuoto e
# non introduce dipendenze esterne (testabile in isolamento, niente symlink farm).
# ─────────────────────────────────────────────────────────────────
devforge_python3_banner() {
    command -v python3 >/dev/null 2>&1 && return 0
    printf '%s\n' \
'⚠️  ATTENZIONE DevForge — python3 NON è installato su questa macchina.' \
'La telemetria (conteggio token, attribuzione identità, KPI di produttività) e le' \
'garanzie zero-loss di durabilità sono DEGRADATE finché python3 non viene installato.' \
'Installa python3 e riavvia la sessione Claude Code:' \
'  • macOS:          brew install python3' \
'  • Debian/Ubuntu:  sudo apt-get install -y python3' \
'  • RHEL/Fedora:    sudo dnf install -y python3' \
'  • Windows:        winget install Python.Python.3'
}
