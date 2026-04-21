#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Install-PythonViaStandaloneEmbedded" {
    BeforeEach { $script:DevForgePythonSha256 = 'EXPECTED_HASH' }

    It "scarica tar.gz, verifica SHA256, estrae in LOCALAPPDATA\DevForge\python" {
        Mock Invoke-WebRequest { } -Verifiable
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'EXPECTED_HASH' } }
        Mock Start-Process { [pscustomobject]@{ ExitCode = 0 } } -Verifiable
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

    It "scarica jq.exe, verifica SHA256, copia in LOCALAPPDATA\DevForge\bin" {
        Mock Invoke-WebRequest { } -Verifiable
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'EXPECTED_HASH_JQ' } }
        $jqPath = Join-Path $env:LOCALAPPDATA 'DevForge\bin\jq.exe'
        Mock Test-Path { $true } -ParameterFilter { $Path -eq $jqPath }

        Install-JqFromAsset | Should -Be $jqPath
    }
    It "copia jq.exe anche in PortableGit\usr\bin se PortableGit presente" {
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
