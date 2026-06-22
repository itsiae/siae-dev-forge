# Changelog

Tutte le modifiche notabili a questo progetto sono documentate in questo file.

Il formato e' basato su [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added — Banner esplicito quando python3 manca

`python3` è prerequisito della telemetria DevForge (token, attribuzione identità, KPI,
durabilità zero-loss). Finora la sua assenza degradava in modo **silenzioso** (solo stderr
+ una riga statusline). Ora `session-start` mostra un **banner esplicito e prominente** in
`additional_context`, con il comando d'installazione per-OS. È solo un avviso — **non blocca**
le operazioni.

- `lib/python3-check.sh` — `devforge_python3_banner` (solo builtin `command`/`printf` →
  testabile in isolamento, nessuna dipendenza esterna).
- `hooks/session-start` — inietta il banner in cima a `additional_context` quando python3 manca.
- Test: `tests/hooks/test_python3_banner.sh` (caso assente/presente + wiring + JSON valido).

### Fixed — Accuratezza telemetria token/costi (scoping per-sessione)

Corregge 3 cause-radice dietro 5 anomalie su token/costi osservate a valle (blocco
`by_model` congelato byte-identico ri-emesso ×36, `cost=0` su 33 dev, copertura
`by_model` 904/96k). Design: `docs/plans/2026-06-16-telemetry-token-accuracy-fix/design.md`;
handover consumer: `docs/handover/2026-06-16-telemetry-token-accuracy.md`.

- **Scoping per-sessione fail-closed** — `lib/token-collector.py`: nuova
  `resolve_session_dir()` che auto-deriva la dir di stato dal session id
  (`~/.claude/.devforge-session-id` → `devforge-state/<sid>`); **rimosso il fallback
  globale per-progetto** che faceva sopravvivere e congelare lo stato tra sessioni.
  `update`/`init`/`write_*` sono no-op quando la sessione non è risolvibile (mai più
  stato globale silenzioso).
- **Reset `by_model` su cambio `.jsonl`** — niente più carry-forward del blocco
  modello quando `update()` passa a un file di sessione diverso.
- **Ordering export in `hooks/session-start`** — `DEVFORGE_SESSION_DIR` esportato
  PRIMA di `token-collector.py init` (il sottoprocesso python non vedeva la dir →
  stato fuori scope). Trigger principale della bassa copertura.
- **`token_state_complete`** — nuovo campo booleano (f14) su `session_end`: `true`
  solo con stato risolto e `total>0`. `hooks/stop-gate` lo emette `false` invece di
  emettere zeri indistinguibili dai dati reali.
- **Cleanup file di stato globali legacy** — `init()` rimuove in modo idempotente i
  `.devforge-token-*-{project_hash}` residui.

## [1.88.0] - 2026-06-15

### Added — Attribuzione identità dev root-cause, cross-platform (Windows + macOS/Linux)

Rende il meccanismo di attribuzione identità (auth_email/auth_account_uuid +
trailer DevForge-Author, già attivo su mac/Linux) **completo e cross-platform**,
chiudendo i 6 problemi di spacchettamento identità. Design+piano:
`docs/plans/2026-06-14-dev-identity-rootcause-crossplatform-design.md`.

- **F1** — `.gitattributes` con `eol=lf` su shell/hook: i CRLF non rompono più gli
  hook bash su Windows (Git Bash). `hooks/run-hook.cmd` (polyglot, sempre via bash) reso `eol=lf` esplicito.
- **F2** — reader JSON portabile `devforge_json_field` (node→python3→degraded): l'identità
  risolve su Windows senza python3. Instradati tutti i siti identità-critici
  (`resolve_auth`, `init_session`, `get_user_raw/source`, `session_token_total`), con guard anti-ricorsione.
- **F3** — `host` normalizzato a short name nel bundle identità (join `(host, os_user)` stabile cross-OS).
- **F4** — write-path zero-loss su Windows senza python3: fallback `python3(flock)→node(mkdir-lock+O_APPEND+fsync)→bash`,
  stale-guard anti-`kill -9`, fall-through su interprete presente-ma-fallito, segnale osservabile `telemetry_degraded`.
  `lib/atomic_write.py` invariato.
- **Trailer hook** hardening: marker v1→v2 (re-deploy automatico), lettura email node→python3 self-contained,
  guard `git interpret-trailers` ≥2.15 con segnale `trailer_hook_skipped_old_git`.
- **`repo_slug`** (org/repo da SSH+HTTPS) e **`pr_author_emails[]`** (autori reali della PR dai trailer) negli eventi;
  marker `duration_source="wallclock"`.
- `scripts/diagnose-identity.sh` (probe account condivisi, VERDICT ISOLATED/SHARED-DEGENERATE/NO-AUTH) +
  guida isolamento per-persona. Handover consumer in `docs/handover/2026-06-14-identity-rootcause-consumer.md`.

Additivo e no-regression: `user`/`actor_canonical`/`auth_*` invariati. Nuova suite data-loss
cross-platform (concorrenza 50-writer, crash, no-interprete) con assert numerico righe==eventi.

## [1.84.0] - 2026-06-11

### Fixed — Gate token-based scattano anche su comandi composti

I 3 hook PreToolUse token-based (`pr-premortem-gate`, `pr-blind-review-gate`,
`pre-commit`) venivano silenziosamente bypassati da comandi composti
(`cd X && env -u P gh pr create`): `_devforge_primary_cmd` taglia al primo
operatore shell → primo token `cd` → no match → fail-open. Bypass reale: PR #311
aperta senza premortem né blind-review.

- **`_devforge_segments`** (`lib/cmd-parser.sh`): split su `&&`/`||`/`;`/`|`/newline
  (gsub awk separati, non ambigui su ogni variante awk).
- **`devforge_cmd_has_subcommand`**: match token-based su OGNI segmento — immune
  ai falsi positivi su stringhe (`printf '...gh pr create...'` non scatta).
- **Strip flag `env`**: `-u VAR`/`-C dir` (2 parole), bare `-x` (1 parola).
- I 3 hook usano il nuovo matcher; fallback esistenti invariati (additive-only).
- Test: 11 e2e (`tests/test_hooks_compound_cmd.py`, JSON reale pipato negli hook)
  + 12 unit shell (`tests/lib/test_cmd_parser.sh` sezione 6). No-regression: 32/32
  + 8/8 + run-all identico a baseline.

Design: `docs/plans/2026-06-11-hook-compound-cmd-match-design.md`.

## [1.78.0] - 2026-06-03

### Added — Segnali raw "chi produce di valore" + pricing multi-vendor (Design A)

Estensione telemetria con segnali RAW additivi su S3 (la valutazione resta a valle in
`developer-telemetry`). Tutto additivo (`schema_version` 2, campi/eventi esistenti invariati),
attribuzione token non gonfiata.

- **`by_skill`** (`session_end`): componenti token per skill da `attributionSkill` nativo,
  ESCLUDENDO `cache_read` (anti-inflazione: il contesto riletto non è "lavoro" della skill).
- **`by_model_tokens`** (`session_end`): breakdown componenti per modello INCLUDENDO `cache_read`
  — il dato raw che permette al consumer di applicare i listini di vendor/soluzioni diverse.
- **`pricing`** (`session_end`): rate-table applicato `{unit:"usd_per_1m_tokens", eur_rate,
  by_model:{model:rates}}` + costante `PRICING_UNIT`. Con `by_model_tokens` il consumer
  ricalcola il costo per qualsiasi vendor; `cost_eur` esistente invariato.
- **`test_run_result`** + **`tdd_cycle`** (`capture-test-result`, prima non emetteva nulla):
  esito test (status/exit/coverage/framework) e transizioni TDD (from/to/elapsed_sec/reason).
- **`session_tokens_cumulative`** su `pr_merged` (ancora token→esito) via helper
  `devforge_session_token_total`.
- `add_usage_delta(...,skill=None)`; `session_fields_line` esteso f11-f13; persist-reload safe.

