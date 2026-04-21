# Windows Telemetry Enforcement — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: usa `siae-subagent-development` (questa sessione) o `siae-executing-plans` (sessione separata) per implementare task per task in pattern TDD.

**Goal:** garantire che ogni dev Windows SIAE emetta i log telemetria DevForge esistenti (`session_start`, `session_end`, `commit_created`, `skill_invoked`, `pr_merged`) identici a Mac/Linux, installando bash+python3+jq via installer PowerShell bulletproof + fail-loud runtime + repair event su bash mancante.

**Architettura:** `install.ps1` entry point → detection chain 8-path per bash/python3/jq → install chain cascade (winget → choco → scoop → direct download GitHub release → PortableGit+Python-Standalone+jq embedded x64 dal release asset del plugin) → health-check dry-run → rollback transazionale su failure. A runtime: `hooks/run-hook.cmd` fail-loud su bash mancante + `hooks/emit-repair-event.ps1` emette 1 event schema v2 canonico in `.global-outbox/batch-<ns>-emergency.jsonl` (drain automatico dal loop `devforge_upload_backlog` esistente senza modifiche agli uploader).

**Stack:** PowerShell 5.1+ (compatibile Windows 10/11), Pester 5 per unit test PS, bats per bash test, GitHub Actions matrix `windows-latest` + `windows-2019` + `ubuntu-latest` + `macos-latest`.

**SP:** 6 SP-Umano / 2.5 SP-Augmented.

**Design doc:** `docs/plans/2026-04-21-windows-telemetry-enforcement-design.md` (commit `fbb346c` su branch `feat/windows-telemetry-enforcement`). APPROVED da spec-reviewer iter-2 (0 BLOCK, 0 WARN).

**Branch:** `feat/windows-telemetry-enforcement` (già creato da `main` aggiornato).

---

## Indice Task

### PR-1 — install.ps1 + CI release packaging (5 SP-U / 2 SP-A)

| # | Task | File | Stato |
|---|------|------|-------|
| 01 | Scaffold install.ps1 + Pester harness + CI workflow Windows matrix | `task-01-scaffold-install-ps1.md` | [DONE] (c497233+a939c1f) |
| 02 | Find-Bash — detection chain 8-path | `task-02-find-bash.md` | [DONE] (6fcc5be) |
| 03 | Find-Python3 + Find-Jq — py launcher + PATH + cache locale | `task-03-find-python-jq.md` | [DONE] (fcbbf67) |
| 04 | Install-GitViaWinget + Install-GitViaChoco | `task-04-install-git-winget-choco.md` | [PENDING] |
| 05 | Install-GitViaScoop + Install-GitViaDirectDownload (SHA256 pin) | `task-05-install-git-scoop-direct.md` | [PENDING] |
| 06 | Install-GitViaPortableEmbedded (SFX extract dal release asset) | `task-06-install-git-portable-embedded.md` | [PENDING] |
| 07 | Install-PythonViaStandaloneEmbedded + Install-JqFromAsset | `task-07-install-python-jq-embedded.md` | [PENDING] |
| 08 | ARM64 detection (PROCESSOR_ARCHITEW6432) + messaggio rinvio x64 | `task-08-arm64-detection.md` | [PENDING] |
| 09 | Dry-Run mode + Write-InstallLog | `task-09-dry-run-log.md` | [DONE] (974a6e8+30115f2) |
| 10 | Snapshot + Rollback transazionale | `task-10-snapshot-rollback.md` | [PENDING] |
| 11 | Install-ClaudePlugin + Invoke-HealthCheck (dry-run session-start + verify jsonl) | `task-11-plugin-healthcheck.md` | [PENDING] |
| 12 | CI release packaging workflow + README Windows + panic button docs | `task-12-ci-release-readme.md` | [PENDING] |

### PR-2 — runtime (1 SP-U / 0.5 SP-A)

| # | Task | File | Stato |
|---|------|------|-------|
| 13 | `hooks/emit-repair-event.ps1` + Pester tests schema v2 | `task-13-emit-repair-event.md` | [PENDING] |
| 14 | Schema validator harness (bash fixture + Pester byte-diff vs logger.sh) | `task-14-schema-validator.md` | [PENDING] |
| 15 | `hooks/run-hook.cmd` fail-loud + DEVFORGE_SILENT_ON_NO_BASH escape hatch | `task-15-run-hook-cmd-fail-loud.md` | [PENDING] |
| 16 | `hooks/lib/repair-banner.sh` isolato + source in `session-start` | `task-16-session-start-banner.md` | [PENDING] |

---

## Dipendenze

**PR-1 ordine sequenziale:**
- T01 (scaffold + CI + Pester harness) → prerequisite per tutti
- T02, T03 (detection) parallelizzabili dopo T01
- T04, T05, T06, T07 (install chain bash/python/jq) parallelizzabili dopo T02/T03
- T08 (ARM64) indipendente, può partire dopo T01
- T09 (DryRun+log) indipendente, può partire dopo T01
- T10 (snapshot+rollback) dopo T09 (usa Write-InstallLog)
- T11 (plugin+healthcheck) dopo T02-T10 (integrazione finale)
- T12 (CI release) può partire in parallelo a T01; completabile solo dopo T06+T07 (serve file reference per asset)

**PR-2 ordine:**
- T13 standalone
- T14 dopo T13 (validator consuma output T13)
- T15, T16 standalone (non dipendono tra loro, né da T13/T14)

**PR-1 deve mergiare prima di PR-2:** AC-5 richiede che l'URL install.ps1 sia disponibile nel messaggio di errore di `run-hook.cmd`, e il release asset deve esistere.

---

## Acceptance Criteria (dal design §10)

17 AC coprono end-to-end: install x64 (AC-1), fallback cascade (AC-2), air-gapped embedded (AC-3), byte-identity hook emission (AC-4), fail-loud run-hook.cmd (AC-5), schema v2 completo (AC-6, AC-6b), drain canonico `.global-outbox/` (AC-7), CI matrix verde (AC-8), dry-run coverage (AC-9), rollback (AC-10), SHA256 pin (AC-11), volontari RC 7gg (AC-12), query silent-users via `siae-dev-analytics` esistente (AC-13), zero nuova infra (AC-14), ARM64 rinvio (AC-15), matrix edge-case verdi (AC-16), panic buttons (AC-17).

## Rollout post-implementazione (dal design §9)

1. PR-1 review + CI verde (2-3gg)
2. PR-2 review + CI verde (1-2gg)
3. Release v1.45.0-rc1 opt-in (3-5gg, 3+ volontari Windows)
4. Promozione GA opt-in (7gg monitoring silent-users)
5. GA auto-update (permanent)
