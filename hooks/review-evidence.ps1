# review-evidence.ps1  -  PowerShell equivalent
# Hook: PreToolUse/PostToolUse | Matcher: Bash | Timeout: 15s
#
# Hardening (Task 16):
#   Q03-M1  guard CWD envelope (absolute + inside git worktree)
#   E01     skip on empty HEAD (just-init repo)
#   E03     advisory lock to serialize concurrent invocations on same SHA
#   E41     fail-CLOSED on collector failure on blocking trigger
#   E42     cache lookup honors fallback path via paths.resolve_evidence_path
#   E48     detect iCloud .icloud placeholder + invalid JSON -> recompute
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "review-evidence"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

Initialize-DevForgeSession 2>$null

# ── Runner auto-bootstrap v1.63.5 ──────────────────────────────────────────
# Ensure runner OSS security tools disponibili. Lancia in background con
# cooldown 1h. Non-blocking.
try {
    $runnerBootstrapPs1 = Join-Path $PLUGIN_ROOT "scripts\runner-bootstrap.ps1"
    $runnerBootstrapSh  = Join-Path $PLUGIN_ROOT "scripts\runner-bootstrap.sh"
    if (Test-Path $runnerBootstrapPs1) {
        Start-Process powershell -ArgumentList "-NonInteractive -File `"$runnerBootstrapPs1`"" -WindowStyle Hidden -ErrorAction SilentlyContinue
    } elseif (Test-Path $runnerBootstrapSh) {
        Start-Process bash -ArgumentList "`"$runnerBootstrapSh`"" -WindowStyle Hidden -ErrorAction SilentlyContinue
    }
} catch {}

# ── Bypass HARDENED ────────────────────────────────────────────────────────
$skipFile = Join-Path $HOME ".claude\.devforge-skip-evidence"
if (Test-Path $skipFile) {
    Remove-Item $skipFile -Force -ErrorAction SilentlyContinue
    Write-DevForgeLog -Event "evidence_bypass_legacy_removed" -Status "warn" `
        -Meta "{`"path`":`"$skipFile`",`"reason`":`"state_file_bypass_removed`"}" 2>$null
}
$sid = Get-DevForgeSid
if ($sid) {
    $bypassMarker = Join-Path $HOME ".claude\devforge-state\$sid\.bypass-evidence"
    if (Test-Path $bypassMarker) {
        Write-DevForgeLog -Event "evidence_bypass_used" -Status "info" `
            -Meta "{`"source`":`"session_marker`",`"sid`":`"$sid`"}" 2>$null
        Write-Output '{}'; exit 0
    }
}
if ($env:DEVFORGE_SKIP_EVIDENCE -eq "1") {
    Write-DevForgeLog -Event "evidence_bypass_used" -Status "info" -Meta "{`"source`":`"env_var`"}" 2>$null
    Write-Output '{}'; exit 0
}

$hookInput      = Read-StdinAll
$toolCommand    = Get-JsonField $hookInput "command"
if (-not $toolCommand) { $toolCommand = Get-JsonField $hookInput "tool_input.command" }
$hookEventName  = Get-JsonField $hookInput "hook_event_name"

# ── Q03-M1: guard ENVELOPE_CWD ─────────────────────────────────────────────
# Honor envelope cwd only if: absolute path, directory exists, inside git worktree.
# Guards against hostile envelopes creating .claude dirs in arbitrary locations.
$envelopeCwd = Get-JsonField $hookInput "cwd"
if ($envelopeCwd) {
    # Must be absolute (starts with drive letter or UNC on Windows, or / on bash-compat)
    $isAbsolute = [System.IO.Path]::IsPathRooted($envelopeCwd)
    if ($isAbsolute -and (Test-Path $envelopeCwd -PathType Container)) {
        # Verify it is inside a git worktree
        $gitCheckRc = 0
        try {
            git -C $envelopeCwd rev-parse --show-toplevel 2>$null | Out-Null
            $gitCheckRc = $LASTEXITCODE
        } catch { $gitCheckRc = 1 }
        if ($gitCheckRc -eq 0) {
            Set-Location $envelopeCwd
        }
    }
}

