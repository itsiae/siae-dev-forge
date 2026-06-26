#!/usr/bin/env bash
# run-all.sh — Runner principale per tutti i test siae-devforge
#
# Uso: ./tests/run-all.sh
#
# Esegue tutte le suite di test disponibili e produce un report aggregato.

set -euo pipefail

# Parse arguments
WITH_TRIGGER_REGRESSION=false
WITH_EVALS=""
for arg in "$@"; do
  case "$arg" in
    --with-trigger-regression) WITH_TRIGGER_REGRESSION=true ;;
    --with-evals) WITH_EVALS="L1" ;;
    --with-evals=*) WITH_EVALS="${arg#--with-evals=}" ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo ""
echo "| 🟢 SICURO — 🔨 DevForge · TEST RUNNER |"
echo "|:---|"
echo "| 🔌 Plugin: \`siae-devforge\` |"
echo "| 📂 Root: \`${PLUGIN_ROOT}\` |"
echo "| 📅 Data: \`$(date +%Y-%m-%d)\` |"
echo ""

TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0

# --- Skill Triggering Tests (SKIPPED by default — richiedono LLM) ---
# Per eseguirli: bash tests/skill-triggering/run-all.sh
echo "SKIP: Skill Triggering Tests (richiedono LLM, usa --with-trigger-regression per includerli)"
TOTAL_SKIP=$((TOTAL_SKIP + 1))

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

# --- Meta-Skill Backbone Validation ---
echo ""
echo "=== Meta-Skill Backbone Validation ==="
echo ""

if command -v node >/dev/null 2>&1; then
  if node "${PLUGIN_ROOT}/tests/using-devforge-backbone.test.js" >/dev/null 2>&1; then
    echo "  PASS  using-devforge: backbone corta e senza duplicazioni"
    TOTAL_PASS=$((TOTAL_PASS + 1))
  else
    echo "  FAIL  using-devforge: backbone regressa o troppo lunga"
    TOTAL_FAIL=$((TOTAL_FAIL + 1))
  fi
else
  echo "  SKIP  node non disponibile, meta-skill backbone non testabile"
  TOTAL_SKIP=$((TOTAL_SKIP + 1))
fi

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
  echo "[WARN] Skipping dynamic catalog test — node non disponibile" >&2
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

# --- Plugin.json Consistency Validation ---
echo ""
echo "=== Plugin.json Consistency Validation ==="
echo ""

consist_ok=0
consist_fail=0

PLUGIN_JSON="${PLUGIN_ROOT}/.claude-plugin/plugin.json"
PLUGIN_DESC=$(grep -o '"description"[[:space:]]*:[[:space:]]*"[^"]*"' "$PLUGIN_JSON" | sed 's/.*"description"[[:space:]]*:[[:space:]]*"//;s/"$//')
PLUGIN_VER=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$PLUGIN_JSON" | sed 's/.*"version"[[:space:]]*:[[:space:]]*"//;s/"$//')

# Count actual skills (directories with SKILL.md)
ACTUAL_SKILLS=$(find "${PLUGIN_ROOT}/skills" -name "SKILL.md" -maxdepth 2 | wc -l | tr -d ' ')
# Count actual commands (.md files in commands/)
ACTUAL_COMMANDS=$(find "${PLUGIN_ROOT}/commands" -name "*.md" -maxdepth 1 | wc -l | tr -d ' ')
# Count actual agents (.md files in agents/)
ACTUAL_AGENTS=$(find "${PLUGIN_ROOT}/agents" -name "*.md" -maxdepth 1 | wc -l | tr -d ' ')
# Count actual hook events in hooks.json
ACTUAL_HOOKS=$(grep -oE '"(SessionStart|UserPromptSubmit|PreToolUse|PostToolUse|Stop)"' "${PLUGIN_ROOT}/hooks/hooks.json" | sort -u | wc -l | tr -d ' ')

# Extract declared counts from description
DECLARED_SKILLS=$(echo "$PLUGIN_DESC" | grep -oE '[0-9]+ skill' | grep -oE '[0-9]+')
DECLARED_COMMANDS=$(echo "$PLUGIN_DESC" | grep -oE '[0-9]+ comandi' | grep -oE '[0-9]+')
DECLARED_AGENTS=$(echo "$PLUGIN_DESC" | grep -oE '[0-9]+ agent' | grep -oE '[0-9]+')
DECLARED_HOOKS=$(echo "$PLUGIN_DESC" | grep -oE '[0-9]+ hook' | grep -oE '[0-9]+')

# Check skills count
if [ "$ACTUAL_SKILLS" = "$DECLARED_SKILLS" ]; then
  echo "  PASS  skill count: ${ACTUAL_SKILLS} actual == ${DECLARED_SKILLS} declared"
  consist_ok=$((consist_ok + 1))
else
  echo "  FAIL  skill count: ${ACTUAL_SKILLS} actual != ${DECLARED_SKILLS} declared in plugin.json"
  consist_fail=$((consist_fail + 1))
fi

# Check commands count
if [ "$ACTUAL_COMMANDS" = "$DECLARED_COMMANDS" ]; then
  echo "  PASS  commands count: ${ACTUAL_COMMANDS} actual == ${DECLARED_COMMANDS} declared"
  consist_ok=$((consist_ok + 1))
else
  echo "  FAIL  commands count: ${ACTUAL_COMMANDS} actual != ${DECLARED_COMMANDS} declared in plugin.json"
  consist_fail=$((consist_fail + 1))
fi

# Check agents count
if [ "$ACTUAL_AGENTS" = "$DECLARED_AGENTS" ]; then
  echo "  PASS  agents count: ${ACTUAL_AGENTS} actual == ${DECLARED_AGENTS} declared"
  consist_ok=$((consist_ok + 1))
else
  echo "  FAIL  agents count: ${ACTUAL_AGENTS} actual != ${DECLARED_AGENTS} declared in plugin.json"
  consist_fail=$((consist_fail + 1))
fi

# Check hooks count
if [ "$ACTUAL_HOOKS" = "$DECLARED_HOOKS" ]; then
  echo "  PASS  hooks count: ${ACTUAL_HOOKS} actual == ${DECLARED_HOOKS} declared"
  consist_ok=$((consist_ok + 1))
else
  echo "  FAIL  hooks count: ${ACTUAL_HOOKS} actual != ${DECLARED_HOOKS} declared in plugin.json"
  consist_fail=$((consist_fail + 1))
fi

# Check version format (semver-like with -mvp suffix)
if echo "$PLUGIN_VER" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$'; then
  echo "  PASS  version format: '${PLUGIN_VER}' is valid semver"
  consist_ok=$((consist_ok + 1))
else
  echo "  FAIL  version format: '${PLUGIN_VER}' is not valid semver"
  consist_fail=$((consist_fail + 1))
fi

echo ""
echo "  Consistency: ${consist_ok} OK | ${consist_fail} FAIL"
TOTAL_PASS=$((TOTAL_PASS + consist_ok))
TOTAL_FAIL=$((TOTAL_FAIL + consist_fail))

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
    if ! grep -qi 'LA LEGGE DI FERRO' "$skill_file"; then
      fail_reasons="${fail_reasons}[MANCA: LA LEGGE DI FERRO] "
    fi
  fi

  # Check 2: Tutte le skill → Tabella Anti-Razionalizzazione inline OR
  # riferimento alla centralizzazione in lib/*.md (post PR #1 anti-dilution).
  # La Tabella Anti-Razionalizzazione è stata centralizzata nelle skill backbone
  # compresse; le skill specialistiche possono mantenerla inline o referenziarla.
  if ! grep -qi 'Tabella Anti-Razionalizzazione\|lib/risk-taxonomy\.md\|lib/permission-denied-handling\.md' "$skill_file"; then
    fail_reasons="${fail_reasons}[MANCA: Tabella Anti-Razionalizzazione o ref lib/*.md] "
  fi

  # Check 3: Classificazione Rischio inline OR riferimento a lib/risk-taxonomy.md
  if ! grep -qi 'Classificazione Rischio\|lib/risk-taxonomy\.md' "$skill_file"; then
    fail_reasons="${fail_reasons}[MANCA: Classificazione Rischio Operazioni o ref lib/risk-taxonomy.md] "
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

# Check 5: post-skill emette skill_completed per skill precedente
SKILL_TS_FILE="${HOME}/.claude/.devforge-skill-start"
echo '1710000000000000000|test-skill-prev|2. Design' > "$SKILL_TS_FILE"
TEST_LOG="/tmp/devforge-test-skill-completed.jsonl"
DEVFORGE_LOG_FILE_BAK="${DEVFORGE_LOG_FILE:-}"
export DEVFORGE_LOG_FILE="$TEST_LOG"
rm -f "$TEST_LOG"
skill_completed_output=$(echo '{"skill":"siae-devforge:siae-brainstorming"}' | bash "${PLUGIN_ROOT}/hooks/post-skill" 2>/dev/null; echo "exit:$?")
if echo "$skill_completed_output" | grep -q 'exit:0' && grep -q '"event":"skill_completed"' "$TEST_LOG" 2>/dev/null; then
  echo "  PASS  hooks/post-skill: emette skill_completed per skill precedente"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/post-skill: non emette skill_completed"
  hook_fail=$((hook_fail + 1))
fi
rm -f "$TEST_LOG" "$SKILL_TS_FILE"
[ -n "$DEVFORGE_LOG_FILE_BAK" ] && export DEVFORGE_LOG_FILE="$DEVFORGE_LOG_FILE_BAK" || unset DEVFORGE_LOG_FILE

# Check 7: tdd-gate BLOCCA per file .java senza siae-tdd (hard gate v1.4.0)
echo "" > "${HOME}/.claude/.devforge-session-skills"
tdd_java_output=$(echo '{"file_path":"src/UserService.java"}' | bash "${PLUGIN_ROOT}/hooks/tdd-gate" 2>/dev/null; echo "exit:$?")
if echo "$tdd_java_output" | grep -q '"decision"' && echo "$tdd_java_output" | grep -q '"block"' && echo "$tdd_java_output" | grep -q 'exit:0'; then
  echo "  PASS  hooks/tdd-gate: BLOCCA per .java senza siae-tdd (hard gate)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/tdd-gate: non blocca per .java"
  hook_fail=$((hook_fail + 1))
