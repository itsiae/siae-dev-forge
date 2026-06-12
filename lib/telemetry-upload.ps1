# telemetry-upload.ps1  -  DevForge Telemetry Upload (Windows/PS5.1)
# Outbox model: activity.jsonl -> outbox/batch-<ts>.jsonl -> POST -> outbox/acked/
# Invocato come script standalone in background da: devforge-flusher, session-start,
# post-commit-review. Equivalente di: source lib/telemetry-upload.sh && devforge_upload_logs
param()
$ErrorActionPreference = 'SilentlyContinue'

$DEVFORGE_TELEMETRY_ENDPOINT = if ($env:DEVFORGE_TELEMETRY_ENDPOINT) { $env:DEVFORGE_TELEMETRY_ENDPOINT } `
    else { "https://5o6tu3hcei.execute-api.eu-west-1.amazonaws.com/v1/logs" }
$DEVFORGE_TELEMETRY_KEY = if ($env:DEVFORGE_TELEMETRY_KEY) { $env:DEVFORGE_TELEMETRY_KEY } `
    else { "WhQioTyfb41PcvRrjD7ji6o8xF59quSd3OYvM1sz" }

# Backward compat: honour legacy DEVFORGE_TELEMETRY_URL if set
if ($env:DEVFORGE_TELEMETRY_URL) { $DEVFORGE_TELEMETRY_ENDPOINT = $env:DEVFORGE_TELEMETRY_URL }

# ---------------------------------------------------------------------------
# Invoke-DevForgeEpochNs  —  timestamp in nanoseconds (best-effort)
# ---------------------------------------------------------------------------
function Invoke-DevForgeEpochNs {
    $ms = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    return ($ms.ToString() + "000000")
}

# ---------------------------------------------------------------------------
# Invoke-DevForgeMaybeRemoveArchived
# Rimuove un archived file se il cursore ha raggiunto la fine (tutto inviato).
# ---------------------------------------------------------------------------
function Invoke-DevForgeMaybeRemoveArchived {
    param([string]$FilePath, [string]$OutboxDir)
    $basename = Split-Path $FilePath -Leaf
    if ($basename -notmatch '^activity-.*\.archived\.jsonl$') { return }
    $cursorFile = Join-Path $OutboxDir ".cursor-$basename"
    $cursor     = 0
    if (Test-Path $cursorFile) { $cursor = [long](Get-Content $cursorFile -Raw -ErrorAction SilentlyContinue).Trim() }
    $fileSize   = 0
    if (Test-Path $FilePath)   { $fileSize = (Get-Item $FilePath).Length }
    if ($fileSize -gt 0 -and $cursor -ge $fileSize) {
        Remove-Item $FilePath   -Force -ErrorAction SilentlyContinue
        Remove-Item $cursorFile -Force -ErrorAction SilentlyContinue
    }
}

