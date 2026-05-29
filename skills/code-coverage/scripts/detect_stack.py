#!/usr/bin/env python3
"""
detect_stack.py — Infers tech stack from repository layout.
Usage: python detect_stack.py <repo_path>
Output: JSON to stdout.
Requires: Python 3.8+, stdlib only.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

_SECRET_PATTERNS = (
    ".env", "*.env", ".env.*",
    "*.pem", "*.key", "*.p12", "*.pfx", "*.crt",
    "*credentials*", "*secret*", "*secrets*",
    "id_rsa", "id_ed25519", "id_ecdsa",
    "aws_credentials", "aws_config",
    "*.ovpn",
)
_MAX_FILE_BYTES = 100 * 1024  # 100 KB


def _is_secret_file(path: Path) -> bool:
    name = path.name.lower()
    return any(fnmatch.fnmatch(name, pat) for pat in _SECRET_PATTERNS)


def _read_json_safe(path: Path) -> dict:
    if _is_secret_file(path):
        return {}
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return {}
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}


def _read_text_safe(path: Path) -> str:
    if _is_secret_file(path):
        return ""
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


# URL forms supportati:
#   https://github.com/owner/repo[.git][/]
#   https://user:token@github.com/owner/repo[.git][/]
#   git@github.com:owner/repo[.git]
#   git@github.com-<alias>:owner/repo[.git]      (SSH multi-account)
#   ssh://git@github.com[:port]/owner/repo[.git]
#   git+ssh://git@github.com/owner/repo[.git]
# Owner non può contenere `/`; repo può contenere `.` (ma rimuoviamo solo `.git` finale).
_GITHUB_HOST_RE = re.compile(r"github\.com(?:-[\w-]+)?")


def _parse_github_owner_repo(url: str) -> Optional[str]:
    """Estrai ``owner/repo`` da un URL git remote in qualunque forma supportata.

    Logica robusta in 3 step:
    1. trim trailing `/`, `.git`, query/fragment
    2. localizza host `github.com` (con eventuale alias SSH `-name`)
    3. raccogli `path` post-host: salta `:port` se presente, salta `:`, prende
       prossimi due path segment ``owner`` e ``repo``

    Ritorna None se URL non è GitHub o malformato.
    """
    if not url:
        return None
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    # Trova host github.com (con eventuale -alias per SSH multi-account)
    m = _GITHUB_HOST_RE.search(url)
    if not m:
        return None
    after_host = url[m.end():]
    # after_host inizia con ':' (SSH/SSH-port) o '/' (https)
    if after_host.startswith(":"):
        after_host = after_host[1:]
        # Skip porta numerica se presente: "22/owner/repo" -> "owner/repo"
        port_m = re.match(r"^(\d+)/(.+)$", after_host)
        if port_m:
            after_host = port_m.group(2)
    elif after_host.startswith("/"):
        after_host = after_host[1:]
    else:
        return None
    # Ora after_host è "owner/repo" o "owner/repo/extra"
    parts = after_host.split("/")
    if len(parts) < 2:
        return None
    owner = parts[0]
    repo = parts[1]
    if not owner or not repo:
        return None
    return f"{owner}/{repo}"


def _resolve_github_remote(repo_path: Path) -> Optional[str]:
    """Estrai ``owner/repo`` da ``git remote get-url origin``.

    Ritorna None se: git non disponibile, repo senza remote, remote non-GitHub,
    timeout. Side-effect free, non solleva eccezioni.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return _parse_github_owner_repo(result.stdout.strip())


_IAC_NAME_RE = re.compile(r"(?:^|[-/])[\w-]*-(iac|iaac)(?:[-/]|$)", re.IGNORECASE)

_RUNTIME_MANIFESTS = {
    "package.json", "pom.xml", "build.gradle", "build.gradle.kts",
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "Pipfile", "poetry.lock", "Cargo.toml", "go.mod",
    "pubspec.yaml", "Gemfile", "composer.json", "*.csproj", "*.fsproj",
}


def is_orchestration_only_repo(root: Path) -> Tuple[bool, Optional[str]]:
    """Detect IaC/orchestration-only repos (Terraform, Terragrunt) senza runtime code.

    Two-step:
      1. By-name: ``-iac`` o ``-iaac`` suffix nel repo slug GitHub.
      2. By-content: nessun manifest runtime (package.json/pom.xml/etc.) e
         >50%% dei file sono ``.tf``/``.hcl``/``.tfvars``.

    Ritorna (True, reason) per orchestration-only, (False, None) altrimenti.
    """
    # 1. By-name check via git remote
    slug = _resolve_github_remote(root)
    if slug:
        repo_name = slug.split("/")[-1]
        m = _IAC_NAME_RE.search(repo_name)
        if m:
            return True, f"name_pattern_{m.group(1).lower()}"

    # 2. By-content check
    has_runtime_manifest = False
    for manifest in _RUNTIME_MANIFESTS:
        if "*" in manifest:
            try:
                if any(root.rglob(manifest)):
                    has_runtime_manifest = True
                    break
            except OSError:
                continue
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


