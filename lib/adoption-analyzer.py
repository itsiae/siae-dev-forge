#!/usr/bin/env python3
"""adoption-analyzer.py — Anti-Dilution PR #3 / ADR-009.

Computes per-user and per-team adoption of the 5 core DevForge skills,
split by task-scope. Feeds /forge-adoption, block explainer, and the
stop-gate recap.

Data sources:
  1. ~/.claude/.devforge-task-skills/<task_id>/skills_validated — PR #2
     ledger, authoritative for per-task user adoption.
  2. ~/.claude/devforge-activity.jsonl — session-level events used for
     team baseline and fallback when the ledger is empty.
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import statistics
import sys
import time
from pathlib import Path

CORE_SKILLS = (
    "siae-brainstorming",
    "siae-tdd",
    "siae-git-workflow",
    "siae-verification",
    "siae-blind-review",
)


def _home() -> Path:
    return Path(os.environ.get("HOME", os.path.expanduser("~")))


def _task_skills_dir() -> Path:
    return _home() / ".claude" / ".devforge-task-skills"


def _activity_log() -> Path:
    return _home() / ".claude" / "devforge-activity.jsonl"


def _parse_iso_ts(ts: str) -> float | None:
    """Parse an ISO 8601 'Z'-suffixed timestamp as epoch UTC."""
    if not ts:
        return None
    try:
        tt = time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    return calendar.timegm(tt)


def _load_activity(window_days: int) -> list[dict]:
    log = _activity_log()
    if not log.is_file():
        return []
    cutoff = time.time() - window_days * 86400
    events: list[dict] = []
    try:
        with log.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ep = _parse_iso_ts(e.get("ts"))
                if ep is None or ep < cutoff:
                    continue
                events.append(e)
    except OSError:
        return []
    return events


def _ledger_task_skills() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    d = _task_skills_dir()
    if not d.is_dir():
        return out
    for task_dir in d.iterdir():
        if not task_dir.is_dir():
            continue
        vfile = task_dir / "skills_validated"
        if not vfile.is_file():
            continue
        try:
            out[task_dir.name] = {
                line.strip() for line in vfile.read_text().splitlines() if line.strip()
            }
        except OSError:
            continue
    return out


def _user_adoption(events: list[dict], ledger: dict[str, set[str]]) -> dict[str, float]:
    """Per-skill adoption for the current user.

    Definition: of all tasks observed in the window, what fraction saw
    THIS skill validated? Falls back to session-level rate if the ledger
    is empty.
    """
    if ledger:
        total = len(ledger)
        out: dict[str, float] = {}
        for s in CORE_SKILLS:
            hits = sum(1 for validated in ledger.values() if s in validated)
            out[s] = (hits / total * 100.0) if total else 0.0
        return out

    sessions: dict[str, set[str]] = {}
    for e in events:
        if e.get("event") != "skill_invoked":
            continue
        sid = e.get("sid")
        sn = (e.get("meta") or {}).get("skill_name", "")
        sn = sn.split(":")[-1] if sn else ""
        if not sid or not sn:
            continue
        sessions.setdefault(sid, set()).add(sn)
    total = len(sessions) or 1
    return {
        s: sum(1 for skills in sessions.values() if s in skills) / total * 100.0
        for s in CORE_SKILLS
    }


def _team_median(events: list[dict]) -> dict[str, float]:
    """Team-wide median adoption per core skill, session-scoped.

    We cannot read other users' task ledgers, so the team baseline is
    necessarily session-scope. The user-vs-team comparison remains
    directional.
    """
    per_user_sessions: dict[str, dict[str, set[str]]] = {}
    for e in events:
        if e.get("event") != "skill_invoked":
            continue
        user = e.get("user") or e.get("actor_canonical") or "unknown"
        sid = e.get("sid")
        sn = (e.get("meta") or {}).get("skill_name", "")
        sn = sn.split(":")[-1] if sn else ""
        if not sid or not sn:
            continue
        per_user_sessions.setdefault(user, {}).setdefault(sid, set()).add(sn)

    if not per_user_sessions:
        return {s: 0.0 for s in CORE_SKILLS}

    medians: dict[str, float] = {}
    for s in CORE_SKILLS:
        rates: list[float] = []
        for sessions in per_user_sessions.values():
            total = len(sessions) or 1
            hits = sum(1 for skills in sessions.values() if s in skills)
            rates.append(hits / total * 100.0)
        medians[s] = statistics.median(rates) if rates else 0.0
    return medians


def _format_table(user: dict[str, float], team: dict[str, float], window: int) -> str:
    lines = ["| Skill | User | Team median | Delta |",
             "|---|---:|---:|---:|"]
    for s in CORE_SKILLS:
        u, t = user[s], team[s]
        delta = u - t
        sign = "+" if delta >= 0 else ""
        lines.append(f"| `{s}` | {u:.0f}% | {t:.0f}% | {sign}{delta:.0f}pp |")
    lines.append("")
    lines.append(f"_Window: last {window} days. `User` is task-scope when ledger is populated,"
                 " session-scope fallback otherwise. `Team median` is always session-scope._")
    return "\n".join(lines)


def _format_recap(user: dict[str, float], team: dict[str, float]) -> str:
    gaps = [(s, user[s] - team[s]) for s in CORE_SKILLS]
    gaps.sort(key=lambda x: x[1])
    weakest, weakest_gap = gaps[0]

    n_tasks = len(_ledger_task_skills())
    line1 = f"📊 DevForge adoption — tasks tracked: {n_tasks}"
    line2 = (f"✅ Weakest skill: `{weakest}` ({user[weakest]:.0f}% vs team "
             f"{team[weakest]:.0f}%, {weakest_gap:+.0f}pp)")
    line3 = (f"➡️  Next session: invoke `{weakest}` earlier to close the gap"
             if weakest_gap < -5 else
             "➡️  Next session: keep the rhythm — you are at/above team median")
    return "\n".join([line1, line2, line3])


def _format_block(skill: str, user: dict[str, float], team: dict[str, float]) -> str:
    if skill not in user:
        return ""
    return (f"La tua adoption `{skill}`: {user[skill]:.0f}% · team median: "
            f"{team[skill]:.0f}%. Closing the gap = meno block nelle prossime sessioni.")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="adoption-analyzer")
    p.add_argument("--format", choices=("table", "json", "recap", "block"),
                   default="table")
    p.add_argument("--window", type=int, default=7,
                   help="Days of activity history to scan (team baseline).")
    p.add_argument("--skill", default=None,
                   help="Required for --format block. One of the 5 core skills.")
    args = p.parse_args(argv)

    events = _load_activity(args.window)
    ledger = _ledger_task_skills()
    user = _user_adoption(events, ledger)
    team = _team_median(events)

    if args.format == "json":
        print(json.dumps({
            "window_days": args.window,
            "n_tasks": len(ledger),
            "user_adoption": user,
            "team_median": team,
        }, indent=2))
    elif args.format == "table":
        print(_format_table(user, team, args.window))
    elif args.format == "recap":
        print(_format_recap(user, team))
    elif args.format == "block":
        if not args.skill:
            print("error: --skill required for --format block", file=sys.stderr)
            return 2
        print(_format_block(args.skill, user, team))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
