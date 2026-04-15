# Task 01 — Scaffold v2

**Goal:** Struttura moduli v2 + requirements aggiornati + SKILL.md v2.
**AC coperti:** AC01, AC02 (base), AC-MACRO-1 (scaffold)
**Dipendenze:** nessuna (primo task)
**Effort:** ~15 min
**Test nuovi:** 2

## File da creare/modificare

- `skills/siae-dev-analytics/scripts/requirements.txt` — append: hypothesis>=6.80, mutmut>=2.4, typeguard>=4.1, anthropic>=0.25, pytz>=2024.1
- `skills/siae-dev-analytics/scripts/__init__.py` — mantieni
- `skills/siae-dev-analytics/scripts/collect_anthropic_api.py` (nuovo, stub)
- `skills/siae-dev-analytics/scripts/compute_ai_impact.py` (nuovo, stub)
- `skills/siae-dev-analytics/scripts/compute_branches.py` (nuovo, stub)
- `skills/siae-dev-analytics/scripts/compute_reviews.py` (nuovo, stub)
- `skills/siae-dev-analytics/scripts/seasonality.py` (nuovo, stub)
- `skills/siae-dev-analytics/scripts/export_charts.py` (nuovo, stub)
- `skills/siae-dev-analytics/scripts/export_glossary.py` (nuovo, stub)
- `skills/siae-dev-analytics/scripts/validators.py` (nuovo, stub)
- `skills/siae-dev-analytics/reference/kpi-glossary-data.yaml` (nuovo, stub con header)
- `skills/siae-dev-analytics/reference/robustness-policy.md` (nuovo, copia NF1-NF30 da design §3)
- `skills/siae-dev-analytics/reference/seasonality-it.md` (nuovo, calendario festività IT)
- `skills/siae-dev-analytics/template/devforge-analytics-dual.yml` (nuovo, template dual-window)
- `skills/siae-dev-analytics/SKILL.md` — aggiorna trigger + flow v2 (riferimento §7 design)
- `skills/siae-dev-analytics/tests/test_scaffold_v2.py` (nuovo, 2 test)

## Step 1 — Append requirements.txt

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/skills/siae-dev-analytics"
cat >> scripts/requirements.txt <<'EOF'

# v2 additions
hypothesis>=6.80
mutmut>=2.4
typeguard>=4.1
anthropic>=0.25
pytz>=2024.1
EOF
```

## Step 2 — Crea stub moduli (9 file)

Ogni stub è:
```python
"""<Module>: <one-line purpose>.

Docstring modulo v2 siae-dev-analytics. Popolato nei task successivi.
"""
from __future__ import annotations

__all__: list[str] = []
```

File da creare con questo contenuto minimo: `collect_anthropic_api.py`, `compute_ai_impact.py`, `compute_branches.py`, `compute_reviews.py`, `seasonality.py`, `export_charts.py`, `export_glossary.py`, `validators.py`.

## Step 3 — SKILL.md v2 update

Nel SKILL.md esistente, aggiorna la sezione Flow e Trigger:

- Trigger aggiuntivi: "AI Impact report", "before/after Claude Code", "branch analytics", "WIP dev"
- Flow Step 4 aggiungi: "IF dual_window: loop baseline + current"
- Prerequisiti aggiungi: AWS_PROFILE=siae-dev-forge (opz) o ANTHROPIC_API_KEY env var per cost

## Step 4 — Reference docs stub

### `reference/robustness-policy.md`
Copia §3 del design doc (NF1-NF30) nel file.

### `reference/seasonality-it.md`
```markdown
# Seasonality Italia — Festività hardcoded

Festività nazionali italiane (calendario fisso + variabili):
- 1 gennaio (Capodanno)
- 6 gennaio (Epifania)
- Pasqua + Pasquetta (variabile, calcolo algoritmo)
- 25 aprile (Liberazione)
- 1 maggio (Lavoro)
- 2 giugno (Repubblica)
- 15 agosto (Ferragosto)
- 1 novembre (Ognissanti)
- 8 dicembre (Immacolata)
- 25-26 dicembre (Natale + Santo Stefano)

Agosto: reduced-activity heuristic, moltiplicatore 0.5 sul throughput atteso (2-3 settimane ferie).
```

### `reference/kpi-glossary-data.yaml`
```yaml
# Source of truth per sheet Glossario KPI.
# Popolato in task-11.
version: 1
kpi: []
```

### `template/devforge-analytics-dual.yml`
```yaml
version: 2
scope:
  repos: [itsiae/example-repo]
time_window:
  baseline: {from: "2026-01-01", to: "2026-02-14"}
  current:  {from: "2026-02-15", to: "today"}
  enable_ai_impact: true
developers:
  exclude: ["dependabot[bot]", "renovate[bot]"]
options:
  anonymize: false
  min_commits_threshold: 5
  parallel_fetch: 4
  enable_branch_tracking: true
  enable_review_tracking: true
  enable_cost_metrics: true
  anthropic_org_id: null
  cost_per_dev_override: {}
output:
  format: xlsx
  path: ./devforge-analytics-report.xlsx
```

## Step 5 — Test scaffold

Crea `tests/test_scaffold_v2.py`:

```python
"""Verifica presenza moduli v2 + import senza errori."""
import importlib

V2_MODULES = [
    "collect_anthropic_api",
    "compute_ai_impact",
    "compute_branches",
    "compute_reviews",
    "seasonality",
    "export_charts",
    "export_glossary",
    "validators",
]


def test_all_v2_modules_importable():
    """Ogni modulo v2 si importa senza errori."""
    for mod_name in V2_MODULES:
        mod = importlib.import_module(mod_name)
        assert mod is not None, f"Import fallito per {mod_name}"


def test_requirements_includes_v2_deps():
    """requirements.txt contiene le 5 dipendenze v2."""
    from pathlib import Path
    req_path = Path(__file__).parent.parent / "scripts" / "requirements.txt"
    content = req_path.read_text()
    for dep in ["hypothesis", "mutmut", "typeguard", "anthropic", "pytz"]:
        assert dep in content, f"Missing dep: {dep}"
```

## Step 6 — Run test

```bash
cd skills/siae-dev-analytics
PYTHONPATH=scripts python3 -m pytest tests/test_scaffold_v2.py -v
```

Output atteso: `2 passed`.

## Criteri accettazione

- [ ] 8 stub moduli v2 creati
- [ ] requirements.txt con 5 deps nuove
- [ ] SKILL.md aggiornato con trigger + flow v2
- [ ] 3 reference docs creati (robustness-policy, seasonality-it, kpi-glossary-data.yaml)
- [ ] template devforge-analytics-dual.yml creato
- [ ] 2 test pass
