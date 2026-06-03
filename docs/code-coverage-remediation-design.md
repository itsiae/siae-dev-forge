# Remediation design — skill `/code-coverage`

> **Fonte**: post-mortem `accertatori-data-service/docs/coverage-postmortem-skill-workflow.md`
> **Metodo**: 4 agenti ciechi indipendenti (Sonnet), un cluster ciascuno, poi sintesi.
> **Branch skill**: `feat/code-coverage-vitest-migration`
> **Data**: 2026-05-29
> **Scope**: (1) eliminare alla radice i 12 gap del post-mortem; (2) introdurre esecuzione multi-agente parallela dei task di coverage (≤4 subagent Sonnet).

---

## 0. Sintesi esecutiva

Il post-mortem documenta che la skill ha chiuso autonomamente la **line coverage** (70.10%) ma è rimasta **~19pp sotto la soglia CI reale per la branch** (47.91% vs 70% org-level), richiedendo **6 commit manuali + 1 fix CI + ~10h di lavoro umano**. Le cause sono 3 famiglie:

1. **Non conosce il target reale** prima di generare (soglie CI, working-directory, line-vs-branch gap).
2. **Genera happy-path** che massimizza line ma non branch, e non conosce le tecniche avanzate (reflection, class-mock, TZ-mock, builder full-populated).
3. **Si arrende troppo presto** (Phase 7 max 3 iter, progress guard locale, marca "intractable" ciò che era trattabile).

In più, la skill **non parallelizza realmente**: oggi splitta solo le Write tool-call dentro un turno, su un unico agente con un unico context window — ecco perché un VERY_LARGE (31k LOC) richiede ~12h: il collo di bottiglia è la **context pressure**, non l'I/O.

### Convergenze indipendenti (proposte identiche da ≥2 agenti — alta confidenza)

| # | Soluzione | Agenti che l'hanno proposta in cieco |
|---|-----------|--------------------------------------|
| K1 | `pre_existing_branch_pct` in `stack.json` (oggi si legge solo line) | A (A4), C (C4/C5) |
| K2 | **Static pre-abort analysis** unificata prima di marcare `intractable` (private/inline-new/Intl/db-only) → 1 script `classify_intractable.py` | B (B3 "Step 0"), C (C2) |
| K3 | `max_iter = min(10, max(3, ceil(batches × 1.5)))` | C (C1), D (D8), B (Flag5) |
| K4 | Nuova categoria `repair-strategies.json` per branch-gap stall | B (Flag4 "private_branch_gap"), C (C2 "branch_gap_stall") |
| K5 | `coverage_mode` line-priority vs branch-priority + branch-matrix template | A (A5.6), B (B1), C (C3 ladder) |
| K6 | Branch-operator counter via **Python regex** (NO ts-morph) | B (B2) — A/C lo presuppongono |
| K7 | CI workflow audit + CI threshold detection = **un solo pass** sui file `.github/workflows/` | A (A1+A2+A5.3) |
| K8 | Test-helper library riusabile (mockTz/mockKnex/mockClass/partialMock/builderFactory) | B (B5/B6), C (ladder consuma gli helper) |

Queste 8 convergenze sono il **nucleo** della remediation: implementarle chiude la maggior parte dei 12 gap con il minor numero di componenti nuovi.

---

## 1. Workstream consolidati (ordinati per dipendenza)

### WS-1 — Fondamenta dati (prerequisito di tutto)
**Obiettivo**: la skill deve *misurare* branch e *conoscere* il target reale prima di generare.

- **1.1** `stack.json += pre_existing_branch_pct, line_branch_delta` — leggere `coverage/coverage-summary.json` (`total.branches.pct`) e `lcov` branch. Guard: se `branches.pct==0 && lines.pct>0` → branch non disponibile (`null`). *(K1)*
  - File: `lib/phase1-discover.sh`, `scripts/detect_stack.py` (`parse_coverage_summary_for_branch()`), `lib/state-schema.json`.
