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
import sys
from pathlib import Path

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


_SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "out", "target",
    ".terraform", "vendor", "coverage", "__pycache__", ".venv", "venv",
    ".next", ".nuxt", ".svelte-kit",
}


def _walk(root: Path, max_depth: int = 6):
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


def detect_monorepo(root: Path) -> bool:
    if _find(root, {"turbo.json", "nx.json", "lerna.json", "pnpm-workspace.yaml", "rush.json"}):
        return True
    pkg = _read_json_safe(root / "package.json")
    if "workspaces" in pkg:
        return True
    child_count = 0
    for d in ["packages", "apps", "services"]:
        dpath = root / d
        if dpath.is_dir():
            child_count += sum(1 for _ in dpath.glob("*/package.json"))
    return child_count >= 2


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


def main() -> None:
    if sys.version_info < (3, 8):
        print(json.dumps({"error": f"Python 3.8+ required. Found: {sys.version}"}), file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: detect_stack.py <repo_path>"}), file=sys.stderr)
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"Not a directory: {root}"}), file=sys.stderr)
        sys.exit(1)

    languages = detect_languages(root)
    frameworks = detect_frameworks(root)

    print(json.dumps({
        "repo_path": str(root),
        "languages": languages,
        "frameworks": frameworks,
        "package_managers": detect_package_managers(root),
        "build_systems": detect_build_systems(root),
        "monorepo": detect_monorepo(root),
        "ci_cd": detect_ci_cd(root),
        "architecture_style": detect_architecture(root, frameworks),
        "existing_test_frameworks": detect_existing_test_frameworks(root),
    }, indent=2))


if __name__ == "__main__":
    main()
