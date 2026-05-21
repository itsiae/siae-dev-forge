#!/usr/bin/env bash
# devforge-install-runners.sh — OSS runner toolchain installer for DevForge
#
# Installs the 17-tool review-evidence v2 OSS runner toolchain in user-space.
# Covers cross-stack SAST/secrets (semgrep, gitleaks, eslint-plugin-security,
# ts-unused-exports), Java (maven, spotbugs), Python (bandit, pip-audit,
# vulture, pyright), iOS (swiftlint), Android (detekt, ktlint) and AWS
# (tflint, tfsec, checkov, cfn-lint).
#
# Usage:
#   bash scripts/devforge-install-runners.sh [--stack <name>] [--check] [--dry-run]
#
# Flags:
#   --stack <java|python|ios|android|aws|cross|all>  Select stack (default: all)
#   --check                                          Report INSTALLED/MISSING only
#   --dry-run                                        Print commands without running
#   -h, --help                                       Show usage
#
# Hard constraints:
#   * NO sudo — pip3 --user, npm via NPM_CONFIG_PREFIX, brew runs no-sudo by design.
#   * Idempotent — pre-flight `command -v` skips already-installed tools.
#   * macOS BSD portability — no GNU `timeout` assumption.
#   * Final report: INSTALLED / SKIPPED / FAILED / NOT_APPLICABLE; exit 1 on FAILED>0.

set -euo pipefail

# -----------------------------------------------------------------------------
# Pinned versions for Linux GitHub-release downloads
# -----------------------------------------------------------------------------
DETEKT_VERSION="1.23.7"
KTLINT_VERSION="1.4.1"
TFLINT_VERSION="0.55.0"
TFSEC_VERSION="1.28.11"
GITLEAKS_VERSION="8.21.2"
SPOTBUGS_VERSION="4.8.6"

# -----------------------------------------------------------------------------
# Color/logging — TTY-aware, no-op on pipes/CI
# -----------------------------------------------------------------------------
if [[ -t 1 ]] && command -v tput >/dev/null 2>&1 && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
    C_RED=$(tput setaf 1); C_GREEN=$(tput setaf 2); C_YELLOW=$(tput setaf 3)
    C_BLUE=$(tput setaf 4); C_DIM=$(tput dim); C_RESET=$(tput sgr0)
else
    C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_DIM=""; C_RESET=""
fi

log_info()  { echo "${C_BLUE}[INFO]${C_RESET}  $*"; }
log_ok()    { echo "${C_GREEN}[OK]${C_RESET}    $*"; }
log_warn()  { echo "${C_YELLOW}[WARN]${C_RESET}  $*"; }
log_err()   { echo "${C_RED}[ERR]${C_RESET}   $*" >&2; }
log_skip()  { echo "${C_DIM}[SKIP]${C_RESET}  $*"; }

# -----------------------------------------------------------------------------
# CLI parsing
# -----------------------------------------------------------------------------
STACK="all"
CHECK_ONLY=0
DRY_RUN=0
ENSURE_TOOL=""
ENSURE_TIMEOUT="${DEVFORGE_RUNNER_ENSURE_TIMEOUT:-90}"

usage() {
    cat <<'EOF'
Usage: devforge-install-runners.sh [--stack <name>] [--check] [--dry-run] [--ensure <tool>] [-h|--help]

Stacks: java | python | ios | android | aws | cross | all  (default: all)

Examples:
  bash scripts/devforge-install-runners.sh
  bash scripts/devforge-install-runners.sh --check
  bash scripts/devforge-install-runners.sh --dry-run --stack python
  bash scripts/devforge-install-runners.sh --stack cross
  bash scripts/devforge-install-runners.sh --ensure semgrep    # lazy install + warning rosso non-blocking

Flags:
  --stack <name>     Limit install to one stack (java/python/ios/android/aws/cross/all)
  --check            Report INSTALLED/MISSING table only — no install
  --dry-run          Print install commands without executing
  --ensure <tool>    Lazy auto-install per singolo tool, NON-BLOCCANTE. Se missing
                     dopo install: WARNING ROSSO su stderr, exit 0. Default
                     timeout 90s, override via DEVFORGE_RUNNER_ENSURE_TIMEOUT.
  -h, --help         Show this help

The installer is user-space only (no sudo). Pinned Linux GitHub-release
versions live at the top of the script (DETEKT_VERSION, KTLINT_VERSION,
TFLINT_VERSION, TFSEC_VERSION, GITLEAKS_VERSION, SPOTBUGS_VERSION).
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --stack)
            STACK="${2:-}"; shift 2 || { log_err "--stack requires a value"; exit 2; }
            ;;
        --stack=*)
            STACK="${1#*=}"; shift
            ;;
        --check)
            CHECK_ONLY=1; shift
            ;;
        --dry-run)
            DRY_RUN=1; shift
            ;;
        --ensure)
            ENSURE_TOOL="${2:-}"; shift 2 || { log_err "--ensure requires a tool name"; exit 2; }
            ;;
        --ensure=*)
            ENSURE_TOOL="${1#*=}"; shift
            ;;
        -h|--help)
            usage; exit 0
            ;;
        *)
            log_err "Unknown argument: $1"
            usage >&2
            exit 2
            ;;
    esac
