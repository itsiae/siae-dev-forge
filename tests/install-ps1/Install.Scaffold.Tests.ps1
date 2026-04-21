#Requires -Version 5.1
Describe "install.ps1 — scaffold" {
    BeforeAll {
        $script:InstallerPath = Join-Path $PSScriptRoot "..\..\install.ps1"
    }

    It "file installer esiste nella root repo" {
        Test-Path $script:InstallerPath | Should -Be $true
    }

    It "parsing senza errori sintattici (no -Force, no side-effect)" {
        $errors = $null
        [System.Management.Automation.Language.Parser]::ParseFile(
            $script:InstallerPath, [ref]$null, [ref]$errors
        ) | Out-Null
        $errors | Should -BeNullOrEmpty
    }

    It "dichiara [CmdletBinding()] e param block con DryRun/NoPortableFallback/Force" {
        $content = Get-Content $script:InstallerPath -Raw
        $content | Should -Match '\[CmdletBinding\(\)\]'
        $content | Should -Match '\[switch\]\$DryRun'
        $content | Should -Match '\[switch\]\$NoPortableFallback'
        $content | Should -Match '\[switch\]\$Force'
    }

    It "definisce le funzioni pubbliche previste dal design §5.1" {
        $content = Get-Content $script:InstallerPath -Raw
        $expected = @(
            'Find-Bash', 'Find-Python3', 'Find-Jq',
            'Install-GitViaWinget', 'Install-GitViaChoco', 'Install-GitViaScoop',
            'Install-GitViaDirectDownload', 'Install-GitViaPortableEmbedded',
            'Install-PythonViaStandaloneEmbedded', 'Install-JqFromAsset',
            'Install-ClaudePlugin', 'Invoke-HealthCheck',
            'New-InstallSnapshot', 'Invoke-Rollback', 'Write-InstallLog'
        )
        foreach ($fn in $expected) {
            $content | Should -Match "function\s+$fn\s*\{"
        }
    }
}
