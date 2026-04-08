# siae-btp-upgrade-audit — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Creare la skill `siae-btp-upgrade-audit` in siae-dev-forge per rilevare regressioni di business logic durante l'upgrade delle librerie SAP BTP deprecate nel repo `itsiae/liquidazione`.
**Architettura:** Skill markdown **Rigid** a due fasi (BASELINE + AUDIT). Layer 1 estrae meccanicamente via bash (grep su JS, XML, CDS). Layer 2 estrae semanticamente via Claude con schema YAML locked (un file per invocazione). Diff strutturale con canonicalizzazione produce gap report per app.
**Stack:** Markdown (skill), Bash (layer1), Python3 (gh api parsing), YAML (fingerprint schema), GitHub API via `gh` CLI
**SP:** 23 SP-Umano / 8 SP-Augmented (schema v1.3)
**Design doc:** `docs/plans/2026-03-31-btp-upgrade-audit-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Skill skeleton + frontmatter + banner (tipo: Rigid) | `task-01-skill-skeleton.md` | [PENDING] |
| 2 | Phase 1: app discovery + Layer 1-A (deprecated imports + OData v2 + EventBus + model lifecycle + fragment + dialog + external formatters) + Layer 1-C (XMLView + Component.js) | `task-02-layer1-deprecated-odata.md` | [PENDING] |
| 3 | Phase 1: Layer 1-B (method signatures ES6 + navigation + routing + dataSources + model bindings) | `task-03-layer1-signatures-nav.md` | [PENDING] |
| 4 | Phase 1: Layer 2 schema-locked atomico (error_handlers + logic_blocks + nesting_depth + timing_annotations + external_calls + callbacks signatures + completeness_ratio) | `task-04-layer2-schema-locked.md` | [PENDING] |
| 5 | Phase 2: diff engine (canonicalizzazione + rename detection + diff ordinato branch_true/false + nesting_depth + completeness gate + tutti i nuovi campi v1.3) | `task-05-diff-engine.md` | [PENDING] |
| 6 | Phase 2: gap report generator (CRITICAL count metrica primaria + merge safety CRITICAL=0 AND LOGIC DIFF≤3) | `task-06-gap-report.md` | [PENDING] |
| 7 | Registrazione skill + smoke test positivo + negative test su `appavvisi` | `task-07-registration-test.md` | [PENDING] |
| 8 | Layer 1-D: CAP CDS handlers + security checks + lib modules + context accesses + annotations (SOLO liquidazione root srv/ — NON wf_*) | `task-08-cap-cds-layer.md` | [PENDING] |
| 9 | Layer 1-E: pre-location trasformazioni dati + timing logic (grep hints per Layer 2) | `task-09-layer1e-data-transforms.md` | [PENDING] |

## Dipendenze

- Task 2 e 3 dipendono da Task 1
- Task 2 e 3 sono eseguibili in parallelo tra loro
- Task 4 dipende da Task 2+3
- Task 8 dipende da Task 2+3 (eseguibile in parallelo con Task 4)
- Task 9 dipende da Task 2+3 (eseguibile in parallelo con Task 4 e Task 8)
- Task 5 dipende da Task 2+3+4+9
- Task 6 dipende da Task 5
- Task 7 dipende da Task 1–6 (e idealmente Task 8+9)

## Note Architetturali (fix da panel 5 esperti — 2026-03-31)

### Fix critici applicati al piano

| Fix | Task coinvolto | Problema risolto |
|-----|---------------|-----------------|
| `gh api` branch→SHA resolution | Task 02, 03, 07 | Branch name non funziona in `/git/trees/` → 404 |
| Layer 1-C XMLView + Component.js | Task 02 | Formatter, event bindings, model registration non tracciati |
| OData v2 API completa | Task 02 | submitChanges, setProperty, bindElement non rilevati |
| dataSources manifest.json | Task 03 | URI servizio OData non tracciata → cambio URL invisibile |
| Method signatures ES6 | Task 03 | Arrow functions e lifecycle hooks non catturati |
| Layer 2 atomico | Task 04 | Ambiguità unità elaborazione → variabilità output |
| Canonicalizzazione verbatim | Task 05 | Falsi positivi per whitespace differences |
| Rename detection | Task 05 | Alert fatigue: metodo rinominato = CRITICAL + INFO invece di suggerimento |
| Regole diff XMLView/Component/dataSources | Task 05 | Nuovi campi schema senza regole diff |
| CRITICAL count come metrica primaria | Task 06 | OK% fuorviante: app con 6 CRITICAL mostrava "75% OK" |
| Negative test | Task 07 | Nessuna prova che il tool rilevi effettivamente regressioni |
| Catalog registration corretto | Task 07 | Edit manuale `using-devforge` → sovrascritto alla rigenerazione |
| Layer 1-D CAP CDS | Task 08 | `srv/*.js` handlers e annotations non tracciati per moduli wf_* |
| Skill type Rigid | Task 01, SKILL.md | Flexible permetteva adattamenti che rompevano il determinismo |

### Checkpoint e parallelismo (per --all mode, 70+ app)

- Salvare fingerprint su filesystem dopo ogni app: `fingerprints/old/{app}.yaml`
- Non tenere fingerprint in memoria tra un'app e l'altra (rischio perdita su crash)
- Per batch >10 app: usare `siae-parallel-agents` con batch da 10 app per sessione
- In caso di crash: riprendere dall'ultimo `{app}.yaml` già salvato

### Tipi di moduli nel repo `itsiae/liquidazione` (v1.3 — ARCHITECTURAL FIX)

- `app*`: SAPUI5 Fiori puri → Task 1-7+9 (Layer 1-A, 1-B, 1-C, Layer 1-E, Layer 2)
- `liquidazione` (root): CAP CDS service → Task 1-8+9 (aggiungere Layer 1-D)
- `wf_*`: **SAP BPM workflow modules (YAML/XML) — NON CAP services — SALTARE sempre**

### Schema Version History

| Versione | Campi aggiunti |
|----------|---------------|
| v1.0 | Base: deprecated_imports, odata_v2_calls, method_signatures, navigation_targets, routing_config, error_handlers, logic_blocks, external_calls |
| v1.1 | xmlview_bindings, component_models, data_sources, cap_handlers, cds_annotations, cap_config |
| v1.2 | branch_true/false come liste, nested conditions, data_transforms, external_calls.callbacks |
| v1.3 | nesting_depth, timing_annotations, completeness_ratio, eventbus_calls, model_lifecycle_handlers, fragment_loads, dialog_lifecycle, model_bindings, external_formatters, callbacks.style + signatures, cap_security_checks, cap_lib_modules, cap_context_accesses, cap_config.odata_version/features/sql, grep `\| sort` obbligatorio |
