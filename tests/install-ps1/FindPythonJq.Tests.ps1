#Requires -Version 5.1
BeforeAll {
    . (Join-Path $PSScriptRoot "..\..\install.ps1")
}

Describe "Find-Python3" {
    It "trova py.exe launcher (Windows default)" {
        Mock Get-Command { [pscustomobject]@{ Source = 'C:\Windows\py.exe' } } -ParameterFilter { $Name -eq 'py' }
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'python3' }
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'python' }
        Find-Python3 | Should -Be 'C:\Windows\py.exe'
    }
    It "cade a python3.exe PATH" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'py' }
        Mock Get-Command { [pscustomobject]@{ Source = 'C:\Python312\python3.exe' } } -ParameterFilter { $Name -eq 'python3' }
        Find-Python3 | Should -Be 'C:\Python312\python3.exe'
    }
    It "cade a python.exe PATH se e' v3+" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'py' -or $Name -eq 'python3' }
        Mock Get-Command { [pscustomobject]@{ Source = 'C:\Python312\python.exe' } } -ParameterFilter { $Name -eq 'python' }
        Mock Invoke-DevForgeCommand { 'Python 3.12.0' } -ParameterFilter { $Executable -match 'python\.exe$' -and $Arguments -contains '--version' }
        Find-Python3 | Should -Be 'C:\Python312\python.exe'
    }
    It "ignora python.exe v2.x" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'py' -or $Name -eq 'python3' }
        Mock Get-Command { [pscustomobject]@{ Source = 'C:\Python27\python.exe' } } -ParameterFilter { $Name -eq 'python' }
        Mock Invoke-DevForgeCommand { 'Python 2.7.18' } -ParameterFilter { $Executable -match 'python\.exe$' -and $Arguments -contains '--version' }
        Mock Test-Path { $false }
        Find-Python3 | Should -Be $null
    }
    It "cerca cache locale DevForge se PATH vuoto" {
        Mock Get-Command { $null }
        $cachePath = Join-Path $env:LOCALAPPDATA 'DevForge\python\python.exe'
        Mock Test-Path { $Path -eq $cachePath }
        Find-Python3 | Should -Be $cachePath
    }
    It "restituisce `$null se niente trovato" {
        Mock Get-Command { $null }
        Mock Test-Path { $false }
        Find-Python3 | Should -Be $null
    }
}

Describe "Find-Jq" {
    It "trova jq in PATH" {
        Mock Get-Command { [pscustomobject]@{ Source = 'C:\tools\jq.exe' } } -ParameterFilter { $Name -eq 'jq' }
        Find-Jq | Should -Be 'C:\tools\jq.exe'
    }
    It "cerca in PortableGit\usr\bin se bash e' PortableGit" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'jq' }
        $portablePath = Join-Path $env:LOCALAPPDATA 'DevForge\PortableGit\usr\bin\jq.exe'
        Mock Test-Path { $Path -eq $portablePath }
        Find-Jq | Should -Be $portablePath
    }
    It "cerca cache locale DevForge" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'jq' }
        $cachePath = Join-Path $env:LOCALAPPDATA 'DevForge\bin\jq.exe'
        Mock Test-Path { $Path -eq $cachePath }
        Find-Jq | Should -Be $cachePath
    }
    It "restituisce `$null se niente trovato" {
        Mock Get-Command { $null }
        Mock Test-Path { $false }
        Find-Jq | Should -Be $null
    }
}
