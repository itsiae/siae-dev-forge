---
title: Piano — Risoluzione root-cause spacchettamento identità dev (cross-platform)
design: ../2026-06-14-dev-identity-rootcause-crossplatform-design.md
REQUIRED SUB-SKILL: siae-executing-plans
status: PENDING
created: 2026-06-14
---

# Piano implementativo — Identità dev root-cause, cross-platform (Windows + macOS/Linux)

## Contesto
Implementa l'Approccio A (hardening additivo no-regression) del design approvato:
rende il meccanismo di attribuzione identità (auth_* + trailer DevForge-Author, già
DONE su mac/Linux) **completo e cross-platform**, chiudendo i 6 problemi. Scope:
producer `siae-dev-forge` + handover consumer `developer-telemetry`.
Cluster-2 (anti-tamper/OIDC/SSO-enforcement) è iniziativa SEPARATA — non qui.

Principi: additivo, no-regression su `user`/`user_raw`/`user_source`/`actor_canonical`
e su `auth_email`/`auth_account_uuid` esistenti; ogni hook resta best-effort exit-0;
degrado sempre osservabile (mai silenzioso).

## Task
- [ ] task-00 — Spike verifica bloccante cross-platform (node PATH + CLAUDE_CONFIG_DIR) [PENDING]
- [x] task-01 — F1: .gitattributes eol=lf + renormalize + test no-CR [DONE]
- [x] task-02 — F2a: helper devforge_json_field (node→python3→degraded) + segnale telemetry_degraded [DONE]
- [x] task-03 — F2b: instrada i siti identità-critici su devforge_json_field (no-regression auth_*) [DONE]
- [x] task-04 — F2c: hardening trailer hook (marker v2 + node→python3 + guard git≥2.15 + emissione install-time) [DONE]
- [x] task-05 — F3: normalizzazione host short-name nel bundle identità [DONE]
- [x] task-06 — 6b+6d: campo repo_slug (org/repo) da SSH+HTTPS + marker duration_source [DONE]
- [ ] task-07 — P5: pr_author_emails[] in post-commit-review [PENDING]
- [ ] task-08 — P2: probe diagnose-identity.sh + guida isolamento per-persona [PENDING]
- [x] task-09 — Write-path zero-loss cross-platform + suite data-loss esaustiva (ALTA priorità) [DONE]
- [ ] task-10 — Handover consumer (developer-telemetry) [PENDING]
- [ ] task-11 — No-regression + verifica criteri di accettazione + registrazione test [PENDING]

## Dipendenze
- task-00 → gate per task-02/03 (node-first vs python3-prereq) e task-08 (isolamento).
- task-02 → task-03 → task-04 (helper, poi routing, poi trailer).
- task-02 → task-09 (la fallback chain interprete è la base del fallback durabile del writer).
- task-01 → task-09 (caso 6 della suite zero-loss: assenza CR negli hook installati).
- task-05/06/07 indipendenti.
- task-10 dopo task-03/05/06/07 (campi definiti). task-11 ultimo.

## Criteri di accettazione globali
I **14** criteri della sez. 7 del design (incluso AC14 = write-path zero-loss, F4):
"conteggio righe = conteggio eventi emessi in ogni scenario di concorrenza/crash/no-interprete".
task-11 li verifica tutti e li mappa ai test; task-09 verifica numericamente la zero-perdita.

## Note esecuzione
Test identità = bash, sourcing `lib/logger.sh` con override `DEVFORGE_CLAUDE_JSON` e
`HOME`/`CLAUDE_CONFIG_DIR` temporanei. Interprete forzabile in test mascherando node/python3
dal PATH (una shim directory in testa al PATH che oscura il binario reale con uno script che esce 127).
Directory test esistente di riferimento: `tests/zero-loss/unit/`.
