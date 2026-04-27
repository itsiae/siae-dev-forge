#!/usr/bin/env bash
# measure-task-baseline.sh — Simulate task-scoped metrics from session-scoped baseline
# ─────────────────────────────────────────────────────────────────
# Part of: PR #1 anti-dilution (pre-measurement for PR #2 lift validation)
# Proxy: task_id = hash(branch + design_doc_path_if_any)
# Output: baseline-metrics-tasks.json
# ─────────────────────────────────────────────────────────────────

set -eu
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

BASELINE_DIR="docs/measurements/baseline-2026-04-25"
INPUT_DIR="$BASELINE_DIR/devforge-state-snapshot"
OUTPUT="$BASELINE_DIR/baseline-metrics-tasks.json"

if [ ! -d "$INPUT_DIR" ]; then
    echo "ERROR: snapshot not found at $INPUT_DIR" >&2
    exit 1
fi

python3 <<'PY' > "$OUTPUT"
import json, os, glob, hashlib
from collections import defaultdict, Counter

BASELINE = "docs/measurements/baseline-2026-04-25/devforge-state-snapshot"

# Build task_id proxy: sha256(branch + design_doc_path)[:12]
# Each session may have 1+ tasks if branch changes mid-session or multiple
# design docs are touched. Our simplification: 1 session = 1 task proxy using
# the most-represented branch and first design doc encountered.

tasks = defaultdict(lambda: {
    "skills": set(), "commits": 0, "ended": False,
    "sessions": set(), "branch": None, "design_doc": None,
})

for f in glob.glob(f"{BASELINE}/*/activity.jsonl"):
    # First pass: find dominant branch + first design_doc for this session
    sid_data = {}
    for line in open(f, errors="replace"):
        try: d = json.loads(line)
        except: continue
        sid = d.get("sid"); br = d.get("branch")
        if not sid: continue
        if sid not in sid_data:
            sid_data[sid] = {"branches": Counter(), "design_doc": None}
        if br: sid_data[sid]["branches"][br] += 1
        # Detect design_doc touch via commit_created or plan_created events
        e = d.get("event",""); m = d.get("meta",{}) or {}
        if e == "plan_created" and m.get("plan_path"):
            if sid_data[sid]["design_doc"] is None:
                sid_data[sid]["design_doc"] = m["plan_path"]

    # Compute proxy task_id per session
    for sid, info in sid_data.items():
        if not info["branches"]: continue
        dominant_branch = info["branches"].most_common(1)[0][0]
        design_doc = info["design_doc"] or ""
        proxy_key = f"{dominant_branch}|{design_doc}"
        task_id = hashlib.sha256(proxy_key.encode()).hexdigest()[:12]
        tasks[task_id]["sessions"].add(sid)
        tasks[task_id]["branch"] = dominant_branch
        tasks[task_id]["design_doc"] = design_doc or None

    # Second pass: attribute skills/commits to task
    for line in open(f, errors="replace"):
        try: d = json.loads(line)
        except: continue
        sid = d.get("sid")
        if sid not in sid_data or not sid_data[sid]["branches"]: continue
        dominant_branch = sid_data[sid]["branches"].most_common(1)[0][0]
        design_doc = sid_data[sid]["design_doc"] or ""
        task_id = hashlib.sha256(f"{dominant_branch}|{design_doc}".encode()).hexdigest()[:12]
        T = tasks[task_id]
        e = d.get("event",""); s = d.get("status",""); m = d.get("meta",{}) or {}
        if e == "skill_invoked":
            name = (m.get("skill_name") or "").split(":")[-1]
            if name: T["skills"].add(name)
        if e == "commit_created": T["commits"] += 1
        if e == "session_end": T["ended"] = True

# Compute adoption per-task
tasks_with_commit = [t for t in tasks.values() if t["commits"] >= 1]
tasks_productive = [t for t in tasks.values() if t["commits"] >= 1 or t["skills"]]

key_skills = ["siae-brainstorming", "siae-tdd", "siae-verification",
              "siae-git-workflow", "siae-blind-review", "siae-security",
              "siae-retrospective", "siae-debugging", "siae-writing-plans"]

def pct(skill, pool):
    if not pool: return 0.0
    return round(sum(1 for t in pool if skill in t["skills"]) / len(pool) * 100, 1)

out = {
    "caveat": "PROXY baseline: task_id = sha256(dominant_branch + first_design_doc_path). "
              "Real task_id (PR #2 ADR-001) may differ. Use as ORDER-OF-MAGNITUDE reference, not exact.",
    "snapshot_date": "2026-04-25",
    "totals": {
        "tasks_identified": len(tasks),
        "tasks_productive": len(tasks_productive),
        "tasks_with_commit": len(tasks_with_commit),
        "session_to_task_ratio": round(sum(len(t["sessions"]) for t in tasks.values()) / max(1, len(tasks)), 2),
    },
    "adoption_per_task_pct": {
        "productive": {k: pct(k, tasks_productive) for k in key_skills},
        "with_commit": {k: pct(k, tasks_with_commit) for k in key_skills},
    },
    "tasks_sample": [
        {
            "task_id": tid,
            "branch": t["branch"],
            "design_doc": t["design_doc"],
            "sessions": len(t["sessions"]),
            "commits": t["commits"],
            "skills": sorted(list(t["skills"])),
        }
        for tid, t in list(tasks.items())[:5]
    ]
}
print(json.dumps(out, indent=2, default=str))
PY

echo "Wrote $OUTPUT"
