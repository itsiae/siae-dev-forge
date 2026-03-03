#!/usr/bin/env bash
# install.sh — Installa siae-devforge come plugin locale di Claude Code
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKETPLACE_DIR="${HOME}/.claude/local-plugins"
MANIFEST_FILE="${MARKETPLACE_DIR}/.claude-plugin/marketplace.json"
SYMLINK="${MARKETPLACE_DIR}/plugins/siae-devforge"

# Colori
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}✓${NC} $1"; }
warning() { echo -e "${YELLOW}!${NC} $1"; }
error()   { echo -e "${RED}✗${NC} $1"; exit 1; }

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║       siae-devforge — Installazione plugin           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Verifica prerequisiti
command -v claude &>/dev/null || error "Claude Code non trovato. Installalo prima: https://docs.anthropic.com/en/docs/build-with-claude/claude-code"

# Crea struttura marketplace
mkdir -p "${MARKETPLACE_DIR}/.claude-plugin"
mkdir -p "${MARKETPLACE_DIR}/plugins"
info "Directory marketplace creata: ${MARKETPLACE_DIR}"

# Crea/aggiorna symlink
if [ -L "${SYMLINK}" ]; then
  warning "Symlink già esistente, aggiorno: ${SYMLINK}"
  rm "${SYMLINK}"
fi
ln -sf "${PLUGIN_DIR}" "${SYMLINK}"
info "Symlink creato: ${SYMLINK} → ${PLUGIN_DIR}"

# Crea manifest marketplace
cat > "${MANIFEST_FILE}" <<EOF
{
  "\$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "siae-local",
  "description": "SIAE private plugins marketplace",
  "owner": {
    "name": "SIAE AI Competence Center",
    "email": "ai-cc@siae.it"
  },
  "plugins": [
    {
      "name": "siae-devforge",
      "description": "SIAE Development Forge - AI SDLC Chain per sviluppo software conforme a standard SIAE. 13 skill, 5 comandi, 3 agent, 2 hook.",
      "version": "1.0.0-mvp",
      "author": {
        "name": "SIAE AI Competence Center",
        "email": "ai-cc@siae.it"
      },
      "source": "./plugins/siae-devforge",
      "category": "development",
      "homepage": "https://github.com/itsiae/siae-devforge"
    }
  ]
}
EOF
info "Manifest marketplace scritto: ${MANIFEST_FILE}"

# Registra marketplace (idempotente)
if claude plugin marketplace list 2>/dev/null | grep -q "siae-local"; then
  warning "Marketplace 'siae-local' già registrato, aggiorno"
  claude plugin marketplace update siae-local 2>/dev/null || true
else
  claude plugin marketplace add "${MARKETPLACE_DIR}" --scope user
  info "Marketplace 'siae-local' registrato"
fi

# Installa/aggiorna plugin
if claude plugin list 2>/dev/null | grep -q "siae-devforge"; then
  warning "Plugin già installato, aggiorno"
  claude plugin update siae-devforge 2>/dev/null || true
else
  claude plugin install siae-devforge@siae-local
  info "Plugin 'siae-devforge' installato"
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Installazione completata. Riavvia Claude Code.      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Per aggiornare in futuro:"
echo "    git pull && claude plugin update siae-devforge"
echo ""
