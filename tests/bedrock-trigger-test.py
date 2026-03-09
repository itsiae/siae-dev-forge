#!/usr/bin/env python3
"""
bedrock-trigger-test.py — Test skill triggering via Bedrock API

Simulates Claude Code's skill triggering decision by presenting the skill
catalog as a system prompt with a Skill tool definition, then checking if
the model responds with a tool_use call for the target skill.

Usage:
    python3 bedrock-trigger-test.py --query "user prompt" --skill siae-brainstorming
    python3 bedrock-trigger-test.py --eval-file evals/trigger-evals/siae-brainstorming.json

Environment variables:
    AWS_REGION          (default: eu-west-1)
    ANTHROPIC_MODEL     (default: eu.anthropic.claude-sonnet-4-20250514-v1:0)

Exit code: 0 = triggered, 1 = not triggered, 2 = error
When --eval-file: prints JSON with results for each query.
"""

import argparse
import json
import os
import subprocess
import sys

def get_skill_catalog(plugin_root):
    """Build skill catalog by running skills-core.js"""
    skills_core = os.path.join(plugin_root, "lib", "skills-core.js")
    if not os.path.exists(skills_core):
        print(f"ERROR: skills-core.js not found at {skills_core}", file=sys.stderr)
        sys.exit(2)

    result = subprocess.run(
        ["node", skills_core, plugin_root],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR: skills-core.js failed: {result.stderr}", file=sys.stderr)
        sys.exit(2)

    return result.stdout.strip()


def build_system_prompt(catalog):
    """Build a system prompt that mimics Claude Code's skill presentation"""
    return f"""You are Claude Code, an AI coding assistant. You have access to skills that provide specialized capabilities.

When the user's request matches a skill's trigger, you MUST invoke it using the Skill tool BEFORE responding.

Available skills:

{catalog}

If a skill matches the user's request, invoke it. If no skill matches, respond normally without using the Skill tool."""


def build_skill_tool():
    """Build the Skill tool definition matching Claude Code's format"""
    return {
        "name": "Skill",
        "description": "Invoke a skill to handle the user's request",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "description": "The skill name to invoke"
                    },
                    "args": {
                        "type": "string",
                        "description": "Optional arguments for the skill"
                    }
                },
                "required": ["skill"]
            }
        }
    }


def test_trigger_bedrock(query, skill_catalog, model_id, region):
    """Test if a query triggers any skill via Bedrock Converse API"""
    import boto3

    client = boto3.client("bedrock-runtime", region_name=region)

    system_prompt = build_system_prompt(skill_catalog)
    skill_tool = build_skill_tool()

    try:
        response = client.converse(
            modelId=model_id,
            messages=[
                {"role": "user", "content": [{"text": query}]}
            ],
            system=[{"text": system_prompt}],
            toolConfig={
                "tools": [
                    {"toolSpec": skill_tool}
                ]
            },
            inferenceConfig={
                "maxTokens": 1024,
                "temperature": 0.0
            }
        )
    except Exception as e:
        print(f"ERROR: Bedrock API call failed: {e}", file=sys.stderr)
        return None, None

    # Check if response contains a tool_use for Skill
    output = response.get("output", {})
    message = output.get("message", {})
    content = message.get("content", [])

    for block in content:
        if "toolUse" in block:
            tool_use = block["toolUse"]
            if tool_use.get("name") == "Skill":
                skill_input = tool_use.get("input", {})
                triggered_skill = skill_input.get("skill", "")
                return True, triggered_skill

    return False, None


def run_single_query(query, target_skill, catalog, model_id, region):
    """Run a single query and return result dict"""
    triggered, skill_name = test_trigger_bedrock(query, catalog, model_id, region)

    if triggered is None:
        return {"query": query, "triggered": None, "error": True}

    # Normalize skill name (remove plugin prefix if present)
    if skill_name:
        skill_name = skill_name.replace("siae-devforge:", "")

    matched = triggered and (skill_name == target_skill or
                              skill_name == f"siae-devforge:{target_skill}")

    return {
        "query": query[:80] + "..." if len(query) > 80 else query,
        "triggered": triggered,
        "triggered_skill": skill_name,
        "matched_target": matched
    }


