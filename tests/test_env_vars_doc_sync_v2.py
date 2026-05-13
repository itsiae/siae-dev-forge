"""Verify ENV_VARS.md doc-sync per nuove env Review Evidence v2 (PR-A).

Extends `tests/test_env_vars_doc_sync.py` (v1 evidence env vars). Documenta
i 3 nuovi env var introdotti dalla foundation PR-A; le 4 env var PR-B
(`DEVFORGE_BASELINE_*`, `DEVFORGE_BREAK_GLASS_REGEX`) verranno aggiunte in
Task 15.
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

V2_EXPECTED_VARS = {
    "DEVFORGE_SCORES_CONFIG_PATH",
    "DEVFORGE_ARCH_CONFIG_PATH",
    "DEVFORGE_SCORING_V2_ENABLED",
    # PR-B vars saranno aggiunte in Task 15
    # v1.57+ runner-level overrides
    "DEVFORGE_SEMGREP_CONFIG",
}

# Env vars that are documented in ENV_VARS.md but not yet consumed by the
# Python codebase (acceptable lag — code-not-yet-wired). The grep
# doc-sync test treats them as a soft warning, not a hard failure. Each
# entry MUST have a tracking comment.
DOCUMENTED_BUT_NOT_CONSUMED_TOLERATED = {
    # Templated config override paths — used by `commands/forge-score.md`
    # workflows and the docs; the Python loader currently reads the file
    # from the repo root directly. Follow-up wiring tracked under PR-B
    # Task 15 polish.
    "DEVFORGE_SCORES_CONFIG_PATH",
    "DEVFORGE_ARCH_CONFIG_PATH",
    # BREAK-GLASS regex is read by the hook + agent advisory; the Python
    # collector does not (yet) inspect commit messages.
    "DEVFORGE_BREAK_GLASS_REGEX",
}


def test_env_vars_md_documents_v2():
    content = (REPO_ROOT / "hooks" / "ENV_VARS.md").read_text()
    missing = [v for v in V2_EXPECTED_VARS if v not in content]
    assert not missing, f"V2 env vars missing from ENV_VARS.md: {missing}"


def test_changelog_has_v1_55_entry():
    cl = (REPO_ROOT / "CHANGELOG.md").read_text()
    assert "v1.55.0" in cl
    assert "review-evidence v2" in cl.lower() or "scoring v2" in cl.lower()


def test_documented_env_vars_have_consumer_or_tolerated():
    """Warn (don't block) when an env documented in ENV_VARS.md has no
    matching ``os.environ`` read anywhere under ``lib/`` or ``hooks/``.

    Fresh-eyes review iter 1 minor finding: three env vars
    (``DEVFORGE_SCORES_CONFIG_PATH``, ``DEVFORGE_ARCH_CONFIG_PATH``,
    ``DEVFORGE_BREAK_GLASS_REGEX``) are documented but never consumed in
    Python. This test surfaces such drift via ``warnings.warn`` so future
    additions get visibility without breaking the build.
    """
    env_vars_md = (REPO_ROOT / "hooks" / "ENV_VARS.md").read_text()
    # Extract all DEVFORGE_* names mentioned in the doc table.
    documented = set(re.findall(r"`(DEVFORGE_[A-Z0-9_]+)`", env_vars_md))

    # Gather consumer text from python + bash code paths.
    consumer_texts = []
    for sub in ("lib", "hooks"):
        for p in (REPO_ROOT / sub).rglob("*"):
            if p.is_file() and p.suffix in ("", ".py", ".sh"):
                try:
                    consumer_texts.append(p.read_text(errors="ignore"))
                except OSError:
                    continue
    blob = "\n".join(consumer_texts)

    undocumented_orphans = []
    for var in documented:
        if var in DOCUMENTED_BUT_NOT_CONSUMED_TOLERATED:
            continue
        # Heuristic match — both Python (os.environ / os.getenv) and bash
        # ($VAR / ${VAR}) forms appear in the codebase.
        if (
            f'"{var}"' not in blob
            and f"'{var}'" not in blob
            and f"${var}" not in blob
            and f"${{{var}" not in blob
        ):
            undocumented_orphans.append(var)

    if undocumented_orphans:
        warnings.warn(
            "Env vars documented in hooks/ENV_VARS.md but not consumed in "
            "lib/ or hooks/: "
            + ", ".join(sorted(undocumented_orphans))
            + ". Add to DEVFORGE_NOT_CONSUMED_TOLERATED with a tracking "
            "comment, or wire the consumer.",
            stacklevel=2,
        )
