# Task 08 — Comprimere skills/siae-blind-review/SKILL.md (178→110 righe)

**Stato:** [PENDING]
**Execution:** subagent (parallel-safe)
**Dipendenze:** T01
**Durata stimata:** 6-8 min

## Scope

File già compatto (178 righe). Compressione leggera: rimuovere solo ridondanze con `lib/*.md`. Target –38%.

## Step

### Step 1: ispeziona sezioni attuali

```bash
grep -nE '^## ' skills/siae-blind-review/SKILL.md
wc -l skills/siae-blind-review/SKILL.md
```

### Step 2: applica K/M/D

- **K**: legge di ferro, hard-gate, processo review (trova tutto, segnala tutto, non giudicare implementazione)
- **M**: Classificazione Rischio → ref a `lib/risk-taxonomy.md`, Limiti → ref a `lib/operational-limits.md`, Permission Denied → ref a `lib/permission-denied-handling.md`
- **D**: Tabella Anti-Razionalizzazione (se presente), esempi ridondanti

### Step 3: verifica target

```bash
wc -l skills/siae-blind-review/SKILL.md
```
Output atteso: `≤110`

### Step 4: smoke test frontmatter + catalog

```bash
head -10 skills/siae-blind-review/SKILL.md | grep -cE "^name:|^description:"  # → 2
node lib/skills-core.js "$(pwd)" 2>&1 | grep -q siae-blind-review && echo "PASS catalog"
```

### Step 5: commit

```bash
git add skills/siae-blind-review/SKILL.md
git commit -m "refactor(skills): compress siae-blind-review SKILL.md (178->110)

Part of PR #1 anti-dilution (ADR-003).
M referenced: risk/limits/permission via lib/*.md.
Behaviour-impacting rules: ZERO changes."
```

## Acceptance

- [ ] `wc -l` ≤ 110
- [ ] `name` + `description` invariati
- [ ] Skill presente nel catalog generato
- [ ] Commit conventional
