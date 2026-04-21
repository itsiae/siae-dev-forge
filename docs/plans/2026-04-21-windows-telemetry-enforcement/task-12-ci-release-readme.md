# Task 12 — CI release packaging + README Windows + panic button docs

**PR:** PR-1 | **SP:** 0.5 SP-Augmented | **Dipendenze:** T06, T07 | **Stato:** [PENDING]

## File coinvolti

- `.github/workflows/auto-release.yml` (modifica: aggiungi step upload asset Windows)
- `scripts/build-windows-assets.sh` (nuovo — scarica upstream e produce SHA256SUMS)
- `docs/windows-install.md` (nuovo — README utente Windows + one-liner + troubleshooting panic buttons)
- `tests/install-ps1/ReleaseAssetsHashes.Tests.ps1` (nuovo — verifica che constanti SHA nel install.ps1 siano settate)

## Versioni upstream pinned

- Git for Windows: v2.46.0 (PortableGit-2.46.0-64-bit.7z.exe)
- Python-Standalone (indygreg): cpython-3.12.3+20240415-x86_64-pc-windows-msvc-shared-install_only.tar.gz
- jq: v1.7.1 (jq-windows-amd64.exe)

## Step 1 — Test RED

File: `tests/install-ps1/ReleaseAssetsHashes.Tests.ps1`

```powershell
#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Release asset SHA256 constants" {
    It "DevForgeGitDirectSha256 non è placeholder zeros" {
        $script:DevForgeGitDirectSha256 | Should -Not -Match '^0{64}$'
        $script:DevForgeGitDirectSha256 | Should -Match '^[0-9A-Fa-f]{64}$'
    }
    It "DevForgePortableGitSha256 non è placeholder zeros" {
        $script:DevForgePortableGitSha256 | Should -Not -Match '^0{64}$'
    }
    It "DevForgePythonSha256 non è placeholder zeros" {
        $script:DevForgePythonSha256 | Should -Not -Match '^0{64}$'
    }
    It "DevForgeJqSha256 non è placeholder zeros" {
        $script:DevForgeJqSha256 | Should -Not -Match '^0{64}$'
    }
}
```

## Step 2 — Run (RED)

```powershell
Invoke-Pester tests/install-ps1/ReleaseAssetsHashes.Tests.ps1
# Atteso: 4 Failed (constants sono ancora "0000...")
```

## Step 3 — Impl

### 3a. Script scarica asset upstream

File: `scripts/build-windows-assets.sh`

```bash
#!/usr/bin/env bash
# Scarica asset upstream x64, calcola SHA256, popola SHA256SUMS.
# Usage: scripts/build-windows-assets.sh <output-dir>
set -euo pipefail

OUT="${1:-dist/windows-assets}"
mkdir -p "$OUT"

GIT_VERSION="2.46.0"
PYTHON_TAG="20240415"
PYTHON_FULL_VERSION="3.12.3"
JQ_VERSION="1.7.1"

download_verify() {
    local url="$1" out="$2"
    echo "→ $url"
    curl -sfL -o "$out" "$url" || { echo "Download $url failed"; exit 1; }
}

# Git installer (per direct-download path)
download_verify \
  "https://github.com/git-for-windows/git/releases/download/v${GIT_VERSION}.windows.1/Git-${GIT_VERSION}-64-bit.exe" \
  "$OUT/Git-${GIT_VERSION}-64-bit.exe"

# PortableGit SFX (per fallback embedded)
download_verify \
  "https://github.com/git-for-windows/git/releases/download/v${GIT_VERSION}.windows.1/PortableGit-${GIT_VERSION}-64-bit.7z.exe" \
  "$OUT/PortableGit-x64.7z.exe"

# Python Standalone (indygreg)
download_verify \
  "https://github.com/indygreg/python-build-standalone/releases/download/${PYTHON_TAG}/cpython-${PYTHON_FULL_VERSION}+${PYTHON_TAG}-x86_64-pc-windows-msvc-shared-install_only.tar.gz" \
  "$OUT/python-standalone-x64.tar.gz"

# jq binary (official)
download_verify \
  "https://github.com/jqlang/jq/releases/download/jq-${JQ_VERSION}/jq-windows-amd64.exe" \
  "$OUT/jq-win64.exe"

# Genera SHA256SUMS
(cd "$OUT" && sha256sum *.exe *.tar.gz > SHA256SUMS)
cat "$OUT/SHA256SUMS"

echo "Asset pronti in $OUT"
```

### 3b. Workflow auto-release: aggiungi step

Modifica `.github/workflows/auto-release.yml` — aggiungi job **prima** del release:

