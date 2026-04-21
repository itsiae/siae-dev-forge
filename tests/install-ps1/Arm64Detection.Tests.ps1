#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Test-IsArm64" {
    It "ritorna true se PROCESSOR_ARCHITEW6432=ARM64" {
        $env:PROCESSOR_ARCHITEW6432 = 'ARM64'
        try { Test-IsArm64 | Should -Be $true }
        finally { Remove-Item Env:PROCESSOR_ARCHITEW6432 -ErrorAction SilentlyContinue }
    }
    It "ritorna true se PROCESSOR_ARCHITECTURE=ARM64 e AREW6432 non settato" {
        Remove-Item Env:PROCESSOR_ARCHITEW6432 -ErrorAction SilentlyContinue
        $env:PROCESSOR_ARCHITECTURE = 'ARM64'
        try { Test-IsArm64 | Should -Be $true }
        finally { $env:PROCESSOR_ARCHITECTURE = 'AMD64' }
    }
    It "ritorna false su AMD64" {
        Remove-Item Env:PROCESSOR_ARCHITEW6432 -ErrorAction SilentlyContinue
        $env:PROCESSOR_ARCHITECTURE = 'AMD64'
        Test-IsArm64 | Should -Be $false
    }
    It "ritorna false su x86 (PROCESSOR_ARCHITEW6432 AMD64 indica emulazione su x64)" {
        $env:PROCESSOR_ARCHITEW6432 = 'AMD64'
        $env:PROCESSOR_ARCHITECTURE = 'x86'
        try { Test-IsArm64 | Should -Be $false }
        finally { Remove-Item Env:PROCESSOR_ARCHITEW6432 -ErrorAction SilentlyContinue }
    }
}
