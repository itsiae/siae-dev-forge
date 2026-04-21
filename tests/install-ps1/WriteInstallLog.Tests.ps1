#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Write-InstallLog" {
    BeforeEach {
        $script:testLogFile = Join-Path $env:TEMP "devforge-test-log-$(Get-Random).log"
        $script:DevForgeLogFile = $script:testLogFile
    }
    AfterEach {
        Remove-Item -Path $script:testLogFile -ErrorAction SilentlyContinue
    }

    It "crea directory log se non esiste" {
        $dir = Split-Path $script:testLogFile -Parent
        Write-InstallLog -Message "test" -Level Info
        Test-Path $dir | Should -Be $true
    }
    It "scrive riga timestamped con level in file log" {
        Write-InstallLog -Message "primo messaggio" -Level Info
        $content = Get-Content $script:testLogFile
        $content | Should -Match '\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\]'
        $content | Should -Match '\[INFO\]'
        $content | Should -Match 'primo messaggio'
    }
    It "accetta level Warning e Error" {
        Write-InstallLog -Message "warn msg" -Level Warning
        Write-InstallLog -Message "err msg" -Level Error
        $content = Get-Content $script:testLogFile -Raw
        $content | Should -Match '\[WARNING\].*warn msg'
        $content | Should -Match '\[ERROR\].*err msg'
    }
    It "default level è Info" {
        Write-InstallLog -Message "default"
        Get-Content $script:testLogFile -Raw | Should -Match '\[INFO\].*default'
    }
    It "scrive anche a Console (Write-Host) con colore per Error" {
        Mock Write-Host { } -Verifiable
        Write-InstallLog -Message "test" -Level Error
        Should -Invoke Write-Host -ParameterFilter { $ForegroundColor -eq 'Red' }
    }
}

Describe "DryRun mode" {
    It "quando `$script:DevForgeDryRun è true, Invoke-Expression NON viene eseguito" {
        $script:DevForgeDryRun = $true
        Mock Invoke-Expression { throw "should not run in dry-run" }
        try {
            { Invoke-DevForgeCommand -Command 'fake-cmd' } | Should -Not -Throw
        } finally {
            $script:DevForgeDryRun = $false
        }
    }
    It "quando DryRun false, esegue normalmente" {
        $script:DevForgeDryRun = $false
        Mock Invoke-Expression { 'ok' } -Verifiable
        Invoke-DevForgeCommand -Command 'fake-cmd' | Out-Null
        Should -Invoke Invoke-Expression
    }
}
