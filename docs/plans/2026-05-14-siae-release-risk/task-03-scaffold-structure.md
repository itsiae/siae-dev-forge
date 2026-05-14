# Task 03 — Scaffold directory structure

**Stato:** [PENDING]
**SP:** 0.5 Human / 0.25 Augmented
**Dipendenze:** task-02

## Goal

Creare scaffold dir + file placeholder vuoti per: `skills/siae-release-risk/`, `lib/release_risk/`, `tests/` placeholders, `evals/release-risk/`.

## File coinvolti

Creazione:
- `skills/siae-release-risk/` (dir)
- `skills/siae-release-risk/reference/` (dir)
- `lib/release_risk/` (dir)
- `evals/release-risk/` (dir)

## Step

### Step 1 — Crea dir skills

Run:
```bash
mkdir -p skills/siae-release-risk/reference
mkdir -p lib/release_risk
mkdir -p evals/release-risk
```

### Step 2 — Crea __init__.py vuoto

Write `lib/release_risk/__init__.py`:
```python
"""lib/release_risk — Release risk assessment framework.

18-criteri pre-deploy risk scoring (0-36) con livelli LOW/MEDIUM/HIGH/CRITICAL.
Vedi docs/plans/2026-05-14-siae-release-risk-design.md per architettura completa.
"""
```

### Step 3 — Verifica struttura

Run:
```bash
tree skills/siae-release-risk lib/release_risk evals/release-risk -L 2
```
Output atteso:
```
skills/siae-release-risk
├── reference
lib/release_risk
└── __init__.py
evals/release-risk
```

### Step 4 — Commit scaffold

Run:
```bash
git add skills/siae-release-risk lib/release_risk evals/release-risk
git commit -m "feat(release-risk): scaffold directory structure"
```

## Criteri di accettazione

- [ ] 4 directory create
- [ ] `__init__.py` scritto con docstring
- [ ] Verifica `tree` mostra struttura corretta
- [ ] Commit eseguito
