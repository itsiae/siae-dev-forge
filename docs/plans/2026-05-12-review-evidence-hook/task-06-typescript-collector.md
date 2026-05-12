# Task 06 — TypeScript collector (vitest lcov + eslint + complexity)

**SP:** 2.0 · **AC mappati:** AC #3 · **Dipendenze:** Task 04 · **Wave:** 3

## Goal

Implementare `lib/review_evidence/collectors/typescript.py`: rileva repo TS/JS (presenza `package.json` con `typescript` o file `.ts`/`.tsx`), parsa `coverage/lcov.info`, invoca `npx eslint --format json`, calcola complessità con `npx complexity-report` (opzionale).

## File coinvolti

**Creare:**
- `lib/review_evidence/collectors/typescript.py`
- `lib/review_evidence/collectors/_lcov.py` (lcov parser helper)
- `tests/test_review_evidence_collector_typescript.py`
- `tests/fixtures/review-evidence/lcov.info`
- `tests/fixtures/review-evidence/eslint_output.json`

## Step TDD

### Step 1 — Fixture lcov.info

```
TN:
SF:src/app.ts
FNF:5
FNH:4
LF:50
LH:42
end_of_record
SF:src/util.ts
FNF:3
FNH:2
LF:20
LH:10
end_of_record
```

`tests/fixtures/review-evidence/eslint_output.json`:

```json
[
  {"filePath":"/repo/src/app.ts","messages":[
    {"ruleId":"@typescript-eslint/no-unused-vars","severity":2,"message":"unused","line":12,"column":3},
    {"ruleId":"prefer-const","severity":1,"message":"const","line":20,"column":5}
  ],"errorCount":1,"warningCount":1,"fixableErrorCount":0,"fixableWarningCount":0}
]
```

### Step 2 — Test fallente

`tests/test_review_evidence_collector_typescript.py`:

```python
"""Tests for TypeScript collector."""
import json
from pathlib import Path
from unittest.mock import patch

from lib.review_evidence.collectors.typescript import TypeScriptCollector
from lib.review_evidence.collectors._lcov import parse_lcov

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_parse_lcov_aggregates_line_hit():
    lcov = (FIX / "lcov.info").read_text()
    parsed = parse_lcov(lcov)
    assert parsed["total_lines"] == 70
    assert parsed["hit_lines"] == 52
    assert round(parsed["pct"], 1) == 74.3
    assert len(parsed["per_file"]) == 2


def test_is_applicable_package_json_with_ts(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"typescript": "5"}}))
    assert TypeScriptCollector().is_applicable(tmp_path) is True


def test_is_applicable_ts_files(tmp_path):
    (tmp_path / "main.ts").write_text("export {}")
    assert TypeScriptCollector().is_applicable(tmp_path) is True


def test_not_applicable_plain_js_only(tmp_path):
    (tmp_path / "main.js").write_text("// js")
    # No package.json, no .ts — should be False (collector è TS-first)
    assert TypeScriptCollector().is_applicable(tmp_path) is False


def test_collect_with_lcov_and_eslint(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"typescript": "5"}}))
    cov_dir = tmp_path / "coverage"
    cov_dir.mkdir()
    (cov_dir / "lcov.info").write_text((FIX / "lcov.info").read_text())

    eslint_out = (FIX / "eslint_output.json").read_text()

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if "eslint" in " ".join(cmd):
            return CompletedProcess(cmd, 0, stdout=eslint_out, stderr="")
        # complexity-report missing
        raise FileNotFoundError(cmd[0])

    with patch("lib.review_evidence.collectors.typescript.subprocess.run", side_effect=fake_run):
        result = TypeScriptCollector().collect(tmp_path, "main", "HEAD")

    assert result["stack"] == "typescript"
    assert round(result["coverage"]["overall_pct"], 1) == 74.3
    assert result["coverage"]["source"] == "local:lcov"
    assert result["lint"]["errors"] == 1
    assert result["lint"]["warnings"] == 1
    assert result["lint"]["source"] == "local:eslint"
    # complexity-report missing → complexity is None
    assert result["complexity"] is None or result["complexity"].get("source") is None


def test_collect_missing_lcov_returns_none_coverage(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"typescript": "5"}}))

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    with patch("lib.review_evidence.collectors.typescript.subprocess.run", side_effect=fake_run):
        result = TypeScriptCollector().collect(tmp_path, "main", "HEAD")
    assert result["coverage"] is None
```

### Step 3 — Implementa _lcov.py

