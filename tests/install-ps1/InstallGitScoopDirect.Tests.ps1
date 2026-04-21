#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Install-GitViaScoop" {
    It "ritorna `$null se scoop non disponibile" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'scoop' }
        Install-GitViaScoop | Should -Be $null
    }
    It "invoca scoop install git" {
        Mock Get-Command { [pscustomobject]@{ Source = 'scoop' } } -ParameterFilter { $Name -eq 'scoop' }
        Mock Invoke-DevForgeCommand { $global:LASTEXITCODE = 0; '' } -Verifiable
        Mock Find-Bash { 'C:\Users\test\scoop\apps\git\current\bin\bash.exe' }
        $result = Install-GitViaScoop
        Should -Invoke Invoke-DevForgeCommand -ParameterFilter {
            $Executable -eq 'scoop' -and $Arguments -contains 'install' -and $Arguments -contains 'git'
        }
        $result | Should -Be 'C:\Users\test\scoop\apps\git\current\bin\bash.exe'
    }
}

Describe "Install-GitViaDirectDownload" {
    BeforeEach {
        $script:tmp = Join-Path $env:TEMP "devforge-test-$(Get-Random)"
        New-Item -ItemType Directory -Path $script:tmp -Force | Out-Null
    }
    AfterEach {
        Remove-Item -Path $script:tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
    It "scarica installer, verifica SHA256, avvia install silent" {
        Mock Invoke-WebRequest { } -Verifiable
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'EXPECTED_SHA256_HASH_UPPERCASE' } }
        Mock Start-Process { [pscustomobject]@{ ExitCode = 0 } } -Verifiable
        Mock Find-Bash { 'C:\Program Files\Git\bin\bash.exe' }
        $script:DevForgeGitDirectSha256 = 'EXPECTED_SHA256_HASH_UPPERCASE'

        $result = Install-GitViaDirectDownload
        Should -Invoke Invoke-WebRequest
        Should -Invoke Start-Process -ParameterFilter {
            $ArgumentList -match '/VERYSILENT' -and
            $ArgumentList -match '/NORESTART' -and
            $ArgumentList -match '/COMPONENTS='
        }
        $result | Should -Be 'C:\Program Files\Git\bin\bash.exe'
    }
    It "abort se SHA256 mismatch" {
        Mock Invoke-WebRequest { }
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'WRONG_HASH' } }
        Mock Start-Process { throw "Should not be called" }
        $script:DevForgeGitDirectSha256 = 'EXPECTED_SHA256_HASH_UPPERCASE'

        Install-GitViaDirectDownload | Should -Be $null
    }
}