- **1.2** **CI workflow single-pass** `scripts/detect_ci_thresholds.py` *(K7)*: scorre `.github/workflows/*.yaml` ed emette `ci-thresholds.json` con:
  - `COVERAGE_LINES/BRANCHES/STATEMENTS/FUNCTIONS` (anche risolvendo i reusable remoti `itsiae/siae-gh-actions/...@ref` via `gh api`, e i `${{ vars.X }}` via `gh variable get`);
  - `working_directory_issues[]` (manifest_root != "." ma reusable senza `working-directory`).
  - Invocato in parallelo da `phase1-discover.sh`.
- **1.3** `sentinel-handshake.sh`: `effective_target = max(user_target, ci_threshold)`; nuovi campi in `user-choice.json` (`user_requested_*`, `ci_threshold_override`, `ci_thresholds_source`, `high_branch_gap`); WARN in `decisions.log`. *(da A2/A4)*
- **1.4** **Stale jest detection**: fix bug reale `validate_env.py:135` (hardcoda workspace `"."` invece di `manifest_root`) + cache-key di `phase1-discover.sh` sul manifest del sub-workspace + `detect_jest_incompat.py` tagga `stale-config:` quando `scripts.test` usa vitest. *(da A3 — questo è un BUG, non solo un miglioramento)*

### WS-2 — Generazione branch-aware (Phase 3 + Phase 5)
**Obiettivo**: generare test che colpiscono i branch, non solo le righe.

- **2.1** `scripts/count_branch_operators.py` *(K6)*: conta `??`/`||`/`&&`/`?:` per file (regex AST-lite, esclude commenti/import). Output `.code-coverage/branch-count/<file>.json` + campo canonico `branch_operator_count` in `batch-plan.json`. Eseguito in Phase 3 (step 3b), JS/TS only.
- **2.2** `scripts/classify_coverage_mode.py` *(K5)*: per file → `branch-priority` se `branch_operator_count > 20` **oppure** (`line ≥ target_line·0.85` e `branch < target_branch·0.80`); altrimenti `line-priority`. Scrive `coverage_mode` in `batch-plan.json`.
- **2.3** Nuovo template `templates/vitest-branch-matrix.template.ts`: per ogni operatore genera 3 `it()` (null / undefined / present). Placeholder `{{CLASS_MOCK_BLOCK}}` e `{{TZ_MOCK_BLOCK}}`.
- **2.4** **Dual-fixture rule** (`branch_operator_count > 40`): generare fixture `minimal` + `full-populated` (chiude i ~60 `?? ""` di `assemblaLocale`).
- **2.5** Aggiornare `references/phase-5-generation.md` ("Coverage Requirements Per Module" → branch-matrix mode) e `SKILL.md` Principio 5 (target line **e** branch separati).

### WS-3 — Tecniche avanzate + helper library (Phase 4 + Phase 5/7)
**Obiettivo**: dotare la skill delle tecniche che oggi sono state scritte a mano.

- **3.1** Test-helper library *(K8)* generata in Phase 4 (se assente): `templates/helpers/{mockTz,mockKnex,mockClass,partialMock,builderFactory}.ts` → materializzati in `<repo>/src/__tests__/helpers/`. Gate PRESERVE_EXISTING.
- **3.2** Scanner statici (alimentano sia Phase 5 che la classificazione intractable):
  - `scripts/scan_private_methods.py` → reflection block.
  - `scripts/scan_class_instantiations.py` → class-mock block (escludendo `new Date/Error/Map/Set/Array/Promise/...`).
  - `scripts/scan_tz_usage.py` → TZ/Intl mock auto-injection (+ ICU probe in Phase 4).
- **3.3** Snippet template: reflection (`(inst as unknown as {m:Fn}).m.call(inst, fx)`), class-mock factory, partial `vi.mock(..., importOriginal)`.
- **3.4** Anti-pattern doc: "vi.fn() piatto per classi istanziate con `new`" → GOOD/BAD in `assets/anti-patterns.md`.

### WS-4 — Repair loop robusto (Phase 7)
**Obiettivo**: non arrendersi finché esistono tecniche non tentate.

