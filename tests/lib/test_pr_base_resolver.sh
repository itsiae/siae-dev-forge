#!/usr/bin/env bash
# test_pr_base_resolver.sh — unit tests for lib/pr-base-resolver.sh (REQ-DF-03)
# ─────────────────────────────────────────────────────────────────
# Covers: precedenza (1) gh pr view esistente, (2) merge-base distance
# voting su origin/release/* + origin/sviluppo, (3) symbolic-ref
# origin/HEAD, (4) fallback letterale 'main'.
# Ogni scenario usa un repo git temporaneo isolato (fixture), mai il
# repo DevForge stesso, per non dipendere dallo stato reale di origin.
# ─────────────────────────────────────────────────────────────────
set -uo pipefail
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
ko(){ echo "  FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

REPO_ROOT="$(git rev-parse --show-toplevel)"
LIB_FILE="${REPO_ROOT}/lib/pr-base-resolver.sh"

if [ ! -f "$LIB_FILE" ]; then
    echo "FAIL — $LIB_FILE not found"
    exit 1
fi

# shellcheck disable=SC1090
source "$LIB_FILE"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

_mk_bare_remote() {
    local remote_dir="$WORKDIR/$1.git"
    git init --bare -q "$remote_dir"
    printf '%s' "$remote_dir"
}

_mk_clone() {
    local clone_dir="$WORKDIR/$1"
    git clone -q "$2" "$clone_dir"
    git -C "$clone_dir" config user.email "test@example.com"
    git -C "$clone_dir" config user.name "Test"
    printf '%s' "$clone_dir"
}

_commit() {
    git -C "$1" commit -q --allow-empty -m "$2"
}

# ── Scenario 1: branch derivato da main, nessuna PR, nessun release/*/sviluppo
REMOTE1=$(_mk_bare_remote "remote1")
CLONE1=$(_mk_clone "clone1" "$REMOTE1")
_commit "$CLONE1" "chore: init main"
git -C "$CLONE1" push -q -u origin main
git -C "$CLONE1" checkout -q -b feature/scenario-main
_commit "$CLONE1" "feat: lavoro su feature/scenario-main"
git -C "$REMOTE1" symbolic-ref HEAD refs/heads/main
RESULT=$(cd "$CLONE1" && devforge_resolve_pr_base 2>/dev/null)
[ "$RESULT" = "main" ] && ok "Scenario1 branch-off-main risolve main" \
    || ko "Scenario1 branch-off-main risolve main" "got '$RESULT'"

# ── Scenario 2: branch derivato da 'sviluppo' → voting sceglie sviluppo
REMOTE2=$(_mk_bare_remote "remote2")
CLONE2=$(_mk_clone "clone2" "$REMOTE2")
_commit "$CLONE2" "chore: init main"
git -C "$CLONE2" push -q -u origin main
git -C "$CLONE2" checkout -q -b sviluppo
_commit "$CLONE2" "chore: init sviluppo"
git -C "$CLONE2" push -q -u origin sviluppo
git -C "$CLONE2" checkout -q -b feature/scenario-sviluppo
_commit "$CLONE2" "feat: lavoro su feature/scenario-sviluppo"
RESULT=$(cd "$CLONE2" && devforge_resolve_pr_base 2>/dev/null)
[ "$RESULT" = "sviluppo" ] && ok "Scenario2 branch-off-sviluppo risolve sviluppo" \
    || ko "Scenario2 branch-off-sviluppo risolve sviluppo" "got '$RESULT'"

# ── Scenario 3: branch derivato da 'release/x' → voting sceglie release/x
REMOTE3=$(_mk_bare_remote "remote3")
CLONE3=$(_mk_clone "clone3" "$REMOTE3")
_commit "$CLONE3" "chore: init main"
git -C "$CLONE3" push -q -u origin main
git -C "$CLONE3" checkout -q -b sviluppo
_commit "$CLONE3" "chore: init sviluppo"
git -C "$CLONE3" push -q -u origin sviluppo
git -C "$CLONE3" checkout -q -b release/2026-07-01
_commit "$CLONE3" "chore: init release/2026-07-01"
git -C "$CLONE3" push -q -u origin release/2026-07-01
git -C "$CLONE3" checkout -q -b fix/scenario-release
_commit "$CLONE3" "fix: lavoro su fix/scenario-release"
RESULT=$(cd "$CLONE3" && devforge_resolve_pr_base 2>/dev/null)
[ "$RESULT" = "release/2026-07-01" ] && ok "Scenario3 branch-off-release risolve release/2026-07-01" \
    || ko "Scenario3 branch-off-release risolve release/2026-07-01" "got '$RESULT'"

# ── Scenario 4: gh stub ritorna una PR esistente con baseRefName='sviluppo' → precedenza (1)
REMOTE4=$(_mk_bare_remote "remote4")
CLONE4=$(_mk_clone "clone4" "$REMOTE4")
_commit "$CLONE4" "chore: init main"
git -C "$CLONE4" push -q -u origin main
git -C "$CLONE4" checkout -q -b feature/scenario-pr-exists
_commit "$CLONE4" "feat: lavoro su feature/scenario-pr-exists"
FAKE_GH_DIR="$WORKDIR/fakebin"
mkdir -p "$FAKE_GH_DIR"
cat > "$FAKE_GH_DIR/gh" <<'FAKEGH'
#!/usr/bin/env bash
if [ "$1" = "pr" ] && [ "$2" = "view" ]; then
    echo "sviluppo"
    exit 0
fi
exit 1
FAKEGH
chmod +x "$FAKE_GH_DIR/gh"
RESULT=$(cd "$CLONE4" && PATH="$FAKE_GH_DIR:$PATH" devforge_resolve_pr_base 2>/dev/null)
[ "$RESULT" = "sviluppo" ] && ok "Scenario4 PR esistente vince su merge-base voting" \
    || ko "Scenario4 PR esistente vince su merge-base voting" "got '$RESULT'"

echo "pr-base-resolver: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
