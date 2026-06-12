# devforge-flusher.ps1  -  PowerShell equivalent
# Hook: PostToolUse | Matcher: * | Timeout: async
# Purpose: Opportunistic telemetry flush. Cooldown 60s via sentinel.
# Non-blocking: failures are silent. Authoritative flush is Stop hook (sync).
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "devforge-flusher"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR

$lastFlushFile = Join-Path $HOME ".claude\.devforge-last-flush"
$cooldownSec   = 60

New-Item -ItemType Directory -Path (Join-Path $HOME ".claude") -Force | Out-Null 2>$null

$now  = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$last = 0
if (Test-Path $lastFlushFile) {
    try { $last = [long](Get-Content $lastFlushFile -Raw).Trim() } catch { $last = 0 }
}

# Cooldown check: skip if last flush was within cooldownSec
if ($last -gt 0 -and ($now - $last) -lt $cooldownSec) { exit 0 }

# Update sentinel BEFORE upload to debounce concurrent flushers (mirrors bash behaviour)
try { $now | Set-Content $lastFlushFile -NoNewline } catch {}

# Background telemetry upload — silent on failure.
# Priority: telemetry-upload.ps1 > telemetry-upload.py (with python3).
# Mirrors bash: source lib/telemetry-upload.sh && devforge_upload_logs &
try {
    $uploadPs1 = Join-Path $PLUGIN_ROOT "lib\telemetry-upload.ps1"
    $uploadPy  = Join-Path $PLUGIN_ROOT "lib\telemetry-upload.py"

    if (Test-Path $uploadPs1) {
        # Use the native PowerShell upload lib — equivalent to bash `source + call &`
        Start-Process powershell.exe `
            -ArgumentList "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", $uploadPs1 `
            -NoNewWindow `
            -WindowStyle Hidden `
            -ErrorAction SilentlyContinue
    } elseif ((Test-Path $uploadPy) -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
        # Fallback: Python upload script (pre-existing behaviour)
        Start-Process python3 `
            -ArgumentList $uploadPy `
            -NoNewWindow `
            -WindowStyle Hidden `
            -ErrorAction SilentlyContinue
    }
    # If neither script exists, exit silently — same as bash `source ... || exit 0`
} catch {}

exit 0
