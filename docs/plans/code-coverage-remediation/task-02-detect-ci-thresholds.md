# Task 02 — CI thresholds + working-directory audit (single pass)

**Goal:** Nuovo script `scripts/detect_ci_thresholds.py` che scorre `.github/workflows/*.yaml` UNA volta ed emette `ci-thresholds.json` con: le soglie `COVERAGE_*` (anche da reusable remoti via `gh api` e `${{ vars.X }}` via `gh variable get`) e la lista `working_directory_issues[]` (manifest_root != "." ma reusable senza `working-directory`). Risolve gap 6.1 (CI rosso ENOENT) e 6.5 (soglia CI sconosciuta) in un solo pass.

**WS:** WS-1 · **Dipendenze:** nessuna (Task 03 consuma il suo output).

## File coinvolti
- Crea: `skills/code-coverage/scripts/detect_ci_thresholds.py`
- Crea: `skills/code-coverage/scripts/tests/test_detect_ci_thresholds.py`
- Modifica: `skills/code-coverage/lib/phase1-discover.sh` (invocazione parallela)

## Step TDD

### Step 1 — Test fallente
Crea `skills/code-coverage/scripts/tests/test_detect_ci_thresholds.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "detect_ci_thresholds.py"


def _run(repo: Path) -> dict:
    out = subprocess.run([sys.executable, str(SCRIPT), str(repo)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _wf(repo: Path, name: str, content: str):
    d = repo / ".github" / "workflows"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(content, encoding="utf-8")


def test_literal_thresholds(tmp_path):
    _wf(tmp_path, "CI.yaml", """
jobs:
  test:
    uses: itsiae/siae-gh-actions/.github/workflows/JS_CI.yaml@v3.0.0
    with:
      working-directory: modules/service/lambda-handler
      COVERAGE_BRANCHES: 70
      COVERAGE_LINES: 80
""")
    out = _run(tmp_path)
    assert out["COVERAGE_BRANCHES"] == 70
    assert out["COVERAGE_LINES"] == 80
    assert out["working_directory_issues"] == []


def test_working_directory_issue_detected(tmp_path):
    # stack.json con manifest_root sub-workspace
    cc = tmp_path / ".code-coverage"
    cc.mkdir()
    (cc / "stack.json").write_text(json.dumps({"manifest_root": "modules/service/lambda-handler"}))
    _wf(tmp_path, "CI.yaml", """
jobs:
  test:
    uses: itsiae/siae-gh-actions/.github/workflows/JS_CI.yaml@v3.0.0
    with:
      node-version: 20
""")
    out = _run(tmp_path)
    assert any("CI.yaml" in iss for iss in out["working_directory_issues"])


def test_no_workflows_dir(tmp_path):
    out = _run(tmp_path)
    assert out == {"working_directory_issues": []} or out.get("working_directory_issues") == []
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_detect_ci_thresholds.py -v`
Output atteso: errore "No such file or directory: detect_ci_thresholds.py" → 3 FAILED.

### Step 3 — Implementa `scripts/detect_ci_thresholds.py`

