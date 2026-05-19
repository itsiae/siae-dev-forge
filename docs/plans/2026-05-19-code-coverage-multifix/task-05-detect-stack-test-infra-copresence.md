# Task 05 — detect_stack.py: test_infrastructure co-presence fix

**Fix-group:** G12
**ADR riferito:** ADR-12 (require *.test.* file inside dir)
**Stato:** [PENDING]
**Dipendenze:** —

## File modificati

- `skills/code-coverage/scripts/detect_stack.py`
- `skills/code-coverage/scripts/tests/test_detect_stack_ext.py` (extend)

## Test (TDD-first)

1. `test_test_dirs_excludes_source_dir_named_test`:
   - Setup: `src/api/test/route.ts` (route directory, no `*.test.*` inside)
   - Atteso: `test_dirs` NON include `src/api/test`

2. `test_test_dirs_includes_dir_with_test_file`:
   - Setup: `src/__tests__/cognito-auth.test.ts`
   - Atteso: `test_dirs` include `src/__tests__`

3. `test_test_dirs_python_test_underscore_prefix`:
   - Setup: `tests/test_pipeline.py`
   - Atteso: `test_dirs` include `tests`

4. `test_test_dirs_java_test_suffix`:
   - Setup: `src/test/java/PaymentServiceTest.java`
   - Atteso: `test_dirs` include `src/test/java`

## Implementazione

In `detect_stack.py.detect_test_infrastructure`:

```python
def _dir_contains_test_files(dir_path: Path) -> bool:
    """True se la dir contiene almeno un file con pattern test riconoscibile."""
    test_patterns = (
        "*.test.ts", "*.test.tsx", "*.test.js", "*.test.jsx",
        "*.spec.ts", "*.spec.js",
        "test_*.py", "*_test.py",
        "*Test.java", "*IT.java", "*Test.kt",
        "*_test.go", "*_test.rs",
    )
    for pat in test_patterns:
        try:
            if any(dir_path.glob(pat)):
                return True
            if any(dir_path.rglob(pat)):
                return True
        except OSError:
            pass
    return False

def detect_test_infrastructure(repo_path: Path, frameworks: list[str]) -> dict:
    test_dirs = []
    for d in ["__tests__", "tests", "test", "spec"]:
        for found in repo_path.rglob(d):
            if not found.is_dir():
                continue
            if any(excl in str(found) for excl in ("node_modules", ".venv", "target", "dist", "build", ".git")):
                continue
            # NEW: require co-presence di almeno 1 file test
            if _dir_contains_test_files(found):
                test_dirs.append(str(found.relative_to(repo_path)))
    test_dirs = sorted(set(test_dirs))[:10]
    # ... resto invariato
```

## Criterio di accettazione

- 4/4 test PASS
- E2E: `detect_stack.py /tmp/jarvis-bff-clone` → `test_dirs` NON contiene `modules/service/lambda/src/api/test` (route dir, no test files inside)
