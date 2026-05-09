# Task 04 — Repair Loop Refactor (P5 + ST2 + ST6)

**Goal:** Implementare repair loop scoped (Edit per blocco, no rigenerazione full-file) + grouping per `error_signature` con normalize() deterministica + progress guard + autonomous early-abort + max 1 full-coverage/iter. Eliminare tutte le iterazioni Phase 7 sprecate.

**SP:** 2 (Augmented)
**Fix IDs covered:** P5 + ST2 + ST6
**Branch:** `feat/code-coverage-opt-repair-refactor`
**Dipendenze:** task-03 (parse_coverage.py disponibile, coverage-report.json contract stabile)

---

## File coinvolti

**Creazione**:
- `skills/code-coverage/scripts/categorize_failure.py` (~280 LOC Python)
- `skills/code-coverage/scripts/tests/test_categorize_failure.py` (~180 LOC test pytest, 6 test)
- `skills/code-coverage/scripts/tests/fixtures/failures/` (directory con 5 sample stderr per Cat 1-5)
- `skills/code-coverage/assets/repair-strategies.json` (~150 LOC) — error_pattern regex → category + fix_steps

**Modifica**:
- `skills/code-coverage/references/phase-7-repair.md` (riduci da 190 a ~80 LOC, logica → script)
- `skills/code-coverage/SKILL.md` (Phase 7 inline con nuovo loop algorithm)

---

## Step bite-sized

### Step 1 — Branch + verifica task-03 merged

```bash
git checkout main && git pull
git checkout -b feat/code-coverage-opt-repair-refactor
test -f skills/code-coverage/scripts/parse_coverage.py && echo "task-03 merged OK"
```

### Step 2 — Crea `assets/repair-strategies.json`

