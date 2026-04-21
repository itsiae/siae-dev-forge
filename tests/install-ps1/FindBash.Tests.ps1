#Requires -Version 5.1
BeforeAll {
    . (Join-Path $PSScriptRoot "..\..\install.ps1")
}

Describe "Find-Bash -- 8-path detection" {
    It "restituisce path se bash in C:\Program Files\Git\bin\bash.exe" {
        Mock Test-Path { $Path -eq 'C:\Program Files\Git\bin\bash.exe' }
        Find-Bash | Should -Be 'C:\Program Files\Git\bin\bash.exe'
    }
    It "cade a (x86)\Git se Program Files assente" {
        Mock Test-Path { $Path -eq 'C:\Program Files (x86)\Git\bin\bash.exe' }
        Find-Bash | Should -Be 'C:\Program Files (x86)\Git\bin\bash.exe'
    }
    It "cade a LOCALAPPDATA user-scope install" {
        $userPath = Join-Path $env:LOCALAPPDATA 'Programs\Git\bin\bash.exe'
        Mock Test-Path { $Path -eq $userPath }
        Find-Bash | Should -Be $userPath
    }
    It "cade a scoop" {
        $scoopPath = Join-Path $env:USERPROFILE 'scoop\apps\git\current\bin\bash.exe'
        Mock Test-Path { $Path -eq $scoopPath }
        Find-Bash | Should -Be $scoopPath
    }
    It "cade a MSYS2" {
        Mock Test-Path { $Path -eq 'C:\msys64\usr\bin\bash.exe' }
        Find-Bash | Should -Be 'C:\msys64\usr\bin\bash.exe'
    }
    It "cade a Cygwin" {
        Mock Test-Path { $Path -eq 'C:\cygwin64\bin\bash.exe' }
        Find-Bash | Should -Be 'C:\cygwin64\bin\bash.exe'
    }
    It "cade a PATH lookup via Get-Command" {
        Mock Test-Path { $false }
        Mock Get-Command { [pscustomobject]@{ Source = 'D:\custom\bash.exe' } } -ParameterFilter { $Name -eq 'bash' }
        Find-Bash | Should -Be 'D:\custom\bash.exe'
    }
    It "restituisce `$null se nessun path valido" {
        Mock Test-Path { $false }
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'bash' }
        Find-Bash | Should -Be $null
    }
}
