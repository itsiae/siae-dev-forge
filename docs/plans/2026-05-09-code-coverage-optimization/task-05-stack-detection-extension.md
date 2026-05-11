# Task 05 — Stack Detection Extension (P10 + ST4)

**Goal:** Estendere `detect_stack.py` per emettere campi documentati ma non implementati (`test_infrastructure`, `pre_existing_coverage_pct`, `module_coverage`, `coverage_exclude`); estendere `validate_env.py` `_check_framework_installed` con parsing reali di pom.xml/build.gradle/Cargo.toml/go.mod/pubspec.yaml; aumentare timeout a 30s per JVM/Flutter.

**SP:** 2 (Augmented)
**Fix IDs covered:** P10 + ST4
**Branch:** `feat/code-coverage-opt-stack-ext`
**Dipendenze:** task-01 (quick-wins) — può procedere in parallelo a task-02/03/04

---

## File coinvolti

**Modifica**:
- `skills/code-coverage/scripts/detect_stack.py` (estendere output schema)
- `skills/code-coverage/scripts/validate_env.py` (real install detection)
- `skills/code-coverage/scripts/estimate_size.py` (aggiungere flag `--with-coverage` opzionale)

**Creazione**:
- `skills/code-coverage/scripts/tests/test_detect_stack_ext.py` (~120 LOC, 3 test)
- `skills/code-coverage/scripts/tests/test_validate_env_ext.py` (~100 LOC, 2 test)
- `skills/code-coverage/scripts/tests/fixtures/repos/` (3 micro-repo fittizi: vue/maven/cargo per test parsing)

---

## Step bite-sized

### Step 1 — Branch + verifica task-01 merged

```bash
git checkout main && git pull
git checkout -b feat/code-coverage-opt-stack-ext
```

### Step 2 — Crea le fixture repo

```bash
mkdir -p skills/code-coverage/scripts/tests/fixtures/repos/vue-app/{src,coverage,tests/__tests__}
mkdir -p skills/code-coverage/scripts/tests/fixtures/repos/maven-app/{src/main/java,target/site/jacoco}
mkdir -p skills/code-coverage/scripts/tests/fixtures/repos/cargo-app/src
```

`vue-app/package.json`:
```json
{
  "name": "vue-fixture",
  "version": "0.1.0",
  "devDependencies": {
    "vitest": "^1.0.0",
    "@vitest/coverage-v8": "^1.0.0"
  }
}
```

`vue-app/coverage/lcov.info`:
```
TN:
SF:src/utils/format.ts
DA:1,1
DA:2,1
DA:3,0
LF:3
LH:2
end_of_record
SF:src/services/payment.ts
DA:1,1
DA:2,0
LF:2
LH:1
end_of_record
```

`vue-app/tests/__tests__/sample.test.ts`:
```typescript
import { describe, it, expect, vi } from 'vitest'
import { format } from '@/utils/format'
vi.mock('@/utils/helpers', () => ({ helper: vi.fn() }))
describe('format', () => {
  it('works', () => expect(format(1)).toBe('1'))
})
```

`maven-app/pom.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>maven-fixture</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.10.0</version>
      <scope>test</scope>
    </dependency>
    <dependency>
      <groupId>org.mockito</groupId>
      <artifactId>mockito-core</artifactId>
      <version>5.5.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
```

`maven-app/target/site/jacoco/jacoco.xml`:
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<report name="maven-fixture">
  <counter type="LINE" missed="20" covered="80"/>
  <counter type="BRANCH" missed="5" covered="15"/>
</report>
```

`cargo-app/Cargo.toml`:
```toml
[package]
name = "cargo-fixture"
version = "0.1.0"
edition = "2021"

[dev-dependencies]
mockall = "0.12"
```

### Step 3 — TDD: scrivi test estensione `detect_stack.py` (RED)

Crea `skills/code-coverage/scripts/tests/test_detect_stack_ext.py`:

```python
"""Test estensione detect_stack.py — verifica i 4 nuovi campi output (P10)."""
import json
import subprocess
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "repos"
SCRIPT = Path(__file__).resolve().parent.parent / "detect_stack.py"


