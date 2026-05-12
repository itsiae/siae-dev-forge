# Task 15 — Docs: ENV_VARS + CHANGELOG + .gitignore + README

**SP:** 1.0 · **AC mappati:** AC #9, AC #10, AC #13, AC #15 · **Dipendenze:** Task 14 · **Wave:** 6

## Goal

Aggiornare documentazione e infrastrutture di repo:
1. `hooks/ENV_VARS.md` — entry per ogni `DEVFORGE_EVIDENCE_*`
2. `CHANGELOG.md` — entry sotto versione corrente
3. `.gitignore` — entry per `.claude/review-evidence/`
4. `README.md` — sezione nuova "Review Evidence Hook" (breve, link al design doc)
5. Doc-sync test che verifica coerenza ENV_VARS.md ↔ codice

## File coinvolti

**Modificare:**
- `hooks/ENV_VARS.md`
- `CHANGELOG.md`
- `.gitignore`
- `README.md`

**Creare:**
- `tests/test_env_vars_doc_sync.py`

## Step TDD

### Step 1 — Test doc-sync (fallisce inizialmente)

`tests/test_env_vars_doc_sync.py`:

```python
"""Verify that every DEVFORGE_EVIDENCE_* env var referenced in code is
documented in hooks/ENV_VARS.md, and vice versa."""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

EXPECTED_VARS = {
    "DEVFORGE_EVIDENCE_MIN_COVERAGE",
    "DEVFORGE_EVIDENCE_MAX_COVERAGE_DELTA",
    "DEVFORGE_EVIDENCE_MAX_LINT_ERRORS",
    "DEVFORGE_EVIDENCE_MAX_COMPLEXITY",
    "DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL",
    "DEVFORGE_EVIDENCE_SPEC_DRIFT_BLOCK",
    "DEVFORGE_EVIDENCE_DESIGN_DOC",
    "DEVFORGE_SKIP_EVIDENCE",
    "DEVFORGE_EVIDENCE_ICLOUD_WARN",
}


def test_env_vars_md_documents_all():
    content = (REPO_ROOT / "hooks" / "ENV_VARS.md").read_text()
    missing = []
    for v in EXPECTED_VARS:
        if v not in content:
            missing.append(v)
    assert not missing, f"Missing from ENV_VARS.md: {missing}"


def test_changelog_has_review_evidence_entry():
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text()
    assert "review-evidence" in changelog.lower() or "review evidence" in changelog.lower()


def test_gitignore_has_review_evidence_dir():
    gitignore = (REPO_ROOT / ".gitignore").read_text()
    assert ".claude/review-evidence/" in gitignore


def test_readme_has_review_evidence_section():
    readme = (REPO_ROOT / "README.md").read_text()
    assert "review-evidence" in readme.lower() or "Review Evidence" in readme
```

### Step 2 — Aggiorna `hooks/ENV_VARS.md`

Aggiungi sezione **dopo** "Per-gate bypass (tracked)" (o equivalente):

```markdown
## Review Evidence (v1.54+)

| Env var | Default | Significato |
|---|---|---|
| `DEVFORGE_EVIDENCE_MIN_COVERAGE` | `60` | Coverage % sotto cui block |
| `DEVFORGE_EVIDENCE_MAX_COVERAGE_DELTA` | `-5` | Delta vs base sotto cui block (pp) |
| `DEVFORGE_EVIDENCE_MAX_LINT_ERRORS` | `0` | Lint errors sopra cui block |
| `DEVFORGE_EVIDENCE_MAX_COMPLEXITY` | `15` | Max cyclomatic per funzione |
| `DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL` | `critical` | `critical` / `high` / `off` per findings SARIF CI |
| `DEVFORGE_EVIDENCE_SPEC_DRIFT_BLOCK` | `1` | Block se drift_severity == high |
| `DEVFORGE_EVIDENCE_DESIGN_DOC` | (auto) | Override path design doc (default: file più recente in docs/plans/) |
| `DEVFORGE_SKIP_EVIDENCE` | `0` | Bypass fallback. Preferito: `touch ~/.claude/.devforge-skip-evidence` (state file più affidabile in subprocess hook). Tracked, abuse log a 5/day. |
| `DEVFORGE_EVIDENCE_ICLOUD_WARN` | `1` | Emit warning se repo in iCloudDocs (atomic rename fragile) |

**State file bypass primario:** `~/.claude/.devforge-skip-evidence` — l'hook
controlla l'esistenza del file PRIMA di compute. Il file può contenere
`N=<count>` per auto-decremento. Pattern raccomandato vs env var perché le
env var possono non propagare a subprocess hook Claude Code.

**Pattern operativo CI:** vedi `commands/forge-evidence.md` per il flow
`gh pr create` → CI completes → `gh pr edit` per pickup SARIF.
```