```yaml
  build-windows-assets:
    runs-on: ubuntu-latest
    outputs:
      sha_git_direct: ${{ steps.hashes.outputs.sha_git_direct }}
      sha_portable_git: ${{ steps.hashes.outputs.sha_portable_git }}
      sha_python: ${{ steps.hashes.outputs.sha_python }}
      sha_jq: ${{ steps.hashes.outputs.sha_jq }}
    steps:
      - uses: actions/checkout@v4
      - name: Build windows assets
        run: bash scripts/build-windows-assets.sh dist/windows-assets
      - name: Compute hashes for install.ps1 substitution
        id: hashes
        run: |
          cd dist/windows-assets
          echo "sha_git_direct=$(sha256sum Git-*-64-bit.exe | cut -d' ' -f1)" >> $GITHUB_OUTPUT
          echo "sha_portable_git=$(sha256sum PortableGit-x64.7z.exe | cut -d' ' -f1)" >> $GITHUB_OUTPUT
          echo "sha_python=$(sha256sum python-standalone-x64.tar.gz | cut -d' ' -f1)" >> $GITHUB_OUTPUT
          echo "sha_jq=$(sha256sum jq-win64.exe | cut -d' ' -f1)" >> $GITHUB_OUTPUT
      - name: Substitute SHA placeholders in install.ps1
        run: |
          sed -i "s/DevForgeGitDirectSha256  = '0\{64\}'/DevForgeGitDirectSha256  = '${{ steps.hashes.outputs.sha_git_direct }}'/" install.ps1
          sed -i "s/DevForgePortableGitSha256 = '0\{64\}'/DevForgePortableGitSha256 = '${{ steps.hashes.outputs.sha_portable_git }}'/" install.ps1
          sed -i "s/DevForgePythonSha256 = '0\{64\}'/DevForgePythonSha256 = '${{ steps.hashes.outputs.sha_python }}'/" install.ps1
          sed -i "s/DevForgeJqSha256 = '0\{64\}'/DevForgeJqSha256 = '${{ steps.hashes.outputs.sha_jq }}'/" install.ps1
      - uses: actions/upload-artifact@v4
        with:
          name: windows-assets
          path: |
            dist/windows-assets/PortableGit-x64.7z.exe
            dist/windows-assets/python-standalone-x64.tar.gz
            dist/windows-assets/jq-win64.exe
            dist/windows-assets/SHA256SUMS
            install.ps1
```

E al job di release esistente, aggiungi:
```yaml
      - uses: actions/download-artifact@v4
        with:
          name: windows-assets
          path: dist/windows-assets
      - name: Upload windows assets to release
        run: |
          gh release upload ${{ github.ref_name }} \
            dist/windows-assets/PortableGit-x64.7z.exe \
            dist/windows-assets/python-standalone-x64.tar.gz \
            dist/windows-assets/jq-win64.exe \
            dist/windows-assets/SHA256SUMS \
            dist/windows-assets/install.ps1 \
            --clobber
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 3c. README Windows

File: `docs/windows-install.md`

```markdown
# DevForge su Windows — Install & Troubleshooting

## Install one-liner (PowerShell)

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
iwr https://github.com/itsiae/siae-dev-forge/releases/latest/download/install.ps1 -UseBasicParsing | iex
```

L'installer:
1. Rileva bash/python3/jq esistenti
2. Se mancanti, installa via winget → choco → scoop → direct download → asset embedded
3. Installa plugin DevForge via `claude plugin install`
4. Esegue health-check (dry-run session-start + verifica event in `~/.claude/devforge-activity.jsonl`)
5. Rollback automatico su failure

## Prerequisiti

- Windows 10 1803+ o Windows 11 (x64). **ARM64 nativo non supportato** — usa emulazione x64.
- Claude Code installato (https://docs.anthropic.com/en/docs/build-with-claude/claude-code)
- Connessione Internet (primo install). Air-gapped ok via asset embedded.

## Dry-run

Per verificare cosa farà senza eseguire nulla:

```powershell
iwr <url>/install.ps1 -UseBasicParsing | iex -DryRun
```

## Panic buttons — env vars troubleshooting

Se qualcosa va storto post-install, puoi disabilitare componenti selettivamente:

| Env var | Effetto |
|---|---|
| `$env:DEVFORGE_DISABLE_REPAIR_EVENT='1'` | `emit-repair-event.ps1` non scrive più l'event `repair_needed`. Usa se l'event corrompe la pipeline. |
| `$env:DEVFORGE_SILENT_ON_NO_BASH='1'` | `run-hook.cmd` ripristina vecchio comportamento `exit /b 0` silent. Usa se sei broken ma non puoi riparare subito e vuoi silenziare stderr. |
| `$env:DEVFORGE_HIDE_REPAIR_BANNER='1'` | `session-start` non mostra il repair banner nel context del model. Usa se banner ridondante in loop. |

Per rendere permanenti, settale a livello User:

```powershell
[Environment]::SetEnvironmentVariable('DEVFORGE_SILENT_ON_NO_BASH', '1', 'User')
```

## Log installer

Path log: `%LOCALAPPDATA%\DevForge\install.log`

## Limiti noti

- **ARM64:** install non supportato nativamente. Il design doc §1.4 documenta il motivo (nessun dev SIAE noto su ARM64 nativo al 2026-04-21).
- **Code-signing:** `install.ps1` non è firmato Authenticode. Windows SmartScreen può mostrare warning. Documentato come follow-up se friction alta.

## Ripristino post-broken

Se il tuo ambiente diventa broken (bash disinstallato, AV quarantine), rilancia l'one-liner:

```powershell
iwr https://github.com/itsiae/siae-dev-forge/releases/latest/download/install.ps1 -UseBasicParsing | iex
```

L'installer è idempotente: rileva cosa c'è, ripara il mancante.
```

## Step 4 — Run (GREEN)

```bash
# Su macchina dev
bash scripts/build-windows-assets.sh /tmp/test-assets
cat /tmp/test-assets/SHA256SUMS

# Sostituisci manualmente le constanti SHA in install.ps1 con i valori calcolati
# (o lascia che CI lo faccia al release)

# Poi in Pester:
Invoke-Pester tests/install-ps1/ReleaseAssetsHashes.Tests.ps1
# Atteso: 4/4 Passed (SHA non sono più "0000..." in release)
```

## Step 5 — Commit

```bash
git add .github/workflows/auto-release.yml scripts/build-windows-assets.sh docs/windows-install.md tests/install-ps1/ReleaseAssetsHashes.Tests.ps1
git commit -m "chore(windows): CI release packaging + README + panic buttons docs [AC-11, AC-17]"
```
