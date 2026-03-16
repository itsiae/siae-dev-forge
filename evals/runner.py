#!/usr/bin/env python3
"""
runner.py — CLI orchestratore per eval service pipeline.

Uso:
    python3 evals/runner.py --skill siae-brainstorming --level L1
    python3 evals/runner.py --all --level L1,L2 --report
    python3 evals/runner.py --skill siae-brainstorming --ab-test --description-b "..."
    python3 evals/runner.py --help
"""

import argparse
import json
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from evals.trigger_eval import run_trigger_eval, read_skill_description
from evals.functional_eval import run_functional_eval
from evals.e2e_eval import run_e2e_eval
from evals.ab_test import run_ab_test
from evals.reporter import generate_report


def find_project_root() -> Path:
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


def resolve_skills(args, eval_sets_dir: Path) -> list[str]:
    if args.all:
        return sorted([
            d.name for d in eval_sets_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ])
    elif args.skill:
        return [args.skill]
    return []


def load_eval_set(eval_sets_dir: Path, skill: str, level: str) -> list[dict] | None:
    filename_map = {"L1": "trigger.json", "L2": "functional.json", "L3": "e2e.json"}
    path = eval_sets_dir / skill / filename_map.get(level, "")
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_result(result: dict, results_dir: Path):
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d_%H%M%S")
    skill = result.get("skill", "unknown")
    level = result.get("level", "X")
    path = results_dir / f"{timestamp}_{level}_{skill}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return path


def main():
    parser = argparse.ArgumentParser(
        description="DevForge Eval Service Pipeline — orchestratore"
    )
    parser.add_argument("--skill", help="Singola skill da valutare")
    parser.add_argument("--all", action="store_true", help="Valuta tutte le skill")
    parser.add_argument("--level", default="L1", help="Livelli: L1,L2,L3 (combinabili con virgola)")
    parser.add_argument("--report", action="store_true", help="Genera report HTML")
    parser.add_argument("--ab-test", action="store_true", help="Esegui A/B test description")
    parser.add_argument("--description-b", help="Description candidata per A/B test")
    parser.add_argument("--model", default=None, help="Modello executor (default: sonnet)")
    parser.add_argument("--runs", type=int, default=3, help="Ripetizioni per query")
    parser.add_argument("--timeout", type=int, default=None, help="Override timeout")
    parser.add_argument("--verbose", action="store_true", help="Progress su stderr")
    args = parser.parse_args()

    eval_sets_dir = SCRIPT_DIR / "eval-sets"
    results_dir = SCRIPT_DIR / "results"
    reports_dir = SCRIPT_DIR / "reports"
    project_root = find_project_root()
    levels = [l.strip() for l in args.level.split(",")]

    # A/B test mode
    if args.ab_test:
        if not args.skill:
            print("Errore: --ab-test richiede --skill", file=sys.stderr)
            sys.exit(1)
        if not args.description_b:
            print("Errore: --ab-test richiede --description-b", file=sys.stderr)
            sys.exit(1)

        eval_set = load_eval_set(eval_sets_dir, args.skill, "L1")
        if not eval_set:
            print(f"Errore: trigger.json non trovato per {args.skill}", file=sys.stderr)
            sys.exit(1)

        result = run_ab_test(
            skill_name=args.skill, eval_set=eval_set,
            plugin_root=PLUGIN_ROOT, project_root=project_root,
            description_b=args.description_b,
            runs_per_query=args.runs,
            timeout=args.timeout or 60,
            model=args.model,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0)

    # Standard eval mode
    skills = resolve_skills(args, eval_sets_dir)
    if not skills:
        print("Errore: specifica --skill <name> o --all", file=sys.stderr)
        sys.exit(1)

    all_results = []
    default_timeouts = {"L1": 60, "L2": 120, "L3": 300}

    for skill in skills:
        for level in levels:
            eval_set = load_eval_set(eval_sets_dir, skill, level)
            if not eval_set:
                if args.verbose:
                    print(f"  SKIP  {skill}/{level}: eval set non trovato", file=sys.stderr)
                continue

            timeout = args.timeout or default_timeouts.get(level, 120)

            if args.verbose:
                print(f"  RUN   {skill}/{level} ({len(eval_set)} scenari)", file=sys.stderr)

            if level == "L1":
                result = run_trigger_eval(
                    skill_name=skill, eval_set=eval_set,
                    plugin_root=PLUGIN_ROOT, project_root=project_root,
                    runs_per_query=args.runs, timeout=timeout, model=args.model,
                )
            elif level == "L2":
                eval_set_dir = eval_sets_dir / skill
                result = run_functional_eval(
                    skill_name=skill, eval_set=eval_set,
                    eval_set_dir=eval_set_dir,
                    runs_per_query=args.runs, timeout=timeout, model=args.model,
                )
            elif level == "L3":
                eval_set_dir = eval_sets_dir / skill
                result = run_e2e_eval(
                    skill_name=skill, eval_set=eval_set,
                    eval_set_dir=eval_set_dir,
                    timeout=timeout, model=args.model,
                )
            else:
                continue

            saved = save_result(result, results_dir)
            all_results.append(result)

            if args.verbose:
                s = result.get("summary", {})
                print(f"  DONE  {skill}/{level}: {s.get('passed', 0)}/{s.get('total', 0)} passed "
                      f"-> {saved.name}", file=sys.stderr)

    # Report
    if args.report and all_results:
        report_path = reports_dir / f"{time.strftime('%Y-%m-%d_%H%M%S')}_report.html"
        generate_report(all_results, report_path)
        if args.verbose:
            print(f"  Report: {report_path}", file=sys.stderr)

    # Output JSON su stdout
    output_summary = []
    for r in all_results:
        s = r.get("summary", {})
        output_summary.append({
            "skill": r["skill"],
            "level": r["level"],
            **s,
        })
    print(json.dumps({"runs": len(all_results), "results": output_summary}, indent=2, ensure_ascii=False))

    # Exit code
    has_failures = any(
        r.get("summary", {}).get("failed", 0) > 0 for r in all_results
    )
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    main()
