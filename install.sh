#!/usr/bin/env bash
# install.sh — Installa siae-devforge come plugin di Claude Code dal repo GitHub
set -euo pipefail

GITHUB_REPO="itsiae/siae-dev-forge"

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

# Installa/aggiorna plugin da GitHub
if claude plugin list 2>/dev/null | grep -q "siae-devforge"; then
  warning "Plugin già installato, aggiorno"
  claude plugin update siae-devforge 2>&1 && info "Plugin aggiornato" || warning "Aggiornamento non necessario"
else
  claude plugin marketplace add "${GITHUB_REPO}"
  claude plugin install siae-devforge --scope user
  info "Plugin 'siae-devforge' installato da GitHub"
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Installazione completata. Riavvia Claude Code.      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Per aggiornare in futuro:"
echo "    claude plugin update siae-devforge"
echo ""