```python
"""Minimal LCOV parser — extracts file-level + total line coverage."""
from __future__ import annotations


def parse_lcov(content: str) -> dict:
    per_file = []
    total_lines = 0
    hit_lines = 0
    current: dict = {}
    for line in content.splitlines():
        if line.startswith("SF:"):
            current = {"path": line[3:]}
        elif line.startswith("LF:"):
            current["lf"] = int(line[3:])
        elif line.startswith("LH:"):
            current["lh"] = int(line[3:])
        elif line == "end_of_record":
            lf = current.get("lf", 0)
            lh = current.get("lh", 0)
            total_lines += lf
            hit_lines += lh
            pct = (lh / lf * 100) if lf else 0.0
            per_file.append({"path": current.get("path", ""), "pct": round(pct, 2), "uncovered_lines": []})
            current = {}
    pct = (hit_lines / total_lines * 100) if total_lines else 0.0
    return {"total_lines": total_lines, "hit_lines": hit_lines, "pct": pct, "per_file": per_file}
```

### Step 4 — Implementa typescript.py

```python
"""TypeScript stack collector: lcov + eslint + complexity-report."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from lib.review_evidence.collectors._lcov import parse_lcov
from lib.review_evidence.registry import register


class TypeScriptCollector:
    name = "typescript"

    def is_applicable(self, repo_root: Path) -> bool:
        pj = repo_root / "package.json"
        if pj.exists():
            try:
                data = json.loads(pj.read_text())
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "typescript" in deps:
                    return True
            except json.JSONDecodeError:
                pass
        return any(repo_root.rglob("*.ts")) or any(repo_root.rglob("*.tsx"))

    def collect(self, repo_root: Path, base_ref: str, head_ref: str) -> dict[str, Any]:
        return {
            "stack": "typescript",
            "coverage": self._coverage(repo_root),
            "lint": self._eslint(repo_root),
            "complexity": self._complexity(repo_root),
        }

    def _coverage(self, repo_root: Path) -> dict[str, Any] | None:
        lcov = repo_root / "coverage" / "lcov.info"
        if not lcov.exists():
            return None
        try:
            parsed = parse_lcov(lcov.read_text())
            return {
                "overall_pct": round(parsed["pct"], 2),
                "delta_vs_base": 0.0,
                "per_file": parsed["per_file"],
                "source": "local:lcov",
            }
        except Exception:
            return None

    def _eslint(self, repo_root: Path) -> dict[str, Any] | None:
        try:
            p = subprocess.run(
                ["npx", "--no-install", "eslint", ".", "--format", "json"],
                cwd=repo_root, capture_output=True, text=True, timeout=15, check=False,
            )
            if not p.stdout.strip():
                return None
            data = json.loads(p.stdout)
            errors = sum(f.get("errorCount", 0) for f in data)
            warnings = sum(f.get("warningCount", 0) for f in data)
            findings = []
            for f in data:
                for m in f.get("messages", []):
                    findings.append({
                        "file": f.get("filePath"),
                        "line": m.get("line"),
                        "rule": m.get("ruleId"),
                        "severity": "error" if m.get("severity") == 2 else "warning",
                        "msg": m.get("message"),
                    })
            return {"errors": errors, "warnings": warnings, "findings": findings, "source": "local:eslint"}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None

    def _complexity(self, repo_root: Path) -> dict[str, Any] | None:
        try:
            p = subprocess.run(
                ["npx", "--no-install", "complexity-report", "--format", "json", "src/"],
                cwd=repo_root, capture_output=True, text=True, timeout=15, check=False,
            )
            if p.returncode != 0 or not p.stdout.strip():
                return None
            data = json.loads(p.stdout)
            max_cx = 0
            over = []
            for report in data.get("reports", []):
                for fn in report.get("functions", []):
                    cx = fn.get("cyclomatic", 0)
                    if cx > max_cx:
                        max_cx = cx
                    if cx > 10:
                        over.append({"path": report.get("path"),
                                     "function": fn.get("name"),
                                     "cyclomatic": cx, "threshold": 10})
            return {"max_cyclomatic": max_cx, "files_over_threshold": over, "source": "local:complexity-report"}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(TypeScriptCollector())
```

### Step 5 — Esegui test e commit

```bash
pytest tests/test_review_evidence_collector_typescript.py -v
# 6 passed atteso

git add lib/review_evidence/collectors/typescript.py \
        lib/review_evidence/collectors/_lcov.py \
        tests/test_review_evidence_collector_typescript.py \
        tests/fixtures/review-evidence/lcov.info \
        tests/fixtures/review-evidence/eslint_output.json
git commit -m "feat(review-evidence): add TypeScript collector (lcov+eslint+complexity) (#task-06)"
```

## Criteri di accettazione

- [ ] `TypeScriptCollector.is_applicable()` rileva TS via package.json deps o file .ts/.tsx
- [ ] Coverage parsato da `coverage/lcov.info` con percentuale totale + per-file
- [ ] ESLint output parsato in errors/warnings/findings
- [ ] Complexity-report opzionale (missing → null)
- [ ] 6 test passano
