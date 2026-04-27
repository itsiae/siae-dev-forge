---
title: Anti-Dilution Enforcement — DevForge Architectural Leap
date: 2026-04-25
status: approved
author: lodetomasi
jira: null
baseline: docs/measurements/baseline-2026-04-25/
---

# Anti-Dilution Enforcement — DevForge Architectural Leap

## Problema

Telemetria di 230 sessioni (3489 eventi, snapshot 2026-04-25 in
`docs/measurements/baseline-2026-04-25/`) rivela adoption reale
molto sotto il target dichiarato:

| Skill | Penetrazione su sessioni con commit |
|---|---|
| siae-git-workflow | 62% |
| siae-brainstorming | 38% |
| siae-tdd | 38% |
| siae-verification | 3% |
| siae-blind-review | 0% |

Quando il gate blocca, la conversione è alta (78-100%). Il problema
non è che il modello ignori i block — è che **i block non scattano
abbastanza e le skill "invocate" spesso non producono evidenza**.

### Root cause — diluizione del comportamento

Il sistema di enforcement attuale ha 3 proprietà che lo rendono
ceremoniale:

1. **Session-scoped** — skill invocata 1× ≡ valida per tutta la sessione
   anche se copre N task diversi.
2. **Invocation-based** — basta chiamare la skill, nessuno verifica che
   produca l'effetto dichiarato (test scritto, design doc, commit
   convenzionale).
3. **Text-heavy** — 2636 righe di SKILL.md nelle 5 backbone + using-devforge
   (wc -l verificato 2026-04-25). Prompt injection baseline da
   materializzare offline dal snapshot (WARN-3 spec-review). Abituazione
   → tag `<EXTREMELY_IMPORTANT>` ignorato come "wolf cry".

Effetto osservato: gate regex-based + escape hatches creano 9 vie di
fuga documentate (vedi Appendice A).

## Obiettivo

Riportare adoption reale a ≥80% per-task (non per-sessione) su tutte
le 5 skill core del backbone, riducendo la superficie testuale e il
rumore di iniezione.

## Decisioni architetturali

### ADR-001 — Task-scoped enforcement

skill_key = (task_id, skill_name) invece di (session_id, skill_name).

```
task_id = sha256(branch_name + design_doc_path + design_doc_mtime)[:12]
```

Stato persistito in `~/.claude/.devforge-task-skills/<task_id>/`.
Cutover via dual-write → shadow-check → switch. Rollback via env var.

### ADR-002 — Evidence contract

Ogni skill backbone dichiara nel frontmatter `validates_via`:

```yaml
validates_via:
  predicate: <nome_predicato>
  evidence_type: state_file | log_event | file_pattern
  evidence_check: <condizione>
```

5 predicati iniziali:

