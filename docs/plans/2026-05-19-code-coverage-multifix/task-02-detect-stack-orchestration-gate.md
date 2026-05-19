# Task 02 — detect_stack.py: orchestration-only gate

**Fix-group:** G1
**ADR riferito:** ADR-1 (IaC + ETL Terragrunt early-exit)
**Stato:** [PENDING]
**Dipendenze:** —

## File modificati

- `skills/code-coverage/scripts/detect_stack.py`
- `skills/code-coverage/scripts/tests/test_detect_stack_ext.py` (extend)

## Test (TDD-first)

Aggiungi a `test_detect_stack_ext.py`:

1. `test_orchestration_only_by_name_iac_suffix`:
   - Setup: tmpdir con `git init` + `git remote add origin git@github.com:itsiae/foobar-iac.git`
   - Chiama `is_orchestration_only_repo(root)` → `(True, "name_pattern_iac")`

2. `test_orchestration_only_by_name_iaac_suffix`:
   - Repo name: `enterpriseplatform-core-iaac` → `(True, "name_pattern_iaac")`

3. `test_orchestration_only_by_content_terraform_dominant`:
   - Setup: 65 file `.tf` + 7 file `.hcl` + zero file `package.json`/`pom.xml`/`requirements.txt`/etc.
   - Atteso: `(True, "terraform_dominant_no_runtime_manifest")`

4. `test_orchestration_only_false_on_terraform_with_lambda`:
   - Setup: 5 file `.tf` + `package.json` con `aws-sdk` dep
   - Atteso: `(False, None)` — c'e' manifest runtime, NON orchestration

5. `test_orchestration_only_false_on_pure_app_repo`:
   - Setup: `package.json` + 30 file `.ts`, zero `.tf`
   - Atteso: `(False, None)`

## Implementazione

In `detect_stack.py`:

1. Nuova funzione `is_orchestration_only_repo(root: Path) -> tuple[bool, str | None]`:
   ```python
   _IAC_NAME_RE = re.compile(r"(?:^|[-/])[\w-]*-(iac|iaac)(?:[-/]|$)", re.IGNORECASE)
   _RUNTIME_MANIFESTS = {
       "package.json", "pom.xml", "build.gradle", "build.gradle.kts",
       "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
       "Pipfile", "poetry.lock", "Cargo.toml", "go.mod",
       "pubspec.yaml", "Gemfile", "composer.json", "*.csproj", "*.fsproj",
   }
   def is_orchestration_only_repo(root: Path) -> tuple[bool, str | None]:
       # 1. By-name check via git remote
       slug = _resolve_github_remote(root)
       if slug and _IAC_NAME_RE.search(slug.split("/")[-1]):
           return True, "name_pattern_iac"
       # 2. By-content check
       has_runtime_manifest = False
       for manifest in _RUNTIME_MANIFESTS:
           if "*" in manifest:
               if any(root.rglob(manifest)):
                   has_runtime_manifest = True
                   break
           elif _find(root, {manifest}):
               has_runtime_manifest = True
               break
       if has_runtime_manifest:
           return False, None
       # Count .tf/.hcl vs total
       tf_hcl = 0
       total = 0
       for _, filenames in _walk(root):
           for f in filenames:
               total += 1
               if f.endswith((".tf", ".hcl", ".tf.json", ".tfvars")):
                   tf_hcl += 1
       if total > 0 and (tf_hcl / total) > 0.5:
           return True, "terraform_dominant_no_runtime_manifest"
       return False, None
   ```

2. In `main()`: chiama prima del resto del flow. Se `orchestration_only=True`, emetti output JSON con campi `orchestration_only`, `orchestration_reason`, e gli altri default (no walk costoso per languages/frameworks).

3. Estendi `_OUTPUT_SCHEMA_DEFAULTS`:
   ```python
   "orchestration_only": False,
   "orchestration_reason": None,
   ```

## Criterio di accettazione

- 5/5 test PASS
- E2E: `detect_stack.py /tmp/dataplatform-dwh-etl-clone` → `orchestration_only=true`, `orchestration_reason="terraform_dominant_no_runtime_manifest"`
- E2E: `detect_stack.py /Users/mazzacuv/Git/siae-dev-forge` → `orchestration_only=false`
