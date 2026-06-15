# DevForge-Helpers.psm1  -  PowerShell equivalent of logger.sh + task-id.sh + helpers
# Loaded via `Import-Module` by every hook .ps1 file.

$DEVFORGE_LOG_FILE = if ($env:DEVFORGE_LOG_FILE) { $env:DEVFORGE_LOG_FILE } else { Join-Path $HOME ".claude\devforge-activity.jsonl" }
$DEVFORGE_SID_FILE = Join-Path $HOME ".claude\.devforge-session-id"

# --- JSON string escaping ---------------------------------------------------
function Convert-ToDevForgeJson {
    param([string]$s)
    $s = $s -replace '\\', '\\'
    $s = $s -replace '"',  '\"'
    $s = $s -replace "`n", '\n'
    $s = $s -replace "`r", '\r'
    $s = $s -replace "`t", '\t'
    $s = [System.Text.RegularExpressions.Regex]::Replace($s, '[\x00-\x08\x0B\x0C\x0E-\x1F]', '')
    return $s
}

# --- Disk gate (mirrors _devforge_disk_gate) --------------------------------
function Get-DevForgeFreeKb {
    $dir = if ($env:DEVFORGE_SESSION_DIR) { $env:DEVFORGE_SESSION_DIR } else { Join-Path $HOME ".claude" }
    try {
        $qualifier = Split-Path $dir -Qualifier
        $driveName = $qualifier.TrimEnd(':')
        $drive = Get-PSDrive -Name $driveName -ErrorAction SilentlyContinue
        if ($drive -and $drive.Free -ne $null) { return [long]($drive.Free / 1024) }
    } catch {}
    return 999999999
}

function Test-DevForgeDiskGate {
    $freeKb = Get-DevForgeFreeKb
    $minKb = 102400  # 100MB
    if ($freeKb -lt $minKb) {
        $recoveryFile = Join-Path $HOME ".claude\.devforge-disk-full-events.tmp"
        $recoveryDir = Split-Path $recoveryFile
        if (-not (Test-Path $recoveryDir)) { New-Item -ItemType Directory -Path $recoveryDir -Force | Out-Null }
        $ts = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
        Add-Content -Path $recoveryFile -Value "${ts}|free_kb=${freeKb}" -Encoding UTF8
        return $false
    }
    return $true
}

# --- Log rotation (mirrors _devforge_check_rotation) ------------------------
# Cap totale 50MB su activity.jsonl + archived. Elimina solo archived
# completamente consumati dal batcher (cursor >= file_size).
function Invoke-DevForgeCheckRotation {
    $capBytes = 52428800  # 50MB
    if (-not $DEVFORGE_LOG_FILE) { return }
    $dir  = Split-Path $DEVFORGE_LOG_FILE
    $base = [System.IO.Path]::GetFileNameWithoutExtension($DEVFORGE_LOG_FILE)

    $total = [long]0
    if (Test-Path $DEVFORGE_LOG_FILE) { $total += (Get-Item $DEVFORGE_LOG_FILE).Length }
    $archived = Get-ChildItem "$dir\${base}-*.archived.jsonl" -ErrorAction SilentlyContinue |
                Sort-Object Name
    foreach ($f in $archived) { $total += $f.Length }
    if ($total -le $capBytes) { return }

    $sessionDir = if ($env:DEVFORGE_SESSION_DIR) { $env:DEVFORGE_SESSION_DIR } else { $dir }
    $outbox = Join-Path $sessionDir "outbox"

    foreach ($a in $archived) {
        if ($total -le $capBytes) { break }
        $cursorFile = Join-Path $outbox ".cursor-$($a.Name)"
        $cursor = [long]0
        if (Test-Path $cursorFile) {
            try { $cursor = [long](Get-Content $cursorFile -Raw -ErrorAction SilentlyContinue).Trim() } catch {}
        }
        $sz = $a.Length
        if ($cursor -ge $sz -and $sz -gt 0) {
            Remove-Item $a.FullName -Force -ErrorAction SilentlyContinue
            Remove-Item $cursorFile -Force -ErrorAction SilentlyContinue
            $total -= $sz
        }
    }
}

