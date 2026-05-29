#!/usr/bin/env python3
"""detect_jest_incompat.py - Evaluate Jest/Vitest compatibility signals per workspace.

Reads `assets/vitest-jest-compat.json` and applies I1..I10 to each JS/TS workspace
in the repo. Writes `.code-coverage/jest-compat.json` and prints it to stdout.

Decision values:
  - "vitest-default"  : no jest artifacts, use Vitest
  - "vitest-migrate"  : jest artifacts present + no incompat signals -> migrate
  - "jest-incompat"   : incompat signal fired -> keep Jest
  - "jest-forced"     : I10 user opt-out -> keep Jest

Exit 0 always (errors in payload). Compatible with Python 3.8+.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".venv",
    "target", "coverage", ".code-coverage",
}

JEST_CONFIG_NAMES = (
    "jest.config.ts", "jest.config.js", "jest.config.mjs",
    "jest.config.cjs", "jest.config.json",
)
NVM_FILES = (".nvmrc", ".node-version")


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _read_json(p: Path) -> dict:
    try:
        return json.loads(_read_text(p))
    except (json.JSONDecodeError, ValueError):
        return {}


def _find_jest_config(ws: Path) -> Path | None:
    for name in JEST_CONFIG_NAMES:
        cand = ws / name
        if cand.is_file():
            return cand
    pkg = _read_json(ws / "package.json")
    if isinstance(pkg.get("jest"), dict):
        return ws / "package.json"
    return None


def _jest_config_text(ws: Path) -> str:
    cfg = _find_jest_config(ws)
    if cfg is None:
        return ""
    if cfg.name == "package.json":
        pkg = _read_json(cfg)
        return json.dumps(pkg.get("jest", {}))
    return _read_text(cfg)


def _detect_jest_artifacts(ws: Path) -> tuple[bool, list[str]]:
    artifacts: list[str] = []
    pkg = _read_json(ws / "package.json")
    scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
    test_script = str(scripts.get("test", "")) if scripts else ""
    all_deps = {
        **(pkg.get("dependencies") or {}),
        **(pkg.get("devDependencies") or {}),
    }
    vitest_active = ("vitest" in test_script) or any("vitest" in k for k in all_deps)

    cfg = _find_jest_config(ws)
    if cfg is not None:
        artifacts.append(f"stale-config:{cfg.name}:vitest-active" if vitest_active
                         else f"config:{cfg.name}")
    if "jest" in test_script and "vitest" not in test_script:
        artifacts.append(f"script:test='{test_script[:60]}'")
    jest_deps = [
        k for k in all_deps
        if k == "jest" or k.startswith("jest-")
        or k in ("@types/jest", "ts-jest", "babel-jest", "@swc/jest", "@jest/globals")
    ]
    if jest_deps:
        artifacts.append(f"stale-deps:{','.join(jest_deps[:5])}" if vitest_active
                         else f"deps:{','.join(jest_deps[:5])}")
    return bool(artifacts), artifacts


def _parse_version_tuple(spec: str) -> tuple[int, int, int] | None:
    m = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", spec)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0))


def _version_lt(spec: str, ref: str) -> bool:
    a = _parse_version_tuple(spec)
    b = _parse_version_tuple(ref)
    if a is None or b is None:
        return False
    return a < b


# ---- Detection primitives ------------------------------------------------

def _check_package_dep_present(ws: Path, names: list[str]) -> bool:
    pkg = _read_json(ws / "package.json")
    deps = pkg.get("dependencies") or {}
    return any(n in deps for n in names)


def _check_package_devdep_present(ws: Path, names: list[str]) -> bool:
    pkg = _read_json(ws / "package.json")
    devdeps = pkg.get("devDependencies") or {}
    return any(n in devdeps for n in names)


def _check_package_dep_prefix(ws: Path, prefix: str) -> bool:
    pkg = _read_json(ws / "package.json")
    all_deps = {
        **(pkg.get("dependencies") or {}),
        **(pkg.get("devDependencies") or {}),
    }
    return any(k.startswith(prefix) for k in all_deps)


def _check_file_exists(ws: Path, files: list[str]) -> bool:
    return any((ws / f).is_file() for f in files)


def _check_regex_in_jest_config(ws: Path, pattern: str) -> bool:
    text = _jest_config_text(ws)
    if not text:
        return False
    return bool(re.search(pattern, text))


def _check_package_json_lacks(ws: Path, names: list[str]) -> bool:
    pkg = _read_json(ws / "package.json")
    all_deps = {
        **(pkg.get("dependencies") or {}),
        **(pkg.get("devDependencies") or {}),
    }
    return not any(n in all_deps for n in names)


def _check_engines_node_lt(ws: Path, ref: str) -> bool:
    pkg = _read_json(ws / "package.json")
    engines = pkg.get("engines") or {}
    spec = str(engines.get("node", ""))
    if not spec:
        return False
    return _version_lt(spec, ref)


def _check_nvmrc_lt(ws: Path, ref: str) -> bool:
    for name in NVM_FILES:
        p = ws / name
        if p.is_file():
            v = _read_text(p).strip().lstrip("v")
            if v and _version_lt(v, ref):
                return True
    return False


def _check_jest_version_lt(ws: Path, ref: str) -> bool:
    pkg = _read_json(ws / "package.json")
    devdeps = pkg.get("devDependencies") or {}
    deps = pkg.get("dependencies") or {}
    spec = devdeps.get("jest") or deps.get("jest") or ""
    if not spec:
        return False
    return _version_lt(spec, ref)


def _check_jest_config_transform_outside_allowlist(
    ws: Path, allowlist: list[str],
) -> bool:
    text = _jest_config_text(ws)
    if not text:
        return False
    m = re.search(r"transform\s*:\s*\{([^}]+)\}", text, re.DOTALL)
    if not m:
        return False
    block = m.group(1)
    pairs = re.findall(
        r"['\"]([^'\"]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]",
        block,
    )
    if not pairs:
        return False
    for _src, transformer in pairs:
        if not any(safe in transformer for safe in allowlist):
            return True
    return False


def _check_test_environment_outside_allowlist(
    ws: Path, allowlist: list[str],
) -> bool:
    text = _jest_config_text(ws)
    if not text:
        return False
    m = re.search(r"testEnvironment\s*:\s*['\"]([^'\"]+)['\"]", text)
    if not m:
        return False
    return m.group(1) not in allowlist


def _check_env_var(name: str, value: str) -> bool:
    return os.environ.get(name) == value


def _check_overrides_force_jest(repo_root: Path) -> bool:
    ov = repo_root / ".code-coverage" / "overrides.json"
    if not ov.is_file():
        return False
    data = _read_json(ov)
    return bool(data.get("force_jest"))


def _overrides_force_jest_reason(repo_root: Path) -> str:
    ov = repo_root / ".code-coverage" / "overrides.json"
    if not ov.is_file():
        return ""
    data = _read_json(ov)
    if not data.get("force_jest"):
        return ""
    return str(data.get("force_jest_reason", ""))


# ---- Generic check dispatcher --------------------------------------------

def _evaluate_check(check: dict, ws: Path, repo_root: Path) -> bool:
    kind = check.get("kind", "")
    try:
        if kind == "package_dep_present":
            return _check_package_dep_present(ws, check["names"])
        if kind == "package_devdep_present":
            return _check_package_devdep_present(ws, check["names"])
        if kind == "package_dep_prefix":
            return _check_package_dep_prefix(ws, check["prefix"])
        if kind == "file_exists":
            return _check_file_exists(ws, check["files"])
        if kind == "regex_in_jest_config":
            return _check_regex_in_jest_config(ws, check["pattern"])
        if kind == "package_json_lacks":
            return _check_package_json_lacks(ws, check["names"])
        if kind == "engines_node_lt":
            return _check_engines_node_lt(ws, check["version"])
        if kind == "nvmrc_lt":
            return _check_nvmrc_lt(ws, check["version"])
        if kind == "jest_version_lt":
            return _check_jest_version_lt(ws, check["version"])
        if kind == "jest_config_transform_outside_allowlist":
            return _check_jest_config_transform_outside_allowlist(
                ws, check["allowlist"],
            )
        if kind == "test_environment_outside_allowlist":
            return _check_test_environment_outside_allowlist(
                ws, check["allowlist"],
            )
        if kind == "env_var":
            return _check_env_var(check["name"], check["value"])
        if kind == "overrides_force_jest":
            return _check_overrides_force_jest(repo_root)
        if kind == "any_of":
            return any(
                _evaluate_check(c, ws, repo_root)
                for c in check.get("checks", [])
            )
        if kind == "all_of":
            return all(
                _evaluate_check(c, ws, repo_root)
                for c in check.get("checks", [])
            )
    except Exception:
        return False
    return False


def _evaluate_signal(sig_def: dict, ws: Path, repo_root: Path) -> bool:
    detect = sig_def.get("detect", {})
    if not detect:
        return False
    return _evaluate_check(detect, ws, repo_root)


# ---- Workspace enumeration -----------------------------------------------

def _enumerate_workspaces(repo_root: Path) -> list[Path]:
    workspaces: list[Path] = []
    for pkg in repo_root.rglob("package.json"):
        if any(part in SKIP_DIRS for part in pkg.parts):
            continue
        workspaces.append(pkg.parent)
    return workspaces or [repo_root]


# ---- Main evaluation -----------------------------------------------------

def evaluate(repo_root: Path) -> dict:
    compat_path = (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "vitest-jest-compat.json"
    )
    try:
        compat = json.loads(compat_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {
            "version": "1.0.0",
            "workspaces": {},
            "error": f"compat asset unreadable: {e}",
        }

    signals = compat.get("incompatibility_signals", {})
    out_workspaces: dict[str, Any] = {}

    for ws_dir in _enumerate_workspaces(repo_root):
        rel = "." if ws_dir == repo_root else str(ws_dir.relative_to(repo_root))
        fired: list[str] = []
        for sig_code, sig_def in signals.items():
            if _evaluate_signal(sig_def, ws_dir, repo_root):
                fired.append(sig_code)

        has_artifacts, artifacts = _detect_jest_artifacts(ws_dir)
        force_ok = _check_overrides_force_jest(repo_root)
        force_reason = _overrides_force_jest_reason(repo_root)

        if "I10" in fired:
            decision = "jest-forced"
            decision_reason = (
                f"force-jest-override:{force_reason}"
                if force_reason else "force-jest-override:env-var"
            )
        elif fired:
            decision = "jest-incompat"
            decision_reason = f"hard-incompat:{','.join(fired)}"
        elif has_artifacts:
            decision = "vitest-migrate"
            decision_reason = "jest-legacy-migrating-to-vitest"
        else:
            decision = "vitest-default"
            decision_reason = "vitest-first-default"

        out_workspaces[rel] = {
            "has_jest_artifacts": has_artifacts,
            "jest_artifacts": artifacts,
            "incompatibility_signals": fired,
            "force_jest": force_ok,
            "force_jest_reason": force_reason or None,
            "decision": decision,
            "decision_reason": decision_reason,
        }

    return {"version": "1.0.0", "workspaces": out_workspaces, "error": None}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate Jest/Vitest compatibility signals.",
    )
    parser.add_argument("repo_path", help="Repo target absolute path")
    args = parser.parse_args()
    repo = Path(args.repo_path).resolve()
    if not repo.is_dir():
        payload = {
            "version": "1.0.0",
            "workspaces": {},
            "error": f"not a directory: {repo}",
        }
        print(json.dumps(payload, indent=2))
        sys.exit(0)

    result = evaluate(repo)

    out_dir = repo / ".code-coverage"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "jest-compat.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
