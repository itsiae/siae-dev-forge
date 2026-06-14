# Design — Insights di valore per-developer (DevForge + Claude Code) nella telemetria S3

**Data:** 2026-06-14
**Autore:** Lorenzo De Tomasi (+ Claude Code)
**Stato:** Draft — in attesa approvazione gate brainstorming
**Topic:** Sistema che scrive dati aggiuntivi nella telemetria S3 e genera insights per-developer su *cosa / come / quale valore* porta DevForge+Claude Code, **interamente nell'infrastruttura telemetrica** (no skill), esposti online via API contract modellato sull'Analytics API di Claude Code
**SDLC phase:** 2. Design

---

## 1. Contesto e problema

### 1.1 Obiettivo reale (dopo refinement)

Generare **insights di valore per-developer**, **dentro la telemetria** (S3), prodotti
dall'**infrastruttura sottostante** (server-side, no skill locale, nessuna invocazione del
developer) ed **esposti online via API**:
- **COSA** fa DevForge+Claude per quello sviluppatore (composizione produttività)
- **COME** lavora (aderenza al workflow: brainstorming/TDD/verification/review)
- **QUALE VALORE** porta (velocità, qualità, costo; e il delta *workflow-seguito vs no*)

Paradigma di riferimento: l'**analytics nativo di Claude Code** (§2) — aggregazione
server-side per-developer/per-giorno + read API.

**Decisioni di scope confermate dall'utente (2026-06-14):**
1. Due layer, **producer prima** (Layer 1 = questa iniziativa).
2. L'insight **deve stare nelle telemetrie S3** — *override*: rimosso l'output "report locale".
3. **Niente skill**: la generazione insight è **tutta sotto l'infrastruttura** (underlying)
   telemetrica, non una skill — *override* della home `siae-dev-analytics`.
4. Esposizione **online via API contract** (deliverable §13).

### 1.2 Perché serve un sistema nostro (razionale decisivo)

> Documentazione ufficiale Anthropic: *"Claude Platform on AWS: The Claude Code Analytics
> API is **not currently available**."*

**SIAE esegue Claude Code via Amazon Bedrock** (seat Anthropic, console `username=Bedrock`,
`bedrock-aws-cap` su CloudWatch). L'Analytics API nativa **NON copre il deployment SIAE**:
la telemetria DevForge è **l'unica fonte possibile** di insights per-developer in SIAE.
In più, ciò che gli insights nativi **non vedono per design** è il valore di DevForge:
l'**aderenza al metodo** (brainstorming/TDD/verification/blind-review), iterazioni di piano,
bypass dei gate, e la **qualità correlata al metodo**.

### 1.3 Cosa esiste già

**Telemetria producer (S3):** ~30 event type via outbox → API Gateway → Lambda (dedup
DynamoDB) → PUT S3 `siae-devforge-telemetry/devforge-logs/year=/month=/day=/sid-<sid>/`.
Schema v2 (`lib/logger.sh:556`). Ogni evento porta top-level `auth_email`, `auth_account_uuid`,
`repo_remote`, `branch`, `jira_id`, `actor_canonical`. Eventi rilevanti: `session_end`
(tokens/cost/by_skill/by_model/skills_count/commits_count), `commit_created`
(insertions/deletions/has_tests/commit_sha/cost_delta), `pr_opened`/`pr_merged`/`pr_metrics`
(time_to_merge_sec/rework_commits/review_cycles), `plan_metrics` (iterations/duration_sec),
`tdd_cycle`, `test_run_result` (coverage), `skill_invoked`/`skill_completed`, eventi gate.

**Segnale adoption calcolato ma mai persistito su S3:** ledger task-scope
`~/.claude/.devforge-task-skills/<task_id>/{skills_invoked,skills_validated,metadata}`
(`lib/task-id.sh:155-174`) + `lib/adoption-analyzer.py --format json`, consumati solo
localmente (recap `hooks/stop-gate:107`).

**Infra telemetrica esistente:** `infra/telemetry/` — Lambda ingest (`lambda/handler.py`),
bucket `siae-devforge-telemetry` (`s3.tf`, lifecycle 90d→Glacier/365d), API Gateway POST
`/v1/logs`, DynamoDB dedup. **Non esiste alcuna read/exposure API né aggregazione insight.**

