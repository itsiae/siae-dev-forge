#!/usr/bin/env bash
# test: onboarding-env-repoint — asserisce che le liste ambienti hardcoded
# siano state rimosse da siae-onboarding e sostituite da un puntatore
# alla fonte canonica skills/using-devforge/reference/siae-environments.md
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SKILL_MD="${REPO_ROOT}/skills/siae-onboarding/SKILL.md"
FACTORY_MD="${REPO_ROOT}/skills/siae-onboarding/reference/factory-configs.md"
CANONICAL="skills/using-devforge/reference/siae-environments.md"

PASS=0; FAIL=0
ok(){ if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

echo "TEST onboarding-env-repoint"

# T1: i tag pattern sospetti (mai verificati) non devono comparire in SKILL.md
ok "T1: nessun tag pattern v*.*.*-dev.* in SKILL.md" \
  '! grep -qF "v*.*.*-dev.*" "$SKILL_MD"'
ok "T1b: nessun tag pattern v*.*.*-rc.* in SKILL.md" \
  '! grep -qF "v*.*.*-rc.*" "$SKILL_MD"'
ok "T1c: nessun tag pattern v*.*.*-cert.* in SKILL.md" \
  '! grep -qF "v*.*.*-cert.*" "$SKILL_MD"'

# T2: la tabella "### 3.2 Ambienti" con colonna "Tag pattern" non deve piu' esistere
ok "T2: nessuna colonna 'Tag pattern' in SKILL.md" \
  '! grep -qF "Tag pattern" "$SKILL_MD"'

# T3: SKILL.md punta alla fonte canonica
ok "T3: SKILL.md referenzia siae-environments.md" \
  'grep -qF "$CANONICAL" "$SKILL_MD"'

# T4: il blocco .siae-config.json non elenca piu' i 4 ambienti inline
ok "T4: nessun array environments hardcoded in SKILL.md" \
  '! grep -qF "\"sviluppo\", \"collaudo\", \"certificazione\", \"produzione\"" "$SKILL_MD"'

# T5: factory-configs.md non ha piu' i tag pattern sospetti collaudo/cert/prod
ok "T5: nessun tag pattern v*.*.*-rc.* in factory-configs.md" \
  '! grep -qF "v*.*.*-rc.*" "$FACTORY_MD"'
ok "T5b: nessun tag pattern v*.*.*-cert.* in factory-configs.md" \
  '! grep -qF "v*.*.*-cert.*" "$FACTORY_MD"'

# T6: factory-configs.md non elenca piu' i 4 ambienti come "regola comune" hardcoded
ok "T6: nessuna riga '4 ambienti: sviluppo, collaudo' in factory-configs.md" \
  '! grep -qF "4 ambienti**: sviluppo, collaudo, certificazione, produzione" "$FACTORY_MD"'

# T7: factory-configs.md punta alla fonte canonica
ok "T7: factory-configs.md referenzia siae-environments.md" \
  'grep -qF "$CANONICAL" "$FACTORY_MD"'

echo ""; echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
