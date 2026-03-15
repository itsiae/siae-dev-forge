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
ACTUAL_HOOKS=$(grep -oE '"(SessionStart|PreToolUse|PostToolUse|Stop)"' "${PLUGIN_ROOT}/hooks/hooks.json" | sort -u | wc -l | tr -d ' ')

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

  # Check 2: Tutte le skill → Tabella Anti-Razionalizzazione
  if ! grep -qi 'Tabella Anti-Razionalizzazione' "$skill_file"; then
    fail_reasons="${fail_reasons}[MANCA: Tabella Anti-Razionalizzazione] "
  fi

  # Check 3: Tutte le skill → Classificazione Rischio Operazioni
  if ! grep -qi 'Classificazione Rischio' "$skill_file"; then
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
devforge_log_timed "session_end" "success" "$(date +%s%N)" '{"skills_used_count":4,"commits_count":3}'
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
echo "$(date +%s%N 2>/dev/null || echo 0)" > "${HOME}/.claude/.devforge-session-start-ns"
echo "1" > "${HOME}/.claude/.devforge-session-commits"
echo "test-skill" > "${HOME}/.claude/.devforge-session-skills"
# Invoke stop-gate twice — session_end should appear only once
stop_input='{"messages":[{"role":"assistant","content":"tutto fatto"}]}'
echo "$stop_input" | bash "${PLUGIN_ROOT}/hooks/stop-gate" 2>/dev/null || true
sleep 1  # wait for background telemetry
echo "$stop_input" | bash "${PLUGIN_ROOT}/hooks/stop-gate" 2>/dev/null || true
sleep 1
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
DEVFORGE_SKIP_UPDATE=1 bash "${PLUGIN_ROOT}/hooks/session-start" >/dev/null 2>&1 || true
if [ ! -d "${HOME}/.claude/.devforge-session-end-guard" ]; then
  echo "  PASS  session-start: cleans up stale session_end guard"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  session-start: did not clean up stale session_end guard"
  telfunc_fail=$((telfunc_fail + 1))
  rm -rf "${HOME}/.claude/.devforge-session-end-guard"
fi

# Test: session-start injects VERSION_STATUS into additional_context JSON
SESSION_JSON=$(DEVFORGE_SKIP_UPDATE=1 bash "${PLUGIN_ROOT}/hooks/session-start" 2>/dev/null) || true
if echo "$SESSION_JSON" | grep -q "DevForge v"; then
  echo "  PASS  session-start: VERSION_STATUS injected in additional_context"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  session-start: VERSION_STATUS missing from additional_context"
  telfunc_fail=$((telfunc_fail + 1))
fi

unset DEVFORGE_LOG_FILE

echo ""
echo "  Telemetry functional: ${telfunc_ok} OK | ${telfunc_fail} FAIL"
TOTAL_PASS=$((TOTAL_PASS + telfunc_ok))
TOTAL_FAIL=$((TOTAL_FAIL + telfunc_fail))

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
devforge_log_timed "session_end" "success" "$(date +%s%N)" '{"skills_used_count":3,"commits_count":2}'

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
