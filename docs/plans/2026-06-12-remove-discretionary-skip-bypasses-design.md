# Design — Rimozione dei bypass discrezionali dei quality gate

> **Data:** 2026-06-12 · **Autore:** Lorenzo De Tomasi (via DevForge)
> **Stato:** APPROVATO al gate (2026-06-12) — ADR-1 = Opzione C (ibrido)
> **Complessità:** Alta (cross-cutting su 6 hook + ENV_VARS.md + test suite)

## Contesto e obiettivo

Gli hook DevForge espongono numerose leve che permettono a una persona di
**saltare un quality gate a propria discrezione**. Questo contraddice la North
Star "zero bug entro 2026-07-31": ogni escape hatch è un punto in cui il gate
diventa opzionale. L'obiettivo è **eliminare tutti i bypass discrezionali**,
mantenendo solo:

1. Un **breakglass dedicato e scoped** per i *fallimenti di tooling reali* in
   `review-evidence` (jq assente, lock contention, placeholder iCloud corrotto,
   evidence assente dopo compute) — così un bug ambientale non blocca per sempre.
2. I **kill-switch globali/admin** esistenti (fuori scope, vedi sotto).

## Scope — deciso con l'utente

### IN scope (rimuovere)

9 env var di skip discrezionale + 2 bypass via state-file:

| # | Meccanismo | Hook | Tipo |
|---|---|---|---|
| 1 | `DEVFORGE_SKIP_BRAINSTORMING` | `brainstorming-gate` | env var |
| 2 | `DEVFORGE_SKIP_BLIND_REVIEW` | `pr-blind-review-gate` | env var |
| 3 | `DEVFORGE_SKIP_EVIDENCE` | `review-evidence` | env var (doppio ruolo) |
| 4 | `DEVFORGE_SKIP_RETRO_GATE` | `stop-gate` | env var |
| 5 | `DEVFORGE_SKIP_GIT_GATE` | `pre-commit` | env var |
| 6 | `DEVFORGE_FORCE_STOP` | `stop-gate` (verification) | env var |
| 7 | `DEVFORGE_SKIP_PREMORTEM` | `pr-premortem-gate` | env var (**emerso in spec-review**) |
| 8 | `DEVFORGE_SKIP_UPDATE` | `session-start` | env var (non-gate) |
| 9 | `DEVFORGE_SKIP_TRAILER_HOOK` | `lib/install-trailer-hook.sh` | env var (non-gate) |
| 10 | `~/.claude/devforge-state/<sid>/.bypass-evidence` | `review-evidence` | state-file |
| 11 | `~/.claude/.devforge-skip-evidence` | `review-evidence` | state-file (**già legacy-inerte**: il codice la rimuove via `rm -f` alle righe 69-74, non la onora più; resta solo da eliminare il blocco) |

### OUT of scope (lasciare invariati)

Kill-switch globali / leve admin / rollback di emergenza — non sono "skip
per-task" ma leve operative di sistema:

- `DEVFORGE_ENFORCEMENT_OFF` (nuke globale)
- `DEVFORGE_USE_SESSION_SCOPE` (rollback task-scope)
- `DEVFORGE_RELEASE_RISK_DISABLED` + `~/.claude/.devforge-skip-release-risk`
- `DEVFORGE_BREAK_GLASS_REGEX` (admin-only, override hard-floor via commit msg)

## Decisioni architetturali

### ADR-1 — Breakglass tool-fail: meccanismo

`DEVFORGE_SKIP_EVIDENCE` oggi ha **doppio ruolo**: short-circuita PRIMA del
compute (linea 86) coprendo sia lo skip discrezionale sia il recovery sui
fallimenti di tooling. Vanno separati: la nuova leva deve agire **solo** sui
path di tool-failure, **mai** sui verdetti di qualità (`BLOCK_REGRESSION`,
`BLOCK_HARD_FLOOR`, `SEVERELY_DEGRADED`).

**I 5 path di tool-failure** in `review-evidence` (verificati in spec-review):
jq assente (102), lock contention (305), **collector crash RC≠0 (351)**,
evidence assente dopo compute (386), placeholder iCloud / JSON non valido (398).
Il breakglass scoped copre **tutti e 5** — sono tutti fallimenti ambientali del
tooling, non verdetti di qualità. (Il caso collector-crash :351 era omesso nella
bozza iniziale, recuperato in spec-review.)

Tre opzioni per il meccanismo:

