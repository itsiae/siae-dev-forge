#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Install-ClaudePlugin" {
    It "ritorna `$true se claude CLI presente + plugin install riesce" {
        Mock Get-Command { [pscustomobject]@{ Source = 'claude.exe' } } -ParameterFilter { $Name -eq 'claude' }
        Mock Invoke-DevForgeCommand { "installed" } -Verifiable
        Install-ClaudePlugin | Should -Be $true
        Should -Invoke Invoke-DevForgeCommand -ParameterFilter {
            $Executable -eq 'claude' -and
            $Arguments -contains 'plugin' -and
            $Arguments -contains 'install' -and
            $Arguments -contains 'siae-devforge@siae-devforge'
        }
    }
    It "ritorna `$false se claude CLI non presente" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'claude' }
        Install-ClaudePlugin | Should -Be $false
    }
}

Describe "Invoke-HealthCheck" {
    BeforeEach {
        $script:testStateDir = Join-Path $env:TEMP "devforge-hc-$(Get-Random)"
        New-Item -ItemType Directory -Path (Join-Path $script:testStateDir 'devforge-state') -Force | Out-Null
        $script:testActivityLog = Join-Path $script:testStateDir 'devforge-activity.jsonl'
    }
    AfterEach {
        Remove-Item -Path $script:testStateDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    It "ritorna `$false se session-start non emette event entro 5s (nessun hook trovato)" {
        Mock Get-ChildItem { @() } -ParameterFilter { $Path -match 'plugins\\cache\\siae-devforge' }
        Invoke-HealthCheck -BashPath 'bash.exe' -PythonPath 'python.exe' | Should -Be $false
    }
    It "ritorna `$false se activity.jsonl non cresce entro deadline" {
        Mock Get-ChildItem {
            @([pscustomobject]@{ FullName = 'C:\fake\plugins\cache\siae-devforge\1.0.0' })
        } -ParameterFilter { $Path -match 'plugins\\cache\\siae-devforge' }
        Mock Test-Path { $true } -ParameterFilter { $Path -match 'session-start' }
        Mock Start-Process { [pscustomobject]@{ ExitCode = 0 } }
        Mock Test-Path { $false } -ParameterFilter { $Path -match 'devforge-activity\.jsonl$' }
        Invoke-HealthCheck -BashPath 'bash.exe' -PythonPath 'python.exe' | Should -Be $false
    }
}
