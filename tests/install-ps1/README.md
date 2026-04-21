# Pester tests per install.ps1

## Esecuzione locale (Windows)

```powershell
Install-Module Pester -MinimumVersion 5.5.0 -Force -SkipPublisherCheck
Invoke-Pester tests/install-ps1
```

## CI

I test girano automaticamente su `windows-latest` + `windows-2019` via `.github/workflows/test-windows-enforcement.yml`.
