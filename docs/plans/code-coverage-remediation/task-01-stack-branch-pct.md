# Task 01 — `pre_existing_branch_pct` in stack.json

**Goal:** `stack.json` espone `pre_existing_branch_pct` e `line_branch_delta` leggendo `coverage/coverage-summary.json` (formato V8/Istanbul, identico Vitest e Jest). Oggi si legge solo la line coverage → la skill è cieca sulla branch fin dall'inizio.

**WS:** WS-1 · **Dipendenze:** nessuna (prerequisito di Task 06 e Task 17).

## File coinvolti
- Modifica: `skills/code-coverage/scripts/detect_stack.py` (nuova funzione + main + dict default riga ~827)
- Modifica: `skills/code-coverage/lib/phase1-discover.sh` (estrazione branch pct in stack.json)
- Modifica: `skills/code-coverage/lib/state-schema.json` (2 campi nuovi)
- Crea: `skills/code-coverage/scripts/tests/test_detect_stack_branch.py`

## Step TDD

### Step 1 — Scrivi il test fallente
Crea `skills/code-coverage/scripts/tests/test_detect_stack_branch.py`:

```python
import json
from pathlib import Path
import detect_stack


def _write_summary(tmp_path: Path, lines_pct: float, branches_pct: float) -> Path:
    cov = tmp_path / "coverage"
    cov.mkdir(parents=True, exist_ok=True)
    summary = {
        "total": {
            "lines": {"total": 100, "covered": int(lines_pct), "pct": lines_pct},
            "branches": {"total": 100, "covered": int(branches_pct), "pct": branches_pct},
            "functions": {"total": 10, "covered": 6, "pct": 60.0},
            "statements": {"total": 100, "covered": int(lines_pct), "pct": lines_pct},
        }
    }
    p = cov / "coverage-summary.json"
    p.write_text(json.dumps(summary), encoding="utf-8")
    return p


def test_parse_branch_from_summary(tmp_path):
    _write_summary(tmp_path, 59.08, 42.31)
    line_pct, branch_pct = detect_stack.parse_coverage_summary_for_branch(tmp_path)
    assert line_pct == 59.08
    assert branch_pct == 42.31


def test_branch_zero_treated_as_unavailable(tmp_path):
    # V8 a volte riporta branches.pct=0 anche se line>0 → branch non disponibile
    _write_summary(tmp_path, 80.0, 0.0)
    line_pct, branch_pct = detect_stack.parse_coverage_summary_for_branch(tmp_path)
    assert line_pct == 80.0
    assert branch_pct == 0.0  # il caller interpreta 0 come "non disponibile"


def test_missing_summary_returns_zeros(tmp_path):
    line_pct, branch_pct = detect_stack.parse_coverage_summary_for_branch(tmp_path)
    assert (line_pct, branch_pct) == (0.0, 0.0)
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_detect_stack_branch.py -v`
Output atteso: `AttributeError: module 'detect_stack' has no attribute 'parse_coverage_summary_for_branch'` (3 FAILED).

### Step 3 — Implementa
In `skills/code-coverage/scripts/detect_stack.py`, **dopo** la funzione `parse_lcov_info` (termina riga ~771), aggiungi:

```python
def parse_coverage_summary_for_branch(repo_path: Path) -> tuple[float, float]:
    """Legge coverage/coverage-summary.json (formato V8/Istanbul).

    Returns (line_pct, branch_pct). (0.0, 0.0) se non disponibile.
    Cerca prima sotto manifest_root/coverage, poi sotto repo/coverage.
    """
    candidates = [
        repo_path / "coverage" / "coverage-summary.json",
    ]
    # sub-workspace: prova anche manifest_root/coverage
    try:
        mr = detect_manifest_root(repo_path)
        if mr and mr != ".":
            candidates.insert(0, repo_path / mr / "coverage" / "coverage-summary.json")
    except Exception:
        pass
    for candidate in candidates:
        try:
            data = json.loads(candidate.read_text(encoding="utf-8", errors="ignore"))
            total = data.get("total", {})
            line_pct = float(total.get("lines", {}).get("pct", 0) or 0)
            branch_pct = float(total.get("branches", {}).get("pct", 0) or 0)
            if line_pct > 0:
                return round(line_pct, 2), round(branch_pct, 2)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return 0.0, 0.0
```

In `main()` (dopo il blocco lcov/jacoco, intorno a riga 879, **prima** del `payload = {...}` finale), aggiungi:

```python
    # Branch coverage pre-esistente (V8/Istanbul summary)
    cov_line, cov_branch = parse_coverage_summary_for_branch(root)
    if cov_line > 0 and pre_existing_source == "missing":
        pre_existing_pct = cov_line
        pre_existing_source = "local_report"
    pre_existing_branch_pct = cov_branch
    # delta None se branch non disponibile (0 con line>0 = V8 non conta i branch)
    line_branch_delta = (
        round(pre_existing_pct - pre_existing_branch_pct, 2)
        if pre_existing_branch_pct > 0 else None
    )
```

Aggiungi al dizionario `payload` finale di `main()` le due chiavi:
```python
        "pre_existing_branch_pct": pre_existing_branch_pct,
        "line_branch_delta": line_branch_delta,
```

Aggiungi al dict default (riga ~827, dove c'è `"pre_existing_coverage_pct": 0.0,`):
```python
    "pre_existing_branch_pct": 0.0,
    "line_branch_delta": None,
```

In `lib/state-schema.json`, nella sezione che descrive `stack.json`, aggiungi le due proprietà (nullable): `pre_existing_branch_pct` (number, default 0.0) e `line_branch_delta` (number|null, default null). Cerca il blocco `"stack.json"` e aggiungi le chiavi sotto `properties`.

In `lib/phase1-discover.sh` non serve modifica se `detect_stack.py` scrive già `stack.json` completo. Verifica che lo step che invoca `detect_stack.py` rediriga su `.code-coverage/stack.json` — se sì, i nuovi campi compaiono automaticamente.

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_detect_stack_branch.py -v`
Output atteso: `3 passed`.
Run regression: `python3 -m pytest scripts/tests/test_detect_stack_ext.py -v` → atteso `passed` (nessuna regressione).

### Step 5 — Commit
```
git add skills/code-coverage/scripts/detect_stack.py skills/code-coverage/lib/state-schema.json skills/code-coverage/scripts/tests/test_detect_stack_branch.py
git commit -m "feat(code-coverage): expose pre_existing_branch_pct + line_branch_delta in stack.json"
```

## Criteri di accettazione
- [ ] `parse_coverage_summary_for_branch` ritorna `(59.08, 42.31)` per il summary di esempio.
- [ ] `branches.pct=0` con `lines.pct>0` ritorna branch=0.0 (il caller lo tratta come non-disponibile via `line_branch_delta=None`).
- [ ] Summary assente → `(0.0, 0.0)`, `line_branch_delta=None`.
- [ ] `stack.json` contiene `pre_existing_branch_pct` e `line_branch_delta`.
- [ ] `test_detect_stack_ext.py` continua a passare.