# --- Session ID -------------------------------------------------------------
function Get-DevForgeSid {
    if ($env:DEVFORGE_PINNED_SID) { return $env:DEVFORGE_PINNED_SID }
    if (Test-Path $DEVFORGE_SID_FILE) { return (Get-Content $DEVFORGE_SID_FILE -Raw).Trim() }
    return New-DevForgeSid
}

function New-DevForgeSid {
    $ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds().ToString()
    $sha = [System.Security.Cryptography.SHA1]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($ts)
    $hash = $sha.ComputeHash($bytes)
    $sid = ([BitConverter]::ToString($hash) -replace '-', '').ToLower().Substring(0, 8)
    $claudeDir = Split-Path $DEVFORGE_SID_FILE
    if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null }
    Set-Content -Path $DEVFORGE_SID_FILE -Value $sid -NoNewline
    return $sid
}

# --- Auth identity (reads oauthAccount from ~/.claude.json) -----------------
function Invoke-DevForgeResolveAuthIdentity {
    $claudeJson = Join-Path $HOME ".claude.json"
    if (-not (Test-Path $claudeJson)) { return "|||" }
    if (-not (Get-Command python3 -ErrorAction SilentlyContinue)) { return "|||" }
    $py = @'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    o = d.get('oauthAccount') or {}
    vals = [str(o.get('emailAddress','') or ''), str(o.get('accountUuid','') or ''),
            str(o.get('organizationUuid','') or ''), str(o.get('organizationName','') or '')]
    vals = [v.replace('|',' ').replace('\n',' ').replace('\r',' ').replace('"',' ') for v in vals]
    sys.stdout.write('|'.join(vals))
except Exception:
    sys.stdout.write('|||')
'@
    $result = python3 -c $py $claudeJson 2>$null
    return if ($result) { $result } else { "|||" }
}

# --- Session init ------------------------------------------------------------
function Initialize-DevForgeSession {
    $sid = Get-DevForgeSid
    $env:DEVFORGE_PINNED_SID = $sid
    $sessionDir = Join-Path $HOME ".claude\devforge-state\$sid"
    if (-not (Test-Path $sessionDir)) { New-Item -ItemType Directory -Path $sessionDir -Force | Out-Null }
    $env:DEVFORGE_SESSION_DIR = $sessionDir

    $userJson = Join-Path $sessionDir "user.json"
    if (Test-Path $userJson) {
        try {
            $d = Get-Content $userJson -Raw | ConvertFrom-Json -ErrorAction Stop
            if ($d.raw) { $env:DEVFORGE_PINNED_USER = Invoke-DevForgeCanonicalizeUser $d.raw }
            # Pin authenticated SSO identity for top-level event fields
            if ($d.identity) {
                if (-not $env:DEVFORGE_AUTH_EMAIL -and $d.identity.auth_email) {
                    $env:DEVFORGE_AUTH_EMAIL = $d.identity.auth_email
                }
                if (-not $env:DEVFORGE_AUTH_ACCOUNT_UUID -and $d.identity.auth_account_uuid) {
                    $env:DEVFORGE_AUTH_ACCOUNT_UUID = $d.identity.auth_account_uuid
                }
            }
        } catch {}
    }
    if (-not $env:DEVFORGE_PINNED_USER) { $env:DEVFORGE_PINNED_USER = Get-DevForgeUser }
}

# --- User identity -----------------------------------------------------------
function Invoke-DevForgeCanonicalizeUser {
    param([string]$raw)
    $r = $raw.Trim().ToLower()
    if (-not $r) { return "unknown" }
    if ($r -match '^\d+\+([^@]+)@users\.noreply\.github\.com$') { return $Matches[1] }
    if ($r -match '^([^@]+)@users\.noreply\.github\.com$') { return $Matches[1] }
    return $r
}

