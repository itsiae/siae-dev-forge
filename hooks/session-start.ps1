# session-start.ps1  -  PowerShell equivalent of hooks/session-start
# Hook: SessionStart | Matcher: startup|resume|clear|compact | async:false
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "session-start"

# Capture start time for duration measurement (mirrors START_NS in bash)
$startTime = [DateTimeOffset]::UtcNow

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR

Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$claudeDir = Join-Path $HOME ".claude"
if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null }

# Read stdin payload (needed for source field — must happen before any output)
$stdinPayload = Read-StdinAll
$sessionSource = Get-JsonField $stdinPayload "source"

# -- Session state setup -------------------------------------------------------
$sid = New-DevForgeSid
$sessionDir = Join-Path $HOME ".claude\devforge-state\$sid"
New-Item -ItemType Directory -Path "$sessionDir\outbox\acked" -Force | Out-Null
$env:DEVFORGE_SESSION_DIR = $sessionDir
$env:DEVFORGE_PINNED_SID  = $sid

# -- User identity -------------------------------------------------------------
$userRaw = ""
$userSource = "unknown"
try { $userRaw = (git config user.email 2>$null); if ($userRaw) { $userSource = "git-config-local" } } catch {}
if (-not $userRaw) {
    try { $userRaw = (git config --global user.email 2>$null); if ($userRaw) { $userSource = "git-config-global" } } catch {}
}
if (-not $userRaw) { $userRaw = $env:USERNAME; $userSource = "os-user" }
$userRaw = $userRaw.Trim()
$userCanonical = Invoke-DevForgeCanonicalizeUser $userRaw
$env:DEVFORGE_PINNED_USER = $userCanonical

# Resolve authenticated SSO identity (best-effort, empty on API-key/Bedrock auth)
$authResolved = Invoke-DevForgeResolveAuthIdentity 2>$null
if (-not $authResolved) { $authResolved = "|||" }
$authParts = $authResolved.Split('|')
$env:DEVFORGE_AUTH_EMAIL        = $authParts[0]
$env:DEVFORGE_AUTH_ACCOUNT_UUID = if ($authParts.Count -gt 1) { $authParts[1] } else { "" }

# Build identity bundle for user.json (mirrors IDENTITY_BUNDLE in bash)
$identityBundle = @{
    git_local_email  = (git config user.email 2>$null)
    git_global_email = (git config --global user.email 2>$null)
    os_user          = $env:USERNAME
    auth_email       = $env:DEVFORGE_AUTH_EMAIL
    auth_account_uuid = $env:DEVFORGE_AUTH_ACCOUNT_UUID
}

# Write user.json (pinned for entire session)
$userJson = Join-Path $sessionDir "user.json"
@{ raw = $userRaw; source = $userSource; canonical = $userCanonical; identity = $identityBundle } |
    ConvertTo-Json -Depth 5 | Set-Content $userJson -Encoding UTF8 2>$null

# Initialize counters
Set-Content (Join-Path $sessionDir "seq") "0" -NoNewline
Set-Content (Join-Path $HOME ".claude\.devforge-session-commits") "0" -NoNewline
Set-Content (Join-Path $HOME ".claude\.devforge-tool-counter") "0" -NoNewline
Set-Content (Join-Path $HOME ".claude\.devforge-message-counter") "0" -NoNewline

# -- (13) Token collector init --------------------------------------------------
# Mirrors: python3 "${PLUGIN_ROOT}/lib/token-collector.py" init 2>/dev/null || true
try {
    $tokenCollectorPy = Join-Path $PLUGIN_ROOT "lib\token-collector.py"
    if (Test-Path $tokenCollectorPy) {
        $pythonCmd = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } `
                     elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } `
                     else { $null }
        if ($pythonCmd) {
            & $pythonCmd $tokenCollectorPy "init" 2>$null | Out-Null
        }
    }
} catch {}

