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

# github DIRECT su rete SIAE: la CLI risolve lo shorthand github in SSH (bloccato)
# e gh/clone HTTPS instradano sul proxy corporate (irraggiungibile off-VPN).
# Idempotente. NO_PROXY append-safe (stessa forma di lib/net-timeout.sh; duplicato
# perché l'installer è self-contained, gira prima che il repo sia sul disco).
setup_github_network() {
  local gh_domains="github.com,api.github.com,.github.com,codeload.github.com,objects.githubusercontent.com,uploads.github.com"
  case ",${NO_PROXY:-}," in *,github.com,*) : ;; *) export NO_PROXY="${NO_PROXY:+${NO_PROXY},}${gh_domains}" ;; esac
  case ",${no_proxy:-}," in *,github.com,*) : ;; *) export no_proxy="${no_proxy:+${no_proxy},}${gh_domains}" ;; esac
  git config --global url."https://github.com/".insteadOf "git@github.com:"
  git config --global http."https://github.com/".proxy ""
  info "Rete github configurata (HTTPS direct) — git config globale aggiornata"
}

echo ""
echo -e "${GREEN}🔨 DevForge · Installazione plugin${NC}"
echo "  ──────────────────────────────────"
echo ""

# Verifica prerequisiti
command -v claude &>/dev/null || error "Claude Code non trovato. Installalo prima: https://docs.anthropic.com/en/docs/build-with-claude/claude-code"
command -v gh &>/dev/null    || error "GitHub CLI (gh) non trovato. Installalo: https://cli.github.com"

# github DIRECT prima di ogni chiamata gh/git su rete SIAE
setup_github_network

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

# Aggiunge permission MCP a ~/.claude/settings.json (idempotente)
# Fallback chain: python3 → jq → warning manuale
add_mcp_permissions() {
  local settings="${HOME}/.claude/settings.json"
  # Nota: Claude converte kebab-case → snake_case per le permission key
  # es. "siae-sport-oracle" → "mcp__siae_sport_oracle__*"
  local perms=("mcp__elasticsearch__*" "mcp__siae_sport_oracle__*")

  if [ ! -f "$settings" ]; then
    warning "settings.json non trovato: aggiungi manualmente mcp__siae_sport_oracle__* in ~/.claude/settings.json > permissions > allow"
    return 0
  fi

  if command -v python3 &>/dev/null; then
    python3 - "$settings" "${perms[@]}" <<'PY'
import json, sys, os
path = sys.argv[1]
perms = sys.argv[2:]
try:
    with open(path) as f:
        data = json.load(f)
except (json.JSONDecodeError, OSError) as e:
    print(f"Warning: impossibile leggere {path}: {e}", file=sys.stderr)
    sys.exit(1)
allow = data.setdefault("permissions", {}).setdefault("allow", [])
added = [p for p in perms if p not in allow]
if added:
    allow.extend(added)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)
PY
    info "Permission MCP configurate in settings.json (python3)"
  elif command -v jq &>/dev/null; then
    local tmp filter perm
    tmp=$(mktemp)
    # Costruisce il filtro jq: inizializza permissions.allow se assente,
    # aggiunge ogni permission solo se non già presente (idempotente)
    filter='. | .permissions //= {} | .permissions.allow //= []'
    for perm in "${perms[@]}"; do
      filter+=" | if (.permissions.allow | index(\"${perm}\")) == null then .permissions.allow += [\"${perm}\"] else . end"
    done
    if jq "$filter" "$settings" > "$tmp" 2>/dev/null; then
      mv "$tmp" "$settings"
      info "Permission MCP configurate in settings.json (jq)"
    else
      rm -f "$tmp"
      warning "jq: errore durante la modifica di settings.json — aggiungi manualmente mcp__siae_sport_oracle__* in permissions > allow"
    fi
  elif command -v node &>/dev/null; then
    # node come terzo fallback: disponibile sulla maggior parte delle macchine con npm
    node - "$settings" "${perms[@]}" <<'JS'
const fs = require('fs');
const [,, path, ...perms] = process.argv;
try {
  const data = JSON.parse(fs.readFileSync(path, 'utf8'));
  const allow = (data.permissions = data.permissions || {}).allow = data.permissions.allow || [];
  const added = perms.filter(p => !allow.includes(p));
  if (added.length) {
    allow.push(...added);
    const tmp = path + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(data, null, 2));
    fs.renameSync(tmp, path);
  }
} catch (e) {
  process.stderr.write('Warning: ' + e.message + '\n');
  process.exit(1);
}
JS
    info "Permission MCP configurate in settings.json (node)"
  else
    warning "python3, jq e node non disponibili: aggiungi manualmente mcp__siae_sport_oracle__* in ~/.claude/settings.json > permissions > allow"
  fi
}

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

add_mcp_permissions

echo ""
echo -e "${GREEN}🔨 DevForge · Installazione completata${NC}"
echo "  ──────────────────────────────────────"
echo -e "  ${GREEN}💡${NC} Riavvia Claude Code per attivare il plugin."
echo ""
echo "  Per aggiornare in futuro, riesegui:"
echo "    bash <(gh api repos/${GITHUB_REPO}/contents/install.sh -q .content | base64 -d)"
echo "  oppure clona il repo ed esegui: ./install.sh"
echo ""