- **4.1** `max_iter` scaling *(K3)* — `references/phase-7-repair.md` riga 11 + `SKILL.md` riga 187.
- **4.2** `scripts/classify_intractable.py` *(K2)* — classifica `NEEDS_REFLECTION | NEEDS_CLASS_MOCK | NEEDS_TZ_MOCK | INTRACTABLE_DB_DEPENDENT | INTRACTABLE_UNKNOWN`. Marca `intractable` **solo** se DB-only/unknown. Risultato cache-ato e condiviso tra i due call-point (pre-abort + global guard).
- **4.3** **Two-tier progress guard + strategy ladder**: locale `delta(N,N-1)<1pp` → *cambia strategia* (non abortire); globale `delta(N,0)<5pp` dopo ≥2 iter → BEST_EFFORT genuino. Ladder: `LINE → BRANCH_MATRIX → REFLECTION → CLASS_MOCK → TZ_MOCK → FULL_FIXTURE`.
- **4.4** `repair-strategies.json` categoria 13 *(K4)* — nome unificato `branch_gap_stall`, con `manual_hints` per ogni `NEEDS_*`.
- **4.5** `scripts/predict_coverage.py` → `coverage-prediction.json` in Phase 3 (predicted branch p6/p7, risk flags, confidence LOW/MEDIUM), mostrato nel sentinel handshake **prima** di Phase 4. Coefficienti empirici, da affinare con telemetry.

### WS-5 — Esecuzione multi-agente parallela (feature nuova richiesta)
Vedi sezione 2.

---

## 2. Architettura esecuzione parallela (Agent D)

