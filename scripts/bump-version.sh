#!/usr/bin/env bash
# bump-version.sh — Bumpa la versione in plugin.json e marketplace.json
#
# Uso: bash scripts/bump-version.sh [major|minor|patch]
#
# Il bump aggiorna plugin.json e marketplace.json in sincronia.
# Dopo il bump, committa le modifiche e apri una PR verso main.
# La GitHub Action auto-release creerà la release al merge.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PLUGIN_JSON="$REPO_ROOT/.claude-plugin/plugin.json"
MARKETPLACE_JSON="$REPO_ROOT/.claude-plugin/marketplace.json"

# --- Validazione input ---
BUMP_TYPE="${1:-}"
if [[ "$BUMP_TYPE" != "major" && "$BUMP_TYPE" != "minor" && "$BUMP_TYPE" != "patch" ]]; then
  echo "Uso: bash scripts/bump-version.sh [major|minor|patch]"
  exit 1
fi

# --- Leggi versione corrente da plugin.json ---
CURRENT=$(python3 -c "import json; print(json.load(open('$PLUGIN_JSON'))['version'])")
echo "Versione corrente: $CURRENT"

# Estrai major.minor.patch e suffix opzionale (es. "-mvp")
SEMVER=$(echo "$CURRENT" | grep -oE '^[0-9]+\.[0-9]+\.[0-9]+')
SUFFIX=$(echo "$CURRENT" | sed "s/^$SEMVER//")

MAJOR=$(echo "$SEMVER" | cut -d. -f1)
MINOR=$(echo "$SEMVER" | cut -d. -f2)
PATCH=$(echo "$SEMVER" | cut -d. -f3)

# --- Calcola nuova versione ---
case "$BUMP_TYPE" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH$SUFFIX"
echo "Nuova versione:    $NEW_VERSION"

# --- Aggiorna plugin.json ---
python3 -c "
import json
with open('$PLUGIN_JSON', 'r') as f:
    d = json.load(f)
d['version'] = '$NEW_VERSION'
with open('$PLUGIN_JSON', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.write('\n')
"
echo "Aggiornato: $PLUGIN_JSON"

# --- Aggiorna marketplace.json ---
python3 -c "
import json
with open('$MARKETPLACE_JSON', 'r') as f:
    d = json.load(f)
for plugin in d.get('plugins', []):
    if plugin.get('name') == 'siae-devforge':
        plugin['version'] = '$NEW_VERSION'
with open('$MARKETPLACE_JSON', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.write('\n')
"
echo "Aggiornato: $MARKETPLACE_JSON"

echo ""
echo "Prossimi passi:"
echo "  git add .claude-plugin/plugin.json .claude-plugin/marketplace.json"
echo "  git commit -m \"chore(release): bump version to $NEW_VERSION\""
echo "  # apri PR verso main → al merge la GitHub Action crea la release"