done

case "$STACK" in
    java|python|ios|android|aws|cross|all) : ;;
    *)
        log_err "Invalid --stack '$STACK' (expected: java|python|ios|android|aws|cross|all)"
        exit 2
        ;;
esac

# -----------------------------------------------------------------------------
# --ensure mode (v1.63.5): lazy auto-install per singolo tool, non-bloccante
#
# Workflow:
#   1. Check if $ENSURE_TOOL is already in PATH -> exit 0 silently
#   2. Tenta install (timeout DEVFORGE_RUNNER_ENSURE_TIMEOUT secondi)
#   3. Re-check. Se OK -> exit 0
#   4. Se ancora missing -> stampa WARNING ROSSO su stderr, exit 0 (NO BLOCK)
#
# Uso: bash scripts/devforge-install-runners.sh --ensure semgrep
# -----------------------------------------------------------------------------
if [ -n "$ENSURE_TOOL" ]; then
    # Step 1: già installato?
    if command -v "$ENSURE_TOOL" >/dev/null 2>&1; then
        exit 0
    fi
    # Determina stack del tool (mappa inline — le funzioni cross_stack_tools/etc
    # sono definite piu' avanti nel file, quindi non disponibili qui)
    case "$ENSURE_TOOL" in
        semgrep|gitleaks|eslint|ts-unused-exports) _ensure_stack="cross" ;;
        mvn|spotbugs)                              _ensure_stack="java" ;;
        bandit|pip-audit|vulture|pyright)          _ensure_stack="python" ;;
        swiftlint)                                  _ensure_stack="ios" ;;
        detekt|ktlint)                              _ensure_stack="android" ;;
        tflint|tfsec|checkov|cfn-lint)              _ensure_stack="aws" ;;
        *)                                          _ensure_stack="" ;;
    esac
    if [ -z "$_ensure_stack" ]; then
        printf '\033[1;31m[DEVFORGE WARN]\033[0m runner unknown: %s (not in any stack registry) — security scan limited\n' "$ENSURE_TOOL" >&2
        exit 0
    fi
    # Step 2: tenta install con timeout (background con kill se eccede)
    log_info "ensure: $ENSURE_TOOL missing — attempting install (stack=$_ensure_stack, timeout=${ENSURE_TIMEOUT}s)..." >&2
    _ensure_log="/tmp/devforge-ensure-${ENSURE_TOOL}.log"
    (
        STACK="$_ensure_stack" CHECK_ONLY=0 ENSURE_TOOL="" \
            bash "$0" --stack "$_ensure_stack" > "$_ensure_log" 2>&1
    ) &
    _ensure_pid=$!
    _elapsed=0
    while kill -0 $_ensure_pid 2>/dev/null; do
        if [ "$_elapsed" -ge "$ENSURE_TIMEOUT" ]; then
            kill $_ensure_pid 2>/dev/null || true
            break
        fi
        sleep 2
        _elapsed=$((_elapsed + 2))
    done
    wait $_ensure_pid 2>/dev/null || true
    # Step 3: re-check
    if command -v "$ENSURE_TOOL" >/dev/null 2>&1; then
        log_ok "ensure: $ENSURE_TOOL installed successfully" >&2
        exit 0
    fi
    # Step 4: WARNING ROSSO, exit 0 (NO BLOCK — security degraded ma non blocca workflow)
    printf '\033[1;31m[DEVFORGE WARN]\033[0m runner missing: %s (stack=%s) — security scan degraded.\n' "$ENSURE_TOOL" "$_ensure_stack" >&2
    printf '\033[1;31m[DEVFORGE WARN]\033[0m install manuale: bash scripts/devforge-install-runners.sh --stack %s\n' "$_ensure_stack" >&2
    printf '\033[1;31m[DEVFORGE WARN]\033[0m log auto-install: %s\n' "$_ensure_log" >&2
    exit 0
