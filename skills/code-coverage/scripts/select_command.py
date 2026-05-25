#!/usr/bin/env python3
"""Risolve framework->stack + selezione build-system/OS -> cov_cmd/report_path/format.

Letto da SKILL.md Phase 6. Sostituisce il jq lookup diretto che usava la chiave
``required_framework`` (framework name) contro ``stack-matrix.json`` indicizzato
per stack name.

Output: JSON su stdout. Exit 0 sempre; errori veicolati in ``error`` field.
Compatibile Python 3.8+.

Usage:
    python3 scripts/select_command.py <repo_path>
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

# Framework -> stack key in stack-matrix.json (vitest risolto via architecture_style)
FW_TO_STACK = {
    "vitest": None,
    "jest": "javascript_jest_fallback",
    "pytest": "python",
    "pytest+chispa": "pyspark",
    "junit5": "java",
    "junit5+mockk": "kotlin",
    "go-test": "go",
    "testing": "go",
    "cargo-test": "rust",
    "xunit": "csharp",
    "flutter_test": "flutter",
    "rspec": "ruby",
    "phpunit": "php",
}


def emit(stack="", cmd="", path="", fmt="", error=None, manifest_root="."):
    print(json.dumps({
        "stack": stack,
        "cov_cmd": cmd,
        "report_path": path,
        "format": fmt,
        "error": error,
        "manifest_root": manifest_root,
    }))
    sys.exit(0)


# JaCoCo plugin snippet completo (Maven). ADR-10: includere <executions> per
# prepare-agent (bind a phase initialize via default) e report (bind a phase test).
# Emesso come actionable error quando pom.xml non wireppa il plugin.
_JACOCO_PLUGIN_SNIPPET = """\
<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
  <version>0.8.12</version>
  <executions>
    <execution>
      <id>prepare-agent</id>
      <goals><goal>prepare-agent</goal></goals>
    </execution>
    <execution>
      <id>report</id>
      <phase>test</phase>
      <goals><goal>report</goal></goals>
    </execution>
  </executions>
