#!/usr/bin/env bash
# cmd-parser.sh — token-aware command parsing for Bash-matcher hooks (ADR-006)
# ─────────────────────────────────────────────────────────────────
# Replaces the fragile regex `[[ $cmd =~ git[[:space:]]+commit ]]` that matched
# strings like `git log | grep commit`, `echo "git commit"`, and
# `python run_git_commit.py`.
#
# Strategy: strip leading env-var assignments (FOO=bar) and wrapper commands
# (sudo, env, nice, time, timeout), take the primary segment before any
# shell operator (| & ; && || >), and expose first/second/third tokens.
# ─────────────────────────────────────────────────────────────────

# _devforge_primary_cmd COMMAND
# Return the primary segment (before | & ; && || > <). Shell-literal strings
# and heredocs are NOT parsed — the intent is a cheap static tokenizer that
# errs on the side of skipping (allow) rather than false-positive blocks.
_devforge_primary_cmd() {
    local cmd="$1"
    # Cut on the first unescaped shell operator — best-effort.
    cmd="${cmd%%|*}"
    cmd="${cmd%%&*}"
    cmd="${cmd%%;*}"
    cmd="${cmd%%>*}"
    cmd="${cmd%%<*}"
    printf '%s' "$cmd"
}

# _devforge_strip_prefix COMMAND
# Remove leading VAR=val assignments and known wrapper commands
# (sudo, env, exec, nice, time, timeout). Leaves the target command as head.
# Loops so `timeout 5 env FOO=bar sudo git commit` fully collapses.
_devforge_strip_prefix() {
    local cmd="$1" prev=""
    cmd=$(_devforge_primary_cmd "$cmd")
    while [ "$cmd" != "$prev" ]; do
        prev="$cmd"
        # Trim leading whitespace first
        cmd="${cmd#"${cmd%%[![:space:]]*}"}"
        # 1. Leading env-var assignment: FOO=bar ...
        if [[ "$cmd" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
            cmd=$(echo "$cmd" | sed -E 's/^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]*//')
            continue
        fi
        # 2. Leading wrapper command (with optional next argument).
        case "$cmd" in
            sudo\ *|exec\ *|nice\ *|time\ *)
                cmd="${cmd#* }"
                continue
                ;;
            env\ *)
                # `env` may be followed by VAR=val pairs (handled by #1
                # after we drop the literal `env` word).
                cmd="${cmd#env }"
                continue
                ;;
            timeout\ *)
                # timeout's first arg is a duration — drop two words.
                cmd="${cmd#timeout }"
                cmd="${cmd#* }"
                continue
                ;;
        esac
    done
    printf '%s' "$cmd"
}

# devforge_first_token COMMAND
devforge_first_token() {
    local stripped; stripped=$(_devforge_strip_prefix "$1")
    printf '%s' "$stripped" | awk '{print $1; exit}'
}

# devforge_second_token COMMAND
devforge_second_token() {
    local stripped; stripped=$(_devforge_strip_prefix "$1")
    printf '%s' "$stripped" | awk '{print $2; exit}'
}

# devforge_third_token COMMAND
devforge_third_token() {
    local stripped; stripped=$(_devforge_strip_prefix "$1")
    printf '%s' "$stripped" | awk '{print $3; exit}'
}

# devforge_cmd_matches FIRST SECOND COMMAND
# Return 0 if the command's first+second tokens match FIRST and SECOND.
devforge_cmd_matches() {
    local want_first="$1" want_second="$2" cmd="$3"
    local first second
    first=$(devforge_first_token "$cmd")
    second=$(devforge_second_token "$cmd")
    [ "$first" = "$want_first" ] && [ "$second" = "$want_second" ]
}