```json
{
  "categories": [
    {
      "id": 1,
      "name": "dependency",
      "patterns": [
        "Cannot find module ['\"]([^'\"]+)['\"]",
        "ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]",
        "error\\[E0432\\]: unresolved import ['\"]([^'\"]+)['\"]",
        "package ([\\w./]+) is not in (?:GOROOT|std|GOPATH)",
        "could not resolve dependency ([\\w./@-]+)"
      ],
      "fix_steps": [
        "Estrai nome dipendenza da capture group 1",
        "Verifica se è in stack-matrix.json install_dev_deps per il framework",
        "Aggiungi a install commands list",
        "Auto-install via validate_env.py install_commands"
      ],
      "systemic_eligible": true,
      "systemic_threshold_count": 2,
      "systemic_fix_template": "Esegui {install_command} una sola volta a livello di repo"
    },
    {
      "id": 2,
      "name": "import",
      "patterns": [
        "does not provide an export named ['\"]([^'\"]+)['\"]",
        "Module .* has no exported member ['\"]([^'\"]+)['\"]",
        "ImportError: cannot import name ['\"]([^'\"]+)['\"]",
        "SyntaxError: The requested module ['\"]([^'\"]+)['\"] does not provide"
      ],
      "fix_steps": [
        "Identifica file source che non esporta il simbolo",
        "Run grep deterministico: grep -nE '^export (default|const|function|class)' <source-file>",
        "Riformula import nel test (default vs named vs namespace)",
        "Edit del solo blocco import nel test file (no rigenerazione full-file)"
      ],
      "systemic_eligible": false,
      "systemic_threshold_count": 0
    },
    {
      "id": 3,
      "name": "runtime",
      "patterns": [
        "ReferenceError: ([\\w$]+) is not defined",
        "TypeError: ([\\w$.]+) is not a function",
        "document is not defined",
        "window is not defined",
        "AttributeError: ['\"]?([\\w]+)['\"]? object has no attribute ['\"]([\\w]+)['\"]",
        "(test|spec) timed out (?:in )?(\\d+ms)"
      ],
      "fix_steps": [
        "Distingui timeout (transient) vs runtime error (persistent)",
        "Se 'document' o 'window' undefined → set environment 'jsdom' nel config",
        "Se timeout: re-run UNA volta senza modifiche (transient retry)",
        "Se attribute error: verifica versione lib in package.json"
      ],
      "systemic_eligible": true,
      "systemic_threshold_count": 2,
      "systemic_fix_template": "Modifica {config_file} per aggiungere {env_setting}"
    },
    {
      "id": 4,
      "name": "mock",
      "patterns": [
        "expected (?:mock )?(?:function )?to (?:have been |be )?called",
        "Expected mock function to (?:have been called|return)",
        "AssertionError: Expected '([\\w$]+)' to (?:have been |be )?called",
        "vi\\.mock\\(\\) factory must (?:return|provide)",
        "jest\\.mock\\(\\) factory must (?:return|provide)"
      ],
      "fix_steps": [
        "Re-leggi mock factory nel test file",
        "Verifica export shape della dependency mockata via grep",
        "Edit factory: usa default export vs named in base al grep result",
        "Se mock non chiamato: aggiungi expect(mock).toHaveBeenCalled() o rivedi flow test"
      ],
      "systemic_eligible": false,
      "systemic_threshold_count": 0
    },
    {
      "id": 5,
      "name": "assertion",
      "patterns": [
        "AssertionError",
        "Expected: ([^\\n]+).*?Received: ([^\\n]+)",
        "expect\\([^)]+\\)\\.to\\w+",
        "assert ([^=]+) == ([^,]+) failed",
        "assertion `(.+)` failed"
      ],
      "fix_steps": [
        "Identifica expected vs actual nel diff",
        "Verifica logica del SUT (potrebbe essere il test sbagliato)",
        "Aggiusta assertion solo se contratto pubblico è chiaro",
        "Se ambiguo: log come stalled e move on"
      ],
      "systemic_eligible": false,
      "systemic_threshold_count": 0
    },
    {
      "id": 6,
      "name": "transient",
      "patterns": [
        "ECONNRESET",
        "EAI_AGAIN",
        "EBUSY",
        "EADDRINUSE",
        "Killed: 9",
        "JavaScript heap out of memory",
        "OOM",
        "registry returned 5\\d\\d"
      ],
      "fix_steps": [
        "Re-run il test file UNA volta senza modifiche",
        "Se errore persiste in re-run: escalate a Cat 1 (dependency) o Cat 3 (runtime)",
        "Se errore scompare: log come transient + procedi"
      ],
      "systemic_eligible": false,
      "systemic_threshold_count": 0
    }
  ],
  "normalize_regex": [
    {"pattern": "/[\\w./-]+", "replace": "·"},
    {"pattern": "\\d{4}-\\d{2}-\\d{2}T?\\d{0,2}:?\\d{0,2}:?\\d{0,2}", "replace": "·"},
    {"pattern": "0x[0-9a-fA-F]+", "replace": "·"},
    {"pattern": ":\\d+:\\d+", "replace": ":·:·"},
    {"pattern": "\\u001b\\[[0-9;]*m", "replace": ""}
  ],
  "max_signature_length": 200
}
```

### Step 3 — TDD: scrivi prima i 6 test (RED)

Crea le 5 fixture stderr in `skills/code-coverage/scripts/tests/fixtures/failures/`:

`cat1-dependency.txt`:
```
FAIL src/services/payment.test.ts
Error: Cannot find module 'lodash' from src/services/payment.ts
```

`cat2-import.txt`:
```
FAIL src/utils/format.test.ts
SyntaxError: The requested module './helpers' does not provide an export named 'formatDate'
```

`cat3-runtime.txt`:
```
FAIL src/components/Button.test.tsx
ReferenceError: document is not defined
  at Object.<anonymous> (src/components/Button.test.tsx:5:3)
```

`cat4-mock.txt`:
```
FAIL src/services/auth.test.ts
AssertionError: expected mock function to have been called once but was called 0 times
  at src/services/auth.test.ts:12:5
```

`cat5-assertion.txt`:
```
FAIL src/utils/validate.test.ts
AssertionError [ERR_ASSERTION]: Values are not equal:
  Expected: "VALID"
  Received: "INVALID"
  at src/utils/validate.test.ts:8:3
```

Crea `skills/code-coverage/scripts/tests/test_categorize_failure.py`:

```python
"""Test per categorize_failure.py — 5 categorie + normalize() determinismo."""
import json
import subprocess
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "failures"
SCRIPT = Path(__file__).resolve().parent.parent / "categorize_failure.py"


def run_categorizer(input_file: Path) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), str(input_file)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_cat1_dependency():
    """Cat 1: 'Cannot find module' → dependency."""
    out = run_categorizer(FIXTURES / "cat1-dependency.txt")
    assert out["category"] == 1
    assert out["category_name"] == "dependency"
    assert "lodash" in out.get("captures", [""])[0]


def test_cat2_import():
    """Cat 2: 'does not provide an export named' → import."""
    out = run_categorizer(FIXTURES / "cat2-import.txt")
    assert out["category"] == 2
    assert out["category_name"] == "import"


def test_cat3_runtime():
    """Cat 3: 'document is not defined' → runtime."""
    out = run_categorizer(FIXTURES / "cat3-runtime.txt")
    assert out["category"] == 3
    assert out["category_name"] == "runtime"


def test_cat4_mock():
    """Cat 4: 'expected mock function to have been called' → mock."""
    out = run_categorizer(FIXTURES / "cat4-mock.txt")
    assert out["category"] == 4
    assert out["category_name"] == "mock"


def test_cat5_assertion():
    """Cat 5: 'AssertionError' senza pattern più specifici → assertion."""
    out = run_categorizer(FIXTURES / "cat5-assertion.txt")
    assert out["category"] == 5
    assert out["category_name"] == "assertion"


def test_normalize_deterministic():
    """normalize() produce stesso signature per stesso errore con timestamp/path/hex diversi."""
    err1 = "Error at /home/user/project/src/foo.ts:12:5 timestamp=2026-05-09T10:00:00 ptr=0xabc123"
    err2 = "Error at /tmp/build/src/bar.ts:99:1 timestamp=2026-05-10T15:30:45 ptr=0xdef456"
    # Importa direttamente per testare la funzione
    import sys
    sys.path.insert(0, str(SCRIPT.parent))
    from categorize_failure import normalize
    sig1 = normalize(err1)
    sig2 = normalize(err2)
    assert sig1 == sig2, f"normalize() non deterministico:\n{sig1}\n!=\n{sig2}"
    assert len(sig1) <= 200
```