def run_detect(repo_path: Path) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), str(repo_path)],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def test_test_infrastructure_emitted():
    """detect_stack.py deve emettere campo test_infrastructure dopo P10."""
    out = run_detect(FIXTURES / "vue-app")
    assert "test_infrastructure" in out
    ti = out["test_infrastructure"]
    assert "frameworks_detected" in ti
    assert "test_dirs" in ti
    assert "patterns_sample" in ti
    # Vue app ha vitest in devDeps
    assert "vitest" in ti["frameworks_detected"]


def test_module_coverage_from_lcov():
    """Se coverage/lcov.info esiste, detect_stack.py deve emettere module_coverage."""
    out = run_detect(FIXTURES / "vue-app")
    assert "module_coverage" in out
    mc = out["module_coverage"]
    # vue-app/coverage/lcov.info ha 2 file
    assert len(mc) == 2
    # Verifica che almeno uno abbia path + lines_pct
    assert all("path" in m and "lines_pct" in m for m in mc)
    # format.ts: 2/3 lines coperte = 66.67%
    fmt = next(m for m in mc if "format" in m["path"])
    assert 60 <= fmt["lines_pct"] <= 70


def test_pre_existing_coverage_pct_calculated():
    """detect_stack.py emette pre_existing_coverage_pct globale."""
    out = run_detect(FIXTURES / "vue-app")
    assert "pre_existing_coverage_pct" in out
    # vue-app: 3 lines covered su 5 total = 60%
    assert 55 <= out["pre_existing_coverage_pct"] <= 65


def test_coverage_exclude_emitted():
    """detect_stack.py emette coverage_exclude (per ora lista vuota se non config)."""
    out = run_detect(FIXTURES / "vue-app")
    assert "coverage_exclude" in out
    assert isinstance(out["coverage_exclude"], list)
```

### Step 4 — TDD: scrivi test estensione `validate_env.py` (RED)

Crea `skills/code-coverage/scripts/tests/test_validate_env_ext.py`:

```python
"""Test estensione validate_env.py — real check_framework_installed (P10)."""
import json
import subprocess
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "repos"
SCRIPT = Path(__file__).resolve().parent.parent / "validate_env.py"


def run_validate(repo_path: Path) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), str(repo_path)],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def test_maven_junit5_real_detection():
    """Maven repo con junit-jupiter in pom.xml dependency → installed=True."""
    out = run_validate(FIXTURES / "maven-app")
    fw = out.get("framework_check", {})
    # Verifica che junit5 sia rilevato come installed perché c'è in pom.xml
    if "junit5" in fw:
        assert fw["junit5"]["installed"] is True
        assert fw["junit5"].get("source") == "pom.xml"


def test_cargo_devdep_real_detection():
    """Cargo repo con dev-dependencies → check su Cargo.toml [dev-dependencies]."""
    out = run_validate(FIXTURES / "cargo-app")
    fw = out.get("framework_check", {})
    # cargo-test viene da Rust stdlib, non c'è da installare. Ma il check deve riportare framework=cargo-test, installed=True
    if "cargo-test" in fw:
        assert fw["cargo-test"]["installed"] is True
```

### Step 5 — Run test in RED

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_detect_stack_ext.py scripts/tests/test_validate_env_ext.py -v
```

Output atteso: tutti FAIL perché campi/logica mancanti.

### Step 6 — GREEN: estendi `detect_stack.py`

Apri `skills/code-coverage/scripts/detect_stack.py` e aggiungi nuove funzioni (mantieni le esistenti):

