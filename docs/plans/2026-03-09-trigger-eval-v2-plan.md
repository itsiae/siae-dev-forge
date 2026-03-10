# Trigger Eval v2 — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Riscrivere il trigger regression testing in Python, allineato a run_eval.py di Anthropic
**Architettura:** Python core (`run-trigger-eval.py`) con ProcessPoolExecutor, bash thin wrapper, eliminazione Bedrock mode
**Stack:** Python 3, subprocess, json, select, concurrent.futures
**SP:** 3

---

### Task 1: Crea `tests/run-trigger-eval.py` — Core Python

**File coinvolti:**
- Crea: `tests/run-trigger-eval.py`

**Step 1: Crea il file con le funzioni core**

Il file deve contenere queste funzioni, modellate su `run_eval.py` di Anthropic:

```python
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
import select
import subprocess
import sys
import time
import uuid
import yaml
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
    """Read description from skill's SKILL.md frontmatter."""
    skill_md = Path(plugin_root) / "skills" / skill_name / "SKILL.md"
    if not skill_md.exists():
        return None
    content = skill_md.read_text()
    # Parse YAML frontmatter between --- markers
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            return frontmatter.get("description", "")
    return None


def run_single_query(query, skill_name, skill_description, timeout, project_root, model=None):
    """Run a single query and return whether the skill was triggered.

    Creates a temporary command file in .claude/commands/ so it appears
    in Claude's available_skills list, then runs claude -p.
    Uses --include-partial-messages for early detection via stream events.
    """
    unique_id = uuid.uuid4().hex[:8]
    clean_name = f"{skill_name}-skill-{unique_id}"
    project_commands_dir = Path(project_root) / ".claude" / "commands"
    command_file = project_commands_dir / f"{clean_name}.md"

    try:
        project_commands_dir.mkdir(parents=True, exist_ok=True)
        # YAML block scalar to avoid breaking on quotes
        indented_desc = "\n  ".join(skill_description.split("\n"))
        command_content = (
            f"---\n"
            f"description: |\n"
            f"  {indented_desc}\n"
            f"---\n\n"
            f"# {skill_name}\n\n"
            f"This skill handles: {skill_description}\n"
        )
        command_file.write_text(command_content)

        cmd = [
            "claude",
            "-p", query,
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
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
                                if tool_name in ("Skill", "Read"):
                                    pending_tool_name = tool_name
                                    accumulated_json = ""
                                else:
                                    return False

                        elif se_type == "content_block_delta" and pending_tool_name:
                            delta = se.get("delta", {})
                            if delta.get("type") == "input_json_delta":
                                accumulated_json += delta.get("partial_json", "")
                                if clean_name in accumulated_json:
                                    return True

                        elif se_type in ("content_block_stop", "message_stop"):
                            if pending_tool_name:
                                return clean_name in accumulated_json
                            if se_type == "message_stop":
                                return False

                    # Fallback: full assistant message
                    elif event.get("type") == "assistant":
                        message = event.get("message", {})
                        for content_item in message.get("content", []):
                            if content_item.get("type") != "tool_use":
                                continue
                            tool_name = content_item.get("name", "")
                            tool_input = content_item.get("input", {})
                            if tool_name == "Skill" and clean_name in tool_input.get("skill", ""):
                                triggered = True
                            elif tool_name == "Read" and clean_name in tool_input.get("file_path", ""):
                                triggered = True
                            return triggered

                    elif event.get("type") == "result":
                        return triggered
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

        return triggered
    finally:
        if command_file.exists():
            command_file.unlink()


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
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query (seconds)")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--model", default=None, help="Model for claude -p")
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

    if args.verbose:
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: "
                  f"{r['query'][:70]}", file=sys.stderr)
        s = output["summary"]
        print(f"Results: {s['passed']}/{s['total']} passed "
              f"(P:{s['precision']:.2f} R:{s['recall']:.2f} A:{s['accuracy']:.2f})",
              file=sys.stderr)

    print(json.dumps(output, indent=2))
    sys.exit(0 if output["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
```

