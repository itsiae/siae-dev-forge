# Task 14 — Version bump + CHANGELOG + PR

**Stato:** [PENDING]
**Execution:** in-session
**Dipendenze:** T01-T13 completi
**Durata stimata:** 15 min

## Goal

Bump plugin a v1.46.0, aggiornare CHANGELOG, lanciare full test suite con test improvements per dimostrare che PR #1 migliora (non solo preserva), aprire PR con body-file.

## Step

### Step 1 — siae-git-workflow invocazione (prerequisito)

Prima di qualsiasi git commit, invoca `Skill tool -> siae-devforge:siae-git-workflow`. Questo soddisfa il pre-commit gate.

### Step 2 — Crea feature branch

```bash
git checkout -b feat/anti-dilution-pr1-foundation
```

### Step 3 — Run full regression + improvement suite

```bash
bash tests/compression-regression/run-all.sh 2>&1 | tail -30
```
Output atteso: tutti i 4 script PASS.

```bash
bash tests/run-all.sh 2>&1 | grep -E "PASS:|FAIL:|SKIP"
```
Output atteso: PASS >= 168, FAIL <= 6.

### Step 4 — Update version

```bash
python3 <<'PY'
import json
with open('.claude-plugin/plugin.json') as f: d = json.load(f)
print(f"From: {d['version']}")
d['version'] = '1.46.0'
with open('.claude-plugin/plugin.json', 'w') as f: json.dump(d, f, indent=2)
print(f"To:   {d['version']}")
PY
```
Output atteso:
```
From: 1.45.0
To:   1.46.0
```

### Step 5 — Compile diff stats for PR

```bash
# Per PR body: compression delta
echo "=== SKILL.md line counts ==="
for f in skills/using-devforge/SKILL.md skills/siae-{brainstorming,tdd,git-workflow,verification,blind-review}/SKILL.md; do
    echo "$(wc -l < $f) $f"
done

echo ""
echo "=== Total ==="
wc -l skills/using-devforge/SKILL.md skills/siae-{brainstorming,tdd,git-workflow,verification,blind-review}/SKILL.md | tail -1

echo ""
echo "=== Compression regression suite ==="
bash tests/compression-regression/run-all.sh 2>&1 | grep -E "^Suite|^Total"

echo ""
echo "=== Baseline suite ==="
bash tests/run-all.sh 2>&1 | grep -E "PASS:|FAIL:|SKIP:"
```

Salva l'output in un file per riferimento durante la PR body.

### Step 6 — Update CHANGELOG (se presente)

```bash
if [ -f CHANGELOG.md ]; then
    # Insert new version entry at the top
    python3 <<'PY'
import datetime
CHANGELOG = 'CHANGELOG.md'
today = datetime.date.today().isoformat()
entry = f"""## [1.46.0] - {today}

### Anti-Dilution Foundation (PR #1 of 3)

#### Added
- `lib/evidence-check.sh` — 5 skill predicate validators (ADR-002)
- `validates_via` frontmatter on 5 core skills (tdd, brainstorming, git-workflow, verification, blind-review)
- `lib/measure-task-baseline.sh` — proxy task-scoped baseline generator
- `baseline-metrics-tasks.json` — pre-measurement for PR #2 lift
- `hooks/devforge-context` — unified UserPromptSubmit hook with budget + diff-based dedup (ADR-004)
- `lib/{{risk-taxonomy,operational-limits,permission-denied-handling,checkpoint-schema}}.md` — centralizations (ADR-003)
- `tests/compression-regression/` — 4-script suite verifying both non-regression AND improvement
- `docs/measurements/baseline-2026-04-25/` — frozen telemetry baseline (230 sessions, 3489 events)

#### Changed
- SKILL.md backbone compressed 2636 -> <=1000 lines (-62%)
  - using-devforge 139 -> 90
  - siae-brainstorming 652 -> 220
  - siae-tdd 578 -> 180
  - siae-git-workflow 744 -> 220
  - siae-verification 345 -> 180
  - siae-blind-review 178 -> 110
- Prompt injection: 3 UserPromptSubmit hooks fused into 1
  - Old: ~12KB reinject every 10 messages
  - New: <=2KB per emission with diff-based dedup

#### Removed (archived in hooks/.archived/)
- `user-prompt-context` v1.45 (archived, functionality merged)
- `devforge-reinject` v1.45 (archived)
- `devforge-context-always` v1.45 (archived)

#### Metrics
- Adoption skill baseline (pre-PR-1): brainstorming 38%, tdd 38%, verification 3%, blind-review 0%
- Target PR #1: non-regression + compression targets met
- Target PR #2+#3: adoption per-task >=80%

"""
with open(CHANGELOG) as f: content = f.read()
# Insert after the first line (typically "# Changelog")
lines = content.split("\n", 1)
new_content = lines[0] + "\n\n" + entry + (lines[1] if len(lines) > 1 else "")
with open(CHANGELOG, 'w') as f: f.write(new_content)
print("CHANGELOG updated")
PY
fi
```

### Step 7 — Commit version bump

```bash
git add .claude-plugin/plugin.json
[ -f CHANGELOG.md ] && git add CHANGELOG.md
git commit -m "chore(release): bump version to 1.46.0

PR #1 anti-dilution foundation + compression.
See CHANGELOG.md for details."
```

### Step 8 — siae-verification invocazione

