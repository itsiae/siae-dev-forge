# install-windows.ps1
# Installs the Windows-native hook configuration for siae-dev-forge.
# Run once after cloning the plugin, or after any update to hooks.windows.json.
#
# Effect: copies hooks.windows.json over hooks.json so Claude Code loads
# PowerShell-native hooks (powershell.exe -File *.ps1) instead of the
# bash-based originals.
#
# The original hooks.json (bash variant) is preserved as hooks.unix.json
# and can be restored with install-unix.ps1.

param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$hooksDir     = $PSScriptRoot
$windowsSrc   = Join-Path $hooksDir "hooks.windows.json"
$unixBackup   = Join-Path $hooksDir "hooks.unix.json"
$target       = Join-Path $hooksDir "hooks.json"

if (-not (Test-Path $windowsSrc)) {
    Write-Error "hooks.windows.json not found in $hooksDir"
    exit 1
}

# Back up the current hooks.json as hooks.unix.json (only if not already done)
if (-not (Test-Path $unixBackup)) {
    Copy-Item $target $unixBackup
    Write-Host "Backed up hooks.json -> hooks.unix.json" -ForegroundColor DarkGray
} elseif ($Force) {
    Copy-Item $target $unixBackup -Force
    Write-Host "Force-updated hooks.unix.json backup" -ForegroundColor DarkGray
}

# Install Windows variant
Copy-Item $windowsSrc $target -Force
Write-Host "OK  hooks.json <- hooks.windows.json (PowerShell-native, no bash/cmd)" -ForegroundColor Green

# Ensure all PS1 hooks have UTF-8 BOM so PowerShell 5.1 reads Unicode correctly.
# Without BOM, PS5.1 falls back to the system ANSI codepage (cp1252) and misreads
# box-drawing characters, emoji, and accented strings — causing ParseException at runtime.
Write-Host ""
Write-Host "Normalizing PS1 encoding (UTF-8 BOM)..." -ForegroundColor DarkGray
$utf8Bom = New-Object System.Text.UTF8Encoding $true
$fixed = 0
Get-ChildItem $hooksDir -Filter "*.ps1" | ForEach-Object {
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    if (-not ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)) {
        $content = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
        [System.IO.File]::WriteAllText($_.FullName, $content, $utf8Bom)
        $fixed++
    }
}
if ($fixed -gt 0) {
    Write-Host "OK  $fixed PS1 file(s) re-encoded with UTF-8 BOM" -ForegroundColor Green
} else {
    Write-Host "OK  All PS1 files already have UTF-8 BOM" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "siae-dev-forge Windows hooks active." -ForegroundColor Cyan
Write-Host "To revert: run install-unix.ps1"