# ---------------------------------------------------------------------------
# Invoke-DevForgeCreateBatch
# Copia le nuove righe di activity.jsonl (e archived) in batch files nell'outbox.
# Usa un cursore per-file (byte offset) per garantire zero-loss e idempotenza.
# ---------------------------------------------------------------------------
function Invoke-DevForgeCreateBatch {
    $sessionDir = $env:DEVFORGE_SESSION_DIR
    if (-not $sessionDir -or -not (Test-Path $sessionDir)) { return }

    $outboxDir = Join-Path $sessionDir "outbox"
    try { New-Item -ItemType Directory -Path $outboxDir -Force | Out-Null } catch { return }

    $lockFile = Join-Path $outboxDir ".batch.lock"
    $mutex    = $null
    $mutexName = "DevForgeBatch_" + ($sessionDir -replace '[^a-zA-Z0-9]', '_')
    try {
        $mutex = New-Object System.Threading.Mutex($false, $mutexName)
        if (-not $mutex.WaitOne(0)) { return }   # another process is batching
    } catch { return }

    try {
        # Archived files (oldest first) then current activity.jsonl
        $archivedFiles = @(Get-ChildItem $sessionDir -Filter "activity-*.archived.jsonl" -ErrorAction SilentlyContinue |
            Sort-Object Name | Select-Object -ExpandProperty FullName)
        $activityFile = Join-Path $sessionDir "activity.jsonl"
        $files = $archivedFiles
        if (Test-Path $activityFile) { $files = $files + @($activityFile) }

        foreach ($f in $files) {
            if (-not (Test-Path $f)) {
                Invoke-DevForgeMaybeRemoveArchived $f $outboxDir
                continue
            }
            $fileSize = (Get-Item $f).Length
            if ($fileSize -eq 0) {
                Invoke-DevForgeMaybeRemoveArchived $f $outboxDir
                continue
            }

            $basename   = Split-Path $f -Leaf
            $cursorFile = Join-Path $outboxDir ".cursor-$basename"
            $cursor     = [long]0
            if (Test-Path $cursorFile) {
                $raw = (Get-Content $cursorFile -Raw -ErrorAction SilentlyContinue).Trim()
                if ($raw -match '^\d+$') { $cursor = [long]$raw }
            }

            if ($fileSize -gt $cursor) {
                $epochNs   = Invoke-DevForgeEpochNs
                $batchFile = Join-Path $outboxDir "batch-${epochNs}-${PID}-$($basename -replace '\.jsonl$','').jsonl"

                try {
                    $fs = [System.IO.FileStream]::new($f, [System.IO.FileMode]::Open,
                        [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
                    $fs.Seek($cursor, [System.IO.SeekOrigin]::Begin) | Out-Null
                    $remaining = $fileSize - $cursor
                    $buf       = New-Object byte[] $remaining
                    $read      = $fs.Read($buf, 0, $remaining)
                    $fs.Close()

                    if ($read -gt 0) {
                        [System.IO.File]::WriteAllBytes($batchFile, $buf[0..($read-1)])
                        [System.IO.File]::WriteAllText($cursorFile, $fileSize.ToString())
                    }
                } catch {
                    Remove-Item $batchFile -Force -ErrorAction SilentlyContinue
                }
            }

            Invoke-DevForgeMaybeRemoveArchived $f $outboxDir
        }
    } finally {
        try { $mutex.ReleaseMutex() } catch {}
        try { $mutex.Dispose()      } catch {}
    }
}

# ---------------------------------------------------------------------------
# Invoke-DevForgeBatchGlobal
# Drena il file globale (~/.claude/devforge-activity.jsonl) che riceve eventi
# quando la sessione non è ancora inizializzata correttamente.
# ---------------------------------------------------------------------------
function Invoke-DevForgeBatchGlobal {
    $globalFile = if ($env:DEVFORGE_LOG_FILE) { $env:DEVFORGE_LOG_FILE } `
        else { Join-Path $HOME ".claude\devforge-activity.jsonl" }
    if (-not (Test-Path $globalFile)) { return }
    $fileSize = (Get-Item $globalFile).Length
    if ($fileSize -eq 0) { return }

    $stateRoot  = Join-Path $HOME ".claude\devforge-state"
    $globalOutbox = Join-Path $stateRoot ".global-outbox"
    try {
        New-Item -ItemType Directory -Path (Join-Path $globalOutbox "acked") -Force | Out-Null
    } catch { return }

    $cursorFile = Join-Path $globalOutbox ".cursor-global"
    $cursor     = [long]0
    if (Test-Path $cursorFile) {
        $raw = (Get-Content $cursorFile -Raw -ErrorAction SilentlyContinue).Trim()
        if ($raw -match '^\d+$') { $cursor = [long]$raw }
    }

    if ($fileSize -gt $cursor) {
        $epochNs   = Invoke-DevForgeEpochNs
        $batchFile = Join-Path $globalOutbox "batch-${epochNs}-${PID}.jsonl"
        try {
            $fs = [System.IO.FileStream]::new($globalFile, [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            $fs.Seek($cursor, [System.IO.SeekOrigin]::Begin) | Out-Null
            $remaining = $fileSize - $cursor
            $buf       = New-Object byte[] $remaining
            $read      = $fs.Read($buf, 0, $remaining)
            $fs.Close()

            if ($read -gt 0) {
                [System.IO.File]::WriteAllBytes($batchFile, $buf[0..($read-1)])
                [System.IO.File]::WriteAllText($cursorFile, $fileSize.ToString())
            }
        } catch {
            Remove-Item $batchFile -Force -ErrorAction SilentlyContinue
        }
    }
}

# ---------------------------------------------------------------------------
# Invoke-DevForgeUploadBacklog
# Itera tutti gli outbox (session + global) e invia i batch pendenti via HTTPS POST.
# ---------------------------------------------------------------------------
function Invoke-DevForgeUploadBacklog {
    if (-not $DEVFORGE_TELEMETRY_ENDPOINT) { return }
    if ($DEVFORGE_TELEMETRY_ENDPOINT -notmatch '^https://') { return }   # never over plain HTTP

    $stateRoot = Join-Path $HOME ".claude\devforge-state"
    if (-not (Test-Path $stateRoot)) { return }

    # Session outboxes + global outbox
    $outboxDirs = @(Get-ChildItem $stateRoot -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path $_.FullName "outbox" }) +
        @(Join-Path $stateRoot ".global-outbox")

    foreach ($outboxDir in $outboxDirs) {
        if (-not (Test-Path $outboxDir)) { continue }
        $batches = Get-ChildItem $outboxDir -Filter "batch-*.jsonl" -ErrorAction SilentlyContinue
        if (-not $batches) { continue }

        foreach ($batch in $batches) {
            try {
                $response = Invoke-WebRequest `
                    -Method POST `
                    -Uri $DEVFORGE_TELEMETRY_ENDPOINT `
                    -Headers @{ 'x-api-key' = $DEVFORGE_TELEMETRY_KEY; 'Content-Type' = 'application/jsonl' } `
                    -InFile $batch.FullName `
                    -TimeoutSec 10 `
                    -UseBasicParsing `
                    -ErrorAction Stop

                if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 201) {
                    $ackedDir = Join-Path $outboxDir "acked"
                    New-Item -ItemType Directory -Path $ackedDir -Force | Out-Null
                    Move-Item $batch.FullName $ackedDir -Force -ErrorAction SilentlyContinue
                }
            } catch {}
        }
    }
}