</plugin>"""


def _pom_has_jacoco_plugin(pom_path):
    """True se ``pom.xml`` contiene ``<artifactId>jacoco-maven-plugin</artifactId>``.

    Check testuale (no XML parse) per resilienza a pom.xml malformati / commenti.
    Una sola sotto-stringa basta: il plugin Maven richiede artifactId esatto.
    """
    try:
        content = pom_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return "<artifactId>jacoco-maven-plugin</artifactId>" in content


def _read_manifest_root(repo_root):
    """Legge ``manifest_root`` da ``stack.json`` (Task 03). Fallback ``"."``.

    Resiliente a stack.json mancante / malformato: ritorna ``"."`` senza errore.
    Consumer (SKILL.md Phase 6 via phase6-coverage.sh) usa il valore per ``cd``
    esplicito prima di eseguire ``cov_cmd`` (vedi Task 11 ADR-11 eval hardening).
    """
    try:
        data = json.loads((repo_root / ".code-coverage" / "stack.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return "."
    mr = data.get("manifest_root", ".")
    return mr if isinstance(mr, str) and mr else "."


def _read_maven_aggregator(repo_root):
    """Legge ``maven_aggregator`` da ``stack.json`` (Task 01). Ritorna None se assente.

    Resiliente a stack.json mancante / malformato. Contiene aggregator_pom,
    modules, selection_reason.
    """
    try:
        data = json.loads((repo_root / ".code-coverage" / "stack.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    agg = data.get("maven_aggregator")
    return agg if isinstance(agg, dict) and agg.get("aggregator_pom") else None


def detect_os():
    s = platform.system()
    return "macos" if s == "Darwin" else "windows" if s == "Windows" else "linux"


def resolve_stack(framework, repo_root):
    if framework not in FW_TO_STACK:
        return None, f"framework '{framework}' not mapped to any stack"
    mapped = FW_TO_STACK[framework]
    if mapped is not None:
        return mapped, None
    # vitest -> javascript_* via architecture_style
    try:
        stack_data = json.loads((repo_root / ".code-coverage" / "stack.json").read_text())
    except FileNotFoundError:
        return None, "stack.json not found (required for vitest stack resolution)"
    except json.JSONDecodeError as e:
        return None, f"stack.json invalid JSON: {e}"
    arch = stack_data.get("architecture_style", "")
    if arch == "frontend-spa":
        return "javascript_frontend", None
    if arch == "serverless":
        return "javascript_serverless", None
    return "javascript_node", None


def _is_maven_multi_module(pom_path):
    """True se ``pom.xml`` contiene un tag ``<modules>`` con almeno un ``<module>``.

    Single-module Maven (caso comune SIAE sport-*-service, pae-*) -> emit path
    canonico ``target/site/jacoco/jacoco.xml`` per leggibilita' anche prima della
    prima build.
    """
    try:
        content = pom_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    import re as _re
    m = _re.search(r"<modules\b[^>]*>(.*?)</modules>", content, _re.DOTALL)
    if not m:
        return False
    return bool(_re.search(r"<module>\s*[\w\-./]+\s*</module>", m.group(1)))


def _resolve_jacoco_report_path(repo_root, stack_def, has_pom, aggregator=None):
    """Risolve coverage_report_path per Java/JaCoCo con supporto multi-module.

    Args:
        aggregator: dict ``maven_aggregator`` (Task 01). Se presente, il pom
            "root logico" è ``aggregator['aggregator_pom']`` (subdir), non
            ``repo_root/pom.xml``.

    Preferenze in ordine:
    1. jacoco-aggregate report esistente (single XML certificato dal plugin aggregate)
    2. Path single-module se pom NON ha ``<modules>`` (canonical, anche pre-build)
    3. Path single-module file effettivamente presente (gradle o pre-build maven)
    4. Repo root come directory (parse_coverage.py jacoco multi via rglob)
    """
    # 1. jacoco-aggregate (Maven aggregate plugin / Gradle jacocoRootReport)
    for agg in repo_root.rglob("target/site/jacoco-aggregate/jacoco.xml"):
        return str(agg.relative_to(repo_root))
    for agg in repo_root.rglob("build/reports/jacoco/jacocoRootReport/jacocoRootReport.xml"):
        return str(agg.relative_to(repo_root))

    single_key = "coverage_report_path_maven" if has_pom else "coverage_report_path_gradle"
    single_path = stack_def.get(single_key)

    # 2. Maven single-module noto (pom senza <modules>) -> emit canonical path
    # Task 01: con aggregator rilevato, controlla il pom in subdir
    if has_pom and single_path:
        if aggregator is not None:
            pom = repo_root / aggregator["aggregator_pom"]
        else:
            pom = repo_root / "pom.xml"
        if pom.is_file() and not _is_maven_multi_module(pom):
            # Path rilativo all'aggregator dir, non al repo root
            if aggregator is not None:
                return f"{aggregator['manifest_root']}/{single_path}"
            return single_path

    # 3. Path single-module file esistente (eventuale pre-build leftover)
    if single_path and (repo_root / single_path).is_file():
        return single_path

    # 4. Fallback directory -> parse_coverage.py jacoco multi
    return "."


def select_fields(stack_key, stack_def, repo_root, os_name, aggregator=None):
    """Ritorna (cov_cmd, report_path, fmt, error). Dispatch unificato per java/kotlin/rust.

    Args:
        aggregator: dict da ``stack.json.maven_aggregator`` (Task 01). Se non
            None, il pom Maven vive in ``aggregator['aggregator_pom']`` (subdir).
            Il comando viene esteso con ``-f <aggregator_pom>``.
    """
    has_root_pom = (repo_root / "pom.xml").is_file()
    has_pom = has_root_pom or aggregator is not None
    has_gradle = (repo_root / "build.gradle.kts").is_file() or (repo_root / "build.gradle").is_file()

    if stack_key == "java":
        if has_pom:
            # Task 01: prioritizza aggregator pom rilevato in subdir.
            if aggregator is not None:
                pom = repo_root / aggregator["aggregator_pom"]
            else:
                pom = repo_root / "pom.xml"
            if not _pom_has_jacoco_plugin(pom):
                err = (
                    f"jacoco-maven-plugin not configured in {pom.relative_to(repo_root)}. "
                    "Add this to <build><plugins> section:\n" + _JACOCO_PLUGIN_SNIPPET
                )
                return None, None, None, err
            cmd = stack_def.get("coverage_command_maven")
            # Task 01: se aggregator in subdir, inject -f <aggregator_pom>.
            # Pattern: "mvn test jacoco:report" → "mvn -f <pom> test jacoco:report".
            # Idempotent: skip se cmd già contiene -f.
            if aggregator is not None and cmd and " -f " not in cmd:
                cmd = cmd.replace("mvn ", f"mvn -f {aggregator['aggregator_pom']} ", 1)
        elif has_gradle:
            cmd_key = "coverage_command_gradle_windows" if os_name == "windows" else "coverage_command_gradle"
            cmd = stack_def.get(cmd_key) or stack_def.get("coverage_command_gradle")
        else:
            return None, None, None, "java stack detected but no pom.xml/build.gradle(.kts) found"
        # Multi-module support: prefer jacoco-aggregate report se presente, altrimenti
        # ritorna repo root come directory (parse_coverage.py jacoco multi via rglob).
        path = _resolve_jacoco_report_path(repo_root, stack_def, has_pom, aggregator=aggregator)
        fmt = stack_def.get("coverage_report_format", "jacoco")
        return cmd, path, fmt, None

    if stack_key == "kotlin":
        cmd_key = "coverage_command_gradle_windows" if os_name == "windows" else "coverage_command_gradle"
        cmd = stack_def.get(cmd_key) or stack_def.get("coverage_command_gradle")
        path = stack_def.get("coverage_report_path")
        fmt = stack_def.get("coverage_report_format", "kover")
        return cmd, path, fmt, None

    if stack_key == "rust":
        cmd = stack_def.get(f"coverage_command_{os_name}")
        path = stack_def.get(f"coverage_report_path_{os_name}")
        fmt = "cargo-tarpaulin" if os_name == "linux" else "cargo-llvm-cov"
        return cmd, path, fmt, None

    # Default: scalar fields + format override per stack che richiedono nuovi parser
    cmd = stack_def.get("coverage_command")
    path = stack_def.get("coverage_report_path")
    fmt = stack_def.get("coverage_report_format", "")
    if stack_key == "csharp":
        fmt = "dotnet-cobertura"
    elif stack_key in ("flutter", "ruby"):
        fmt = "lcov"
    return cmd, path, fmt, None


def main():
    parser = argparse.ArgumentParser(description="Resolve framework->stack + build/OS selection for Phase 6.")
    parser.add_argument("repo_path", help="Repo target absolute path")
    args = parser.parse_args()

    repo_root = Path(args.repo_path)
    env_path = repo_root / ".code-coverage" / "env.json"

    # manifest_root letto early — sopravvive a ogni branch di errore in emit().
    manifest_root = _read_manifest_root(repo_root)

    try:
        env = json.loads(env_path.read_text())
    except FileNotFoundError:
        emit(error=f"env.json not found at {env_path}", manifest_root=manifest_root)
    except json.JSONDecodeError as e:
        emit(error=f"env.json invalid JSON: {e}", manifest_root=manifest_root)

    framework = env.get("required_framework", "")
    if not framework or framework == "unknown":
        emit(error=f"required_framework is '{framework or 'missing'}' - no stack resolvable", manifest_root=manifest_root)

    stack_key, err = resolve_stack(framework, repo_root)
    if err or not stack_key:
        emit(error=err or "stack resolution failed", manifest_root=manifest_root)

    matrix_path = Path(__file__).resolve().parent.parent / "assets" / "stack-matrix.json"
    try:
        matrix = json.loads(matrix_path.read_text())
    except FileNotFoundError:
        emit(stack=stack_key, error=f"stack-matrix.json not found at {matrix_path}", manifest_root=manifest_root)
    except json.JSONDecodeError as e:
        emit(stack=stack_key, error=f"stack-matrix.json invalid JSON: {e}", manifest_root=manifest_root)

    stack_def = matrix.get("stacks", {}).get(stack_key)
    if stack_def is None:
        emit(stack=stack_key, error=f"stack '{stack_key}' not in stack-matrix.json", manifest_root=manifest_root)

    # Task 01: legge aggregator info da stack.json (può essere None per repo
    # mono-pom o non-Maven).
    aggregator = _read_maven_aggregator(repo_root)
    cmd, path, fmt, err = select_fields(stack_key, stack_def, repo_root, detect_os(), aggregator=aggregator)
    if err or not cmd or not path:
        emit(stack=stack_key, cmd=cmd or "", path=path or "", fmt=fmt or "", error=err or "command/path/format resolution failed", manifest_root=manifest_root)

    emit(stack=stack_key, cmd=cmd, path=path, fmt=fmt, manifest_root=manifest_root)


if __name__ == "__main__":
    main()
