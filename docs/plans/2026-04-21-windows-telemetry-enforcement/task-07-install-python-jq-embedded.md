# Task 07 — Install-PythonViaStandaloneEmbedded + Install-JqFromAsset

**PR:** PR-1 | **SP:** 0.3 SP-Augmented | **Dipendenze:** T01, T03, T06 | **Stato:** [DONE]

## File coinvolti

- `install.ps1` (modifica: `Install-PythonViaStandaloneEmbedded`, `Install-JqFromAsset`)
- `tests/install-ps1/InstallPythonJqEmbedded.Tests.ps1` (nuovo)

## Fonti asset

- Python-Standalone: `https://github.com/itsiae/siae-dev-forge/releases/latest/download/python-standalone-x64.tar.gz` (mirror di `indygreg/python-build-standalone` v3.12.x)
- jq: `https://github.com/itsiae/siae-dev-forge/releases/latest/download/jq-win64.exe` (mirror di `jqlang/jq` v1.7.1)

## Step 1 — Test RED

File: `tests/install-ps1/InstallPythonJqEmbedded.Tests.ps1`

```powershell
#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Install-PythonViaStandaloneEmbedded" {
    BeforeEach { $script:DevForgePythonSha256 = 'EXPECTED_HASH' }

    It "scarica tar.gz, verifica SHA256, estrae in LOCALAPPDATA\\DevForge\\python" {
        Mock Invoke-WebRequest { } -Verifiable
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'EXPECTED_HASH' } }
        Mock Start-Process { [pscustomobject]@{ ExitCode = 0 } } -Verifiable  # tar.exe nativo Win10+
        $pythonExe = Join-Path $env:LOCALAPPDATA 'DevForge\python\python.exe'
        Mock Test-Path { $true } -ParameterFilter { $Path -eq $pythonExe }

        Install-PythonViaStandaloneEmbedded | Should -Be $pythonExe
        Should -Invoke Start-Process -ParameterFilter { $FilePath -match 'tar' }
    }
    It "abort su SHA256 mismatch" {
        Mock Invoke-WebRequest { }
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'WRONG' } }
        Mock Start-Process { throw "should not run" }
        Install-PythonViaStandaloneEmbedded | Should -Be $null
    }
}

Describe "Install-JqFromAsset" {
    BeforeEach { $script:DevForgeJqSha256 = 'EXPECTED_HASH_JQ' }

    It "scarica jq.exe, verifica SHA256, copia in LOCALAPPDATA\\DevForge\\bin" {
        Mock Invoke-WebRequest { } -Verifiable
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'EXPECTED_HASH_JQ' } }
        $jqPath = Join-Path $env:LOCALAPPDATA 'DevForge\bin\jq.exe'
        Mock Test-Path { $true } -ParameterFilter { $Path -eq $jqPath }

        Install-JqFromAsset | Should -Be $jqPath
    }
    It "copia jq.exe anche in PortableGit\\usr\\bin se PortableGit presente" {
        Mock Invoke-WebRequest { }
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'EXPECTED_HASH_JQ' } }
        $portableUsrBin = Join-Path $env:LOCALAPPDATA 'DevForge\PortableGit\usr\bin'
        Mock Test-Path { $true } -ParameterFilter { $Path -eq $portableUsrBin }
        Mock Copy-Item { } -Verifiable -ParameterFilter {
            $Destination -match 'PortableGit\\usr\\bin'
        }
        Install-JqFromAsset | Out-Null
        Should -Invoke Copy-Item
    }
}
```

## Step 2 — Run (RED)

```powershell
Invoke-Pester tests/install-ps1/InstallPythonJqEmbedded.Tests.ps1
# Atteso: 4 Failed
```

## Step 3 — Impl

