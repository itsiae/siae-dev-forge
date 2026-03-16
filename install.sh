#!/usr/bin/env bash
# install.sh — Installa siae-devforge come plugin di Claude Code dal repo GitHub
set -euo pipefail

GITHUB_REPO="itsiae/siae-dev-forge"
MARKETPLACE_NAME="siae-devforge"
PLUGIN_KEY="siae-devforge@siae-devforge"

# Colori
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}✓${NC} $1"; }
warning() { echo -e "${YELLOW}!${NC} $1"; }
error()   { echo -e "${RED}✗${NC} $1"; exit 1; }

echo ""
echo "| 🟢 SICURO — 🔨 DevForge · Installazione plugin |"
echo "|:---|"
echo ""

# Verifica prerequisiti
command -v claude &>/dev/null || error "Claude Code non trovato. Installalo prima: https://docs.anthropic.com/en/docs/build-with-claude/claude-code"
command -v gh &>/dev/null    || error "GitHub CLI (gh) non trovato. Installalo: https://cli.github.com"

# Verifica autenticazione GitHub
if ! gh auth status &>/dev/null; then
  error "Non autenticato su GitHub. Esegui: gh auth login"
fi
info "GitHub autenticato"

# Verifica accesso al repo
if ! gh repo view "${GITHUB_REPO}" &>/dev/null; then
  error "Impossibile accedere a ${GITHUB_REPO}. Verifica i permessi GitHub."
fi
info "Accesso al repo ${GITHUB_REPO} verificato"

# Abilita autoUpdate per il marketplace (richiede python3)
enable_autoupdate() {
  local mkt_file="${HOME}/.claude/plugins/known_marketplaces.json"
  if [ -f "$mkt_file" ] && command -v python3 &>/dev/null; then
    python3 - "$mkt_file" "$MARKETPLACE_NAME" <<'PY'
import json, sys
path, name = sys.argv[1], sys.argv[2]
with open(path) as f:
    data = json.load(f)
if name in data and not data[name].get("autoUpdate"):
    data[name]["autoUpdate"] = True
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
PY
    info "autoUpdate abilitato per il marketplace"
  fi
}

# Installa o aggiorna plugin
if claude plugin list 2>/dev/null | grep -q "siae-devforge"; then
  warning "Plugin già installato — aggiorno all'ultima versione"
  # Aggiorna il marketplace cache (git pull del repo)
  claude plugin marketplace update "${MARKETPLACE_NAME}"
  info "Marketplace cache aggiornato"
  # Reinstalla per applicare la nuova versione
  claude plugin uninstall "${MARKETPLACE_NAME}" 2>/dev/null || true
  claude plugin install "${PLUGIN_KEY}" --scope user
  info "Plugin aggiornato all'ultima versione"
else
  # Prima installazione
  claude plugin marketplace add "${GITHUB_REPO}"
  enable_autoupdate
  claude plugin install "${PLUGIN_KEY}" --scope user
  info "Plugin 'siae-devforge' installato da GitHub"
fi

echo ""
echo "| 🟢 SICURO — 🔨 DevForge · Installazione completata |"
echo "|:---|"
echo "| 💡 Riavvia Claude Code per attivare il plugin. |"
echo ""
echo "  Per aggiornare in futuro, riesegui:"
echo "    bash <(gh api repos/${GITHUB_REPO}/contents/install.sh -q .content | base64 -d)"
echo "  oppure clona il repo ed esegui: ./install.sh"
echo ""
