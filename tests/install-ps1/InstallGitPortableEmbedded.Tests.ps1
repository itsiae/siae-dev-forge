#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Install-GitViaPortableEmbedded" {
    BeforeEach { $script:DevForgePortableGitSha256 = 'EXPECTED_HASH' }

    It "scarica asset dal release plugin, verifica SHA256, estrae in LOCALAPPDATA" {
        Mock Invoke-WebRequest { } -Verifiable
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'EXPECTED_HASH' } }
        Mock Start-Process { [pscustomobject]@{ ExitCode = 0 } } -Verifiable
        $portableBash = Join-Path $env:LOCALAPPDATA 'DevForge\PortableGit\bin\bash.exe'
        Mock Test-Path { $true } -ParameterFilter { $Path -eq $portableBash }

        $result = Install-GitViaPortableEmbedded
        $result | Should -Be $portableBash
        Should -Invoke Invoke-WebRequest -ParameterFilter {
            $Uri -match 'itsiae/siae-dev-forge/releases' -and
            $Uri -match 'PortableGit-x64\.7z\.exe'
        }
        Should -Invoke Start-Process -ParameterFilter {
            $ArgumentList -match '-o' -and
            $ArgumentList -match '-y'
        }
    }
    It "abort su SHA256 mismatch" {
        Mock Invoke-WebRequest { }
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'WRONG' } }
        Mock Start-Process { throw "should not run" }
        Install-GitViaPortableEmbedded | Should -Be $null
    }
    It "skip se NoPortableFallback switch attivo" {
        Mock Invoke-WebRequest { throw "should not be invoked" }
        Install-GitViaPortableEmbedded -NoPortableFallback | Should -Be $null
    }
}