fi

# Check 8: tdd-gate silenzioso su file .md
tdd_md_output=$(echo '{"file_path":"docs/README.md"}' | bash "${PLUGIN_ROOT}/hooks/tdd-gate" 2>/dev/null)
if [ "$tdd_md_output" = "{}" ]; then
  echo "  PASS  hooks/tdd-gate: silenzioso su file .md (non produzione)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/tdd-gate: non silenzioso su file .md"
  hook_fail=$((hook_fail + 1))
fi

# Check 9: tdd-gate silenzioso su file test
tdd_test_output=$(echo '{"file_path":"tests/test_service.py"}' | bash "${PLUGIN_ROOT}/hooks/tdd-gate" 2>/dev/null)
if [ "$tdd_test_output" = "{}" ]; then
  echo "  PASS  hooks/tdd-gate: silenzioso su file test (escluso)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/tdd-gate: non silenzioso su file test"
  hook_fail=$((hook_fail + 1))
fi

# Check 10: tdd-gate silenzioso con siae-tdd già invocata
echo "siae-tdd" > "${HOME}/.claude/.devforge-session-skills"
tdd_with_skill=$(echo '{"file_path":"src/UserService.java"}' | bash "${PLUGIN_ROOT}/hooks/tdd-gate" 2>/dev/null)
if [ "$tdd_with_skill" = "{}" ]; then
  echo "  PASS  hooks/tdd-gate: silenzioso con siae-tdd in sessione"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/tdd-gate: non silenzioso con siae-tdd in sessione"
  hook_fail=$((hook_fail + 1))
fi

# Check 11: plan-gate BLOCCA senza siae-brainstorming (hard gate v1.4.0)
echo "" > "${HOME}/.claude/.devforge-session-skills"
plan_output=$(echo '{"tool_name":"EnterPlanMode"}' | bash "${PLUGIN_ROOT}/hooks/plan-gate" 2>/dev/null; echo "exit:$?")
if echo "$plan_output" | grep -q '"decision"' && echo "$plan_output" | grep -q '"block"' && echo "$plan_output" | grep -q 'exit:0'; then
  echo "  PASS  hooks/plan-gate: BLOCCA senza siae-brainstorming (hard gate)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/plan-gate: non blocca senza brainstorming"
  hook_fail=$((hook_fail + 1))
fi

# Check 12: plan-gate silenzioso con siae-brainstorming invocata
echo "siae-brainstorming" > "${HOME}/.claude/.devforge-session-skills"
plan_with_skill=$(echo '{"tool_name":"EnterPlanMode"}' | bash "${PLUGIN_ROOT}/hooks/plan-gate" 2>/dev/null)
if [ "$plan_with_skill" = "{}" ]; then
  echo "  PASS  hooks/plan-gate: silenzioso con siae-brainstorming in sessione"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/plan-gate: non silenzioso con siae-brainstorming"
  hook_fail=$((hook_fail + 1))
fi

# Check 13: pre-commit BLOCCA git commit senza siae-git-workflow (hard gate v1.4.0)
echo "" > "${HOME}/.claude/.devforge-session-skills"
precommit_block_output=$(echo '{"command":"git commit -m test"}' | bash "${PLUGIN_ROOT}/hooks/pre-commit" 2>/dev/null; echo "exit:$?")
if echo "$precommit_block_output" | grep -q '"decision"' && echo "$precommit_block_output" | grep -q '"block"' && echo "$precommit_block_output" | grep -q 'exit:0'; then
  echo "  PASS  hooks/pre-commit: BLOCCA git commit senza siae-git-workflow (hard gate)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/pre-commit: non blocca git commit senza siae-git-workflow"
  hook_fail=$((hook_fail + 1))
fi

# Check 14: pre-commit consente git commit con siae-git-workflow invocata
echo "siae-git-workflow" > "${HOME}/.claude/.devforge-session-skills"
precommit_allow_output=$(echo '{"command":"git commit -m test"}' | bash "${PLUGIN_ROOT}/hooks/pre-commit" 2>/dev/null; echo "exit:$?")
if echo "$precommit_allow_output" | grep -q "additional_context" && echo "$precommit_allow_output" | grep -q 'exit:0'; then
  echo "  PASS  hooks/pre-commit: consente git commit con siae-git-workflow"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/pre-commit: non consente git commit con siae-git-workflow"
  hook_fail=$((hook_fail + 1))
fi

# Check 15: sub-skill-gate BLOCCA skill con prerequisiti mancanti
echo "" > "${HOME}/.claude/.devforge-session-skills"
subskill_block_output=$(echo '{"skill":"siae-devforge:siae-finishing-branch"}' | bash "${PLUGIN_ROOT}/hooks/sub-skill-gate" 2>/dev/null; echo "exit:$?")
if echo "$subskill_block_output" | grep -q '"decision"' && echo "$subskill_block_output" | grep -q '"block"' && echo "$subskill_block_output" | grep -q 'exit:0'; then
  echo "  PASS  hooks/sub-skill-gate: BLOCCA siae-finishing-branch senza prerequisiti"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/sub-skill-gate: non blocca senza prerequisiti"
  hook_fail=$((hook_fail + 1))
fi

# Check 16: sub-skill-gate consente skill con prerequisiti soddisfatti
echo "siae-git-env,siae-git-workflow" > "${HOME}/.claude/.devforge-session-skills"
subskill_allow_output=$(echo '{"skill":"siae-devforge:siae-finishing-branch"}' | bash "${PLUGIN_ROOT}/hooks/sub-skill-gate" 2>/dev/null)
if [ "$subskill_allow_output" = "{}" ]; then
  echo "  PASS  hooks/sub-skill-gate: consente con prerequisiti soddisfatti"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/sub-skill-gate: non consente con prerequisiti soddisfatti"
  hook_fail=$((hook_fail + 1))
fi

# Check 17: sub-skill-gate silenzioso per skill senza prerequisiti
# Use siae-architecture: a flexible skill that has no prerequisite in
# lib/prereq-map.generated (PR #2, Task 4 expanded the map — siae-tdd is
# no longer a prereq-free skill so it can't be used for this assertion).
echo "" > "${HOME}/.claude/.devforge-session-skills"
subskill_noreq_output=$(echo '{"skill":"siae-devforge:siae-architecture"}' | bash "${PLUGIN_ROOT}/hooks/sub-skill-gate" 2>/dev/null)
if [ "$subskill_noreq_output" = "{}" ]; then
  echo "  PASS  hooks/sub-skill-gate: silenzioso per skill senza prerequisiti"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/sub-skill-gate: non silenzioso per skill senza prerequisiti"
  hook_fail=$((hook_fail + 1))
fi

# Check 18: tdd-gate BLOCCA codice produzione in fase INIT (nessun test fallente)
echo "siae-tdd" > "${HOME}/.claude/.devforge-session-skills"
echo "INIT|pending|awaiting-test|$(date +%s)" > "${HOME}/.claude/.devforge-tdd-state"
tdd_init_output=$(echo '{"file_path":"src/MyService.java"}' | bash "${PLUGIN_ROOT}/hooks/tdd-gate" 2>/dev/null; echo "exit:$?")
if echo "$tdd_init_output" | grep -q '"decision"' && echo "$tdd_init_output" | grep -q '"block"' && echo "$tdd_init_output" | grep -q 'test fallente'; then
  echo "  PASS  hooks/tdd-gate: BLOCCA codice produzione in fase INIT (state machine)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/tdd-gate: non blocca codice produzione in fase INIT"
  hook_fail=$((hook_fail + 1))
fi

# Check 18b: tdd-gate CONSENTE codice produzione in fase RED (test fallente confermato)
echo "RED|src/MyService.java|testShouldWork|$(date +%s)" > "${HOME}/.claude/.devforge-tdd-state"
tdd_red_output=$(echo '{"file_path":"src/MyService.java"}' | bash "${PLUGIN_ROOT}/hooks/tdd-gate" 2>/dev/null)
if [ "$tdd_red_output" = "{}" ]; then
  echo "  PASS  hooks/tdd-gate: consente codice produzione in fase RED (test fallente confermato)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/tdd-gate: blocca codice produzione in fase RED (deadlock!)"
  hook_fail=$((hook_fail + 1))
fi

# Check 19: tdd-gate consente codice produzione in fase GREEN
echo "GREEN|src/MyService.java|testShouldWork|$(date +%s)" > "${HOME}/.claude/.devforge-tdd-state"
tdd_green_output=$(echo '{"file_path":"src/MyService.java"}' | bash "${PLUGIN_ROOT}/hooks/tdd-gate" 2>/dev/null)
if [ "$tdd_green_output" = "{}" ]; then
  echo "  PASS  hooks/tdd-gate: consente codice produzione in fase GREEN"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/tdd-gate: non consente codice produzione in fase GREEN"
  hook_fail=$((hook_fail + 1))
fi

# Check 19b: capture-test-result avanza INIT→RED su test FAIL (test fallente confermato)
echo "siae-tdd" > "${HOME}/.claude/.devforge-session-skills"
echo "INIT|pending|awaiting-test|$(date +%s)" > "${HOME}/.claude/.devforge-tdd-state"
echo '{"command":"npm test","exit_code":1,"stdout":"Tests: 1 failed"}' | bash "${PLUGIN_ROOT}/hooks/capture-test-result" 2>/dev/null
TDD_INIT_TO_RED=$(cat "${HOME}/.claude/.devforge-tdd-state" 2>/dev/null | cut -d'|' -f1)
if [ "$TDD_INIT_TO_RED" = "RED" ]; then
  echo "  PASS  hooks/capture-test-result: avanza INIT→RED su test FAIL"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/capture-test-result: non avanza INIT→RED (got: ${TDD_INIT_TO_RED})"
  hook_fail=$((hook_fail + 1))
fi

