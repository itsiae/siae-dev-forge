#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "New-InstallSnapshot" {
    It "ritorna oggetto con collezioni vuote TrackedFiles/TrackedDirs/TrackedRegistry/TrackedTasks" {
        $s = New-InstallSnapshot
        $s.TrackedFiles | Should -BeNullOrEmpty
        $s.TrackedDirs | Should -BeNullOrEmpty
        $s.TrackedRegistry | Should -BeNullOrEmpty
        $s.TrackedTasks | Should -BeNullOrEmpty
        $s.Timestamp | Should -Not -BeNullOrEmpty
    }
    It "espone i membri AddFile AddDir AddRegistry AddTask" {
        $s = New-InstallSnapshot
        $s.AddFile('C:\foo\bar.txt')
        $s.AddDir('C:\foo')
        $s.AddRegistry('HKCU:\Software\DevForge', 'InstallDate')
        $s.AddTask('DevForgeCanary')
        $s.TrackedFiles.Count | Should -Be 1
        $s.TrackedDirs.Count | Should -Be 1
        $s.TrackedRegistry.Count | Should -Be 1
        $s.TrackedTasks.Count | Should -Be 1
    }
}

Describe "Invoke-Rollback" {
    It "rimuove file tracciati in ordine inverso" {
        $tmp = Join-Path $env:TEMP "devforge-rb-$(Get-Random)"
        New-Item -ItemType Directory -Path $tmp -Force | Out-Null
        $f1 = Join-Path $tmp 'file1.txt'; $f2 = Join-Path $tmp 'file2.txt'
        Set-Content -Path $f1 -Value 'a'; Set-Content -Path $f2 -Value 'b'

        $s = New-InstallSnapshot
        $s.AddFile($f1); $s.AddFile($f2)

        Invoke-Rollback -Snapshot $s

        Test-Path $f1 | Should -Be $false
        Test-Path $f2 | Should -Be $false
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
    It "rimuove directory tracciate solo se vuote" {
        $tmp = Join-Path $env:TEMP "devforge-rb-$(Get-Random)"
        New-Item -ItemType Directory -Path $tmp -Force | Out-Null
        $emptyDir = Join-Path $tmp 'empty'; New-Item -ItemType Directory -Path $emptyDir | Out-Null

        $s = New-InstallSnapshot
        $s.AddDir($emptyDir)
        Invoke-Rollback -Snapshot $s

        Test-Path $emptyDir | Should -Be $false
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
    It "rimuove scheduled task via Unregister-ScheduledTask" {
        Mock Unregister-ScheduledTask { } -Verifiable
        Mock Get-ScheduledTask { [pscustomobject]@{ TaskName = 'DevForgeCanary' } }
        $s = New-InstallSnapshot
        $s.AddTask('DevForgeCanary')
        Invoke-Rollback -Snapshot $s
        Should -Invoke Unregister-ScheduledTask
    }
    It "logga ogni step di rollback via Write-InstallLog" {
        Mock Write-InstallLog { } -Verifiable
        $s = New-InstallSnapshot
        Invoke-Rollback -Snapshot $s
        Should -Invoke Write-InstallLog -ParameterFilter { $Message -match 'Rollback' }
    }
}
