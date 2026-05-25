#!/usr/bin/env python3
"""
validate_env.py — Checks runtime and package manager availability for a repo.
Usage: python validate_env.py <repo_path> [--framework <name>]
Output: JSON to stdout.
Requires: Python 3.8+, stdlib only.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _python_bin() -> str:
    return "python3" if shutil.which("python3") else "python"


def _pip_bin() -> str:
    return "pip3" if shutil.which("pip3") else "pip"


FRAMEWORK_RUNTIME_MAP = {
    "vitest": "node",
    "jest": "node",
    "pytest": "python3",
    "junit5": "java",
    "mockk": "java",
    "go-test": "go",
    "cargo-test": "cargo",
    "xunit": "dotnet",
    "flutter_test": "flutter",
}

RUNTIME_CHECKS = [
    ("node",    ["node", "--version"], "18.0.0", 5),
    ("python3", ["python3", "--version"], "3.10.0", 5),
    ("java",    ["java", "-version"], "17", 30),
    ("go",      ["go", "version"], "1.21", 5),
    ("cargo",   ["cargo", "--version"], "1.70.0", 5),
    ("dotnet",  ["dotnet", "--version"], "8.0.0", 5),
    ("flutter", ["flutter", "--version"], "3.0.0", 30),
]

PM_CHECKS = [
    ("npm",      ["npm", "--version"], 5),
    ("yarn",     ["yarn", "--version"], 5),
    ("pnpm",     ["pnpm", "--version"], 5),
    ("bun",      ["bun", "--version"], 5),
    ("pip",      ["pip3", "--version"], 5),
    ("poetry",   ["poetry", "--version"], 5),
    ("pipenv",   ["pipenv", "--version"], 5),
    ("maven",    ["mvn", "--version"], 30),
    ("gradle",   ["gradle", "--version"], 30),
    ("bundler",  ["bundle", "--version"], 5),
    ("composer", ["composer", "--version"], 5),
]


def _run(cmd: list[str], timeout: int = 5) -> tuple[bool, str, str | None]:
    """Run subprocess. Return (ok, version_line, reason). reason='TIMEOUT' se scaduto."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        output = (result.stdout + result.stderr).strip().splitlines()
        version_line = output[0] if output else ""
        return True, version_line, None
    except subprocess.TimeoutExpired:
        return False, "", "TIMEOUT"
    except (FileNotFoundError, OSError):
        return False, "", None


def _parse_version(version_str: str) -> tuple[int, ...]:
    import re
    nums = re.findall(r"\d+", version_str)
    try:
        return tuple(int(n) for n in nums[:3])
    except ValueError:
        return (0,)


def _version_ok(actual: str, minimum: str) -> bool:
    return _parse_version(actual) >= _parse_version(minimum)


_SKIP_DIRS_VALIDATE = {
    "node_modules", ".git", "dist", "build", "out", "target",
    ".terraform", "vendor", "coverage", "__pycache__", ".venv", "venv",
    ".next", ".nuxt", ".svelte-kit", ".code-coverage",
}