# ── iCloud Drive detection (E48 variant: ICLOUD_WARNING) ───────────────────
# Emitted as env var so the Python collector can embed it in verdict.warnings.
$icloudWarning = ""
if ($env:DEVFORGE_EVIDENCE_ICLOUD_WARN -ne "0") {
    $cwd = (Get-Location).Path
    if ($cwd -match 'Mobile Documents' -or $cwd -match 'iCloud Drive') {
        $icloudWarning = "repo in iCloudDocs — atomic rename fragile, potential .icloud placeholder issues"
    }
}
$env:DEVFORGE_EVIDENCE_ICLOUD_WARNING = $icloudWarning

# Determine trigger
$trigger     = "other"
$isBlocking  = $false
if ($hookEventName -eq "PreToolUse") {
    if ($toolCommand -match 'gh\s+pr\s+(create|edit)') { $trigger = "pre_pr"; $isBlocking = $true }
} elseif ($hookEventName -eq "PostToolUse") {
    if ($toolCommand -match 'git\s+(commit|push)') { $trigger = "post_commit" }
} else {
    $trigger = "skill_or_manual"
}

if ($trigger -eq "other") { Write-Output '{}'; exit 0 }

# ── Compute SHA ─────────────────────────────────────────────────────────────
# E01: git rev-parse --verify HEAD exits non-zero on just-init repo.
$sha = try { (git rev-parse --verify HEAD 2>$null).Trim() } catch { "" }
if ($sha -notmatch '^[0-9a-f]{40}$') { $sha = "" }
if (-not $sha) {
    Write-DevForgeLog -Event "evidence_skip_no_head" -Status "info" -Meta "{}" 2>$null
    @'
{"additional_context":"review-evidence: no HEAD commit yet, evidence skipped"}
'@
    exit 0
}

# Dirty tree check (exclude .claude/ — plugin output, never user source)
$dirty     = $false
$dirtyLines = try { (git status --porcelain 2>$null | Where-Object { $_ -notmatch '^\s*\.claude/?$|^\s*\.claude/' }) } catch { @() }
if ($dirtyLines) { $dirty = $true }

$evidenceDir  = ".claude\review-evidence"
$evidenceFile = Join-Path $evidenceDir "$sha.json"

# Q03-M1 (continuation): only mkdir AFTER we have a non-empty SHA and safe cwd.
New-Item -ItemType Directory -Path $evidenceDir -Force -ErrorAction SilentlyContinue | Out-Null

# ── E48: detect iCloud .icloud placeholder ─────────────────────────────────
# iCloud offloads files by replacing foo.json with .<name>.json.icloud stub.
# If the placeholder exists, force recompute by removing the evidence file.
$icloudPlaceholder = Join-Path $evidenceDir ".$sha.json.icloud"
if (Test-Path $icloudPlaceholder) {
    Write-DevForgeLog -Event "evidence_icloud_placeholder" -Status "warn" `
        -Meta "{`"sha`":`"$sha`"}" 2>$null
    Remove-Item $evidenceFile -Force -ErrorAction SilentlyContinue
}
# Also remove if existing evidence file is not valid JSON
if (Test-Path $evidenceFile) {
    $jsonValid = $true
    try { Get-Content $evidenceFile -Raw | ConvertFrom-Json -ErrorAction Stop | Out-Null } catch { $jsonValid = $false }
    if (-not $jsonValid) {
        Write-DevForgeLog -Event "evidence_invalid_json" -Status "warn" `
            -Meta "{`"sha`":`"$sha`"}" 2>$null
        Remove-Item $evidenceFile -Force -ErrorAction SilentlyContinue
    }
}

# ── E42: cache lookup honors fallback path ─────────────────────────────────
# atomic_io may have written to a fallback dir when iCloud was blocking primary.
# Use the python helper so PS1 and bash hook agree on where to look.
if (-not (Test-Path $evidenceFile)) {
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        try {
            $resolvedEvidence = (python3 -c @"
import sys
sys.path.insert(0, r'$PLUGIN_ROOT')
try:
    from lib.review_evidence.paths import resolve_evidence_path
    from pathlib import Path
    p = resolve_evidence_path('$sha', Path('.'))
    if p is not None:
        print(p)
except Exception:
    pass
"@ 2>$null)
            if ($resolvedEvidence -and (Test-Path $resolvedEvidence)) {
                $evidenceFile = $resolvedEvidence
            }
        } catch {}
    }
}

