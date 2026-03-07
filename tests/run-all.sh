#!/usr/bin/env bash
# run-all.sh — Runner principale per tutti i test siae-devforge
#
# Uso: ./tests/run-all.sh
#
# Esegue tutte le suite di test disponibili e produce un report aggregato.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  🔨 DevForge — TEST RUNNER                                      ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  Plugin:  siae-devforge                                          ║"
echo "║  Root:    ${PLUGIN_ROOT}                                         "
echo "║  Data:    $(date +%Y-%m-%d)                                      "
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0

# --- Skill Triggering Tests ---
if [ -x "${SCRIPT_DIR}/skill-triggering/run-all.sh" ]; then
  echo "=== Skill Triggering Tests ==="
  echo ""

  if "${SCRIPT_DIR}/skill-triggering/run-all.sh"; then
    echo ""
    echo "Skill triggering suite completed."
  else
    echo ""
    echo "Skill triggering suite completed with failures."
  fi

  echo ""
else
  echo "SKIP: skill-triggering/run-all.sh non trovato o non eseguibile"
  TOTAL_SKIP=$((TOTAL_SKIP + 1))
fi

# --- Structure Validation ---
echo "=== Structure Validation ==="
echo ""

# Verify all skills have SKILL.md with frontmatter
skill_count=0
skill_ok=0
skill_fail=0