> La skill `siae-dev-analytics` calcola KPI/ROI per-developer ma è **invocata dall'utente**
> (locale, GitHub-ground-truth). Per decisione utente §1.1(3) **NON** è la home del Layer 2:
> l'insight va prodotto server-side dall'infra. La logica KPI/DORA della skill resta un
> **riferimento di calcolo** (anti-pattern, formule), non una dipendenza runtime.

### 1.4 Gap che chiudiamo

- **G1 (Layer 1):** aderenza al workflow per-task non su S3 → dimensione **COME** inosservabile.
- **G2 (Layer 1):** bypass `DEVFORGE_ENFORCEMENT_OFF=1` (gate muti, `brainstorming-gate:26`) e
  `git commit --no-verify` non tracciati (i breakglass `BREAK-GLASS:`/evidence-tool-fail sì).
- **G3 (Layer 1):** outcome event (`commit_created`, `pr_*`) senza `task_id` → join
  *adesione↔outcome* solo per `branch`/`jira_id`.
- **G4 (Layer 2):** nessuna aggregazione server-side che produca l'insight per-developer
  cosa/come/valore, né esposizione online.

## 2. Paradigma di riferimento — analytics nativo Claude Code

Due superfici: **dashboard** + **Analytics Admin API**
(`GET /v1/organizations/usage_report/claude_code`, **per-user, per-day**, attore =
`email_address`, cursor pagination, freschezza ~1h, daily aggregation server-side).

| Categoria CC | Metriche CC | Mappatura DevForge (cosa/come/valore) |
|---|---|---|
| Produttività (core) | num_sessions, lines_of_code add/rem, commits, PRs | **COSA** — `session_end`/`commit_created`/`pr_*` + breakdown skill |
| Engagement (tool) | accept/reject per tool → accept rate | parziale (§7 — non raggiungibile lato hook) |
| Costo | tokens (input/output/cache) + cost per modello | **VALORE** (efficienza) — `session_end.by_model`/`pricing` |
| Contribution/ROI | PR con-CC vs senza, leaderboard | **VALORE** (ROI) — DevForge: *task con-workflow vs senza* |

**Anti-vanity:** adottiamo il *paradigma* CC (per-developer, categorie) ma **NON** LOC/giorno
(anti-pattern DORA). VALORE = outcome DORA-allineati (lead time, rework, change-failure proxy)
+ costo. Solo metriche oggettive (no self-reporting — perception gap METR 2025).

## 3. Architettura — tutto nell'infrastruttura telemetrica

```
┌─ LAYER 1 — PRODUCER (QUESTA iniziativa) ───────────────────────────┐
│ Hook emettono segnali RAW additivi su S3 (no score nel producer)   │
│  • task_adoption   (G1 — aderenza workflow per task)               │
│  • gate_bypassed   (G2 — enforcement_off + git_no_verify)          │
│  • task_id join-key su commit_created/pr_* (G3 — correlazione)     │
└────────────────────────────────────────────────────────────────────┘
            │ POST /v1/logs → Lambda ingest → S3 devforge-logs/ (raw)
            ▼
┌─ LAYER 2 — INSIGHT INFRA (iniziativa SUCCESSIVA, server-side) ─────┐
│ NESSUNA skill. Tutto in infra/telemetry/ (AWS):                     │
│  • Aggregatore schedulato (EventBridge cron giornaliero →           │
│    Lambda, o Athena CTAS) legge devforge-logs/ raw                  │
│  • Calcola per-developer/per-giorno: COSA / COME / VALORE           │
│  • Persiste in S3 telemetria: derived/insights/year=/month=/day=/   │
│  • Read API (API Gateway + Lambda) espone gli insight ONLINE (§13)  │
└────────────────────────────────────────────────────────────────────┘
```

**Sequenza:** Layer 1 si pianifica e implementa **ora**; Layer 2 **subito dopo** (design qui;
piano+implementazione in iniziativa separata).

## 4. Decisioni architetturali (ADR)

- **ADR-1 — Eventi raw dedicati, non arricchire `session_end`** (evento `task_adoption`).
  Scartato l'arricchimento di `session_end` (mescola scope session vs task → `apples-to-oranges`)
  e l'emissione al task-boundary (invasivo, perde task senza PR).
