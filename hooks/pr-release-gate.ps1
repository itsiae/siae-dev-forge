# pr-release-gate.ps1  -  PowerShell equivalent
# Hook: PostToolUse | Matcher: Bash | Timeout: 30s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "pr-release-gate"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

# Skip if disabled
$skipFile = Join-Path $HOME ".claude\.devforge-skip-release-risk"
if ((Test-Path $skipFile) -or $env:DEVFORGE_RELEASE_RISK_DISABLED -eq "1") { exit 0 }

$hookInput   = Read-StdinAll
$toolCommand = Get-JsonField $hookInput "command"
if (-not $toolCommand) { $toolCommand = Get-JsonField $hookInput "tool_input.command" }

# Only on gh pr create --base main
if ($toolCommand -notmatch 'gh pr create.+--base[= ]main') { exit 0 }

$currentBranch = try { (git branch --show-current 2>$null).Trim() } catch { "" }
if ($currentBranch -notmatch '^release/') { exit 0 }

$repoRoot = try { (git rev-parse --show-toplevel 2>$null).Trim() } catch { (Get-Location).Path }
$service  = Split-Path $repoRoot -Leaf

# Get PR number
$prNumber = ""
if (Get-Command gh -ErrorAction SilentlyContinue) {
    try { $prNumber = (gh pr list --head $currentBranch --base main --json number --jq '.[0].number' 2>$null).Trim() } catch {}
}

# Generate diff files in temp dir (nomi univoci per evitare collisioni tra PR concorrenti)
$tmpBase         = [System.IO.Path]::GetTempFileName()
Remove-Item $tmpBase -Force -ErrorAction SilentlyContinue
$diffFilesPath   = $tmpBase + "-devforge-diff-files.txt"
$diffContentPath = $tmpBase + "-devforge-diff-content.txt"

try {
    git fetch origin main --quiet 2>$null | Out-Null
} catch {}

try {
    $diffFiles   = (git diff "origin/main...origin/$currentBranch" --name-only 2>$null)
    $diffContent = (git diff "origin/main...origin/$currentBranch" 2>$null)
    if ($null -eq $diffFiles)   { $diffFiles   = "" }
    if ($null -eq $diffContent) { $diffContent = "" }
    # Avoid Out-String trailing newline: join array with newline explicitly
    ($diffFiles   -join "`n") | Set-Content $diffFilesPath   -Encoding UTF8
    ($diffContent -join "`n") | Set-Content $diffContentPath -Encoding UTF8
} catch {
    "" | Set-Content $diffFilesPath   -Encoding UTF8
    "" | Set-Content $diffContentPath -Encoding UTF8
}

# ── Invoke Python CLI with timeout (25s, matching bash behaviour) ───────────
# Primary: python3 -m lib.release_risk assess (more robust, matches bash)
# Fallback: direct path lib\release_risk\__main__.py
$assessOutput = ""
$collectorAvailable = $false

if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $moduleCheckRc = 0
    try {
        python3 -c "import lib.release_risk" 2>$null | Out-Null
        $moduleCheckRc = $LASTEXITCODE
    } catch { $moduleCheckRc = 1 }

    if ($moduleCheckRc -eq 0) {
        $collectorAvailable = $true
    } else {
        $fallbackPath = Join-Path $PLUGIN_ROOT "lib\release_risk\__main__.py"
        if (Test-Path $fallbackPath) { $collectorAvailable = $true }
    }
}

if ($collectorAvailable) {
    try {
        # Run with 25s timeout via Start-Job (mirrors bash `timeout 25 python3 -m lib.release_risk assess`)
        $job = Start-Job -ScriptBlock {
            param($repoRoot, $branch, $service, $diffFilesPath, $diffContentPath, $pluginRoot, $moduleCheckRc, $fallbackPath)
            Set-Location $repoRoot
            if ($moduleCheckRc -eq 0) {
                python3 -m lib.release_risk assess `
                    --repo-root $repoRoot --branch $branch --service $service `
                    --diff-files $diffFilesPath --diff-content $diffContentPath `
                    --trigger pr-open 2>$null
            } else {
                python3 $fallbackPath assess `
                    --repo-root $repoRoot --branch $branch --service $service `
                    --diff-files $diffFilesPath --diff-content $diffContentPath `
                    --trigger pr-open 2>$null
            }
        } -ArgumentList $repoRoot, $currentBranch, $service, $diffFilesPath, $diffContentPath, $PLUGIN_ROOT, $moduleCheckRc, (Join-Path $PLUGIN_ROOT "lib\release_risk\__main__.py")

        $completed = Wait-Job $job -Timeout 25
        if ($completed) {
            $assessOutput = Receive-Job $job 2>$null
        } else {
            Stop-Job $job -ErrorAction SilentlyContinue
            # Timeout: emit advisory warning, no block (fail-open)
            Remove-Job $job -Force -ErrorAction SilentlyContinue
            Remove-Item $diffFilesPath, $diffContentPath -Force -ErrorAction SilentlyContinue
            @'
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"⚠️ [siae-release-risk] CLI timeout o errore. Run /forge-release-risk manualmente."}}
'@
            exit 0
        }
        Remove-Job $job -Force -ErrorAction SilentlyContinue
    } catch {
        $assessOutput = ""
    }
}

# Cleanup temp files guaranteed anche su eccezione (mirrors bash: trap 'rm -rf $TMPDIR' EXIT)
try {} finally {
    Remove-Item $diffFilesPath, $diffContentPath -Force -ErrorAction SilentlyContinue
}

if ($assessOutput) {
    $lastLine = ($assessOutput -split "`n" | Select-Object -Last 1).Trim()
    try {
        $parsed   = $lastLine | ConvertFrom-Json -ErrorAction Stop
        $level    = if ($parsed.level)       { $parsed.level }       else { "UNKNOWN" }
        $outPath  = if ($parsed.output_path) { $parsed.output_path } else { "" }
        $diffHash = if ($parsed.diff_hash)   { $parsed.diff_hash }   else { "" }
        $cached   = if ($parsed.cached)      { $parsed.cached }      else { $false }

        if ($prNumber -and $diffHash -and (Get-Command gh -ErrorAction SilentlyContinue)) {
            try {
                $repoFull = (gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>$null).Trim()
                if ($repoFull) {
                    $existing = (gh api "repos/$repoFull/issues/$prNumber/comments" --jq '.[].body' 2>$null | Select-String "release-risk:$diffHash")
                    if (-not $existing -and $outPath -and (Test-Path $outPath)) {
                        gh pr comment $prNumber --body-file $outPath 2>$null | Out-Null
                    }
                }
            } catch {}
        }
        @"
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"🔨 [siae-release-risk] Scorecard posted to PR #$prNumber. Level: $level. Output: $outPath. Cached: $cached."}}
"@
    } catch {
    }
}
exit 0