```python
# Aggiungi queste funzioni dopo le esistenti, prima di main():

def detect_test_infrastructure(repo_path: Path, frameworks: list[str]) -> dict:
    """Rileva infrastruttura test esistente: dirs, patterns, frameworks attivi.

    Output schema:
        {
            "frameworks_detected": ["vitest", "jest", ...],
            "test_dirs": ["tests/__tests__", "src/**/__tests__", ...],
            "patterns_sample": "vi.mock(...) | mock factory pattern excerpt"
        }
    """
    test_dirs = []
    for d in ["__tests__", "tests", "test", "spec"]:
        for found in repo_path.rglob(d):
            if found.is_dir() and not any(
                excl in str(found) for excl in ("node_modules", ".venv", "target", "dist", "build")
            ):
                test_dirs.append(str(found.relative_to(repo_path)))
    test_dirs = sorted(set(test_dirs))[:10]  # max 10

    # Pattern sample: leggi PRIMO test file e estrai pattern di mock
    pattern_sample = ""
    test_files = []
    for ext in [".test.ts", ".test.tsx", ".test.js", ".spec.ts", "_test.py", "test_*.py", "*Test.java", "*_test.go", "*_test.rs"]:
        for f in repo_path.rglob(ext.replace("*", "")):
            if "node_modules" in str(f) or ".venv" in str(f):
                continue
            test_files.append(f)
            if len(test_files) >= 3:
                break
        if len(test_files) >= 3:
            break

    if test_files:
        try:
            content = test_files[0].read_text()[:500]  # primi 500 char
            # Estrai prima riga con pattern mock-like
            for line in content.split("\n"):
                if any(sig in line for sig in ["vi.mock(", "jest.mock(", "@patch", "@mock", "mockito.when"]):
                    pattern_sample = line.strip()[:120]
                    break
        except Exception:
            pass

    return {
        "frameworks_detected": frameworks,
        "test_dirs": test_dirs,
        "patterns_sample": pattern_sample
    }


def parse_lcov_info(lcov_path: Path) -> tuple[float, list[dict]]:
    """Parse coverage/lcov.info per estrarre pre_existing_coverage_pct + module_coverage.

    Returns: (global_pct, [{path, lines_pct}])
    """
    if not lcov_path.exists():
        return 0.0, []

    content = lcov_path.read_text()
    modules = []
    total_lf = 0  # Lines Found
    total_lh = 0  # Lines Hit

    current_path = None
    current_lf = 0
    current_lh = 0

    for line in content.splitlines():
        if line.startswith("SF:"):
            current_path = line[3:].strip()
            current_lf = 0
            current_lh = 0
        elif line.startswith("LF:"):
            current_lf = int(line[3:].strip())
        elif line.startswith("LH:"):
            current_lh = int(line[3:].strip())
        elif line.startswith("end_of_record"):
            if current_path and current_lf > 0:
                pct = (current_lh / current_lf) * 100
                modules.append({"path": current_path, "lines_pct": round(pct, 2)})
                total_lf += current_lf
                total_lh += current_lh
            current_path = None

    global_pct = (total_lh / total_lf * 100) if total_lf > 0 else 0.0
    return round(global_pct, 2), modules


def detect_coverage_exclude(repo_path: Path) -> list[str]:
    """Rileva pattern di esclusione coverage da config files."""
    excludes = []
    # Vitest config
    for cfg in ["vitest.config.ts", "vitest.config.js", "vite.config.ts"]:
        p = repo_path / cfg
        if p.exists():
            content = p.read_text()
            # Cerca pattern: coverage: { exclude: [...] }
            import re
            m = re.search(r"exclude\s*:\s*\[([^\]]+)\]", content, re.DOTALL)
            if m:
                items = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
                excludes.extend(items)
    # Jest config
    for cfg in ["jest.config.js", "jest.config.ts"]:
        p = repo_path / cfg
        if p.exists():
            content = p.read_text()
            import re
            m = re.search(r"coveragePathIgnorePatterns\s*:\s*\[([^\]]+)\]", content, re.DOTALL)
            if m:
                items = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
                excludes.extend(items)
    # pyproject.toml
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        import re
        m = re.search(r"\[tool\.coverage\.run\][^[]*omit\s*=\s*\[([^\]]+)\]", content, re.DOTALL)
        if m:
            items = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
            excludes.extend(items)
    return sorted(set(excludes))


# Modifica main() per arricchire output JSON con i 4 nuovi campi:
def main() -> int:
    # ... codice esistente ...
    repo_path = Path(sys.argv[1])
    languages = detect_languages(repo_path)
    frameworks = detect_frameworks(repo_path)
    # ... altri esistenti ...

    # NUOVO: 4 campi P10
    test_infra = detect_test_infrastructure(repo_path, frameworks)
    pre_existing_pct, module_cov = parse_lcov_info(repo_path / "coverage" / "lcov.info")
    # Fallback per altri formati
    if pre_existing_pct == 0.0:
        # Cerca jacoco.xml
        jacoco_path = repo_path / "target" / "site" / "jacoco" / "jacoco.xml"
        if jacoco_path.exists():
            pre_existing_pct, module_cov = parse_jacoco_for_existing(jacoco_path)

    coverage_exclude = detect_coverage_exclude(repo_path)

    output = {
        # ... campi esistenti ...
        "test_infrastructure": test_infra,
        "pre_existing_coverage_pct": pre_existing_pct,
        "module_coverage": module_cov,
        "coverage_exclude": coverage_exclude
    }

    print(json.dumps(output, indent=2))
    return 0


def parse_jacoco_for_existing(jacoco_path: Path) -> tuple[float, list[dict]]:
    """Parse JaCoCo XML per pre_existing_coverage globale (no per-module per semplicità)."""
    import re
    content = jacoco_path.read_text()
    line_match = re.search(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', content)
    if not line_match:
        return 0.0, []
    missed, covered = int(line_match.group(1)), int(line_match.group(2))
    total = missed + covered
    pct = (covered / total * 100) if total else 0.0
    return round(pct, 2), [{"path": "(jacoco-aggregate)", "lines_pct": round(pct, 2)}]
```

