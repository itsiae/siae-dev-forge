# install-trailer-hook.ps1  -  DevForge installer per il prepare-commit-msg hook (Windows/PS5.1)
# Stampa "DevForge-Author: <sso-email>" in ogni commit in modo che l'autore autenticato
# sopravviva al mirror GitLab->GitHub, anche senza telemetria.
#
# Idempotente, zero-harm (non sovrascrive hook altrui), best-effort.
# Invocato da hooks/session-start.ps1. Opt-out: DEVFORGE_SKIP_TRAILER_HOOK=1.
#
# Return codes: 0 = installato/aggiornato/non-applicabile; 2 = skippato (hook di terzi presente)
param()
$ErrorActionPreference = 'SilentlyContinue'

if ($env:DEVFORGE_SKIP_TRAILER_HOOK -eq "1") { exit 0 }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { exit 0 }

# Deve essere dentro un repo git
$gitDir = (git rev-parse --git-dir 2>$null)
if (-not $gitDir) { exit 0 }

$hooksDir = (git rev-parse --git-path hooks 2>$null)
if (-not $hooksDir) { exit 0 }
$hooksDir = $hooksDir.Trim()
if (-not $hooksDir) { exit 0 }

try { New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null } catch { exit 0 }

$target = Join-Path $hooksDir "prepare-commit-msg"
$marker = "# DEVFORGE-TRAILER-HOOK v1"

# Zero-harm: se esiste un prepare-commit-msg senza il nostro marker -> hook di terzi, skip
if (Test-Path $target) {
    $content = Get-Content $target -Raw -ErrorAction SilentlyContinue
    if ($content -and -not ($content -match [regex]::Escape($marker))) {
        exit 2
    }
}

# Recupera email SSO da ~/.claude.json (stesso metodo del bash)
function Get-DevForgeEmail {
    $cjPath = if ($env:DEVFORGE_CLAUDE_JSON) { $env:DEVFORGE_CLAUDE_JSON } `
        else { Join-Path $HOME ".claude.json" }
    if (-not (Test-Path $cjPath)) { return "" }
    if (-not (Get-Command python3 -ErrorAction SilentlyContinue)) { return "" }
    $email = (python3 -c @"
import json,sys
try:
    d=json.load(open(r'$($cjPath -replace "'","\'")'))
    acc=d.get('oauthAccount') or {}
    print(acc.get('emailAddress','') or '')
except: print('')
"@ 2>$null)
    if ($email) { return $email.Trim().Trim('"') }
    return ""
}

# Scrivi (o aggiorna) il hook bash — Git for Windows lo esegue tramite la propria sh.
# Il contenuto è identico alla versione bash (le variabili $1, ${EMAIL}, ecc. sono
# letterali nel file, non vengono espanse ora in PS).
$hookContent = @'
#!/usr/bin/env bash
# DEVFORGE-TRAILER-HOOK v1
# Stamps "DevForge-Author: <sso-email>" so the authenticated author survives the
# GitLab->GitHub mirror, even outside telemetry. Best-effort; NEVER blocks a commit.
set +e
MSG_FILE="$1"; SRC="${2:-}"
# No single meaningful author for merge/squash commits.
case "$SRC" in merge|squash) exit 0 ;; esac
# Resolve authenticated SSO email from Claude Code's local oauth account (best-effort).
CJ="${DEVFORGE_CLAUDE_JSON:-${HOME}/.claude.json}"
EMAIL=""
if [ -f "$CJ" ] && command -v python3 >/dev/null 2>&1; then
    EMAIL=$(python3 -c "import json,sys;print((json.load(open(sys.argv[1])).get('oauthAccount') or {}).get('emailAddress','') or '')" "$CJ" 2>/dev/null)
fi
EMAIL=$(printf '%s' "$EMAIL" | tr -d '\n\r"')
[ -z "$EMAIL" ] && exit 0
[ -f "$MSG_FILE" ] || exit 0
command -v git >/dev/null 2>&1 || exit 0
# --in-place: on failure, the message file is left untouched (no data loss).
# --if-exists doNothing: idempotent per-token (amend/re-run never duplicate).
git interpret-trailers --in-place --if-exists doNothing \
    --trailer "DevForge-Author: ${EMAIL}" "$MSG_FILE" 2>/dev/null
exit 0
'@

try {
    # Scrivi con LF (Unix line endings) perché git-bash legge il file con sh
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    $hookLf    = $hookContent -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($target, $hookLf, $utf8NoBom)
} catch {
    exit 0
}

exit 0
