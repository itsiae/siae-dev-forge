# Task 03 — detect_stack.py: manifest_root surfacing

**Fix-group:** G2
**ADR riferito:** ADR-2 (manifest_root field per monorepo)
**Stato:** [PENDING]
**Dipendenze:** —

## File modificati

- `skills/code-coverage/scripts/detect_stack.py`
- `skills/code-coverage/scripts/tests/test_detect_stack_ext.py` (extend)

## Test (TDD-first)

1. `test_manifest_root_flat_repo`:
   - Setup: `package.json` a root, no nested
   - Atteso: `manifest_root="."`

2. `test_manifest_root_nested_lambda_modules_service`:
   - Setup: root `package.json` con solo husky, `modules/service/lambda/package.json` con vitest + test script
   - Atteso: `manifest_root="modules/service/lambda"`

3. `test_detect_monorepo_extended_modules_pattern`:
   - Setup: tmpdir con `<root>/package.json` (solo husky in deps) + `<root>/modules/service/lambda/package.json` (con vitest + scripts.test)
   - Atteso: `detect_monorepo(root) == True`

4. `test_manifest_root_picks_deepest_with_test_script`:
   - Setup: 2 nested package.json, solo uno ha `scripts.test`
   - Atteso: manifest_root = path di quello con test script

## Implementazione

In `detect_stack.py`:

1. Nuova funzione `detect_manifest_root(root: Path) -> str`:
   ```python
   def detect_manifest_root(root: Path) -> str:
       """Trova il PIU' DEEP manifest (package.json/pom.xml/pyproject.toml)
       che dichiara un test script o test framework. Default ``"."``.
       """
       candidates = []
       for dirpath, filenames in _walk(root, max_depth=4):
           rel = dirpath.relative_to(root)
           rel_str = "." if str(rel) == "." else str(rel)
           for fname in ("package.json", "pom.xml", "pyproject.toml", "build.gradle", "build.gradle.kts"):
               if fname in filenames:
                   has_tests = _manifest_declares_tests(dirpath / fname)
                   candidates.append((rel_str, has_tests, len(rel.parts)))
       if not candidates:
           return "."
       # Preferenza: has_tests=True > deepest
       candidates.sort(key=lambda x: (not x[1], -x[2]))
       return candidates[0][0]

   def _manifest_declares_tests(manifest_path: Path) -> bool:
       fname = manifest_path.name
       if fname == "package.json":
           pkg = _read_json_safe(manifest_path)
           scripts = pkg.get("scripts", {})
           deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
           if any("test" in k.lower() for k in scripts.keys()):
               return True
           if any(k in deps for k in ("vitest", "jest", "mocha", "@vitest/coverage-v8")):
               return True
           return False
       text = _read_text_safe(manifest_path).lower()
       return any(kw in text for kw in ("junit", "pytest", "spring-boot-starter-test", "testng"))
   ```

2. Estendi `detect_monorepo()` per riconoscere `modules/*/package.json` o `modules/*/*/package.json`:
   ```python
   def detect_monorepo(root: Path) -> bool:
       # ... existing checks ...
       child_count = 0
       for d in ["packages", "apps", "services", "modules"]:
           dpath = root / d
           if dpath.is_dir():
               # Direct: packages/<x>/package.json
               child_count += sum(1 for _ in dpath.glob("*/package.json"))
               # Nested: modules/<x>/<y>/package.json (SIAE canonical)
               child_count += sum(1 for _ in dpath.glob("*/*/package.json"))
       return child_count >= 2 or (child_count >= 1 and (root / "package.json").exists())
   ```

3. In `main()` estendi output: `"manifest_root": detect_manifest_root(root)`.

4. Estendi `_OUTPUT_SCHEMA_DEFAULTS`: `"manifest_root": "."`.

## Criterio di accettazione

- 4/4 test PASS
- E2E: `detect_stack.py /tmp/uptime-console-backend-clone` → `manifest_root="modules/service/lambda"`, `monorepo=true`
- E2E: `detect_stack.py /Users/mazzacuv/Git/siae-dev-forge` → `manifest_root="."`