fi

# -----------------------------------------------------------------------------
# OS / arch detection
# -----------------------------------------------------------------------------
UNAME_S="$(uname -s 2>/dev/null || echo Unknown)"
UNAME_M="$(uname -m 2>/dev/null || echo unknown)"

case "$UNAME_S" in
    Darwin) OS="macos" ;;
    Linux)  OS="linux" ;;
    *)
        log_err "Unsupported OS: $UNAME_S (only Darwin/Linux are supported)"
        exit 2
        ;;
esac

log_info "OS=$OS arch=$UNAME_M stack=$STACK check_only=$CHECK_ONLY dry_run=$DRY_RUN"

# -----------------------------------------------------------------------------
# Counters
# -----------------------------------------------------------------------------
INSTALLED=0
SKIPPED=0
FAILED=0
NOT_APPLICABLE=0

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

# run_cmd: echo + execute, or echo-only under --dry-run.
run_cmd() {
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  ${C_DIM}\$${C_RESET} $*"
        return 0
    fi
    echo "  ${C_DIM}\$${C_RESET} $*"
    "$@"
}

# check_tool <name>: returns 0 if tool is on PATH, 1 otherwise.
check_tool() {
    command -v "$1" >/dev/null 2>&1
}

# report_check <tool>: prints "<tool> INSTALLED" or "<tool> MISSING".
report_check() {
    local tool="$1"
    if check_tool "$tool"; then
        printf "  %-22s ${C_GREEN}INSTALLED${C_RESET}\n" "$tool"
    else
        printf "  %-22s ${C_YELLOW}MISSING${C_RESET}\n" "$tool"
    fi
}

# install_brew_pkg <tool> <pkg>: brew install if missing.
install_brew_pkg() {
    local tool="$1" pkg="${2:-$1}"
    if check_tool "$tool"; then
        log_skip "$tool (already installed)"
        SKIPPED=$((SKIPPED+1))
        return 0
    fi
    if ! check_tool brew; then
        log_warn "brew missing — cannot install $tool. Install Homebrew first: https://brew.sh"
        FAILED=$((FAILED+1))
        return 0
    fi
    if run_cmd brew install "$pkg"; then
        [[ "$DRY_RUN" -eq 1 ]] || log_ok "installed $tool via brew"
        INSTALLED=$((INSTALLED+1))
    else
        log_err "brew install $pkg failed"
        FAILED=$((FAILED+1))
    fi
}

# install_pip_pkg <tool> <pkg>: pip3 install --user.
install_pip_pkg() {
    local tool="$1" pkg="${2:-$1}"
    if check_tool "$tool"; then
        log_skip "$tool (already installed)"
        SKIPPED=$((SKIPPED+1))
        return 0
    fi
    if ! check_tool pip3; then
        log_warn "pip3 missing — cannot install $tool. Install Python 3 + pip first."
        FAILED=$((FAILED+1))
        return 0
    fi
    if run_cmd pip3 install --user "$pkg"; then
        [[ "$DRY_RUN" -eq 1 ]] || log_ok "installed $tool via pip3 --user"
        INSTALLED=$((INSTALLED+1))
    else
        log_err "pip3 install --user $pkg failed"
        FAILED=$((FAILED+1))
    fi
}

