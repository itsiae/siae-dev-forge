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
#   bash sentinel-handshake.sh read   <repo>            # → key=value su stdout
#   bash sentinel-handshake.sh prompt <repo>            # → interactive 3-option
#                                                        prompt, exports
#                                                        TARGET_LINE/TARGET_BRANCH
#                                                        and writes user-choice.json
#   bash sentinel-handshake.sh write  <repo> <N>        # → user-choice.json
#                                                        N integer in [1, 95]
#                                                        (40 = quick-win,
#                                                         70 = full-bundle,
#                                                         altri = custom)
#
# Exit codes:
#   0 = success
#   1 = sentinel missing / malformed / invalid target / write failure

set -e
set -o pipefail

usage() {
    cat <<'EOF' >&2
Usage:
  sentinel-handshake.sh read   <repo>
  sentinel-handshake.sh prompt <repo>
  sentinel-handshake.sh write  <repo> <target_line>

  read:   legge .code-coverage/pending-user-choice.json + emit key=value su stdout
  prompt: 3-option interactive prompt (Quick / Full / Custom); exports
          TARGET_LINE + TARGET_BRANCH e scrive .code-coverage/user-choice.json
  write:  target_line ∈ [1, 95] (40=quick-win, 70=full-bundle, altri=custom) →
          scrive .code-coverage/user-choice.json
EOF
}

# Validate integer target in [1, 95]. Echoes target on success, exits 1 on failure.
_validate_target_line() {
    local target="${1:-}"
    if ! [[ "$target" =~ ^[0-9]+$ ]]; then
        echo "[sentinel-handshake] ERROR: target_line must be an integer (got: '$target')" >&2
        return 1
    fi
    if [ "$target" -lt 1 ] || [ "$target" -gt 95 ]; then
        echo "[sentinel-handshake] ERROR: target_line must be between 1 and 95 (got: $target). Presets: 40 (quick-win), 70 (full-bundle)." >&2
        return 1
    fi
    return 0
}

# Derive branch target: branch == line. Il valore inserito dall'utente e' il
# floor minimo e vale identico per line e branch (preset 40/70 e custom).
# La CI threshold (vedi cmd_write) puo' alzarlo, mai abbassarlo.
_derive_branch_target() {
    echo "$1"
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
# C-1 FIX: read ci_threshold_override / ci_thresholds_source / high_branch_gap
# from user-choice.json (written by cmd_write) when it exists.
# ctx in pending-user-choice.json does NOT carry these fields → always None.
import os as _os
_uc_path = _os.path.join(_os.path.dirname(path), "user-choice.json")
_ci_override = None
_ci_src = None
_hbg = None
try:
    with open(_uc_path, "r", encoding="utf-8") as _uc:
        _uc_data = json.load(_uc)
    _ci_override = _uc_data.get("ci_threshold_override")
    _ci_src = _uc_data.get("ci_thresholds_source")
    _hbg = _uc_data.get("high_branch_gap")
except Exception:
    pass
emit("ci_threshold_override", _ci_override)
emit("ci_thresholds_source", _ci_src)
emit("high_branch_gap", _hbg)
import pathlib as _pl
_pred = _pl.Path(path).parent / "coverage-prediction.json"
if _pred.exists():
    try:
        _p = json.loads(_pred.read_text())
        emit("predicted_branch_after_phase7", _p["predictions"]["predicted_branch_after_phase7"])
        emit("branch_risk", _p["risk_flags"][0]["flag"] if _p.get("risk_flags") else "NONE")
    except Exception:
        pass
PY
}