function Get-DevForgeUser {
    if ($env:DEVFORGE_PINNED_USER) { return $env:DEVFORGE_PINNED_USER }
    # Session user file (mirrors DEVFORGE_SESSION_USER_FILE in bash)
    $sessionUserFile = Join-Path $HOME ".claude\.devforge-session-user"
    if (Test-Path $sessionUserFile) {
        $val = (Get-Content $sessionUserFile -Raw -ErrorAction SilentlyContinue).Trim()
        if ($val) { return Invoke-DevForgeCanonicalizeUser $val }
    }
    $raw = ""
    try { $raw = (git config user.email 2>$null) } catch {}
    if (-not $raw) { try { $raw = (git config --global user.email 2>$null) } catch {} }
    # Legacy cache (mirrors ~/.claude/.devforge-user in bash)
    if (-not $raw) {
        $legacyCache = Join-Path $HOME ".claude\.devforge-user"
        if (Test-Path $legacyCache) {
            $raw = (Get-Content $legacyCache -Raw -ErrorAction SilentlyContinue).Trim()
        }
    }
    if (-not $raw) { $raw = $env:USERNAME }
    if (-not $raw) { $raw = "unknown" }
    return Invoke-DevForgeCanonicalizeUser $raw
}

# Returns raw (non-canonical) user, preferring pinned session user.json
function Get-DevForgeUserRaw {
    if ($env:DEVFORGE_SESSION_DIR) {
        $ujson = Join-Path $env:DEVFORGE_SESSION_DIR "user.json"
        if (Test-Path $ujson) {
            try {
                $d = Get-Content $ujson -Raw | ConvertFrom-Json -ErrorAction Stop
                if ($d.raw) { return $d.raw }
            } catch {}
        }
    }
    # Session user file (mirrors DEVFORGE_SESSION_USER_FILE in bash)
    $sessionUserFile = Join-Path $HOME ".claude\.devforge-session-user"
    if (Test-Path $sessionUserFile) {
        $val = (Get-Content $sessionUserFile -Raw -ErrorAction SilentlyContinue).Trim()
        if ($val) { return $val }
    }
    $raw = ""
    try { $raw = (git config user.email 2>$null) } catch {}
    if (-not $raw) { try { $raw = (git config --global user.email 2>$null) } catch {} }
    # Legacy cache
    if (-not $raw) {
        $legacyCache = Join-Path $HOME ".claude\.devforge-user"
        if (Test-Path $legacyCache) {
            $raw = (Get-Content $legacyCache -Raw -ErrorAction SilentlyContinue).Trim()
        }
    }
    if (-not $raw) { $raw = $env:USERNAME }
    return $raw
}

# Returns the source string stored in session user.json
function Get-DevForgeUserSource {
    if ($env:DEVFORGE_SESSION_DIR) {
        $ujson = Join-Path $env:DEVFORGE_SESSION_DIR "user.json"
        if (Test-Path $ujson) {
            try {
                $d = Get-Content $ujson -Raw | ConvertFrom-Json -ErrorAction Stop
                if ($d.source) { return $d.source }
            } catch {}
        }
    }
    # Session user source file (mirrors DEVFORGE_SESSION_USER_SOURCE_FILE in bash)
    $sessionUserSourceFile = Join-Path $HOME ".claude\.devforge-session-user-source"
    if (Test-Path $sessionUserSourceFile) {
        $val = (Get-Content $sessionUserSourceFile -Raw -ErrorAction SilentlyContinue).Trim()
        if ($val) { return $val }
    }
    return "unknown"
}

# Cache user identity to session files (mirrors devforge_cache_user in bash)
function Set-DevForgeUserCache {
    param([string]$RawUser, [string]$Source = "unknown")
    $sessionUserFile       = Join-Path $HOME ".claude\.devforge-session-user"
    $sessionUserSourceFile = Join-Path $HOME ".claude\.devforge-session-user-source"
    $legacyCache           = Join-Path $HOME ".claude\.devforge-user"
    Set-Content -Path $sessionUserFile       -Value $RawUser -NoNewline -Encoding utf8
    Set-Content -Path $sessionUserSourceFile -Value $Source  -NoNewline -Encoding utf8
    Set-Content -Path $legacyCache           -Value $RawUser -NoNewline -Encoding utf8
}