### Decisioni chiave
- **Unità di parallelismo = il BATCH** (già calcolato da `plan_batches.py`, tier-omogeneo, file disgiunti, è già l'unità di resume). NON il file, NON il modulo.
- **≤4 subagent Sonnet** (`claude-sonnet-4-6`), attivati solo su `LARGE`/`VERY_LARGE` con `pending_batches ≥ 2`. SMALL/MEDIUM → flusso single-agent invariato.
- **Mapping**: round-robin batch→agente di default; bin-packing per effort se la deviazione dei bucket > 40%.
- **Isolation = path-disgiunti, NO worktree**: gli agenti scrivono solo spec file in path disgiunti. Il worktree (~GB/agente, richiede repo git) non serve perché non c'è merge conflict su sorgente di produzione.
- **Il coordinatore è l'unico writer dello stato condiviso**: Phase 4 (env, install, config, helpers), Phase 6 (un solo `vitest run --coverage` dopo il join — niente LCOV merge), aggiornamento `batch-plan.json`/`decisions.log`. Gli agenti **NON** lanciano coverage, **NON** toccano `package.json`/`vitest.config.ts`/sorgente.
- **Orchestrazione = Agent dispatch in parallel-tool-use (stesso turno)**, non il tool `Workflow`: il numero di agenti è dinamico, i prompt sono costruiti a runtime da `batch-plan.json`, il pattern è coerente con `siae-parallel-agents`/`siae-subagent-development`.

### Perché risolve il problema dei ~12h
Oggi il coordinatore legge **tutti** i sorgenti (context cresce con i LOC → ricompattazioni). Con il dispatch, il coordinatore conosce solo `batch-plan.json`/`stack.json`/`env.json` (~pochi KB) e **non legge mai i sorgenti**; ogni agente ha context isolato sui suoi 2-5 file. È l'implementazione architetturale del Principio #2 ("context-safety over completeness").

### OUTPUT CONTRACT del subagent (schema v1)
JSON con: `batch_id, agent_id, status(completed|partial|failed), files_written[], files_skipped_preserve[], files_failed[], intractable_flags[], decisions_log_fragment[]`. **Niente** coverage report. Il coordinatore fa merge sequenziale, aggiorna `batch-plan.json` (nuovi campi `status/assigned_to/completed_by/completed_at`), aggrega `intractable.json`, e re-queua i batch `partial/failed` in fallback sequenziale.

### Phase 7 parallelizzabile (parziale)
- Systemic fix (config condiviso) → sequenziale, coordinatore.
- Per-file fix (≥2 file, categorie diverse) → fino a 4 repair-agent in parallelo (ogni agente un file).
- Full coverage run → sempre coordinatore, 1 volta/iter.
- Ortogonale a `max_iter` scaling (WS-4.1): la parallelizzazione accelera l'iter, non riduce il numero di iter.

### Trigger / fallback
`VERY_LARGE|LARGE & pending≥2` → on. Off su: `pending==1`, `CC_NO_PARALLEL_AGENTS=1`, `overrides.json.force_sequential`, Agent tool non disponibile (verifica pre-Phase-5), batch tutti T3/T4 ceiling=1.

---

## 3. Master list file (nuovi / modificati)

### Nuovi script
| File | WS | Scopo |
|------|----|-------|
| `scripts/detect_ci_thresholds.py` | 1 | soglie CI + working-directory issues (single pass) |
| `scripts/count_branch_operators.py` | 2 | conteggio `??/\|\|/&&/?:` per file |
| `scripts/classify_coverage_mode.py` | 2 | line-priority vs branch-priority |
| `scripts/scan_private_methods.py` | 3 | private methods → reflection |
| `scripts/scan_class_instantiations.py` | 3 | `new ClassFoo()` → class-mock |
| `scripts/scan_tz_usage.py` | 3 | Intl/TZ → mock |
| `scripts/classify_intractable.py` | 4 | gate pre-intractable (unifica B3+C2) |
| `scripts/predict_coverage.py` | 4 | prediction upfront |

### Nuovi template / asset
| File | WS |
|------|----|
| `templates/vitest-branch-matrix.template.ts` | 2 |
| `templates/helpers/{mockTz,mockKnex,mockClass,partialMock,builderFactory}.ts` | 3 |
| `references/phase-5-parallel.md` (~200 LOC) | 5 |

### File modificati
| File | WS | Modifica |
|------|----|----------|
| `lib/phase1-discover.sh` | 1 | branch pct, ci-thresholds dispatch, cache-key sub-workspace |
| `scripts/detect_stack.py` | 1 | `parse_coverage_summary_for_branch`, `detect_ci_thresholds` |
| `scripts/validate_env.py` | 1 | **fix bug** workspace key (riga 135) |
| `scripts/detect_jest_incompat.py` | 1 | tag `stale-config:` |
| `lib/sentinel-handshake.sh` | 1/4 | effective_target, prediction, branch warning |
| `lib/state-schema.json` | 1/4/5 | nuovi campi/file di stato |
| `references/phase-3-sizing.md` | 2/5 | step 3b scan, coverage_mode, batch-plan schema (status/assigned_to) |
| `references/phase-5-generation.md` | 2/3 | branch-matrix mode, dual-fixture, helper auto-import |
| `references/phase-7-repair.md` | 4 | max_iter, Step 0 pre-abort, two-tier guard, strategy ladder |
| `scripts/plan_batches.py` | 2/5 | campi `branch_operator_count`, `coverage_mode`, `status` |
| `assets/repair-strategies.json` | 4 | categoria 13 `branch_gap_stall` |
| `assets/anti-patterns.md` | 3 | flat-vi.fn() per classi |
| `assets/few-shot-e2e.md` | 2 | esempio branch-matrix |
| `SKILL.md` | tutti | Principi 2/5/7; Phase 3/5/7 hook |

---

## 4. Decisioni aperte per l'utente

1. **Ts-morph vs regex** per il branch counter: gli agenti raccomandano **regex Python** (no nuova devDep, deterministico, sufficiente per i DAO). Confermi o vuoi AST vero (ts-morph)?
2. **Coefficienti di prediction**: in v1 sono empirici (calibrati su 1 post-mortem, confidence LOW). OK partire così e affinare con telemetry, o vuoi disabilitare la prediction finché non c'è più dato?
3. **Cap `max_iter`**: 9 o 10? (C propone min 10, D cita cap 9). Allineo a **10**.
4. **Worktree**: confermato NON necessario per gli spec (path-disgiunti). OK?
5. **Ordine di rollout**: WS-1 → WS-2/3 → WS-4 → WS-5 (parallel). WS-5 dà il guadagno di tempo ma WS-1..4 danno il guadagno di *qualità* (la branch coverage). Quale priorità?