# install_npm_global_pkg <tool> <pkg>: npm -g via $HOME prefix (no sudo).
install_npm_global_pkg() {
    local tool="$1" pkg="${2:-$1}"
    if check_tool "$tool"; then
        log_skip "$tool (already installed)"
        SKIPPED=$((SKIPPED+1))
        return 0
    fi
    if ! check_tool npm; then
        log_warn "npm missing — cannot install $tool. Install Node.js first."
        FAILED=$((FAILED+1))
        return 0
    fi
    # Honour user-set NPM_CONFIG_PREFIX, otherwise default to $HOME/.npm-global
    local npm_prefix="${NPM_CONFIG_PREFIX:-$HOME/.npm-global}"
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  ${C_DIM}\$${C_RESET} NPM_CONFIG_PREFIX=$npm_prefix npm install -g $pkg"
        return 0
    fi
    mkdir -p "$npm_prefix"
    if NPM_CONFIG_PREFIX="$npm_prefix" npm install -g "$pkg"; then
        log_ok "installed $tool via npm -g (prefix=$npm_prefix)"
        log_info "Ensure $npm_prefix/bin is on your PATH"
        INSTALLED=$((INSTALLED+1))
    else
        log_err "npm install -g $pkg failed"
        FAILED=$((FAILED+1))
    fi
}

# download_to_bin <tool> <url>: curl -sSL <url> -> $HOME/.local/bin/<tool>, chmod +x.
download_to_bin() {
    local tool="$1" url="$2"
    if check_tool "$tool"; then
        log_skip "$tool (already installed)"
        SKIPPED=$((SKIPPED+1))
        return 0
    fi
    if ! check_tool curl; then
        log_warn "curl missing — cannot download $tool"
        FAILED=$((FAILED+1))
        return 0
    fi
    local dest_dir="$HOME/.local/bin"
    local dest="$dest_dir/$tool"
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  ${C_DIM}\$${C_RESET} curl -sSL '$url' -o '$dest' && chmod +x '$dest'"
        return 0
    fi
    mkdir -p "$dest_dir"
    if run_cmd curl -fsSL "$url" -o "$dest" && chmod +x "$dest"; then
        log_ok "downloaded $tool to $dest"
        log_info "Ensure $dest_dir is on your PATH"
        INSTALLED=$((INSTALLED+1))
    else
        log_err "download $tool from $url failed"
        FAILED=$((FAILED+1))
    fi
}

# -----------------------------------------------------------------------------
# Stack tool lists (single source of truth for --check)
# -----------------------------------------------------------------------------
cross_stack_tools()  { echo "semgrep gitleaks eslint ts-unused-exports"; }
java_stack_tools()   { echo "mvn spotbugs"; }
python_stack_tools() { echo "bandit pip-audit vulture pyright"; }
ios_stack_tools()    { echo "swiftlint"; }
android_stack_tools(){ echo "detekt ktlint"; }
aws_stack_tools()    { echo "tflint tfsec checkov cfn-lint"; }

stack_active() {
    [[ "$STACK" == "all" || "$STACK" == "$1" ]]
}

# -----------------------------------------------------------------------------
# --check mode
# -----------------------------------------------------------------------------
if [[ "$CHECK_ONLY" -eq 1 ]]; then
    log_info "Running --check (no install)"
    echo ""
    if stack_active cross; then
        echo "${C_BLUE}== cross-stack ==${C_RESET}"
        for t in $(cross_stack_tools); do report_check "$t"; done
    fi
    if stack_active java; then
        echo "${C_BLUE}== java ==${C_RESET}"
        for t in $(java_stack_tools); do report_check "$t"; done
    fi
    if stack_active python; then
        echo "${C_BLUE}== python ==${C_RESET}"
        for t in $(python_stack_tools); do report_check "$t"; done
    fi
    if stack_active ios; then
        echo "${C_BLUE}== ios ==${C_RESET}"
        if [[ "$OS" != "macos" ]]; then
            echo "  ${C_DIM}NOT_APPLICABLE_ON_OS${C_RESET} (iOS toolchain requires macOS)"
        else
            for t in $(ios_stack_tools); do report_check "$t"; done
        fi
    fi
    if stack_active android; then
        echo "${C_BLUE}== android ==${C_RESET}"
        for t in $(android_stack_tools); do report_check "$t"; done
    fi
    if stack_active aws; then
        echo "${C_BLUE}== aws ==${C_RESET}"
        for t in $(aws_stack_tools); do report_check "$t"; done
    fi
    echo ""
    log_info "Check complete."
    exit 0