def read_github_coverage_variable(repo_path: Path) -> Tuple[float, str]:
    """Legge ``TEST_COVERAGE_PERCENTAGE`` come repository variable GitHub.

    Pattern: ``gh variable get TEST_COVERAGE_PERCENTAGE -R <owner/repo>``.
    Ritorna (value, source) dove source vale ``"github_variable"`` (var trovata
    e parsabile) oppure ``"missing"`` (gh assente, non autenticato, repo
    non-GitHub, var assente, timeout, valore non parsabile).

    Convenzione: var assente == no tests configurati lato repo → baseline 0.0.
    """
    repo_slug = _resolve_github_remote(repo_path)
    if not repo_slug:
        return 0.0, "missing"
    try:
        result = subprocess.run(
            ["gh", "variable", "get", "TEST_COVERAGE_PERCENTAGE", "-R", repo_slug],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return 0.0, "missing"
    if result.returncode != 0:
        return 0.0, "missing"
    raw = result.stdout.strip().rstrip("%").strip()
    try:
        value = float(raw)
    except ValueError:
        return 0.0, "missing"
    return value, "github_variable"


_SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "out", "target",
    ".terraform", "vendor", "coverage", "__pycache__", ".venv", "venv",
    ".next", ".nuxt", ".svelte-kit",
}


