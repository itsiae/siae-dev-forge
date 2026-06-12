## Obiettivo

Rimozione dei **bypass discrezionali** dai quality gate DevForge + **network
resilience** per le chiamate GitHub negli hook (folding di un'iniziativa
accoppiata, vedi Premortem).

## Parte 1 — Rimozione bypass discrezionali

I quality gate non devono più poter essere saltati via env var o state-file
arbitrari. Rimossi: `SKIP_BRAINSTORMING`, `SKIP_PREMORTEM`, `SKIP_BLIND_REVIEW`,
`SKIP_GIT_GATE`, `SKIP_RETRO_GATE`/`FORCE_STOP`, skip evidence
(`SKIP_EVIDENCE` + state-file), `SKIP_UPDATE`, `SKIP_TRAILER_HOOK`.

Mantenuto un **breakglass ibrido scoped** (ADR-1 Opzione C) sui 5 path
tool-fail di `review-evidence` (`DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS` +
state-file `~/.claude/.devforge-evidence-toolfail` con auto-decremento). Mai
sui verdetti di qualità (`BLOCK_REGRESSION`/hard-floor) — verificato per
costruzione e da test (`test_breakglass_does_not_release_quality_block`).

## Parte 2 — Network resilience GitHub (folding)

Le call `gh`/`git` verso github bloccavano la sessione (**~744s su
session-start**, misurato) perché: (1) `NO_PROXY` SIAE non include github →
routing sul proxy corporate morto (i/o timeout ~30s/call); (2) nessun timeout
hard portabile (`timeout`/`gtimeout` assenti su macOS BSD; il fallback `perl`
era fragile).

- `lib/net-timeout.sh`: `_devforge_no_proxy_github` (idempotente, exported →
  github DIRECT, ~1s) + `net_run` (timeout hard portabile macOS/Linux/Git-Bash).
- Cablato in `session-start`, `pr-release-gate`, `post-commit-review`;
  rimossa la catena `timeout`/`gtimeout`/`perl`. (Verificato: gli altri hook con
  `gh`/`git` nel testo — premortem/blind-review/pr-gate/review-evidence — fanno
  solo match di stringa su `$TOOL_COMMAND`, **nessuna call di rete reale**.)
- **VPN-aware autoconfig** (`_devforge_proxy_autoconfig`): un probe TCP a tempo
  (`_devforge_on_siae_net`, `net_run 1` su `/dev/tcp/<proxy>`) rileva se siamo su
  rete/VPN SIAE. On-net → proxy attivo + github DIRECT; **off-VPN → strippa tutte
  le var proxy** così le call vanno DIRECT invece di appendersi ~30s sul proxy
  irraggiungibile. Endpoint dedotto da `https_proxy`/`*_PROXY`, fallback al proxy
  SIAE noto. Nessuna env var di override (coerente con la Parte 1).
- **Bugfix `net_run`:** sostituito il `trap ... RETURN` (che, annidato dentro
  `_devforge_on_siae_net`, restava registrato e rifaceva fire al ritorno dei
  chiamanti → `tmp: unbound` sotto `set -u`) con cleanup esplicito ai due return.
- **Verifica empirica:** `gh release list` **30s → 1s** con proxy SIAE attivo;
  off-VPN il probe risolve in ~1s e le call non si appendono più.

## Premortem (top-3)

1. **[TECNICA]** `SKIP_UPDATE` rimosso si appoggiava a un guard `command -v
   timeout` rotto su macOS → blocco 744s. **Mitigato** foldando net_run +
   NO_PROXY in questa PR (Parte 2).
2. **[OPERATIVA]** Rimozione simultanea di tutti i bypass: rischio hard-block
   su falso positivo di un gate. **Mitigato** dal breakglass tool-fail scoped
   (infra-fail) e dalla preservazione dei kill-switch admin/globali.
3. **[OPERATIVA]** Branch indietro di 23 commit su `origin/main` (stessi hook).
   **Mitigazione:** rebase + suite verde prima del merge.

## Test (solo robe cambiate, no-regression mirato)

60/60 PASS: `test_net_timeout.sh` (12, +4 VPN autoconfig), `test_net_resilience_wiring.sh` (7),
`test_no_discretionary_bypass.py` + `test_review_evidence_breakglass.py` (11),
post-commit hook .sh (2), session-start-advisor + release-risk + compound-cmd (28).

## Review

- Blind review: **PASS** (10/10, zero drift/missing).
- code-reviewer: **APPROVED** (0 CRITICAL, 0 MAJOR; 3 MINOR — 2 fixati: trap
  quoting path-spazi + `local` nel breakglass).
- spec-reviewer: **PASS** (10/10 task bypass + criteri network-resilience).

## Follow-up noti (non bloccanti)

- CHANGELOG entry (richiede decisione bump versione).
- CI job `windows-smoke` per net-timeout su Git Bash.

Co-Authored-By: SIAE DevForge <ai-platforms@siae.it>