fi

# -----------------------------------------------------------------------------
# Install: cross-stack
# -----------------------------------------------------------------------------
if stack_active cross; then
    echo "${C_BLUE}== cross-stack (semgrep, gitleaks, eslint-plugin-security, ts-unused-exports) ==${C_RESET}"
    if [[ "$OS" == "macos" ]]; then
        install_brew_pkg semgrep
        install_brew_pkg gitleaks
    else
        install_pip_pkg semgrep
        if check_tool gitleaks; then
            log_skip "gitleaks (already installed)"; SKIPPED=$((SKIPPED+1))
        elif check_tool curl; then
            tarball_url="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
            if [[ "$DRY_RUN" -eq 1 ]]; then
                echo "  ${C_DIM}\$${C_RESET} curl -fsSL '$tarball_url' | tar -xz -C \$HOME/.local/bin gitleaks"
            else
                mkdir -p "$HOME/.local/bin"
                if curl -fsSL "$tarball_url" | tar -xz -C "$HOME/.local/bin" gitleaks 2>/dev/null; then
                    log_ok "installed gitleaks v${GITLEAKS_VERSION}"
                    INSTALLED=$((INSTALLED+1))
                else
                    log_err "gitleaks download from $tarball_url failed"
                    FAILED=$((FAILED+1))
                fi
            fi
        else
            log_warn "curl missing — cannot install gitleaks"
            FAILED=$((FAILED+1))
        fi
    fi
    # eslint + ts-unused-exports are npm globals on every OS
    install_npm_global_pkg eslint "eslint eslint-plugin-security"
    install_npm_global_pkg ts-unused-exports ts-unused-exports
fi

# -----------------------------------------------------------------------------
# Install: java
# -----------------------------------------------------------------------------
if stack_active java; then
    echo "${C_BLUE}== java (maven, spotbugs; find-sec-bugs is a SpotBugs plugin via -PfindSecBugs) ==${C_RESET}"
    if [[ "$OS" == "macos" ]]; then
        install_brew_pkg mvn maven
        install_brew_pkg spotbugs
    else
        # Linux: pip3 install --user has no maven; rely on curl tarball / system pkg manager pointer
        if check_tool mvn; then
            log_skip "mvn (already installed)"; SKIPPED=$((SKIPPED+1))
        else
            log_warn "mvn missing on Linux — install via your distro package manager (e.g. apt-get install -y maven default-jre). Skipping."
            FAILED=$((FAILED+1))
        fi
        if check_tool spotbugs; then
            log_skip "spotbugs (already installed)"; SKIPPED=$((SKIPPED+1))
        elif check_tool curl; then
            jar_url="https://github.com/spotbugs/spotbugs/releases/download/${SPOTBUGS_VERSION}/spotbugs-${SPOTBUGS_VERSION}.tgz"
            if [[ "$DRY_RUN" -eq 1 ]]; then
                echo "  ${C_DIM}\$${C_RESET} curl -fsSL '$jar_url' -o \$HOME/.local/share/spotbugs-${SPOTBUGS_VERSION}.tgz"
                echo "  ${C_DIM}\$${C_RESET} # then extract and symlink bin/spotbugs into \$HOME/.local/bin"
            else
                mkdir -p "$HOME/.local/share" "$HOME/.local/bin"
                arc="$HOME/.local/share/spotbugs-${SPOTBUGS_VERSION}.tgz"
                if curl -fsSL "$jar_url" -o "$arc" && tar -xzf "$arc" -C "$HOME/.local/share" \
                    && ln -sf "$HOME/.local/share/spotbugs-${SPOTBUGS_VERSION}/bin/spotbugs" "$HOME/.local/bin/spotbugs"; then
                    log_ok "installed spotbugs v${SPOTBUGS_VERSION}"
                    log_info "Ensure $HOME/.local/bin is on your PATH"
                    INSTALLED=$((INSTALLED+1))
                else
                    log_err "spotbugs download from $jar_url failed"
                    FAILED=$((FAILED+1))
                fi
            fi
        else
            log_warn "curl missing — cannot install spotbugs"
            FAILED=$((FAILED+1))
        fi
        log_info "find-sec-bugs ships as SpotBugs plugin — enable via Maven '-PfindSecBugs' profile, no separate install."
    fi