# Check 20: capture-test-result avanza RED→GREEN su test PASS
echo "siae-tdd" > "${HOME}/.claude/.devforge-session-skills"
echo "RED|src/MyService.java|testShouldWork|$(date +%s)" > "${HOME}/.claude/.devforge-tdd-state"
echo '{"command":"npm test","exit_code":0,"stdout":"Tests: 1 passed"}' | bash "${PLUGIN_ROOT}/hooks/capture-test-result" 2>/dev/null
TDD_AFTER_PASS=$(cat "${HOME}/.claude/.devforge-tdd-state" 2>/dev/null | cut -d'|' -f1)
if [ "$TDD_AFTER_PASS" = "GREEN" ]; then
  echo "  PASS  hooks/capture-test-result: avanza RED→GREEN su test PASS"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/capture-test-result: non avanza RED→GREEN (got: ${TDD_AFTER_PASS})"
  hook_fail=$((hook_fail + 1))
fi

# Check 21: capture-test-result mantiene RED su test FAIL
echo "RED|src/MyService.java|testShouldWork|$(date +%s)" > "${HOME}/.claude/.devforge-tdd-state"
echo '{"command":"npm test","exit_code":1,"stdout":"Tests: 1 failed"}' | bash "${PLUGIN_ROOT}/hooks/capture-test-result" 2>/dev/null
TDD_AFTER_FAIL=$(cat "${HOME}/.claude/.devforge-tdd-state" 2>/dev/null | cut -d'|' -f1)
if [ "$TDD_AFTER_FAIL" = "RED" ]; then
  echo "  PASS  hooks/capture-test-result: mantiene RED su test FAIL (atteso)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/capture-test-result: non mantiene RED su FAIL (got: ${TDD_AFTER_FAIL})"
  hook_fail=$((hook_fail + 1))
fi

# Check 22: session-start resetta TDD state
echo "RED|test|test|0" > "${HOME}/.claude/.devforge-tdd-state"
# Cleanup: remove state
rm -f "${HOME}/.claude/.devforge-tdd-state"

# Check 23: batch-checkpoint silenzioso senza siae-executing-plans
echo "" > "${HOME}/.claude/.devforge-session-skills"
rm -f "${HOME}/.claude/.devforge-batch-checkpoint" "${HOME}/.claude/.devforge-batch-counter"
batch_noskill=$(echo '{"command":"git commit -m docs(plans): mark task 1 as DONE"}' | bash "${PLUGIN_ROOT}/hooks/batch-checkpoint" 2>/dev/null)
if [ "$batch_noskill" = "{}" ]; then
  echo "  PASS  hooks/batch-checkpoint: silenzioso senza siae-executing-plans"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/batch-checkpoint: non silenzioso senza siae-executing-plans"
  hook_fail=$((hook_fail + 1))
fi

# Check 24: batch-checkpoint incrementa contatore con siae-executing-plans
echo "siae-executing-plans" > "${HOME}/.claude/.devforge-session-skills"
echo "0" > "${HOME}/.claude/.devforge-batch-counter"
rm -f "${HOME}/.claude/.devforge-batch-checkpoint"
echo '{"command":"git commit -m docs(plans): mark task 1 as DONE"}' | bash "${PLUGIN_ROOT}/hooks/batch-checkpoint" 2>/dev/null
BATCH_COUNT=$(cat "${HOME}/.claude/.devforge-batch-counter" 2>/dev/null || echo "0")
if [ "$BATCH_COUNT" = "1" ]; then
  echo "  PASS  hooks/batch-checkpoint: incrementa contatore task (0→1)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/batch-checkpoint: contatore non incrementato (got: ${BATCH_COUNT})"
  hook_fail=$((hook_fail + 1))
fi

# Check 25: batch-checkpoint BLOCCA dopo 3 task
echo "2" > "${HOME}/.claude/.devforge-batch-counter"
rm -f "${HOME}/.claude/.devforge-batch-checkpoint"
# This commit is task 3 → triggers checkpoint
echo '{"command":"git commit -m docs(plans): mark task 3 as DONE"}' | bash "${PLUGIN_ROOT}/hooks/batch-checkpoint" 2>/dev/null
# Now checkpoint file should exist
if [ -f "${HOME}/.claude/.devforge-batch-checkpoint" ]; then
  # Next commit should be blocked
  batch_blocked=$(echo '{"command":"git commit -m docs(plans): mark task 4 as DONE"}' | bash "${PLUGIN_ROOT}/hooks/batch-checkpoint" 2>/dev/null)
  if echo "$batch_blocked" | grep -q '"decision"' && echo "$batch_blocked" | grep -q '"block"'; then
    echo "  PASS  hooks/batch-checkpoint: BLOCCA dopo batch di 3 task"
    hook_ok=$((hook_ok + 1))
  else
    echo "  FAIL  hooks/batch-checkpoint: non blocca dopo batch completo"
    hook_fail=$((hook_fail + 1))
  fi
else
  echo "  FAIL  hooks/batch-checkpoint: checkpoint file non creato dopo 3 task"
  hook_fail=$((hook_fail + 1))
fi

# Check 26: batch-reset sblocca dopo feedback utente (bypass age check with old mtime)
# Set checkpoint mtime to 30 seconds ago to bypass the 10-second minimum age
touch -t "$(date -v-30S '+%Y%m%d%H%M.%S' 2>/dev/null || date -d '30 seconds ago' '+%Y%m%d%H%M.%S' 2>/dev/null)" "${HOME}/.claude/.devforge-batch-checkpoint" 2>/dev/null || true
batch_reset_output=$(bash "${PLUGIN_ROOT}/hooks/batch-reset" 2>/dev/null)
if [ ! -f "${HOME}/.claude/.devforge-batch-checkpoint" ]; then
  echo "  PASS  hooks/batch-reset: sblocca checkpoint dopo feedback utente"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/batch-reset: non sblocca checkpoint"
  hook_fail=$((hook_fail + 1))
fi

# Cleanup batch state
rm -f "${HOME}/.claude/.devforge-batch-checkpoint" "${HOME}/.claude/.devforge-batch-counter"

# Check 27: capture-test-result estrae coverage da Jest/Vitest output
echo "siae-tdd" > "${HOME}/.claude/.devforge-session-skills"
rm -f "${HOME}/.claude/.devforge-last-coverage"
echo '{"command":"npx vitest run --coverage","exit_code":0,"stdout":"All files | 85.71 | 100 | 75 | 85.71"}' | bash "${PLUGIN_ROOT}/hooks/capture-test-result" 2>/dev/null
COV_VITEST=$(cat "${HOME}/.claude/.devforge-last-coverage" 2>/dev/null | cut -d'|' -f1)
if [ "$COV_VITEST" = "85.71" ]; then
  echo "  PASS  hooks/capture-test-result: estrae coverage 85.71% da Vitest output"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/capture-test-result: coverage Vitest non estratta (got: ${COV_VITEST})"
  hook_fail=$((hook_fail + 1))
fi

# Check 28: capture-test-result estrae coverage da pytest-cov output
rm -f "${HOME}/.claude/.devforge-last-coverage"
echo '{"command":"pytest --cov","exit_code":0,"stdout":"TOTAL    150     30    80%"}' | bash "${PLUGIN_ROOT}/hooks/capture-test-result" 2>/dev/null
COV_PYTEST=$(cat "${HOME}/.claude/.devforge-last-coverage" 2>/dev/null | cut -d'|' -f1)
if [ "$COV_PYTEST" = "80" ]; then
  echo "  PASS  hooks/capture-test-result: estrae coverage 80% da pytest-cov"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/capture-test-result: coverage pytest non estratta (got: ${COV_PYTEST})"
  hook_fail=$((hook_fail + 1))
fi

# Check 29: capture-test-result estrae coverage da Go test output
rm -f "${HOME}/.claude/.devforge-last-coverage"
echo '{"command":"go test -cover","exit_code":0,"stdout":"coverage: 72.5% of statements"}' | bash "${PLUGIN_ROOT}/hooks/capture-test-result" 2>/dev/null
COV_GO=$(cat "${HOME}/.claude/.devforge-last-coverage" 2>/dev/null | cut -d'|' -f1)
if [ "$COV_GO" = "72.5" ]; then
  echo "  PASS  hooks/capture-test-result: estrae coverage 72.5% da Go test"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/capture-test-result: coverage Go non estratta (got: ${COV_GO})"
  hook_fail=$((hook_fail + 1))
fi

# Check 30: pre-commit BLOCCA se coverage < 70%
echo "siae-git-workflow" > "${HOME}/.claude/.devforge-session-skills"
echo "65|$(date +%s)|npx vitest" > "${HOME}/.claude/.devforge-last-coverage"
cov_block_output=$(echo '{"command":"git commit -m test"}' | bash "${PLUGIN_ROOT}/hooks/pre-commit" 2>/dev/null)
if echo "$cov_block_output" | grep -q '"decision"' && echo "$cov_block_output" | grep -q '"block"' && echo "$cov_block_output" | grep -q '65%'; then
  echo "  PASS  hooks/pre-commit: BLOCCA commit con coverage 65% < 70%"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/pre-commit: non blocca commit con coverage bassa"
  hook_fail=$((hook_fail + 1))
fi

# Check 31: pre-commit consente commit se coverage >= soglia (floor globale 70%)
echo "85|$(date +%s)|npx vitest" > "${HOME}/.claude/.devforge-last-coverage"
cov_allow_output=$(echo '{"command":"git commit -m test"}' | bash "${PLUGIN_ROOT}/hooks/pre-commit" 2>/dev/null)
if echo "$cov_allow_output" | grep -q "additional_context" && ! echo "$cov_allow_output" | grep -q '"block"'; then
  echo "  PASS  hooks/pre-commit: consente commit con coverage 85% >= soglia"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/pre-commit: non consente commit con coverage sufficiente"
  hook_fail=$((hook_fail + 1))
fi

