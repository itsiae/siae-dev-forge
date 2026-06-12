# install.ps1  -  Idempotent installer for DevForge status line (Windows/PS5.1)
# Injects statusLine configuration into $HOME/.claude/settings.json
param()
$ErrorActionPreference = 'SilentlyContinue'

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR

$statuslineScript = Join-Path $PLUGIN_ROOT "statusline\devforge-statusline.ps1"
$settingsFile     = Join-Path $HOME ".claude\settings.json"

# 1. Verify devforge-statusline.ps1 exists
if (-not (Test-Path $statuslineScript)) {
    Write-Error "[DevForge] ERROR: devforge-statusline.ps1 non trovato in $statuslineScript"
    exit 1
}

$desiredCommand = "powershell -NonInteractive -ExecutionPolicy Bypass -File `"$statuslineScript`""

# 2. Create settings.json with {} if it does not exist
$claudeDir = Split-Path $settingsFile
if (-not (Test-Path $claudeDir)) {
    New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null
}
if (-not (Test-Path $settingsFile)) {
    '{}' | Set-Content $settingsFile -Encoding UTF8
}

# 3. Read current settings
$settingsRaw = Get-Content $settingsFile -Raw -ErrorAction SilentlyContinue
if (-not $settingsRaw) { $settingsRaw = '{}' }

$settings = $null
try { $settings = $settingsRaw | ConvertFrom-Json -ErrorAction Stop } catch {}
if (-not $settings) { $settings = New-Object PSObject }

# 4. Check current statusLine
$currentCommand = ""
if ($settings.statusLine -and $settings.statusLine.command) {
    $currentCommand = $settings.statusLine.command
}

if ($currentCommand) {
    if ($currentCommand -like "*devforge-statusline*") {
        if ($currentCommand -eq $desiredCommand) {
            # Already configured correctly
            exit 0
        }
        # Path changed (plugin moved) — update
        $settings.statusLine.command = $desiredCommand
    } else {
        # Different statusLine — do NOT overwrite
        Write-Host "[DevForge] NOTA: statusLine gia' configurata con un comando custom. Non sovrascrivo." -ForegroundColor Yellow
        Write-Host "[DevForge] Comando attuale: $currentCommand" -ForegroundColor Yellow
        Write-Host "[DevForge] Per usare DevForge statusline, aggiungi manualmente a ${settingsFile}:" -ForegroundColor Yellow
        Write-Host "  `"statusLine`": { `"type`": `"command`", `"command`": `"$desiredCommand`" }" -ForegroundColor Yellow
        exit 0
    }
} else {
    # statusLine not configured — inject
    $statusLineObj = New-Object PSObject
    $statusLineObj | Add-Member -NotePropertyName "type"    -NotePropertyValue "command" -Force
    $statusLineObj | Add-Member -NotePropertyName "command" -NotePropertyValue $desiredCommand -Force
    $settings | Add-Member -NotePropertyName "statusLine" -NotePropertyValue $statusLineObj -Force
}

# 5. Write back
$tmpFile = $settingsFile + ".tmp"
try {
    $settings | ConvertTo-Json -Depth 20 | Set-Content $tmpFile -Encoding UTF8 -Force
    Move-Item $tmpFile $settingsFile -Force
    Write-Host "[DevForge] Status line installata/aggiornata." -ForegroundColor Green
} catch {
    Remove-Item $tmpFile -Force -ErrorAction SilentlyContinue
    Write-Error "[DevForge] Errore scrittura settings.json: $_"
    exit 1
}
exit 0