Design: `docs/plans/2026-06-02-telemetry-raw-value-signals-design.md`. Test: +13 casi
(pytest + bash). Follow-up: `tokens_at_block` sui gate (Comp.3b).

## [1.76.0] - 2026-06-02

### Added — Bundle identità developer raw per risoluzione resiliente a valle

Per rendere estremamente resiliente la risoluzione dei nomi developer a valle
(`developer-telemetry`), il producer ora emette **tutti i segnali grezzi di identità**
invece di una sola identità pre-risolta (lossy su macchine condivise / git config errata).
Tutto additivo (`schema_version` resta 2, eventi e campi esistenti invariati).

- Nuovo helper `lib/logger.sh::devforge_identity_bundle` → oggetto JSON a singola riga con
  `git_local_email`, `git_local_name`, `git_global_email`, `git_global_name`, `os_user`,
  `host`. Ogni segnale best-effort (vuoto se assente), sanitizzato, non aborta mai sotto
  `set -euo pipefail`. `repo_root` escluso (già campo top-level dell'evento).
- `hooks/session-start` emette il bundle in `session_start.meta` (fonte autorevole su S3) e in
  `user.json` (cache locale, best-effort python3-only). Catena first-match e `actor_canonical`
  invariati. Bundle non-parsabile → `user.json` senza `identity` (silent skip), sessione mai
  bloccata.

Design: `docs/plans/2026-06-02-developer-identity-bundle-design.md`. Test: +6 casi bash in
`tests/test_telemetry_fixes.sh` (16/16 PASS).

## [1.73.0] - 2026-05-30

### Changed — DevForge subagent default model: `inherit` → `sonnet`

Tutti e 5 i subagent DevForge (`code-reviewer`, `doc-generator`, `mcp-impact-analyst`,
`qa-investigator`, `spec-reviewer`) ora dichiarano `model: sonnet` nel frontmatter
invece di `model: inherit`. Significa che ogni dispatch via Agent tool gira di
default su Claude Sonnet (oggi 4.6), indipendentemente dal modello della sessione
parent (Opus 4.7, Haiku 4.5, ecc.).

**Razionale:**
- **Coerenza eval baseline:** tutti i dispatch DevForge convergono sullo stesso modello → output piu' riproducibile, regression detection piu' affidabile
- **Cost efficiency:** Sonnet 4.6 e' ~5x meno costoso di Opus 4.7 per token; review/spec-review/qa-investigator hanno pattern di output che non beneficiano significativamente di Opus
- **Throughput:** Sonnet 4.6 ha latenza minore → review parallel piu' veloci

**Override esplicito:**
chi vuole un agent specifico su Opus puo' ancora forzarlo in-call:

```
Agent({subagent_type: "siae-devforge:code-reviewer", model: "opus", prompt: ...})
```

Il `model` passato come parametro tool ha precedenza sul frontmatter agent.

**Migration:** zero migration richiesta. Utenti che non hanno mai customizzato
nulla vedono comportamento invariato (i loro dispatch usavano gia' il modello
default della sessione, che in molti casi era Sonnet); chi era esplicitamente su
Opus per i subagent ora si trova Sonnet — vedi override sopra per ripristinare.

### Tests

- `tests/agent_model_sonnet.test.sh` — 18 check (5 agenti × 2 + frontmatter integrity + count check + zero residui inherit/altri valori)

## [1.68.0] - 2026-05-25

### Added — siae-premortem skill + pr-premortem-gate hook

Klein premortem method (HBR 2007 "Performing a Project Premortem") integrato come
gate pre-PR su itsiae/*. Cattura failure mode che la code review missa per
hindsight bias (Klein: +30% identificazione cause fallimento usando hindsight
prospettico vs. domanda "cosa puo' andare storto?").

**Skill `siae-premortem`** — metodo a 5 step adattato per LLM single-agent:
1. Set the premise ("3 mesi dopo merge, fallimento conclamato")
2. Brainstorm 5-10 cause concrete e specifiche
3. Categorizzazione (Tecnica / Operativa / Adozione / Esterna)
4. Top-3 con mitigazioni concrete (no wishful thinking)
5. Decisione: PROCEDI / RIVISITA / REJECT

**Hook `pr-premortem-gate`** — PreToolUse Bash matcher, blocca `gh pr create|edit`
senza evidenza siae-premortem in session-skills o task-scoped. Pattern speculare a
`pr-blind-review-gate`. Scope: itsiae/* only. Bypass tracciato 5/giorno:
`DEVFORGE_SKIP_PREMORTEM=1` (solo hotfix/bump/revert).

**Anti-pattern guard nella skill:**
- "Bias da implementer" se cause solo Tecniche → forza Adozione/Operativa/Esterna
- "Wishful mitigation" ("faremo attenzione") esplicitamente rigettata
- "PR piccola, niente puo' andare storto" → le PR piccole rompono produzione quanto le grandi

Reference: https://hbr.org/2007/09/performing-a-project-premortem

## [1.66.0] - 2026-05-21

### Changed — code-coverage skill v2 optimization (10 fixes consolidated)

Three parallel expert audits (best-practice, runtime, full-stack) converged on
10 high-ROI fixes to reduce iterations / wall-time / token spend without losing
efficacy (>=70% global, P1>=80%).

**Expected impact on LARGE repo runs:** tokens ~280-400k → ~180-220k (-35%);
round-trips 12-18 → 7-9; Phase 5 batch from sequential turns to parallel.

**SKILL.md + references:** description frontmatter trim, HARD READ POLICY
anti-eager-load, inlined `phase-2-strategy.md` + `phase-4-environment.md`
into `SKILL.md` (refs deleted), explicit parallel-Write directive, Phase 5b
note moved.

**Python scripts (`parse_coverage.py`, `detect_stack.py`):** new
`--view {full,repair,summary}` flag on parse_coverage; `detect_monorepo_workspaces`
adds Maven `<modules>` + Gradle `include()` parsing.

**Templates + categorize + phase1 + cache:** idempotent `clean_template_placeholders`
helper, `categorize_failure` normalize multi-line, Phase 5b probe inside
`phase1-discover.sh`, `decisions.log` archive on completion + `discovery-summary.json`
emit.

### Fixed — auto-review iter findings

- `phase1-discover.sh:88-99` — Python heredoc injection (`$REPO` interpolated
  in `python3 -c "..."`). Converted to `python3 - "$REPO" <<'PYEOF'` + `sys.argv[1]`.
- `cache-helper.sh:42-50` — archive race condition: `archive_ts` now includes
  `_$$` (PID) + `rm -f "$sentinel"` post-archive.

### Breaking — semantics fix

- **`priority-rules.json` v1.0 → v1.1**: priority assignment via `path_patterns`
  now anchored to `last_2_segments` (parity with `estimate_size.py`). Paths
  like `src/api/restore.ts` no longer match `**/store/**`. Existing baselines
  may shift module priority assignment.
- **`parse_go_cover`**: returns line% weighted by `numStmt` from `coverage.out`
  raw format. Previously over-reported on funcs with unequal statement counts.
  Go repos that passed spuriously may now report accurate (lower) coverage.

### Test coverage

142/142 passed (was 103 baseline, +39 new tests). Coverage gate bypass
(`DEVFORGE_SKIP_GIT_GATE=1`) tracked: pre-existing gap on `estimate_size.py`,
`select_command.py`, `validate_env.py` (not touched by this PR).

## [1.65.0] - 2026-05-21

### Changed — Skill `siae-functional-bug-hunter` v1.1.0 -> v1.2.0

Audit a 4 agenti paralleli + implementation plan via 3-blind-agent consensus
(Round 1 Independent + Round 2 Cross-pollination + Round 3 fact-check empirico
+ Round 4 sintesi). Vedi `audit-reports/functional-bug-hunter-audit-2026-05-21.md`
e `docs/plans/2026-05-21-functional-bug-hunter-improvements-design.md`.

**Score impact** (atteso): 6.75/10 -> ~8.5/10 sui 4 assi audit (scope
coherence, Anthropic best practice, token efficiency, bug-finding effectiveness).

#### Added

- `scripts/path_feasibility.py` — Phase 6 filter codificato (glob + keyword,
  no AST, stdlib only). 5 test pytest. Chiude gap A1 #2 audit ("capability
  dichiarata ma non codificata").
- `scripts/run_lock.py dispatch` sub-command — Mode enum
  (interactive/strict/report-only) x 5 STOP events -> Action
  (PAUSE/CONTINUE/DEGRADE). 17 test pytest. Chiude gap A1 #3.
- `commands/siae-functional-bug-hunter.md` — slash command file registrato
  (pattern allineato a `commands/forge-*.md`). Chiude gap A1 #4.
- `references/pipeline_internals.md` — Phase 0..8 narrative estratta
  on-demand (-1600 tok eager). Chiude gap A3 #5.
- `references/hallucination_guard.md` — HG-01..05 contract + grounding
  policy estratti (-520 tok eager). Chiude gap A3 #9.
- `references/README.md` — load-matrix progressive disclosure
  Phase->Reference->Load-condition. Chiude gap A2 #6.
- `references/runtime_modes.md` — single source of truth per dispatch
  matrix (sincronizzata con `run_lock.py::_DISPATCH_TABLE`).
- `references/stacks/typescript-javascript.md` — BP-024 react-lifecycle-race
  e BP-025 set-state-after-unmount. Chiude gap A4 #1.
- `references/stacks/data-platform.md` — BP-026 nullable-join-key-loss e
  BP-027 window-missing-partition-by. Chiude gap A4 #2.
- `tests/test_path_feasibility.py` (5 test) e
  `tests/test_run_lock_dispatch.py` (17 test). Coverage: 32/32 PASS.

#### Changed

- `SKILL.md` description ridotta da 1209 a 854 char (conformita' Anthropic
  Agent Skills frontmatter ≤1024). Chiude gap A2 #1.
- `SKILL.md` body compresso da 422 LOC / 4059 token a 228 LOC / 2314 token
  (-43%) via estrazione Phase narrative + dedup hallucination guard.
- `SKILL.md` aggiunte sezioni `## When to use` e `## Supported stacks`
  (recupero stack list rimossa dalla description).
- `skill_semver` 1.1.0 -> 1.2.0.

#### Out of scope (rimandato a v1.3.0)

Vedi design doc, sezione "Out of scope". Notabili: split `bug_patterns.md`
(5290 tok, on-demand soft cap), `@file:` imports formali, BP-028/029,
test suite pytest completa per ogni script.

## [1.64.0] - 2026-05-21

### Added — Skill `siae-functional-bug-hunter` (manual-only)

Integrata nel marketplace la skill `siae-functional-bug-hunter` (skill_semver 1.1.0): static, multi-repo, cross-stack functional bug hunter. Ingerisce uno o piu' root di repository, rileva quando occorre estendere la dependency closure, genera ipotesi di bug da una matrice di pattern stack-aware, le filtra per path feasibility ed emette un `qa_report.md` deterministico raggruppato per user-journey con recipe di riproduzione minimally-flaky scritte per un tester manuale (profilo ISTQB Foundation + 2 anni di esperienza).

Stack supportati: Java, TypeScript/JavaScript, Python, Go, Rust, Kotlin, Swift, Ruby, .NET/C#, Scala, Flutter/Dart, Terraform/HCL, AWS serverless (SAM/CDK/SFN/EventBridge), data platforms (dbt/Airflow/Spark/SQL), piu' un profilo di fallback generico.

**Invocazione manual-only**: la skill parte solo via slash command esplicito `/siae-functional-bug-hunter` con JSON conforme al contratto Inputs. Nessun hook automatico, nessun session-start activation, nessun auto-trigger natural-language. Tre runtime mode: `interactive` (TTY, pausa su scope mancante), `strict` (CI, mai pausa), `report-only` (low-confidence partial ammesso).

**Esclusioni**: findings SAST-only che non passano il functional manifestation test; generazione di codice di test automatizzato.

**File aggiunti:** `skills/siae-functional-bug-hunter/` (88 file, 580K) — SKILL.md, `scripts/` (preflight, dependency_closure, list_entry_points, render_qa_report, hallucination_guard, redact_pii, generate_payloads, run_lock), `references/` (bug_patterns, cross_stack_bridges, lifecycle_playbook, severity_rubric, repro_voice_guide, qa_inclusion_tree, qa_report_json_schema, repo_granularity, subagent_contract, stacks/INDEX.md), `tools/` (check_pluggability, repro_voice_lint, triggerlint, wordcount), `tests/`, `eval/`, `assets/`.

**File modificati:**
- `.claude-plugin/plugin.json` — version 1.63.4 -> 1.64.0, count 43 skill -> 44 skill
- `.claude-plugin/marketplace.json` — version 1.63.4 -> 1.64.0, count 43 skill -> 44 skill
- `README.md` — count 43 skill -> 44 skill (header + tree)

## [1.63.4] - 2026-05-20

### Fixed — Bypass evidence subprocess-safe (BUG A)

In v1.63.3 abbiamo rimosso il state file globale `~/.claude/.devforge-skip-evidence` per stoppare il pattern set-and-forget. Resto solo `DEVFORGE_SKIP_EVIDENCE=1` come breakglass env var. **Bug residuo scoperto subito**: Claude Code NON propaga env var della shell utente ai subprocess hook (memoria `feedback_env_var_not_propagated_to_hooks`). Quindi `DEVFORGE_SKIP_EVIDENCE=1 gh pr create` settava la env var solo nel processo `gh`, mai nel hook PreToolUse → breakglass inutilizzabile.

**Fix**: oltre a env var, il hook `review-evidence` ora accetta un **marker file session-scoped** in `~/.claude/devforge-state/<sid>/.bypass-evidence`:
- Subprocess-safe (file su disco, leggibile da qualsiasi hook child)
- Session-scoped (auto-rimosso dal `stop-gate` hook a fine sessione, no set-and-forget)
- Path determinato dal `sid` corrente in `~/.claude/.devforge-sid`

**Workflow utente breakglass v1.63.4+:**
```bash
touch ~/.claude/devforge-state/$(cat ~/.claude/.devforge-sid)/.bypass-evidence
gh pr create ...      # bypassa review-evidence
# auto-cleanup a fine sessione
```

**File modificati:**
- `hooks/review-evidence:51-60` — check session marker prima di env var
- `hooks/stop-gate:106-112` — cleanup `.bypass-evidence` a session_end
- `hooks/ENV_VARS.md:35` — doc workflow workaround

**Note BUG B (drift_severity_high blocca bug fix)**: bug architetturale identificato in iter-review v1.63.3 ma **richiede design doc dedicato** (cambia semantica del gate review-evidence). Tracciato per follow-up: il check `lib/review_evidence/thresholds.py:64` dovrebbe degradare a warning quando `CHANGELOG.md` ha entry strutturata per `plugin.json.version` corrente. Implementazione differita.

## [1.63.3] - 2026-05-20

### Fixed — 3 bug critici telemetria S3 (audit 2026-05-20)

Audit empirico telemetria DevForge su S3 `siae-devforge-telemetry/devforge-logs/` ha rivelato **103× inflazione** dei `commit_created` events (S3: 20.087 vs GitHub commits reali 6gg: 195). Tre bug indipendenti che inflavano sia il numeratore (signal) che il denominatore (commits) delle metriche di adoption, rendendo i numeri reali artificialmente bassi.

**Bug 1 — `lib/logger.sh:344` sid fallback letterale `"no-session"`**

`devforge_get_sid()` ritornava la stringa letterale `"no-session"` quando il file `$DEVFORGE_SID_FILE` non esisteva. Risultato: **43.808 eventi orfani in 6gg** (53% del totale) collassati su un singolo bucket `sid=no-session`, rendendo impossibile distinguere sessioni Claude reali da invocazioni hook fuori-sessione (es. shell esterna che richiama hook plugin senza session init).

Fix: ora genera un nuovo sid via `devforge_new_sid()` e lo persiste in `$DEVFORGE_SID_FILE`. Eventi orfani spariscono.

**Bug 2 — `hooks/post-commit-review:31` `LAST_HASH_FILE` globale invece di per-repo**

Il file `${HOME}/.claude/.devforge-last-commit-hash` era globale per tutta la macchina. Lavorando su N repo, il check `if [ "$CURRENT_HEAD" != "$SAVED_HASH" ]` riusciva sempre perché ogni `git rev-parse HEAD` in un repo diverso produceva un SHA diverso dal salvato. Risultato: **2.629 commit_created duplicati** per cross-repo switching + lavoro su worktree multipli.

Fix: `LAST_HASH_FILE` ora include hash del `git --show-toplevel`: `~/.claude/.devforge-last-commit-hash-<shasum-repo-path>`. Stato per-repo, no più cross-contamination.

**Bug 3 — `hooks/review-evidence` state file bypass set-and-forget**

`touch ~/.claude/.devforge-skip-evidence` creava un bypass permanente che restava attivo per settimane (mio caso: dal 16 maggio, scoperto il 20). Risultato: **5.786 `evidence_bypass_used` events in 6gg** (top event in volume, più di `commit_created`).

Fix: state file `~/.claude/.devforge-skip-evidence` **completamente rimosso**. Se trovato (legacy), viene auto-cancellato + loggato come `evidence_bypass_legacy_removed`. Resta solo `DEVFORGE_SKIP_EVIDENCE=1` env var di sessione (breakglass esplicito che richiede `export` ogni shell, no persistenza). Suggerimenti `touch` in 8 messaggi `decision:block` sostituiti con `export DEVFORGE_SKIP_EVIDENCE=1`.

**Impatto sui dati pre-fix:**
- Commits S3 (6gg): `3.209 → 580 dopo dedup` (-82%, ora coerente con 195 GitHub firmati)
- Events totali: `13.726 → 11.041` (-19%, no-session droppati)
- Adoption brainstorming (session-based): metrica ora calcolabile = **21.5%**
- Adoption TDD: **40.5%**
- Adoption verification: **3.5%**

**Telemetria pre-fix non recuperabile**: i log su S3 prima di v1.63.3 restano inflazionati. La dashboard locale `~/Library/Mobile Documents/com~apple~CloudDocs/devforge-dashboard/` applica dedup retroattivo on-the-fly in `build_data.py` per ricostruire metriche pulite anche dai vecchi log (chiave dedup: `(commit_sha, repo)` + drop `sid=no-session`).

## [1.63.2] - 2026-05-20

### Added — Test deterministici anti-allucinazione (3 file, 19 test, 100% PASS)

Implementazione del follow-up identificato dal code-reviewer in PR #263: *"Senza un test deterministico, il drift si ripresenterà alla prossima release"*. Tre test suite che bloccano automaticamente le 3 classi di regressione anti-dilution emerse nella sessione di razionalizzazione.

**`tests/test_count_consistency.py`** (6 test) — chiude la classe "count hallucination" (v1.62.3 dichiarava `30 hook` con count inventato):
- `test_dual_source_version_sync` — `plugin.json.version == marketplace.json.version` (memoria `project_plugin_version_dual_source`)
- `test_dual_source_description_sync` — description identiche carattere-per-carattere
- `test_description_counts_match_empirical` — parsing description + match con `len(glob skills/*/)`, `commands/*.md`, `agents/*.md`, `hooks/` netti (esclusi `lib/`, `*.md`, `*.json`, `run-hook.cmd`, `skill-advisory-helpers.sh`)
- `test_readme_version_matches_plugin` — README metadata tabella `| Versione | \`X.Y.Z\` |` = `plugin.json.version`
- 2 test di sanity check (JSON valido)

**`tests/test_backbone_validates_via.py`** (5 test) — chiude la classe "evidence contract incompleto":
- `test_backbone_skills_all_have_validates_via` — 9/9 backbone hanno il blocco
- `test_validates_via_has_predicate` — predicate non-vuoto/non-TBD
- `test_validates_via_has_evidence_type` — in allowlist `{log_event, file_exists, exit_code, state_file, file_pattern, git_state}`
- `test_validates_via_has_evidence_check` — check non-vuoto, >10 char, no TBD
- `test_predicate_names_unique_across_backbone` — predicate univoci (evita ambiguita' gate)

**`tests/test_phantom_slash_commands.py`** (3 test) — chiude la classe "slash command fantasma" (v1.62.3 ne aveva rimossi 14):
- `test_no_phantom_slash_commands_in_skills` — ogni `/forge-X` in SKILL.md esiste come `commands/forge-X.md` (eccezione: `PHANTOM_WHITELIST` per anti-esempi documentati come `/forge-spec-review`)
- `test_whitelist_entries_actually_referenced` — whitelist non-stale (entry deve essere effettivamente citata in qualche SKILL.md)
- `test_no_orphan_commands` — ogni `commands/forge-X.md` ha skill backing OR è logic-heavy documentato

**Effetto**: i 4 problemi rilevati durante questa sessione (count drift 30/26/25, version desync 1.62.3/1.62.4, `/forge-spec-review` whitelist, validates_via gap 4/9) sono ora **bloccati automaticamente da CI/pytest** alla prossima recidiva. Promessa = test.

**Allowlist evidence_type estesa**: scoperti `file_pattern` (siae-brainstorming) e `git_state` (siae-git-workflow) in uso ma non documentati; aggiunti all'allowlist.

## [1.63.1] - 2026-05-20

### Fixed — Reconcile bot bump 1.63.0 + self-audit fix 3 MAJOR di v1.62.3/v1.62.4

**Context**: durante l'apertura PR #263 (rationalization v1.62.4), il bot
`chore/bump-version-1.63.0` ha mergiato un auto-bump a 1.63.0 (PR #262) con
`marketplace.json` description stale (`39 skill, 8 comandi, 3 agent, 20 hook`)
e `plugin.json` description con count `17 comandi` (pre-cleanup v1.62.2). Il
rebase ha richiesto reconciliation: tengo i count empirici corretti e bumpo
a 1.63.1.

**Description finale empirica:**
- 43 skill (immutato dalle release recenti)
- 10 comandi (post-cleanup v1.62.2)
- 5 agent (immutato)
- 25 hook (count empirico verificato)

### Fixed — Self-audit: 3 MAJOR introdotte da v1.62.3/v1.62.4 chiuse

Code review della PR #263 ha identificato che la PR stessa (mentre razionalizzava il catalog e chiudeva gap anti-dilution) ha introdotto **3 nuove regressioni anti-dilution**: count drift, version drift e file tree incoerenza. Il code-reviewer ha sintetizzato il pattern: *"l'auditor non audita se stesso"*.

**Fix MAJOR-1 — Count hook drift revert.** v1.62.3 dichiarava di fixare drift `25 → 30 hook` perché aveva contato male (`ls hooks/* | grep -v '\.md$'` includeva `lib/`, `run-hook.cmd`, `skill-advisory-helpers.sh`, `hooks.json`). Count empirico corretto: **25 hook file netti** (`ls hooks/` escludendo `.md`, `.json`, `lib/`, `run-hook.cmd`, `skill-advisory-helpers`). Revert in 4 punti:
- `plugin.json` description: `30 hook` → `25 hook`
- `marketplace.json` description: idem
- `README.md:18` (TL;DR header)
- `README.md:251` (sezione "Hook (30)" → "Hook (25)") + indice + ancora link

**Fix MAJOR-2 — README version sync.** v1.62.4 ha bumped `plugin.json`/`marketplace.json`/`CHANGELOG` a `1.62.4` ma ha lasciato `README.md:22` metadata tabella su `1.62.3`. Aggiunto inoltre row mancante `| 1.62.4 |` nella tabella "Release recenti" del README.

**Fix MAJOR-3 — File tree README incoerenza.** File tree dichiarava `25 trigger script` mentre testo poco sopra dichiarava `30 hook`. Ora entrambi `25` (count empirico).

**Fix MINOR-1 — SDLC diagram ADR removal.** Diagramma backbone `1. BRAINSTORMING → 7-step design intake → opzioni → ADR` aveva ancora `ADR` come output, ma `docs/adr/` non esiste. Sostituito con `→ doc` (design doc `docs/plans/<topic>-design.md`).

**Lezione (memoria candidata):** quando una release dichiara di chiudere drift di promesse non verificabili, l'auditor stesso deve sottoporsi a verifica empirica prima del merge. Pattern follow-up identificato dal code-reviewer: aggiungere `tests/test_count_consistency.py` deterministico che verifica `plugin.json` count == `len(glob hooks/*)` empirico, `marketplace.json` count == `plugin.json` count, skill count == `len(glob skills/*/SKILL.md)`, command count == `len(glob commands/*.md)`. Senza test, il drift si ripresenterà alla prossima release.

**Verdetti review PR #263:**
- code-reviewer: CHANGES REQUESTED → tutti i 3 MAJOR chiusi in questo commit, verdetto atteso APPROVED
- spec-reviewer: PASS (28/28 claim CONFIRMED, 2 low-severity discrepancies cosmetiche tracciate)

## [1.62.4] - 2026-05-20

### Added/Fixed — Anti-dilution gap closure

Audit anti-dilution su 9 backbone skill ha rilevato **4 gap di evidence contract** e **5 menzioni ADR fantasma** nel README. Il backbone enforcement è efficace solo se ogni skill backbone dichiara `validates_via` nel frontmatter — altrimenti i gate hook non possono verificare il completamento e l'utente può claimare "fatto" senza evidence concreta.

**1. validates_via aggiunto a 4 backbone skill (closure gap):**

| Skill | predicate | evidence_type | check |
|---|---|---|---|
| `siae-writing-plans` | `plan_produced` | `file_exists` | `docs/plans/<topic>/overview.md` con task-NN files + marker `[PENDING]`/`[DONE]` |
| `siae-debugging` | `root_cause_identified` | `log_event` | `debugging_root_cause` event con `hypothesis_validated=true` |
| `siae-security` | `security_review_run` | `log_event` | `security_check` event per current task_id |
| `siae-finishing-branch` | `pre_flight_passed` | `log_event` | `finishing_branch_verdict` event con `verdict=PASS` |

Coverage backbone evidence contract: 5/9 (56%) → **9/9 (100%)**.

**2. README ADR fantasma rimossi (5 occorrenze):**

Il README v1.62.3 citava `docs/adr/ADR-001…ADR-009`, `### Evidence contract (ADR-002)`, `### Task-scoped enforcement (ADR-001)`, `ADR-2 MCP bridge`. La directory `docs/adr/` non esiste e nessun ADR è mai stato creato. Promesse non mantenute = dilute trust nel catalog. Rimosse:
- Riferimento alla directory `docs/adr/` nel file tree
- `ADR-001`/`ADR-002` dalle section headers Evidence contract / Task-scoped enforcement
- `ADR-2` dalla tabella release recenti (v1.57.0)

**Rationale**: il principio anti-dilution è che ogni promessa del catalog deve essere verificabile. Documentazione che cita strutture inesistenti è anti-dilution debt che si accumula nel tempo.

**Follow-up identificati (NON in questa release):**
- **8 escape hatches attivi** (`DEVFORGE_SKIP_*` × 6 + `DEVFORGE_FORCE_*` × 2): proporre consolidamento in singolo `DEVFORGE_SKIP=<feature>` con allowlist temporanea (3 usi/giorno tracked).
- **10+ piani vecchi orfani** in `docs/plans/` con marker `[PENDING]` ≥60 giorni (best-practices-alignment 12/12 PENDING, session-aware-enforcement, superpowers-improvements): archiviare in `docs/plans/archived/` con marker `[ABANDONED]`.
- **57 file dup iCloud untracked** (`X 2.py`, `X 3.sh`): aggiungere pattern `* [0-9].*` a `.gitignore`.

## [1.62.3] - 2026-05-20

### Removed/Fixed — Contraddizioni catalog (allineamento)

Audit sistematico del catalog DevForge ha rilevato 16 contraddizioni interne fra ciò che le SKILL.md prometteono e ciò che esiste:

**1. 14 `/forge-X` fantasma rimossi dalle SKILL.md description.** Citati come trigger ma il file `commands/` non esisteva (mai creato oppure eliminato in 1.62.2). Le skill restano invocabili tramite trigger sentence naturali (presenti nel description).

| Fantasma rimosso | Skill | Sostituzione |
|---|---|---|
| `/forge-automate` | siae-automation | "automatizza test", "setup Playwright/Cypress" |
| `/forge-autoresearch` | siae-autoresearch | "ottimizza skill", "analizza performance skill" |
| `/forge-blind-review` | siae-blind-review | "blind review", "audit spec-vs-codice" |
| `/forge-cost` | siae-finops | "stima costi PR", "Infracost" |
| `/forge-doc` | siae-documentation | "richiesta documentazione" |
| `/forge-finops` | siae-finops | "review costi AWS" |
| `/forge-flows` | siae-nr-test-flows | "NRT suite", "mappa flussi" |
| `/forge-jasper` | siae-jasper-from-pdf | "jrxml da pdf" |
| `/forge-logic-build` | siae-service-logic-map | "build catalogo L1/L2/L3" |
| `/forge-logic-search` | siae-service-logic-map | "cerca workflow di X" |
| `/forge-map` | siae-codebase-map | "mappa codebase" |
| `/forge-qa` | siae-qa | "genera test plan Xray" |
| `/forge-retro` | siae-retrospective | "retrospettiva", "lezioni apprese" |
| `/forge-sysmap` | siae-microservices-map | "mappa sistema", "topologia distribuita" |

Mantenuto solo `/forge-spec-review` come **anti-esempio intenzionale** in `siae-subagent-development` Permission Denied ("NON inventare slash command", documentazione difensiva).

**2. Count hook drift fixed.** `plugin.json` / `marketplace.json` dichiaravano "25 hook" ma quelli reali sono **30**. Aggiornato.

**Rationale**: zero false promesse, catalog onesto. Un utente che digita un comando inesistente prima vedeva "command not found"; ora trova solo trigger sentence naturali che il modello sa interpretare.

**Trade-off accettato**: ridotta discoverability slash per i 14 comandi mai esistiti. Le skill restano scoperte via descrizione + skill catalog injection.

## [1.62.2] - 2026-05-20

### Removed — Slash command thin-wrapper

Elimina 8 slash command che erano "thin wrapper" di una singola skill (testo unico: "Invoca la skill X e seguila esattamente") senza logica propria, allowed-tools speciali, argomenti, o multi-step. Le skill restano pienamente invocabili via **trigger sentence** (frase naturale: es. "scrivi test prima del codice" → `siae-tdd`).

**Eliminati (8):**
| Slash command rimosso | Skill backing | Come invocare ora |
|---|---|---|
| `/forge-automate` | `siae-automation` | "automatizza test", "setup Playwright", "setup Cypress" |
| `/forge-cost` | `siae-finops` | "stima costi PR", "Infracost", "shift-left FinOps" |
| `/forge-doc` | `siae-documentation` | "genera HLD", "genera LLD", "documentazione tecnica" |
| `/forge-finops` | `siae-finops` | "review costi AWS", "ottimizzazione risorse", "tag compliance" |
| `/forge-flows` | `siae-nr-test-flows` | "NRT suite", "flow map test", "test list per sezione" |
| `/forge-jasper` | `siae-jasper-from-pdf` | "jrxml da pdf", "ricostruisci jasper" |
| `/forge-test` | `siae-tdd` | "TDD per feature", "Red-Green-Refactor", "scrivo test prima" |
| `/forge-mcp-snapshot` | (utility, no skill) | invocare manualmente lo script (raramente usato, 0 ext-refs) |

**Mantenuti (10):** comandi con logica/argomenti propri o allowed-tools speciali — `code-coverage`, `forge-adoption`, `forge-analytics`, `forge-evidence`, `forge-execute`, `forge-fix-evidence`, `forge-implement`, `forge-mcp-preflight`, `forge-release-risk`, `forge-score`.

**Rationale:** la skill catalog è la fonte primaria di discovery; gli slash command devono essere un'optimization, non un duplicato. Il count 18→10 riduce friction discovery, allinea con principio anti-bloat e con la regola "comando esiste = ha logica oltre a invocare la skill".

**Trade-off accettato:** ridotta discoverability per gli 8 comandi rimossi. Le menzioni `/forge-<nome>` residue nelle SKILL.md description restano come trigger sentence colloquiale (il modello le interpreta in chat), ma l'autocompletion slash sparisce.

## [1.62.1] - 2026-05-20

### Fixed — Execution handoff slash command mancante

Quando `siae-writing-plans` completava il piano e proponeva l'Opzione 2 ("sessione separata"), il modello inventava per simmetria con `/forge-implement` uno slash command `/forge-execute` che non esisteva — l'utente apriva la nuova sessione, digitava il comando suggerito e otteneva "command not found". Cause: (a) `/forge-execute` mai registrato in `commands/`, (b) `writing-plans-execution-handoff.md` istruiva un handoff in prosa libera ("Carica il piano con: cat docs/plans/...") senza ancorare il modello a uno slash command esistente, (c) `siae-subagent-development` permission-denied path emetteva istruzioni "Apri una nuova sessione ... e incolla questo prompt" senza nominare un comando concreto.

**Aggiunte:**
- Nuovo slash command `/forge-execute` → invoca `siae-executing-plans` (pendant di `/forge-implement` per la sessione separata)

**Modifiche:**
- `skills/siae-writing-plans/reference/writing-plans-execution-handoff.md` — Opzione 2 emette ora un blocco prompt esatto con `/forge-execute docs/plans/<topic>/overview.md`, con anti-pattern documentato ("NON dire 'incolla il prompt qui sopra fino a Procedi'")
- `skills/siae-subagent-development/SKILL.md` Permission Denied — vieta esplicitamente l'invenzione di slash command, distingue Implementer (`/forge-execute`) da reviewer (trigger sentence + blocco prompt copy-paste)

**Memoria correlata:** `feedback_verify_code_before_documenting` (grep nomi prima di referenziarli)

## [1.62.0] - 2026-05-19

### Added — Tiered CLAUDE.md generation

Implementa best practice Anthropic post [How Claude Code works in large codebases](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start) (14 mag 2026): generazione automatica gerarchia `CLAUDE.md` (L1 root + L2 package + L3 child on-demand) con import `@` chain e anti-bloat.

**Nuova sub-skill `siae-codebase-map-tiered`**
- Invocata da `siae-codebase-map` Step 7a quando flag `--tiered` presente
- Genera L1 root (`./CLAUDE.md`, <200 righe big picture)
- Genera L2 per ogni Maven module / TS package (`./<module>/CLAUDE.md` con import `@../CLAUDE.md`)
- Genera L3 child on-demand solo se subdir >=10 file AND pattern locale distintivo (anti-bloat)

**Nuovo hook `session-start-tiered-advisor`**
- Async, non-bloccante (exit 0 sempre — memory `feedback_session_start_hook_invariants`)
- Matcher `startup|resume` (escluso `clear|compact`)
- Rileva CLAUDE.md mancante → suggerimento via `additionalContext`
- Rileva stale (>=30 commit OR >14 giorni dal `last_mapped`) → suggerimento update
- Timeout 3s hard cap, errori silent

**Script Python (stdlib only, Python 3.9+):**
- `scripts/emit-claude-md.py`: frammenta `docs/CODEBASE_MAP.md` → CLAUDE.md gerarchici (90% coverage, 6/6 test PASS)
- `scripts/anti-bloat-lint.py`: lint advisory exit-0 (line_count, parent_overlap, placeholder, missing_import, empty_sections — 94% coverage, 18/18 test PASS)

**Modifiche `siae-codebase-map`**
- Step 7 split: 7a (tiered mode opt-in) + 7b (mono-file default, comportamento invariato)
- Zero-regression: `/forge-map` senza `--tiered` produce CODEBASE_MAP.md identico a prima

**Test:**
- 32 nuovi test (6 emit + 18 anti-bloat + 8 hook tiered-advisor) — TUTTI PASS
- Test no-regression hook count bumped 25 → 26

**Design e piano:**
- Design doc: `docs/plans/2026-05-19-tiered-claude-md-design.md`
- Piano implementativo: `docs/plans/2026-05-19-tiered-claude-md/` (overview + 8 task)

**Note operative:**
- Per attivare: `/forge-map --tiered` su repo Maven multi-module o monorepo TS
- L'hook advisory è async, non blocca boot
- Anti-bloat lint mostra warning su stdout, exit code 0

## [1.60.0] - 2026-05-19

### Added — Security Hook Vulnerability Prevention Library (Wave 1)

Estensione DevForge per intercettare automaticamente codice con vulnerability pattern OWASP/JWT/XSS + 5 SIAE-specific famiglie dal pentest 2026-05-18 broadcasting.

**5 Semgrep custom rules SIAE attive in `rules/semgrep/siae/`:**
- F1 `siae.formula-injection.ts.csv-row-join-naive` + sibling `csv-rows-join-newline-naive` (CWE-1236 + CWE-93)
- F2 `siae.authz-tenant.ts.dao-missing-tenant-filter` (CWE-639 IDOR)
- F4 `siae.soft-delete.sql.view-only-state-filter` (CWE-639 soft-delete bypass)
- F6 `siae.authz-tenant.ts.query-param-tenant-override` (CWE-639)
- F26 `siae.jwt.ts.jwt-in-localstorage` (CWE-1004 + CWE-79)

**Architettura layered (5 layer):**
- L1 community Semgrep `auto` ruleset (preserved)
- L2 SIAE custom YAML rules con DIR auto-discovery
- L3 structured suppression engine + PR-gate schema validation (ADR-009)
- L4 balanced severity (ADR-005) — ERROR+HIGH = critical (block); WARNING = high bucket (visible, no block default)
- L5 performance: `--diff-aware` env-driven, `--jobs` parallel, `--timeout=10` per-file (ReDoS protection)

**Componenti aggiunti:**
- `lib/review_evidence/suppression.py` + `suppression_validator.py` (parse + apply + ADR-009 schema validation hard)
- `lib/review_evidence/drools_check.py` (ADR-007 Form A label + Form B header)
- `lib/review_evidence/tools/fp_rate.py` (ADR-005a FP measurement, thresholds 5%/10%)
- `rules/semgrep/siae/` con MANIFEST.md + README.md + suppressions.yaml + version.lock
- 14 fixture sintetiche in `tests/fixtures/semgrep_siae/synthetic/` (ADR-004 no broadcasting reale)

**Componenti modificati:**
- `lib/review_evidence/runners/semgrep.py` — version check ≥1.50, layered config DIR, by_family parsing, EVIDENCE_TOOL_MISSING distinct exit
- `lib/review_evidence/scoring.py` — `SecurityFindings.tool_unavailable` factory + `by_family` field
- `hooks/pr-gate` — suppressions schema validation + Drools `.drl` review check
- `skills/siae-security/SKILL.md` — Rule Reference section con 5 rule documentate

**Test coverage:** 56/56 PASS (19 regression + 17 SIAE MVP + 8 perf + 14 suppression + 10 FP/Drools).

**Riferimenti:**
- Design v2.1: `docs/plans/2026-05-18-security-hook-vulnerability-prevention-design.md` (9 ADR, 23 AC, 46 edge-case CRITICAL chiusi)
- Pentest: `pentest-broadcasting/PENTEST_REPORT.md` (2026-05-18 itsiae/broadcasting-*)
- North Star: zero-bug-jul-2026
- PR: [#255](https://github.com/itsiae/siae-dev-forge/pull/255)

**Breaking changes:** nessuno. Backward-compatible via env `DEVFORGE_SEMGREP_CONFIG`.

## [1.57.0] - 2026-05-14

### Added — Release Risk Assessment
- **siae-release-risk** skill: pre-deploy risk assessment per release branch (18 criteri, score 0-36, level LOW/MEDIUM/HIGH/CRITICAL, decision GO/POSTPONE/NO_GO)
- **/forge-release-risk** slash command on-demand
- **hooks/pr-release-gate** PostToolUse Bash hook automatic su `gh pr create --base main` con head `release/**` (advisory-only)
- 3 controlli aggiuntivi vs skill esterna originale:
  - Criterion 16: Functional regression delta vs precedente release (coverage + test disabled/deleted)
  - Criterion 17: Security vulnerability state (MVP HEAD-only via pip-audit + npm-audit)
  - Criterion 18: Unexpected feature in release (genesis confirmation Step 4b)
- Integrazione MCP sport-kg per critical service detection (Criterion 5) via JSON prefetch bridge
- Cache `(branch, diff-hash, baseline-main-sha)` per skip re-run idempotenti
- Output versionato `docs/releases/<date>-<service>-<branch>.md` + PR comment auto con idempotency marker
- Activity ledger event `release-risk` via `devforge_log`

### Changed
- Plugin manifest: bump 1.56.0 → 1.57.0
- Plugin description: count audit accurato (42 skill, 17 comandi, 5 agent, 24 hook)

### Reference
- Design doc: `docs/plans/2026-05-14-siae-release-risk-design.md` (13 ADR)
- Plan: `docs/plans/2026-05-14-siae-release-risk/` (42 task bite-sized)

### Out of scope (backlog futuro)
- CVE per-ID identification (v3.x)
- Criterion 17 delta vs baseline (v2.x — richiede extension EvidenceV2 schema)
- Maven security runner (estensione runners/)
- 4 controlli aggiuntivi: data migration delta, perf regression, contract breaking, OCP drift
- Auto-calibrazione weight via incident correlation
- CAB ticket auto-creation
- Dashboard release-risk in siae-dev-analytics
- Tag-creation hook + auto-block evolution

## [Unreleased] — v1.55.0 (review-evidence v2 scoring)

### Added

- **Schema v2** (`lib/review_evidence/schema.py`): `ScoreCard`, `RegressionVerdict`
  (5 decision branch: AUTO_APPROVE / REVIEWER_HANDOFF / BLOCK_HARD_FLOOR /
  BLOCK_REGRESSION / SEVERELY_DEGRADED), `ReviewerVerdict`, `EvidenceV2` extension
  additive con forward-compat v1.
- **Score algorithm** (`lib/review_evidence/scoring.py`): 5 score functions
  (security/quality/coverage/spec/discipline) + `compute_overall` con D6
  severely_degraded handling. Coverage anti-gaming via `lines_covered` drop
  penalty (CRITICAL B1+B7+C5).
- **5 OSS runner MVP** (`lib/review_evidence/runners/`): bandit, gitleaks,
  pip-audit, npm-audit, eslint-security. Zero costo licenza, no Qodana
  commercial dependency.
- **`arch_drift` check** (`lib/review_evidence/checks/arch_drift.py`): detect
  violazioni `forbidden_paths` configurate in `.devforge-arch.yml`.
- **Config parsers** (`lib/review_evidence/config.py`): `.devforge-scores.yml`
  (weights + hard_floors + regression_budget) + `.devforge-arch.yml`. Weights
  validation sum ~= 1.0 (E4 fix). Config change detection in PR (CRITICAL B3 fix).
- **Hook bash v2 extension** (`hooks/review-evidence`): 5 decision branch case
  per gestire `regression_verdict.decision`. v1 fallback preservato.

### Changed

- `lib/review_evidence/collector.py`: extension `orchestrate_v2()` per scoring
  layer. v1 `orchestrate()` stays for back-compat.

### Added (PR-B advanced)

- **Baseline cache S3** (`lib/review_evidence/baseline_cache.py`): S3 backend
  via boto3 + local fallback (`~/.claude/review-evidence-baseline-local`).
  Cache key = main HEAD SHA, **NO TTL** (A1 CRITICAL fix). Force-push
  invalidation via `git cat-file -e` (A2 fix). OIDC IAM trust provisioned per
  `itsiae/*` repos (Task 16 Terraform).
- **`skill_adoption` check** (`lib/review_evidence/checks/skill_adoption.py`):
  4-tier fallback signal (activity.jsonl -> design doc -> git log -> neutral)
  per discipline score. Bot PR detection (Dependabot, Renovate) -> discipline
  skip (no false negatives su auto-bumps).
- **Regression analyzer** (`lib/review_evidence/regression.py`): budget
  snapshot at PR_OPEN_TIME (E1 CRITICAL fix — admin change budget post-PR non
  sposta snapshot), 5 decision branch enforcement, hard floor **NON-overridable**
  da reviewer agent (F1+E5 CRITICAL fix).
- **Reviewer agent Step 0.6** (`agents/code-reviewer.md`): 5 decision branch
  gatekeeper logic. AUTO_APPROVE emette comunque review summary advisory
  (W2 fix). BLOCK_HARD_FLOOR ignora reviewer APPROVED (solo admin BREAK-GLASS).
- **Skill `/forge-score`** (`commands/forge-score.md`): on-demand score card
  markdown 5-dim copy-paste pronto per `gh pr comment`. Advisory only.
- **40 edge case** (8 CRITICAL + 17 HIGH + 9 LOW) mitigati con chaos test
  suite v2 (15+ test failure-injection): cache S3 unreachable, force-push
  baseline, budget tampering, severely_degraded fallback, hard floor F1+E5.
- **Terraform module** (`infra/terraform/review-evidence-baseline/`):
  S3 bucket `itsiae-review-evidence-baseline-prod` (eu-west-1, versioning
  on, encryption SSE-S3) + IAM role OIDC trust per `repo:itsiae/*`.
- **E2E test full pipeline** (`tests/test_review_evidence_e2e.py` v2 extension):
  hook bash -> collector -> S3 baseline -> reviewer agent contract.

### Added (siae-fix-evidence skill)

- **Skill `siae-fix-evidence`** (`skills/siae-fix-evidence/SKILL.md`): auto-fix
  loop hook-driven per `BLOCK_REGRESSION` review-evidence v2. Skill composer
  che legge `block_reasons` atomici e dispatcha `siae-tdd` o
  `siae-code-standards` via Skill tool (ADR-7 dynamic prompt) fino ad
  `AUTO_APPROVE` o escalation. Max 5 iter, token budget 200k, oscillation
  guard (stesso `frozenset(block_reasons)` 2 iter consecutivi -> escalate).
- **Fix parser** (`lib/review_evidence/fix_parser.py`): `parse_block_reasons`
  riusa `evidence_from_json` (forward-compat 1.x/2.x). MVP 2 atomic patterns:
  `coverage_below_threshold:X<Y` -> `siae-tdd` (priority 2), `lint_errors:N>M`
  -> `siae-code-standards` (priority 1, applied first per minimizzare blast
  radius). Unknown reasons -> `FixAction(kind="unknown", sub_skill=None)`
  per escalation safety vs crash. 3 pattern follow-up MVP (complexity, drift,
  ci_critical) marcati TODO in-code.
- **Test unit** (`tests/test_fix_parser.py`): 5 test (coverage match, lint
  match, both sorted by priority, unknown reason, empty reasons). E2E loop
  test deferred a follow-up PR-D.
- **Command `/forge-fix-evidence`** (`commands/forge-fix-evidence.md`):
  espone la skill con `allowed-tools: Read, Bash, Skill`. Pre-flight check
  documentato (working tree pulito + evidence presente + decision ==
  BLOCK_REGRESSION + hard_floor_breaches vuoto).
- **Env vars** (`hooks/ENV_VARS.md`): `DEVFORGE_FIX_EVIDENCE_TOKEN_BUDGET`
  (default 200000), `DEVFORGE_FIX_EVIDENCE_MAX_ITER` (default 5).

### Added (auto-trigger fully-autonomous, follow-up PR #244)

- **Auto-trigger pattern fully-autonomous** (`hooks/review-evidence` +
  `skills/siae-fix-evidence/SKILL.md`): chiude il loop "zero bug usando
  DevForge" senza azione utente manuale. Quando `DEVFORGE_FIX_EVIDENCE_AUTO=1`
  e il hook emette `BLOCK_REGRESSION` (no hard floor, no bot, not degraded),
  il campo `additional_context` include signal canonico grep-friendly
  `AUTO_FIX_TRIGGER:/forge-fix-evidence:sha=<SHA>`. L'agent (Claude Code)
  intercept signal PRIMA di propagare il block all'utente, auto-invoca
  `siae-fix-evidence` skill, e ri-prova action originale su `AUTO_APPROVE`.
- **Env var** `DEVFORGE_FIX_EVIDENCE_AUTO` (default `0`, opt-in): attiva il
  pattern auto-trigger. `0` = no behaviour change vs MVP manuale
  `/forge-fix-evidence`.
- **Signal additivo** (NOT replace block): `decision:block` resta per safety,
  signal in `additional_context` per intercept agent. Hook resta single-file
  (B3 PR #243 fix preserved).
- **Skip conditions hook-level** identiche alla skill: `hard_floor_breaches`
  non vuoto, `GITHUB_ACTOR` matches bot pattern (`dependabot[bot]`,
  `renovate[bot]`, `github-actions[bot]`), decision SEVERELY_DEGRADED /
  BLOCK_HARD_FLOOR (case branch separati). Telemetry log
  `evidence_auto_fix_trigger_emitted` / `_skipped`.
- **Test** (`tests/test_review_evidence_auto_trigger.py`): verifica signal
  emitted on AUTO=1 + clean BLOCK_REGRESSION, no signal on AUTO=0,
  no signal su hard_floor_breaches non vuoto / bot actor.

### BREAKING (default behavior change, follow-up `feat/fix-evidence-auto-trigger`)

- **`DEVFORGE_FIX_EVIDENCE_AUTO` default flipped `0` -> `1`.** L'auto-trigger
  fully-autonomous e' ora il comportamento **default** invece di opt-in.
  Motivazione: DevForge default opinionato verso "zero bug usando DevForge"
  — ogni `BLOCK_REGRESSION` clean (no hard floor, no bot, not degraded)
  tenta un auto-fix loop prima di propagare il block all'utente.
- **Opt-out kill-switch:** `export DEVFORGE_FIX_EVIDENCE_AUTO=0` disabilita
  globalmente l'auto-trigger (comportamento pre-flip). Skip conditions
  semantic (hard floor / bot PR / SEVERELY_DEGRADED) restano invariate come
  safety net e non emettono mai il marker, indipendentemente dal valore env.
- **Test updates** (`tests/test_review_evidence_auto_trigger.py`): il caso
  `test_block_regression_without_auto_emits_no_signal` (AUTO=0 esplicito)
  resta verde — opt-out funziona. Il caso
  `test_block_regression_auto_unset_emits_no_signal` rinominato e invertito
  (`test_block_regression_auto_unset_emits_signal_by_default`) — default
  ON, signal ora emesso quando env unset.
- **Hook bash** (`hooks/review-evidence`): `${DEVFORGE_FIX_EVIDENCE_AUTO:-0}`
  -> `${DEVFORGE_FIX_EVIDENCE_AUTO:-1}`. Tutto il resto invariato
  (skip conditions, telemetry log `evidence_auto_fix_trigger_emitted` /
  `_skipped`, single-file architecture B3).

### Configuration

- `.devforge-scores.yml` template: `docs/templates/.devforge-scores.yml`
- `.devforge-arch.yml` template (esistente)
- JSON Schema draft-07: `docs/schemas/devforge-scores.schema.json`

### Docs

- `hooks/ENV_VARS.md`: sezione "Review Evidence v2 — Scoring (v1.55+)" estesa
  con PR-B vars (`DEVFORGE_BASELINE_S3_*`, `DEVFORGE_BREAK_GLASS_REGEX`,
  `DEVFORGE_ACTIVITY_PROJECT`).
- `README.md`: sezione "Review Evidence v2 — Scoring (v1.55+)" con 5 decision
  branch, tool stack OSS, baseline cache S3, hard floor non-overridable,
  config + skill `/forge-score`.

## [Unreleased] — 2026-05-12

### Added

- **Review Evidence Hook (`hooks/review-evidence`)** — pre-calcola in modo
  deterministico coverage, lint, complessita' ciclomatica, CI quality
  reports SARIF e spec-drift per ogni SHA. Scrive evidence cacheable in
  `.claude/review-evidence/<sha>.json`. Consumato come renderer da
  `code-reviewer` e `spec-reviewer` (nuovo Step 0.5 evidence-loading) per
  verdetti riproducibili allineati a CI.
- **Multi-stack collector framework** (`lib/review_evidence/`): Java
  (jacoco + checkstyle + pmd), TypeScript (lcov + eslint +
  complexity-report), Python (coverage.py + ruff + radon), HCL (tflint +
  terraform validate).
- **CI-fetch SARIF parser** tool-agnostic (Qodana, SonarQube, CodeQL —
  qualsiasi tool che emetta SARIF 2.1.0).
- **Spec-drift detector** con code-fence robustness (estrae path solo da
  sezioni allowlist del design doc, ignora code-fence / inline code /
  blockquote).
- **Hard-block soglie** configurabili via env var (`DEVFORGE_EVIDENCE_*`)
  + bypass primario via state file `~/.claude/.devforge-skip-evidence`.
- Skill `/forge-evidence` (`commands/forge-evidence.md`) per invocazione
  on-demand.

### Changed

- `agents/code-reviewer.md`, `agents/spec-reviewer.md`: aggiunto Step 0.5
  evidence-loading prima del 6-punti / spec analysis.
- `hooks/hooks.json`: `review-evidence` registrato in PreToolUse Bash (su
  `gh pr create|edit`) e PostToolUse Bash (async cache warm su commit).

### Docs

- `hooks/ENV_VARS.md`: documentate 9 nuove env var `DEVFORGE_EVIDENCE_*`.
- `.gitignore`: aggiunto `.claude/review-evidence/`.
- `README.md`: nuova sezione "Review Evidence Hook".

## [Previous] — 2026-05-03

### Changed
- `siae-tdd` description trigger keyword ridotti da 12+ a 6 mirate
  (anti-dilution PR-6). Pattern Anthropic "Use when X".

### Removed
- `siae-tdd` trigger keyword: "implementa", "codifica", "sviluppa", "scrivi
  funzione", "aggiungi metodo", "crea classe", "modifica logica", "nuovo
  endpoint", "implementazione feature", "bug fix", "refactoring", "qualsiasi
  scrittura di codice".

### Migration path

Se invocavi `siae-tdd` con prompt come "implementa la funzione X" -> ora il
prompt attivera' `siae-brainstorming` (design first per memory backbone). Per
forzare TDD direttamente: usa "TDD per implementare X" o "Red-Green-Refactor
sulla funzione X". Comunque siae-brainstorming -> siae-writing-plans ->
siae-tdd e' il flusso canonico.