### Step 4 — Run test in RED state

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_categorize_failure.py -v
```

Output atteso: 6 errors (FileNotFoundError categorize_failure.py).

### Step 5 — GREEN: implementa `scripts/categorize_failure.py`

Crea `skills/code-coverage/scripts/categorize_failure.py`:

```python
#!/usr/bin/env python3
"""categorize_failure.py — categorizza failure stderr in Cat 1-6 deterministicamente.

Usage:
    python3 categorize_failure.py <stderr-file>
    python3 categorize_failure.py --stdin < stderr-stream

Output (stdout): JSON con schema:
    {
        "category": int (1-6) | null,
        "category_name": str | null,
        "signature": str,                 # normalize() del primo error message
        "captures": [str],                # capture groups del regex match
        "fix_steps": [str],               # da repair-strategies.json
        "systemic_eligible": bool,
        "systemic_threshold_count": int,
        "raw_first_line": str
    }

Exit code: 0 sempre (errore in JSON `category: null` se non categorizzabile).
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
STRATEGIES_PATH = SKILL_ROOT / "assets" / "repair-strategies.json"


def load_strategies() -> dict:
    with open(STRATEGIES_PATH) as f:
        return json.load(f)


def normalize(error_message: str, normalize_rules: list | None = None) -> str:
    """Normalizza un messaggio d'errore in una signature deterministica.

    Strip:
    - Path assoluti / relativi (regex /[\\w./-]+ → ·)
    - Timestamp ISO (2026-05-09T...)
    - Hex addresses (0xabc123)
    - Line:col specifiers (:12:5)
    - ANSI escape sequences

    Tronca a 200 char. Lavora SOLO sulla prima riga del messaggio (split su \\n).
    """
    if normalize_rules is None:
        strategies = load_strategies()
        normalize_rules = strategies.get("normalize_regex", [])

    first_line = error_message.split("\n")[0]
    sig = first_line
    for rule in normalize_rules:
        sig = re.sub(rule["pattern"], rule["replace"], sig)

    # Collassa whitespace multipli
    sig = re.sub(r"\s+", " ", sig).strip()

    return sig[:200]


def categorize(stderr_content: str, strategies: dict) -> dict:
    """Categorizza un blob stderr in Cat 1-6 in base a pattern matching.

    Ordine valutazione: Cat 6 (transient) PRIMA di Cat 1-5 (errori specifici)
    per evitare false categorization di network errors come dependency.
    Poi Cat 1, 2, 3, 4, 5.
    """
    raw_lines = stderr_content.split("\n")
    raw_first_line = next((line for line in raw_lines if line.strip()), "")

    categories = strategies["categories"]
    # Riordina: Cat 6 (transient) per primo
    cat6 = next((c for c in categories if c["id"] == 6), None)
    others = [c for c in categories if c["id"] != 6]
    eval_order = ([cat6] if cat6 else []) + sorted(others, key=lambda c: c["id"])

    for cat in eval_order:
        for pattern in cat["patterns"]:
            match = re.search(pattern, stderr_content, flags=re.MULTILINE | re.IGNORECASE)
            if match:
                signature = normalize(stderr_content, strategies.get("normalize_regex"))
                return {
                    "category": cat["id"],
                    "category_name": cat["name"],
                    "signature": signature,
                    "captures": list(match.groups()),
                    "fix_steps": cat["fix_steps"],
                    "systemic_eligible": cat.get("systemic_eligible", False),
                    "systemic_threshold_count": cat.get("systemic_threshold_count", 0),
                    "raw_first_line": raw_first_line[:300],
                }

    # Nessun pattern matched
    return {
        "category": None,
        "category_name": None,
        "signature": normalize(stderr_content, strategies.get("normalize_regex")),
        "captures": [],
        "fix_steps": ["Manual investigation required — no automatic categorization"],
        "systemic_eligible": False,
        "systemic_threshold_count": 0,
        "raw_first_line": raw_first_line[:300],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stderr_file", nargs="?", type=Path,
                        help="File contenente stderr del test runner. Se omesso, legge stdin.")
    parser.add_argument("--stdin", action="store_true", help="Legge stderr da stdin")
    args = parser.parse_args()

    if args.stdin or args.stderr_file is None:
        stderr_content = sys.stdin.read()
    else:
        if not args.stderr_file.exists():
            print(json.dumps({"error": f"File not found: {args.stderr_file}", "category": None}))
            return 0
        stderr_content = args.stderr_file.read_text()

    strategies = load_strategies()
    result = categorize(stderr_content, strategies)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Make executable:
```bash
chmod +x skills/code-coverage/scripts/categorize_failure.py
```

### Step 6 — Run test in GREEN state

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_categorize_failure.py -v
```

Output atteso:
```
test_categorize_failure.py::test_cat1_dependency PASSED
test_categorize_failure.py::test_cat2_import PASSED
test_categorize_failure.py::test_cat3_runtime PASSED
test_categorize_failure.py::test_cat4_mock PASSED
test_categorize_failure.py::test_cat5_assertion PASSED
test_categorize_failure.py::test_normalize_deterministic PASSED

6 passed in <1s>
```

### Step 7 — Coverage del nuovo script ≥70%

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_categorize_failure.py --cov=scripts/categorize_failure --cov-report=term-missing
```

Coverage attesa ≥70%. Aggiungi test per Cat 6 (transient) e branch "no match" se sotto.

### Step 8 — Riscrivi `phase-7-repair.md` da 190 a ~80 LOC

Nuovo contenuto:

```markdown
# Phase 7 — Repair Loop

**Goal**: dopo Phase 6, riparare moduli/test sotto threshold tramite categorizzazione deterministica + grouping per error_signature + fix scoped + progress guard.

**Pre-requisito**: `.code-coverage/coverage-report.json` (output di parse_coverage.py) + esecuzione test runner che ha prodotto stderr.

## Algoritmo

```python
import json
import subprocess
from pathlib import Path

# Read coverage report
report = json.loads(Path(".code-coverage/coverage-report.json").read_text())
failing_tests = []  # popolato da run del framework: list of (test_file, stderr_blob)

iteration = 0
max_iter = 3
prev_global_pct = 0.0
prev_failing_count = len(failing_tests)
loop_max_remaining = max_iter

while iteration < loop_max_remaining and (
    report["global_pct"] < 70 or
    any(m["status"] == "FAIL" for m in report["modules"] if m["priority"])
):
    iteration += 1

    # Categorize tutti i failure
    failures = []
    for test_file, stderr in failing_tests:
        cat_result = subprocess.run(
            ["python3", "skills/code-coverage/scripts/categorize_failure.py"],
            input=stderr, capture_output=True, text=True, check=True
        ).stdout
        failures.append({"test_file": test_file, **json.loads(cat_result)})

    # Persisti per audit
    Path(".code-coverage/failures.json").write_text(json.dumps({
        "iteration": iteration,
        "failures": failures
    }, indent=2))

    # GROUPING per error_signature
    from collections import defaultdict
    grouped = defaultdict(list)
    for f in failures:
        grouped[f["signature"]].append(f)

    # SYSTEMIC FIX detection: count >= 2 OR >= 30% file
    total_failing = len(failing_tests)
    systemic_threshold = max(2, int(total_failing * 0.30))

    for signature, group in grouped.items():
        first = group[0]
        if first["systemic_eligible"] and len(group) >= systemic_threshold:
            # Apply systemic config-level fix
            apply_systemic_fix(first)  # esegui fix_steps[0] una sola volta a livello config
            continue
        # Per-file fix scoped (Edit del solo blocco failing, NO rigenerazione full-file)
        for f in group:
            apply_scoped_fix(f)

    # Re-run SOLO test file modificati, NO --coverage
    rerun_modified_tests(failing_tests)

    # Re-run full coverage UNA VOLTA per iterazione
    run_full_coverage()  # come Phase 6
    report = json.loads(Path(".code-coverage/coverage-report.json").read_text())
    new_failing_count = sum(1 for m in report["modules"] if m["status"] == "FAIL")

    # PROGRESS GUARD
    delta_global = report["global_pct"] - prev_global_pct
    delta_failing = prev_failing_count - new_failing_count
    if delta_global < 0.5 and delta_failing <= 0:
        log("STOP: progress guard triggered (Δglobal<0.5pp AND no failure reduction)")
        break

    # AUTONOMOUS EARLY-ABORT iter 1
    if iteration == 1 and report["global_pct"] < 30:
        p1_modules = [m for m in report["modules"] if m["priority"] == "P1"]
        if any(m["lines_pct"] < 40 for m in p1_modules):
            loop_max_remaining = iteration + 1  # 1 sola iter aggiuntiva
            log("WARN: critical low coverage, single retry attempted")

    prev_global_pct = report["global_pct"]
    prev_failing_count = new_failing_count

# OUTPUT best-effort se non ha raggiunto target
emit_block_8_with_remaining_failing()
```

## Categorie failure (vedi `assets/repair-strategies.json`)

| Cat | Name | Pattern signal | Systemic eligible |
|-----|------|----------------|-------------------|
| 1 | dependency | `Cannot find module`, `ModuleNotFoundError` | YES (count≥2) |
| 2 | import | `does not provide an export`, `cannot import name` | NO |
| 3 | runtime | `ReferenceError`, `is not defined`, timeout | YES (count≥2) |
| 4 | mock | `expected mock to have been called`, factory error | NO |
| 5 | assertion | `AssertionError`, expect mismatch | NO |
| 6 | transient | `ECONNRESET`, `OOM`, `EBUSY` (eval prima di Cat 1-5) | NO |

## Best-Effort Report (se max_iter raggiunto)

In OUTPUT Block 8 aggiungi sotto-tabella **Stalled Files**:
```
| File | Iter | Last category | Last signature | Suggested action |
|------|------|---------------|-----------------|--------------------|
| ...  | 3    | mock          | ·expected mock·to have been called· | Manual review |
```
```

### Step 9 — SKILL.md: aggiorna Phase 7 inline

In SKILL.md aggiorna la Phase 7 (riga 150-156) sostituendo con riferimento all'algoritmo di phase-7-repair.md + max budget rule:

```
### Phase 7 — Repair (INLINE algorithm)
**Load `skills/code-coverage/references/phase-7-repair.md` per il pseudocodice completo.**

Budget rules (deterministic):
- max iterazioni: 3 (autonomous early-abort iter 1 può ridurre a 2)
- max 1 full coverage run per iterazione
- categorize via `python3 scripts/categorize_failure.py` (deterministic)
- progress guard: Δglobal_coverage < 0.5pp AND Δfailing_count ≤ 0 → STOP
- systemic fix: count ≥ 2 OR ≥ 30% file con stessa signature E categoria systemic_eligible → fix config-level UNA VOLTA
- per-file fix: Edit scoped (solo blocco failing), NO rigenerazione full-file

Output: `.code-coverage/failures.json` per ogni iter (audit trail).
```

### Step 10 — Spec-reviewer

Lancia spec-reviewer.

### Step 11 — Commit + PR

```bash
git add skills/code-coverage/scripts/categorize_failure.py \
        skills/code-coverage/scripts/tests/test_categorize_failure.py \
        skills/code-coverage/scripts/tests/fixtures/failures/ \
        skills/code-coverage/assets/repair-strategies.json \
        skills/code-coverage/references/phase-7-repair.md \
        skills/code-coverage/SKILL.md
git commit -m "feat(code-coverage): repair loop refactor — scoped + grouped + autonomous (P5, ST2, ST6)

P5: repair scoped (Edit per blocco), grouping per error_signature,
    systemic fix se count>=2 OR >=30% file, progress guard <0.5pp,
    autonomous early-abort iter1<30% senza prompt utente,
    max 1 full-coverage/iter
ST2: nuovo scripts/categorize_failure.py (Cat 1-6 deterministico)
     + 6 test in scripts/tests/ (>=70% coverage)
     + assets/repair-strategies.json (single source patterns)
ST6: normalize() regex deterministica (path/timestamp/hex stripping, max 200 char)

phase-7-repair.md ridotto da 190 a ~80 LOC.

Refs design doc 2026-05-09-code-coverage-optimization-design.md PR4.

Co-Authored-By: SIAE DevForge"

git push -u origin feat/code-coverage-opt-repair-refactor
gh pr create --title "feat(code-coverage): repair loop refactor (P5, ST2, ST6)" --body "$(cat <<'EOF'
## Summary
- Nuovo `scripts/categorize_failure.py` con 6 categorie + normalize() deterministica
- `assets/repair-strategies.json` single source per error patterns + fix steps
- Repair loop in phase-7-repair.md: grouping, systemic fix, progress guard, autonomous early-abort
- 6 test pytest, coverage >=70%

Refs: docs/plans/2026-05-09-code-coverage-optimization-design.md PR4

## Test plan
- [x] 6 test PASS (Cat 1-5 + normalize determinismo)
- [x] Coverage categorize_failure.py >=70%
- [ ] Smoke test: simula iter Phase 7 su benchmark MEDIUM con 5 failure (verifica grouping + systemic detection)
- [ ] Spec-reviewer PASS

Co-Authored-By: SIAE DevForge
EOF
)"
```

---

## Acceptance criteria

- [ ] `scripts/categorize_failure.py` esiste, eseguibile, gestisce 6 categorie
- [ ] `assets/repair-strategies.json` valido JSON con 6 categorie + normalize_regex
- [ ] 6 test in `test_categorize_failure.py` tutti PASS
- [ ] Coverage `categorize_failure.py` ≥ 70%
- [ ] `normalize()` produce signature identico per error con timestamp/path/hex diversi
- [ ] `phase-7-repair.md` ridotto a ~80 LOC con algoritmo Python pseudocodice
- [ ] SKILL.md Phase 7 aggiornato con budget rules deterministic
- [ ] Smoke test: simulazione 5 failure con 3 stesse signature → systemic fix detected
- [ ] Spec-reviewer PASS

## Note operative

- Ordine evaluation Cat 6 (transient) PRIMA di Cat 1-5 evita false positive (es. `ECONNRESET` matchabile come dependency)
- Cat 6 (transient) include 1 retry automatico — se fallisce di nuovo, escalate a Cat 1/3
- normalize() strip ANSI escape codes (rilevanti per output Vitest/Jest colorati)
- `apply_systemic_fix()` e `apply_scoped_fix()` sono pseudo-codice in phase-7-repair.md — l'esecuzione concreta è demandata all'agent LLM che orchestra Edit/Bash tools