# --- Per-session sequence counter (atomic) ----------------------------------
function Get-DevForgeNextSeq {
    $sessionDir = $env:DEVFORGE_SESSION_DIR
    if (-not $sessionDir -or -not (Test-Path $sessionDir)) { return 0 }
    $seqFile = Join-Path $sessionDir "seq"
    $mutex = New-Object System.Threading.Mutex($false, "DevForgeSeq")
    try {
        $mutex.WaitOne(2000) | Out-Null
        $current = if (Test-Path $seqFile) { [int](Get-Content $seqFile -Raw -ErrorAction SilentlyContinue).Trim() } else { 0 }
        $next = $current + 1
        Set-Content $seqFile $next.ToString() -NoNewline
        return $next
    } catch {
        return 0
    } finally {
        try { $mutex.ReleaseMutex() } catch {}
    }
}

# --- Git context -------------------------------------------------------------
function Get-DevForgeGitContext {
    $branch = "no-branch"
    $jiraId = "null"
    $project = Split-Path (Get-Location) -Leaf
    try {
        $branch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
        $toplevel = (git rev-parse --show-toplevel 2>$null).Trim()
        if ($toplevel) { $project = Split-Path $toplevel -Leaf }
        if ($branch -match '(feature|bugfix|hotfix)/([A-Z]+-\d+)') { $jiraId = "`"$($Matches[2])`"" }
    } catch {}
    return @{ Branch = $branch; JiraId = $jiraId; Project = $project }
}

# --- SDLC phase mapping ------------------------------------------------------
function Get-DevForgeSdlcPhase {
    param([string]$skill)
    switch -Wildcard ($skill) {
        "*onboarding*"     { return "1. Init" }
        "*brainstorming*"  { return "2. Design" }
        "*architecture*"   { return "2. Design" }
        "*git-workflow*"   { return "3. Branching" }
        "*code-standards*" { return "4. Implementation" }
        "*security*"       { return "4. Implementation" }
        "*iac*"            { return "4. Implementation" }
        "*data-engineering*" { return "4. Implementation" }
        "*frontend*"       { return "4. Implementation" }
        "*subagent*"       { return "4. Implementation" }
        "*tdd*"            { return "5. Testing" }
        "*qa*"             { return "5. Testing / QA" }
        "*automation*"     { return "5. Testing / Automation" }
        "*debugging*"      { return "6. QA Gate" }
        "*documentation*"  { return "7. Release" }
        "*verification*"   { return "Cross-cutting" }
        "*writing-skills*" { return "Meta" }
        default            { return "unknown" }
    }
}

# --- Telemetry: schema v2, atomic append, dual-write ------------------------
# Mirrors devforge_log / devforge_log_timed from logger.sh.
# Pass -DurationMs >= 0 to get the duration_ms field (log_timed behaviour).
function Write-DevForgeLog {
    param(
        [string]$Event,
        [string]$Status = "success",
        [string]$Meta = "{}",
        [long]$DurationMs = -1
    )
    # Skip write if disk is critically low (mirrors _devforge_disk_gate)
    if (-not (Test-DevForgeDiskGate)) { return }
    Invoke-DevForgeCheckRotation

    $logFile = $DEVFORGE_LOG_FILE
    $logDir = Split-Path $logFile
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

    $ts       = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.000Z")
    $sid      = Get-DevForgeSid
    $seq      = Get-DevForgeNextSeq
    $eventId  = "$sid-$seq"
    $ctx      = Get-DevForgeGitContext
    $user     = Get-DevForgeUser
    $userRaw  = Get-DevForgeUserRaw
    $userSrc  = Get-DevForgeUserSource
    $hookName = if ($env:DEVFORGE_CURRENT_HOOK) { $env:DEVFORGE_CURRENT_HOOK } else { "unknown" }

    $repoRoot = ""
    try { $repoRoot = (git rev-parse --show-toplevel 2>$null).Trim() } catch {}
    if (-not $repoRoot) { $repoRoot = (Get-Location).Path }
    $projectCanonical = Split-Path $repoRoot -Leaf

    $repoRemote = ""
    try { $repoRemote = (git remote get-url origin 2>$null).Trim() } catch {}

    $authEmail = if ($env:DEVFORGE_AUTH_EMAIL) { $env:DEVFORGE_AUTH_EMAIL } else { "" }
    $authUuid  = if ($env:DEVFORGE_AUTH_ACCOUNT_UUID) { $env:DEVFORGE_AUTH_ACCOUNT_UUID } else { "" }

    # jira_id is null (JSON null) when not present, else quoted string
    $jiraIdJson = if ($ctx.JiraId -eq "null") { "null" } else { "`"$(Convert-ToDevForgeJson ($ctx.JiraId.Trim('"')))`"" }

    $safeEventId   = Convert-ToDevForgeJson $eventId
    $safeHookName  = Convert-ToDevForgeJson $hookName
    $safeUser      = Convert-ToDevForgeJson $user
    $safeUserRaw   = Convert-ToDevForgeJson $userRaw
    $safeUserSrc   = Convert-ToDevForgeJson $userSrc
    $safeSid       = Convert-ToDevForgeJson $sid
    $safeBranch    = Convert-ToDevForgeJson $ctx.Branch
    $safeProject   = Convert-ToDevForgeJson $ctx.Project
    $safeEvent     = Convert-ToDevForgeJson $Event
    $safeStatus    = Convert-ToDevForgeJson $Status
    $safeRepoRoot  = Convert-ToDevForgeJson $repoRoot
    $safeProjCanon = Convert-ToDevForgeJson $projectCanonical
    $safeRemote    = Convert-ToDevForgeJson $repoRemote
    $safeAuthEmail = Convert-ToDevForgeJson $authEmail
    $safeAuthUuid  = Convert-ToDevForgeJson $authUuid

    # Build JSON line (schema v2 — matches devforge_log / devforge_log_timed)
    $base = "{`"event_id`":`"$safeEventId`",`"schema_version`":2,`"session_seq`":$seq," +
            "`"hook_name`":`"$safeHookName`",`"actor_canonical`":`"$safeUser`"," +
            "`"repo_root`":`"$safeRepoRoot`",`"project_canonical`":`"$safeProjCanon`"," +
            "`"repo_remote`":`"$safeRemote`",`"auth_email`":`"$safeAuthEmail`"," +
            "`"auth_account_uuid`":`"$safeAuthUuid`",`"ts`":`"$ts`"," +
            "`"user`":`"$safeUser`",`"user_raw`":`"$safeUserRaw`",`"user_source`":`"$safeUserSrc`"," +
            "`"sid`":`"$safeSid`",`"branch`":`"$safeBranch`",`"jira_id`":$jiraIdJson," +
            "`"project`":`"$safeProject`",`"event`":`"$safeEvent`",`"status`":`"$safeStatus`""
    if ($DurationMs -ge 0) {
        $line = $base + ",`"duration_ms`":$DurationMs,`"meta`":$Meta}"
    } else {
        $line = $base + ",`"meta`":$Meta}"
    }

    # Atomic append via named mutex (mirrors python3 atomic_write.py flock)
    try {
        $mutex = New-Object System.Threading.Mutex($false, "DevForgeTelemetry")
        $mutex.WaitOne(5000) | Out-Null
        Add-Content -Path $logFile -Value $line -Encoding UTF8
        $mutex.ReleaseMutex() | Out-Null
    } catch {
        # Degraded path: no lock, still append
        Add-Content -Path $logFile -Value $line -Encoding UTF8 2>$null
    }

    # Dual write: session-specific activity.jsonl (schema v2)
    if ($env:DEVFORGE_SESSION_DIR -and (Test-Path $env:DEVFORGE_SESSION_DIR)) {
        $sessionActivity = Join-Path $env:DEVFORGE_SESSION_DIR "activity.jsonl"
        if ($sessionActivity -ne $logFile) {
            try { Add-Content -Path $sessionActivity -Value $line -Encoding UTF8 } catch {}
        }
    }
}

# --- Session skills ----------------------------------------------------------
function Get-DevForgeSessionSkills {
    $f = Join-Path $HOME ".claude\.devforge-session-skills"
    if (Test-Path $f) { return (Get-Content $f -Raw).Trim() }
    return ""
}

function Add-DevForgeSessionSkill {
    param([string]$skillName)
    $f = Join-Path $HOME ".claude\.devforge-session-skills"
    $existing = Get-DevForgeSessionSkills
    if (-not $existing) {
        Set-Content $f $skillName -NoNewline
    } elseif ($existing -notlike "*$skillName*") {
        Set-Content $f "$existing,$skillName" -NoNewline
    }
}

# --- Task ID (SHA-256 of branch|design_doc_relative_path|mtime) -------------
# Uses relative path for design_doc (like bash: "docs/plans/foo-design.md")
# so the hash is cross-platform consistent.
function Get-DevForgeTaskId {
    try {
        git rev-parse --git-dir 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { return "" }
    } catch { return "" }

    $remote = ""
    try { $remote = (git remote get-url origin 2>$null).Trim() } catch {}
    if ($remote -notmatch '[/:]itsiae/') { return "" }

    $branch = ""
    try { $branch = (git branch --show-current 2>$null).Trim() } catch {}
    if (-not $branch) {
        # Detached HEAD: prefer stable ref over raw sha
        $ref = ""
        try { $ref = (git describe --all --contains HEAD 2>$null).Trim() -replace '^.*/', '' } catch {}
        if (-not $ref -or $ref -eq "HEAD") {
            try { $ref = (git rev-parse --short HEAD 2>$null).Trim() } catch { $ref = "nohead" }
        }
        $branch = "detached@$ref"
    }

    $designDoc   = ""
    $designMtime = "0"
    if (Test-Path "docs\plans") {
        $latest = Get-ChildItem "docs\plans\*-design.md" -ErrorAction SilentlyContinue |
                  Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latest) {
            # Relative path with forward slashes — matches bash ls output
            $designDoc   = "docs/plans/" + $latest.Name
            $designMtime = [DateTimeOffset]::new($latest.LastWriteTime).ToUnixTimeSeconds().ToString()
        }
    }

    $material = "${branch}|${designDoc}|${designMtime}"
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($material)
    $hash = $sha.ComputeHash($bytes)
    return ([BitConverter]::ToString($hash) -replace '-', '').ToLower().Substring(0, 12)
}

# --- Task skill tracking ----------------------------------------------------
function Register-DevForgeTaskSkillInvoked {
    param([string]$taskId, [string]$skillName)
    $dir  = Join-Path $HOME ".claude\.devforge-task-skills\$taskId"
    $file = Join-Path $dir "skills_invoked"
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $existing = if (Test-Path $file) { Get-Content $file } else { @() }
    if ($skillName -notin $existing) { Add-Content $file $skillName }
}

function Test-DevForgeTaskSkillValidated {
    param([string]$taskId, [string]$skillName)
    $file = Join-Path $HOME ".claude\.devforge-task-skills\$taskId\skills_validated"
    if (-not (Test-Path $file)) { return $false }
    return $skillName -in (Get-Content $file)
}

function Add-DevForgeTaskSkillMarkValidated {
    param([string]$taskId, [string]$skillName)
    $dir  = Join-Path $HOME ".claude\.devforge-task-skills\$taskId"
    $file = Join-Path $dir "skills_validated"
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $existing = if (Test-Path $file) { Get-Content $file } else { @() }
    if ($skillName -notin $existing) { Add-Content $file $skillName }
}

# Copies skills_invoked + skills_validated when task_id changes mid-session
# (design doc revised but same branch and doc path). Mirrors devforge_task_id_transition.
function Invoke-DevForgeTaskIdTransition {
    param([string]$OldId, [string]$NewId)
    if (-not $OldId -or -not $NewId -or $OldId -eq $NewId) { return }
    $oldDir = Join-Path $HOME ".claude\.devforge-task-skills\$OldId"
    $newDir = Join-Path $HOME ".claude\.devforge-task-skills\$NewId"
    if (-not (Test-Path "$oldDir\metadata")) { return }

    $getField = { param($file, $key)
        $line = Get-Content $file -ErrorAction SilentlyContinue | Where-Object { $_ -match "^$key=" } | Select-Object -First 1
        if ($line) { return $line -replace "^$key=", '' }
        return ""
    }

    $oldBranch = & $getField "$oldDir\metadata" "branch_name"
    $oldDesign = & $getField "$oldDir\metadata" "design_doc"
    $newBranch = if (Test-Path "$newDir\metadata") { & $getField "$newDir\metadata" "branch_name" } else { "" }
    $newDesign = if (Test-Path "$newDir\metadata") { & $getField "$newDir\metadata" "design_doc" } else { "" }

    # Only transfer if branch AND design_doc path are unchanged
    if ($oldBranch -ne $newBranch -or $oldDesign -ne $newDesign) { return }

    New-Item -ItemType Directory -Path $newDir -Force | Out-Null
    foreach ($f in @("skills_invoked", "skills_validated")) {
        $oldFile = Join-Path $oldDir $f
        $newFile = Join-Path $newDir $f
        if (Test-Path $oldFile) {
            $oldLines = Get-Content $oldFile
            $newLines = if (Test-Path $newFile) { Get-Content $newFile } else { @() }
            $merged = ($oldLines + $newLines) | Where-Object { $_ } | Sort-Object -Unique
            Set-Content $newFile $merged
        }
    }
}

# --- Helpers -----------------------------------------------------------------
function Read-StdinAll {
    $sb = [System.Text.StringBuilder]::new()
    $reader = [System.Console]::In
    $buf = New-Object char[] 4096
    while (($n = $reader.Read($buf, 0, 4096)) -gt 0) {
        $sb.Append($buf, 0, $n) | Out-Null
    }
    return $sb.ToString()
}

function Get-JsonField {
    param([string]$json, [string]$field)
    if (-not $json) { return "" }
    if (Get-Command jq -ErrorAction SilentlyContinue) {
        $val = ($json | jq -r ".$field // empty" 2>$null)
        return if ($val -and $val -ne "null") { $val } else { "" }
    }
    # Fallback: nested dot-path (e.g. "tool_input.command")
    $parts = $field.Split('.')
    $current = $json
    foreach ($p in $parts) {
        if ($current -match "`"$p`"\s*:\s*`"([^`"]*)`"") { $current = $Matches[1] } else { return "" }
    }
    return $current
}

# --- Mode sentinels (mirrors devforge_set_mode / devforge_clear_mode) -------
function Set-DevForgeMode {
    param([string]$Mode, [string]$Context)
    $sentinelFile = Join-Path (Get-Location) ".devforge-active-${Mode}"
    Set-Content -Path $sentinelFile -Value $Context -NoNewline -Encoding utf8
}

function Clear-DevForgeMode {
    param([string]$Mode)
    $sentinelFile = Join-Path (Get-Location) ".devforge-active-${Mode}"
    Remove-Item -Path $sentinelFile -Force -ErrorAction SilentlyContinue
}

# --- TDD state machine (mirrors devforge_tdd_set/get/reset_phase) -----------
function Set-DevForgeTddPhase {
    param(
        [string]$Phase,
        [string]$Target   = "unknown",
        [string]$TestName = "unknown"
    )
    $stateFile = Join-Path $HOME ".claude\.devforge-tdd-state"
    $ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    Set-Content -Path $stateFile -Value "${Phase}|${Target}|${TestName}|${ts}" -NoNewline -Encoding utf8
}

function Get-DevForgeTddPhase {
    $stateFile = Join-Path $HOME ".claude\.devforge-tdd-state"
    if (-not (Test-Path $stateFile)) { return "" }
    $content = (Get-Content $stateFile -Raw -ErrorAction SilentlyContinue).Trim()
    if (-not $content) { return "" }
    return $content.Split('|')[0]
}

function Reset-DevForgeTdd {
    $stateFile = Join-Path $HOME ".claude\.devforge-tdd-state"
    Remove-Item -Path $stateFile -Force -ErrorAction SilentlyContinue
}

Export-ModuleMember -Function *