# Check 32: pre-commit consente commit con coverage 75% indipendentemente dal branch name
# (regressione: era bloccato su feature/* con soglia 80% — invariante: threshold=70% per tutti i branch)
echo "75|$(date +%s)|npx vitest" > "${HOME}/.claude/.devforge-last-coverage"
cov_75_output=$(echo '{"command":"git commit -m test"}' | bash "${PLUGIN_ROOT}/hooks/pre-commit" 2>/dev/null)
if echo "$cov_75_output" | grep -q "additional_context" && ! echo "$cov_75_output" | grep -q '"block"'; then
  echo "  PASS  hooks/pre-commit: consente commit con coverage 75% >= 70% (floor globale)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/pre-commit: blocca coverage 75% che supera il floor 70%"
  hook_fail=$((hook_fail + 1))
fi

# Check 33: pre-commit consente commit senza coverage file (graceful)
rm -f "${HOME}/.claude/.devforge-last-coverage"
cov_nocov_output=$(echo '{"command":"git commit -m test"}' | bash "${PLUGIN_ROOT}/hooks/pre-commit" 2>/dev/null)
if echo "$cov_nocov_output" | grep -q "additional_context" && ! echo "$cov_nocov_output" | grep -q '"block"'; then
  echo "  PASS  hooks/pre-commit: consente commit senza coverage data (graceful)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/pre-commit: blocca commit senza coverage data"
  hook_fail=$((hook_fail + 1))
fi

# Cleanup coverage state
rm -f "${HOME}/.claude/.devforge-last-coverage"

# NOTE: tests for hooks/user-prompt-context are ARCHIVED (T12 PR #1 anti-dilution).
# Hook replaced by hooks/devforge-context. Coverage delegated to:
# - tests/hooks/test_devforge_context.sh (behavioral TDD suite)
# - tests/compression-regression/assert_injection_reduction.sh (budget + dedup)

# Check: devforge_set_mode/clear_mode helpers
TEST_DIR=$(mktemp -d)
source "${PLUGIN_ROOT}/lib/logger.sh"
(cd "$TEST_DIR" && devforge_set_mode "test" "hello-world")
if [ -f "${TEST_DIR}/.devforge-active-test" ] && grep -q "hello-world" "${TEST_DIR}/.devforge-active-test"; then
  echo "  PASS  logger.sh: devforge_set_mode crea sentinel file"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  logger.sh: devforge_set_mode non crea sentinel file"
  hook_fail=$((hook_fail + 1))
fi
(cd "$TEST_DIR" && devforge_clear_mode "test")
if [ ! -f "${TEST_DIR}/.devforge-active-test" ]; then
  echo "  PASS  logger.sh: devforge_clear_mode rimuove sentinel file"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  logger.sh: devforge_clear_mode non rimuove sentinel file"
  hook_fail=$((hook_fail + 1))
fi
rm -rf "$TEST_DIR"

# NOTE: further user-prompt-context tests archived with T12 — see note above.

# Check 13: pre-commit tool counter incrementa e reset da session-start
echo "0" > "${HOME}/.claude/.devforge-tool-counter"
echo '{"command":"ls"}' | bash "${PLUGIN_ROOT}/hooks/pre-commit" >/dev/null 2>&1
COUNTER_VAL=$(cat "${HOME}/.claude/.devforge-tool-counter" 2>/dev/null || echo "0")
if [ "$COUNTER_VAL" = "1" ]; then
  echo "  PASS  hooks/pre-commit: tool counter incrementa (0 -> 1)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/pre-commit: tool counter non incrementa (val=$COUNTER_VAL)"
  hook_fail=$((hook_fail + 1))
fi
# Verify session-start resets counter
bash "${PLUGIN_ROOT}/hooks/session-start" >/dev/null 2>&1 || true
COUNTER_AFTER_RESET=$(cat "${HOME}/.claude/.devforge-tool-counter" 2>/dev/null || echo "X")
if [ "$COUNTER_AFTER_RESET" = "0" ]; then
  echo "  PASS  hooks/session-start: resetta tool counter a 0"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/session-start: non resetta tool counter (val=$COUNTER_AFTER_RESET)"
  hook_fail=$((hook_fail + 1))
fi

# Cleanup session state
echo "" > "${HOME}/.claude/.devforge-session-skills"
echo "0" > "${HOME}/.claude/.devforge-tool-counter"

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

# --- Telemetry Functional Tests ---
echo ""
echo "=== Telemetry Functional Tests ==="
echo ""

telfunc_ok=0
telfunc_fail=0

# Test: commit_created event includes correct fields
COMMIT_TEST_LOG="/tmp/devforge-test-commit-created.jsonl"
rm -f "$COMMIT_TEST_LOG"
export DEVFORGE_LOG_FILE="$COMMIT_TEST_LOG"
source "${PLUGIN_ROOT}/lib/logger.sh"
devforge_log "commit_created" "success" '{"files_changed":5,"insertions":30,"deletions":10,"has_tests":true}'
if command -v jq >/dev/null 2>&1; then
  if jq -e '.meta.files_changed == 5 and .meta.has_tests == true' "$COMMIT_TEST_LOG" >/dev/null 2>&1 || \
     grep -q '"files_changed":5' "$COMMIT_TEST_LOG" 2>/dev/null; then
    echo "  PASS  commit_created: emette files_changed, insertions, deletions, has_tests"
    telfunc_ok=$((telfunc_ok + 1))
  else
    echo "  FAIL  commit_created: campi mancanti o errati"
    telfunc_fail=$((telfunc_fail + 1))
  fi
else
  if grep -q '"files_changed":5' "$COMMIT_TEST_LOG" && grep -q '"has_tests":true' "$COMMIT_TEST_LOG"; then
    echo "  PASS  commit_created: emette files_changed e has_tests (no jq, grep check)"
    telfunc_ok=$((telfunc_ok + 1))
  else
    echo "  FAIL  commit_created: campi mancanti"
    telfunc_fail=$((telfunc_fail + 1))
  fi
fi
rm -f "$COMMIT_TEST_LOG"

# Test: session_end counters are consistent
SESSION_END_LOG="/tmp/devforge-test-session-end.jsonl"
rm -f "$SESSION_END_LOG"
export DEVFORGE_LOG_FILE="$SESSION_END_LOG"
source "${PLUGIN_ROOT}/lib/logger.sh"
devforge_log_timed "session_end" "success" "$(_devforge_epoch_ns)" '{"skills_used_count":4,"commits_count":3}'
if grep -q '"skills_used_count":4' "$SESSION_END_LOG" && grep -q '"commits_count":3' "$SESSION_END_LOG"; then
  echo "  PASS  session_end: skills_used_count e commits_count presenti e corretti"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  session_end: contatori mancanti o errati"
  telfunc_fail=$((telfunc_fail + 1))
fi
if grep -q '"duration_ms":' "$SESSION_END_LOG"; then
  echo "  PASS  session_end: duration_ms presente"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  session_end: duration_ms mancante"
  telfunc_fail=$((telfunc_fail + 1))
fi
rm -f "$SESSION_END_LOG"

# Test: pr_opened skipped gracefully when gh is not available
# We simulate by checking post-commit-review handles non-push commands without error
PROPENTEST_LOG="/tmp/devforge-test-propened.jsonl"
rm -f "$PROPENTEST_LOG"
export DEVFORGE_LOG_FILE="$PROPENTEST_LOG"
propened_output=$(echo '{"command":"git status"}' | bash "${PLUGIN_ROOT}/hooks/post-commit-review" 2>/dev/null; echo "exit:$?")
if echo "$propened_output" | grep -q 'exit:0'; then
  echo "  PASS  pr_opened: non-push command handled gracefully (exit 0)"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  pr_opened: crash on non-push command"
  telfunc_fail=$((telfunc_fail + 1))
fi
rm -f "$PROPENTEST_LOG"

# Test: JSON sanitization function works
SANITIZE_LOG="/tmp/devforge-test-sanitize.jsonl"
rm -f "$SANITIZE_LOG"
export DEVFORGE_LOG_FILE="$SANITIZE_LOG"
source "${PLUGIN_ROOT}/lib/logger.sh"
UNSAFE_STRING='test"with"quotes\and\\backslashes'
SAFE=$(devforge_sanitize_json_str "$UNSAFE_STRING")
devforge_log "test_sanitize" "success" "{\"value\":\"${SAFE}\"}"
if command -v jq >/dev/null 2>&1; then
  if jq . "$SANITIZE_LOG" >/dev/null 2>&1; then
    echo "  PASS  JSON sanitization: output valido con caratteri speciali"
    telfunc_ok=$((telfunc_ok + 1))
  else
    echo "  FAIL  JSON sanitization: output JSON non valido"
    telfunc_fail=$((telfunc_fail + 1))
  fi
else
  echo "  SKIP  JSON sanitization: jq non disponibile"
  TOTAL_SKIP=$((TOTAL_SKIP + 1))
fi
rm -f "$SANITIZE_LOG"

unset DEVFORGE_LOG_FILE

# Test: session_end guard — stop-gate emits session_end only once
GUARD_LOG="/tmp/devforge-test-guard.jsonl"
rm -f "$GUARD_LOG"
export DEVFORGE_LOG_FILE="$GUARD_LOG"
# Cleanup any stale guard
rm -rf "${HOME}/.claude/.devforge-session-end-guard"
# Setup session state
echo "$(_devforge_epoch_ns)" > "${HOME}/.claude/.devforge-session-start-ns"
echo "1" > "${HOME}/.claude/.devforge-session-commits"
echo "test-skill" > "${HOME}/.claude/.devforge-session-skills"
# Invoke stop-gate twice — session_end should appear only once
stop_input='{"messages":[{"role":"assistant","content":"tutto fatto"}]}'
echo "$stop_input" | bash "${PLUGIN_ROOT}/hooks/stop-gate" 2>/dev/null || true
echo "$stop_input" | bash "${PLUGIN_ROOT}/hooks/stop-gate" 2>/dev/null || true
SESSION_END_COUNT=$(grep -c '"event":"session_end"' "$GUARD_LOG" 2>/dev/null || echo "0")
if [ "$SESSION_END_COUNT" -eq 1 ]; then
  echo "  PASS  session_end guard: emesso esattamente 1 volta su 2 invocazioni stop-gate"
  telfunc_ok=$((telfunc_ok + 1))
