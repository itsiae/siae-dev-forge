# setup-mcp-kibana.ps1  -  PowerShell equivalent
# Hook: SessionStart (async, idempotent)
param()
$ErrorActionPreference = 'SilentlyContinue'

$installDir = Join-Path $HOME ".claude\mcp-servers\siae-mcp-kibana"
$binary     = Join-Path $installDir "dist\index.js"
$repoUrl    = "https://github.com/itsiae/siae-mcp-kibana.git"

$esHosts    = "http://10.255.1.165:9200,http://10.255.1.166:9200"
$esUsername = "prod-claude-mcp-user"
$esPassword = "fL7w_^yX0@d3"

# Idempotency check
if ((Test-Path $binary)) {
    try {
        $mcpList = (claude mcp list 2>$null)
        if ($mcpList -match "elasticsearch.*$([regex]::Escape($installDir))") { exit 0 }
    } catch { }
}

Write-Host "DevForge: installazione siae-mcp-kibana..." -ForegroundColor Cyan

$parentDir = Split-Path $installDir
New-Item -ItemType Directory -Path $parentDir -Force | Out-Null

if (Test-Path (Join-Path $installDir ".git")) {
    git -C $installDir pull --quiet 2>$null | Out-Null
} else {
    git clone --quiet $repoUrl $installDir 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "DevForge: git clone siae-mcp-kibana fallito" -ForegroundColor Red
        exit 1
    }
}

Set-Location $installDir
npm install --quiet --no-audit 2>$null | Out-Null
npm run build --quiet 2>$null | Out-Null

# Register MCP server
try { claude mcp remove elasticsearch -s user 2>$null | Out-Null } catch { }
claude mcp add elasticsearch `
    --transport stdio `
    node $binary `
    -e "ES_HOSTS=$esHosts" `
    -e "ES_USERNAME=$esUsername" `
    -e "ES_PASSWORD=$esPassword" `
    -s user 2>$null | Out-Null

Write-Host "DevForge: siae-mcp-kibana installato e configurato." -ForegroundColor Green
exit 0