fi

# -----------------------------------------------------------------------------
# Install: python
# -----------------------------------------------------------------------------
if stack_active python; then
    echo "${C_BLUE}== python (bandit, pip-audit, vulture, pyright) ==${C_RESET}"
    install_pip_pkg bandit
    install_pip_pkg pip-audit
    install_pip_pkg vulture
    install_pip_pkg pyright
fi

# -----------------------------------------------------------------------------
# Install: ios
# -----------------------------------------------------------------------------
if stack_active ios; then
    echo "${C_BLUE}== ios (swiftlint) ==${C_RESET}"
    if [[ "$OS" == "macos" ]]; then
        install_brew_pkg swiftlint
    else
        log_warn "ios toolchain skipped: requires macOS (NOT_APPLICABLE_ON_OS)"
        NOT_APPLICABLE=$((NOT_APPLICABLE+1))
    fi
fi

# -----------------------------------------------------------------------------
# Install: android
# -----------------------------------------------------------------------------
if stack_active android; then
    echo "${C_BLUE}== android (detekt, ktlint) ==${C_RESET}"
    if [[ "$OS" == "macos" ]]; then
        install_brew_pkg detekt
        install_brew_pkg ktlint
    else
        detekt_url="https://github.com/detekt/detekt/releases/download/v${DETEKT_VERSION}/detekt"
        ktlint_url="https://github.com/pinterest/ktlint/releases/download/${KTLINT_VERSION}/ktlint"
        download_to_bin detekt "$detekt_url"
        download_to_bin ktlint "$ktlint_url"
    fi
fi

# -----------------------------------------------------------------------------
# Install: aws
# -----------------------------------------------------------------------------
if stack_active aws; then
    echo "${C_BLUE}== aws (tflint, tfsec, checkov, cfn-lint) ==${C_RESET}"
    if [[ "$OS" == "macos" ]]; then
        install_brew_pkg tflint
        install_brew_pkg tfsec
        install_brew_pkg checkov
        install_brew_pkg cfn-lint
    else
        install_pip_pkg checkov
        install_pip_pkg cfn-lint
        if check_tool tflint; then
            log_skip "tflint (already installed)"; SKIPPED=$((SKIPPED+1))
        elif check_tool curl && check_tool unzip; then
            zip_url="https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_amd64.zip"
            if [[ "$DRY_RUN" -eq 1 ]]; then
                echo "  ${C_DIM}\$${C_RESET} curl -fsSL '$zip_url' -o /tmp/tflint.zip && unzip -o /tmp/tflint.zip -d \$HOME/.local/bin"
            else
                mkdir -p "$HOME/.local/bin"
                if curl -fsSL "$zip_url" -o /tmp/tflint.zip && unzip -o /tmp/tflint.zip -d "$HOME/.local/bin" >/dev/null; then
                    log_ok "installed tflint v${TFLINT_VERSION}"
                    INSTALLED=$((INSTALLED+1))
                else
                    log_err "tflint install failed"
                    FAILED=$((FAILED+1))
                fi
            fi
        else
            log_warn "curl/unzip missing — cannot install tflint"
            FAILED=$((FAILED+1))
        fi
        if check_tool tfsec; then
            log_skip "tfsec (already installed)"; SKIPPED=$((SKIPPED+1))
        else
            tfsec_url="https://github.com/aquasecurity/tfsec/releases/download/v${TFSEC_VERSION}/tfsec-linux-amd64"
            download_to_bin tfsec "$tfsec_url"
        fi
    fi
fi

# -----------------------------------------------------------------------------
# Final report
# -----------------------------------------------------------------------------
echo ""
echo "${C_BLUE}===== DevForge runner install summary =====${C_RESET}"
echo "  INSTALLED:              $INSTALLED"
echo "  SKIPPED (already):      $SKIPPED"
echo "  FAILED:                 $FAILED"
echo "  NOT_APPLICABLE_ON_OS:   $NOT_APPLICABLE"
echo ""
if [[ "$FAILED" -gt 0 ]]; then
    log_err "One or more installs failed."
    exit 1
fi
log_ok "All requested installs succeeded (or already present)."
exit 0