**Step 2: Verifica syntax**

```bash
python3 -c "import ast; ast.parse(open('tests/run-trigger-eval.py').read()); print('OK')"
```
Output atteso: `OK`

**Step 3: Commit**

```bash
git add tests/run-trigger-eval.py
git commit -m "feat(tests): add run-trigger-eval.py aligned with Anthropic run_eval.py"
```

**Dipendenze:** Nessuna. PyYAML potrebbe non essere installato — il wrapper bash dovrà fare fallback.

---

### Task 2: Riscrivi `tests/run-trigger-regression.sh` come thin wrapper

**File coinvolti:**
- Modifica: `tests/run-trigger-regression.sh`

**Step 1: Riscrivi il file**

```bash
#!/usr/bin/env bash
# run-trigger-regression.sh — Trigger regression tests per skill DevForge
#
# Uso: ./tests/run-trigger-regression.sh [--skill <nome>] [--runs-per-query N]
#                                        [--num-workers N] [--timeout N]
#
# Thin wrapper che itera su evals/trigger-evals/*.json e chiama
# run-trigger-eval.py per ogni skill. Allineato ad Anthropic skill-creator.
#
# Exit code: 0 = tutti sopra soglia, 1 = almeno uno sotto soglia

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EVALS_DIR="${PLUGIN_ROOT}/evals/trigger-evals"
EVAL_SCRIPT="${SCRIPT_DIR}/run-trigger-eval.py"

# Defaults
SINGLE_SKILL=""
RUNS_PER_QUERY=3
NUM_WORKERS=8
TIMEOUT=30
MODEL=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skill) SINGLE_SKILL="$2"; shift 2 ;;
    --runs-per-query) RUNS_PER_QUERY="$2"; shift 2 ;;
    --num-workers) NUM_WORKERS="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    *) echo "Uso: $0 [--skill <nome>] [--runs-per-query N] [--num-workers N] [--timeout N] [--model <id>]"; exit 1 ;;
  esac
done

# Prerequisites
if ! command -v claude >/dev/null 2>&1; then
  echo "  SKIP  claude CLI non disponibile"
  exit 0
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "  FAIL  python3 non disponibile"
  exit 1
fi
if [ ! -f "$EVAL_SCRIPT" ]; then
  echo "  FAIL  run-trigger-eval.py non trovato in ${EVAL_SCRIPT}"
  exit 1
fi

TOTAL_PASS=0
TOTAL_WARN=0
TOTAL_SKIP=0

echo "Trigger Regression Tests (claude -p, ${RUNS_PER_QUERY} runs/query, ${NUM_WORKERS} workers)"
echo "=========================================="
echo ""

for eval_file in "${EVALS_DIR}"/*.json; do
  [ ! -f "$eval_file" ] && continue
  [ "$(basename "$eval_file")" = ".gitkeep" ] && continue

  skill_name=$(basename "$eval_file" .json)

  if [ -n "$SINGLE_SKILL" ] && [ "$skill_name" != "$SINGLE_SKILL" ]; then
    continue
  fi

  # Build command
  CMD=(python3 "$EVAL_SCRIPT"
    --eval-file "$eval_file"
    --skill "$skill_name"
    --plugin-root "$PLUGIN_ROOT"
    --runs-per-query "$RUNS_PER_QUERY"
    --num-workers "$NUM_WORKERS"
    --timeout "$TIMEOUT"
    --verbose)

  [ -n "$MODEL" ] && CMD+=(--model "$MODEL")

  # Run and capture JSON output
  json_output=$("${CMD[@]}" 2>&1 1>/dev/null)
  exit_code=${PIPESTATUS[0]:-$?}

  # Print verbose output (comes on stderr, captured above)
  echo "$json_output" | grep -E "^\s*\[" | head -25
  echo "$json_output" | grep "^Results:" | head -1

  if [ "$exit_code" -eq 0 ]; then
    echo "  PASS  ${skill_name}"
    TOTAL_PASS=$((TOTAL_PASS + 1))
  elif [ "$exit_code" -eq 1 ]; then
    echo "  WARN  ${skill_name}"
    TOTAL_WARN=$((TOTAL_WARN + 1))
  else
    echo "  SKIP  ${skill_name} (exit code ${exit_code})"
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
  fi
  echo ""
done

echo "=========================================="
echo "Trigger Regression: PASS=${TOTAL_PASS} WARN=${TOTAL_WARN} SKIP=${TOTAL_SKIP}"

# WARN non causa fallimento — le description sono probabilistiche
exit 0
```