# ── Cache check ─────────────────────────────────────────────────────────────
$needsCompute = $true
if (-not $dirty -and (Test-Path $evidenceFile)) {
    try { Get-Content $evidenceFile -Raw | ConvertFrom-Json -ErrorAction Stop | Out-Null; $needsCompute = $false } catch { }
}

# ── E03: advisory lock — serialize concurrent writers on same SHA ───────────
$lockDir      = Join-Path $evidenceDir "$sha.lock"
$lockAcquired = $false

if ($needsCompute -and $trigger -ne "post_commit") {
    for ($i = 0; $i -lt 30; $i++) {
        try {
            New-Item -ItemType Directory -Path $lockDir -ErrorAction Stop | Out-Null
            $lockAcquired = $true
            break
        } catch {
            Start-Sleep -Seconds 1
            # Another writer may have finished while we waited
            if (-not $dirty -and (Test-Path $evidenceFile)) {
                try { Get-Content $evidenceFile -Raw | ConvertFrom-Json -ErrorAction Stop | Out-Null; $needsCompute = $false; break } catch {}
            }
        }
    }
    if (-not $lockAcquired -and $needsCompute) {
        Write-DevForgeLog -Event "evidence_lock_contention" -Status "warn" `
            -Meta "{`"sha`":`"$sha`",`"attempts`":30}" 2>$null
        if ($isBlocking) {
            @"
{"decision":"block","reason":"review-evidence: lock contention on $($sha.Substring(0,8)), cannot verify quality. Retry, or override: DEVFORGE_SKIP_EVIDENCE=1 (env var, session-scoped breakglass)"}
"@
        } else {
            @'
{"additional_context":"review-evidence: lock contention (non-blocking)"}
'@
        }
        exit 0
    }
}

if ($needsCompute) {
    $baseBranch = try { ((git symbolic-ref refs/remotes/origin/HEAD 2>$null) -replace '^refs/remotes/origin/', '').Trim() } catch { "main" }
    if (-not $baseBranch) { $baseBranch = "main" }

    # Allow tests/chaos to substitute the collector script (E41 chaos test)
    $collectorPath = if ($env:DEVFORGE_EVIDENCE_COLLECTOR_PATH) {
        $env:DEVFORGE_EVIDENCE_COLLECTOR_PATH
    } else {
        Join-Path $PLUGIN_ROOT "lib\review_evidence\collector.py"
    }
    $collectorAvailable = (Test-Path $collectorPath) -and (Get-Command python3 -ErrorAction SilentlyContinue)

    if ($trigger -eq "post_commit") {
        # Async: detach so we never block the commit hook chain.
        if ($collectorAvailable) {
            Start-Process python3 -ArgumentList "`"$collectorPath`" --sha $sha --base $baseBranch --dirty $([int]$dirty) --out `"$evidenceFile`"" -WindowStyle Hidden -ErrorAction SilentlyContinue
        }
        @"
{"additional_context":"review-evidence: async compute scheduled for $($sha.Substring(0,8))"}
"@
        exit 0
    }

    # Sync (pre_pr or skill_or_manual) — lock held; finally releases it
    try {
        if ($collectorAvailable) {
            $rc = 0
            try {
                python3 $collectorPath --sha $sha --base $baseBranch --dirty ([int]$dirty) --out $evidenceFile 2>$null
                $rc = $LASTEXITCODE
            } catch { $rc = 1 }

            if ($rc -ne 0) {
                # E41: collector failure (disk full, python crash, etc.)
                # On a blocking trigger we MUST fail-CLOSED.
                if ($isBlocking) {
                    $blockReason = if ($rc -eq 2) {
                        "disk full / quota exceeded — cannot persist evidence"
                    } else {
                        "collector exited $rc — cannot verify quality"
                    }
                    Write-DevForgeLog -Event "evidence_block_compute_failed" -Status "error" `
                        -Meta "{`"sha`":`"$sha`",`"rc`":$rc}" 2>$null
                    @"
{"decision":"block","reason":"review-evidence: $blockReason. Override: DEVFORGE_SKIP_EVIDENCE=1 (env var, session-scoped breakglass)"}
"@
                    exit 0
                }
                @"
{"additional_context":"review-evidence: compute failed (non-blocking, rc=$rc)"}
"@
                exit 0
            }

            # E42 post-compute: after compute the file may live in fallback dir.
            # Re-resolve so the rest of the hook reads from the right place.
            if (-not (Test-Path $evidenceFile)) {
                if (Get-Command python3 -ErrorAction SilentlyContinue) {
                    try {
                        $resolvedEvidence2 = (python3 -c @"
import sys
sys.path.insert(0, r'$PLUGIN_ROOT')
try:
    from lib.review_evidence.paths import resolve_evidence_path
    from pathlib import Path
    p = resolve_evidence_path('$sha', Path('.'))
    if p is not None:
        print(p)
except Exception:
    pass
"@ 2>$null)
                        if ($resolvedEvidence2 -and (Test-Path $resolvedEvidence2)) {
                            $evidenceFile = $resolvedEvidence2
                        }
                    } catch {}
                }
            }

        } else {
            # E41: collector unavailable — fail-CLOSED on blocking trigger
            if ($isBlocking) {
                Write-DevForgeLog -Event "evidence_block_compute_failed" -Status "error" `
                    -Meta "{`"sha`":`"$sha`",`"rc`":0}" 2>$null
                @'
{"decision":"block","reason":"review-evidence: Python collector non disponibile — cannot verify quality. Override: DEVFORGE_SKIP_EVIDENCE=1 (env var, session-scoped breakglass)"}
'@
                exit 0
            } else {
                Write-Output '{}'
                exit 0
            }
        }
    } finally {
        if ($lockAcquired) { Remove-Item $lockDir -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

# ── Read verdict ────────────────────────────────────────────────────────────
if (-not (Test-Path $evidenceFile)) {
    if ($isBlocking) {
        @"
{"decision":"block","reason":"review-evidence: no evidence file for $($sha.Substring(0,8)) after compute. Cannot verify quality. Override: DEVFORGE_SKIP_EVIDENCE=1 (env var, session-scoped breakglass)"}
"@
    } else { Write-Output '{}' }
    exit 0
}

# Final JSON sanity check before reading verdict
try {
    $evidence = Get-Content $evidenceFile -Raw | ConvertFrom-Json -ErrorAction Stop
} catch {
    if ($isBlocking) {
        @"
{"decision":"block","reason":"review-evidence: evidence file $evidenceFile is not valid JSON (likely iCloud placeholder). Override: DEVFORGE_SKIP_EVIDENCE=1 (env var, session-scoped breakglass)"}
"@
    } else {
        @'
{"additional_context":"review-evidence: evidence file unreadable (non-blocking)"}
'@
    }
    exit 0
}

# ── v2 verdict routing ──────────────────────────────────────────────────────
$decision         = if ($evidence.regression_verdict) { $evidence.regression_verdict.decision } else { "" }
$regressionReason = if ($evidence.regression_verdict) { $evidence.regression_verdict.reason }   else { "" }

switch ($decision) {
    "BLOCK_HARD_FLOOR" {
        $safeReason = Convert-ToDevForgeJson $regressionReason
        Write-DevForgeLog -Event "evidence_v2_block_hard_floor" -Status "warn" -Meta "{`"sha`":`"$sha`"}" 2>$null
        @"
{"decision":"block","reason":"review-evidence v2: hard floor breach  -  $safeReason. NOT overridable by reviewer. Admin BREAK-GLASS: commit msg 'BREAK-GLASS: <jira>' + 2 reviewer + post-mortem 48h."}
"@
        exit 0
    }
    "BLOCK_REGRESSION" {
        $safeReason = Convert-ToDevForgeJson $regressionReason
        # AUTO_FIX_TRIGGER: emit when auto-fix enabled (default) and no hard floor breaches and not a bot
        $autoSignal = ""
        if ($env:DEVFORGE_FIX_EVIDENCE_AUTO -ne "0") {
            $hardFloorCount = 0
            try {
                if ($evidence.regression_verdict.hard_floor_breaches) {
                    $hardFloorCount = @($evidence.regression_verdict.hard_floor_breaches).Count
                }
            } catch {}
            $isBot = $env:GITHUB_ACTOR -match 'dependabot\[bot\]|renovate\[bot\]|github-actions\[bot\]'
            if ($hardFloorCount -eq 0 -and -not $isBot) {
                $autoSignal = " AUTO_FIX_TRIGGER:/forge-fix-evidence:sha=$sha"
                Write-DevForgeLog -Event "evidence_auto_fix_trigger_emitted" -Status "info" `
                    -Meta "{`"sha`":`"$sha`"}" 2>$null
            } else {
                Write-DevForgeLog -Event "evidence_auto_fix_trigger_skipped" -Status "info" `
                    -Meta "{`"sha`":`"$sha`",`"hard_floor_count`":$hardFloorCount,`"is_bot`":$([int]([bool]$isBot))}" 2>$null
            }
        }
        Write-DevForgeLog -Event "evidence_v2_block_regression" -Status "warn" -Meta "{`"sha`":`"$sha`"}" 2>$null
        @"
{"decision":"block","reason":"review-evidence v2: regression block  -  $safeReason. Override: DEVFORGE_SKIP_EVIDENCE=1 (env var, session-scoped breakglass) (tracked, abuse 5/day).","additional_context":"review-evidence v2: BLOCK_REGRESSION $($sha.Substring(0,8))  -  $safeReason.$autoSignal"}
"@
        exit 0
    }
    "REVIEWER_HANDOFF" {
        @"
{"additional_context":"review-evidence v2: regression in warn zone  -  code-reviewer agent will gatekeep. $regressionReason"}
"@
        exit 0
    }
    "SEVERELY_DEGRADED" {
        $missing = if ($evidence.current_scores.missing_components) { $evidence.current_scores.missing_components -join "," } else { "unknown" }
        @"
{"additional_context":"review-evidence v2: SEVERELY_DEGRADED  -  DevForge runners parzialmente non disponibili: $missing. Hard floor SKIP."}
"@
        exit 0
    }
    "AUTO_APPROVE" {
        $score = if ($null -ne $evidence.current_scores.overall) { $evidence.current_scores.overall } else { "n/a" }
        @"
{"additional_context":"review-evidence v2: AUTO_APPROVE (overall=$score)."}
"@
        exit 0
    }
}