# ---------------------------------------------------------------------------
# Invoke-DevForgeUploadLogs  —  entry point principale (mirrors devforge_upload_logs)
# ---------------------------------------------------------------------------
function Invoke-DevForgeUploadLogs {
    Invoke-DevForgeCreateBatch   2>$null
    Invoke-DevForgeBatchGlobal   2>$null
    Invoke-DevForgeUploadBacklog 2>$null
}

# ---------------------------------------------------------------------------
# Get-DevForgePendingCount  —  conta batch non ancora inviati (mirrors devforge_pending_count)
# ---------------------------------------------------------------------------
function Get-DevForgePendingCount {
    $stateRoot = Join-Path $HOME ".claude\devforge-state"
    if (-not (Test-Path $stateRoot)) { return 0 }
    $count = 0
    $outboxDirs = @(Get-ChildItem $stateRoot -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path $_.FullName "outbox" }) +
        @(Join-Path $stateRoot ".global-outbox")
    foreach ($d in $outboxDirs) {
        if (Test-Path $d) {
            $count += @(Get-ChildItem $d -Filter "batch-*.jsonl" -ErrorAction SilentlyContinue).Count
        }
    }
    return $count
}

# ---------------------------------------------------------------------------
# Esecuzione standalone (quando invocato con & o Start-Job)
# ---------------------------------------------------------------------------
Invoke-DevForgeUploadLogs
