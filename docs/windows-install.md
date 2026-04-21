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

Per verificare cosa farà senza eseguire nulla, scarica prima lo script e invocalo con `-DryRun`:

```powershell
iwr https://github.com/itsiae/siae-dev-forge/releases/latest/download/install.ps1 -OutFile $env:TEMP\install.ps1
& $env:TEMP\install.ps1 -DryRun
```

Il DryRun logga ogni azione in `%LOCALAPPDATA%\DevForge\install.log` senza eseguirla.

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

Contiene ogni azione timestamped ISO-8601Z con severity (INFO/WARNING/ERROR):

```
[2026-04-21T14:32:01Z] [INFO] Tentativo install Git via winget...
[2026-04-21T14:32:15Z] [INFO] Git installato via winget: C:\Program Files\Git\bin\bash.exe
[2026-04-21T14:32:16Z] [INFO] SHA256 verificato: A1B2C3...
```

## Limiti noti

- **ARM64:** install non supportato nativamente. Il design doc §1.4 documenta il motivo (nessun dev SIAE noto su ARM64 nativo al 2026-04-21).
- **Code-signing:** `install.ps1` non è firmato Authenticode. Windows SmartScreen può mostrare warning. Documentato come follow-up se friction alta.

## Ripristino post-broken

Se il tuo ambiente diventa broken (bash disinstallato, AV quarantine), rilancia l'one-liner:

```powershell
iwr https://github.com/itsiae/siae-dev-forge/releases/latest/download/install.ps1 -UseBasicParsing | iex
```

L'installer è idempotente: rileva cosa c'è, ripara il mancante.
