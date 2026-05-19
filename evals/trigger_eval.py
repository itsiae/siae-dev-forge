"""
trigger_eval.py — L1 trigger evaluation module

Refactored from tests/run-trigger-eval.py as importable module.
No CLI / argparse — runner.py handles that.
"""

import json
import os
import re
import select
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def find_project_root():
    """Find project root by walking up looking for .claude/ directory."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


def read_skill_description(plugin_root, skill_name):
    """Read description from skill's SKILL.md frontmatter.

    Parses YAML frontmatter manually (no PyYAML dependency).
    Supports both single-line and multiline (block scalar) descriptions:
      description: "some text"
      description: >
        multiline
        text
    """
    skill_md = Path(plugin_root) / "skills" / skill_name / "SKILL.md"
    if not skill_md.exists():
        return None
    content = skill_md.read_text()
    # Parse YAML frontmatter between --- markers
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    frontmatter = parts[1]

    # Try to find 'description:' line
    lines = frontmatter.split("\n")
    desc_lines = []
    in_description = False
    desc_indent = 0

    for line in lines:
        if not in_description:
            # Match 'description:' at the start
            m = re.match(r'^description:\s*(.*)', line)
            if m:
                value = m.group(1).strip()
                if value in (">", "|", ">-", "|-"):
                    # Block scalar — collect indented lines that follow
                    in_description = True
                    desc_indent = 0
                    continue
                else:
                    # Single-line value: strip optional quotes
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    return value if value else None
        else:
            # Collecting multiline block scalar content
            if line.strip() == "":
                # Blank line — could be part of block or end
                desc_lines.append("")
                continue
            current_indent = len(line) - len(line.lstrip())
            if desc_indent == 0:
                # First content line sets the indent level
                desc_indent = current_indent
            if current_indent >= desc_indent and desc_indent > 0:
                desc_lines.append(line[desc_indent:])
            else:
                # Dedented — end of block scalar
                break

    if desc_lines:
        # Strip trailing blank lines
        while desc_lines and desc_lines[-1] == "":
            desc_lines.pop()
        return " ".join(line for line in desc_lines if line != "").strip() or None

    return None


def run_single_query(query, skill_name, skill_description, timeout, project_root, model=None):
    """Run a single query and return which skill was actually triggered.

    Returns:
        dict: {"triggered": bool, "actual_skill": str|None}
        - triggered: True if the expected skill was invoked
        - actual_skill: the skill that was actually invoked (None if no Skill tool called)
    """
    expected_skill_id = f"siae-devforge:{skill_name}"

    cmd = [
        "claude",
        "-p", query,
        "--output-format", "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--permission-mode", "bypassPermissions",
    ]
    if model:
        cmd.extend(["--model", model])

    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=project_root,
        env=env,
    )

    start_time = time.time()
    buffer = ""
    pending_tool_name = None
    accumulated_json = ""
    no_skill = {"triggered": False, "actual_skill": None}

    def _extract_skill_id(json_str):
        """Estrai skill ID dal JSON accumulato del tool Skill."""
        try:
            parsed = json.loads("{" + json_str + "}") if not json_str.startswith("{") else json.loads(json_str)
            return parsed.get("skill", "")
        except (json.JSONDecodeError, TypeError):
            # Prova estrazione regex come fallback
            import re
            m = re.search(r'"skill"\s*:\s*"([^"]+)"', json_str)
            return m.group(1) if m else json_str

    try:
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                remaining = process.stdout.read()
                if remaining:
                    buffer += remaining.decode("utf-8", errors="replace")
                break

            ready, _, _ = select.select([process.stdout], [], [], 1.0)
            if not ready:
                continue

            chunk = os.read(process.stdout.fileno(), 8192)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("type") == "stream_event":
                    se = event.get("event", {})
                    se_type = se.get("type", "")

                    if se_type == "content_block_start":
                        cb = se.get("content_block", {})
                        if cb.get("type") == "tool_use":
                            tool_name = cb.get("name", "")
                            if tool_name == "Skill":
                                pending_tool_name = tool_name
                                accumulated_json = ""
                            else:
                                pending_tool_name = None

                    elif se_type == "content_block_delta" and pending_tool_name:
                        delta = se.get("delta", {})
                        if delta.get("type") == "input_json_delta":
                            accumulated_json += delta.get("partial_json", "")
                            # Early exit se troviamo la skill attesa
                            if expected_skill_id in accumulated_json:
                                return {"triggered": True, "actual_skill": expected_skill_id}

                    elif se_type in ("content_block_stop", "message_stop"):
                        if pending_tool_name and accumulated_json:
                            actual = _extract_skill_id(accumulated_json)
                            return {
                                "triggered": expected_skill_id in accumulated_json,
                                "actual_skill": actual or None,
                            }
                        if se_type == "message_stop":
                            return no_skill

                elif event.get("type") == "assistant":
                    message = event.get("message", {})
                    for content_item in message.get("content", []):
                        if content_item.get("type") != "tool_use":
                            continue
                        tool_name = content_item.get("name", "")
                        tool_input = content_item.get("input", {})
                        if tool_name == "Skill":
                            actual = tool_input.get("skill", "")
                            return {
                                "triggered": expected_skill_id in actual,
                                "actual_skill": actual or None,
                            }

                elif event.get("type") == "result":
                    return no_skill
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()

    return no_skill


def run_trigger_eval(
    skill_name: str,
    eval_set: list[dict],
    plugin_root: Path,
    project_root: Path,
    runs_per_query: int = 3,
    trigger_threshold: float = 0.5,
    num_workers: int = 8,
    timeout: int = 60,
    model: str | None = None,
    description_override: str | None = None,
) -> dict:
    """Run the full trigger eval set and return results with precision/recall.

    Args:
        skill_name: Target skill name (e.g. "siae-brainstorming")
        eval_set: List of dicts with "query" and "should_trigger" keys
        plugin_root: Path to the plugin root directory
        project_root: Path to the project root (where .claude/ lives)
        runs_per_query: Number of times to run each query
        trigger_threshold: Minimum trigger rate to consider a positive pass
        num_workers: Number of parallel workers
        timeout: Timeout per query in seconds
        model: Optional model override for claude -p
        description_override: Optional description (logged in metadata, does not
            change trigger behaviour — the description lives in the plugin system prompt)

    Returns:
        Dict conforming to the L1 result schema.
    """
    # Read skill description for passing to run_single_query
    description = description_override or read_skill_description(plugin_root, skill_name)

    t0 = time.time()
    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    model,
                )
                future_to_info[future] = (item, run_idx)

        query_results_raw = {}
        query_items = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_results_raw:
                query_results_raw[query] = []
            try:
                query_results_raw[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_results_raw[query].append({"triggered": False, "actual_skill": None})

    # Aggrega risultati e traccia skill "ladre"
    stolen_by = {}  # {actual_skill: count} — chi ruba i trigger

    for query, run_results in query_results_raw.items():
        item = query_items[query]
        triggers = sum(1 for r in run_results if r["triggered"])
        trigger_rate = triggers / len(run_results)
        should_trigger = item["should_trigger"]

        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold

        # Raccogli actual_skill per query should_trigger che NON hanno triggerato
        actual_skills = []
        for r in run_results:
            actual = r.get("actual_skill")
            if actual:
                actual_skills.append(actual)
                if should_trigger and not r["triggered"] and actual:
                    stolen_by[actual] = stolen_by.get(actual, 0) + 1

        # Skill piu' frequente triggerata (per diagnostica)
        actual_counts = {}
        for a in actual_skills:
            actual_counts[a] = actual_counts.get(a, 0) + 1
        most_common_actual = max(actual_counts, key=actual_counts.get) if actual_counts else None

        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": triggers,
            "runs": len(run_results),
            "pass": did_pass,
            "actual_skill": most_common_actual,
        })

    elapsed = time.time() - t0

    # Calculate precision, recall, accuracy
    pos = [r for r in results if r["should_trigger"]]
    neg = [r for r in results if not r["should_trigger"]]
    tp = sum(r["triggers"] for r in pos)
    pos_runs = sum(r["runs"] for r in pos)
    fn = pos_runs - tp
    fp = sum(r["triggers"] for r in neg)
    neg_runs = sum(r["runs"] for r in neg)
    tn = neg_runs - fp
    total = tp + tn + fp + fn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    accuracy = (tp + tn) / total if total > 0 else 0.0

    passed = sum(1 for r in results if r["pass"])

    # Top stolen-by skills (ordinate per frequenza)
    top_stolen = sorted(stolen_by.items(), key=lambda x: -x[1])[:5]

    return {
        "skill": skill_name,
        "level": "L1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": model or "default",
        "results": results,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "precision": round(precision, 2),
            "recall": round(recall, 2),
            "accuracy": round(accuracy, 2),
        },
        "stolen_by": [{"skill": s, "count": c} for s, c in top_stolen],
        "metadata": {
            "runs_per_query": runs_per_query,
            "trigger_threshold": trigger_threshold,
            "num_workers": num_workers,
            "timeout": timeout,
            "elapsed_s": round(elapsed, 1),
            "description_override": description_override,
        },
    }
