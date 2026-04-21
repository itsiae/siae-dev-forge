#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

# Coverage AC-9: verify DryRun mode bypasses side effects (Invoke-WebRequest,
# Start-Process, Remove-Item, New-Item, Copy-Item) in every install function
# that does NOT route through Invoke-DevForgeCommand splat. Without these
# early-returns, -DryRun would still download binaries and run installers.

Describe "DryRun coverage -- install functions that bypass Invoke-DevForgeCommand" {
    BeforeEach { $script:DevForgeDryRun = $true }
    AfterEach  { $script:DevForgeDryRun = $false }

    It "Install-GitViaDirectDownload returns canonical path without web/FS side effects" {
        Mock Invoke-WebRequest { throw "should not run in dry-run" }
        Mock Start-Process { throw "should not run in dry-run" }
        Mock New-Item { throw "should not run in dry-run" }
        Install-GitViaDirectDownload | Should -Be 'C:\Program Files\Git\bin\bash.exe'
    }

    It "Install-GitViaPortableEmbedded returns canonical path without side effects" {
        Mock Invoke-WebRequest { throw "should not run in dry-run" }
        Mock Start-Process { throw "should not run in dry-run" }
        $expected = Join-Path $env:LOCALAPPDATA 'DevForge\PortableGit\bin\bash.exe'
        Install-GitViaPortableEmbedded | Should -Be $expected
    }

    It "Install-GitViaPortableEmbedded respects -NoPortableFallback even in DryRun" {
        Mock Write-InstallLog { }
        Install-GitViaPortableEmbedded -NoPortableFallback | Should -Be $null
    }

    It "Install-PythonViaStandaloneEmbedded returns canonical path without side effects" {
        Mock Invoke-WebRequest { throw "should not run in dry-run" }
        Mock Start-Process { throw "should not run in dry-run" }
        $expected = Join-Path $env:LOCALAPPDATA 'DevForge\python\python.exe'
        Install-PythonViaStandaloneEmbedded | Should -Be $expected
    }

    It "Install-JqFromAsset returns canonical path without side effects" {
        Mock Invoke-WebRequest { throw "should not run in dry-run" }
        Mock Copy-Item { throw "should not run in dry-run" }
        Mock New-Item { throw "should not run in dry-run" }
        $expected = Join-Path $env:LOCALAPPDATA 'DevForge\bin\jq.exe'
        Install-JqFromAsset | Should -Be $expected
    }

    It "Invoke-HealthCheck returns true in DryRun without spawning hook" {
        Mock Start-Process { throw "should not run in dry-run" }
        Mock Get-ChildItem { throw "should not run in dry-run" }
        Invoke-HealthCheck -BashPath 'bash.exe' -PythonPath 'python.exe' | Should -Be $true
    }
}
