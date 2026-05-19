# Task 07 — validate_env.py: manifest_root path resolution

**Fix-group:** G2
**ADR riferito:** ADR-2
**Stato:** [PENDING]
**Dipendenze:** Task 03 (manifest_root field)

## File modificati

- `skills/code-coverage/scripts/validate_env.py`
- `skills/code-coverage/scripts/tests/test_validate_env_ext.py` (extend)

## Test (TDD-first)

1. `test_check_framework_installed_walks_to_manifest_root`:
   - Setup: tmpdir con root `package.json` (no vitest) + `modules/service/lambda/package.json` (con vitest + node_modules)
   - `stack.json` con `manifest_root="modules/service/lambda"`
   - Atteso: `framework_installed=true` (cerca in manifest_root, non in root)

2. `test_install_commands_target_manifest_root`:
   - Setup: required framework vitest, manifest_root nested, vitest NON installato
   - Atteso: `install_commands` include un prefisso `cd modules/service/lambda && ...` o comunque path-aware

## Implementazione

In `validate_env.py`:

1. Verifica preliminare signature corrente: `_check_framework_installed(repo_path, framework)` — l'arg ORDER e' `(repo_path, framework)`. Aggiungi terzo arg con default `"."`:

   ```python
   import json
   def _check_framework_installed(repo_path: Path, framework: str, manifest_root_rel: str = ".") -> bool:
       check_root = repo_path / manifest_root_rel if manifest_root_rel != "." else repo_path
       pkg_path = check_root / "package.json"
       if not pkg_path.is_file():
           return False
       try:
           pkg = json.loads(pkg_path.read_text(encoding="utf-8", errors="ignore"))
       except (json.JSONDecodeError, OSError):
           return False
       deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
       if framework in deps:
           node_modules = check_root / "node_modules" / framework
           return node_modules.exists()
       return False
   ```
   **NB:** `_read_json_safe` NON esiste in `validate_env.py` (verificato con grep — 0 match). Usare il pattern `json.loads + try/except` inline mostrato nello snippet `_check_framework_installed` qui sopra.

2. In `main()`: leggi `manifest_root` da `.code-coverage/stack.json` (se esiste, default `"."`). Passa a tutti i call site di `_check_framework_installed(repo_path, fw, manifest_root_rel)`.

3. Estendi install_commands con prefisso cd se manifest_root != ".":
   ```python
   prefix = f"cd {manifest_root_rel} && " if manifest_root_rel != "." else ""
   install_commands = [prefix + cmd for cmd in raw_install_commands]
   ```

## Criterio di accettazione

- 2/2 test PASS
- E2E: nessuna regressione su flat repo (manifest_root=".")