elif [ "$SESSION_END_COUNT" -eq 0 ]; then
  echo "  FAIL  session_end guard: non emesso (atteso 1)"
  telfunc_fail=$((telfunc_fail + 1))
else
  echo "  FAIL  session_end guard: emesso ${SESSION_END_COUNT} volte (atteso 1)"
  telfunc_fail=$((telfunc_fail + 1))
fi
rm -f "$GUARD_LOG" "${HOME}/.claude/.devforge-session-start-ns" "${HOME}/.claude/.devforge-session-commits" "${HOME}/.claude/.devforge-session-skills"
rm -rf "${HOME}/.claude/.devforge-session-end-guard"

# Test: post-skill with empty SKILL_NAME produces no events
EMPTY_SKILL_LOG="/tmp/devforge-test-empty-skill.jsonl"
rm -f "$EMPTY_SKILL_LOG"
export DEVFORGE_LOG_FILE="$EMPTY_SKILL_LOG"
# Setup a previous skill timestamp to verify it does NOT get closed
echo '1710000000000000000|should-not-close|2. Design' > "${HOME}/.claude/.devforge-skill-start"
# Send input without skill field — SKILL_NAME should be empty
empty_output=$(echo '{"not_a_skill":"true"}' | bash "${PLUGIN_ROOT}/hooks/post-skill" 2>/dev/null; echo "exit:$?")
if echo "$empty_output" | grep -q 'exit:0'; then
  if [ ! -s "$EMPTY_SKILL_LOG" ] || ! grep -q 'skill_completed' "$EMPTY_SKILL_LOG" 2>/dev/null; then
    echo "  PASS  post-skill: empty SKILL_NAME produces no events (guard works)"
    telfunc_ok=$((telfunc_ok + 1))
  else
    echo "  FAIL  post-skill: empty SKILL_NAME still emitted skill_completed"
    telfunc_fail=$((telfunc_fail + 1))
  fi
else
  echo "  FAIL  post-skill: crashed with empty SKILL_NAME"
  telfunc_fail=$((telfunc_fail + 1))
fi
rm -f "$EMPTY_SKILL_LOG" "${HOME}/.claude/.devforge-skill-start"

# Test: session-start cleans up stale guard directory
rm -rf "${HOME}/.claude/.devforge-session-end-guard"
mkdir -p "${HOME}/.claude/.devforge-session-end-guard"  # simulate stale guard
bash "${PLUGIN_ROOT}/hooks/session-start" >/dev/null 2>&1 || true
if [ ! -d "${HOME}/.claude/.devforge-session-end-guard" ]; then
  echo "  PASS  session-start: cleans up stale session_end guard"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  session-start: did not clean up stale session_end guard"
  telfunc_fail=$((telfunc_fail + 1))
  rm -rf "${HOME}/.claude/.devforge-session-end-guard"
fi

# Test: session-start injects VERSION_STATUS into additional_context JSON
SESSION_JSON=$(bash "${PLUGIN_ROOT}/hooks/session-start" 2>/dev/null) || true
if echo "$SESSION_JSON" | grep -q "DevForge v"; then
  echo "  PASS  session-start: VERSION_STATUS injected in additional_context"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  session-start: VERSION_STATUS missing from additional_context"
  telfunc_fail=$((telfunc_fail + 1))
fi

# Test Fix1-A: hookSpecificOutput must NOT contain additionalContext (payload deduplication)
# Extract only the JSON block — skip npm/tsc noise emitted by background processes on stdout
SESSION_JSON_FIX1_CLEAN=$(echo "$SESSION_JSON" | awk '/^\{/{f=1} f')
if echo "$SESSION_JSON_FIX1_CLEAN" | python3 -c "import sys,json; d=json.loads(sys.stdin.read(),strict=False); assert 'additionalContext' not in d.get('hookSpecificOutput',{})" 2>/dev/null; then
  echo "  PASS  session-start Fix1: hookSpecificOutput does not contain additionalContext"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  session-start Fix1: hookSpecificOutput contains additionalContext (payload duplication regression)"
  telfunc_fail=$((telfunc_fail + 1))
fi

# Test Fix4-A: global memory injected when directory contains .md files
TEST_TMP=$(mktemp -d)
TEST_MEM_DIR="${TEST_TMP}/.claude/devforge-global-memory"
mkdir -p "$TEST_MEM_DIR"
printf '# Test memory\nContenuto-globale-test-fixture' > "${TEST_MEM_DIR}/feedback-test.md"
SESSION_JSON_GM=$(HOME="${TEST_TMP}" bash "${PLUGIN_ROOT}/hooks/session-start" 2>/dev/null) || true
# Extract only the JSON block (skip npm/tsc noise from background processes)
SESSION_JSON_GM_CLEAN=$(echo "$SESSION_JSON_GM" | awk '/^\{/{f=1} f')
if echo "$SESSION_JSON_GM_CLEAN" | grep -q "Contenuto-globale-test-fixture"; then
  echo "  PASS  session-start Fix4: global memory injected when directory exists"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  session-start Fix4: global memory not injected"
  telfunc_fail=$((telfunc_fail + 1))
fi

# Test Fix4-B: MEMORY.md index file is NOT injected (case-insensitive skip)
printf '# Index\n- entry' > "${TEST_MEM_DIR}/MEMORY.md"
SESSION_JSON_IDX=$(HOME="${TEST_TMP}" bash "${PLUGIN_ROOT}/hooks/session-start" 2>/dev/null) || true
SESSION_JSON_IDX_CLEAN=$(echo "$SESSION_JSON_IDX" | awk '/^\{/{f=1} f')
if ! echo "$SESSION_JSON_IDX_CLEAN" | grep -q "# Index"; then
  echo "  PASS  session-start Fix4: MEMORY.md index file skipped"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  session-start Fix4: MEMORY.md index file incorrectly injected"
  telfunc_fail=$((telfunc_fail + 1))
fi

# Test Fix4-C: exit 0 without crash when global memory directory does not exist
SESSION_JSON_NODIR=$(HOME="${TEST_TMP}/no-such-dir" bash "${PLUGIN_ROOT}/hooks/session-start" 2>/dev/null; echo "exit:$?") || true
# Use raw variable: "exit:0" is appended after the JSON block, so awk (from first '{') may strip it.
if echo "$SESSION_JSON_NODIR" | grep -q "exit:0"; then
  echo "  PASS  session-start Fix4: exits cleanly when devforge-global-memory dir absent"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  session-start Fix4: crash when devforge-global-memory dir absent"
  telfunc_fail=$((telfunc_fail + 1))
fi

# Test Fix4-D: symlinks in global memory dir are skipped (no info-disclosure)
# Use a controlled target file with a unique marker — avoids dependency on /etc/hosts content
if command -v ln >/dev/null 2>&1; then
  SYMLINK_TARGET="${TEST_TMP}/fake-secret.txt"
  printf 'DEVFORGE_SYMLINK_LEAK_MARKER_XYZ' > "$SYMLINK_TARGET"
  ln -sf "$SYMLINK_TARGET" "${TEST_MEM_DIR}/evil-symlink.md" 2>/dev/null || true
  SESSION_JSON_SYM=$(HOME="${TEST_TMP}" bash "${PLUGIN_ROOT}/hooks/session-start" 2>/dev/null) || true
  SESSION_JSON_SYM_CLEAN=$(echo "$SESSION_JSON_SYM" | awk '/^\{/{f=1} f')
  if ! echo "$SESSION_JSON_SYM_CLEAN" | grep -q "DEVFORGE_SYMLINK_LEAK_MARKER_XYZ"; then
    echo "  PASS  session-start Fix4: symlinks in global memory dir skipped"
    telfunc_ok=$((telfunc_ok + 1))
  else
    echo "  FAIL  session-start Fix4: symlink content leaked into context"
    telfunc_fail=$((telfunc_fail + 1))
  fi
  rm -f "${TEST_MEM_DIR}/evil-symlink.md" "$SYMLINK_TARGET"
else
  echo "  SKIP  session-start Fix4 symlink: ln not available"
  TOTAL_SKIP=$((TOTAL_SKIP + 1))
fi

rm -rf "$TEST_TMP"

# Test F5: stop-gate with empty stdin emits telemetry but no verification JSON
F5_LOG="/tmp/devforge-test-f5.jsonl"
rm -f "$F5_LOG"
export DEVFORGE_LOG_FILE="$F5_LOG"
rm -rf "${HOME}/.claude/.devforge-session-end-guard"
echo "$(_devforge_epoch_ns)" > "${HOME}/.claude/.devforge-session-start-ns"
echo "0" > "${HOME}/.claude/.devforge-session-commits"
echo "" > "${HOME}/.claude/.devforge-session-skills"
F5_OUTPUT=$(echo "" | bash "${PLUGIN_ROOT}/hooks/stop-gate" 2>/dev/null || true)
if [ -z "$F5_OUTPUT" ] && grep -q '"event":"session_end"' "$F5_LOG" 2>/dev/null; then
  echo "  PASS  stop-gate F5: empty stdin emits session_end, no verification JSON"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  stop-gate F5: empty stdin — output='${F5_OUTPUT}', session_end=$(grep -c session_end "$F5_LOG" 2>/dev/null || echo 0)"
  telfunc_fail=$((telfunc_fail + 1))
fi
rm -f "$F5_LOG" "${HOME}/.claude/.devforge-session-start-ns" "${HOME}/.claude/.devforge-session-commits" "${HOME}/.claude/.devforge-session-skills"
rm -rf "${HOME}/.claude/.devforge-session-end-guard"

# Test F2: commit_created detection via HEAD hash comparison
# v1.63.3: LAST_HASH_FILE è per-repo (era globale). Allinea path al fix di post-commit-review.
F2_LOG="/tmp/devforge-test-f2.jsonl"
rm -f "$F2_LOG"
export DEVFORGE_LOG_FILE="$F2_LOG"
REAL_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "abc123")
F2_GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -n "$F2_GIT_ROOT" ]; then
  F2_REPO_KEY=$(echo "$F2_GIT_ROOT" | shasum 2>/dev/null | awk '{print $1}' | head -c 16)
  F2_LAST_HASH_FILE="${HOME}/.claude/.devforge-last-commit-hash-${F2_REPO_KEY:-global}"
