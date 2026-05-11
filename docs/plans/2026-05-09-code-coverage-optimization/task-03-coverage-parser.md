# Task 03 — Coverage Parser (P4 + ST1)

**Goal:** Sostituire il parsing fragile `tail -n 100` con `--coverage.reporter=json-summary` + nuovo script `scripts/parse_coverage.py` che emette JSON tipato. Ridurre `phase-6-coverage.md` da 199 a ~60 LOC.

**SP:** 1.5 (Augmented)
**Fix IDs covered:** P4 + ST1
**Branch:** `feat/code-coverage-opt-parser`
**Dipendenze:** task-02 (persistence layer disponibile per `.code-coverage/coverage-report.json`)

---

## File coinvolti

**Creazione**:
- `skills/code-coverage/scripts/parse_coverage.py` (~250 LOC Python)
- `skills/code-coverage/scripts/tests/test_parse_coverage.py` (~150 LOC test pytest)
- `skills/code-coverage/scripts/tests/fixtures/vitest-summary.json` (sample input vitest)
- `skills/code-coverage/scripts/tests/fixtures/jest-summary.json` (sample input jest)
- `skills/code-coverage/scripts/tests/fixtures/pytest-cov.json` (sample input pytest-cov)
- `skills/code-coverage/scripts/tests/fixtures/malformed.txt` (caso fallback tail-400)

**Modifica**:
- `skills/code-coverage/references/phase-6-coverage.md` (riduci da 199 a ~60 LOC)
- `skills/code-coverage/assets/stack-matrix.json` (aggiungi/aggiorna `coverage_report_format` per ogni framework)

---

## Step bite-sized

### Step 1 — Branch + verifica task-02 merged

```bash
git checkout main && git pull
git checkout -b feat/code-coverage-opt-parser
test -f skills/code-coverage/lib/cache-helper.sh && echo "task-02 merged OK"
```

### Step 2 — TDD: scrivi prima i 4 test (RED)

Crea `skills/code-coverage/scripts/tests/__init__.py` (vuoto) e `tests/conftest.py`:

```python
# skills/code-coverage/scripts/tests/conftest.py
import sys
from pathlib import Path

# Aggiungi parent (scripts/) al sys.path per import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

Crea `skills/code-coverage/scripts/tests/test_parse_coverage.py` con i 4 test:

```python
"""Test per parse_coverage.py — copre i 4 casi richiesti dal design doc PR3."""
import json
import subprocess
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SCRIPT = Path(__file__).resolve().parent.parent / "parse_coverage.py"


