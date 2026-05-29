#!/usr/bin/env python3
"""detect_ci_thresholds.py — Risolve soglie coverage CI + audit working-directory.

Pass UNICO su .github/workflows/*.yaml. Output JSON:
  {
    "COVERAGE_BRANCHES": 70, "COVERAGE_LINES": 80, ...,
    "source": "CI.yaml" | "remote:owner/repo/wf@ref",
    "working_directory_issues": ["CI.yaml: reusable caller without working-directory"]
  }
Risoluzione soglie:
  1. literal nei file locali
  2. reusable remoto (gh api) se nessuna soglia locale ma reusable presente
  3. ${{ vars.X }} via gh variable get (best-effort)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

_VAR_RE = re.compile(
    r"(COVERAGE_(?:LINES|BRANCHES|STATEMENTS|FUNCTIONS|THRESHOLD)|MIN_COVERAGE)"
    r"\s*[:=]\s*['\"]?(\d+\.?\d*)['\"]?",
    re.IGNORECASE,
)
_VARREF_RE = re.compile(
    r"(COVERAGE_(?:LINES|BRANCHES|STATEMENTS|FUNCTIONS|THRESHOLD))\s*:\s*"
    r"\$\{\{\s*vars\.([A-Z_]+)\s*\}\}",
)
_REUSABLE_RE = re.compile(
    r"uses:\s+([\w.\-]+/[\w.\-]+)/\.github/workflows/([\w.\-]+\.ya?ml)@([\w.\-/]+)"
)


def _scan_text(text: str) -> dict:
    result: dict[str, float] = {}
    for m in _VAR_RE.finditer(text):
        key = m.group(1).upper()
        val = float(m.group(2))
        if key not in result or val > result[key]:
            result[key] = val
    return result


def _gh_api_reusable(repo_slug: str, wf_path: str, ref: str) -> str:
    try:
        r = subprocess.run(
            ["gh", "api",
             f"repos/{repo_slug}/contents/.github/workflows/{wf_path}?ref={ref}",
             "-H", "Accept: application/vnd.github.raw"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            return r.stdout
    except Exception:
        pass
    return ""


def _gh_variable(slug: str, var: str) -> float | None:
    try:
        r = subprocess.run(["gh", "variable", "get", var, "-R", slug],
                           capture_output=True, text=True, timeout=8)
        if r.returncode == 0 and r.stdout.strip().replace(".", "", 1).isdigit():
            return float(r.stdout.strip())
    except Exception:
        pass
    return None


def _manifest_root(repo: Path) -> str:
    stack = repo / ".code-coverage" / "stack.json"
    try:
        return json.loads(stack.read_text(encoding="utf-8")).get("manifest_root", ".")
    except Exception:
        return "."


def _repo_slug(repo: Path) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=5)
        m = re.search(r"[:/]([\w.\-]+/[\w.\-]+?)(?:\.git)?$", r.stdout.strip())
        return m.group(1) if m else None
    except Exception:
        return None


def main() -> None:
    # M-1: argv guard — exit 0 + safe JSON if no argument provided
    if len(sys.argv) < 2:
        print(json.dumps({"working_directory_issues": [],
                          "error": "Usage: detect_ci_thresholds.py <repo_path>"}))
        sys.exit(0)

    repo = Path(sys.argv[1]).resolve()
    wf_dir = repo / ".github" / "workflows"
    thresholds: dict[str, float] = {}
    source = ""
    wd_issues: list[str] = []
    reusables: list[tuple[str, str, str]] = []
    varrefs: list[tuple[str, str]] = []
    manifest_root = _manifest_root(repo)

    if wf_dir.is_dir():
        for wf in sorted(list(wf_dir.glob("*.yaml")) + list(wf_dir.glob("*.yml"))):
            text = wf.read_text(encoding="utf-8", errors="ignore")
            found = _scan_text(text)
            if found:
                # M-2: merge keeping max per key; update source only when a key is set/raised
                for key, val in found.items():
                    if key not in thresholds or val > thresholds[key]:
                        thresholds[key] = val
                        source = wf.name
            for m in _REUSABLE_RE.finditer(text):
                reusables.append((m.group(1), m.group(2), m.group(3)))
                # working-directory audit: solo se sub-workspace
                # NOTA: audit file-scoped (single-caller SIAE); multi-job per-block non coperto
                if manifest_root != "." and "working-directory" not in text:
                    wd_issues.append(
                        f"{wf.name}: reusable caller without working-directory "
                        f"(manifest_root={manifest_root})"
                    )
            for m in _VARREF_RE.finditer(text):
                varrefs.append((m.group(1).upper(), m.group(2)))

    # Reusable remoto se nessuna soglia locale
    if not thresholds and reusables:
        for slug, wf_path, ref in reusables:
            remote = _gh_api_reusable(slug, wf_path, ref)
            if remote:
                found = _scan_text(remote)
                if found:
                    thresholds.update(found)
                    source = f"remote:{slug}/{wf_path}@{ref}"
                    break

    # ${{ vars.X }} via gh variable get
    if varrefs:
        slug = _repo_slug(repo)
        if slug:
            for key, var in varrefs:
                if key not in thresholds:
                    v = _gh_variable(slug, var)
                    if v is not None:
                        thresholds[key] = v
                        source = source or f"github-variable:{var}"

    out = {k: int(v) if v == int(v) else v for k, v in thresholds.items()}
    if source:
        out["source"] = source
    out["working_directory_issues"] = sorted(set(wd_issues))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
