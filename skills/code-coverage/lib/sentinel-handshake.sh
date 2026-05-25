#!/usr/bin/env bash
# sentinel-handshake.sh — helper per Task 10 sentinel pattern (forced-choice).
#
# estimate_effort.py emette .code-coverage/pending-user-choice.json con due opzioni
# A (40%) e B (70%). Il consumer (Claude main loop o bash chain) deve leggere il
# sentinel, prompt user, scrivere user-choice.json.
#
# Questo script standardizza l'integration con input strutturato per il prompt
# (key=value su stdout) e output strutturato per il follow-up (user-choice.json).
#
# Usage:
#   bash sentinel-handshake.sh read <repo>           # → key=value su stdout
#   bash sentinel-handshake.sh write <repo> <40|70>  # → user-choice.json
#
# Exit codes:
#   0 = success
#   1 = sentinel missing / malformed / invalid target / write failure

set -e
set -o pipefail

usage() {
    cat <<'EOF' >&2
Usage:
  sentinel-handshake.sh read <repo>
  sentinel-handshake.sh write <repo> <target_line>

  read:  legge .code-coverage/pending-user-choice.json + emit key=value su stdout
  write: target_line ∈ {40, 70} → scrive .code-coverage/user-choice.json
EOF
}

cmd_read() {
    local repo="${1:?usage: read <repo>}"
    local sentinel="$repo/.code-coverage/pending-user-choice.json"

    if [ ! -f "$sentinel" ]; then
        echo "[sentinel-handshake] ERROR: sentinel not found: $sentinel" >&2
        return 1
    fi

    python3 - "$sentinel" <<'PY'
import json
import sys

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
except (OSError, json.JSONDecodeError) as exc:
    print(f"[sentinel-handshake] ERROR: invalid JSON: {exc}", file=sys.stderr)
    sys.exit(1)

# Validation: shape attesa
if data.get("type") != "forced_choice_coverage_target":
    print(f"[sentinel-handshake] ERROR: unexpected type: {data.get('type')!r}",
          file=sys.stderr)
    sys.exit(1)

ctx = data.get("context") or {}
opts = data.get("options") or {}
opt_a = opts.get("A") or {}
opt_b = opts.get("B") or {}

required = [
    ("option_a_target_line", opt_a.get("target_line")),
    ("option_b_target_line", opt_b.get("target_line")),
]
for name, val in required:
    if val is None:
        print(f"[sentinel-handshake] ERROR: missing field: {name}", file=sys.stderr)
        sys.exit(1)

# Emit key=value pairs
def emit(key, val):
    if val is None:
        val = ""
    if isinstance(val, bool):
        val = "true" if val else "false"
    print(f"{key}={val}")

emit("type", data.get("type"))
emit("repo", ctx.get("repo"))
emit("size_class", ctx.get("size_class"))
emit("spring_boot", ctx.get("spring_boot"))
emit("source_level", ctx.get("source_level"))
emit("lombok_jdk_mismatch", ctx.get("lombok_jdk_mismatch"))
emit("assertj_present", ctx.get("assertj_present"))
emit("option_a_label", opt_a.get("label"))
emit("option_a_target_line", opt_a.get("target_line"))
emit("option_a_target_branch", opt_a.get("target_branch"))
emit("option_a_p50_min", opt_a.get("estimated_wallclock_min_p50"))
emit("option_a_p90_min", opt_a.get("estimated_wallclock_min_p90"))
emit("option_b_label", opt_b.get("label"))
emit("option_b_target_line", opt_b.get("target_line"))
emit("option_b_target_branch", opt_b.get("target_branch"))
emit("option_b_p50_min", opt_b.get("estimated_wallclock_min_p50"))
emit("option_b_p90_min", opt_b.get("estimated_wallclock_min_p90"))
PY
}

cmd_write() {
    local repo="${1:?usage: write <repo> <target_line>}"
    local target="${2:?usage: write <repo> <target_line>}"

    if [ "$target" != "40" ] && [ "$target" != "70" ]; then
        echo "[sentinel-handshake] ERROR: target_line must be 40 or 70 (got: $target)" >&2
        return 1
    fi

    local sentinel="$repo/.code-coverage/pending-user-choice.json"
    if [ ! -f "$sentinel" ]; then
        echo "[sentinel-handshake] ERROR: sentinel not found: $sentinel" >&2
        return 1
    fi

    local out="$repo/.code-coverage/user-choice.json"
    python3 - "$sentinel" "$out" "$target" <<'PY'
import json
import sys
import time

sentinel_path = sys.argv[1]
out_path = sys.argv[2]
target = int(sys.argv[3])

try:
    with open(sentinel_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
except (OSError, json.JSONDecodeError) as exc:
    print(f"[sentinel-handshake] ERROR: invalid sentinel JSON: {exc}",
          file=sys.stderr)
    sys.exit(1)

ctx = data.get("context") or {}
opts = data.get("options") or {}
chosen_key = "A" if target == 40 else "B"
chosen = opts.get(chosen_key) or {}

p50 = chosen.get("estimated_wallclock_min_p50")
p90 = chosen.get("estimated_wallclock_min_p90")

# target_branch: regola fissa (30 per 40, 60 per 70)
target_branch = 30 if target == 40 else 60

payload = {
    "target_line": target,
    "target_branch": target_branch,
    "size_class": ctx.get("size_class"),
    "estimated_wallclock_min_p50": p50,
    "estimated_wallclock_min_p90": p90,
    "user_choice_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "source": "sentinel_handshake",
}

try:
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
except OSError as exc:
    print(f"[sentinel-handshake] ERROR: cannot write user-choice.json: {exc}",
          file=sys.stderr)
    sys.exit(1)

print(f"[sentinel-handshake] wrote {out_path} (target_line={target}, "
      f"target_branch={target_branch})")
PY
}

main() {
    local sub="${1:-}"
    if [ -z "$sub" ]; then
        usage
        return 1
    fi
    shift

    case "$sub" in
        read)
            cmd_read "$@"
            ;;
        write)
            cmd_write "$@"
            ;;
        -h|--help|help)
            usage
            return 0
            ;;
        *)
            echo "[sentinel-handshake] ERROR: unknown subcommand: $sub" >&2
            usage
            return 1
            ;;
    esac
}

# Standalone CLI: detection sourcing vs exec
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
    exit $?
fi
