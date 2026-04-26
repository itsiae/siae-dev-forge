#!/usr/bin/env bash
# test_file_taxonomy.sh — unit tests for lib/file-taxonomy.sh (ADR-005)
# ─────────────────────────────────────────────────────────────────
# Covers: devforge_file_requires_tdd, devforge_file_requires_brainstorming,
# devforge_file_is_config_only, path exclusions, DEVFORGE_BASH_TDD opt-in.
# ─────────────────────────────────────────────────────────────────
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
LIB_FILE="${REPO_ROOT}/lib/file-taxonomy.sh"

if [ ! -f "$LIB_FILE" ]; then
    echo "FAIL — $LIB_FILE not found"
    exit 1
fi

# shellcheck disable=SC1090
source "$LIB_FILE"

_expect_tdd() {
    local name="$1" path="$2"
    if devforge_file_requires_tdd "$path"; then
        echo "  PASS  $name — $path"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — $path should require TDD"; FAIL=$((FAIL+1))
    fi
}

_expect_no_tdd() {
    local name="$1" path="$2"
    if devforge_file_requires_tdd "$path"; then
        echo "  FAIL  $name — $path should NOT require TDD"; FAIL=$((FAIL+1))
    else
        echo "  PASS  $name — $path"; PASS=$((PASS+1))
    fi
}

_expect_brainstorm() {
    local name="$1" path="$2"
    if devforge_file_requires_brainstorming "$path"; then
        echo "  PASS  $name — $path"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — $path should require brainstorming"; FAIL=$((FAIL+1))
    fi
}

_expect_no_brainstorm() {
    local name="$1" path="$2"
    if devforge_file_requires_brainstorming "$path"; then
        echo "  FAIL  $name — $path should NOT require brainstorming"; FAIL=$((FAIL+1))
    else
        echo "  PASS  $name — $path"; PASS=$((PASS+1))
    fi
}

_expect_config_only() {
    local name="$1" path="$2"
    if devforge_file_is_config_only "$path"; then
        echo "  PASS  $name — $path"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — $path should be config_only"; FAIL=$((FAIL+1))
    fi
}

echo "=== 1. TDD-required extensions ==="
_expect_tdd   "java"         "src/main/java/UserService.java"
_expect_tdd   "typescript"   "src/api.ts"
_expect_tdd   "tsx"          "src/App.tsx"
_expect_tdd   "javascript"   "src/util.js"
_expect_tdd   "python"       "app/handler.py"
_expect_tdd   "vue"          "src/Button.vue"
_expect_tdd   "go"           "cmd/main.go"
_expect_tdd   "kotlin"       "app/Foo.kt"
_expect_tdd   "ruby"         "lib/foo.rb"
_expect_tdd   "rust"         "src/main.rs"
_expect_tdd   "swift"        "Sources/App/App.swift"
_expect_tdd   "scala"        "src/main/scala/Foo.scala"
_expect_tdd   "sql"          "migrations/001_users.sql"

echo ""
echo "=== 2. Extensions OUTSIDE TDD scope ==="
_expect_no_tdd "yaml"        "config/app.yaml"
_expect_no_tdd "yml"         ".github/workflows/ci.yml"
_expect_no_tdd "json"        "package.json"
_expect_no_tdd "tf"          "terraform/main.tf"
_expect_no_tdd "hcl"         "terragrunt.hcl"
_expect_no_tdd "markdown"    "README.md"
_expect_no_tdd "unknown"     "Dockerfile"

echo ""
echo "=== 3. Path exclusions (test files and docs) ==="
_expect_no_tdd "test dir"         "tests/unit/test_foo.py"
_expect_no_tdd "__tests__"        "src/__tests__/foo.spec.ts"
_expect_no_tdd "spec.ts"          "src/foo.spec.ts"
_expect_no_tdd "test.py prefix"   "tests/test_user.py"
_expect_no_tdd "go test suffix"   "pkg/foo_test.go"
_expect_no_tdd "java Test"        "src/test/java/FooTest.java"
_expect_no_tdd "java IT"          "src/test/java/FooIT.java"
_expect_no_tdd "docs"             "docs/plans/foo-design.md"
_expect_no_tdd "evals"            "evals/cases/foo.yaml"

echo ""
echo "=== 4. .sh deny-by-default, opt-in via DEVFORGE_BASH_TDD ==="
unset DEVFORGE_BASH_TDD
_expect_no_tdd "sh default"       "hooks/my-hook.sh"
_expect_no_tdd "bash default"     "scripts/build.bash"
(
    export DEVFORGE_BASH_TDD=1
    if devforge_file_requires_tdd "hooks/my-hook.sh"; then
        echo "  PASS  sh with DEVFORGE_BASH_TDD=1 requires TDD"
    else
        echo "  FAIL  sh with DEVFORGE_BASH_TDD=1 should require TDD"
        exit 1
    fi
) && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

echo ""
echo "=== 5. brainstorming-required superset = TDD + .tf/.hcl ==="
_expect_brainstorm    "java triggers brainstorm"  "src/main/java/X.java"
_expect_brainstorm    "tf triggers brainstorm"    "terraform/vpc.tf"
_expect_brainstorm    "hcl triggers brainstorm"   "modules/foo/terragrunt.hcl"
_expect_brainstorm    "python triggers brainstorm" "app/foo.py"
_expect_no_brainstorm "yaml no brainstorm"        "config/values.yaml"
_expect_no_brainstorm "md no brainstorm"          "README.md"
_expect_no_brainstorm "test file no brainstorm"   "tests/test_foo.py"

echo ""
echo "=== 6. config_only classification ==="
_expect_config_only "yaml"        "k8s/deploy.yaml"
_expect_config_only "yml"         "ci.yml"
_expect_config_only "json"        "package.json"
_expect_config_only "toml"        "pyproject.toml"
_expect_config_only "ini"         "setup.ini"
_expect_config_only "properties"  "application.properties"

# Negative: java is not config_only
if devforge_file_is_config_only "src/Foo.java"; then
    echo "  FAIL  java wrongly classified as config_only"; FAIL=$((FAIL+1))
else
    echo "  PASS  java not config_only"; PASS=$((PASS+1))
fi

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