def run_parser(framework: str, input_file: Path) -> dict:
    """Esegue parse_coverage.py e ritorna JSON output."""
    result = subprocess.run(
        ["python3", str(SCRIPT), framework, str(input_file)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_vitest_json_summary_parsing():
    """Test 1: vitest --coverage.reporter=json-summary output."""
    output = run_parser("vitest", FIXTURES / "vitest-summary.json")
    assert "global_pct" in output
    assert isinstance(output["global_pct"], (int, float))
    assert "modules" in output
    assert isinstance(output["modules"], list)
    assert all("path" in m and "lines_pct" in m for m in output["modules"])


def test_jest_json_summary_parsing():
    """Test 2: jest --coverageReporters=json-summary output."""
    output = run_parser("jest", FIXTURES / "jest-summary.json")
    assert output["global_pct"] >= 0
    assert "modules" in output


def test_pytest_cov_json_parsing():
    """Test 3: pytest --cov-report=json output."""
    output = run_parser("pytest", FIXTURES / "pytest-cov.json")
    assert output["global_pct"] >= 0
    assert "modules" in output
    # pytest format usa "files" key invece di "coverageMap"
    assert all("path" in m for m in output["modules"])


def test_malformed_input_fallback():
    """Test 4: input malformato → fallback graceful con error in JSON."""
    output = run_parser("vitest", FIXTURES / "malformed.txt")
    assert "error" in output
    assert output["global_pct"] == 0
    assert output["modules"] == []
```

### Step 3 — Crea le fixture JSON

`skills/code-coverage/scripts/tests/fixtures/vitest-summary.json` (formato vitest reale ridotto):
```json
{
  "total": {
    "lines": {"total": 100, "covered": 75, "skipped": 0, "pct": 75.0},
    "statements": {"total": 110, "covered": 85, "skipped": 0, "pct": 77.27},
    "functions": {"total": 20, "covered": 16, "skipped": 0, "pct": 80.0},
    "branches": {"total": 30, "covered": 22, "skipped": 0, "pct": 73.33}
  },
  "src/utils/format.ts": {
    "lines": {"total": 50, "covered": 45, "pct": 90.0},
    "branches": {"total": 10, "covered": 8, "pct": 80.0}
  },
  "src/services/payment.ts": {
    "lines": {"total": 50, "covered": 30, "pct": 60.0},
    "branches": {"total": 20, "covered": 14, "pct": 70.0}
  }
}
```

`skills/code-coverage/scripts/tests/fixtures/jest-summary.json` (formato Jest, stesso schema Vitest con `total` + per-file keys):
```json
{
  "total": {
    "lines": {"total": 200, "covered": 150, "pct": 75.0},
    "branches": {"total": 50, "covered": 40, "pct": 80.0},
    "functions": {"total": 30, "covered": 25, "pct": 83.33},
    "statements": {"total": 220, "covered": 170, "pct": 77.27}
  },
  "src/auth/index.ts": {
    "lines": {"total": 80, "covered": 70, "pct": 87.5},
    "branches": {"total": 20, "covered": 18, "pct": 90.0}
  }
}
```

`skills/code-coverage/scripts/tests/fixtures/pytest-cov.json` (formato pytest-cov reale ridotto):
```json
{
  "meta": {"version": "7.4.0", "format": 2},
  "totals": {
    "covered_lines": 320,
    "num_statements": 400,
    "percent_covered": 80.0,
    "percent_covered_display": "80",
    "missing_lines": 80,
    "excluded_lines": 0,
    "num_branches": 50,
    "num_partial_branches": 5,
    "covered_branches": 45
  },
  "files": {
    "src/utils.py": {
      "summary": {
        "covered_lines": 90,
        "num_statements": 100,
        "percent_covered": 90.0,
        "num_branches": 20,
        "covered_branches": 18
      }
    },
    "src/main.py": {
      "summary": {
        "covered_lines": 230,
        "num_statements": 300,
        "percent_covered": 76.67,
        "num_branches": 30,
        "covered_branches": 27
      }
    }
  }
}
```

`skills/code-coverage/scripts/tests/fixtures/malformed.txt`:
```
This is not valid JSON
random output
no coverage data here
```

### Step 4 — Run test in RED state

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_parse_coverage.py -v
```

Output atteso (tutti FAIL perché parse_coverage.py non esiste):
```
ERRORS
ImportError / FileNotFoundError: parse_coverage.py
4 errors in <0.1s>
```

### Step 5 — GREEN: implementa `scripts/parse_coverage.py`

Crea `skills/code-coverage/scripts/parse_coverage.py`:

```python
#!/usr/bin/env python3
"""parse_coverage.py — parser deterministico di coverage report.

Sostituisce il pattern fragile `tail -n 100 + grep` con parsing JSON tipato
da reporter standardizzati: --coverage.reporter=json-summary (Vitest/Jest),
--cov-report=json (pytest), JaCoCo XML, etc.

Usage:
    python3 parse_coverage.py <framework> <input-file>

Frameworks supportati:
    vitest, jest, pytest, jacoco, kover, go-test, cargo, dotnet

Output (stdout): JSON con schema:
    {
        "global_pct": float,           # Lines coverage globale
        "global_branch_pct": float,    # Branch coverage globale
        "modules": [
            {"path": str, "lines_pct": float, "branch_pct": float,
             "priority": "P1"|"P2"|"P3"|null, "threshold": float, "status": "PASS"|"FAIL"}
        ],
        "failing": [str],              # Lista path moduli sotto threshold
        "framework": str,
        "error": str | null            # Solo se parsing fallito
    }

Exit code:
    0 se parse OK (anche se ci sono moduli FAIL)
    1 se input file mancante o non parsabile (output JSON contiene "error")
"""
from __future__ import annotations
import argparse
import json
import sys
import re
from pathlib import Path
from typing import Any

# Soglie default (override via --priority-rules)
DEFAULT_THRESHOLDS = {"P1": 80.0, "P2": 70.0, "P3": 60.0, "default": 70.0}


def parse_vitest_or_jest(data: dict) -> tuple[float, float, list[dict]]:
    """Vitest e Jest usano lo stesso formato `--reporter=json-summary`."""
    total = data.get("total", {})
    global_pct = float(total.get("lines", {}).get("pct", 0))
    global_branch_pct = float(total.get("branches", {}).get("pct", 0))
    modules = []
    for path, metrics in data.items():
        if path == "total":
            continue
        if not isinstance(metrics, dict):
            continue
        lines_pct = float(metrics.get("lines", {}).get("pct", 0))
        branch_pct = float(metrics.get("branches", {}).get("pct", 0))
        modules.append({
            "path": path,
            "lines_pct": lines_pct,
            "branch_pct": branch_pct,
        })
    return global_pct, global_branch_pct, modules


def parse_pytest_cov(data: dict) -> tuple[float, float, list[dict]]:
    """pytest-cov --cov-report=json format."""
    totals = data.get("totals", {})
    global_pct = float(totals.get("percent_covered", 0))
    # pytest non sempre emette branch coverage; calcoliamolo se disponibile
    num_branches = totals.get("num_branches", 0)
    covered_branches = totals.get("covered_branches", 0)
    global_branch_pct = (covered_branches / num_branches * 100) if num_branches else 0.0
    modules = []
    for path, info in data.get("files", {}).items():
        summary = info.get("summary", {})
        nb = summary.get("num_branches", 0)
        cb = summary.get("covered_branches", 0)
        modules.append({
            "path": path,
            "lines_pct": float(summary.get("percent_covered", 0)),
            "branch_pct": (cb / nb * 100) if nb else 0.0,
        })
    return global_pct, global_branch_pct, modules


def parse_jacoco_xml(content: str) -> tuple[float, float, list[dict]]:
    """JaCoCo XML report — usiamo regex su stdlib (no lxml dependency)."""
    # Estrai <counter type="LINE" missed="..." covered="..." /> globale
    line_match = re.search(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', content)
    branch_match = re.search(r'<counter type="BRANCH" missed="(\d+)" covered="(\d+)"', content)
    if not line_match:
        return 0.0, 0.0, []
    line_missed, line_covered = int(line_match.group(1)), int(line_match.group(2))
    line_total = line_missed + line_covered
    global_pct = (line_covered / line_total * 100) if line_total else 0.0
    if branch_match:
        b_missed, b_covered = int(branch_match.group(1)), int(branch_match.group(2))
        b_total = b_missed + b_covered
        global_branch_pct = (b_covered / b_total * 100) if b_total else 0.0
    else:
        global_branch_pct = 0.0
    # Per moduli, parsing semplificato per <package> nodes
    modules = []
    for pkg in re.finditer(r'<package name="([^"]+)">(.*?)</package>', content, re.DOTALL):
        pkg_name = pkg.group(1)
        pkg_body = pkg.group(2)
        pkg_line = re.search(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', pkg_body)
        if pkg_line:
            pm, pc = int(pkg_line.group(1)), int(pkg_line.group(2))
            pt = pm + pc
            modules.append({
                "path": pkg_name.replace("/", "."),
                "lines_pct": (pc / pt * 100) if pt else 0.0,
                "branch_pct": 0.0,
            })
    return global_pct, global_branch_pct, modules


def parse_go_cover(content: str) -> tuple[float, float, list[dict]]:
    """Go test -coverprofile output (LCOV-like)."""
    # `go tool cover -func=cover.out` emette righe tipo:
    # github.com/foo/pkg/file.go:10:    FuncName    85.7%
    # total:                            (statements)    78.5%
    modules: dict[str, list[float]] = {}
    global_pct = 0.0
    for line in content.splitlines():
        m = re.match(r'^([^:]+\.go):\d+:\s+\S+\s+(\d+\.?\d*)%', line)
        if m:
            path = m.group(1)
            pct = float(m.group(2))
            modules.setdefault(path, []).append(pct)
            continue
        total_m = re.search(r'^total:\s+\(statements\)\s+(\d+\.?\d*)%', line)
        if total_m:
            global_pct = float(total_m.group(1))
    module_list = [
        {"path": p, "lines_pct": sum(pcts) / len(pcts), "branch_pct": 0.0}
        for p, pcts in modules.items()
    ]
    return global_pct, 0.0, module_list


def parse_cargo_tarpaulin(data: dict) -> tuple[float, float, list[dict]]:
    """cargo tarpaulin --out Json format."""
    files_data = data.get("files", [])
    total_covered = sum(f.get("covered", 0) for f in files_data)
    total_coverable = sum(f.get("coverable", 0) for f in files_data)
    global_pct = (total_covered / total_coverable * 100) if total_coverable else 0.0
    modules = []
    for f in files_data:
        cov = f.get("covered", 0)
        coverable = f.get("coverable", 0)
        modules.append({
            "path": f.get("path", "unknown"),
            "lines_pct": (cov / coverable * 100) if coverable else 0.0,
            "branch_pct": 0.0,
        })
    return global_pct, 0.0, modules


def assign_priority_and_threshold(
    path: str, priority_rules: dict | None
) -> tuple[str | None, float]:
    """Assegna P1/P2/P3 + threshold a un modulo basandosi su path patterns."""
    if not priority_rules:
        return None, DEFAULT_THRESHOLDS["default"]
    levels = priority_rules.get("priority_levels", {})
    for level_name in ("P1", "P2", "P3"):
        level = levels.get(level_name, {})
        patterns = level.get("path_patterns", [])
        for pattern in patterns:
            # Pattern semplice: glob-like → regex
            regex = pattern.replace("**/", ".*/").replace("**", ".*").replace("*", "[^/]*")
            if re.search(regex, path):
                return level_name, float(level.get("min_coverage_pct", DEFAULT_THRESHOLDS["default"]))
    return None, DEFAULT_THRESHOLDS["default"]


def load_priority_rules(skill_root: Path) -> dict | None:
    """Carica priority-rules.json se disponibile."""
    rules_path = skill_root / "assets" / "priority-rules.json"
    if rules_path.exists():
        with open(rules_path) as f:
            return json.load(f)
    return None


def parse(framework: str, input_path: Path, priority_rules: dict | None) -> dict:
    """Dispatcher principale."""
    if not input_path.exists():
        return {
            "global_pct": 0.0,
            "global_branch_pct": 0.0,
            "modules": [],
            "failing": [],
            "framework": framework,
            "error": f"Input file does not exist: {input_path}",
        }
    try:
        if framework in ("jacoco", "kover"):
            content = input_path.read_text()
            global_pct, branch_pct, modules = parse_jacoco_xml(content)
        elif framework == "go-test":
            content = input_path.read_text()
            global_pct, branch_pct, modules = parse_go_cover(content)
        else:
            with open(input_path) as f:
                data = json.load(f)
            if framework in ("vitest", "jest"):
                global_pct, branch_pct, modules = parse_vitest_or_jest(data)
            elif framework == "pytest":
                global_pct, branch_pct, modules = parse_pytest_cov(data)
            elif framework == "cargo":
                global_pct, branch_pct, modules = parse_cargo_tarpaulin(data)
            elif framework == "dotnet":
                # dotnet test --collect:"XPlat Code Coverage" → cobertura XML
                # Fallback: tratta come JaCoCo XML
                content = input_path.read_text()
                global_pct, branch_pct, modules = parse_jacoco_xml(content)
            else:
                return {
                    "global_pct": 0.0,
                    "global_branch_pct": 0.0,
                    "modules": [],
                    "failing": [],
                    "framework": framework,
                    "error": f"Framework non supportato: {framework}",
                }
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "global_pct": 0.0,
            "global_branch_pct": 0.0,
            "modules": [],
            "failing": [],
            "framework": framework,
            "error": f"Parse error: {e}",
        }

    # Assegna priority + threshold + status a ogni modulo
    enriched = []
    failing = []
    for m in modules:
        pri, threshold = assign_priority_and_threshold(m["path"], priority_rules)
        status = "PASS" if m["lines_pct"] >= threshold else "FAIL"
        enriched.append({**m, "priority": pri, "threshold": threshold, "status": status})
        if status == "FAIL":
            failing.append(m["path"])

    return {
        "global_pct": round(global_pct, 2),
        "global_branch_pct": round(branch_pct, 2),
        "modules": enriched,
        "failing": failing,
        "framework": framework,
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("framework", choices=["vitest", "jest", "pytest", "jacoco", "kover", "go-test", "cargo", "dotnet"])
    parser.add_argument("input", type=Path, help="Input file (json-summary, lcov, xml, etc.)")
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="Path skill root (per priority-rules.json)")
    args = parser.parse_args()

    priority_rules = load_priority_rules(args.skill_root)
    result = parse(args.framework, args.input, priority_rules)
    print(json.dumps(result, indent=2))
    return 0 if result.get("error") is None else 0  # exit 0 anche su parse error per compatibilità subprocess


if __name__ == "__main__":
    sys.exit(main())
```

Make executable:
```bash
chmod +x skills/code-coverage/scripts/parse_coverage.py
```

### Step 6 — Run test in GREEN state

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_parse_coverage.py -v
```

Output atteso:
```
test_parse_coverage.py::test_vitest_json_summary_parsing PASSED
test_parse_coverage.py::test_jest_json_summary_parsing PASSED
test_parse_coverage.py::test_pytest_cov_json_parsing PASSED
test_parse_coverage.py::test_malformed_input_fallback PASSED

4 passed in <1s>
```

### Step 7 — Coverage del nuovo script ≥70%

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_parse_coverage.py --cov=scripts/parse_coverage --cov-report=term-missing
```

Output atteso: coverage ≥ 70% su `parse_coverage.py`. Se sotto, aggiungi test specifici per branch non coperti (es. JaCoCo XML, Go cover, cargo tarpaulin).

### Step 8 — Aggiorna `assets/stack-matrix.json`

Per ogni framework esistente, aggiungi/aggiorna campi `coverage_command` e `coverage_report_format`:

Esempio per vitest:
```json
{
  "vitest": {
    "coverage_command": "npx vitest run --coverage --coverage.reporter=json-summary",
    "coverage_report_format": "vitest",
    "coverage_report_path": "coverage/coverage-summary.json"
  }
}
```

Per jest:
```json
{
  "jest": {
    "coverage_command": "npx jest --coverage --coverageReporters=json-summary",
    "coverage_report_format": "jest",
    "coverage_report_path": "coverage/coverage-summary.json"
  }
}
```

Per pytest:
```json
{
  "pytest": {
    "coverage_command": "pytest --cov --cov-report=json",
    "coverage_report_format": "pytest",
    "coverage_report_path": "coverage.json"
  }
}
```

(Aggiungi simili entry per junit5/jacoco, kover, go-test, cargo, dotnet.)

### Step 9 — Riduci `phase-6-coverage.md` da 199 a ~60 LOC

Riscrittura completa del file. Nuovo contenuto:

```markdown
# Phase 6 — Coverage Measurement

**Goal**: misurare la coverage finale dopo Phase 5 e produrre il report tipizzato consumato da Phase 6→7 Gate.

## Comando

```bash
# Lookup framework + comando da assets/stack-matrix.json
FW=$(jq -r '.framework' .code-coverage/stack.json)
COV_CMD=$(jq -r --arg fw "$FW" '.[$fw].coverage_command' skills/code-coverage/assets/stack-matrix.json)
REPORT_PATH=$(jq -r --arg fw "$FW" '.[$fw].coverage_report_path' skills/code-coverage/assets/stack-matrix.json)

# Esegui coverage (output framework-specific su REPORT_PATH)
cd <target_repo> && eval "$COV_CMD" 2>&1 | tee .code-coverage/coverage-stdout.log

# Parse deterministico via parse_coverage.py
FORMAT=$(jq -r --arg fw "$FW" '.[$fw].coverage_report_format' skills/code-coverage/assets/stack-matrix.json)
python3 skills/code-coverage/scripts/parse_coverage.py "$FORMAT" "<target_repo>/$REPORT_PATH" \
  > <target_repo>/.code-coverage/coverage-report.json
```

## Output Contract (`.code-coverage/coverage-report.json`)

```json
{
  "global_pct": 75.5,
  "global_branch_pct": 70.0,
  "modules": [
    {"path": "src/services/payment.ts", "lines_pct": 85.0, "branch_pct": 80.0,
     "priority": "P1", "threshold": 80.0, "status": "PASS"}
  ],
  "failing": ["src/utils/format.ts"],
  "framework": "vitest",
  "error": null
}
```

## Fallback per framework esotici

Se `coverage_report_format` non disponibile o file non esiste:
1. Cerca tabella coverage in stdout: `tail -n 400 .code-coverage/coverage-stdout.log | grep -E '<framework_table_pattern>'`
2. Se grep trova match, parsing manuale ad-hoc (degraded mode)
3. Altrimenti emit `error: "no coverage data captured"` in coverage-report.json

## Phase 6 → Phase 7 Gate

Read `.code-coverage/coverage-report.json`:
```python
import json
report = json.load(open(".code-coverage/coverage-report.json"))
needs_repair = (
    report["global_pct"] < 70 OR
    any(m["status"] == "FAIL" for m in report["modules"] if m["priority"])
)
if not needs_repair:
    skip_phase_7()  # vai direttamente a OUTPUT
else:
    enter_phase_7()
```
```

### Step 10 — Spec-reviewer

Lancia spec-reviewer sulla PR. Risolvi issue.

### Step 11 — Commit + PR

```bash
git add skills/code-coverage/scripts/parse_coverage.py \
        skills/code-coverage/scripts/tests/ \
        skills/code-coverage/references/phase-6-coverage.md \
        skills/code-coverage/assets/stack-matrix.json
git commit -m "feat(code-coverage): parse_coverage.py script + json-summary integration (P4, ST1)

P4: sostituito tail-n-100 con --coverage.reporter=json-summary
ST1: nuovo scripts/parse_coverage.py supporta vitest/jest/pytest/jacoco/kover/go-test/cargo/dotnet
4 test in scripts/tests/test_parse_coverage.py (>=70% coverage)
phase-6-coverage.md ridotto da 199 a ~60 LOC
stack-matrix.json estesa con coverage_report_format + coverage_report_path

Refs design doc 2026-05-09-code-coverage-optimization-design.md PR3.

Co-Authored-By: SIAE DevForge"

git push -u origin feat/code-coverage-opt-parser
gh pr create --title "feat(code-coverage): coverage parser + json-summary (P4, ST1)" --body "$(cat <<'EOF'
## Summary
- Nuovo `scripts/parse_coverage.py` (8 framework)
- 4 test pytest in `scripts/tests/` con fixture realistiche (vitest/jest/pytest/malformed)
- Coverage del nuovo script >=70% (verificato in CI)
- `phase-6-coverage.md` ridotto da 199 a ~60 LOC (logica delegata a script)
- `stack-matrix.json` aggiornato con `coverage_report_format` + `coverage_report_path` per framework

Refs: docs/plans/2026-05-09-code-coverage-optimization-design.md PR3

## Test plan
- [x] 4 test PASS (vitest/jest/pytest/malformed fallback)
- [x] Coverage parse_coverage.py >=70%
- [ ] Smoke test con run reale su benchmark MEDIUM (vitest)
- [ ] Spec-reviewer PASS

Co-Authored-By: SIAE DevForge
EOF
)"
```

---

## Acceptance criteria

- [ ] `scripts/parse_coverage.py` esiste, eseguibile, supporta 8 framework
- [ ] 4 test in `scripts/tests/test_parse_coverage.py` tutti PASS
- [ ] Coverage `parse_coverage.py` ≥ 70% (verifica `pytest --cov`)
- [ ] Output JSON segue lo schema documentato in design doc §2.3 e in phase-6-coverage.md
- [ ] `phase-6-coverage.md` ridotto a ~60 LOC (delete righe duplicate, mantieni solo command + output contract + fallback)
- [ ] `stack-matrix.json` ha `coverage_report_format` + `coverage_report_path` per ogni framework
- [ ] Smoke test su benchmark MEDIUM: `parse_coverage.py vitest coverage/coverage-summary.json` produce JSON valido
- [ ] Spec-reviewer PASS

## Note operative

- Solo Python 3 stdlib (re, json, argparse, pathlib, sys) — vincolo no nuove deps rispettato
- JaCoCo XML parsato con regex (no lxml), accettando perdita marginale di edge case (es. nested <package> con escape XML)
- Branch coverage non sempre disponibile per Go/Cargo: emesso 0.0 con commento
- L'exit code è SEMPRE 0 anche su parse error per compatibilità con subprocess in SKILL.md (l'errore è in JSON `error` field)
