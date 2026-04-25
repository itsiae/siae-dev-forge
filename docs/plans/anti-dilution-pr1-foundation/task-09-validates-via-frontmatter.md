# Task 09 — Aggiungere frontmatter validates_via su 5 skill core

**Stato:** [PENDING]
**Execution:** in-session (indipendente, può eseguire in parallelo con compression)
**Dipendenze:** nessuna (tocca solo frontmatter top)
**Durata stimata:** 10 min

## Goal

Aggiungere campo `validates_via` al frontmatter YAML di 5 skill core. Il campo è letto (ma non ancora enforced) dai gate di PR #1; sarà enforced in PR #2 cutover.

## Schema frontmatter

```yaml
---
name: <invariato>
description: <invariato>
validates_via:
  predicate: <predicate_id>
  evidence_type: state_file | log_event | file_pattern | git_state
  evidence_path: <opzionale, solo per state_file>
  evidence_check: <descrizione human-readable>
---
```

## Modifiche richieste (5 skill, 5 edit atomici)

### 1. skills/siae-tdd/SKILL.md

Frontmatter aggiuntivo:
```yaml
validates_via:
  predicate: tdd_red_green_observed
  evidence_type: state_file
  evidence_path: ~/.claude/.devforge-tdd-state
  evidence_check: phase ∈ (GREEN, REFACTOR), transitioned from RED
```

### 2. skills/siae-brainstorming/SKILL.md

```yaml
validates_via:
  predicate: design_doc_produced
  evidence_type: file_pattern
  evidence_check: docs/plans/*-design.md mtime > DEVFORGE_SESSION_START_S
```

### 3. skills/siae-git-workflow/SKILL.md

```yaml
validates_via:
  predicate: conventional_commit_made
  evidence_type: git_state
  evidence_check: git log -1 --format=%s matches ^(feat|fix|chore|docs|refactor|test|style|perf|build|ci|revert)(\(.+\))?!?:
```

### 4. skills/siae-verification/SKILL.md

```yaml
validates_via:
  predicate: verification_run_passed
  evidence_type: log_event
  evidence_check: DEVFORGE_LOG_FILE contains verification_run event with exit=0 for current sid
```

### 5. skills/siae-blind-review/SKILL.md

```yaml
validates_via:
  predicate: blind_review_completed
  evidence_type: log_event
  evidence_check: DEVFORGE_LOG_FILE contains blind_review_verdict event for current sid
```

## Step

### Step 1: Read frontmatter corrente per ogni skill

```bash
for s in tdd brainstorming git-workflow verification blind-review; do
  echo "=== siae-$s ==="
  awk '/^---/{c++} c==1 || c==2' skills/siae-$s/SKILL.md | head -15
done
```

### Step 2: Apply edits

Per ogni skill, usa il tool `Edit` per inserire `validates_via:` come ULTIMA chiave prima della chiusura `---`. Non modificare `name` o `description`.

### Step 3: verifica YAML valido

```bash
for s in tdd brainstorming git-workflow verification blind-review; do
  python3 -c "
import yaml, sys
with open('skills/siae-$s/SKILL.md') as f:
    content = f.read()
parts = content.split('---', 2)
meta = yaml.safe_load(parts[1])
assert 'validates_via' in meta, 'missing validates_via'
assert 'predicate' in meta['validates_via'], 'missing predicate'
print(f'PASS siae-$s -> {meta[\"validates_via\"][\"predicate\"]}')"
done
```
Output atteso: 5 PASS.

### Step 4: verifica coerenza con lib/evidence-check.sh

Ogni `predicate` dichiarato nel frontmatter deve avere un handler in `lib/evidence-check.sh`:

```bash
for p in tdd_red_green_observed design_doc_produced conventional_commit_made verification_run_passed blind_review_completed; do
  grep -q "$p" lib/evidence-check.sh && echo "PASS evidence_check has $p" || echo "FAIL missing $p"
done
```
Output atteso: 5 PASS (richiede T02 completo).

### Step 5: commit

```bash
git add skills/siae-tdd/SKILL.md skills/siae-brainstorming/SKILL.md skills/siae-git-workflow/SKILL.md skills/siae-verification/SKILL.md skills/siae-blind-review/SKILL.md
git commit -m "feat(skills): add validates_via frontmatter to 5 core skills

Part of PR #1 anti-dilution (ADR-002 Evidence Contract).
Declarative predicate per skill, consumed by lib/evidence-check.sh.
Not yet enforced by gate hooks (cutover in PR #2 dual-write phase).

Predicates:
- siae-tdd -> tdd_red_green_observed (state_file)
- siae-brainstorming -> design_doc_produced (file_pattern)
- siae-git-workflow -> conventional_commit_made (git_state)
- siae-verification -> verification_run_passed (log_event)
- siae-blind-review -> blind_review_completed (log_event)"
```

## Acceptance

- [ ] 5 skill hanno `validates_via` nel frontmatter
- [ ] YAML valido (verificato via python3 yaml.safe_load)
- [ ] Ogni `predicate` dichiarato ha handler in `lib/evidence-check.sh`
- [ ] Commit conventional `feat(skills):`