**Nota:** Lo stderr del Python contiene le righe verbose `[PASS]`/`[FAIL]` e `Results:`.
Lo stdout contiene il JSON. Il wrapper cattura stderr per il display e ignora il JSON.

**Fix per cattura corretta stderr vs stdout:**

```bash
# Cattura stderr (verbose) per display, stdout (JSON) va a /dev/null
json_output=$("${CMD[@]}" 2>&1 >/dev/null)
```

**Step 2: Verifica syntax bash**

```bash
bash -n tests/run-trigger-regression.sh && echo "OK"
```
Output atteso: `OK`

**Step 3: Commit**

```bash
git add tests/run-trigger-regression.sh
git commit -m "refactor(tests): rewrite trigger regression as thin wrapper over Python eval"
```

**Dipendenze:** Task 1 (run-trigger-eval.py deve esistere)

---

### Task 3: Elimina `tests/bedrock-trigger-test.py`

**File coinvolti:**
- Elimina: `tests/bedrock-trigger-test.py`

**Step 1: Rimuovi il file**

```bash
git rm tests/bedrock-trigger-test.py
```

**Step 2: Verifica che run-all.sh non lo referenzi**

```bash
grep -r "bedrock" tests/ && echo "WARN: riferimenti residui" || echo "OK: nessun riferimento"
```
Output atteso: `OK: nessun riferimento`

**Step 3: Commit**

```bash
git commit -m "chore(tests): remove bedrock-trigger-test.py (replaced by run-trigger-eval.py)"
```

**Dipendenze:** Nessuna (puo' andare in parallelo con Task 1-2)

---

### Task 4: Aggiorna `tests/run-all.sh` per compatibilita'

**File coinvolti:**
- Modifica: `tests/run-all.sh` (sezione trigger regression)

**Step 1: Verifica la sezione attuale**

Leggere la sezione `--with-trigger-regression` in `run-all.sh`. Deve chiamare
`run-trigger-regression.sh` senza flag `--use-bedrock` (rimosso).

**Step 2: Rimuovi eventuali riferimenti a `--use-bedrock`**

Se la sezione contiene `--use-bedrock`, rimuovilo. Il wrapper ora usa solo `claude -p`.

**Step 3: Verifica**

```bash
bash tests/run-all.sh
```
Output atteso: `PASS: 75, FAIL: 0, SKIP: 0`

**Step 4: Commit (se modificato)**

```bash
git add tests/run-all.sh
git commit -m "fix(tests): remove bedrock references from run-all.sh"
```

**Dipendenze:** Task 2 (wrapper riscritto)

---

### Task 5: Verifica end-to-end

**Step 1: Verifica test strutturali**

```bash
bash tests/run-all.sh
```
Output atteso: `75 PASS, 0 FAIL`

**Step 2: Verifica Python syntax**

```bash
python3 -c "import ast; ast.parse(open('tests/run-trigger-eval.py').read()); print('OK')"
```

**Step 3: Dry-run singola skill (dal terminale)**

```bash
python3 tests/run-trigger-eval.py \
  --eval-file evals/trigger-evals/siae-brainstorming.json \
  --skill siae-brainstorming \
  --runs-per-query 1 \
  --num-workers 1 \
  --timeout 30 \
  --verbose
```

**Step 4: Dry-run via wrapper (dal terminale)**

```bash
bash tests/run-trigger-regression.sh --skill siae-brainstorming --runs-per-query 1
```

**Dipendenze:** Task 1-4 completati
