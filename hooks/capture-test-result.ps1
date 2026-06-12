# capture-test-result.ps1  -  PowerShell equivalent
# Hook: PostToolUse | Matcher: Bash | Timeout: 10s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "capture-test-result"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$stateDir  = Join-Path $HOME ".claude"
$resultFile = Join-Path $stateDir ".devforge-last-test-result"

Initialize-DevForgeSession 2>$null

$hookInput = Read-StdinAll
$command  = Get-JsonField $hookInput "command"
if (-not $command) { $command = Get-JsonField $hookInput "tool_input.command" }

# Exit code derivation: cascade .exit_code // .tool_output.exit_code // .tool_response.exit_code // is_error
# Mirrors bash cascade: .exit_code // .tool_output.exit_code // .tool_response.exit_code // (is_error mapping)
$exitCode = ""
$stdout   = ""
try {
    $data = $hookInput | ConvertFrom-Json -ErrorAction Stop

    # Exit code cascade
    if ($null -ne $data.exit_code -and "$($data.exit_code)" -ne "") {
        $exitCode = "$($data.exit_code)"
    } elseif ($null -ne $data.tool_output -and $null -ne $data.tool_output.exit_code -and "$($data.tool_output.exit_code)" -ne "") {
        $exitCode = "$($data.tool_output.exit_code)"
    } elseif ($null -ne $data.tool_response -and $null -ne $data.tool_response.exit_code -and "$($data.tool_response.exit_code)" -ne "") {
        $exitCode = "$($data.tool_response.exit_code)"
    } else {
        # Derive from is_error (Claude Code real payload)
        $isError = $null
        if ($null -ne $data.tool_response) { $isError = $data.tool_response.is_error }
        if ($isError -eq $false) { $exitCode = "0" } elseif ($isError -eq $true) { $exitCode = "1" }
    }

    # Stdout cascade: .stdout // .tool_output.stdout // .tool_response.stdout // .tool_response.output
    if ($data.stdout) { $stdout = $data.stdout }
    elseif ($null -ne $data.tool_output -and $data.tool_output.stdout) { $stdout = $data.tool_output.stdout }
    elseif ($null -ne $data.tool_response -and $data.tool_response.stdout) { $stdout = $data.tool_response.stdout }
    elseif ($null -ne $data.tool_response -and $data.tool_response.output) { $stdout = $data.tool_response.output }
    if (-not $stdout) { $stdout = "" }
} catch { $stdout = "" }

# Only care about test commands — includes run-all.sh and run-all.ps1 (bonus)
if ($command -notmatch '(test|jest|vitest|pytest|mvn.*test|gradle.*test|npm.*test|yarn.*test|go test|cargo test|run-all\.sh|run-all\.ps1|\.spec\.|\.test\.)') {
    exit 0
}

# --- TDD State Machine ---
$sessionSkills = Get-DevForgeSessionSkills
$tddStateFile  = Join-Path $stateDir ".devforge-tdd-state"
$curPhase      = ""
$prevEpoch     = "0"

if ($sessionSkills -like "*siae-tdd*") {
    $curStateRaw = if (Test-Path $tddStateFile) { (Get-Content $tddStateFile -Raw).Trim().Split('|') } else { @() }
    $curPhase    = if ($curStateRaw.Count -gt 0) { $curStateRaw[0] } else { "" }
    $prevEpoch   = if ($curStateRaw.Count -gt 3) { $curStateRaw[3] } else { "0" }
    $nowSec      = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

    if ($exitCode -eq "0") {
        # Test PASS
        switch ($curPhase) {
            "INIT" {
                # INIT + PASS = test passed immediately → not TDD (test existed already)
                # Stay INIT — user needs to write a NEW failing test
                # (no write — state unchanged)
            }
            "RED" {
                # RED + PASS = transition to GREEN (implementation code made test pass)
                $curState2 = (Get-Content $tddStateFile -Raw).Trim().Split('|')
                $f2 = if ($curState2.Count -gt 1) { $curState2[1] } else { "unknown" }
                $f3 = if ($curState2.Count -gt 2) { $curState2[2] } else { "impl-passed" }
                "GREEN|$f2|$f3|$nowSec" | Set-Content $tddStateFile -NoNewline
            }
            "GREEN" {
                # GREEN + PASS = stay GREEN (refactor safe, tests still passing)
                # (no write — state unchanged)
            }
            "REFACTOR" {
                # REFACTOR + PASS = stay REFACTOR (refactor safe)
                # (no write — state unchanged)
            }
        }
    } else {
        # Test FAIL
        switch -Regex ($curPhase) {
            '^$|^NONE$|^INIT$' { "RED|unknown|test-confirmed|$nowSec" | Set-Content $tddStateFile -NoNewline }
            '^GREEN$'           { "RED|unknown|regression|$nowSec"     | Set-Content $tddStateFile -NoNewline }
            '^REFACTOR$'        { "RED|unknown|refactor-regression|$nowSec" | Set-Content $tddStateFile -NoNewline }
            '^RED$'             { } # RED + FAIL = expected, stay RED
        }
    }

    # Emit tdd_cycle on phase transition
    $newStateRaw = if (Test-Path $tddStateFile) { (Get-Content $tddStateFile -Raw).Trim().Split('|') } else { @() }
    $newPhase    = if ($newStateRaw.Count -gt 0) { $newStateRaw[0] } else { "" }
    $newReason   = if ($newStateRaw.Count -gt 2) { $newStateRaw[2] } else { "" }
    if ($curPhase -and $newPhase -and $newPhase -ne $curPhase) {
        $elapsed = 0
        if ($prevEpoch -match '^\d+$') { $elapsed = [math]::Max(0, $nowSec - [long]$prevEpoch) }
        $safeReason = Convert-ToDevForgeJson $newReason
        Write-DevForgeLog -Event "tdd_cycle" -Status "success" `
            -Meta "{`"from_phase`":`"$curPhase`",`"to_phase`":`"$newPhase`",`"elapsed_sec`":$elapsed,`"reason`":`"$safeReason`"}" 2>$null
    }
}

