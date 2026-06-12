# setup-mcp-sport.ps1  -  PowerShell equivalent
# Hook: SessionStart (async, idempotent)
param()
$ErrorActionPreference = 'SilentlyContinue'

$installDir = Join-Path $HOME ".claude\mcp-servers\siae-sport-mcp"
$binary     = Join-Path $installDir "dist\index.js"
$repoUrl    = "https://github.com/itsiae/siae-sport-mcp.git"
$claudeJson = Join-Path $HOME ".claude.json"

$oracleUser        = "MCPCLAUDEUSER"
$oraclePassword    = "U45mdUcPL3C3_2026"
$oracleHost        = "dbsport-scan.servizi.siae"
$oraclePort        = "1521"
$oracleServiceName = "SPORTPRD.NET.SIAE"

# Idempotency
if ((Test-Path $binary) -and (Test-Path $claudeJson)) {
    if ((Get-Content $claudeJson -Raw) -match '"siae-sport-oracle"') { exit 0 }
}

Write-Host "DevForge: installazione siae-sport-mcp..." -ForegroundColor Cyan

$parentDir = Split-Path $installDir
New-Item -ItemType Directory -Path $parentDir -Force | Out-Null

if (Test-Path (Join-Path $installDir ".git")) {
    git -C $installDir pull --quiet 2>$null | Out-Null
} else {
    git clone --quiet $repoUrl $installDir 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "DevForge: git clone siae-sport-mcp fallito" -ForegroundColor Red
        exit 1
    }
}

Set-Location $installDir
npm install --quiet --no-audit 2>$null | Out-Null
npm run build --quiet 2>$null | Out-Null

# Register in ~/.claude.json via PowerShell JSON manipulation
try {
    $config = if (Test-Path $claudeJson) {
        Get-Content $claudeJson -Raw | ConvertFrom-Json
    } else {
        [PSCustomObject]@{}
    }

    if (-not $config.mcpServers) {
        $config | Add-Member -MemberType NoteProperty -Name mcpServers -Value ([PSCustomObject]@{}) -Force
    }

    $serverConfig = [PSCustomObject]@{
        type    = "stdio"
        command = "node"
        args    = @("$installDir\dist\index.js")
        env     = [PSCustomObject]@{
            ORACLE_USER         = $oracleUser
            ORACLE_PASSWORD     = $oraclePassword
            ORACLE_HOST         = $oracleHost
            ORACLE_PORT         = $oraclePort
            ORACLE_SERVICE_NAME = $oracleServiceName
        }
    }
    $config.mcpServers | Add-Member -MemberType NoteProperty -Name "siae-sport-oracle" -Value $serverConfig -Force

    $config | ConvertTo-Json -Depth 10 | Set-Content $claudeJson -Encoding UTF8
    Write-Host "DevForge: siae-sport-mcp installato e configurato." -ForegroundColor Green
    exit 0
} catch {
    Write-Host "DevForge: registrazione siae-sport-oracle in ~/.claude.json fallita: $_" -ForegroundColor Red
    exit 1
}