| Opzione | Pro | Contro | Complessità |
|---|---|---|---|
| **A. Env var dedicata** `DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS=1` | Esplicita, scope minimo, è ciò che l'utente ha citato | Le env var **non propagano** ai subprocess hook (memory `feedback_env_var_not_propagated_to_hooks`) — proprio i tool-fail avvengono nel subprocess | Bassa |
| **B. State-file** `~/.claude/.devforge-evidence-toolfail` (pattern SID-safe come l'attuale `.bypass-evidence`) | Subprocess-safe → funziona davvero quando jq manca nel subprocess | File residuo = rischio bypass permanente dimenticato; serve auto-expiry | Media |
| **C. Ibrido** env var OR state-file, entrambi controllati solo nei path tool-fail, state-file con auto-decremento `N=count` | Subprocess-safe + ergonomico + non permanente | Due meccanismi da mantenere | Media |

**Raccomandazione: Opzione C (ibrido).** Motivazione: i tool-fail (jq missing,
lock contention) si manifestano nel subprocess hook, dove l'env var potrebbe non
arrivare — quindi serve lo state-file per affidabilità. L'env var resta come
comodità quando propaga. Auto-decremento `N=count` evita che il breakglass
diventi permanente. L'utente aveva indicato "env var dedicata": l'ibrido la
include come superset, nessuna funzionalità persa.

> **DECISO al gate (2026-06-12): Opzione C (ibrido).** Env var
> `DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS=1` OR state-file
> `~/.claude/.devforge-evidence-toolfail` con auto-decremento `N=count`,
> entrambi controllati SOLO nei 5 path di tool-fail. Lo state-file riusa il
> pattern SID-safe esistente. Auto-decremento evita la permanenza del bypass.

### ADR-2 — Verdetti di qualità diventano non-overridable da utente

Con la rimozione di `DEVFORGE_SKIP_EVIDENCE`:
- `BLOCK_REGRESSION` → non più overridable via env var. Risolvibile solo via
  fix reale o `/forge-fix-evidence` (auto-loop già esistente).
- `BLOCK_HARD_FLOOR` → già non-overridable se non admin BREAK-GLASS (invariato).
- `SEVERELY_DEGRADED` → già fail-closed senza bypass (invariato; **non** coperto
  dal nuovo breakglass tool-fail — è una degradazione di copertura, non un
  fallimento di tool puntuale).

### ADR-3 — `SKIP_UPDATE`: guard automatico al posto dello skip

`SKIP_UPDATE` non è un quality gate: disabilita il check `gh release list` al
session-start. È usato da `run-all.sh` (7 invocazioni) per evitare chiamate di
rete nei test. Rimuovendolo:
- Tolgo `&& [ "${DEVFORGE_SKIP_UPDATE:-}" != "1" ]` dal guard (session-start:146).
- Aggiungo un **timeout portabile** alla chiamata `gh release list` (pattern
  memory `feedback_macos_timeout_portability`: fallback via `command -v timeout`)
  così offline/proxy-bloccato fallisce fast e ritorna vuoto (degrada a no-update,
  comportamento già presente via `|| echo ""`).
- Rimuovo il prefisso `DEVFORGE_SKIP_UPDATE=1` dalle 7 righe di `run-all.sh`.

Nessuna nuova env var test-only: il timeout rende i test resilienti senza skip.

### ADR-4 — `SKIP_TRAILER_HOOK`: rimozione opt-out install

`install-trailer-hook.sh:14` ritorna early se la var è `1`. Rimuovo il check →
l'installer (già zero-harm: salta repo con `prepare-commit-msg` estraneo)
installa sempre. Per saltare un singolo commit resta `git commit --no-verify`.

### ADR-5 — Counter file di abuse diventano dead code

Rimuovendo i branch di bypass spariscono le scritture su:
`~/.claude/.devforge-bypass-count`, `.devforge-git-gate-bypass-count`,
`.devforge-blind-review-bypass-count`, `.devforge-force-stop-count`,
`.devforge-premortem-bypass-count`.
La sezione "Abuse-tracking data files" di `ENV_VARS.md` va aggiornata
(rimossi i 5 counter discrezionali; resta eventuale tracking del breakglass).

## Componenti e modifiche per file

| File | Modifica |
|---|---|
| `hooks/brainstorming-gate` | Rimuovi branch `SKIP_BRAINSTORMING` (linee ~110-135) + counter |
| `hooks/pr-blind-review-gate` | Rimuovi branch `SKIP_BLIND_REVIEW` (linea 85) + ref in `reason` (139); rimuovi counter |
| `hooks/stop-gate` | Rimuovi branch `FORCE_STOP` (253) + `SKIP_RETRO_GATE` (190) + counter; aggiorna `reason` (284) |
| `hooks/pre-commit` | Rimuovi branch `SKIP_GIT_GATE` (112) + ref in `reason` (142) + counter |
| `hooks/pr-premortem-gate` | Rimuovi branch `SKIP_PREMORTEM` (83) + counter (84) + ref in `reason` (137) |
| `hooks/review-evidence` | Rimuovi short-circuit discrezionale (state-file `.bypass-evidence` 78-84 + env var 86-91 + blocco legacy `.devforge-skip-evidence` 69-74); aggiungi breakglass scoped (ADR-1) sui **5** path tool-fail (jq 102, lock 305, collector-crash 351, no-evidence 386, placeholder 398); rimuovi ref `DEVFORGE_SKIP_EVIDENCE` da reason quality (460, 500) |
| `hooks/session-start` | Rimuovi `SKIP_UPDATE` dal guard (146) + timeout su `gh release list` |
| `lib/install-trailer-hook.sh` | Rimuovi check `SKIP_TRAILER_HOOK` (14) + commento (9) |
| `hooks/ENV_VARS.md` | Rimuovi le 8+2 voci; documenta nuovo breakglass tool-fail; aggiorna sezione counter |
| `tests/run-all.sh` | Rimuovi prefisso `SKIP_UPDATE=1` (7 occorrenze) |

## Testing

Test esistenti che asseriscono il bypass → invertire l'asserzione (gate
**continua a bloccare** anche con la var settata) o rimuovere:

- `tests/hooks/brainstorming-gate.test.sh`
- `tests/hooks/test_pr_blind_review_gate.sh`
- `tests/hooks/test_trailer_hook.sh`
- `tests/test_review_evidence_hook.py`
- `tests/test_forge_evidence_command.py`
- `tests/test_hooks_compound_cmd.py`
- eventuale test del premortem gate (verificare in fase di piano se esiste
  `tests/hooks/*premortem*`)
- `tests/test_env_vars_doc_sync.py` — **NB: copre SOLO `DEVFORGE_EVIDENCE_*`**
  (pattern grep `DEVFORGE_EVIDENCE_[A-Z_]+`). NON è sentinella per le altre 7 var
  (SKIP_BRAINSTORMING, SKIP_BLIND_REVIEW, SKIP_RETRO_GATE, SKIP_GIT_GATE,
  FORCE_STOP, SKIP_PREMORTEM, SKIP_UPDATE, SKIP_TRAILER_HOOK) → serve un test
  dedicato (sotto).

Nuovi test:
- **Doc↔code per le var rimosse**: nuovo test che grep-a il codice funzionale
  degli hook e asserisce che nessuna delle 9 var di skip discrezionale compare
  più in un branch attivo, e che non compaiono più in ENV_VARS.md. Colma il gap
  di copertura di `test_env_vars_doc_sync.py`.
- Breakglass tool-fail: con leva attiva, jq-missing/lock/collector-crash/
  no-evidence/placeholder → `{}` (allow); con leva attiva,
  `BLOCK_REGRESSION`/hard-floor → **resta block**.
- Regressione: ogni gate con la vecchia var settata → **block** (non più allow).

## Criteri di accettazione

1. Nessun branch funzionale legge le **9** env var di skip discrezionale
   (incluso `SKIP_PREMORTEM`).
2. I 2 state-file discrezionali (`.bypass-evidence`, `.devforge-skip-evidence`)
   non sono più consultati come short-circuit.
3. Breakglass tool-fail attivo sui **5** path di tool-failure (jq, lock,
   collector-crash, no-evidence, placeholder), mai sui verdetti di qualità
   (test di prova esplicito su `BLOCK_REGRESSION`).
4. `SKIP_UPDATE` rimosso; `run-all.sh` verde senza chiamate di rete bloccanti
   (timeout guard).
5. `ENV_VARS.md` allineato + nuovo test doc↔code che verifica l'assenza delle 9
   var rimosse (non basta `test_env_vars_doc_sync.py`, che copre solo
   `DEVFORGE_EVIDENCE_*`).
6. Kill-switch globali/admin invariati (ENFORCEMENT_OFF, USE_SESSION_SCOPE,
   RELEASE_RISK_DISABLED, BREAK_GLASS_REGEX).
7. `tests/run-all.sh` interamente PASS.

## Stima

| Scala | SP |
|---|---|
| Umano | 5 |
| AI-augmented | 2 |

## Rischi

- **Test infra (`SKIP_UPDATE`)**: senza timeout, i test session-start andrebbero
  in rete. Mitigato da ADR-3.
- **Breakglass affidabilità**: env-var-only fallirebbe nei subprocess (ADR-1 → C).
- **Doc drift**: mitigato da `test_env_vars_doc_sync.py`.