# Build summary
$nowTime = [DateTime]::UtcNow.ToString("HH:mm")
$status  = if ($exitCode -eq "0") { "PASS" } else { "FAIL (exit $exitCode)" }

$summaryLines = ""
if ($stdout) {
    $summaryLines = ($stdout -split "`n" | Where-Object { $_ -match '(passed|failed|error|Tests run|test suites|FAIL|OK|SUCCESS|assertions)' } | Select-Object -Last 5) -join "`n"
}
"$status at $nowTime  -  cmd: $command`n$summaryLines".Trim() | Set-Content $resultFile -Encoding UTF8

# Coverage extraction
$coverageFile = Join-Path $stateDir ".devforge-last-coverage"
$coveragePct  = ""

if ($stdout) {
    # Jest/Vitest: "All files | 85.71 | 100 | 75 | 85.71"
    if (-not $coveragePct) {
        if ($stdout -match 'All files\s*\|\s*(\d+(?:\.\d+)?)') { $coveragePct = $Matches[1] }
    }
    # Jest/Vitest/Istanbul: "Statements : 85.71%"
    if (-not $coveragePct) {
        if ($stdout -match 'Statements\s*:?\s*(\d+(?:\.\d+)?)%') { $coveragePct = $Matches[1] }
    }
    # pytest-cov: "TOTAL    150     30    80%"
    if (-not $coveragePct) {
        if ($stdout -match 'TOTAL\s+\d+\s+\d+\s+(\d+)%') { $coveragePct = $Matches[1] }
    }
    # Go: "coverage: 82.3% of statements"
    if (-not $coveragePct) {
        if ($stdout -match 'coverage:\s*(\d+(?:\.\d+)?)%') { $coveragePct = $Matches[1] }
    }
    # JaCoCo / generic: "Coverage: 75%" or "Total coverage: 75%"
    if (-not $coveragePct) {
        if ($stdout -match '[Cc]overage:?\s*(\d+(?:\.\d+)?)%') { $coveragePct = $Matches[1] }
    }
    # Vitest v8: table row "  85.71 |" — first column numeric value per row
    if (-not $coveragePct) {
        if ($stdout -match '(?m)^\s*(\d+(?:\.\d+)?)\s*\|') { $coveragePct = $Matches[1] }
    }
}

if ($coveragePct) {
    $ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    "$coveragePct|$ts|$command" | Set-Content $coverageFile -Encoding UTF8
}

# Telemetry
$trrStatus = if ($exitCode -eq "0") { "PASS" } else { "FAIL" }
$framework = switch -Regex ($command) {
    'pytest'       { "pytest"; break }
    'vitest'       { "vitest"; break }
    'jest'         { "jest"; break }
    'mvn'          { "maven"; break }
    'gradle'       { "gradle"; break }
    'go test'      { "go"; break }
    'cargo test'   { "cargo"; break }
    default        { "unknown" }
}
$covJson  = if ($coveragePct -match '^\d+(\.\d+)?$') { $coveragePct } else { "null" }
$exitJson = if ($exitCode -match '^\d+$') { $exitCode } else { "null" }
Write-DevForgeLog -Event "test_run_result" -Status "success" `
    -Meta "{`"status`":`"$trrStatus`",`"exit_code`":$exitJson,`"coverage_pct`":$covJson,`"framework`":`"$framework`"}" 2>$null

# bash exits with exit 0 (no final output to stdout)
exit 0