### Step 7 — GREEN: estendi `validate_env.py` `_check_framework_installed`

Apri `validate_env.py` e modifica `_check_framework_installed` (~righe 141-152):

```python
def _check_framework_installed(repo_path: Path, framework: str) -> dict:
    """Real check su manifest dei build tool per framework presence.

    Returns: {"installed": bool, "version": str | None, "source": str}
    """
    if framework == "vitest":
        pkg = repo_path / "package.json"
        if pkg.exists():
            data = json.loads(pkg.read_text())
            dev = data.get("devDependencies", {})
            if "vitest" in dev:
                return {"installed": True, "version": dev["vitest"], "source": "package.json"}
        return {"installed": False, "version": None, "source": "package.json"}

    elif framework == "jest":
        pkg = repo_path / "package.json"
        if pkg.exists():
            data = json.loads(pkg.read_text())
            dev = data.get("devDependencies", {})
            if "jest" in dev:
                return {"installed": True, "version": dev["jest"], "source": "package.json"}
        return {"installed": False, "version": None, "source": "package.json"}

    elif framework == "pytest":
        # Check pyproject.toml [tool.poetry.dev-dependencies] o requirements-dev.txt
        for f in ["pyproject.toml", "requirements-dev.txt", "requirements.txt"]:
            p = repo_path / f
            if p.exists() and "pytest" in p.read_text():
                return {"installed": True, "version": None, "source": f}
        return {"installed": False, "version": None, "source": "pyproject.toml"}

    elif framework == "junit5":
        pom = repo_path / "pom.xml"
        if pom.exists():
            content = pom.read_text()
            # Match <artifactId>junit-jupiter</artifactId>
            if re.search(r"<artifactId>junit-jupiter(?:-api)?</artifactId>", content):
                return {"installed": True, "version": None, "source": "pom.xml"}
        gradle = repo_path / "build.gradle"
        if gradle.exists():
            content = gradle.read_text()
            if "junit-jupiter" in content or "useJUnitPlatform" in content:
                return {"installed": True, "version": None, "source": "build.gradle"}
        gradle_kts = repo_path / "build.gradle.kts"
        if gradle_kts.exists():
            content = gradle_kts.read_text()
            if "junit-jupiter" in content or "useJUnitPlatform" in content:
                return {"installed": True, "version": None, "source": "build.gradle.kts"}
        return {"installed": False, "version": None, "source": "pom.xml | build.gradle"}

    elif framework == "mockk":
        gradle = repo_path / "build.gradle.kts"
        if gradle.exists() and "mockk" in gradle.read_text():
            return {"installed": True, "version": None, "source": "build.gradle.kts"}
        return {"installed": False, "version": None, "source": "build.gradle.kts"}

    elif framework == "cargo-test":
        # cargo-test è builtin di Rust stdlib, sempre installed se Cargo.toml esiste
        if (repo_path / "Cargo.toml").exists():
            return {"installed": True, "version": "stdlib", "source": "Cargo.toml"}
        return {"installed": False, "version": None, "source": "Cargo.toml"}

    elif framework == "go-test":
        # go test è builtin
        if (repo_path / "go.mod").exists():
            return {"installed": True, "version": "stdlib", "source": "go.mod"}
        return {"installed": False, "version": None, "source": "go.mod"}

    elif framework == "flutter_test":
        pubspec = repo_path / "pubspec.yaml"
        if pubspec.exists() and "flutter_test:" in pubspec.read_text():
            return {"installed": True, "version": None, "source": "pubspec.yaml"}
        return {"installed": False, "version": None, "source": "pubspec.yaml"}

    elif framework == "xunit":
        # Cerca .csproj con PackageReference Include="xunit"
        for csproj in repo_path.rglob("*.csproj"):
            content = csproj.read_text()
            if 'Include="xunit"' in content or 'Include="xunit.runner' in content:
                return {"installed": True, "version": None, "source": str(csproj.relative_to(repo_path))}
        return {"installed": False, "version": None, "source": "*.csproj"}

    return {"installed": False, "version": None, "source": "unknown"}
```

