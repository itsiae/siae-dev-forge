# session-start-tiered-advisor.ps1  -  PowerShell equivalent
# Hook: SessionStart | Matcher: startup|resume | async:true
param()
$ErrorActionPreference = 'SilentlyContinue'

$ROOT = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { (Get-Location).Path }
$MAP  = Join-Path $ROOT "docs\CODEBASE_MAP.md"

# Worker scriptblock — all slow work runs inside, with a 3s timeout
$workerScript = {
    param($ROOT, $MAP)

    if (-not (Test-Path $MAP)) {
        return '{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "Nessuna codebase map in docs/CODEBASE_MAP.md. Per generarla: /forge-map (o /forge-map --tiered per gerarchia)."}}'
    }

    # Parse last_mapped from frontmatter
    $lastMapped = ""
    $lines = Get-Content $MAP -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        if ($line -match '^last_mapped:\s*(.+)$') { $lastMapped = $Matches[1].Trim(); break }
    }
    if (-not $lastMapped) { return $null }

    # Compute age in days
    $ageDays = 0
    try {
        $mapDt = [DateTime]::Parse($lastMapped, [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::AssumeUniversal)
        $ageDays = [int]([DateTime]::UtcNow - $mapDt).TotalDays
    } catch { return $null }

    # Count commits since last_mapped (slow git call — inside the timeout job)
    $commits = 0
    try {
        $commitOut = (git -C $ROOT rev-list --count HEAD "--since=$lastMapped" 2>$null)
        if ($commitOut -match '^\d+$') { $commits = [int]$commitOut }
    } catch {}

    # Emit advisory if stale
    if ($ageDays -gt 14 -or $commits -ge 30) {
        $msg = "Codebase map stale: $ageDays giorni, $commits commit dall'ultimo mapping. Suggerito: /forge-map (--tiered per gerarchia)."
        return "{`"hookSpecificOutput`": {`"hookEventName`": `"SessionStart`", `"additionalContext`": `"$msg`"}}"
    }
    return $null
}

# Run worker with 3s timeout (mirrors bash subshell + polling 100ms x 30)
$job = Start-Job -ScriptBlock $workerScript -ArgumentList $ROOT, $MAP
$completed = Wait-Job -Job $job -Timeout 3

if ($completed) {
    $result = Receive-Job -Job $job -ErrorAction SilentlyContinue
    Remove-Job -Job $job -Force
    if ($result) { Write-Output $result }
} else {
    # Timeout: kill the job
    Remove-Job -Job $job -Force
}

exit 0