else
  F2_LAST_HASH_FILE="${HOME}/.claude/.devforge-last-commit-hash-nogit"
fi
# Same hash → should NOT emit commit_created
echo "$REAL_HEAD" > "$F2_LAST_HASH_FILE"
echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' | bash "${PLUGIN_ROOT}/hooks/post-commit-review" 2>/dev/null || true
F2_COUNT_SAME=$(grep -c '"event":"commit_created"' "$F2_LOG" 2>/dev/null || echo "0")
# Different hash → should emit commit_created
echo "0000000000000000000000000000000000000000" > "$F2_LAST_HASH_FILE"
echo "0" > "${HOME}/.claude/.devforge-session-commits"
echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' | bash "${PLUGIN_ROOT}/hooks/post-commit-review" 2>/dev/null || true
F2_COUNT_DIFF=$(grep -c '"event":"commit_created"' "$F2_LOG" 2>/dev/null || echo "0")
if [ "$F2_COUNT_SAME" -eq 0 ] && [ "$F2_COUNT_DIFF" -eq 1 ]; then
  echo "  PASS  post-commit-review F2: hash comparison detects new commit correctly"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  post-commit-review F2: same_hash_events=$F2_COUNT_SAME (want 0), diff_hash_events=$F2_COUNT_DIFF (want 1)"
  telfunc_fail=$((telfunc_fail + 1))
fi
rm -f "$F2_LOG" "$F2_LAST_HASH_FILE" "${HOME}/.claude/.devforge-session-commits"

# Test post-commit-review commit_sha enrichment (K8 adoption health AC-8)
if bash "${PLUGIN_ROOT}/tests/hooks/post-commit-review-sha.test.sh" >/dev/null 2>&1; then
  echo "  PASS  post-commit-review: emette commit_sha nel commit_created event"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  post-commit-review: commit_sha assente in commit_created"
  telfunc_fail=$((telfunc_fail + 1))
fi

# Test PR lifecycle events (KPI Rosario #3: rework/review iterations)
if bash "${PLUGIN_ROOT}/tests/hooks/post-commit-pr-lifecycle.test.sh" >/dev/null 2>&1; then
  echo "  PASS  post-commit-pr-lifecycle: pr_opened/commit_after_open/review_cycle/merged/metrics"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  post-commit-pr-lifecycle: eventi PR lifecycle non emessi correttamente"
  telfunc_fail=$((telfunc_fail + 1))
fi

# Test brainstorming-gate progressive enforcement (adoption 3.3% -> 50%+)
if bash "${PLUGIN_ROOT}/tests/hooks/brainstorming-gate.test.sh" >/dev/null 2>&1; then
  echo "  PASS  brainstorming-gate: progressive enforcement (nudge/warn/block + bypass + anti-abuse)"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  brainstorming-gate: hook enforcement non funziona"
  telfunc_fail=$((telfunc_fail + 1))
fi

# Test hooks.json var expansion (fix: CLAUDE_PLUGIN_ROOT single-quote bug)
if bash "${PLUGIN_ROOT}/tests/hooks/hooks-json-var-expansion.test.sh" >/dev/null 2>&1; then
  echo "  PASS  hooks.json: \${CLAUDE_PLUGIN_ROOT} expansion (22 commands, runtime smoke)"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  hooks.json: \${CLAUDE_PLUGIN_ROOT} single-quote bug presente o JSON invalido"
  telfunc_fail=$((telfunc_fail + 1))
fi

# Test net-timeout: timeout hard portabile + NO_PROXY-github hardening
if bash "${PLUGIN_ROOT}/tests/lib/test_net_timeout.sh" >/dev/null 2>&1; then
  echo "  PASS  net-timeout: net_run cappa al budget + _devforge_no_proxy_github idempotente/exported"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  net-timeout: net_run o NO_PROXY hardening non funzionano"
  telfunc_fail=$((telfunc_fail + 1))
fi

# T-WIRE: i 3 hook con call di rete sorgiano net-timeout.sh e avvolgono ogni call github in net_run
if bash "${PLUGIN_ROOT}/tests/hooks/test_net_resilience_wiring.sh" >/dev/null 2>&1; then
  echo "  PASS  net-resilience-wiring: session-start/pr-release-gate/post-commit-review avvolgono gh/git in net_run"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  net-resilience-wiring: call github nuda o source net-timeout.sh mancante"
  telfunc_fail=$((telfunc_fail + 1))
fi

if bash "${PLUGIN_ROOT}/tests/hooks/test_adoption_emit.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/hooks/test_adoption_emit.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/hooks/test_adoption_emit.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/hooks/test_stop_gate_task_adoption_wiring.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/hooks/test_stop_gate_task_adoption_wiring.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/hooks/test_stop_gate_task_adoption_wiring.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/hooks/test_session_start_enforcement_off.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/hooks/test_session_start_enforcement_off.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/hooks/test_session_start_enforcement_off.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/hooks/test_session_start_global_rules.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/hooks/test_session_start_global_rules.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/hooks/test_session_start_global_rules.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/hooks/test_post_commit_no_verify.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/hooks/test_post_commit_no_verify.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/hooks/test_post_commit_no_verify.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/hooks/test_simplicity_reminder.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/hooks/test_simplicity_reminder.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/hooks/test_simplicity_reminder.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/hooks/test_post_commit_task_id.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/hooks/test_post_commit_task_id.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/hooks/test_post_commit_task_id.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/statusline/test_statusline_python_warning.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/statusline/test_statusline_python_warning.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/statusline/test_statusline_python_warning.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/hooks/test_session_start_plugin_update.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/hooks/test_session_start_plugin_update.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/hooks/test_session_start_plugin_update.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/statusline/test_statusline_plugin_update.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/statusline/test_statusline_plugin_update.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/statusline/test_statusline_plugin_update.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/statusline/test_statusline_version_label.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/statusline/test_statusline_version_label.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/statusline/test_statusline_version_label.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/statusline/test_statusline_git_cache_perrepo.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/statusline/test_statusline_git_cache_perrepo.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/statusline/test_statusline_git_cache_perrepo.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/statusline/test_statusline_telemetry_health.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/statusline/test_statusline_telemetry_health.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/statusline/test_statusline_telemetry_health.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/zero-loss/unit/test_logger_perl_fsync.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/zero-loss/unit/test_logger_perl_fsync.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/zero-loss/unit/test_logger_perl_fsync.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

if bash "${PLUGIN_ROOT}/tests/zero-loss/unit/test_writepath_zeroloss_crossplatform.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/zero-loss/unit/test_writepath_zeroloss_crossplatform.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/zero-loss/unit/test_writepath_zeroloss_crossplatform.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

# Telemetria/identità cross-platform (parità Windows≡macOS≡Linux) — design 2026-06-18
for _t in \
  "tests/zero-loss/unit/test_logger_event_id_concurrency.sh" \
  "tests/zero-loss/unit/test_logger_identity_signals.sh" \
  "tests/zero-loss/unit/test_logger_rotation_crosstier.sh" \
  "tests/zero-loss/unit/test_batch_global_archives.sh" \
  "tests/zero-loss/unit/test_logger_crlf_cursor.sh" \
  "tests/zero-loss/integration/test_crossplatform_no_degradation.sh" \
  "tests/test_telemetry_fixes.sh" \
  "tests/test_telemetry_flush_storm.sh"; do
  if bash "${PLUGIN_ROOT}/${_t}" >/dev/null 2>&1; then
    echo "  PASS  ${_t}"
    TOTAL_PASS=$((TOTAL_PASS + 1))
  else
    echo "  FAIL  ${_t}"
    TOTAL_FAIL=$((TOTAL_FAIL + 1))
  fi
done

if python3 -m pytest "${PLUGIN_ROOT}/tests/test_task_adoption_meta.py" -q >/dev/null 2>&1; then
  echo "  PASS  tests/test_task_adoption_meta.py"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/test_task_adoption_meta.py"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi

# Test F3: user cache fallback in devforge_get_user
F3_CACHE="${HOME}/.claude/.devforge-user"
F3_BACKUP=""
[ -f "$F3_CACHE" ] && F3_BACKUP=$(cat "$F3_CACHE")
echo "cached-test-user@siae.it" > "$F3_CACHE"
# Call devforge_get_user from a non-git directory where git config fails
F3_USER=$(cd /tmp && GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null HOME_ORIG="$HOME" bash -c "
  source '${PLUGIN_ROOT}/lib/logger.sh'
  devforge_get_user
" 2>/dev/null || echo "")
if echo "$F3_USER" | grep -qF "cached-test-user@siae.it"; then
  echo "  PASS  logger.sh F3: user cache fallback works"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  logger.sh F3: user cache returned '${F3_USER}' instead of 'cached-test-user@siae.it'"
  telfunc_fail=$((telfunc_fail + 1))
fi
# Restore cache
if [ -n "$F3_BACKUP" ]; then echo "$F3_BACKUP" > "$F3_CACHE"; else rm -f "$F3_CACHE"; fi

unset DEVFORGE_LOG_FILE

echo ""
echo "  Telemetry functional: ${telfunc_ok} OK | ${telfunc_fail} FAIL"
TOTAL_PASS=$((TOTAL_PASS + telfunc_ok))
TOTAL_FAIL=$((TOTAL_FAIL + telfunc_fail))

# ============================================================================
# Plugin Update Safety (design 2026-06-19) — un test per criterio di accettazione
# ============================================================================
echo ""
echo "=== Plugin Update Safety ==="
echo ""
pus_ok=0; pus_fail=0
SS="${PLUGIN_ROOT}/hooks/session-start"
PVLIB="${PLUGIN_ROOT}/lib/plugin-version.sh"

# T-AC1: nessun claude plugin update / rm -rf cache ATTIVO (non commentato)
if ! grep -nE '^[[:space:]]*[^#].*claude[[:space:]]+plugin[[:space:]]+update' "$SS" >/dev/null 2>&1 \
   && ! grep -nE '^[[:space:]]*[^#].*rm[[:space:]]+-rf[^#]*plugins/cache' "$SS" >/dev/null 2>&1; then
  echo "  PASS  T-AC1: session-start non esegue claude plugin update / rm -rf cache"; pus_ok=$((pus_ok+1))
else
  echo "  FAIL  T-AC1: trovato claude plugin update o rm -rf cache attivo"; pus_fail=$((pus_fail+1))
fi

# T-AC2: nessun falso successo / call-to-action manuale
if ! grep -nE '^[[:space:]]*[^#].*(Esegui:|aggiornato a v|Aggiornamento fallito)' "$SS" >/dev/null 2>&1; then
  echo "  PASS  T-AC2: nessun messaggio di falso successo / call-to-action"; pus_ok=$((pus_ok+1))
else
  echo "  FAIL  T-AC2: trovato messaggio falso successo/call-to-action"; pus_fail=$((pus_fail+1))
fi

# T-AC3: confronto numerico robusto + suffisso prerelease scartato
if ( source "$PVLIB" 2>/dev/null
     _ver_lt 1.9.0 1.10.0 && ! _ver_lt 1.10.0 1.9.0 && ! _ver_lt 1.93.0 1.93.0 && ! _ver_lt 1.93.0-rc1 1.93.0 ); then
  echo "  PASS  T-AC3: _ver_lt numerico (1.9<1.10, =, no prerelease bump)"; pus_ok=$((pus_ok+1))
else
  echo "  FAIL  T-AC3: _ver_lt errato"; pus_fail=$((pus_fail+1))
fi

# T-AC4: evento plugin_version_observed con status valido (anche in fallback)
PUS_LOG=$(mktemp 2>/dev/null || echo "/tmp/pus_log.$$")
DEVFORGE_LOG_FILE="$PUS_LOG" bash "$SS" >/dev/null 2>&1 || true
if grep -q '"event":"plugin_version_observed"' "$PUS_LOG" 2>/dev/null \
   && grep -oE '"status":"(up_to_date|behind|unavailable)"' "$PUS_LOG" >/dev/null 2>&1; then
  echo "  PASS  T-AC4: plugin_version_observed emesso con status valido"; pus_ok=$((pus_ok+1))
else
  echo "  FAIL  T-AC4: evento plugin_version_observed mancante o status non valido"; pus_fail=$((pus_fail+1))
fi
rm -f "$PUS_LOG"

# T-AC5: install.sh scrive path STABILE non-versionato + idempotenza
if command -v jq >/dev/null 2>&1; then
  PUS_HOME=$(mktemp -d 2>/dev/null || echo "/tmp/pus_home.$$"); mkdir -p "$PUS_HOME"
  mkdir -p "$PUS_HOME/.claude/plugins/marketplaces/siae-devforge/statusline"
  : > "$PUS_HOME/.claude/plugins/marketplaces/siae-devforge/statusline/devforge-statusline.sh"
  HOME="$PUS_HOME" bash "${PLUGIN_ROOT}/statusline/install.sh" >/dev/null 2>&1 || true
  CMD1=$(jq -r '.statusLine.command // empty' "$PUS_HOME/.claude/settings.json" 2>/dev/null)
  HOME="$PUS_HOME" bash "${PLUGIN_ROOT}/statusline/install.sh" >/dev/null 2>&1 || true
  CMD2=$(jq -r '.statusLine.command // empty' "$PUS_HOME/.claude/settings.json" 2>/dev/null)
  if ! printf '%s' "$CMD1" | grep -qE 'plugins/cache/siae-devforge/siae-devforge/[0-9]+\.[0-9]+\.[0-9]+' \
     && printf '%s' "$CMD1" | grep -q 'marketplaces/siae-devforge' && [ -n "$CMD1" ] && [ "$CMD1" = "$CMD2" ]; then
    echo "  PASS  T-AC5: install.sh path stabile non-versionato + idempotente"; pus_ok=$((pus_ok+1))
  else
    echo "  FAIL  T-AC5: path versionato o non idempotente (CMD1='$CMD1' CMD2='$CMD2')"; pus_fail=$((pus_fail+1))
  fi
  rm -rf "$PUS_HOME"
else
  echo "  SKIP  T-AC5: jq non disponibile"
fi

# T-AC6: VERSION_STATUS ancora presente → coperto dal test esistente "session-start injects
# VERSION_STATUS into additional_context JSON" (cerca "DevForge v"). Non duplicato qui per non
# eseguire session-start due volte (lento per la call gh).

# T-AC7: la lib versione non dipende da pgrep/kill su processi nativi (cross-platform safe)
if ! grep -nE 'pgrep|kill[[:space:]]+-|_net_kill_tree' "$PVLIB" >/dev/null 2>&1; then
  echo "  PASS  T-AC7: plugin-version.sh privo di pgrep/kill (Windows-safe)"; pus_ok=$((pus_ok+1))
else
  echo "  FAIL  T-AC7: trovato pgrep/kill in plugin-version.sh"; pus_fail=$((pus_fail+1))
fi

echo ""
echo "  Plugin Update Safety: ${pus_ok} OK | ${pus_fail} FAIL"
TOTAL_PASS=$((TOTAL_PASS + pus_ok))
TOTAL_FAIL=$((TOTAL_FAIL + pus_fail))

# ============================================================================
# Plugin Cache Resilience (design 2026-06-19) — un test per AC
# Sessioni attive sopravvivono all'auto-update nativo che rimuove cache versionate.
# ============================================================================
echo ""
echo "=== Plugin Cache Resilience ==="
echo ""
pcr_ok=0; pcr_fail=0
PCRLIB="${PLUGIN_ROOT}/lib/plugin-cache-resilience.sh"
CACHE_REL=".claude/plugins/cache/siae-devforge/siae-devforge"
# helper: crea un HOME isolato con una cache 'cur' reale; echo della BASE
_pcr_setup() { local h; h="$1"; mkdir -p "$h/$CACHE_REL/$2/hooks"; : > "$h/$CACHE_REL/$2/hooks/run-hook.cmd"; printf '%s/%s' "$h" "$CACHE_REL"; }

# T1 (AC1): versione vecchia rimossa nel registro → ricreata risolvibile
H=$(mktemp -d); B=$(_pcr_setup "$H" 1.95.0); echo "1.91.0" > "$H/.claude/.devforge-known-plugin-versions"
( set -euo pipefail; HOME="$H"; source "$PCRLIB"; devforge_ensure_version_compat "$B/1.95.0" ) 2>/dev/null || true
if [ -e "$B/1.91.0/hooks/run-hook.cmd" ]; then echo "  PASS  T1(AC1): path versionato rimosso → ripristinato"; pcr_ok=$((pcr_ok+1)); else echo "  FAIL  T1(AC1)"; pcr_fail=$((pcr_fail+1)); fi
rm -rf "$H"

# T2 (AC2): dir reale (anche incompleta) NON toccata
H=$(mktemp -d); B=$(_pcr_setup "$H" 1.95.0)
mkdir -p "$B/1.94.0/hooks"; echo REAL > "$B/1.94.0/hooks/run-hook.cmd"; mkdir -p "$B/1.93.0"  # 1.93.0 reale INCOMPLETA
printf '1.94.0\n1.93.0\n' >> "$H/.claude/.devforge-known-plugin-versions"
( set -euo pipefail; HOME="$H"; source "$PCRLIB"; devforge_ensure_version_compat "$B/1.95.0" ) 2>/dev/null || true
if [ "$(cat "$B/1.94.0/hooks/run-hook.cmd")" = REAL ] && [ ! -L "$B/1.94.0" ] && [ ! -L "$B/1.93.0" ] && [ ! -e "$B/1.93.0/hooks/run-hook.cmd" ]; then
  echo "  PASS  T2(AC2): dir reale completa+incompleta intatte (no data loss)"; pcr_ok=$((pcr_ok+1)); else echo "  FAIL  T2(AC2)"; pcr_fail=$((pcr_fail+1)); fi
rm -rf "$H"

# T3 (AC3): symlink rotto semver-puro → ripuntato; symlink estranei (path esterno E target
# semver+suffisso tipo 1.2.3-beta) → NON toccati (regex GUARD-4 ancorata ^..$)
H=$(mktemp -d); B=$(_pcr_setup "$H" 1.95.0)
ln -s 9.9.9 "$B/1.90.0"; ln -s /external/path "$B/1.89.0"; ln -s 1.2.3-beta "$B/1.88.0"
printf '1.90.0\n1.89.0\n1.88.0\n' >> "$H/.claude/.devforge-known-plugin-versions"
( set -euo pipefail; HOME="$H"; source "$PCRLIB"; devforge_ensure_version_compat "$B/1.95.0" ) 2>/dev/null || true
if [ -e "$B/1.90.0/hooks/run-hook.cmd" ] && [ "$(readlink "$B/1.89.0")" = /external/path ] && [ "$(readlink "$B/1.88.0")" = 1.2.3-beta ]; then
  echo "  PASS  T3(AC3): symlink rotto riparato; estranei (esterno + semver-suffisso) preservati"; pcr_ok=$((pcr_ok+1)); else echo "  FAIL  T3(AC3)"; pcr_fail=$((pcr_fail+1)); fi
rm -rf "$H"

# T4 (AC4): cross-platform — dopo il repair il path esiste comunque (symlink su macOS, copia su
# Windows-GitBash senza symlink nativi). Verifica generica del ramo "path risolvibile".
H=$(mktemp -d); B=$(_pcr_setup "$H" 1.95.0); echo "1.87.0" > "$H/.claude/.devforge-known-plugin-versions"
( set -euo pipefail; HOME="$H"; source "$PCRLIB"; devforge_ensure_version_compat "$B/1.95.0" ) 2>/dev/null || true
if [ -e "$B/1.87.0/hooks/run-hook.cmd" ]; then echo "  PASS  T4(AC4): path risolvibile (symlink o copia)"; pcr_ok=$((pcr_ok+1)); else echo "  FAIL  T4(AC4)"; pcr_fail=$((pcr_fail+1)); fi
rm -rf "$H"

# T5 (AC5): base inesistente → rc 0, nessun errore sotto set -euo pipefail
H=$(mktemp -d); RC=0; ( set -euo pipefail; HOME="$H"; source "$PCRLIB"; devforge_ensure_version_compat "$H/$CACHE_REL/1.95.0" ) 2>/dev/null || RC=$?
if [ "$RC" = 0 ]; then echo "  PASS  T5(AC5): base assente → rc 0 (best-effort)"; pcr_ok=$((pcr_ok+1)); else echo "  FAIL  T5(AC5): rc=$RC"; pcr_fail=$((pcr_fail+1)); fi
rm -rf "$H"

# T6 (AC6): dedup + cap 10
H=$(mktemp -d); B=$(_pcr_setup "$H" 1.95.0); reg="$H/.claude/.devforge-known-plugin-versions"
for i in $(seq 1 12); do echo "1.$i.0" >> "$reg"; done
( set -euo pipefail; HOME="$H"; source "$PCRLIB"; devforge_ensure_version_compat "$B/1.95.0"; devforge_ensure_version_compat "$B/1.95.0" ) 2>/dev/null || true
LINES=$(grep -c . "$reg"); DUP=$(sort "$reg" | uniq -d | grep -c . || true)
if [ "$LINES" -le 10 ] && [ "$DUP" = 0 ]; then echo "  PASS  T6(AC6): registro cap=$LINES, no duplicati"; pcr_ok=$((pcr_ok+1)); else echo "  FAIL  T6(AC6): lines=$LINES dup=$DUP"; pcr_fail=$((pcr_fail+1)); fi
rm -rf "$H"

# T7 (AC7): plugin_root FUORI dalla cache → nessuna operazione
H=$(mktemp -d); mkdir -p "$H/fake/siae-dev-forge"; echo "1.91.0" > "$H/.claude/.devforge-known-plugin-versions" 2>/dev/null || mkdir -p "$H/.claude" && echo "1.91.0" > "$H/.claude/.devforge-known-plugin-versions"
( set -euo pipefail; HOME="$H"; source "$PCRLIB"; devforge_ensure_version_compat "$H/fake/siae-dev-forge" ) 2>/dev/null || true
if ! ls "$H/fake" 2>/dev/null | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then echo "  PASS  T7(AC7): guard path, nessun file in path arbitrario"; pcr_ok=$((pcr_ok+1)); else echo "  FAIL  T7(AC7)"; pcr_fail=$((pcr_fail+1)); fi
rm -rf "$H"

# T8 (AC8): base con solo symlink, plugin_root non-semver → no autoreferenza
H=$(mktemp -d); B="$H/$CACHE_REL"; mkdir -p "$B"; ln -s 9.9.9 "$B/1.91.0"; echo "1.91.0" > "$H/.claude/.devforge-known-plugin-versions"
( set -euo pipefail; HOME="$H"; source "$PCRLIB"; devforge_ensure_version_compat "$B/notsemver" ) 2>/dev/null || true
if [ "$(readlink "$B/1.91.0" 2>/dev/null)" != 1.91.0 ]; then echo "  PASS  T8(AC8): nessun symlink autoreferenziale"; pcr_ok=$((pcr_ok+1)); else echo "  FAIL  T8(AC8): autoreferenza"; pcr_fail=$((pcr_fail+1)); fi
rm -rf "$H"

# T9 (AC9): due invocazioni concorrenti → path valido, nessun residuo .compat.*, registro senza duplicati
H=$(mktemp -d); B=$(_pcr_setup "$H" 1.95.0); echo "1.80.0" > "$H/.claude/.devforge-known-plugin-versions"
( set -euo pipefail; HOME="$H"; source "$PCRLIB"; devforge_ensure_version_compat "$B/1.95.0" ) 2>/dev/null &
( set -euo pipefail; HOME="$H"; source "$PCRLIB"; devforge_ensure_version_compat "$B/1.95.0" ) 2>/dev/null &
wait
T9DUP=$(sort "$H/.claude/.devforge-known-plugin-versions" 2>/dev/null | uniq -d | grep -c . || true)
if [ -e "$B/1.80.0/hooks/run-hook.cmd" ] && ! ls "$B"/.compat.* >/dev/null 2>&1 && [ "$T9DUP" = 0 ]; then echo "  PASS  T9(AC9): concorrenza → path valido, nessun residuo tmp, registro dedup"; pcr_ok=$((pcr_ok+1)); else echo "  FAIL  T9(AC9): dup=$T9DUP"; pcr_fail=$((pcr_fail+1)); fi
rm -rf "$H"

echo ""
echo "  Plugin Cache Resilience: ${pcr_ok} OK | ${pcr_fail} FAIL"
TOTAL_PASS=$((TOTAL_PASS + pcr_ok))
TOTAL_FAIL=$((TOTAL_FAIL + pcr_fail))

# --- Telemetry Event Validation ---
echo ""
echo "=== Telemetry Event Validation ==="
echo ""

telemetry_ok=0
telemetry_fail=0

# Test has_tests detection regex
HAS_TESTS_PATTERN='(Test\.|_test\.|\.test\.|\.spec\.|/test/|/tests/|^test_|^tests/)'

# Positive cases
for test_file in "UserServiceTest.java" "test_validator.py" "app.test.ts" "login.spec.ts" "src/test/MyTest.java" "tests/test_main.py"; do
  if echo "$test_file" | grep -qE "$HAS_TESTS_PATTERN"; then
    echo "  PASS  has_tests: riconosce '$test_file'"
    telemetry_ok=$((telemetry_ok + 1))
  else
    echo "  FAIL  has_tests: non riconosce '$test_file'"
    telemetry_fail=$((telemetry_fail + 1))
  fi
done

# Negative cases (should NOT match)
for src_file in "UserService.java" "validator.py" "app.ts" "login.vue" "README.md"; do
  if echo "$src_file" | grep -qE "$HAS_TESTS_PATTERN"; then
    echo "  FAIL  has_tests: falso positivo su '$src_file'"
    telemetry_fail=$((telemetry_fail + 1))
  else
    echo "  PASS  has_tests: correttamente ignora '$src_file'"
    telemetry_ok=$((telemetry_ok + 1))
  fi
done

# Test JSONL schema: verify all event types produce valid JSON
echo ""
echo "  --- JSONL Schema Validation ---"
SCHEMA_LOG="/tmp/devforge-test-schema.jsonl"
rm -f "$SCHEMA_LOG"
DEVFORGE_LOG_FILE_BAK="${DEVFORGE_LOG_FILE:-}"
export DEVFORGE_LOG_FILE="$SCHEMA_LOG"

source "${PLUGIN_ROOT}/lib/logger.sh"

# Generate sample events
devforge_log "skill_invoked" "success" '{"skill_name":"test","sdlc_phase":"5. Testing"}'
devforge_log "skill_completed" "success" '{"skill_name":"test","sdlc_phase":"5. Testing","outcome":"success"}'
devforge_log "commit_created" "success" '{"files_changed":3,"insertions":42,"deletions":7,"has_tests":true}'
devforge_log "pr_opened" "success" '{"pr_number":1,"base_branch":"main","files_changed":5,"commits_count":2}'
devforge_log "pr_merged" "success" '{"pr_number":1,"review_cycle_hours":4.5,"reviewers_count":2}'
devforge_log_timed "session_end" "success" "$(_devforge_epoch_ns)" '{"skills_used_count":3,"commits_count":2}'

# Validate each line is valid JSON
TOTAL_LINES=$(wc -l < "$SCHEMA_LOG" | tr -d ' ')
VALID_LINES=0
if command -v jq >/dev/null 2>&1; then
    while IFS= read -r line; do
        if echo "$line" | jq . >/dev/null 2>&1; then
            VALID_LINES=$((VALID_LINES + 1))
        fi
    done < "$SCHEMA_LOG"

    if [ "$VALID_LINES" -eq "$TOTAL_LINES" ]; then
        echo "  PASS  JSONL schema: ${VALID_LINES}/${TOTAL_LINES} linee JSON valide"
        telemetry_ok=$((telemetry_ok + 1))
    else
        echo "  FAIL  JSONL schema: ${VALID_LINES}/${TOTAL_LINES} linee JSON valide"
        telemetry_fail=$((telemetry_fail + 1))
    fi
else
    echo "  SKIP  JSONL schema: jq non disponibile"
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
fi

rm -f "$SCHEMA_LOG"
[ -n "$DEVFORGE_LOG_FILE_BAK" ] && export DEVFORGE_LOG_FILE="$DEVFORGE_LOG_FILE_BAK" || unset DEVFORGE_LOG_FILE

echo ""
echo "  Telemetry check: ${telemetry_ok} OK | ${telemetry_fail} FAIL"
TOTAL_PASS=$((TOTAL_PASS + telemetry_ok))
TOTAL_FAIL=$((TOTAL_FAIL + telemetry_fail))

# --- Eval Service Pipeline (opzionale, richiede claude CLI + Bedrock) ---
if [ -n "$WITH_EVALS" ]; then
  echo ""
  echo "=== Eval Service Pipeline (levels: ${WITH_EVALS}) ==="
  echo ""

  if [ -f "${PLUGIN_ROOT}/evals/runner.py" ]; then
    python3 "${PLUGIN_ROOT}/evals/runner.py" \
      --all --level "${WITH_EVALS}" --verbose --report 2>&1 || true
  else
    echo "  SKIP  evals/runner.py non trovato"
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
  fi
fi

# --- Report Finale ---
echo ""
echo "| 🟢 SICURO — 🔨 DevForge · REPORT FINALE |"
echo "|:---|"
echo "| ✅ PASS: \`${TOTAL_PASS}\` |"
echo "| ❌ FAIL: \`${TOTAL_FAIL}\` |"
echo "| ⏭️  SKIP: \`${TOTAL_SKIP}\` |"
echo ""

if [ "$TOTAL_FAIL" -gt 0 ]; then
  exit 1
fi

exit 0