```powershell
$script:DevForgePythonUrl    = 'https://github.com/itsiae/siae-dev-forge/releases/latest/download/python-standalone-x64.tar.gz'
$script:DevForgePythonSha256 = '0000000000000000000000000000000000000000000000000000000000000000'

$script:DevForgeJqUrl    = 'https://github.com/itsiae/siae-dev-forge/releases/latest/download/jq-win64.exe'
$script:DevForgeJqSha256 = '0000000000000000000000000000000000000000000000000000000000000000'

function Install-PythonViaStandaloneEmbedded {
    [CmdletBinding()]
    param()
    Write-InstallLog "Install Python-Standalone embedded..." -Level Info

    $tmpDir = Join-Path $env:TEMP "devforge-python-$(Get-Random)"
    New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
    $tgzPath = Join-Path $tmpDir "python.tar.gz"
    $destDir = Join-Path $env:LOCALAPPDATA 'DevForge\python'

    try {
        Invoke-WebRequest -Uri $script:DevForgePythonUrl -OutFile $tgzPath -UseBasicParsing -TimeoutSec 300
    } catch {
        Write-InstallLog "Download Python-Standalone fallito: $_" -Level Error
        Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        return $null
    }

    $actualHash = (Get-FileHash -Path $tgzPath -Algorithm SHA256).Hash.ToUpper()
    if ($actualHash -ne $script:DevForgePythonSha256.ToUpper()) {
        Write-InstallLog "SHA256 Python mismatch — ABORT" -Level Error
        Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        return $null
    }

    if (Test-Path -LiteralPath $destDir) {
        Remove-Item -LiteralPath $destDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null

    # Win10 1803+ include tar.exe nativo
    $proc = Start-Process -FilePath 'tar.exe' -ArgumentList @('-xzf', $tgzPath, '-C', $destDir, '--strip-components=1') -Wait -PassThru -NoNewWindow
    Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue

    if ($proc.ExitCode -ne 0) {
        Write-InstallLog "tar extract exit code $($proc.ExitCode)" -Level Warning
    }

    $pythonExe = Join-Path $destDir 'python.exe'
    if (Test-Path -LiteralPath $pythonExe) {
        Write-InstallLog "Python-Standalone estratto: $pythonExe" -Level Info
        return $pythonExe
    }
    return $null
}

function Install-JqFromAsset {
    [CmdletBinding()]
    param()
    Write-InstallLog "Install jq da release asset..." -Level Info

    $destDir = Join-Path $env:LOCALAPPDATA 'DevForge\bin'
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    $jqPath = Join-Path $destDir 'jq.exe'

    try {
        Invoke-WebRequest -Uri $script:DevForgeJqUrl -OutFile $jqPath -UseBasicParsing -TimeoutSec 120
    } catch {
        Write-InstallLog "Download jq fallito: $_" -Level Error
        return $null
    }

    $actualHash = (Get-FileHash -Path $jqPath -Algorithm SHA256).Hash.ToUpper()
    if ($actualHash -ne $script:DevForgeJqSha256.ToUpper()) {
        Write-InstallLog "SHA256 jq mismatch — ABORT" -Level Error
        Remove-Item $jqPath -Force -ErrorAction SilentlyContinue
        return $null
    }

    # Copia anche in PortableGit\usr\bin\ se PortableGit presente (aumenta discoverability)
    $portableUsrBin = Join-Path $env:LOCALAPPDATA 'DevForge\PortableGit\usr\bin'
    if (Test-Path -LiteralPath $portableUsrBin) {
        Copy-Item -Path $jqPath -Destination $portableUsrBin -Force -ErrorAction SilentlyContinue
        Write-InstallLog "jq copiato in $portableUsrBin" -Level Info
    }

    Write-InstallLog "jq installato: $jqPath" -Level Info
    return $jqPath
}
```

## Step 4 — Run (GREEN)

```powershell
Invoke-Pester tests/install-ps1/InstallPythonJqEmbedded.Tests.ps1
# Atteso: 4/4 Passed
```

## Step 5 — Commit

```bash
git add install.ps1 tests/install-ps1/InstallPythonJqEmbedded.Tests.ps1
git commit -m "feat(windows): install Python-Standalone + jq from release assets [AC-3, AC-11]"
```
