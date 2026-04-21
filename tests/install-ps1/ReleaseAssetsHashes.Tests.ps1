#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

# Tag 'Release': regression guard run ONLY on release-built install.ps1 (post
# T12 CI SHA256 substitution). Default Pester run excludes this tag because
# in-tree install.ps1 contains placeholder '0{64}' hashes by design.
Describe "Release asset SHA256 constants" -Tag 'Release' {
    It "DevForgeGitDirectSha256 non e' placeholder zeros" {
        $script:DevForgeGitDirectSha256 | Should -Not -Match '^0{64}$'
        $script:DevForgeGitDirectSha256 | Should -Match '^[0-9A-Fa-f]{64}$'
    }
    It "DevForgePortableGitSha256 non e' placeholder zeros" {
        $script:DevForgePortableGitSha256 | Should -Not -Match '^0{64}$'
        $script:DevForgePortableGitSha256 | Should -Match '^[0-9A-Fa-f]{64}$'
    }
    It "DevForgePythonSha256 non e' placeholder zeros" {
        $script:DevForgePythonSha256 | Should -Not -Match '^0{64}$'
        $script:DevForgePythonSha256 | Should -Match '^[0-9A-Fa-f]{64}$'
    }
    It "DevForgeJqSha256 non e' placeholder zeros" {
        $script:DevForgeJqSha256 | Should -Not -Match '^0{64}$'
        $script:DevForgeJqSha256 | Should -Match '^[0-9A-Fa-f]{64}$'
    }
}