for skill_dir in "${PLUGIN_ROOT}"/skills/*/; do
  skill_name=$(basename "$skill_dir")
  skill_file="${skill_dir}SKILL.md"
  skill_count=$((skill_count + 1))

  if [ ! -f "$skill_file" ]; then
    echo "  FAIL  ${skill_name}: SKILL.md mancante"
    skill_fail=$((skill_fail + 1))
    continue
  fi

  # Check frontmatter
  if head -1 "$skill_file" | grep -q '^---'; then
    if grep -q '^name:' "$skill_file" && grep -q '^description:' "$skill_file"; then
      echo "  PASS  ${skill_name}: SKILL.md con frontmatter valido"
      skill_ok=$((skill_ok + 1))
    else
      echo "  FAIL  ${skill_name}: frontmatter incompleto (manca name o description)"
      skill_fail=$((skill_fail + 1))
    fi
  else
    echo "  FAIL  ${skill_name}: frontmatter YAML mancante (--- non trovato)"
    skill_fail=$((skill_fail + 1))
  fi
done

echo ""
echo "  Skill totali: ${skill_count} | OK: ${skill_ok} | FAIL: ${skill_fail}"
TOTAL_PASS=$((TOTAL_PASS + skill_ok))
TOTAL_FAIL=$((TOTAL_FAIL + skill_fail))

# --- Dynamic Catalog Validation ---
echo ""
echo "=== Dynamic Catalog Validation ==="
echo ""

if command -v node >/dev/null 2>&1; then
  catalog_output=$(node "${PLUGIN_ROOT}/lib/skills-core.js" "${PLUGIN_ROOT}" 2>&1)
  catalog_lines=$(echo "$catalog_output" | wc -l | tr -d ' ')
  # Subtract 2 for header rows
  catalog_skills=$((catalog_lines - 2))

  # The catalog excludes using-devforge (meta-skill), so expected = skill_ok - 1
  expected_catalog=$((skill_ok - 1))
  if [ "$catalog_skills" -ge "$expected_catalog" ]; then
    echo "  PASS  Catalogo dinamico: ${catalog_skills} skill rilevate (attese >= ${expected_catalog}, meta-skill esclusa)"
    TOTAL_PASS=$((TOTAL_PASS + 1))
  else
    echo "  FAIL  Catalogo dinamico: ${catalog_skills} skill rilevate (attese >= ${expected_catalog})"
    TOTAL_FAIL=$((TOTAL_FAIL + 1))
  fi
else
  echo "  SKIP  node non disponibile, catalogo dinamico non testabile"
  TOTAL_SKIP=$((TOTAL_SKIP + 1))
fi

# --- Commands Validation ---
echo ""
echo "=== Commands Validation ==="
echo ""

cmd_count=0
cmd_ok=0

for cmd_file in "${PLUGIN_ROOT}"/commands/*.md; do
  cmd_name=$(basename "$cmd_file" .md)
  cmd_count=$((cmd_count + 1))

  if head -1 "$cmd_file" | grep -q '^---'; then
    echo "  PASS  /${cmd_name}: frontmatter presente"
    cmd_ok=$((cmd_ok + 1))
  else
    echo "  FAIL  /${cmd_name}: frontmatter mancante"
    TOTAL_FAIL=$((TOTAL_FAIL + 1))
  fi
done

echo ""
echo "  Comandi totali: ${cmd_count} | OK: ${cmd_ok}"
TOTAL_PASS=$((TOTAL_PASS + cmd_ok))

# --- Visual Design System Validation ---
echo ""
echo "=== Visual Design System Validation ==="
echo ""

vds_ok=0
vds_fail=0

# using-devforge is the meta-skill/OS of the plugin — excluded from VDS checks
# (it uses a different structure: Red Flags table instead of Anti-Razi, no Tipo)
EXCLUDED_FROM_VDS="using-devforge"

for skill_dir in "${PLUGIN_ROOT}"/skills/*/; do
  skill_name=$(basename "$skill_dir")
  skill_file="${skill_dir}SKILL.md"

  [ ! -f "$skill_file" ] && continue

  if echo "$EXCLUDED_FROM_VDS" | grep -q "$skill_name"; then
    echo "  SKIP  ${skill_name}: meta-skill, VDS check escluso"
    continue
  fi

  fail_reasons=""

  # Check 1: Skill Rigid → LA LEGGE DI FERRO obbligatoria
  if grep -qE '\*\*Tipo:\*\*\s+Rigid' "$skill_file"; then
    if ! grep -q 'LA LEGGE DI FERRO' "$skill_file"; then
      fail_reasons="${fail_reasons}[MANCA: LA LEGGE DI FERRO] "
    fi
  fi

  # Check 2: Tutte le skill → Tabella Anti-Razionalizzazione
  if ! grep -q 'Tabella Anti-Razionalizzazione' "$skill_file"; then
    fail_reasons="${fail_reasons}[MANCA: Tabella Anti-Razionalizzazione] "
  fi

  # Check 3: Tutte le skill → Classificazione Rischio Operazioni
  if ! grep -q 'Classificazione Rischio' "$skill_file"; then
    fail_reasons="${fail_reasons}[MANCA: Classificazione Rischio Operazioni] "
  fi

  # Check 4: Se Card=Si nel Risk Table → almeno un generate-card.py presente
  if grep -qE '\|\s*Si\s*\|' "$skill_file"; then
    if ! grep -q 'generate-card.py' "$skill_file"; then
      fail_reasons="${fail_reasons}[MANCA: generate-card.py (Risk Table ha Card=Si)] "
    fi
  fi

  if [ -z "$fail_reasons" ]; then
    echo "  PASS  ${skill_name}: VDS completo"
    vds_ok=$((vds_ok + 1))
  else
    echo "  FAIL  ${skill_name}: ${fail_reasons}"
    vds_fail=$((vds_fail + 1))
  fi
done

echo ""
echo "  Skill VDS totali: $((vds_ok + vds_fail)) | OK: ${vds_ok} | FAIL: ${vds_fail}"
TOTAL_PASS=$((TOTAL_PASS + vds_ok))
TOTAL_FAIL=$((TOTAL_FAIL + vds_fail))

# --- Report Finale ---
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  REPORT FINALE                                                   ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  PASS: ${TOTAL_PASS}                                            "
echo "║  FAIL: ${TOTAL_FAIL}                                            "
echo "║  SKIP: ${TOTAL_SKIP}                                            "
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

if [ "$TOTAL_FAIL" -gt 0 ]; then
  exit 1
fi

exit 0