def _find_manifest_recursive(root: Path, filename: str, max_depth: int = 4) -> Path | None:
    """Cerca ``filename`` da ``root`` con walk depth-limited (default 4).

    Skippa directory di build/cache. Ritorna il PRIMO match trovato (BFS-like,
    ma os.walk usa DFS in pratica — accettabile per detection use case).
    Ritorna None se non trovato.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        if depth > max_depth:
            dirnames.clear()
            continue
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS_VALIDATE]
        if filename in filenames:
            return Path(dirpath) / filename
    return None


def _detect_required_framework(repo_path: Path) -> str:
    """Infer the required test framework from repo manifest files.

    Walk depth=4 per supportare layout SIAE serverless con Terraform root +
    Lambda manifest nested (es. ``modules/<service>/lambda-<name>/package.json``).
    Allineato a ``detect_stack._find`` per evitare discrepanze tra detection.
    """
    # Try root-level package.json prima (fast path)
    pkg_json = _find_manifest_recursive(repo_path, "package.json")
    if pkg_json is not None:
        # Condition (a) Principle 4: jest.config.{ts,js,mjs,cjs} accanto al package.json
        pkg_dir = pkg_json.parent
        for cfg_name in ("jest.config.ts", "jest.config.js", "jest.config.mjs", "jest.config.cjs"):
            if (pkg_dir / cfg_name).exists():
                return "jest"
        # Anche al root, per retrocompat
        if pkg_dir != repo_path:
            for cfg_name in ("jest.config.ts", "jest.config.js", "jest.config.mjs", "jest.config.cjs"):
                if (repo_path / cfg_name).exists():
                    return "jest"
        try:
            import json as _json
            pkg = _json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
            all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            scripts = pkg.get("scripts", {})
            vitest_in_deps = any("vitest" in k for k in all_deps)
            test_script = scripts.get("test", "")
            jest_in_deps = any("jest" in k for k in all_deps) and not vitest_in_deps
            jest_in_test_script = "jest" in test_script and "vitest" not in test_script and not vitest_in_deps
            if jest_in_deps or jest_in_test_script:
                return "jest"
            return "vitest"
        except Exception:
            return "vitest"

    # Pyspark sniff prima del fallback pytest generico: allinea il dispatch al branch
    # `pyspark` in stack-matrix.json (test_framework=pytest+chispa). Senza questo check,
    # repository PySpark/Databricks ricadrebbero su pytest standard perdendo il template
    # PySpark e la dep `chispa`.
    for fname in ("pyproject.toml", "requirements.txt"):
        p = _find_manifest_recursive(repo_path, fname)
        if p is None:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            continue
        if "pyspark" in content or "databricks" in content:
            return "pytest+chispa"

    # Fallback su altri manifest, cercati a depth=4
    for fname, fw in [
        ("requirements.txt", "pytest"), ("pyproject.toml", "pytest"),
        ("pom.xml", "junit5"), ("build.gradle.kts", "junit5"), ("build.gradle", "junit5"),
        ("pubspec.yaml", "flutter_test"), ("go.mod", "go-test"),
        ("Cargo.toml", "cargo-test"),
    ]:
        if _find_manifest_recursive(repo_path, fname) is not None:
            return fw

    # *.csproj (glob): cerca con rglob depth-limited via list
    for csproj in repo_path.rglob("*.csproj"):
        try:
            depth = len(csproj.relative_to(repo_path).parts)
        except ValueError:
            continue
        if depth <= 4 and not any(skip in csproj.parts for skip in _SKIP_DIRS_VALIDATE):
            return "xunit"

    return "unknown"


def _check_framework_installed(repo_path: Path, framework: str, manifest_root_rel: str = ".") -> dict:
    """Real check su manifest dei build tool per framework presence (P10/ST4).

    Args:
        repo_path: Repo root.
        framework: Framework name (vitest/jest/pytest/...).
        manifest_root_rel: Relative path da repo_path al manifest dir (default ".").
            Per layout monorepo/nested (es. Terraform root + Lambda nested),
            il manifest del framework vive in ``modules/<svc>/lambda-<name>``,
            non al repo root. Allineato a ``stack.json.manifest_root``.

    Returns: {"installed": bool, "version": str | None, "source": str, "location": str}
    """
    check_root = repo_path / manifest_root_rel if manifest_root_rel not in (".", "") else repo_path

    if framework == "vitest":
        pkg = check_root / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
                dev = {**data.get("devDependencies", {}), **data.get("dependencies", {})}
                if "vitest" in dev:
                    return {"installed": True, "version": dev["vitest"], "source": "package.json", "location": "node_modules/vitest"}
            except Exception:
                pass
        nm = check_root / "node_modules" / "vitest"
        if nm.exists():
            return {"installed": True, "version": None, "source": "node_modules", "location": "node_modules/vitest"}
        return {"installed": False, "version": None, "source": "package.json", "location": "node_modules/vitest"}

    if framework == "jest":
        pkg = check_root / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
                dev = {**data.get("devDependencies", {}), **data.get("dependencies", {})}
                if "jest" in dev:
                    return {"installed": True, "version": dev["jest"], "source": "package.json", "location": "node_modules/jest"}
            except Exception:
                pass
        nm = check_root / "node_modules" / "jest"
        if nm.exists():
            return {"installed": True, "version": None, "source": "node_modules", "location": "node_modules/jest"}
        return {"installed": False, "version": None, "source": "package.json", "location": "node_modules/jest"}

    if framework == "pytest":
        for f in ["pyproject.toml", "requirements-dev.txt", "requirements.txt", "setup.cfg"]:
            p = check_root / f
            if p.exists():
                try:
                    if "pytest" in p.read_text(encoding="utf-8", errors="ignore"):
                        return {"installed": True, "version": None, "source": f, "location": "site-packages/pytest"}
                except Exception:
                    continue
        ok, _, _ = _run([_python_bin(), "-c", "import pytest"])
        if ok:
            return {"installed": True, "version": None, "source": "site-packages", "location": "site-packages/pytest"}
        return {"installed": False, "version": None, "source": "pyproject.toml", "location": "site-packages/pytest"}

    if framework == "junit5":
        pom = check_root / "pom.xml"
        if pom.exists():
            content = pom.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"<artifactId>junit-jupiter(?:-api)?</artifactId>", content):
                return {"installed": True, "version": None, "source": "pom.xml", "location": "Maven dependencies"}
        for gradle_file in ["build.gradle.kts", "build.gradle"]:
            gradle = check_root / gradle_file
            if gradle.exists():
                content = gradle.read_text(encoding="utf-8", errors="ignore")
                if "junit-jupiter" in content or "useJUnitPlatform" in content:
                    return {"installed": True, "version": None, "source": gradle_file, "location": "Gradle dependencies"}
        return {"installed": False, "version": None, "source": "pom.xml | build.gradle", "location": "Maven/Gradle dependencies"}

    if framework == "mockk":
        for gradle_file in ["build.gradle.kts", "build.gradle"]:
            gradle = check_root / gradle_file
            if gradle.exists() and "mockk" in gradle.read_text(encoding="utf-8", errors="ignore"):
                return {"installed": True, "version": None, "source": gradle_file, "location": "Gradle dependencies"}
        return {"installed": False, "version": None, "source": "build.gradle.kts", "location": "Gradle dependencies"}

    if framework == "cargo-test":
        if (check_root / "Cargo.toml").exists():
            return {"installed": True, "version": "stdlib", "source": "Cargo.toml", "location": "cargo (built-in)"}
        return {"installed": False, "version": None, "source": "Cargo.toml", "location": "cargo (built-in)"}

    if framework == "go-test":
        if (check_root / "go.mod").exists():
            return {"installed": True, "version": "stdlib", "source": "go.mod", "location": "go stdlib (built-in)"}
        return {"installed": False, "version": None, "source": "go.mod", "location": "go stdlib (built-in)"}

    if framework == "flutter_test":
        pubspec = check_root / "pubspec.yaml"
        if pubspec.exists() and "flutter_test:" in pubspec.read_text(encoding="utf-8", errors="ignore"):
            return {"installed": True, "version": None, "source": "pubspec.yaml", "location": "flutter SDK (built-in)"}
        return {"installed": False, "version": None, "source": "pubspec.yaml", "location": "flutter SDK"}

    if framework == "xunit":
        for csproj in check_root.rglob("*.csproj"):
            try:
                content = csproj.read_text(encoding="utf-8", errors="ignore")
                if 'Include="xunit"' in content or 'Include="xunit.runner' in content:
                    return {"installed": True, "version": None, "source": str(csproj.relative_to(check_root)), "location": "NuGet packages"}
            except Exception:
                continue
        return {"installed": False, "version": None, "source": "*.csproj", "location": "NuGet packages"}

    return {"installed": False, "version": None, "source": "unknown", "location": "unknown"}


def _build_install_commands(framework: str, repo_path: Path) -> list[str]:
    """Return install commands for the given framework based on detected PM."""
    commands = []

    # Detect package manager
    pm = "npm"
    if (repo_path / "pnpm-lock.yaml").exists():
        pm = "pnpm"
    elif (repo_path / "yarn.lock").exists():
        pm = "yarn"
    elif (repo_path / "bun.lockb").exists():
        pm = "bun"

    if framework == "vitest":
        if pm == "pnpm":
            commands = ["pnpm add -D vitest @vitest/coverage-v8"]
        elif pm == "yarn":
            commands = ["yarn add --dev vitest @vitest/coverage-v8"]
        elif pm == "bun":
            commands = ["bun add -d vitest @vitest/coverage-v8"]
        else:
            commands = ["npm install --save-dev vitest @vitest/coverage-v8"]
    elif framework == "jest":
        if pm == "pnpm":
            commands = ["pnpm add -D jest @types/jest ts-jest"]
        elif pm == "yarn":
            commands = ["yarn add --dev jest @types/jest ts-jest"]
        else:
            commands = ["npm install --save-dev jest @types/jest ts-jest"]
    elif framework == "pytest":
        commands = ["pip install pytest pytest-cov pytest-asyncio pytest-mock"]
    elif framework == "junit5":
        commands = [
            "# Add to pom.xml: junit-jupiter:5.11+, mockito-junit-jupiter:5+, jacoco-maven-plugin:0.8+",
            "# Then run: mvn dependency:resolve",
        ]
    elif framework == "flutter_test":
        commands = [
            "# Add to pubspec.yaml dev_dependencies:",
            "#   flutter_test:",
            "#     sdk: flutter",
            "#   mocktail: ^1.0.0",
            "flutter pub get",
        ]
    elif framework == "cargo-test":
        if sys.platform in ("darwin", "win32"):
            commands = ["cargo install cargo-llvm-cov"]
        else:  # Linux
            commands = ["cargo install cargo-tarpaulin"]
    elif framework == "xunit":
        commands = [
            "dotnet add package xunit",
            "dotnet add package xunit.runner.visualstudio",
            "dotnet add package Moq",
            "dotnet add package coverlet.msbuild",
        ]

    return commands


_ASSERTJ_RE = re.compile(r"<artifactId>\s*assertj-core\s*</artifactId>")

# Task 02: placeholder Maven not defined in pom — pipeline CI iniettava ${appVersion}, ${revision}
_MAVEN_PLACEHOLDER_RE = re.compile(
    r"\$\{(appVersion|revision|sha1|changelist|[a-zA-Z][a-zA-Z0-9_]*\.version)\}"
)
_MAVEN_BUILTIN_TOKENS = {
    "project.version", "pom.version", "project.artifactId", "project.groupId",
    "project.basedir", "pom.basedir", "project.name", "project.build.directory",
    "project.build.finalName", "project.build.outputDirectory",
    "java.version",  # builtin del JVM, non placeholder CI
}
_MAVEN_PLACEHOLDER_DEFAULT = "1.0.0-SNAPSHOT"


def _pom_defines_property(pom_path: Path, name: str) -> bool:
    """True se il pom dichiara <properties><name>...</name></properties>.

    Check shallow: solo properties direttamente nel pom (no parent resolution).
    Task 07 estende con effective-pom risolto.
    """
    try:
        content = Path(pom_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    # Estrai blocco <properties>...</properties> e cerca <name>
    m = re.search(r"<properties>(.*?)</properties>", content, re.DOTALL)
    if not m:
        return False
    return bool(re.search(rf"<{re.escape(name)}\b[^>]*>", m.group(1)))


def _read_overrides(repo_path: Path) -> dict:
    """Legge ``.code-coverage/overrides.json`` se presente.

    Schema (Task 02 sezione):
        {"maven_placeholders": {"appVersion": "2.0.0-RELEASE"}}
    """
    ov = Path(repo_path) / ".code-coverage" / "overrides.json"
    if not ov.is_file():
        return {}
    try:
        return json.loads(ov.read_text(encoding="utf-8", errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return {}


def scan_maven_placeholders(pom_paths: list, overrides: dict | None = None) -> dict:
    """Task 02: scansiona pom per placeholder Maven non risolti.

    Esclude:
    - Built-in Maven (``project.*``, ``pom.*``, ``java.version``)
    - Placeholder definiti localmente nel ``<properties>`` del pom

    Inietta default ``1.0.0-SNAPSHOT`` per ogni placeholder rilevato; può essere
    sovrascritto via overrides.json ``maven_placeholders``.

    Args:
        pom_paths: lista pom.xml (Path).
        overrides: dict opzionale, di solito ``_read_overrides(repo)``.

    Returns:
        dict {placeholder_token: default_value}
    """
    ov_placeholders = (overrides or {}).get("maven_placeholders", {})
    if not isinstance(ov_placeholders, dict):
        ov_placeholders = {}

    found: dict[str, str] = {}
    for pom in pom_paths:
        try:
            content = Path(pom).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for token in _MAVEN_PLACEHOLDER_RE.findall(content):
            if token in _MAVEN_BUILTIN_TOKENS:
                continue
            if _pom_defines_property(pom, token):
                continue
            # Override esplicito utente > default
            value = ov_placeholders.get(token, _MAVEN_PLACEHOLDER_DEFAULT)
            found[token] = value
    return found
# Task 05: regex per estrarre include/exclude da blocco surefire-plugin
_SUREFIRE_PLUGIN_BLOCK_RE = re.compile(
    r"<plugin>\s*(?:<groupId>[^<]+</groupId>\s*)?<artifactId>\s*maven-surefire-plugin\s*</artifactId>(.*?)</plugin>",
    re.DOTALL,
)
_SUREFIRE_INCLUDE_RE = re.compile(r"<include>([^<]+)</include>")
_SUREFIRE_EXCLUDE_RE = re.compile(r"<exclude>([^<]+)</exclude>")
# Pattern surefire "standard" considerati NON restrittivi (default behavior)
_SUREFIRE_DEFAULT_PATTERNS = {
    "**/*Test.java", "**/Test*.java", "**/*Tests.java", "**/*TestCase.java",
}


def detect_surefire_config(pom_path) -> dict:
    """Task 05: estrae <includes>/<excludes> di maven-surefire-plugin da un pom.

    Ritorna ``{'includes': [...], 'excludes': [...], 'restrictive': bool}``.

    ``restrictive=True`` se:
    - include list non vuota
    - AND nessun include matcha pattern standard (``**/*Test.java`` etc.)

    Su pom con configurazione restrittiva, Phase 5 deve allineare naming dei
    test generati (Opzione A) o generare proposed-pom-patches.diff (Opzione B).
    Skill NON modifica autonomamente il pom (Principle 1).
    """
    default = {"includes": [], "excludes": [], "restrictive": False}
    try:
        content = Path(pom_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return default

    block_match = _SUREFIRE_PLUGIN_BLOCK_RE.search(content)
    if not block_match:
        return default

    plugin_block = block_match.group(1)
    includes = [m.strip() for m in _SUREFIRE_INCLUDE_RE.findall(plugin_block) if m.strip()]
    excludes = [m.strip() for m in _SUREFIRE_EXCLUDE_RE.findall(plugin_block) if m.strip()]
    restrictive = bool(includes) and not any(
        inc in _SUREFIRE_DEFAULT_PATTERNS for inc in includes
    )
    return {"includes": includes, "excludes": excludes, "restrictive": restrictive}


_JACOCO_SKIP_RE = re.compile(
    r"<jacoco\.skip>\s*true\s*</jacoco\.skip>", re.IGNORECASE
)


def detect_jacoco_skipped_modules(aggregator_base: Path, modules: list) -> list:
    """Task 06: identifica moduli con ``<jacoco.skip>true</jacoco.skip>``.

    Phase 8 filtra questi moduli dal bundle coverage (evita falsi 0% LINE su
    moduli by-design senza source Java o senza tests — es. siae-pae-bollettino-service
    è solo aggregator).

    Args:
        aggregator_base: dir base contenente i moduli (manifest_root).
        modules: lista nomi modulo da stack.json.maven_aggregator.modules.

    Returns:
        list di nomi modulo con jacoco.skip=true (ordinato per stabilità).
    """
    skipped: list = []
    for mod in modules:
        mod_pom = Path(aggregator_base) / str(mod) / "pom.xml"
        if not mod_pom.is_file():
            continue
        try:
            content = mod_pom.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if _JACOCO_SKIP_RE.search(content):
            skipped.append(mod)
    return skipped


def detect_assertion_lib(pom_paths: list) -> str:
    """Task 04: rileva quale assertion library è presente nei pom.

    Ritorna ``"assertj"`` se ``assertj-core`` presente in almeno UN pom,
    altrimenti ``"junit5_vanilla"`` (fallback: usare ``Assertions.*`` di JUnit5).

    Principle 1: NON modifica autonomamente il pom per aggiungere AssertJ.
    L'utente decide se vuole upgrade — il template vanilla è equivalente.

    Args:
        pom_paths: lista pom.xml da scansionare (Path).

    Returns:
        "assertj" | "junit5_vanilla"
    """
    for pom in pom_paths:
        try:
            content = Path(pom).read_text(encoding="utf-8", errors="ignore")
        except (OSError, AttributeError):
            continue
        if _ASSERTJ_RE.search(content):
            return "assertj"
    return "junit5_vanilla"


def _collect_pom_paths(repo_path: Path, manifest_root_rel: str = ".") -> list[Path]:
    """Raccoglie i pom.xml per detect_assertion_lib: aggregator + tutti i moduli
    figli (path letti da stack.json.maven_aggregator.modules quando disponibile).

    Solo pom letti da ``manifest_root_rel`` o sotto.
    """
    base = repo_path / manifest_root_rel if manifest_root_rel not in (".", "") else repo_path
    poms: list[Path] = []
    root_pom = base / "pom.xml"
    if root_pom.is_file():
        poms.append(root_pom)
    # Carica moduli da stack.json se disponibile
    stack_path = repo_path / ".code-coverage" / "stack.json"
    if stack_path.is_file():
        try:
            stack = json.loads(stack_path.read_text(encoding="utf-8", errors="ignore"))
            agg = stack.get("maven_aggregator") or {}
            for mod in agg.get("modules", []):
                mod_pom = base / str(mod) / "pom.xml"
                if mod_pom.is_file():
                    poms.append(mod_pom)
        except (json.JSONDecodeError, OSError):
            pass
    return poms


def _is_safe_gradlew(gradlew_path: Path, repo_root: Path) -> bool:
    """Return True only if gradlew is inside repo_root and has no unsafe permission bits.

    Prevents execution of a malicious gradlew planted in an untrusted repository.
    Checks:
      1. Resolved path is strictly under repo_root (no symlink escape).
      2. File is not world-writable (mode & 0o002) or group-writable (mode & 0o020).
         World-writable executables are a common indicator of tampering.
    """
    try:
        resolved = gradlew_path.resolve()
        repo_resolved = repo_root.resolve()
        # Must be a descendant of repo_root
        resolved.relative_to(repo_resolved)
        stat = resolved.stat()
        # Reject world-writable or group-writable
        if stat.st_mode & 0o022:
            return False
        return True
    except (OSError, ValueError):
        return False


def main() -> None:
    if sys.version_info < (3, 8):
        print(json.dumps({"error": f"Python 3.8+ required. Found: {sys.version}"}), file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: validate_env.py <repo_path> [--framework <name>]"}),
              file=sys.stderr)
        sys.exit(1)

    repo_path = Path(sys.argv[1]).resolve()
    if not repo_path.is_dir():
        print(json.dumps({"error": f"Not a directory: {repo_path}"}), file=sys.stderr)
        sys.exit(1)

    # Optional explicit framework override
    framework = None
    if "--framework" in sys.argv:
        idx = sys.argv.index("--framework")
        if idx + 1 < len(sys.argv):
            framework = sys.argv[idx + 1]
    if framework is None:
        framework = _detect_required_framework(repo_path)

    # ADR-2: leggi manifest_root da .code-coverage/stack.json (se presente)
    # per supportare layout monorepo/nested (TF root + Lambda nested).
    manifest_root_rel = "."
    stack_json_path = repo_path / ".code-coverage" / "stack.json"
    if stack_json_path.is_file():
        try:
            stack_data = json.loads(stack_json_path.read_text(encoding="utf-8", errors="ignore"))
            mr = stack_data.get("manifest_root")
            if isinstance(mr, str) and mr.strip():
                manifest_root_rel = mr.strip()
        except (json.JSONDecodeError, OSError):
            manifest_root_rel = "."

    available = []
    missing = []
    blocking = False

    py_bin = _python_bin()
    pip_bin = _pip_bin()
    runtime_checks = list(RUNTIME_CHECKS)
    runtime_checks[1] = ("python3", [py_bin, "--version"], "3.10.0", 5)
    pm_checks = list(PM_CHECKS)
    pm_checks[4] = ("pip", [pip_bin, "--version"], 5)

    for tool, cmd, min_ver, timeout in runtime_checks:
        ok, version_line, reason = _run(cmd, timeout=timeout)
        entry = {"tool": tool, "version": version_line, "min_required": min_ver, "ok": ok}
        if reason:
            entry["reason"] = reason
        if ok:
            entry["version_ok"] = _version_ok(version_line, min_ver)
            available.append(entry)
        else:
            missing.append(entry)

    for tool, cmd, timeout in pm_checks:
        ok, version_line, reason = _run(cmd, timeout=timeout)
        if ok:
            available.append({"tool": tool, "version": version_line, "ok": True})
        elif reason == "TIMEOUT":
            available.append({"tool": tool, "version": None, "ok": False, "reason": "TIMEOUT"})

    # B-03: prefer ./gradlew wrapper over global gradle for enterprise repos
    gradlew_bin = repo_path / "gradlew"
    gradlew_bat = repo_path / "gradlew.bat"
    gradlew_path = gradlew_bin if gradlew_bin.exists() else (gradlew_bat if gradlew_bat.exists() else None)
    if gradlew_path:
        available = [e for e in available if e["tool"] != "gradle"]
        missing = [e for e in missing if e.get("tool") != "gradle"]
        if not _is_safe_gradlew(gradlew_path, repo_path):
            available.append({"tool": "gradle", "version": "wrapper present (skipped — safety check failed)", "ok": False})
        else:
            ok_gw, ver_gw, reason_gw = _run([str(gradlew_path), "--version"], timeout=30)
            label = f"wrapper: {ver_gw}" if ok_gw else "wrapper present (run failed — JDK required)"
            entry = {"tool": "gradle", "version": label, "ok": True}
            if reason_gw:
                entry["reason"] = reason_gw
            available.append(entry)

    fw_status = _check_framework_installed(repo_path, framework, manifest_root_rel)
    if not fw_status["installed"]:
        blocking = framework in ("unknown",)
        missing.append({
            "tool": framework,
            "location": fw_status["location"],
            "ok": False,
        })

    # B-02: block if the primary runtime required by this framework is absent
    required_runtime = FRAMEWORK_RUNTIME_MAP.get(framework)
    if required_runtime and any(t.get("tool") == required_runtime for t in missing):
        blocking = True

    # Task 04: assertion-lib-probe per Java (junit5/junit5+mockk).
    # Per stack non-Java, lascia field a None.
    assertion_lib = None
    maven_placeholders: dict = {}
    surefire_config: dict = {"includes": [], "excludes": [], "restrictive": False}
    if framework in ("junit5", "junit5+mockk"):
        pom_paths = _collect_pom_paths(repo_path, manifest_root_rel)
        assertion_lib = detect_assertion_lib(pom_paths)
        # Task 02: maven-placeholder-inject — scan + emit defaults.
        overrides_data = _read_overrides(repo_path)
        maven_placeholders = scan_maven_placeholders(pom_paths, overrides=overrides_data)
        # Task 05: surefire-includes-detect — root pom (aggregator); Phase 5
        # legge anche moduli individuali se Phase 7 entra in loop.
        if pom_paths:
            surefire_config = detect_surefire_config(pom_paths[0])

    # Task 06: jacoco-skip-detect — filtra moduli by-design (no source / no tests).
    skipped_modules: list = []
    if framework in ("junit5", "junit5+mockk"):
        try:
            stack_data = json.loads(
                (repo_path / ".code-coverage" / "stack.json").read_text(
                    encoding="utf-8", errors="ignore"
                )
            )
            agg = stack_data.get("maven_aggregator") or {}
            modules = agg.get("modules") or []
            if modules:
                agg_base = repo_path / agg.get("manifest_root", ".")
                skipped_modules = detect_jacoco_skipped_modules(agg_base, modules)
        except (json.JSONDecodeError, OSError, FileNotFoundError):
            pass

    raw_install_commands = _build_install_commands(framework, repo_path)
    # ADR-2: prefix install commands con `cd <manifest_root_rel> &&` se nested.
    # Commenti (linee che iniziano con "#") restano invariati per leggibilità.
    if manifest_root_rel not in (".", ""):
        prefix = f"cd {manifest_root_rel} && "
        install_commands = [
            (cmd if cmd.lstrip().startswith("#") else prefix + cmd)
            for cmd in raw_install_commands
        ]
    else:
        install_commands = raw_install_commands

    print(json.dumps({
        "repo_path": str(repo_path),
        "required_framework": framework,
        "manifest_root": manifest_root_rel,
        "framework_installed": fw_status["installed"],
        "framework_check": {framework: fw_status},
        "available": available,
        "missing": missing,
        "install_commands": install_commands,
        "blocking": blocking,
        "assertion_lib": assertion_lib,
        "skipped_modules": skipped_modules,
        "maven_placeholders": maven_placeholders,
        "surefire_config": surefire_config,
    }, indent=2))


if __name__ == "__main__":
    main()
