#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Install-GitViaWinget" {
    It "ritorna `$null se winget non e' disponibile" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'winget' }
        Install-GitViaWinget | Should -Be $null
    }
    It "invoca winget install Git.Git con scope user e flags silent" {
        Mock Get-Command { [pscustomobject]@{ Source = 'winget.exe' } } -ParameterFilter { $Name -eq 'winget' }
        Mock Invoke-DevForgeCommand { '' } -Verifiable
        Mock Find-Bash { 'C:\Program Files\Git\bin\bash.exe' }
        $result = Install-GitViaWinget
        Should -Invoke Invoke-DevForgeCommand -ParameterFilter {
            $Executable -eq 'winget' -and
            $Arguments -contains 'install' -and
            $Arguments -contains 'Git.Git' -and
            $Arguments -contains '--scope' -and
            $Arguments -contains 'user' -and
            $Arguments -contains '--silent' -and
            $Arguments -contains '--accept-source-agreements' -and
            $Arguments -contains '--accept-package-agreements'
        }
        $result | Should -Be 'C:\Program Files\Git\bin\bash.exe'
    }
    It "tratta exit code 1978335224 (already installed) come success" {
        Mock Get-Command { [pscustomobject]@{ Source = 'winget.exe' } } -ParameterFilter { $Name -eq 'winget' }
        Mock Invoke-DevForgeCommand { $global:LASTEXITCODE = 1978335224; '' }
        Mock Find-Bash { 'C:\Program Files\Git\bin\bash.exe' }
        Install-GitViaWinget | Should -Be 'C:\Program Files\Git\bin\bash.exe'
    }
    It "ritorna `$null su exit code non-zero non-noto + bash ancora assente" {
        Mock Get-Command { [pscustomobject]@{ Source = 'winget.exe' } } -ParameterFilter { $Name -eq 'winget' }
        Mock Invoke-DevForgeCommand { $global:LASTEXITCODE = 1; '' }
        Mock Find-Bash { $null }
        Install-GitViaWinget | Should -Be $null
    }
}

Describe "Install-GitViaChoco" {
    It "ritorna `$null se choco non disponibile" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'choco' }
        Install-GitViaChoco | Should -Be $null
    }
    It "invoca choco install git -y --no-progress" {
        Mock Get-Command { [pscustomobject]@{ Source = 'choco.exe' } } -ParameterFilter { $Name -eq 'choco' }
        Mock Invoke-DevForgeCommand { $global:LASTEXITCODE = 0; '' } -Verifiable
        Mock Find-Bash { 'C:\Program Files\Git\bin\bash.exe' }
        Install-GitViaChoco | Should -Be 'C:\Program Files\Git\bin\bash.exe'
        Should -Invoke Invoke-DevForgeCommand -ParameterFilter {
            $Executable -eq 'choco' -and
            $Arguments -contains 'install' -and
            $Arguments -contains 'git' -and
            $Arguments -contains '-y' -and
            $Arguments -contains '--no-progress'
        }
    }
}