# ── v1 fallback ─────────────────────────────────────────────────────────────
$block   = if ($null -ne $evidence.verdict.block) { $evidence.verdict.block } else { $false }
$reasons = if ($evidence.verdict.block_reasons) { $evidence.verdict.block_reasons -join ", " } else { "" }

if ($isBlocking -and $block) {
    $safeReasons = Convert-ToDevForgeJson $reasons
    Write-DevForgeLog -Event "evidence_block" -Status "warn" `
        -Meta "{`"sha`":`"$sha`",`"reasons`":`"$safeReasons`"}" 2>$null
    @"
{"decision":"block","reason":"review-evidence: hard-block triggered. Reasons: $safeReasons. Evidence: $evidenceFile. Override: DEVFORGE_SKIP_EVIDENCE=1 (env var, session-scoped breakglass)"}
"@
    exit 0
}

# ── Advisory (always) ────────────────────────────────────────────────────────
$cov  = if ($null -ne $evidence.metrics.coverage.overall_pct) { $evidence.metrics.coverage.overall_pct } else { "n/a" }
$lint = if ($null -ne $evidence.metrics.lint.errors)          { $evidence.metrics.lint.errors }          else { 0 }
@"
{"additional_context":"review-evidence $($sha.Substring(0,8)): coverage=$cov%, lint_errors=$lint, block=$block. File: $evidenceFile"}
"@
exit 0
