# Task 01 — Test Scaffold

**Goal:** Setup directory `tests/skill-activation/` con README + cost-cap doc + .gitignore.

**File coinvolti:**
- `tests/skill-activation/README.md` (nuovo)
- `tests/skill-activation/.gitignore` (nuovo)
- `requirements-test.txt` (nuovo, root) — Python deps

## Step 1 — Crea struttura directory

```bash
mkdir -p tests/skill-activation
```

## Step 2 — README

In `tests/skill-activation/README.md`:

```markdown
# Skill Activation Test Suite

Suite di test che misura quale skill DevForge viene invocata da Claude per ogni
prompt rappresentativo. Usa AWS Bedrock (Sonnet 4.6 default, Haiku 4.5 fallback)
per evitare di consumare quota Claude Code utente.

## Quick start

```bash
# Setup environment
export AWS_REGION=eu-west-1
export AWS_BEARER_TOKEN_BEDROCK=<your-token>
export CLAUDE_CODE_USE_BEDROCK=1

# Smoke test (3 prompt, ~$0.01)
TEST_MODEL=haiku ./tests/skill-activation/run.sh --smoke

# Full baseline (30 prompt, ~$0.04 Sonnet o $0.014 Haiku)
TEST_MODEL=sonnet ./tests/skill-activation/run.sh
```

## Cost cap

- Per-run: ~$0.04 Sonnet, ~$0.014 Haiku
- Iterazioni 50 max: ~$2 Sonnet, ~$0.70 Haiku
- Hard cap: $5 CloudWatch alarm su account Bedrock
- Runner exit early su rate limit / 4xx

## Output

Report markdown in `tests/skill-activation/report-YYYY-MM-DD-<label>.md`.

## Files

- `cases.yml` — 30 prompt rappresentativi (input)
- `run.sh` — runner Bedrock
- `evaluator.py` — parser output + match logic + report generator
- `baseline-2026-05-03.md` — snapshot baseline pre-PR-5 (immutabile)
- `report-*.md` — report iterativi post-modifica
```

## Step 3 — .gitignore

In `tests/skill-activation/.gitignore`:

```
# Output run-time (eccetto baseline)
report-*.md
!report-template.md
.cache/
*.tmp
```

## Step 4 — requirements-test.txt

In repo root `requirements-test.txt`:

```
boto3>=1.34
pyyaml>=6.0
```

## Step 5 — Commit

```bash
git add tests/skill-activation/README.md tests/skill-activation/.gitignore requirements-test.txt
git commit -m "test(skill-activation): scaffold directory + README + Python deps

Setup test suite Bedrock per misurare baseline activation skill DevForge.
Cost cap $5, runner Sonnet 4.6 default, Haiku 4.5 fallback per cost-tight runs."
```

## Criteri accettazione

- `tests/skill-activation/` directory esiste
- README + .gitignore + requirements-test.txt committati
- Nessun secret committato (token via env var)