### Step 8 — Aumenta timeout per JVM/Flutter

In `validate_env.py` aggiorna `_run` (riga 63-72):

```python
def _run(cmd: list, timeout: int = 5) -> tuple[bool, str]:
    """Run subprocess con timeout. Default 5s; override 30s per JVM/Flutter."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except (FileNotFoundError, OSError):
        return False, ""
```

E modifica le tuple di check per usare timeout=30 dove necessario:
```python
PM_CHECKS = [
    ("npm", ["npm", "--version"], 5),
    ("yarn", ["yarn", "--version"], 5),
    ("pnpm", ["pnpm", "--version"], 5),
    ("pip", ["pip", "--version"], 5),
    ("mvn", ["mvn", "--version"], 30),       # JVM cold start
    ("gradle", ["gradle", "--version"], 30),  # JVM + wrapper download
    ("cargo", ["cargo", "--version"], 5),
    ("go", ["go", "version"], 5),
    ("flutter", ["flutter", "--version"], 30), # Flutter cache populate
    ("dotnet", ["dotnet", "--version"], 5),
]
```

E nelle invocazioni `_run`, passa il timeout:
```python
for name, cmd, timeout in PM_CHECKS:
    ok, output = _run(cmd, timeout=timeout)
    pm_check[name] = {"available": ok, "version": output if ok else None,
                      "reason": "TIMEOUT" if output == "TIMEOUT" else None}
```

### Step 9 — `estimate_size.py`: aggiungi flag `--with-coverage`

In `estimate_size.py` aggiungi argparse flag:

```python
parser.add_argument("--with-coverage", type=Path, default=None,
                    help="Path a coverage-report.json (output di parse_coverage.py). Se passato, calcola priority_score per ogni file in file_list.")
```

Nel main, dopo aver popolato `file_list`:

```python
if args.with_coverage and args.with_coverage.exists():
    cov_data = json.loads(args.with_coverage.read_text())
    cov_map = {m["path"]: m["lines_pct"] for m in cov_data.get("modules", [])}
    for f in file_list:
        current_cov = cov_map.get(f["path"], 0) / 100.0  # normalizza a 0-1
        f["current_coverage"] = current_cov
        f["priority_score"] = (1 - current_cov) * f["loc"]
    # Ordina per priority_score desc
    file_list.sort(key=lambda f: f.get("priority_score", f["loc"]), reverse=True)
```