| Skill | Predicato | Check |
|---|---|---|
| siae-tdd | tdd_red_green_observed | RED→GREEN transition nel task |
| siae-brainstorming | design_doc_produced | docs/plans/*-design.md mtime > session_start |
| siae-git-workflow | conventional_commit_made | regex conventional commit sull'ultimo commit del task |
| siae-verification | verification_run_passed | verification_run event exit=0 nel task |
| siae-blind-review | blind_review_completed | blind_review_verdict event nel task |

Funzione `devforge_skill_validated(skill, task_id)` in
`lib/evidence-check.sh`. Gate rewrite da:

```bash
grep -qF "$SKILL_NAME" "$SESSION_SKILLS_FILE"
```

a:

```bash
devforge_skill_validated "$SKILL_NAME" "$TASK_ID"
```

### ADR-003 — Radical SKILL.md compression

Target: 2636 → ≤1000 righe sulle 5 skill core + using-devforge (–62%).
Breakdown target per skill:

| Skill | Oggi | Target | Δ |
|---|---|---|---|
| using-devforge | 139 | 90 | –35% |
| siae-brainstorming | 652 | 220 | –66% |
| siae-tdd | 578 | 180 | –69% |
| siae-git-workflow | 744 | 220 | –70% |
| siae-verification | 345 | 180 | –48% |
| siae-blind-review | 178 | 110 | –38% |
| **Totale** | **2636** | **1000** | **–62%** |

Metodo:

| Classe | Trattamento |
|---|---|
| K (Keep) | Legge di ferro, hard-gate, checklist obbligatorie, checkpoint schema |
| M (Merge) | Sezioni ripetute cross-skill → centralizzate in `lib/*.md` |
| D (Delete) | Tabelle anti-razionalizzazione, flussi grafici, didattica, esempi inline ripetuti |

Centralizzazioni:
- `lib/risk-taxonomy.md` — Classificazione Rischio (da 5 skill)
- `lib/operational-limits.md` — Limiti operativi (da 5 skill)
- `lib/permission-denied-handling.md` — Handling permessi (da 5 skill)
- `lib/checkpoint-schema.md` — Schema output strutturato (da 5 skill)

Safety test: `tests/compression-regression/` verifica che i checkpoint
obbligatori siano ancora emessi post-compression usando eval sets
esistenti.

### ADR-004 — Prompt injection budget

**Scope fusione**: 3 hook UserPromptSubmit fusi in 1 `devforge-context`:
- `user-prompt-context`
- `devforge-reinject`
- `devforge-context-always`

**Out-of-scope fusione**: `batch-reset` resta standalone (responsabilità
distinta: reset batch-checkpoint counter, non iniezione context).

Regole del nuovo `devforge-context`:

- Max 500 token (2KB) per iniezione
- Diff-based: hash stato → reinject solo se cambiato
- `<EXTREMELY_IMPORTANT>` tier-based:
  - no tag: context informativo (default, 80% casi)
  - `<IMPORTANT>`: gate violato turno precedente (15%)
  - `<EXTREMELY_IMPORTANT>`: hard-gate attivo (5%)
- Reinject interval adaptive: skip se task-skills già complete

Target misurabile:

| Metrica | Baseline | Target |
|---|---|---|
| Bytes/sessione 50-turni | ~110KB | ≤30KB |
| `<EXTREMELY_IMPORTANT>` /sessione | ~5 | ≤1 |
| Reinject hit rate | 100% | ≤30% |

## Considered but rejected

Le due decisioni seguenti sono state valutate e scartate. Documentate
per traceability, non sono ADR attivi.

### Rejected — Personalization (maturity levels)

Considerata (maturity levels W0-W3) e scartata. Motivi:
- Complessità non giustificata per 98 utenti
- YAGNI: aggiungibile post-hoc se emergono reclami
- Un livello = `W2 hard-block` per tutti

### Rejected — Semantic gate (LLM-judge)

Considerata (LLM-judge per estensioni ambigue) e scartata. Motivi:
- Fragile: dipende dal modello in sessione rispondendo coerentemente
- Aggiunge percorso decisionale ambiguo = dilution

Sostituita da deny-by-default su estensioni ambigue (ADR-005).

## ADR attivi (continuazione)

### ADR-005 — Scope cleanup

File taxonomy esplicita in `lib/file-taxonomy.sh`:

```
tdd_required:          .java .ts .py .go .kt .rb .rs .swift .scala .sql
brainstorming_required: ^tdd_required + .tf .hcl
config_only:           .yaml .yml .json (no gate by default)
ambiguous:             .sh .bash (opt-in via DEVFORGE_BASH_TDD=1)
```

Scope repo: **mantenuto hardcoded `itsiae/*`** come oggi.
Decisione esplicita dell'utente (2026-04-25): DevForge enforcement si
applica solo ai repo dell'org `itsiae/`. Fork personali e repo di altra
natura restano esclusi per design.

Il check in tdd-gate/brainstorming-gate resta:

```bash
if ! echo "$REMOTE_URL" | grep -qE "[/:]itsiae/"; then
  echo '{}'; exit 0
fi
```

**Motivazione**:
- Vincolo di business SIAE (plugin proprietario)
- Nessun beneficio dal gating di progetti personali
- Semplicità operativa (zero config richiesta)

**Conseguenza per ADR-001 (task-scope)**: computazione `task_id` viene
**skippata** sui repo non-itsiae. I gate fanno early-exit sullo stesso
check `itsiae/*` prima di toccare task-skills. Net: zero overhead su
repo fuori scope.

### ADR-006 — Rimozione escape hatches

| Gate | Oggi | Nuovo |
|---|---|---|
| stop-gate | 2-block auto-escape | `DEVFORGE_FORCE_STOP=1` esplicito + counter |
| brainstorming-gate | `W2_DEFAULT=0` → no-op | Sempre attivo |
| pre-commit | regex substring `git commit` | Parser primo-token |

### ADR-007 — Prereq map autogenerata

`sub-skill-gate` PREREQ_MAP da 7 entry hardcoded a 39 autogenerate.
Frontmatter skill:

```yaml
prerequisites:
  - siae-brainstorming
  - siae-writing-plans
```

Script `lib/generate-prereq-map.sh` → `lib/prereq-map.generated`.
Hook lo carica e valida.

### ADR-008 — Nuovi gate

| Gate | Matcher | Check |
|---|---|---|
| pr-blind-review-gate (nuovo) | PreToolUse:Bash `gh pr create\|edit` | siae-blind-review validata per task |
| plan-gate-write (estensione) | PreToolUse:Write `docs/plans/*-design.md` | siae-brainstorming validata per task |
| evidence-stop-gate (rewrite) | Stop | verification_run event con exit=0 |
| coverage-force-run (rewrite) | PreToolUse:Bash `git commit` | Force run se coverage stale + test in diff |

### ADR-009 — Observability loop

Nuova superficie visibile:

| Componente | Dove |
|---|---|
| `/forge-adoption` command | commands/forge-adoption.md + lib/adoption-analyzer.py |
| Stop-gate recap (3 righe) | Estensione stop-gate |
| Extension siae-dev-analytics | skill esistente + dashboard |
| Gate block explainer (+dato) | Tutti i gate block messages |

## Architettura

### Componenti nuovi

```
lib/
├── evidence-check.sh          # devforge_skill_validated()
├── task-id.sh                 # devforge_compute_task_id()
├── file-taxonomy.sh           # classificazione estensioni
├── generate-prereq-map.sh     # build PREREQ_MAP da frontmatter
├── prereq-map.generated       # output autogenerato
├── adoption-analyzer.py       # core /forge-adoption
├── risk-taxonomy.md           # da ADR-003
├── operational-limits.md      # da ADR-003
├── permission-denied-handling.md
└── checkpoint-schema.md

hooks/
├── devforge-context           # fusione 3 hook (ADR-004)
├── pr-blind-review-gate       # nuovo (ADR-010)
├── (plan-gate esteso)
├── (stop-gate + recap)
├── (tdd-gate + task-scope)
├── (brainstorming-gate + task-scope)
├── (pre-commit + parser + coverage-force-run)
└── (sub-skill-gate + 39 entry)

commands/
└── forge-adoption.md          # nuovo (ADR-011)

docs/measurements/
└── baseline-2026-04-25/       # snapshot 230 sessioni (pre-change)
```

### State files

```
~/.claude/
├── .devforge-task-skills/<task_id>/
│   ├── skills_invoked
│   ├── skills_validated
│   └── metadata
├── .devforge-last-injection-hash      # diff-based reinject
└── .devforge-force-stop-count         # daily counter escape-hatch esplicito
```

### Data flow enforcement

```
user action
  ↓
PreToolUse hook
  ↓
1. compute task_id (lib/task-id.sh)
  ↓
2. load task-skills (.devforge-task-skills/<task_id>/)
  ↓
3. check validates_via (lib/evidence-check.sh)
  ↓
4. decision:
   - allow → pass-through
   - block → structured message + block explainer + dato personale
```

## Piano per PR

### PR #1 — v1.46 Foundation + Compression (SP 5/3)

**Scope**: evidence contract + compression + injection budget.
Low risk. Nessun cambio di comportamento del gate, solo cosa il gate
considera evidence.

**Deliverables**:
1. `lib/evidence-check.sh` — funzioni `devforge_skill_validated`
2. Frontmatter `validates_via` su 5 skill core
3. Compressione 5 SKILL.md backbone (2458 → ≤940 righe)
4. Centralizzazioni in `lib/*.md`
5. Fusione 3 hook → 1 `devforge-context` con budget + diff
6. Regression test `tests/compression-regression/`

**Criteri accettazione**:
- [ ] Tutti gli eval sets esistenti passano (baseline: 168 PASS / 6 FAIL / 1 SKIP, no peggioramento)
- [ ] `<EXTREMELY_IMPORTANT>` ≤1 per sessione 50-turni (misurato con nuovo evento telemetry `prompt_injection_emitted` con flag `tier`)
- [ ] Bytes/sessione ≤30KB (misurato con nuovo evento `prompt_injection_size`)
- [ ] SKILL.md backbone totale ≤1000 righe (wc -l deterministico)
- [ ] Baseline offline-computed: `docs/measurements/baseline-2026-04-25/baseline-metrics.json` con `bytes_per_session_p50/p95`, `extremely_important_count`, `reinject_hit_rate` estratti dal snapshot
- [ ] **Pre-measurement baseline task-scoped**: script `lib/measure-task-baseline.sh` genera baseline per-task simulato dal snapshot session-scoped (proxy via branch+design-doc pairing) in `baseline-metrics-tasks.json`. Serve come riferimento per PR #2 delta.

### PR #2 — v1.47 Task-Scope + Scope Cleanup (SP 5/3)

**Scope**: migrazione task-scoped + cleanup escape hatches + nuovi gate.
Medium risk, cutover fasato (dual-write → shadow → switch).

**Deliverables**:
1. `lib/task-id.sh` — computazione task_id
2. 8 gate migrati a task-scoped
3. `lib/file-taxonomy.sh` — extension classification
4. Rimozione 3 escape hatches (stop-gate, brainstorming-gate, pre-commit regex)
5. `lib/generate-prereq-map.sh` + autogen 39 entry
6. Nuovo `pr-blind-review-gate`
7. Estensione `plan-gate-write`
8. Rewrite `evidence-stop-gate` + `coverage-force-run`

**Criteri accettazione**:
- [ ] Dual-write phase funzionante (legacy + task-scoped coesistono)
- [ ] Shadow-check loggato per ≥1 giorno senza divergenza >10%
- [ ] Rollback testato via scenario: (a) set `DEVFORGE_USE_SESSION_SCOPE=1`, (b) invoca skill + commit, (c) verify `.devforge-session-skills` popolato con skill name, (d) verify `.devforge-task-skills/<id>/` assente, (e) unset env var, (f) verify comportamento task-scoped ripristinato
- [ ] Tutti i nuovi gate testati con positive + negative case
- [ ] Adoption per-task misurata post-deploy vs `baseline-metrics-tasks.json` (da PR #1)
- [ ] Abuse tracking definito per ogni bypass env var: soglia (≥5/giorno), azione (log `bypass_abuse_suspected`), visibilità (campo in `/forge-adoption`)

### PR #3 — v1.48 Observability (SP 3/2)

**Scope**: feedback loop visibile.
Low risk. Nessuna logica enforcement nuova.

**Deliverables**:
1. `commands/forge-adoption.md` + `lib/adoption-analyzer.py`
2. Stop-gate 3-righe recap
3. Extension siae-dev-analytics
4. Gate block explainer con dati personali

**Criteri accettazione**:
- [ ] `/forge-adoption` emette output atteso
- [ ] Recap stop-gate visibile a fine sessione
- [ ] Gate block explainer testato su tdd/pre-commit/stop
- [ ] Dashboard dev-analytics estesa

## Rischi e mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| task_id cambia mid-task → gate reset | Media | Alto | Evidence copy-forward: se nuovo task_id ha stesso `branch_name` del precedente E `design_doc_path` invariato (solo mtime cambiato = design revisionato), copia `skills_validated` dal task_id precedente al nuovo. Se branch E design_doc cambiano entrambi = nuovo task legittimo, no copy. Se solo branch cambia = cambio reale di lavoro, no copy. Implementato in `lib/task-id.sh::devforge_task_id_transition()`. |
| Compression rompe comportamento skill | Media | Alto | Regression test su eval sets esistenti + review incrementale per skill |
| Fusione 3 hook → 1 fa perdere eventi | Bassa | Medio | Shadow run per 1 giorno con entrambi attivi + diff log |
| Nuovi gate bloccano workflow legittimo | Media | Medio | Bypass esplicito via env var + tracking abuse |
| Utenti senior protestano per più friction | Media | Basso | Dato per-utente nel block explainer + `/forge-adoption` motiva |

## Stima

- **SP totali**: 13 SP-Umano / 8 SP-Augmented
- **Timeline**: 3 PR sequenziali, 1-2 giorni ciascuna
- **Rollback**: per-PR via env var o git revert

## Criteri di accettazione globali

- [ ] Adoption per-task ≥80% su 5 skill core (misurato 2 settimane post-PR #2)
- [ ] Bytes prompt injection/sessione ≤30KB (misurato post-PR #1)
- [ ] SKILL.md backbone ≤940 righe totali
- [ ] Zero regression su test suite esistente
- [ ] `/forge-adoption` usabile e testato

## Appendice A — 9 vie di fuga documentate

Testate empiricamente nel turno #1 di analisi:

1. `brainstorming-gate` spento di default (`W2_DEFAULT=0`)
2. `tdd-gate` limitato a 9 estensioni (org `itsiae/` **corretto per design**)
3. `stop-gate` escape dopo 2 block consecutivi
4. `plan-gate` bypassabile via Write diretto su `.md`
5. `sub-skill-gate` copre solo 7/39 skill
6. `pre-commit` regex substring fa falsi positivi/negativi
7. `coverage-gate` passa sempre se file di test non eseguiti
8. Iniezione prompt genera abituazione → wolf-cry effect
9. `blind-review` 0% — nessun gate corrispondente

Mapping problema → ADR (spec-review confermato 2026-04-25):

| # | Problema | ADR |
|---|---|---|
| 1 | W2_DEFAULT=0 no-op | ADR-006 |
| 2 | tdd-gate 9 estensioni (scope itsiae/* scelta design) | ADR-005 |
| 3 | stop-gate 2-block escape | ADR-006 |
| 4 | plan-gate bypass via Write | ADR-008 (plan-gate-write) |
| 5 | sub-skill-gate 7/39 | ADR-007 |
| 6 | Pre-commit regex substring | ADR-006 (parser primo-token) |
| 7 | Coverage-gate passa se test non eseguiti | ADR-008 (coverage-force-run) |
| 8 | Wolf-cry injection | ADR-004 (tier-based EXTREMELY_IMPORTANT) |
| 9 | blind-review 0% nessun gate | ADR-008 (pr-blind-review-gate) |

Evidence/task-scoping (ADR-001, ADR-002) sono trasversali ai 9 problemi
e trasformano l'enforcement da session-scoped a task-scoped.

## Appendice B — Baseline pre-change

`docs/measurements/baseline-2026-04-25/devforge-state-snapshot/`
(230 sessioni, 3489 eventi, 2026-04-25).
