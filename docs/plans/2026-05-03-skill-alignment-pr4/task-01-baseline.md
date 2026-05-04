# Task 01 — Baseline Measurement

**Goal:** Misurare e committare baseline immutabile pre-PR-4: line count delle 8 skill backbone, leakage SIAE grep count, snapshot description pattern. Indispensabile per verifica no-regression in Task 13.

**File coinvolti:**
- Output: `docs/measurements/skill-alignment-baseline-2026-05-03.md` (nuovo)
- Read-only: tutte 8 skill backbone

## Step 1 — Crea directory misurazioni

```bash
mkdir -p docs/measurements
```

## Step 2 — Genera baseline file

Run il seguente script bash (può essere inline o salvato in `scripts/baseline-skill-alignment.sh`):

```bash
#!/usr/bin/env bash
set -euo pipefail
OUT="docs/measurements/skill-alignment-baseline-2026-05-03.md"
BACKBONE=(siae-brainstorming siae-tdd siae-debugging siae-verification siae-writing-plans siae-executing-plans siae-finishing-branch using-devforge)

{
  echo "# Skill Alignment Baseline 2026-05-03"
  echo
  echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
  echo "Commit: $(git rev-parse HEAD)"
  echo
  echo "## Line counts (backbone)"
  echo
  echo "| Skill | Lines |"
  echo "|---|---|"
  for s in "${BACKBONE[@]}"; do
    f="skills/$s/SKILL.md"
    if [ -f "$f" ]; then
      echo "| $s | $(wc -l < "$f") |"
    else
      echo "| $s | MISSING |"
    fi
  done
  echo
  echo "## Leakage grep count (SIAE-specific in backbone)"
  echo
  echo '```'
  for s in "${BACKBONE[@]}"; do
    f="skills/$s/SKILL.md"
    [ -f "$f" ] || continue
    echo "=== $s ==="
    grep -nE 'sport-\*|pop-\*|pae-\*|PRODUZIONE|CERTIFICAZIONE' "$f" || echo "(no match)"
  done
  echo '```'
  echo
  echo "## Description frontmatter snapshot (first 15 lines each)"
  echo
  for s in "${BACKBONE[@]}"; do
    f="skills/$s/SKILL.md"
    [ -f "$f" ] || continue
    echo "### $s"
    echo '```yaml'
    sed -n '1,15p' "$f"
    echo '```'
    echo
  done
} > "$OUT"

echo "Baseline written: $OUT"
wc -l "$OUT"
```

## Step 3 — Verifica output

```bash
ls -la docs/measurements/skill-alignment-baseline-2026-05-03.md
head -30 docs/measurements/skill-alignment-baseline-2026-05-03.md
```

Output atteso: file >100 righe con tabella line count + grep leakage + 8 frontmatter snapshot.

## Step 4 — Commit baseline (immutabile)

```bash
git add docs/measurements/skill-alignment-baseline-2026-05-03.md
git commit -m "docs(measurements): baseline skill alignment 2026-05-03 (PR-4 pre)"
```

## Criteri accettazione

- File `docs/measurements/skill-alignment-baseline-2026-05-03.md` esiste e committato
- Line count 8 skill presente
- Grep leakage mostra 3 file con match (service-logic-map non in backbone, ma git-workflow sì se in lista — verifica se git-workflow è nei backbone misurati: NO, solo siae-{brainstorming,tdd,debugging,verification,writing-plans,executing-plans,finishing-branch} + using-devforge)
- 8 description snapshot presenti

## NO-REGRESSION reference

Questo file è il riferimento immutabile per Task 13. **Mai modificarlo dopo il commit di questo task.**
