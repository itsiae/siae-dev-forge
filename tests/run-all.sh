#!/usr/bin/env bash
# run-all.sh — Runner principale per tutti i test siae-devforge
#
# Uso: ./tests/run-all.sh
#
# Esegue tutte le suite di test disponibili e produce un report aggregato.

set -euo pipefail

# Parse arguments
WITH_TRIGGER_REGRESSION=false
for arg in "$@"; do
  case "$arg" in
    --with-trigger-regression) WITH_TRIGGER_REGRESSION=true ;;
  esac
done

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

# --- Subagent Prompt Content Validation ---
echo ""
echo "=== Subagent Prompt Content Validation ==="
echo ""

IMPL_PROMPT="${PLUGIN_ROOT}/skills/siae-subagent-development/implementer-prompt.md"
prompt_ok=0
prompt_fail=0

if [ -f "$IMPL_PROMPT" ]; then
  # Check TDD read instruction
  if grep -q 'Glob(".*siae-tdd/SKILL.md")' "$IMPL_PROMPT"; then
    echo "  PASS  implementer-prompt: contiene istruzione Glob per siae-tdd"
    prompt_ok=$((prompt_ok + 1))
  else
    echo "  FAIL  implementer-prompt: manca istruzione Glob per siae-tdd/SKILL.md"
    prompt_fail=$((prompt_fail + 1))
  fi

  # Check telemetry event
  if grep -q 'devforge_log "tdd_cycle"' "$IMPL_PROMPT"; then
    echo "  PASS  implementer-prompt: contiene telemetria tdd_cycle"
    prompt_ok=$((prompt_ok + 1))
  else
    echo "  FAIL  implementer-prompt: manca telemetria tdd_cycle"
    prompt_fail=$((prompt_fail + 1))
  fi

  # Check TDD cycles in report
  if grep -q 'TDD cycles:' "$IMPL_PROMPT"; then
    echo "  PASS  implementer-prompt: report contiene campo TDD cycles"
    prompt_ok=$((prompt_ok + 1))
  else
    echo "  FAIL  implementer-prompt: report manca campo TDD cycles"
    prompt_fail=$((prompt_fail + 1))
  fi

  # Check bash snippet syntax
  bash_snippet=$(sed -n '/^```bash$/,/^```$/p' "$IMPL_PROMPT" | grep -v '```')
  if echo "$bash_snippet" | bash -n 2>/dev/null; then
    echo "  PASS  implementer-prompt: snippet bash sintatticamente valido"
    prompt_ok=$((prompt_ok + 1))
  else
    echo "  FAIL  implementer-prompt: snippet bash ha errori di sintassi"
    prompt_fail=$((prompt_fail + 1))
  fi
else
  echo "  FAIL  implementer-prompt.md non trovato"
  prompt_fail=$((prompt_fail + 1))
fi

echo ""
echo "  Prompt check: ${prompt_ok} OK | ${prompt_fail} FAIL"
TOTAL_PASS=$((TOTAL_PASS + prompt_ok))
TOTAL_FAIL=$((TOTAL_FAIL + prompt_fail))
echo ""

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

  # Check 4: Se Card=Si nel Risk Table → almeno una pre-flight card presente
  # Supporta sia il formato legacy (generate-card.py) che il nuovo formato inline (tabella markdown)
  if grep -qE '\|\s*Si\s*\|' "$skill_file"; then
    if ! grep -qE 'generate-card\.py|🟡 MEDIO|🔴 ALTO|🚨 CRITICO' "$skill_file"; then
      fail_reasons="${fail_reasons}[MANCA: pre-flight card (Risk Table ha Card=Si)] "
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

# --- Hook Validation ---
echo ""
echo "=== Hook Validation ==="
echo ""

hook_ok=0
hook_fail=0

# Check 1: pr-gate esiste ed è eseguibile
if [ -x "${PLUGIN_ROOT}/hooks/pr-gate" ]; then
  echo "  PASS  hooks/pr-gate: esiste ed è eseguibile"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/pr-gate: mancante o non eseguibile"
  hook_fail=$((hook_fail + 1))
fi

# Check 2: stop-gate esiste ed è eseguibile
if [ -x "${PLUGIN_ROOT}/hooks/stop-gate" ]; then
  echo "  PASS  hooks/stop-gate: esiste ed è eseguibile"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/stop-gate: mancante o non eseguibile"
  hook_fail=$((hook_fail + 1))
fi

# Check 3: hooks.json contiene entry per pr-gate e Stop/stop-gate
if grep -q 'pr-gate' "${PLUGIN_ROOT}/hooks/hooks.json" && grep -q '"Stop"' "${PLUGIN_ROOT}/hooks/hooks.json"; then
  echo "  PASS  hooks/hooks.json: contiene entry pr-gate e Stop"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/hooks.json: entry pr-gate o Stop mancanti"
  hook_fail=$((hook_fail + 1))
fi

# Check 4a: pre-commit gestisce git checkout -b con JIRA ID senza crash
checkout_output=$(echo '{"command":"git checkout -b feature/SPORT-456-test"}' | bash "${PLUGIN_ROOT}/hooks/pre-commit" 2>/dev/null; echo "exit:$?")
if echo "$checkout_output" | grep -q 'exit:0'; then
  echo "  PASS  hooks/pre-commit: gestisce git checkout -b con JIRA ID (exit 0)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/pre-commit: crash su git checkout -b con JIRA ID"
  hook_fail=$((hook_fail + 1))
fi

# Check 4b: pre-commit gestisce git checkout -b senza JIRA ID silenziosamente
nojira_output=$(echo '{"command":"git checkout -b fix/no-jira-id"}' | bash "${PLUGIN_ROOT}/hooks/pre-commit" 2>/dev/null; echo "exit:$?")
if echo "$nojira_output" | grep -q 'exit:0'; then
  echo "  PASS  hooks/pre-commit: gestisce git checkout -b senza JIRA ID (exit 0, silenzioso)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/pre-commit: crash su git checkout -b senza JIRA ID"
  hook_fail=$((hook_fail + 1))
fi

echo ""
echo "  Hook totali: $((hook_ok + hook_fail)) | OK: ${hook_ok} | FAIL: ${hook_fail}"
TOTAL_PASS=$((TOTAL_PASS + hook_ok))
TOTAL_FAIL=$((TOTAL_FAIL + hook_fail))

# --- Trigger Regression Tests (opzionale, richiede claude CLI + token) ---
if [ "$WITH_TRIGGER_REGRESSION" = true ]; then
  echo ""
  echo "=== Trigger Regression Tests ==="
  echo ""

  if [ -x "${SCRIPT_DIR}/run-trigger-regression.sh" ]; then
    "${SCRIPT_DIR}/run-trigger-regression.sh" || true
  else
    echo "  SKIP  run-trigger-regression.sh non trovato o non eseguibile"
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
  fi
fi

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