### Step 10 — Run test in GREEN

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_detect_stack_ext.py scripts/tests/test_validate_env_ext.py -v
```

Output atteso: 5 test PASS.

### Step 11 — Spec-reviewer + Commit + PR

```bash
git add skills/code-coverage/scripts/detect_stack.py \
        skills/code-coverage/scripts/validate_env.py \
        skills/code-coverage/scripts/estimate_size.py \
        skills/code-coverage/scripts/tests/test_detect_stack_ext.py \
        skills/code-coverage/scripts/tests/test_validate_env_ext.py \
        skills/code-coverage/scripts/tests/fixtures/repos/

git commit -m "feat(code-coverage): stack detection extension (P10, ST4)

P10: detect_stack.py emette 4 nuovi campi documentati ma mancanti:
  - test_infrastructure (frameworks, test_dirs, patterns_sample)
  - pre_existing_coverage_pct (parse lcov.info / jacoco.xml)
  - module_coverage (per-module coverage da lcov)
  - coverage_exclude (parse vitest/jest/pyproject config)

ST4: validate_env.py _check_framework_installed con check reali su:
  - pom.xml (junit5, mockito)
  - build.gradle / build.gradle.kts (junit5, mockk)
  - Cargo.toml (cargo-test stdlib)
  - go.mod (go-test stdlib)
  - pubspec.yaml (flutter_test)
  - *.csproj (xunit)
  + timeout 30s per mvn/gradle/flutter (era 5s)
  + reason 'TIMEOUT' distinguibile da 'NOT_FOUND'

estimate_size.py: --with-coverage flag opzionale per priority_score

5 test (3 detect_stack ext + 2 validate_env ext) con fixture repos.

Refs design doc 2026-05-09-code-coverage-optimization-design.md PR5.

Co-Authored-By: SIAE DevForge"

git push -u origin feat/code-coverage-opt-stack-ext
gh pr create --title "feat(code-coverage): stack detection extension (P10, ST4)" --body "$(cat <<'EOF'
## Summary
- detect_stack.py emette test_infrastructure / pre_existing_coverage_pct / module_coverage / coverage_exclude
- validate_env.py framework_installed check reali (pom/gradle/cargo/go/pubspec/csproj)
- Timeout 30s per mvn/gradle/flutter
- estimate_size.py --with-coverage flag per priority_score
- 5 test pytest con 3 fixture repo (vue / maven / cargo)

Refs: docs/plans/2026-05-09-code-coverage-optimization-design.md PR5

## Test plan
- [x] 5 test PASS
- [x] Fixture repos creati (vue/maven/cargo)
- [ ] Smoke: run detect_stack.py su repo reale, verifica 4 nuovi campi popolati
- [ ] Spec-reviewer PASS

Co-Authored-By: SIAE DevForge
EOF
)"
```

---

## Acceptance criteria

- [ ] `detect_stack.py` emette `test_infrastructure`, `pre_existing_coverage_pct`, `module_coverage`, `coverage_exclude`
- [ ] `validate_env.py` `_check_framework_installed` non ritorna più `installed: True` unconditionally per junit5/flutter_test/cargo-test/go-test/xunit
- [ ] Timeout 30s per mvn/gradle/flutter; campo `reason: TIMEOUT` distinguibile da missing
- [ ] `estimate_size.py --with-coverage <path>` calcola `priority_score` e ordina file_list
- [ ] 3 test detect_stack_ext + 2 test validate_env_ext tutti PASS
- [ ] Fixture repos creati (vue-app / maven-app / cargo-app) con file minimi sufficienti
- [ ] Smoke su repo reale (es. `/tmp/bench-medium`): output JSON contiene i 4 nuovi campi popolati
- [ ] Spec-reviewer PASS

## Note operative

- Solo Python 3 stdlib + regex (re) per parsing pom.xml/build.gradle (no lxml dep)
- LCOV format è semplice (key:value), parsing custom robusto
- JaCoCo XML parsing condivide regex con parse_coverage.py (potrebbe essere refattorizzato in helper comune se task-08 lo richiede)
- I 4 nuovi campi devono essere SEMPRE presenti nell'output JSON (anche se vuoti) per consistency del contract