def _walk(root: Path, max_depth: int = 10):
    """Walk filesystem skip dir di build/cache.

    max_depth=10 supporta layout Java enterprise SIAE (es.
    ``src/main/java/it/siae/<modulo>/<package>/<sub>/<file>.java``,
    depth 7-11). Coerente con ``estimate_size.py`` walk.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        if depth > max_depth:
            dirnames.clear()
            continue
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        yield Path(dirpath), filenames


def _find(root: Path, names: set[str]) -> list[Path]:
    found = []
    for dirpath, filenames in _walk(root, max_depth=4):
        for name in names:
            if name in filenames:
                found.append(dirpath / name)
    return found


def detect_languages(root: Path) -> list[str]:
    ext_map = {
        ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
        ".py": "python",
        ".java": "java",
        ".kt": "kotlin", ".kts": "kotlin",
        ".dart": "dart",
        ".go": "go",
        ".rs": "rust",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
        ".scala": "scala",
    }
    langs: set[str] = set()
    for _, filenames in _walk(root):
        for f in filenames:
            ext = Path(f).suffix.lower()
            if ext in ext_map:
                langs.add(ext_map[ext])
    return sorted(langs)


def detect_frameworks(root: Path) -> list[str]:
    fw: set[str] = set()

    for pkg_path in _find(root, {"package.json"}):
        pkg = _read_json_safe(pkg_path)
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        mapping = {
            "react": "react", "next": "next.js", "vue": "vue", "nuxt": "nuxt",
            "@angular/core": "angular", "svelte": "svelte",
            "@remix-run/react": "remix", "astro": "astro",
            "express": "express", "fastify": "fastify", "koa": "koa",
            "@nestjs/core": "nestjs", "aws-cdk": "aws-cdk",
            "@sst/core": "sst", "serverless": "serverless",
        }
        for dep_key, fw_name in mapping.items():
            if any(dep_key in k for k in deps):
                fw.add(fw_name)
        if any("aws-sdk" in k or "@aws-sdk" in k for k in deps):
            fw.add("lambda")

    for p in _find(root, {"requirements.txt", "pyproject.toml"}):
        text = _read_text_safe(p).lower()
        for kw, name in [
            ("fastapi", "fastapi"), ("flask", "flask"), ("django", "django"),
            ("celery", "celery"), ("pyspark", "pyspark"), ("databricks", "databricks"),
        ]:
            if kw in text:
                fw.add(name)

    poms = _find(root, {"pom.xml"})
    if poms:
        pom = _read_text_safe(poms[0]).lower()
        for kw, name in [("spring-boot", "spring-boot"), ("quarkus", "quarkus"), ("micronaut", "micronaut")]:
            if kw in pom:
                fw.add(name)

    if _find(root, {"pubspec.yaml"}):
        fw.add("flutter")

    go_mods = _find(root, {"go.mod"})
    if go_mods:
        go_mod = _read_text_safe(go_mods[0])
        for kw, name in [("gin-gonic/gin", "gin"), ("labstack/echo", "echo"), ("gofiber/fiber", "fiber"), ("go-chi/chi", "chi")]:
            if kw in go_mod:
                fw.add(name)

    return sorted(fw)


def detect_package_managers(root: Path) -> list[str]:
    checks = [
        ("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"),
        ("package-lock.json", "npm"), ("bun.lockb", "bun"),
        ("requirements.txt", "pip"), ("Pipfile", "pipenv"),
        ("poetry.lock", "poetry"), ("pom.xml", "maven"),
        ("build.gradle.kts", "gradle"), ("build.gradle", "gradle"),
        ("Gemfile", "bundler"), ("composer.json", "composer"),
        ("go.sum", "go-modules"), ("Cargo.lock", "cargo"),
    ]
    seen: set[str] = set()
    pms = []
    for fname, pm in checks:
        if _find(root, {fname}) and pm not in seen:
            pms.append(pm)
            seen.add(pm)
    return pms


def detect_build_systems(root: Path) -> list[str]:
    checks = [
        ("vite.config.ts", "vite"), ("vite.config.js", "vite"),
        ("webpack.config.js", "webpack"), ("turbo.json", "turborepo"),
        ("nx.json", "nx"), ("pom.xml", "maven"),
        ("build.gradle.kts", "gradle"), ("build.gradle", "gradle"),
        ("Makefile", "make"), ("Cargo.toml", "cargo"),
        ("go.mod", "go-build"),
    ]
    seen: set[str] = set()
    bs = []
    for fname, name in checks:
        if _find(root, {fname}) and name not in seen:
            bs.append(name)
            seen.add(name)
    return bs


_MAVEN_MODULES_BLOCK_RE = re.compile(r"<modules>(.*?)</modules>", re.DOTALL)
_MAVEN_MODULE_ENTRY_RE = re.compile(r"<module>([^<]+)</module>")
_MAVEN_PACKAGING_POM_RE = re.compile(r"<packaging>\s*pom\s*</packaging>", re.IGNORECASE)
_MAVEN_JACOCO_PLUGIN_RE = re.compile(r"<artifactId>\s*jacoco-maven-plugin\s*</artifactId>")
_MAVEN_JUNIT5_RE = re.compile(r"<artifactId>\s*junit-jupiter(?:-api)?\s*</artifactId>")
_POM_MAXDEPTH_DEFAULT = 4
_GRADLE_INCLUDE_KOTLIN_RE = re.compile(r"include\(([^)]*)\)")
_GRADLE_QUOTED_RE = re.compile(r"['\"]([^'\"]+)['\"]")
_GRADLE_INCLUDE_GROOVY_BLOCK_RE = re.compile(
    r"include\s+(['\"][^'\"]+['\"](?:\s*,\s*['\"][^'\"]+['\"])*)"
)


def detect_monorepo_workspaces(root: Path) -> list[str]:
    """Estrae i workspace path Maven (pom.xml ``<modules>``) e Gradle
    (settings.gradle[.kts] ``include``).

    Maven: parse ``<modules><module>name</module>...</modules>`` (top-level pom).
    Gradle: parse ``include 'a'``, ``include "a", "b:c"``, ``include('a', 'b:c')``.
    Path Gradle ``a:b:c`` viene normalizzato a ``a/b/c``.

    Ritorna lista deduplicata in ordine di scoperta (Maven prima, poi Gradle).
    """
    workspaces: list[str] = []
    seen: set[str] = set()

    # Maven reactor (top-level pom)
    pom_path = root / "pom.xml"
    if pom_path.is_file():
        content = _read_text_safe(pom_path)
        for block in _MAVEN_MODULES_BLOCK_RE.findall(content):
            for module in _MAVEN_MODULE_ENTRY_RE.findall(block):
                module = module.strip()
                if module and module not in seen:
                    workspaces.append(module)
                    seen.add(module)

    # Gradle multi-module (top-level settings.gradle[.kts])
    for fname in ("settings.gradle", "settings.gradle.kts"):
        spath = root / fname
        if not spath.is_file():
            continue
        content = _read_text_safe(spath)
        # Strip line comments (// ...) per evitare match dentro a commenti
        sanitized_lines = []
        for line in content.splitlines():
            idx = line.find("//")
            sanitized_lines.append(line[:idx] if idx != -1 else line)
        sanitized = "\n".join(sanitized_lines)

        raw_modules: list[str] = []
        if fname.endswith(".kts"):
            # Kotlin DSL: include("a", "b:c") — extract args, then all quoted strings
            for args in _GRADLE_INCLUDE_KOTLIN_RE.findall(sanitized):
                raw_modules.extend(_GRADLE_QUOTED_RE.findall(args))
        else:
            # Groovy DSL: include 'a', 'b:c'
            for m in _GRADLE_INCLUDE_GROOVY_BLOCK_RE.finditer(sanitized):
                raw_modules.extend(_GRADLE_QUOTED_RE.findall(m.group(1)))

        for raw in raw_modules:
            # Gradle usa ':' come separator: ':services:api' o 'services:api' -> 'services/api'
            normalized = raw.strip().lstrip(":").replace(":", "/")
            if normalized and normalized not in seen:
                workspaces.append(normalized)
                seen.add(normalized)

    return workspaces


def _find_pom_files(root: Path, max_depth: int = _POM_MAXDEPTH_DEFAULT) -> list[Path]:
    """Lista pom.xml fino a max_depth, esclude node_modules/target/.code-coverage."""
    result: list[Path] = []
    for dirpath, filenames in _walk(root, max_depth=max_depth):
        depth = len(dirpath.relative_to(root).parts)
        if depth > max_depth:
            continue
        if "pom.xml" in filenames:
            result.append(dirpath / "pom.xml")
    return result


def detect_maven_aggregator(root: Path, max_depth: int | None = None) -> dict | None:
    """Cerca un pom aggregator Maven (Task 01) in `root` con walk depth-limited.

    Selezione deterministica in priorità:
    1. Pom con ``<packaging>pom</packaging>`` AND ``<modules>`` non vuoto
       (aggregator vero). In caso di multipli match, vince il PIU' SHALLOW
       (depth minore = aggregator radice). A parità di depth, ordine
       lessicografico.
    2. Fallback: pom con ``jacoco-maven-plugin`` AND ``junit-jupiter`` deps
       (modulo con tooling unit-test coerente).

    Args:
        root: repo root path.
        max_depth: profondità walk. Default 4 (configurabile via env var
            ``CC_POM_MAXDEPTH``).

    Returns:
        dict con chiavi ``manifest_root``, ``aggregator_pom``, ``modules``,
        ``selection_reason``, oppure None se non trovato.
    """
    if max_depth is None:
        env_val = os.environ.get("CC_POM_MAXDEPTH")
        try:
            max_depth = int(env_val) if env_val else _POM_MAXDEPTH_DEFAULT
        except ValueError:
            max_depth = _POM_MAXDEPTH_DEFAULT

    # Override esplicito utente via .code-coverage/overrides.json (AC 4)
    overrides_path = root / ".code-coverage" / "overrides.json"
    if overrides_path.is_file():
        try:
            ov = json.loads(overrides_path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(ov, dict) and ov.get("aggregator_pom"):
                agg_rel = str(ov["aggregator_pom"])
                manifest_rel = str(ov.get("manifest_root") or str(Path(agg_rel).parent))
                pom_abs = root / agg_rel
                modules: list[str] = []
                if pom_abs.is_file():
                    try:
                        content = pom_abs.read_text(encoding="utf-8", errors="ignore")
                        modules = [m.strip() for m in _MAVEN_MODULE_ENTRY_RE.findall(content) if m.strip()]
                    except OSError:
                        pass
                return {
                    "manifest_root": manifest_rel,
                    "aggregator_pom": agg_rel,
                    "modules": modules,
                    "selection_reason": "user-override",
                }
        except (json.JSONDecodeError, OSError):
            pass

    poms = _find_pom_files(root, max_depth=max_depth)
    if not poms:
        return None

    aggregator_candidates: list[tuple[int, str, Path, list[str]]] = []
    fallback_candidates: list[tuple[int, str, Path]] = []

    for pom_path in poms:
        try:
            content = pom_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        depth = len(pom_path.relative_to(root).parts) - 1  # parent dir depth
        rel_parent = pom_path.parent.relative_to(root)
        rel_parent_str = "." if str(rel_parent) == "." else str(rel_parent)

        # Priorità 1: packaging-pom + modules non vuoti
        if _MAVEN_PACKAGING_POM_RE.search(content):
            mods = [m.strip() for m in _MAVEN_MODULE_ENTRY_RE.findall(content) if m.strip()]
            if mods:
                aggregator_candidates.append((depth, rel_parent_str, pom_path, mods))
                continue

        # Priorità 2: fallback jacoco + junit5
        if _MAVEN_JACOCO_PLUGIN_RE.search(content) and _MAVEN_JUNIT5_RE.search(content):
            fallback_candidates.append((depth, rel_parent_str, pom_path))

    if aggregator_candidates:
        # PIU' SHALLOW vince; tiebreak ordine lessicografico
        aggregator_candidates.sort(key=lambda t: (t[0], t[1]))
        depth, rel_parent_str, pom_path, mods = aggregator_candidates[0]
        agg_rel = str(pom_path.relative_to(root))
        return {
            "manifest_root": rel_parent_str,
            "aggregator_pom": agg_rel,
            "modules": mods,
            "selection_reason": "packaging-pom-with-modules",
        }

    if fallback_candidates:
        # PIU' SHALLOW vince; tiebreak ordine lessicografico
        fallback_candidates.sort(key=lambda t: (t[0], t[1]))
        depth, rel_parent_str, pom_path = fallback_candidates[0]
        agg_rel = str(pom_path.relative_to(root))
        return {
            "manifest_root": rel_parent_str,
            "aggregator_pom": agg_rel,
            "modules": [],
            "selection_reason": "jacoco-junit5-fallback",
        }

    return None


def detect_monorepo(root: Path) -> bool:
    if _find(root, {"turbo.json", "nx.json", "lerna.json", "pnpm-workspace.yaml", "rush.json"}):
        return True
    pkg = _read_json_safe(root / "package.json")
    if "workspaces" in pkg:
        return True
    # Maven reactor / Gradle multi-module
    if detect_monorepo_workspaces(root):
        return True
    child_count = 0
    for d in ["packages", "apps", "services", "modules"]:
        dpath = root / d
        if dpath.is_dir():
            # Direct: <d>/<x>/package.json
            child_count += sum(1 for _ in dpath.glob("*/package.json"))
            # Nested SIAE-canonical: <d>/<x>/<y>/package.json (es. modules/service/lambda/)
            child_count += sum(1 for _ in dpath.glob("*/*/package.json"))
    if child_count >= 2:
        return True
    # Edge case: 1 nested child + root package.json (root husky-only + nested lambda real pkg)
    return child_count >= 1 and (root / "package.json").exists()


def _manifest_declares_tests(manifest_path: Path) -> bool:
    """True se il manifest dichiara test framework o test script."""
    fname = manifest_path.name
    if fname == "package.json":
        pkg = _read_json_safe(manifest_path)
        scripts = pkg.get("scripts", {})
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if any("test" in k.lower() for k in scripts.keys()):
            return True
        return any(k in deps for k in ("vitest", "jest", "mocha", "@vitest/coverage-v8"))
    text = _read_text_safe(manifest_path).lower()
    return any(kw in text for kw in ("junit", "pytest", "spring-boot-starter-test", "testng"))


def detect_manifest_root(root: Path) -> str:
    """Trova il PIU' DEEP manifest che dichiara test. Default ``"."``.

    ADR-2: per repo SIAE monorepo Terraform-root con TS Lambda annidato
    (``modules/service/lambda/package.json``), il "real" manifest e' nested,
    non il root husky-only. Phase 4/6 useranno questo path per ``cd``.
    """
    candidates: list[tuple[str, bool, int]] = []
    for dirpath, filenames in _walk(root, max_depth=4):
        rel = dirpath.relative_to(root)
        rel_str = "." if str(rel) == "." else str(rel)
        for fname in ("package.json", "pom.xml", "pyproject.toml", "build.gradle", "build.gradle.kts"):
            if fname in filenames:
                has_tests = _manifest_declares_tests(dirpath / fname)
                candidates.append((rel_str, has_tests, len(rel.parts)))
    if not candidates:
        return "."
    # Preferenza: has_tests=True > deepest path
    candidates.sort(key=lambda x: (not x[1], -x[2]))
    return candidates[0][0]


def detect_ci_cd(root: Path) -> list[str]:
    ci = []
    checks = [
        (".github/workflows", "github-actions"),
        (".gitlab-ci.yml", "gitlab-ci"),
        ("Jenkinsfile", "jenkins"),
        (".circleci/config.yml", "circleci"),
        ("azure-pipelines.yml", "azure-devops"),
        ("bitbucket-pipelines.yml", "bitbucket"),
        (".travis.yml", "travis"),
        ("buildspec.yml", "aws-codebuild"),
    ]
    for path_str, name in checks:
        if (root / path_str).exists():
            ci.append(name)
    return ci


def detect_architecture(root: Path, frameworks: list[str]) -> str:
    fw_set = set(frameworks)
    if fw_set & {"react", "next.js", "vue", "nuxt", "angular", "svelte", "astro"}:
        return "frontend-spa"
    if fw_set & {"lambda", "sst", "serverless", "aws-cdk"}:
        return "serverless"
    if fw_set & {"express", "fastify", "koa", "nestjs"}:
        return "microservices" if detect_monorepo(root) else "backend-api"
    if fw_set & {"pyspark", "databricks"}:
        return "data-pipeline"
    if fw_set & {"spring-boot", "quarkus", "micronaut"}:
        return "java-microservice"
    if "flutter" in fw_set:
        return "mobile-flutter"
    return "unknown"


def detect_existing_test_frameworks(root: Path) -> list[str]:
    existing: set[str] = set()
    for pkg_path in _find(root, {"package.json"}):
        pkg = _read_json_safe(pkg_path)
        all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        scripts = pkg.get("scripts", {})
        if any("vitest" in k for k in all_deps) or any("vitest" in v for v in scripts.values()):
            existing.add("vitest")
        if any("jest" in k for k in all_deps) or any("jest" in str(v) for v in scripts.values()):
            existing.add("jest")
    for fname in {"pytest.ini", "conftest.py"}:
        if _find(root, {fname}):
            existing.add("pytest")
    for fname in {"pom.xml", "build.gradle", "build.gradle.kts"}:
        for p in _find(root, {fname}):
            text = _read_text_safe(p).lower()
            if "junit-jupiter" in text:
                existing.add("junit5")
            if "mockk" in text:
                existing.add("mockk")
            if "mockito" in text:
                existing.add("mockito")
    if _find(root, {"pubspec.yaml"}):
        existing.add("flutter_test")
    return sorted(existing)


_TEST_FILE_PATTERNS = (
    "*.test.ts", "*.test.tsx", "*.test.js", "*.test.jsx",
    "*.spec.ts", "*.spec.js",
    "test_*.py", "*_test.py",
    "*Test.java", "*IT.java", "*Test.kt",
    "*_test.go", "*_test.rs",
)


def _dir_contains_test_files(dir_path: Path) -> bool:
    """True se la dir contiene almeno un file con pattern test riconoscibile.

    ADR-12: previene false-positive su source dir literalmente nominate
    ``test/``/``tests/`` ma contenenti solo codice di produzione (es. route
    ``src/api/test/route.ts`` in jarvis-bff).
    """
    for pat in _TEST_FILE_PATTERNS:
        try:
            if any(dir_path.glob(pat)) or any(dir_path.rglob(pat)):
                return True
        except OSError:
            continue
    return False


def detect_test_infrastructure(repo_path: Path, frameworks: list[str]) -> dict:
    test_dirs = []
    for d in ["__tests__", "tests", "test", "spec"]:
        for found in repo_path.rglob(d):
            if not found.is_dir():
                continue
            if any(excl in str(found) for excl in ("node_modules", ".venv", "target", "dist", "build", ".git")):
                continue
            # ADR-12: co-presenza required prima di contare come test dir
            if _dir_contains_test_files(found):
                test_dirs.append(str(found.relative_to(repo_path)))
    test_dirs = sorted(set(test_dirs))[:10]

    pattern_sample = ""
    test_files: list[Path] = []
    for ext_glob in ["*.test.ts", "*.test.tsx", "*.test.js", "*.spec.ts", "test_*.py", "*_test.py", "*Test.java", "*_test.go", "*_test.rs"]:
        for f in repo_path.rglob(ext_glob):
            if any(excl in str(f) for excl in ("node_modules", ".venv", "target", "dist", "build", ".git")):
                continue
            test_files.append(f)
            if len(test_files) >= 3:
                break
        if len(test_files) >= 3:
            break

    if test_files:
        try:
            content = test_files[0].read_text(encoding="utf-8", errors="ignore")[:1000]
            for line in content.split("\n"):
                if any(sig in line for sig in ["vi.mock(", "jest.mock(", "@patch", "@mock", "mockito.when", "MockK", "mocker.patch"]):
                    pattern_sample = line.strip()[:120]
                    break
        except Exception:
            pass

    return {
        "frameworks_detected": frameworks,
        "test_dirs": test_dirs,
        "patterns_sample": pattern_sample,
    }


def parse_lcov_info(lcov_path: Path) -> tuple[float, list[dict]]:
    if not lcov_path.exists():
        return 0.0, []
    content = _read_text_safe(lcov_path)
    modules = []
    total_lf = 0
    total_lh = 0
    current_path = None
    current_lf = 0
    current_lh = 0
    for line in content.splitlines():
        if line.startswith("SF:"):
            current_path = line[3:].strip()
            current_lf = 0
            current_lh = 0
        elif line.startswith("LF:"):
            try:
                current_lf = int(line[3:].strip())
            except ValueError:
                current_lf = 0
        elif line.startswith("LH:"):
            try:
                current_lh = int(line[3:].strip())
            except ValueError:
                current_lh = 0
        elif line.startswith("end_of_record"):
            if current_path and current_lf > 0:
                pct = (current_lh / current_lf) * 100
                modules.append({"path": current_path, "lines_pct": round(pct, 2)})
                total_lf += current_lf
                total_lh += current_lh
            current_path = None
    global_pct = (total_lh / total_lf * 100) if total_lf > 0 else 0.0
    return round(global_pct, 2), modules


def parse_coverage_summary_for_branch(repo_path: Path) -> tuple[float, float]:
    """Legge coverage/coverage-summary.json (formato V8/Istanbul).

    Returns (line_pct, branch_pct). (0.0, 0.0) se non disponibile.
    Cerca prima sotto manifest_root/coverage, poi sotto repo/coverage.
    """
    candidates = [
        repo_path / "coverage" / "coverage-summary.json",
    ]
    # sub-workspace: prova anche manifest_root/coverage
    try:
        mr = detect_manifest_root(repo_path)
        if mr and mr != ".": 
            candidates.insert(0, repo_path / mr / "coverage" / "coverage-summary.json")
    except Exception:
        pass
    for candidate in candidates:
        try:
            data = json.loads(candidate.read_text(encoding="utf-8", errors="ignore"))
            total = data.get("total", {})
            line_pct = float(total.get("lines", {}).get("pct", 0) or 0)
            branch_pct = float(total.get("branches", {}).get("pct", 0) or 0)
            if line_pct > 0:
                return round(line_pct, 2), round(branch_pct, 2)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return 0.0, 0.0


def parse_jacoco_for_existing(jacoco_path: Path) -> tuple[float, list[dict]]:
    if not jacoco_path.exists():
        return 0.0, []
    content = _read_text_safe(jacoco_path)
    line_match = re.search(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', content)
    if not line_match:
        return 0.0, []
    missed, covered = int(line_match.group(1)), int(line_match.group(2))
    total = missed + covered
    pct = (covered / total * 100) if total else 0.0
    return round(pct, 2), [{"path": "(jacoco-aggregate)", "lines_pct": round(pct, 2)}]


def detect_coverage_exclude(repo_path: Path) -> list[str]:
    excludes: list[str] = []
    for cfg in ["vitest.config.ts", "vitest.config.js", "vite.config.ts"]:
        p = repo_path / cfg
        if p.exists():
            content = _read_text_safe(p)
            m = re.search(r"exclude\s*:\s*\[([^\]]+)\]", content, re.DOTALL)
            if m:
                items = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
                excludes.extend(items)
    for cfg in ["jest.config.js", "jest.config.ts"]:
        p = repo_path / cfg
        if p.exists():
            content = _read_text_safe(p)
            m = re.search(r"coveragePathIgnorePatterns\s*:\s*\[([^\]]+)\]", content, re.DOTALL)
            if m:
                items = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
                excludes.extend(items)
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        content = _read_text_safe(pyproject)
        m = re.search(r"\[tool\.coverage\.run\][^[]*omit\s*=\s*\[([^\]]+)\]", content, re.DOTALL)
        if m:
            items = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
            excludes.extend(items)
    return sorted(set(excludes))


_OUTPUT_SCHEMA_DEFAULTS: dict = {
    "repo_path": "",
    "languages": [],
    "frameworks": [],
    "package_managers": [],
    "build_systems": [],
    "monorepo": False,
    "monorepo_workspaces": [],
    "ci_cd": [],
    "architecture_style": "unknown",
    "existing_test_frameworks": [],
    "test_infrastructure": {"frameworks_detected": [], "test_dirs": [], "patterns_sample": ""},
    "pre_existing_coverage_pct": 0.0,
    "pre_existing_coverage_source": "missing",
    "pre_existing_coverage_hint": 0.0,
    "module_coverage": [],
    "coverage_exclude": [],
    "manifest_root": ".",
    "maven_aggregator": None,
    "orchestration_only": False,
    "orchestration_reason": None,
    "pre_existing_branch_pct": 0.0,
    "line_branch_delta": None,
}


def _emit_error(message: str) -> None:
    """Pattern Anthropic: stdout JSON full-shape con ``error`` non-null + exit 0.

    Consumer (SKILL.md Phase 1) puo' sempre parsare lo stesso shape e leggere
    ``.error // empty`` senza branching su exit code o stderr.
    """
    payload = dict(_OUTPUT_SCHEMA_DEFAULTS)
    payload["error"] = message
    print(json.dumps(payload, indent=2))
    sys.exit(0)


def main() -> None:
    if sys.version_info < (3, 8):
        _emit_error(f"Python 3.8+ required. Found: {sys.version}")
    if len(sys.argv) < 2:
        _emit_error("Usage: detect_stack.py <repo_path>")

    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        _emit_error(f"Not a directory: {root}")

    languages = detect_languages(root)
    frameworks = detect_frameworks(root)
    existing_tf = detect_existing_test_frameworks(root)

    test_infra = detect_test_infrastructure(root, existing_tf)
    # ADR-8: local report = source of truth. gh variable demoted to hint.
    pre_existing_pct = 0.0
    pre_existing_source = "missing"
    module_cov: list = []
    lcov_pct, lcov_modules = parse_lcov_info(root / "coverage" / "lcov.info")
    if lcov_modules:
        pre_existing_pct = lcov_pct
        pre_existing_source = "local_report"
        module_cov = lcov_modules
    else:
        jacoco_pct, jacoco_modules = parse_jacoco_for_existing(root / "target" / "site" / "jacoco" / "jacoco.xml")
        if jacoco_modules:
            pre_existing_pct = jacoco_pct
            pre_existing_source = "local_report"
            module_cov = jacoco_modules
    # gh variable as auxiliary hint (non source of truth)
    gh_hint, _ = read_github_coverage_variable(root)
    coverage_exclude = detect_coverage_exclude(root)

    # Branch coverage pre-esistente (V8/Istanbul summary)
    cov_line, cov_branch = parse_coverage_summary_for_branch(root)
    if cov_line > 0 and pre_existing_source == "missing":
        pre_existing_pct = cov_line
        pre_existing_source = "local_report"
    pre_existing_branch_pct = cov_branch
    # delta None se branch non disponibile (0 con line>0 = V8 non conta i branch)
    line_branch_delta = (
        round(pre_existing_pct - pre_existing_branch_pct, 2)
        if pre_existing_branch_pct > 0 else None
    )

    # ADR-1: orchestration-only early-exit (IaC/Terragrunt repo).
    orch_only, orch_reason = is_orchestration_only_repo(root)
    if orch_only:
        payload = dict(_OUTPUT_SCHEMA_DEFAULTS)
        payload.update({
            "repo_path": str(root),
            "orchestration_only": True,
            "orchestration_reason": orch_reason,
            "error": None,
        })
        print(json.dumps(payload, indent=2))
        return

    # Task 01: detect aggregator pom (SIAE multi-module layout)
    maven_agg = detect_maven_aggregator(root)
    manifest_root_default = detect_manifest_root(root)
    # Aggregator override: se rilevato un pom aggregator vero, manifest_root
    # punta alla sua directory (Phase 4/6 fa cd su questo path).
    manifest_root_final = maven_agg["manifest_root"] if maven_agg else manifest_root_default

    print(json.dumps({
        "repo_path": str(root),
        "languages": languages,
        "frameworks": frameworks,
        "package_managers": detect_package_managers(root),
        "build_systems": detect_build_systems(root),
        "monorepo": detect_monorepo(root),
        "monorepo_workspaces": detect_monorepo_workspaces(root),
        "ci_cd": detect_ci_cd(root),
        "architecture_style": detect_architecture(root, frameworks),
        "existing_test_frameworks": existing_tf,
        "test_infrastructure": test_infra,
        "pre_existing_coverage_pct": pre_existing_pct,
        "pre_existing_coverage_source": pre_existing_source,
        "pre_existing_coverage_hint": gh_hint,
        "module_coverage": module_cov,
        "coverage_exclude": coverage_exclude,
        "manifest_root": manifest_root_final,
        "maven_aggregator": maven_agg,
        "orchestration_only": False,
        "orchestration_reason": None,
        "pre_existing_branch_pct": pre_existing_branch_pct,
        "line_branch_delta": line_branch_delta,
        "error": None,
    }, indent=2))


if __name__ == "__main__":
    main()