- **ADR-2 — `gate_bypassed` unico con `mechanism`** ∈ {enforcement_off, git_no_verify}.
- **ADR-3 — Producer raw-only; insight derivati server-side.** Il producer (Layer 1) resta
  raw-additivo (`telemetry-raw-only-additive`). L'insight (Layer 2) è una **derivazione
  prodotta dall'infra**, persistita in **prefisso separato `derived/insights/`** dello stesso
  bucket telemetria — mai mischiata con `devforge-logs/` raw.
- **ADR-4 — Niente skill nel Layer 2.** L'aggregazione gira server-side (Lambda schedulato /
  Athena), non come skill invocata dal developer. La logica KPI/DORA di `siae-dev-analytics`
  è riferimento di calcolo (formule, anti-pattern), **non** dipendenza runtime.
- **ADR-5 — Infra Layer 1: zero modifiche.** Il Lambda ingest non filtra per event type
  (`handler.py:34-58`): i nuovi eventi passano trasparenti. Schema v2 invariato. (L'infra
  *nuova* — aggregatore + read API — è interamente Layer 2.)

## 5. LAYER 1 — eventi e modifiche (scope implementativo immediato)

### 5.1 `task_adoption` (G1)
Emesso da `_devforge_emit_session_end` (`hooks/stop-gate`) per il `task_id` corrente, se non vuoto
(scope `itsiae/*`). Raw, no percentuali.
```json
{ "event": "task_adoption", "status": "success",
  "meta": {
    "task_id": "<12-hex>", "task_branch": "<da metadata>", "design_doc": "<da metadata o \"\">",
    "skills_invoked": ["siae-brainstorming","siae-tdd"],
    "skills_validated": ["siae-tdd"],
    "core_skills_validated": { "siae-brainstorming": false, "siae-tdd": true,
      "siae-git-workflow": false, "siae-verification": false, "siae-blind-review": false }
  } }
```
I 5 core sono `lib/adoption-analyzer.py:25-31` (single source riusata, **mai duplicata** in
bash). Idempotenza: re-emissione cross-sessione dello stesso `task_id` innocua (downstream
prende `ts` massimo per `task_id`).

### 5.2 `gate_bypassed` (G2)
**(a)** `hooks/session-start` se `DEVFORGE_ENFORCEMENT_OFF=1` →
`{"mechanism":"enforcement_off","scope":"session"}` (status `warning`).
**(b)** `hooks/post-commit-review` se git commit contiene `--no-verify` (o `-n` word-boundary)
→ `{"mechanism":"git_no_verify","commit_sha":"<sha o \"\">"}`.
> **Semantica `commit_sha` (best-effort):** `git rev-parse HEAD` al momento del PostToolUse;
> hint, non linkage autoritativo (correlazione affidabile = `auth_email + ts`).

### 5.3 `task_id` join-key (G3)
Aggiungere `meta.task_id` a `commit_created`, `pr_opened`, `pr_merged`, `pr_metrics`
(`hooks/post-commit-review`) via `devforge_compute_task_id` (vuoto fuori scope). Abilita la
join precisa *adesione↔outcome*. `branch`/`jira_id` top-level = fallback (già su ogni evento).

### 5.4 Tabella modifiche file (Layer 1)
| File | Modifica | Tipo |
|------|----------|------|
| `lib/task-id.sh` | Nuova fn `devforge_read_task_ledger TASK_ID` → stdout invoked/validated | additivo |
| `lib/adoption-emit.sh` *(nuovo file)* | `devforge_emit_task_adoption` (riusa core list adoption-analyzer; chiama `devforge_log "task_adoption"`). File dedicato per ridurre conflitti coi branch telemetria in volo (§9) | additivo |
| `hooks/stop-gate` | In `_devforge_emit_session_end`: source `lib/adoption-emit.sh` + `devforge_emit_task_adoption` (best-effort `\|\| true`) | additivo |
| `hooks/session-start` | Se `DEVFORGE_ENFORCEMENT_OFF=1` → `gate_bypassed`. **`\|\| true` + pipefail-safe + nessun stdout** (`session_start_hook_invariants`) | additivo |
| `hooks/post-commit-review` | Detection `--no-verify`/`-n` → `gate_bypassed`; aggiunge `task_id` a commit_created/pr_* | additivo |
| `tests/` | Test: lettura ledger, shape `task_adoption`, detection no-verify (pos+neg), enforcement_off, `task_id` negli outcome | nuovo |

