"""Guard: le istruzioni prosa iniettate come additional_context a fresh LLM
agent (o come prompt subagent) NON devono istruire l'agent a eseguire
`git diff origin/main...HEAD` letterale — su un branch derivato da
`sviluppo`/`release/*` quel comando produce un diff sbagliato (REQ-DF-03).
L'istruzione corretta risolve la base dinamicamente via
`devforge_resolve_pr_base()` / `$PARENT_BRANCH`.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).parent.parent

FILES = [
    REPO / "hooks" / "pr-gate",
    REPO / "hooks" / "post-commit-review",
    REPO / "skills" / "siae-subagent-development" / "SKILL.md",
]

FORBIDDEN_SNIPPETS = [
    "git diff origin/main...HEAD",
    "git diff origin/main..HEAD",
    "git merge-base HEAD origin/main)..HEAD",
]


def test_no_hardcoded_origin_main_diff_in_agent_prompts():
    offenders = []
    for f in FILES:
        text = f.read_text(errors="ignore")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in text:
                offenders.append(f"{f.relative_to(REPO)}: {snippet!r}")
    assert not offenders, (
        "Prosa rivolta all'agent hardcoda ancora origin/main come base "
        "letterale (rompe su branch derivati da sviluppo/release): "
        + "; ".join(offenders)
    )


def test_pr_gate_instructs_dynamic_base_resolution():
    text = (REPO / "hooks" / "pr-gate").read_text()
    assert "devforge_resolve_pr_base" in text


def test_post_commit_review_instructs_dynamic_base_resolution():
    text = (REPO / "hooks" / "post-commit-review").read_text()
    assert "devforge_resolve_pr_base" in text


def test_fresh_eyes_prompt_uses_resolved_parent_branch():
    text = (REPO / "skills" / "siae-subagent-development" / "SKILL.md").read_text()
    assert "$PARENT_BRANCH" in text
