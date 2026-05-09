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


def _detect_required_framework(repo_path: Path) -> str:
    """Infer the required test framework from repo manifest files."""
    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        try:
            import json as _json
            pkg = _json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
            all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            scripts = pkg.get("scripts", {})
            vitest_in_deps = any("vitest" in k for k in all_deps)
            # Condition (a): explicit jest config file is checked by detect_stack.py, not here
            # Condition (b): scripts.test contains "jest" AND vitest NOT in devDependencies
            test_script = scripts.get("test", "")
            jest_in_deps = any("jest" in k for k in all_deps) and not vitest_in_deps
            jest_in_test_script = "jest" in test_script and "vitest" not in test_script and not vitest_in_deps
            if jest_in_deps or jest_in_test_script:
                return "jest"
            return "vitest"
        except Exception:
            return "vitest"

    for fname, fw in [
        ("requirements.txt", "pytest"), ("pyproject.toml", "pytest"),
        ("pom.xml", "junit5"), ("build.gradle.kts", "junit5"),
        ("pubspec.yaml", "flutter_test"), ("go.mod", "go-test"),
        ("Cargo.toml", "cargo-test"), ("*.csproj", "xunit"),
    ]:
        if fname.startswith("*"):
            matches = list(repo_path.glob(fname))
            if matches:
                return fw
        elif (repo_path / fname).exists():
            return fw

    return "unknown"


def _check_framework_installed(repo_path: Path, framework: str) -> dict:
    """Real check su manifest dei build tool per framework presence (P10/ST4).

    Returns: {"installed": bool, "version": str | None, "source": str, "location": str}
    """
    if framework == "vitest":
        pkg = repo_path / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
                dev = {**data.get("devDependencies", {}), **data.get("dependencies", {})}
                if "vitest" in dev:
                    return {"installed": True, "version": dev["vitest"], "source": "package.json", "location": "node_modules/vitest"}
            except Exception:
                pass
        nm = repo_path / "node_modules" / "vitest"
        if nm.exists():
            return {"installed": True, "version": None, "source": "node_modules", "location": "node_modules/vitest"}
        return {"installed": False, "version": None, "source": "package.json", "location": "node_modules/vitest"}

    if framework == "jest":
        pkg = repo_path / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
                dev = {**data.get("devDependencies", {}), **data.get("dependencies", {})}
                if "jest" in dev:
                    return {"installed": True, "version": dev["jest"], "source": "package.json", "location": "node_modules/jest"}
            except Exception:
                pass
        nm = repo_path / "node_modules" / "jest"
        if nm.exists():
            return {"installed": True, "version": None, "source": "node_modules", "location": "node_modules/jest"}
        return {"installed": False, "version": None, "source": "package.json", "location": "node_modules/jest"}

    if framework == "pytest":
        for f in ["pyproject.toml", "requirements-dev.txt", "requirements.txt", "setup.cfg"]:
            p = repo_path / f
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
        pom = repo_path / "pom.xml"
        if pom.exists():
            content = pom.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"<artifactId>junit-jupiter(?:-api)?</artifactId>", content):
                return {"installed": True, "version": None, "source": "pom.xml", "location": "Maven dependencies"}
        for gradle_file in ["build.gradle.kts", "build.gradle"]:
            gradle = repo_path / gradle_file
            if gradle.exists():
                content = gradle.read_text(encoding="utf-8", errors="ignore")
                if "junit-jupiter" in content or "useJUnitPlatform" in content:
                    return {"installed": True, "version": None, "source": gradle_file, "location": "Gradle dependencies"}
        return {"installed": False, "version": None, "source": "pom.xml | build.gradle", "location": "Maven/Gradle dependencies"}

    if framework == "mockk":
        for gradle_file in ["build.gradle.kts", "build.gradle"]:
            gradle = repo_path / gradle_file
            if gradle.exists() and "mockk" in gradle.read_text(encoding="utf-8", errors="ignore"):
                return {"installed": True, "version": None, "source": gradle_file, "location": "Gradle dependencies"}
        return {"installed": False, "version": None, "source": "build.gradle.kts", "location": "Gradle dependencies"}

    if framework == "cargo-test":
        if (repo_path / "Cargo.toml").exists():
            return {"installed": True, "version": "stdlib", "source": "Cargo.toml", "location": "cargo (built-in)"}
        return {"installed": False, "version": None, "source": "Cargo.toml", "location": "cargo (built-in)"}

    if framework == "go-test":
        if (repo_path / "go.mod").exists():
            return {"installed": True, "version": "stdlib", "source": "go.mod", "location": "go stdlib (built-in)"}
        return {"installed": False, "version": None, "source": "go.mod", "location": "go stdlib (built-in)"}

    if framework == "flutter_test":
        pubspec = repo_path / "pubspec.yaml"
        if pubspec.exists() and "flutter_test:" in pubspec.read_text(encoding="utf-8", errors="ignore"):
            return {"installed": True, "version": None, "source": "pubspec.yaml", "location": "flutter SDK (built-in)"}
        return {"installed": False, "version": None, "source": "pubspec.yaml", "location": "flutter SDK"}

    if framework == "xunit":
        for csproj in repo_path.rglob("*.csproj"):
            try:
                content = csproj.read_text(encoding="utf-8", errors="ignore")
                if 'Include="xunit"' in content or 'Include="xunit.runner' in content:
                    return {"installed": True, "version": None, "source": str(csproj.relative_to(repo_path)), "location": "NuGet packages"}
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

    fw_status = _check_framework_installed(repo_path, framework)
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

    install_commands = _build_install_commands(framework, repo_path)

    print(json.dumps({
        "repo_path": str(repo_path),
        "required_framework": framework,
        "framework_installed": fw_status["installed"],
        "framework_check": {framework: fw_status},
        "available": available,
        "missing": missing,
        "install_commands": install_commands,
        "blocking": blocking,
    }, indent=2))


if __name__ == "__main__":
    main()