# -- (1) NTP clock skew check --------------------------------------------------
# Mirrors: curl -sfI -m 2 https://time.cloudflare.com/ + _devforge_check_clock_skew
# Silent failure: any network issue must not block session-start before JSON output.
$ntpEpoch = ""
try {
    $ntpResponse = Invoke-WebRequest -Uri "https://time.cloudflare.com/" -Method Head `
        -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop 2>$null
    $dateHeader = $ntpResponse.Headers["Date"]
    if ($dateHeader) {
        $ntpParsed = [System.DateTime]::Parse($dateHeader, [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::AdjustToUniversal)
        $ntpEpoch = [System.DateTimeOffset]::new($ntpParsed).ToUnixTimeSeconds().ToString()
    }
} catch {}

if ($ntpEpoch) {
    try {
        $localEpoch = [System.DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        $skewSec = [Math]::Abs($localEpoch - [long]$ntpEpoch)
        # If skew > 1h (3600s) flag it in session dir
        if ($skewSec -gt 3600) {
            $skewFile = Join-Path $sessionDir "force_received_at"
            Set-Content $skewFile "1" -NoNewline
            Write-DevForgeLog -Event "clock_skew_detected" -Status "warning" `
                -Meta "{`"skew_seconds`":$skewSec}" 2>$null
        }
    } catch {}
}

# -- Plugin version ------------------------------------------------------------
$pluginVersion = "unknown"
try {
    $pjson = Get-Content (Join-Path $PLUGIN_ROOT ".claude-plugin\plugin.json") -Raw | ConvertFrom-Json
    $pluginVersion = $pjson.version
} catch {}

# -- (4) Auto-install statusline -----------------------------------------------
# Mirrors: bash "${PLUGIN_ROOT}/statusline/install.sh" >/dev/null 2>&1 || true
# PS1 runs install.ps1 if present, silent fallback otherwise.
try {
    $statuslinePs1 = Join-Path $PLUGIN_ROOT "statusline\install.ps1"
    if (Test-Path $statuslinePs1) {
        & $statuslinePs1 2>$null | Out-Null
    }
} catch {}

# -- (5) Trailer hook install --------------------------------------------------
# Mirrors: bash "${PLUGIN_ROOT}/lib/install-trailer-hook.sh" >/dev/null 2>&1 || TRAILER_RC=$?
# PS1 runs lib/install-trailer-hook.ps1 if present, silent fallback otherwise.
$trailerRc = 0
try {
    $trailerPs1 = Join-Path $PLUGIN_ROOT "lib\install-trailer-hook.ps1"
    if (Test-Path $trailerPs1) {
        & $trailerPs1 2>$null | Out-Null
        $trailerRc = $LASTEXITCODE
        if ($trailerRc -eq 2) {
            Write-DevForgeLog -Event "trailer_hook_skipped_foreign" -Status "success" -Meta "{}" 2>$null
        }
    }
} catch {}

# -- setup-mcp-kibana (async) --------------------------------------------------
# Mirrors: bash "${PLUGIN_ROOT}/hooks/setup-mcp-kibana" >/dev/null 2>&1 &
try {
    $mcpKibanaPs1 = Join-Path $PLUGIN_ROOT "hooks\setup-mcp-kibana.ps1"
    if (Test-Path $mcpKibanaPs1) {
        Start-Job -ScriptBlock { param($p) & $p 2>$null | Out-Null } -ArgumentList $mcpKibanaPs1 | Out-Null
    }
} catch {}

# -- setup-mcp-sport (async) ---------------------------------------------------
# Mirrors: bash "${PLUGIN_ROOT}/hooks/setup-mcp-sport" >/dev/null 2>&1 &
try {
    $mcpSportPs1 = Join-Path $PLUGIN_ROOT "hooks\setup-mcp-sport.ps1"
    if (Test-Path $mcpSportPs1) {
        Start-Job -ScriptBlock { param($p) & $p 2>$null | Out-Null } -ArgumentList $mcpSportPs1 | Out-Null
    }
} catch {}

# -- (12) Banner ASCII ---------------------------------------------------------
# Mirrors: cat >&2 <<'BANNER' ... BANNER
# Uses [Console]::Error.WriteLine to write to stderr.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::Error.WriteLine("")
[Console]::Error.WriteLine("╔══════════════════════════════════════════════════════════════════╗")
[Console]::Error.WriteLine("║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║")
[Console]::Error.WriteLine("║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║")
[Console]::Error.WriteLine("║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║")
[Console]::Error.WriteLine("║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║")
[Console]::Error.WriteLine("║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║")
[Console]::Error.WriteLine("║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║")
[Console]::Error.WriteLine("║              🔨 DevForge · AI Competence Center                ║")
[Console]::Error.WriteLine("║         `"Il codice si forgia. Il developer cresce.`"            ║")
[Console]::Error.WriteLine("╚══════════════════════════════════════════════════════════════════╝")
[Console]::Error.WriteLine("")

# -- (2 + 3) Auto-update check with VERSION_STATUS emoji ----------------------
# Mirrors bash: gh release list --repo itsiae/siae-dev-forge + sort -V comparison
# VERSION_STATUS gets 🔄 or ✅ based on update availability.
$versionStatus = ""
if ((Get-Command gh -ErrorAction SilentlyContinue) -and $pluginVersion -ne "unknown" -and $env:DEVFORGE_SKIP_UPDATE -ne "1") {
    try {
        $latestTag = (gh release list --repo itsiae/siae-dev-forge --limit 1 --json tagName --jq '.[0].tagName' 2>$null)
        $latestVersion = $latestTag -replace '^v', ''

        # Validate semver format (optional suffix)
        if ($latestVersion -match '^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$') {
            # Compare versions using [System.Version] (strip any pre-release suffix for comparison)
            $currentBase = ($pluginVersion -replace '-.*$', '')
            $latestBase  = ($latestVersion -replace '-.*$', '')

            $currentSysVer = $null
            $latestSysVer  = $null
            try { $currentSysVer = [System.Version]$currentBase } catch {}
            try { $latestSysVer  = [System.Version]$latestBase  } catch {}

            if ($currentSysVer -and $latestSysVer) {
                if ($currentSysVer -lt $latestSysVer) {
                    $versionStatus = "🔄 Aggiornamento disponibile: v${pluginVersion} → v${latestVersion}. Esegui: claude plugin update siae-devforge@siae-devforge"
                    [Console]::Error.WriteLine("🔄 DevForge: aggiornamento disponibile v${pluginVersion} → v${latestVersion}")
                    [Console]::Error.WriteLine("   Aggiornamento in corso...")
                    # Only the update itself runs in background to not block session start
                    $bgScript = @"
`$marketplaceDir = Join-Path `$env:USERPROFILE '.claude\plugins\marketplaces\siae-devforge'
if (Test-Path (Join-Path `$marketplaceDir '.git')) {
    git -C `$marketplaceDir pull origin main --ff-only 2>`$null | Out-Null
}
Remove-Item (Join-Path `$env:USERPROFILE '.claude\plugins\cache\siae-devforge') -Recurse -Force 2>`$null
`$result = claude plugin update 'siae-devforge@siae-devforge' 2>&1
if (`$LASTEXITCODE -eq 0) {
    [Console]::Error.WriteLine('✅ DevForge aggiornato a v$latestVersion. Riavvia Claude Code per attivare.')
} else {
    [Console]::Error.WriteLine('⚠️  Aggiornamento fallito. Esegui manualmente: claude plugin update siae-devforge@siae-devforge')
}
"@
                    Start-Job -ScriptBlock ([scriptblock]::Create($bgScript)) | Out-Null
                } else {
                    $versionStatus = "✅ DevForge v${pluginVersion} — aggiornato"
                }
            }
        }
    } catch {}
}
# Fallback if gh is not available or version check failed
if (-not $versionStatus -and $pluginVersion -ne "unknown") {
    $versionStatus = "DevForge v$pluginVersion"
}

# -- Read using-devforge skill content ----------------------------------------
$usingDevforgeContent = ""
$udfPath = Join-Path $PLUGIN_ROOT "skills\using-devforge\SKILL.md"
if (Test-Path $udfPath) { $usingDevforgeContent = Get-Content $udfPath -Raw }

# -- Dynamic skill catalog via Node.js ----------------------------------------
$skillCatalog = ""
$skillsCoreJs = Join-Path $PLUGIN_ROOT "lib\skills-core.js"
if ((Get-Command node -ErrorAction SilentlyContinue) -and (Test-Path $skillsCoreJs)) {
    $skillCatalog = (node $skillsCoreJs $PLUGIN_ROOT 2>$null)
}
if (-not $skillCatalog) { $skillCatalog = "| (catalogo non disponibile  -  skills-core.js ha fallito) | | |" }

# -- (6) Global DevForge memory - skip symlinks --------------------------------
# Mirrors bash: [ -L "$mf" ] && continue
$globalMemorySection = ""
$globalMemoryDir = Join-Path $HOME ".claude\devforge-global-memory"
if (Test-Path $globalMemoryDir) {
    $parts = ""
    $count = 0
    Get-ChildItem "$globalMemoryDir\*.md" -ErrorAction SilentlyContinue | Select-Object -First 20 | ForEach-Object {
        # Skip symlinks (mirrors bash `[ -L "$mf" ] && continue`)
        if ($_.LinkType) { return }
        if ($_.Name -notmatch '^[Mm][Ee][Mm][Oo][Rr][Yy]\.md$') {
            $content = Get-Content $_.FullName -TotalCount 50 -Raw 2>$null
            if ($content) {
                $escaped = Convert-ToDevForgeJson $content
                $parts += "\n---\n$escaped"
                $count++
            }
        }
    }
    if ($parts) { $globalMemorySection = "\n\n**Global DevForge Memory (cross-project):**$parts" }
}

# -- (14) Branching compliance check -------------------------------------------
# Mirrors bash: gh repo view + gh pr list + violation reporting
$branchingSection = ""
if (Get-Command gh -ErrorAction SilentlyContinue) {
    try {
        $currentRepo = (gh repo view --json nameWithOwner -q '.nameWithOwner' 2>$null)
        if ($currentRepo) {
            $defaultBranch = (gh repo view --json defaultBranchRef -q '.defaultBranchRef.name' 2>$null)
            if (-not $defaultBranch) { $defaultBranch = "main" }
            $viols = 0
            $violDetails = ""

            if ($defaultBranch -ne "main") {
                $viols++
                $violDetails = "default branch is ``${defaultBranch}`` (atteso: ``main``)"
            } else {
                $badPrs = (gh pr list --base main --state open `
                    --json number,headRefName `
                    --jq '[.[] | select(.headRefName | test("^release/") | not) | "#\(.number) (\(.headRefName))"] | join(", ")' 2>$null)
                if ($badPrs) {
                    $viols++
                    $violDetails = "PR verso main da branch non-release: $badPrs"
                }
            }

            if ($viols -gt 0) {
                $branchingSummary = "⚠️ Branching compliance [${currentRepo}]: ${violDetails} — invoca /branching-strategy-check per dettagli."
                $branchingSummaryEscaped = Convert-ToDevForgeJson $branchingSummary
                $branchingSection = "\n\n$branchingSummaryEscaped"
            }
        }
    } catch {}
}

# -- Build session context -----------------------------------------------------
$udfEscaped      = Convert-ToDevForgeJson $usingDevforgeContent
$catalogEscaped  = Convert-ToDevForgeJson $skillCatalog
$versionEscaped  = Convert-ToDevForgeJson $versionStatus

$sessionContext = "<EXTREMELY_IMPORTANT>\nHai siae-devforge.\n\n$versionEscaped$branchingSection\n\n**Below is the content of your 'siae-devforge:using-devforge' meta-skill - the DevForge backbone for skill activation. For all other skills, use the 'Skill' tool:**\n\n$udfEscaped\n\n**Dynamic Skill Catalog (auto-generated):**\n\n$catalogEscaped$globalMemorySection\n</EXTREMELY_IMPORTANT>"

# -- Emit JSON output (standard DevForge additional_context) ------------------
@"
{
  "additional_context": "$sessionContext",
  "hookSpecificOutput": {
    "hookEventName": "SessionStart"
  }
}
"@

# -- Preserve or reset session skills based on source (mirrors bash session-start logic) --
# startup  -> fresh session, reset skills
# resume|clear|compact -> same logical session, preserve skills so gates stay valid
# unknown/empty -> default PRESERVE (resetting mid-work is the more damaging failure mode)
switch ($sessionSource) {
    "startup" {
        Set-Content (Join-Path $HOME ".claude\.devforge-session-skills") "" -NoNewline
    }
    { $_ -in @("resume", "clear", "compact") } {
        $safeSrc = Convert-ToDevForgeJson $sessionSource
        Write-DevForgeLog -Event "session_start_preserved_skills" -Status "success" `
            -Meta "{`"source`":`"$safeSrc`"}" 2>$null
    }
    default {
        Write-DevForgeLog -Event "session_start_preserved_skills" -Status "success" `
            -Meta "{`"source`":`"unknown`",`"reason`":`"default_preserve`"}" 2>$null
    }
}
Remove-Item (Join-Path $HOME ".claude\.devforge-tdd-state") -Force 2>$null
Remove-Item (Join-Path $HOME ".claude\.devforge-last-coverage") -Force 2>$null
Remove-Item (Join-Path $HOME ".claude\.devforge-retro-reminded") -Force 2>$null
Remove-Item (Join-Path $HOME ".claude\.devforge-skill-start") -Force 2>$null
Remove-Item (Join-Path $HOME ".claude\.devforge-session-end-guard") -Recurse -Force 2>$null

# Init last commit hash
$gitRoot = ""
try { $gitRoot = (git rev-parse --show-toplevel 2>$null).Trim() } catch {}
if ($gitRoot) {
    $repoKey = [System.Security.Cryptography.SHA1]::Create()
    $keyBytes = $repoKey.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($gitRoot))
    $keyHex = ([BitConverter]::ToString($keyBytes) -replace '-','').ToLower().Substring(0,16)
    $hashFile = Join-Path $HOME ".claude\.devforge-last-commit-hash-$keyHex"
    try { $head = (git rev-parse HEAD 2>$null).Trim(); Set-Content $hashFile $head -NoNewline } catch { Set-Content $hashFile "" -NoNewline }
}

# Save sid for other hooks
Set-Content (Join-Path $HOME ".claude\.devforge-sid") $sid -NoNewline

# -- (8) Session lock ----------------------------------------------------------
# Mirrors: SESSION_LOCK_FILE + CURRENT_PID=$$ + kill -0 check
$sessionLockFile = Join-Path $HOME ".claude\.devforge-session-lock"
$currentPid = $PID
if (Test-Path $sessionLockFile) {
    try {
        $oldPid = [int](Get-Content $sessionLockFile -Raw -ErrorAction SilentlyContinue).Trim()
        if ($oldPid -and $oldPid -ne $currentPid) {
            # Check if old session process is still running
            $oldProc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
            if ($oldProc) {
                Write-DevForgeLog -Event "session_conflict" -Status "warning" `
                    -Meta "{`"reason`":`"concurrent_session_detected`",`"old_pid`":$oldPid,`"new_pid`":$currentPid}" 2>$null
            }
        }
    } catch {}
}
Set-Content $sessionLockFile $currentPid.ToString() -NoNewline

# -- (7) PR merge detection ----------------------------------------------------
# Mirrors bash: gh pr list --state merged --author "@me" + jq + devforge_log
if ((Get-Command gh -ErrorAction SilentlyContinue) -and (Get-Command jq -ErrorAction SilentlyContinue)) {
    try {
        $ghRepo = ""
        try {
            $remoteUrl = (git remote get-url origin 2>$null).Trim()
            if ($remoteUrl -match '[/:]([^/:]+/[^/]+?)(?:\.git)?$') {
                $ghRepo = $Matches[1]
            }
        } catch {}

        if ($ghRepo) {
            $since24h = [System.DateTimeOffset]::UtcNow.AddHours(-24).ToUnixTimeSeconds()
            $mergedPrsJson = (gh pr list --repo $ghRepo --state merged --author "@me" `
                --json number,mergedAt,createdAt,reviews `
                --jq "[.[] | select((.mergedAt | fromdateiso8601) > $since24h)]" 2>$null)

            if ($mergedPrsJson -and $mergedPrsJson -ne "[]") {
                $seenFile = Join-Path $HOME ".claude\.devforge-seen-pr-merges"
                if (-not (Test-Path $seenFile)) { New-Item -ItemType File -Path $seenFile -Force | Out-Null }
                $seenContent = Get-Content $seenFile -Raw -ErrorAction SilentlyContinue

                try {
                    $mergedPrs = $mergedPrsJson | ConvertFrom-Json
                    foreach ($pr in $mergedPrs) {
                        $prNumber = $pr.number
                        $prKey = "${ghRepo}#${prNumber}"
                        if ($seenContent -and $seenContent.Contains($prKey)) { continue }

                        $createdAt = $pr.createdAt
                        $mergedAt  = $pr.mergedAt
                        $reviewersCount = 0
                        try {
                            $reviewerLogins = $pr.reviews | ForEach-Object { $_.author.login } | Sort-Object -Unique
                            $reviewersCount = @($reviewerLogins).Count
                        } catch {}

                        $reviewCycleHours = "0"
                        if ($createdAt -and $mergedAt) {
                            try {
                                $createdEpoch = [System.DateTimeOffset]::Parse($createdAt).ToUnixTimeSeconds()
                                $mergedEpoch  = [System.DateTimeOffset]::Parse($mergedAt).ToUnixTimeSeconds()
                                $deltaSeconds = $mergedEpoch - $createdEpoch
                                $reviewCycleHours = [Math]::Round($deltaSeconds / 3600.0, 1).ToString([System.Globalization.CultureInfo]::InvariantCulture)
                            } catch {}
                        }

                        Write-DevForgeLog -Event "pr_merged" -Status "success" `
                            -Meta "{`"pr_number`":$prNumber,`"review_cycle_hours`":$reviewCycleHours,`"reviewers_count`":$reviewersCount}" 2>$null

                        Add-Content $seenFile $prKey -Encoding UTF8

                        # Trim seen file to last 200 lines
                        $lines = Get-Content $seenFile -ErrorAction SilentlyContinue
                        if ($lines -and $lines.Count -gt 200) {
                            $trimmed = $lines | Select-Object -Last 200
                            Set-Content $seenFile $trimmed -Encoding UTF8
                        }
                    }
                } catch {}
            }
        }
    } catch {}
}

# -- (10) Stale sentinel cleanup (> 24h) ---------------------------------------
# Mirrors bash: for sentinel in .devforge-active-*; stat mtime; rm if > 24h
$staleAgeSec = 86400
$nowDt = Get-Date
try {
    Get-ChildItem -Path (Get-Location) -Filter ".devforge-active-*" -ErrorAction SilentlyContinue | ForEach-Object {
        $ageSec = ($nowDt - $_.LastWriteTime).TotalSeconds
        if ($ageSec -gt $staleAgeSec) {
            $safeSentinel = Convert-ToDevForgeJson $_.Name
            $ageHours = [Math]::Floor($ageSec / 3600)
            Write-DevForgeLog -Event "session_start_cleanup" -Status "info" `
                -Meta "{`"file`":`"$safeSentinel`",`"age_hours`":$ageHours}" 2>$null
            Remove-Item $_.FullName -Force 2>$null
        }
    }
} catch {}

# -- (9) Review-evidence cleanup (> 7 days) ------------------------------------
# Mirrors bash: find .claude/review-evidence -mtime +7 -delete
# Also cleans lock dirs > 1h and iCloud placeholders.
$reviewEvidenceLocal = Join-Path (Get-Location) ".claude\review-evidence"
if (Test-Path $reviewEvidenceLocal) {
    try {
        # Clean stale JSON files > 7 days
        Get-ChildItem -Path $reviewEvidenceLocal -Filter "*.json" -MaxDepth 1 -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt $nowDt.AddDays(-7) } |
            ForEach-Object { Remove-Item $_.FullName -Force 2>$null }

        # Clean orphaned lock dirs > 1h
        Get-ChildItem -Path $reviewEvidenceLocal -Filter "*.lock" -Directory -MaxDepth 1 -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt $nowDt.AddHours(-1) } |
            ForEach-Object { Remove-Item $_.FullName -Recurse -Force 2>$null }

        # Clean iCloud placeholders > 7 days
        Get-ChildItem -Path $reviewEvidenceLocal -Filter ".*.json.icloud" -MaxDepth 1 -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt $nowDt.AddDays(-7) } |
            ForEach-Object { Remove-Item $_.FullName -Force 2>$null }
    } catch {}
}

$reviewEvidenceFallback = Join-Path $HOME ".claude\review-evidence-fallback"
if (Test-Path $reviewEvidenceFallback) {
    try {
        Get-ChildItem -Path $reviewEvidenceFallback -Filter "*.json" -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName.Split([IO.Path]::DirectorySeparatorChar).Count -le ($reviewEvidenceFallback.Split([IO.Path]::DirectorySeparatorChar).Count + 2) } |
            Where-Object { $_.LastWriteTime -lt $nowDt.AddDays(-7) } |
            ForEach-Object { Remove-Item $_.FullName -Force 2>$null }
    } catch {}
}

# -- (11) Session state dir cleanup (> 48h without pending outbox) -------------
# Mirrors bash: for session_dir in ~/.claude/devforge-state/*/; check age + pending
$stateRootDir = Join-Path $HOME ".claude\devforge-state"
if (Test-Path $stateRootDir) {
    try {
        Get-ChildItem -Path $stateRootDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $dirAge = ($nowDt - $_.LastWriteTime).TotalSeconds
            if ($dirAge -lt 172800) { return }  # < 48h, skip

            $outboxDir = Join-Path $_.FullName "outbox"
            $pendingCount = 0
            if (Test-Path $outboxDir) {
                $pendingCount = @(Get-ChildItem -Path $outboxDir -Filter "*.jsonl" -ErrorAction SilentlyContinue |
                    Where-Object { $_.FullName -notlike "*\acked\*" }).Count
            }
            if ($pendingCount -gt 0) { return }  # has pending outbox, preserve

            Remove-Item $_.FullName -Recurse -Force 2>$null
        }
    } catch {}
}

# -- Log session_start with duration (mirrors devforge_log_timed) -------------
$safePwd     = Convert-ToDevForgeJson (Get-Location).Path
$safeVer     = Convert-ToDevForgeJson $pluginVersion
$durationMs  = [long]([DateTimeOffset]::UtcNow - $startTime).TotalMilliseconds
Write-DevForgeLog -Event "session_start" -Status "success" -DurationMs $durationMs `
    -Meta "{`"project_dir`":`"$safePwd`",`"plugin_version`":`"$safeVer`"}" 2>$null

# Save session start timestamp for duration calculation in stop-gate
$startNs = $startTime.ToUnixTimeMilliseconds() * 1000000
Set-Content (Join-Path $HOME ".claude\.devforge-session-start-ns") $startNs.ToString() -NoNewline