Prima di creare la PR, invoca `Skill tool -> siae-devforge:siae-verification` per il completion claim. Esegui i 5 step IDENTIFICA/ESEGUI/LEGGI/VERIFICA/AFFERMA sui criteri di accettazione.

### Step 9 — Create PR body file

```bash
cat > /tmp/pr-body.md <<'EOF'
## Summary

PR #1 di 3 dell'initiative **Anti-Dilution Enforcement** (design: `docs/plans/2026-04-25-anti-dilution-enforcement-design.md`).

Questa PR stabilisce le fondazioni: evidence contract, radical SKILL.md compression, prompt injection budget. Le PR #2 (task-scoped enforcement) e #3 (observability loop) seguiranno.

## Baseline observed (pre-PR)

Telemetry su 230 sessioni / 3489 eventi:
- Skill brainstorming: 38% delle sessioni con commit
- Skill tdd: 38%
- Skill verification: **3%**
- Skill blind-review: **0%**

Root cause identificato: session-scoped enforcement + invocation-based (non evidence-based) + 2636 righe di SKILL.md backbone + ~12KB injection periodica = diluizione del comportamento, wolf-cry effect.

## Changes (this PR)

### ADR-002 Evidence Contract
- `lib/evidence-check.sh` con `devforge_skill_validated(skill, task_id)` e 5 predicati
- Frontmatter `validates_via` su 5 skill core
- Funzione implementata e unit-tested, cutover nei gate deferred a PR #2

### ADR-003 Radical Compression
- SKILL.md backbone: 2636 -> <=1000 lines (-62%)
- Centralizzazioni in `lib/risk-taxonomy.md`, `lib/operational-limits.md`, `lib/permission-denied-handling.md`, `lib/checkpoint-schema.md`
- Regole comportamentali K preservate verbatim (Legge di Ferro, Hard-Gate, Checkpoint, Pre-Flight Card)

### ADR-004 Prompt Injection Budget
- 3 hook UserPromptSubmit fusi in `devforge-context`
- Budget hard-cap 2KB per emission
- Diff-based dedup (hash stato invariato -> output vuoto)
- Tier-based tags (default none, IMPORTANT se gate violation <60s)
- Telemetry: `prompt_injection_emitted` event con size + tier

### Baseline + improvement tests
- `docs/measurements/baseline-2026-04-25/baseline-metrics.json` - session-scoped baseline
- `docs/measurements/baseline-2026-04-25/baseline-metrics-tasks.json` - proxy task-scoped (pre-measurement for PR #2)
- `tests/compression-regression/` - 4 script che verificano:
  - `assert_behavioral_invariants.sh` - K sections preserved (non-regression)
  - `assert_compression_targets.sh` - wc -l targets achieved (improvement)
  - `assert_injection_reduction.sh` - devforge-context budget respected (improvement)
  - `assert_baseline_preserved.sh` - 168 PASS / 6 FAIL baseline preserved

## Test plan

- [x] Baseline suite: PASS >= 168, FAIL <= 6 (preserved)
- [x] `tests/compression-regression/run-all.sh`: tutti i 4 script PASS
- [x] `tests/lib/test_evidence_check.sh`: 10 PASS (5 predicati × pos+neg)
- [x] `tests/hooks/test_devforge_context.sh`: budget + diff + telemetry verificati
- [x] `node lib/skills-core.js`: catalog si genera correttamente post-compression
- [x] Version bump a 1.46.0

## Non-regression guarantee

1. Tutti i comportamenti enforcement attuali invariati (gate still session-scoped in PR #1)
2. Compression non tocca regole K (Legge di Ferro, Hard-Gate, Pre-Flight Card, checkpoint schema)
3. `devforge-context` sostituisce funzionalmente i 3 hook fusi (no new behavior)
4. `validates_via` frontmatter non ancora letto dai gate (introdotto in PR #2 dual-write phase)

## Rollback

Per rollback: `git revert <merge_commit>`. Archive in `hooks/.archived/` permette restore puntuale dei 3 hook precedenti.

## Next

- **PR #2** (v1.47): Task-scoped enforcement + scope cleanup + nuovi gate
- **PR #3** (v1.48): Observability loop (`/forge-adoption`, stop-gate recap, block explainer)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

### Step 10 — Push + create PR (via body-file)

Pre-flight card 🟡 MEDIO prima del push:

| 🟡 MEDIO — 🔨 DevForge · siae-git-workflow |
|:---|
| Operazione: `git push origin feat/anti-dilution-pr1-foundation` |
| 1. Azione: push feature branch |
| Perché: apri PR per review |
| Se NO: PR non apre |

```bash
git push -u origin feat/anti-dilution-pr1-foundation
gh pr create --title "feat: anti-dilution foundation + compression (v1.46.0)" --body-file /tmp/pr-body.md --base main
```

Usa `--body-file` (tua memory: heredoc bash si rompe su markdown+emoji).

### Step 11 — Output PR URL

```bash
gh pr view --json url --jq .url
```

## Acceptance

- [ ] Feature branch creato
- [ ] `tests/compression-regression/run-all.sh` all PASS
- [ ] `tests/run-all.sh` baseline preserved o improved (PASS>=168, FAIL<=6)
- [ ] `.claude-plugin/plugin.json` version = "1.46.0"
- [ ] CHANGELOG aggiornato (se presente)
- [ ] siae-verification invocata prima del PR create
- [ ] PR aperta con `--body-file` (non heredoc)
- [ ] PR URL ritornato