```python
#!/usr/bin/env python3
"""detect_ci_thresholds.py — Risolve soglie coverage CI + audit working-directory.

Pass UNICO su .github/workflows/*.yaml. Output JSON:
  {
    "COVERAGE_BRANCHES": 70, "COVERAGE_LINES": 80, ...,
    "source": "CI.yaml" | "remote:owner/repo/wf@ref",
    "working_directory_issues": ["CI.yaml: reusable caller without working-directory"]
  }
Risoluzione soglie:
  1. literal nei file locali
  2. reusable remoto (gh api) se nessuna soglia locale ma reusable presente
  3. ${{ vars.X }} via gh variable get (best-effort)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

_VAR_RE = re.compile(
    r"(COVERAGE_(?:LINES|BRANCHES|STATEMENTS|FUNCTIONS|THRESHOLD)|MIN_COVERAGE)"
    r"\s*[:=]\s*['\"]?(\d+\.?\d*)['\"]?",
    re.IGNORECASE,
)
_VARREF_RE = re.compile(
    r"(COVERAGE_(?:LINES|BRANCHES|STATEMENTS|FUNCTIONS|THRESHOLD))\s*:\s*"
    r"\$\{\{\s*vars\.([A-Z_]+)\s*\}\}",
)
_REUSABLE_RE = re.compile(
    r"uses:\s+([\w.\-]+/[\w.\-]+)/\.github/workflows/([\w.\-]+\.ya?ml)@([\w.\-/]+)"
)


def _scan_text(text: str) -> dict:
    result: dict[str, float] = {}
    for m in _VAR_RE.finditer(text):
        key = m.group(1).upper()
        val = float(m.group(2))
        if key not in result or val > result[key]:
            result[key] = val
    return result


def _gh_api_reusable(repo_slug: str, wf_path: str, ref: str) -> str:
    try:
        r = subprocess.run(
            ["gh", "api",
             f"repos/{repo_slug}/contents/.github/workflows/{wf_path}?ref={ref}",
             "-H", "Accept: application/vnd.github.raw"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            return r.stdout
    except Exception:
        pass
    return ""


def _gh_variable(slug: str, var: str) -> float | None:
    try:
        r = subprocess.run(["gh", "variable", "get", var, "-R", slug],
                           capture_output=True, text=True, timeout=8)
        if r.returncode == 0 and r.stdout.strip().replace(".", "", 1).isdigit():
            return float(r.stdout.strip())
    except Exception:
        pass
    return None


def _manifest_root(repo: Path) -> str:
    stack = repo / ".code-coverage" / "stack.json"
    try:
        return json.loads(stack.read_text()).get("manifest_root", ".")
    except Exception:
        return "."


def _repo_slug(repo: Path) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=5)
        m = re.search(r"[:/]([\w.\-]+/[\w.\-]+?)(?:\.git)?$", r.stdout.strip())
        return m.group(1) if m else None
    except Exception:
        return None


def main() -> None:
    repo = Path(sys.argv[1]).resolve()
    wf_dir = repo / ".github" / "workflows"
    thresholds: dict[str, float] = {}
    source = ""
    wd_issues: list[str] = []
    reusables: list[tuple[str, str, str]] = []
    varrefs: list[tuple[str, str]] = []
    manifest_root = _manifest_root(repo)

    if wf_dir.is_dir():
        for wf in sorted(list(wf_dir.glob("*.yaml")) + list(wf_dir.glob("*.yml"))):
            text = wf.read_text(encoding="utf-8", errors="ignore")
            found = _scan_text(text)
            if found:
                thresholds.update(found)
                source = wf.name
            for m in _REUSABLE_RE.finditer(text):
                reusables.append((m.group(1), m.group(2), m.group(3)))
                # working-directory audit: solo se sub-workspace
                if manifest_root != "." and "working-directory" not in text:
                    wd_issues.append(
                        f"{wf.name}: reusable caller without working-directory "
                        f"(manifest_root={manifest_root})"
                    )
            for m in _VARREF_RE.finditer(text):
                varrefs.append((m.group(1).upper(), m.group(2)))

    # Reusable remoto se nessuna soglia locale
    if not thresholds and reusables:
        for slug, wf_path, ref in reusables:
            remote = _gh_api_reusable(slug, wf_path, ref)
            if remote:
                found = _scan_text(remote)
                if found:
                    thresholds.update(found)
                    source = f"remote:{slug}/{wf_path}@{ref}"
                    break

    # ${{ vars.X }} via gh variable get
    if varrefs:
        slug = _repo_slug(repo)
        if slug:
            for key, var in varrefs:
                if key not in thresholds:
                    v = _gh_variable(slug, var)
                    if v is not None:
                        thresholds[key] = v
                        source = source or f"github-variable:{var}"

    out = {k: int(v) if v == int(v) else v for k, v in thresholds.items()}
    if source:
        out["source"] = source
    out["working_directory_issues"] = sorted(set(wd_issues))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
```

In `lib/phase1-discover.sh`, accanto agli altri detector paralleli, aggiungi:
```bash
python3 "$SKILL_DIR/scripts/detect_ci_thresholds.py" "$REPO" \
  > "$REPO/.code-coverage/ci-thresholds.json" 2>/dev/null &
PIDS+=($!)
```
(adatta `$SKILL_DIR`, `$REPO`, `PIDS` ai nomi reali già usati nel file — leggilo prima.)

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_detect_ci_thresholds.py -v`
Output atteso: `3 passed`. (I test non richiedono `gh`: usano soglie literal e working-dir audit locale.)

### Step 5 — Commit
```
git add skills/code-coverage/scripts/detect_ci_thresholds.py skills/code-coverage/scripts/tests/test_detect_ci_thresholds.py skills/code-coverage/lib/phase1-discover.sh
git commit -m "feat(code-coverage): detect CI coverage thresholds + working-directory audit in single pass"
```

## Criteri di accettazione
- [ ] Soglie literal `COVERAGE_BRANCHES: 70` lette in `ci-thresholds.json`.
- [ ] manifest_root sub-workspace + reusable senza `working-directory` → `working_directory_issues[]` non vuoto.
- [ ] Nessuna `.github/workflows/` → `{"working_directory_issues": []}`, exit 0.
- [ ] `gh` assente → nessun crash (i path remoti/var sono best-effort).