## 6. LAYER 2 — infra insight server-side (scope design, iniziativa successiva)

Tutto in `infra/telemetry/` (Terraform + Lambda). **Nessuna skill, nessuna invocazione utente.**

### 6.1 Aggregatore schedulato
- **Trigger:** EventBridge cron giornaliero (mirror della cadenza CC daily + freschezza ~1h).
- **Compute:** Lambda (o Athena CTAS) legge `devforge-logs/` raw del giorno, raggruppa per
  `auth_email` (+ `auth_account_uuid`), calcola le metriche **cosa/come/valore** (§6.3).
- **Idempotenza:** ri-esecuzione di un giorno sovrascrive il record derivato di quel giorno
  (chiave `derived/insights/year=/month=/day=/<email-hash>.json`).

### 6.2 Persistenza
S3 telemetria, prefisso **`derived/insights/year=YYYY/month=MM/day=DD/`** (stesso bucket
`siae-devforge-telemetry`), record per-developer/per-giorno. Etichettato `kind: "derived"`,
mai in `devforge-logs/`.

### 6.3 Schema insight (cosa/come/valore) — vedi API contract §13 per i campi esatti
- **COSA (produttività):** num_sessions, commits, prs_opened, prs_merged, skills_used
  (breakdown), tasks_tracked.
- **COME (metodo — DevForge-unico):** core_skill_adoption % (brainstorming/tdd/git/verification/
  blind-review da `task_adoption`), plan_iterations_avg (`plan_metrics`), review_cycles_avg
  (`pr_metrics`), gate_bypasses (`gate_bypassed` per mechanism).
- **VALORE (outcome + ROI):** lead_time_p50_sec (`pr_metrics.time_to_merge_sec`), rework_commits,
  has_tests_rate, coverage_avg, cost (token+EUR per modello); **workflow_vs_nonworkflow** —
  outcome dei task con-workflow vs senza (join via `task_id`/`branch`).

### 6.4 Read API (esposizione online)
API Gateway + Lambda read-only che serve gli insight da `derived/insights/`. Contratto in §13.
Auth `x-api-key` (admin). Gate privacy: dati nominativi → GDPR (vedi §7).

> Piano/implementazione del Layer 2 = **iniziativa separata** (post Layer 1). Qui definito a
> livello di design per garantire che Layer 1 emetta i segnali corretti.

## 7. Gestione errori / edge cases / privacy

**Layer 1:**
- **Fuori scope (`task_id` vuoto / repo non-itsiae):** `task_adoption` e `task_id` join-key no-op.
- **Ledger assente/vuoto:** nessun `task_adoption`.
- **`_devforge_emit_session_end` con stdin vuoto** (`hooks/stop-gate:120`): emissione comunque.
- **best-effort:** ogni emissione `\|\| true`; non blocca lo stop né fa fallire l'hook.
- **session-start `set -euo pipefail` (riga 11):** `gate_bypassed` con `\|\| true`, nessun stdout.
- **Detection `-n`:** match flag (anche combinato `-nm`), niente falsi positivi su `-n` nella
  commit message → verifica empirica nei test (`review_claims_verify_empirically`).
- **JSON injection:** `design_doc`/`task_branch` via `devforge_sanitize_json_str`.

**Layer 2:**
- **Tool accept/reject rate (engagement CC):** non raggiungibile dagli hook → l'API espone
  `null`/`"N/A"`, non un valore inventato.
- **Privacy/GDPR:** gli insight per-developer sono dati nominativi. La read API richiede auth
  admin; supporta `actor` in chiaro (email) o pseudonimizzato (hash SHA256) via parametro;
  retention/lifecycle del prefisso `derived/insights/` da definire nel piano Layer 2.
- **Bassa numerosità:** confronto workflow-vs-non-workflow con n sotto soglia → l'API segnala
  `"insufficient_data"`, niente claim spurio.

## 8. Downstream / consumer (fuori scope, documentato)