cmd_write() {
    local repo="${1:?usage: write <repo> <target_line>}"
    local target="${2:?usage: write <repo> <target_line>}"

    _validate_target_line "$target" || return 1

    local sentinel="$repo/.code-coverage/pending-user-choice.json"
    if [ ! -f "$sentinel" ]; then
        echo "[sentinel-handshake] ERROR: sentinel not found: $sentinel" >&2
        return 1
    fi

    local out="$repo/.code-coverage/user-choice.json"
    python3 - "$sentinel" "$out" "$target" "$repo" <<'PY'
import json
import os
import sys
import time

sentinel_path = sys.argv[1]
out_path = sys.argv[2]
target = int(sys.argv[3])
repo = sys.argv[4]

try:
    with open(sentinel_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
except (OSError, json.JSONDecodeError) as exc:
    print(f"[sentinel-handshake] ERROR: invalid sentinel JSON: {exc}",
          file=sys.stderr)
    sys.exit(1)

ctx = data.get("context") or {}
opts = data.get("options") or {}

# Preset paths use the pre-computed p50/p90 from the sentinel.
# Custom paths fall back to the closest preset bucket (A=40 for <55, B=70 otherwise).
if target == 40:
    chosen = opts.get("A") or {}
    preset = "quick-win"
elif target == 70:
    chosen = opts.get("B") or {}
    preset = "full-bundle"
else:
    chosen = opts.get("A") if target < 55 else opts.get("B")
    chosen = chosen or {}
    preset = "custom"

p50 = chosen.get("estimated_wallclock_min_p50")
p90 = chosen.get("estimated_wallclock_min_p90")

# target_branch == target_line: il valore inserito dall'utente e' il floor
# minimo e vale identico per line e branch (preset 40/70 e custom). La CI
# threshold sotto puo' alzarlo, mai abbassarlo.
target_branch = target

# ── CI threshold override ─────────────────────────────────────────────────────
_user_line = target
_user_branch = target_branch
_eff_line = _user_line
_eff_branch = _user_branch
_ci_src = "none"

_ci_path = os.path.join(repo, ".code-coverage", "ci-thresholds.json")
try:
    with open(_ci_path, "r", encoding="utf-8") as _fh:
        _ci = json.load(_fh)
    _ci_branch = _ci.get("COVERAGE_BRANCHES") or _ci.get("COVERAGE_THRESHOLD")
    _ci_line = _ci.get("COVERAGE_LINES") or _ci.get("COVERAGE_THRESHOLD")
    if _ci_branch is not None and float(_ci_branch) > _eff_branch:
        _eff_branch = min(95, float(_ci_branch))
    if _ci_line is not None and float(_ci_line) > _eff_line:
        _eff_line = min(95, float(_ci_line))
    _ci_src = _ci.get("source", "none")
except Exception:
    pass

# ── high_branch_gap surfacing ─────────────────────────────────────────────────
_high_branch_gap = False
try:
    _stack_path = os.path.join(repo, ".code-coverage", "stack.json")
    with open(_stack_path, "r", encoding="utf-8") as _sfh:
        _stack = json.load(_sfh)
    _delta = _stack.get("line_branch_delta")
    _high_branch_gap = (_delta is not None and _delta > 15)
except Exception:
    pass

# ── determine effective override flag and update targets ──────────────────────
_override = (_eff_branch > _user_branch) or (_eff_line > _user_line)
target = int(_eff_line)
target_branch = int(_eff_branch)

if _override:
    _msg = (
        f"[sentinel] WARN: CI enforces higher thresholds than user preset. "
        f"Effective line={target} branch={target_branch} "
        f"(user line={_user_line} branch={_user_branch}). source={_ci_src}"
    )
    _log_path = os.path.join(repo, ".code-coverage", "decisions.log")
    with open(_log_path, "a", encoding="utf-8") as _lf:
        _lf.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {_msg}\n")

payload = {
    "target_line": target,
    "target_branch": target_branch,
    "size_class": ctx.get("size_class"),
    "estimated_wallclock_min_p50": p50,
    "estimated_wallclock_min_p90": p90,
    "user_choice_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "source": "sentinel_handshake",
    "preset": preset,
    "user_requested_line": _user_line,
    "user_requested_branch": _user_branch,
    "ci_threshold_override": _override,
    "ci_thresholds_source": _ci_src,
    "high_branch_gap": _high_branch_gap,
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

# cmd_prompt: 3-option interactive prompt.
# Exports TARGET_LINE and TARGET_BRANCH for downstream scripts (when sourced),
# then delegates to cmd_write which materialises user-choice.json.
cmd_prompt() {
    local repo="${1:?usage: prompt <repo>}"
    local choice=""
    local custom=""

    while true; do
        echo "Choose a coverage target:" >&2
        echo "  1) Quick Win  — 40% line / 30% branch" >&2
        echo "  2) Full Bundle — 70% line / 60% branch" >&2
        echo "  3) Custom     — enter your own line target (1–95)" >&2
        printf "Selection [1/2/3]: " >&2
        read -r choice </dev/tty || {
            echo "[sentinel-handshake] ERROR: stdin closed (cannot prompt)" >&2
            return 1
        }
        case "$choice" in
            1)
                TARGET_LINE=40
                TARGET_BRANCH=30
                break
                ;;
            2)
                TARGET_LINE=70
                TARGET_BRANCH=60
                break
                ;;
            3)
                while true; do
                    printf "Custom target line (1-95): " >&2
                    read -r custom </dev/tty || {
                        echo "[sentinel-handshake] ERROR: stdin closed" >&2
                        return 1
                    }
                    if _validate_target_line "$custom" 2>/dev/null; then
                        TARGET_LINE="$custom"
                        TARGET_BRANCH="$(_derive_branch_target "$custom")"
                        break 2
                    fi
                    echo "Invalid value. Enter integer between 1 and 95." >&2
                done
                ;;
            *)
                echo "Invalid choice. Pick 1, 2, or 3." >&2
                ;;
        esac
    done

    export TARGET_LINE TARGET_BRANCH
    echo "[sentinel-handshake] selected TARGET_LINE=$TARGET_LINE TARGET_BRANCH=$TARGET_BRANCH" >&2
    cmd_write "$repo" "$TARGET_LINE"
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
        prompt)
            cmd_prompt "$@"
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
