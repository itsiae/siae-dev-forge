#!/usr/bin/env bash
# test_cmd_parser.sh — lib/cmd-parser.sh (ADR-006 token parser)
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091
source "${REPO_ROOT}/lib/cmd-parser.sh"

_expect_match() {
    local name="$1" first="$2" second="$3" cmd="$4"
    if devforge_cmd_matches "$first" "$second" "$cmd"; then
        echo "  PASS  $name"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — cmd=[$cmd]"; FAIL=$((FAIL+1))
    fi
}

_expect_no_match() {
    local name="$1" first="$2" second="$3" cmd="$4"
    if ! devforge_cmd_matches "$first" "$second" "$cmd"; then
        echo "  PASS  $name"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — cmd=[$cmd] unexpectedly matched"; FAIL=$((FAIL+1))
    fi
}

echo "=== 1. Direct match ==="
_expect_match "git commit"              git commit "git commit -m 'x'"
_expect_match "git commit with flags"   git commit "git commit --amend"
_expect_match "git checkout -b"         git checkout "git checkout -b feature/x"
_expect_match "gh pr create"            gh  pr      "gh pr create --title x"

echo ""
echo "=== 2. Prefix stripping ==="
_expect_match "FOO=bar git commit"      git commit "FOO=bar git commit"
_expect_match "FOO=bar BAZ=qux git commit" git commit "FOO=bar BAZ=qux git commit"
_expect_match "sudo git commit"         git commit "sudo git commit"
_expect_match "env FOO=bar git commit"  git commit "env FOO=bar git commit"
_expect_match "timeout 5 git commit"    git commit "timeout 5 git commit"

echo ""
echo "=== 3. False-positive immunity ==="
_expect_no_match "echo 'git commit'"    git commit "echo 'git commit'"
_expect_no_match "python wrapper"       git commit "python run_git_commit.py"
_expect_no_match "pipeline with commit" git commit "git log --oneline | grep commit"
_expect_no_match "git log, not commit"  git commit "git log --format=%s"
_expect_no_match "in-string"            git commit "/bin/git-commit-msg-hook"

echo ""
echo "=== 4. Primary segment (split on shell operators) ==="
_expect_match "pipeline primary"        git commit "git commit && git push"
_expect_match "semicolon primary"       git commit "git commit ; exit"
_expect_no_match "piped-away"           git commit "cat log | git commit"
# `cat log | git commit` primary = `cat log`, second call of git commit is
# downstream of pipe — our tokenizer cannot see it (intentional: safer to
# skip than to block on ambiguous inputs).

echo ""
echo "=== 5. gh pr create / edit detection ==="
_expect_match "gh pr create"   gh pr "gh pr create --base main"
_expect_match "gh pr edit"     gh pr "gh pr edit 42 --body Z"
# third-token check for the action
THIRD=$(devforge_third_token "gh pr create --base main")
if [ "$THIRD" = "create" ]; then
    echo "  PASS  third token = create"; PASS=$((PASS+1))
else
    echo "  FAIL  third token actual=[$THIRD]"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 6. Compound command matching (devforge_cmd_has_subcommand) ==="
_expect_sub() {
    local name="$1"; shift
    local cmd="$1"; shift
    if devforge_cmd_has_subcommand "$cmd" "$@"; then
        echo "  PASS  $name"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — cmd=[$cmd]"; FAIL=$((FAIL+1))
    fi
}
_expect_no_sub() {
    local name="$1"; shift
    local cmd="$1"; shift
    if ! devforge_cmd_has_subcommand "$cmd" "$@"; then
        echo "  PASS  $name"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — cmd=[$cmd] unexpectedly matched"; FAIL=$((FAIL+1))
    fi
}
_expect_sub    "cd && gh pr create"          'cd /x && gh pr create --base main' gh pr create
_expect_sub    "cd && env -u P gh pr create" 'cd /x && env -u http_proxy gh pr create' gh pr create
_expect_sub    "env -u doppio"               'env -u http_proxy -u https_proxy gh pr create' gh pr create
_expect_sub    "env -C dir"                  'env -C /tmp gh pr edit 42' gh pr edit
_expect_sub    "env -i bare flag"            'env -i git commit -m x' git commit
_expect_sub    "semicolon git commit"        'cd /x; git commit -m x' git commit
_expect_sub    "downstream di pipe"          'cat body.md | gh pr create --base main' gh pr create
_expect_no_sub "stringa con separatori"      "echo 'usa: git commit'" git commit
_expect_no_sub "wrapper python"              'python run_git_commit.py && ls' git commit
_expect_no_sub "git log non commit"          'cd /x && git log --oneline' git commit
# _devforge_segments: split corretto su tutti i separatori
SEG_COUNT=$(_devforge_segments 'a|b;c&&d||e' | grep -c "")
if [ "$SEG_COUNT" -eq 5 ]; then
    echo "  PASS  _devforge_segments: 5 segmenti da a|b;c&&d||e"; PASS=$((PASS+1))
else
    echo "  FAIL  _devforge_segments: attesi 5 segmenti, got $SEG_COUNT"; FAIL=$((FAIL+1))
fi
# env -u: first token dopo strip e' il comando reale
FT=$(devforge_first_token "env -u http_proxy gh pr create")
if [ "$FT" = "gh" ]; then
    echo "  PASS  strip env -u: first token = gh"; PASS=$((PASS+1))
else
    echo "  FAIL  strip env -u: first token = [$FT]"; FAIL=$((FAIL+1))
fi

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