### Step 3 — Aggiorna `CHANGELOG.md`

Aggiungi entry sotto la versione di sviluppo corrente (controlla l'header esistente):

```markdown
## [Unreleased] / v1.54.0

### Added

- **Review Evidence Hook (`hooks/review-evidence`)** — pre-calcola in modo deterministico
  coverage, lint, complessità ciclomatica, CI quality reports SARIF e spec-drift per
  ogni SHA. Scrive evidence cacheable in `.claude/review-evidence/<sha>.json`.
  Consumato come renderer da `code-reviewer` e `spec-reviewer` (nuovo Step 0.5
  evidence-loading) per verdetti riproducibili allineati a CI.
- **Multi-stack collector framework** (`lib/review_evidence/`): Java (jacoco+checkstyle+pmd),
  TypeScript (lcov+eslint+complexity-report), Python (coverage.py+ruff+radon),
  HCL (tflint+terraform validate).
- **CI-fetch SARIF parser** tool-agnostic (Qodana, SonarQube, CodeQL — qualsiasi tool che emetta SARIF 2.1.0).
- **Spec-drift detector** con code-fence robustness (estrae path solo da sezioni
  allowlist del design doc, ignora code-fence / inline code / blockquote).
- **Hard-block soglie** configurabili via env var (`DEVFORGE_EVIDENCE_*`) + bypass
  primario via state file `~/.claude/.devforge-skip-evidence`.
- Skill `/forge-evidence` (`commands/forge-evidence.md`) per invocazione on-demand.

### Changed

- `agents/code-reviewer.md`, `agents/spec-reviewer.md`: aggiunto Step 0.5
  evidence-loading prima del 6-punti / spec analysis.
- `hooks/hooks.json`: review-evidence registrato in PreToolUse Bash (su `gh pr create|edit`)
  e PostToolUse Bash (async cache warm su commit).

### Docs

- `hooks/ENV_VARS.md`: documentate 9 nuove env var `DEVFORGE_EVIDENCE_*`.
- `.gitignore`: aggiunto `.claude/review-evidence/`.
```

### Step 4 — Aggiorna `.gitignore`

Aggiungi dopo le entries esistenti (es. dopo `.pytest_cache/`):

```
# Review evidence cache (per-SHA, deterministically computed by hooks/review-evidence)
.claude/review-evidence/
```

### Step 5 — Aggiorna `README.md`

Aggiungi sezione nuova (cerca un buon punto, ad es. dopo la lista hook esistente):

```markdown
### Review Evidence Hook

`hooks/review-evidence` pre-calcola in modo deterministico i segnali di qualità
(coverage, lint, complessità ciclomatica, CI SARIF, spec-drift) per il SHA
corrente. Il risultato è scritto in `.claude/review-evidence/<sha>.json` e
consumato come ground-truth dagli agent di code review (`code-reviewer`,
`spec-reviewer`).

**Trigger:**
- `PreToolUse` Bash su `gh pr create|edit` → sync compute, hard-block su soglie
- `PostToolUse` Bash su commit → async cache warm
- Skill `/forge-evidence` → on-demand

**Design:** `docs/plans/2026-05-12-review-evidence-hook-design.md`

**Stack supportati:** Java (jacoco + checkstyle + pmd), TypeScript (lcov +
eslint + complexity-report), Python (coverage.py + ruff + radon), HCL (tflint
+ terraform validate). CI reports: parser SARIF 2.1.0 generico (Qodana,
SonarQube, CodeQL, qualsiasi tool che emetta SARIF).
```

### Step 6 — Esegui test e commit

```bash
pytest tests/test_env_vars_doc_sync.py -v
# 4 passed

git add hooks/ENV_VARS.md CHANGELOG.md .gitignore README.md \
        tests/test_env_vars_doc_sync.py
git commit -m "docs(review-evidence): ENV_VARS + CHANGELOG + .gitignore + README + doc-sync test (#task-15)"
```

### Step 7 — Verifica finale: tutte le test suites passano

```bash
pytest tests/ -q --tb=short
# tutti i nuovi test passano
# tutti gli esistenti passano (no-regression)
```

## Criteri di accettazione

- [ ] `hooks/ENV_VARS.md` documenta 9 env var `DEVFORGE_EVIDENCE_*`
- [ ] `CHANGELOG.md` ha entry "Review Evidence Hook" sotto unreleased
- [ ] `.gitignore` contiene `.claude/review-evidence/`
- [ ] `README.md` ha sezione "Review Evidence Hook"
- [ ] 4 doc-sync test passano
- [ ] Full test suite green (no regression)