DDL Athena su `task_adoption`/`gate_bypassed` (raw) per query team-wide = follow-up infra.
Il prefisso `derived/insights/` e la read API sono il punto di consumo per dashboard/Control
Tower. Nessuna ridefinizione del consumer Control Tower (`scope_devforge_vs_downstream`).

## 9. Coordinamento branch (rischio)

- `feat/telemetry-kpi-enrichment` (committato, non pushato): tocca `branch-tracker` +
  `post-commit-review` (has_tests). **Overlap con Layer 1 §5.2-5.3 su `post-commit-review`**
  → rebase/coordinamento al merge.
- `fix/telemetry-flush-storm`, `feat/telemetry-raw-value-signals`, `*-write-hardening`:
  toccano lib telemetria. **Mitigazione:** `devforge_emit_task_adoption` in nuovo file
  `lib/adoption-emit.sh`; branch da `main`.

## 10. Criteri di accettazione

### Layer 1 (testabili ora)
1. Fine sessione su repo `itsiae/*` con ledger popolato → **un** `task_adoption` con `task_id`,
   `skills_invoked[]`, `skills_validated[]`, `core_skills_validated{}` (5 bool).
2. Repo non-`itsiae/*` o `task_id` vuoto → **nessun** `task_adoption`.
3. Ledger vuoto → **nessun** `task_adoption`.
4. `DEVFORGE_ENFORCEMENT_OFF=1` a session-start → **un** `gate_bypassed mechanism=enforcement_off`;
   session-start emette comunque il JSON `additional_context` (no abort).
5. `git commit --no-verify -m x` → `gate_bypassed mechanism=git_no_verify`;
   `git commit -m "fix -n test"` → **nessun** evento (no falso positivo).
6. `commit_created`/`pr_opened`/`pr_merged`/`pr_metrics` su repo in scope portano
   `meta.task_id` non vuoto; fuori scope → assente/vuoto.
7. Emissioni best-effort: con `devforge_log`/ledger non disponibili gli hook **non falliscono**
   e non sporcano stdout JSON.
8. Lista 5 core skill **non duplicata** in bash (riuso `adoption-analyzer.py`).
9. Nessuna modifica a Lambda/Terraform per Layer 1; eventi visibili su S3 sotto partizione `sid`.
10. Test no-regression hook count aggiornato (`pr252_test_count_drift`).

### Layer 2 (acceptance per iniziativa successiva, definita ora)
11. Aggregatore schedulato produce record per-developer/per-giorno in `derived/insights/...`
    con sezioni **cosa/come/valore**; COME alimentata da `task_adoption`/`gate_bypassed`.
12. Read API conforme al contratto §13 (paginazione, auth, schema); attore = `auth_email`.
13. Insight di correlazione *workflow vs non-workflow* presente, o `"insufficient_data"` se n<soglia.
14. Nessuna skill introdotta; tutto in `infra/telemetry/`. Nessuna metrica LOC/giorno.
    Dati nominativi protetti da auth + pseudonimizzazione opzionale.

## 11. Stima (doppia scala)

| Layer | Umano | Augmented | Note |
|-------|------:|----------:|------|
| Layer 1 (questa iniziativa) | ~5 SP | ~2 SP | 3 hook + 2 lib fn + join-key + suite test |
| Layer 2 (successiva) | ~13 SP | ~5 SP | Lambda aggregatore + EventBridge + S3 derived + read API (API GW + Lambda) + Terraform + auth/GDPR |

## 12. Handoff

> **REQUIRED SUB-SKILL:** `siae-writing-plans` — piano implementativo **del Layer 1**
> (subtask TDD per AC 1-10). Layer 2 (infra insight + read API) avrà brainstorming+piano
> propri come iniziativa successiva, con il contratto §13 come specifica di interfaccia.

## 13. API contract (deliverable)

Contratto OpenAPI 3.1 dell'esposizione online degli insight, modellato sull'Analytics API di
Claude Code:
**`docs/plans/2026-06-14-devforge-telemetry-insights-api.openapi.yaml`**

Endpoint principale: `GET /v1/devforge/usage_report` (per-developer, per-day, cursor
pagination) — sezioni `core_metrics` (COSA), `workflow_metrics` (COME), `value_metrics`
(VALORE). Vedi il file YAML per schema completo, parametri, esempi e auth.