def main():
    parser = argparse.ArgumentParser(description="Test skill triggering via Bedrock")
    parser.add_argument("--query", help="Single query to test")
    parser.add_argument("--skill", help="Target skill name")
    parser.add_argument("--eval-file", help="JSON file with eval queries")
    parser.add_argument("--plugin-root", default=None, help="Plugin root directory")
    parser.add_argument("--model", default=None, help="Bedrock model ID")
    parser.add_argument("--region", default=None, help="AWS region")
    parser.add_argument("--json-output", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    # Resolve plugin root
    plugin_root = args.plugin_root
    if not plugin_root:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        plugin_root = os.path.dirname(script_dir)

    # Resolve model and region from env or args
    model_id = args.model or os.environ.get(
        "ANTHROPIC_MODEL",
        "eu.anthropic.claude-sonnet-4-20250514-v1:0"
    )
    region = args.region or os.environ.get("AWS_REGION", "eu-west-1")

    # Build catalog
    catalog = get_skill_catalog(plugin_root)

    if args.query and args.skill:
        # Single query mode
        result = run_single_query(args.query, args.skill, catalog, model_id, region)
        if args.json_output:
            print(json.dumps(result, indent=2))
        else:
            if result.get("error"):
                print(f"  ERROR  API call failed")
                sys.exit(2)
            elif result["matched_target"]:
                print(f"  PASS  triggered {result['triggered_skill']}")
                sys.exit(0)
            elif result["triggered"]:
                print(f"  FAIL  triggered {result['triggered_skill']} (expected {args.skill})")
                sys.exit(1)
            else:
                print(f"  FAIL  no skill triggered (expected {args.skill})")
                sys.exit(1)

    elif args.eval_file:
        # Eval file mode
        skill_name = args.skill
        if not skill_name:
            skill_name = os.path.basename(args.eval_file).replace(".json", "")

        with open(args.eval_file) as f:
            evals = json.load(f)

        tp = fp = tn = fn = errors = 0

        for ev in evals:
            query = ev["query"]
            should_trigger = ev["should_trigger"]

            result = run_single_query(query, skill_name, catalog, model_id, region)

            if result.get("error"):
                errors += 1
                continue

            if should_trigger:
                if result["matched_target"]:
                    tp += 1
                else:
                    fn += 1
                    if not args.json_output:
                        print(f"    MISS  should-trigger: {result['query']}")
            else:
                if result["triggered"] and result.get("triggered_skill", "").replace("siae-devforge:", "") == skill_name:
                    fp += 1
                    if not args.json_output:
                        print(f"    FALSE+ should-not-trigger: {result['query']}")
                else:
                    tn += 1

        total_should = tp + fn
        total_should_not = tn + fp

        recall = tp / total_should if total_should > 0 else 1.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0

        summary = {
            "skill": skill_name,
            "tp": tp, "fn": fn, "tn": tn, "fp": fp, "errors": errors,
            "recall": round(recall, 2),
            "precision": round(precision, 2),
            "total_should_trigger": total_should,
            "total_should_not_trigger": total_should_not
        }

        if args.json_output:
            print(json.dumps(summary, indent=2))
        else:
            recall_ok = recall >= 0.80
            precision_ok = precision >= 0.80
            status = "PASS" if (recall_ok and precision_ok) else "WARN"
            print(f"  {status}  {skill_name}: {tp}/{total_should} should-trigger, "
                  f"{tn}/{total_should_not} should-not-trigger "
                  f"(P:{precision:.2f} R:{recall:.2f})")
            if not recall_ok:
                print(f"         ↳ recall {recall:.2f} < 0.80")
            if not precision_ok:
                print(f"         ↳ precision {precision:.2f} < 0.80")

        sys.exit(0 if (recall >= 0.80 and precision >= 0.80) else 1)

    else:
        parser.error("Specify --query + --skill, or --eval-file")


if __name__ == "__main__":
    main()
