#!/usr/bin/env python3
"""
run-trigger-eval.py — Test skill triggering via claude -p

Modellato su Anthropic's run_eval.py da skill-creator.
Usa claude -p con stream-json parsing per testare se le query
triggerano la skill corretta.

Usage:
    python3 tests/run-trigger-eval.py \
      --eval-file evals/trigger-evals/siae-brainstorming.json \
      --skill siae-brainstorming \
      --plugin-root /path/to/siae-dev-forge
"""

import argparse
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
        return " ".join(l for l in desc_lines if l != "").strip() or None

    return None


def run_single_query(query, skill_name, skill_description, timeout, project_root, model=None):
    """Run a single query and return whether the skill was triggered.

    Plugin skills are already available via the siae-devforge plugin.
    We run claude -p and check if it invokes Skill("siae-devforge:<skill-name>").
    Uses --include-partial-messages for early detection via stream events.
    """
    # The plugin skill is invoked as "siae-devforge:<skill-name>"
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

    # Remove CLAUDECODE env var to allow nesting claude -p
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=project_root,
        env=env,
    )

    triggered = False
    start_time = time.time()
    buffer = ""
    pending_tool_name = None
    accumulated_json = ""

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

                # Early detection via stream events
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
                                # First tool call is not Skill — skill not triggered
                                pending_tool_name = None

                    elif se_type == "content_block_delta" and pending_tool_name:
                        delta = se.get("delta", {})
                        if delta.get("type") == "input_json_delta":
                            accumulated_json += delta.get("partial_json", "")
                            if expected_skill_id in accumulated_json:
                                return True

                    elif se_type in ("content_block_stop", "message_stop"):
                        if pending_tool_name:
                            return expected_skill_id in accumulated_json
                        if se_type == "message_stop":
                            return False

                # Fallback: full assistant message (may contain text-only or tool_use)
                elif event.get("type") == "assistant":
                    message = event.get("message", {})
                    for content_item in message.get("content", []):
                        if content_item.get("type") != "tool_use":
                            continue
                        tool_name = content_item.get("name", "")
                        tool_input = content_item.get("input", {})
                        if tool_name == "Skill" and expected_skill_id in tool_input.get("skill", ""):
                            return True

                elif event.get("type") == "result":
                    return triggered
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()

    return triggered


def run_eval(eval_set, skill_name, description, num_workers, timeout,
             project_root, runs_per_query=3, trigger_threshold=0.5, model=None):
    """Run the full eval set and return results with precision/recall."""
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

        query_triggers = {}
        query_items = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_triggers:
                query_triggers[query] = []
            try:
                query_triggers[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_triggers[query].append(False)

    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold
        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": sum(triggers),
            "runs": len(triggers),
            "pass": did_pass,
        })

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

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "precision": round(precision, 2),
            "recall": round(recall, 2),
            "accuracy": round(accuracy, 2),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill")
    parser.add_argument("--eval-file", required=True, help="Path to eval set JSON")
    parser.add_argument("--skill", required=True, help="Target skill name")
    parser.add_argument("--plugin-root", default=None, help="Plugin root directory")
    parser.add_argument("--description", default=None, help="Override description")
    parser.add_argument("--num-workers", type=int, default=8, help="Parallel workers")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout per query (seconds)")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--model", default=None, help="Model for claude -p")
    parser.add_argument("--results-dir", default=None, help="Save JSON results to this directory")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_file).read_text())

    # Resolve plugin root
    plugin_root = args.plugin_root
    if not plugin_root:
        script_dir = Path(__file__).resolve().parent
        plugin_root = str(script_dir.parent)

    # Get description
    description = args.description or read_skill_description(plugin_root, args.skill)
    if not description:
        print(f"Error: no description found for {args.skill}", file=sys.stderr)
        sys.exit(2)

    project_root = find_project_root()

    if args.verbose:
        print(f"Evaluating: {args.skill} ({len(eval_set)} queries, "
              f"{args.runs_per_query} runs each, {args.num_workers} workers)",
              file=sys.stderr)

    t0 = time.time()
    output = run_eval(
        eval_set=eval_set,
        skill_name=args.skill,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=project_root,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )
    elapsed = time.time() - t0

    # Add metadata for logging
    output["metadata"] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": args.model or "default",
        "runs_per_query": args.runs_per_query,
        "trigger_threshold": args.trigger_threshold,
        "num_workers": args.num_workers,
        "timeout": args.timeout,
        "elapsed_seconds": round(elapsed, 1),
    }

    if args.verbose:
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: "
                  f"{r['query'][:70]}", file=sys.stderr)
        s = output["summary"]
        print(f"Results: {s['passed']}/{s['total']} passed "
              f"(P:{s['precision']:.2f} R:{s['recall']:.2f} A:{s['accuracy']:.2f}) "
              f"in {elapsed:.1f}s",
              file=sys.stderr)

    # Save results to file if --results-dir specified
    if args.results_dir:
        results_dir = Path(args.results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d_%H%M%S")
        result_file = results_dir / f"{timestamp}_{args.skill}.json"
        result_file.write_text(json.dumps(output, indent=2))
        if args.verbose:
            print(f"Results saved to: {result_file}", file=sys.stderr)

    print(json.dumps(output, indent=2))
    sys.exit(0 if output["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
