---
status: handover
owner: Lorenzo De Tomasi
created: 2026-04-22
target: siae-telemetry-control-tower
topic: Eventi DevForge per KPI efficienza Rosario
---

# Handover — Eventi DevForge per siae-telemetry-control-tower

## Contesto

Rosario (CEO) ha richiesto 3 KPI di efficienza sviluppatori:

1. **Lead time brainstorming → plan approvato** (quanto ci mette un dev dal design al piano validato)
2. **Iterazioni di design** (quante volte rivede il design prima di approvare)
3. **Iterazioni rework post-PR** (quanti commit extra + review cycles tra fine sviluppo e merge)

Questa PR DevForge (branch `feat/devforge-enrichment-commit-sha-plan-events`) introduce **tutti gli eventi producer** per calcolare i 3 KPI. `siae-telemetry-control-tower` è il consumer: deve aggregare questi eventi dal data lake e produrre il report.

## Dove trovi gli eventi

Gli eventi vengono emessi localmente come JSONL da hook Claude Code, poi uploadati verso il data lake SIAE tramite `lib/telemetry-upload.sh` (già esistente).

**Destinazione finale (già nota):** bucket S3 `siae-devforge-telemetry-*` (path per-dev, ingestion batch).

**Schema comune di ogni evento JSONL:**

```json
{
  "event_id": "...",
  "schema_version": 2,
  "session_seq": 0,
  "hook_name": "post-commit-review" | "post-skill",
  "actor_canonical": "nome.cognome@siae.it",
  "repo_root": "/path/to/repo",
  "project_canonical": "nome-repo",
  "ts": "2026-04-22T08:15:23Z",
  "user": "...",
  "sid": "session-id",
  "branch": "feat/...",
  "jira_id": "XXX-123" | null,
  "event": "<event_name>",
  "status": "success" | "triggered",
  "meta": { ... payload specifico ... }
}
```

Il campo **`event`** identifica il tipo. Il campo **`meta`** contiene il payload.

## Eventi da consumare

### 1. `commit_created`

Ogni commit locale.

```json
"meta": {
  "commit_sha": "ad39dffab...",   // 40-hex, NUOVO da questa PR
  "files_changed": 3,
  "insertions": 45,
  "deletions": 12,
  "has_tests": true,
  "output_tokens_delta": 1234,
  "total_tokens_delta": 5678,
  "cost_delta_eur": 0.0234,
  "session_tokens_cumulative": 123456
}
```

**Uso Control Tower:** join con `pr_opened.commits_at_open` per ricostruire la timeline del branch; aggrega per `actor_canonical` + giorno per velocity.

### 2. Plan lifecycle events

Emessi da `hooks/post-skill` su invocazione di `siae-brainstorming` / `siae-writing-plans`.

```json
// plan_created — design doc nuovo
"event": "plan_created",
"meta": {
  "plan_path": "docs/plans/2026-04-22-xxx-design.md",
  "origin_skill": "siae-devforge:siae-brainstorming"
}

// plan_revised — iterazione di design sul medesimo plan_path
"event": "plan_revised",
"meta": {
  "plan_path": "...",
  "origin_skill": "..."
}

// plan_approved — design con frontmatter "status: approved"
"event": "plan_approved",
"meta": {
  "plan_path": "...",
  "origin_skill": "siae-devforge:siae-writing-plans"
}

// plan_metrics — aggregato subito dopo plan_approved
"event": "plan_metrics",
"meta": {
  "plan_path": "...",
  "iterations": 2,           // count plan_revised per plan_path
  "duration_sec": 3847,      // plan_approved.ts - plan_created.ts
  "origin_skill": "..."
}
```

**Uso Control Tower per KPI #1 + #2:**

| KPI | Query concettuale |
|---|---|
| Lead time mediano | `SELECT actor_canonical, PERCENTILE(meta.duration_sec, 50) FROM events WHERE event='plan_metrics' GROUP BY actor_canonical` |
| Iterazioni medie | `SELECT actor_canonical, AVG(meta.iterations) FROM events WHERE event='plan_metrics' GROUP BY actor_canonical` |

**Nota:** `plan_metrics.iterations == 0` significa design lineare (zero revisioni). Non filtrarlo.

### 3. PR lifecycle events

Emessi da `hooks/post-commit-review` su `git push` / `gh pr merge`.

```json
// pr_opened — 1x per pr_number (idempotente via snapshot locale)
"event": "pr_opened",
"meta": {
  "pr_number": 213,
  "base_branch": "main",
  "files_changed": 8,
  "commits_count": 4         // commits al momento dell'apertura
}

// pr_commit_after_open — ogni push successivo sulla PR
"event": "pr_commit_after_open",
"meta": {
  "pr_number": 213,
  "commit_sha": "0c45e805...",
  "commits_since_open": 1    // delta commit dal pr_opened
}

// pr_review_cycle — reviewDecision passa a CHANGES_REQUESTED
"event": "pr_review_cycle",
"meta": {
  "pr_number": 213,
  "cycle_num": 1,
  "trigger": "changes_requested"
}

// pr_merged — gh pr merge CLI O catch-up su UI web
"event": "pr_merged",
"meta": {
  "pr_number": 213,
  "merge_method": "cli" | "web" | "closed",
  "total_commits": 5,
  "delta_from_open": 3       // commit aggiunti dopo apertura PR
}

// pr_metrics — aggregato subito dopo pr_merged
"event": "pr_metrics",
"meta": {
  "pr_number": 213,
  "rework_commits": 3,           // count pr_commit_after_open per pr_number
  "review_cycles": 1,            // count pr_review_cycle per pr_number
  "time_to_merge_sec": 86400,    // now - opened_ts (dal snapshot locale)
  "first_push_to_merge_sec": 86400
}
```

**Uso Control Tower per KPI #3:**

| Metrica | Query concettuale |
|---|---|
| Rework commits mediano | `PERCENTILE(meta.rework_commits, 50) WHERE event='pr_metrics'` |
| Review cycles mediano | `PERCENTILE(meta.review_cycles, 50) WHERE event='pr_metrics'` |
| Time to merge mediano | `PERCENTILE(meta.time_to_merge_sec, 50) WHERE event='pr_metrics'` |
| % PR senza rework | `COUNT(meta.rework_commits=0) / COUNT(*) WHERE event='pr_metrics'` |
| % PR mergiate da CLI vs UI | `COUNT(meta.merge_method='cli'|'web'|'closed') GROUP BY meta.merge_method` |

## Limiti noti (importanti per il consumer)

### 1. `pr_review_cycle` under-count

Il cycle è rilevato **solo coincidendo con un `git push`**. Se reviewer lascia `CHANGES_REQUESTED` e il dev discute senza pushare, il cycle non viene contato.

**Implicazione**: `review_cycles` rappresenta "cicli di rework che hanno portato a nuovo codice", non "tutti i cicli di feedback".

### 2. `time_to_merge_sec` proxy

Misurato come `now - opened_ts` dove `opened_ts` è il **primo push con PR aperta**, non l'apertura logica della PR. Differenza < 1 min nella maggior parte dei casi (dev pusha e crea PR subito dopo).

### 3. `pr_merged` via UI web

Catturato dal **push successivo** (via catch-up polling). Se il dev non pusha più dopo il merge UI, il `pr_merged` non viene emesso. Questo caso è raro (merge chiude il branch, dev tipicamente pusha il prossimo lavoro presto).

**Mitigation consumer-side**: usa `gh pr list --state merged --json` periodicamente per riconciliare PR che mancano nell'event stream.

### 4. Dev senza `gh` CLI

Il hook fa `skip silent` se `gh` non installato. Per questi dev gli eventi PR lifecycle non arrivano. Adoption gap è tracciabile via `commit_created` (che funziona senza gh) vs `pr_opened` (che richiede gh).

## Versioning eventi

- `schema_version: 2` è il livello corrente del logger SIAE.
- Consumer deve **tollerare campi extra** nel `meta` (forward-compat).
- Gli eventi `plan_*` e `pr_*` sono **nuovi in questa PR** — aggiungere ai consumer solo dopo merge su `main` e deploy telemetry upload.

## Roadmap consigliata per Control Tower

| # | Task | Priorità |
|---|------|---------|
| 1 | Ingestion tabella `plan_metrics` (KPI #1, #2) | HIGH — dato già fluisce post-merge |
| 2 | Ingestion tabella `pr_metrics` (KPI #3) | HIGH |
| 3 | Dashboard "Efficienza per dev" (3 KPI + % PR senza rework) | HIGH — primo outcome per Rosario |
| 4 | Reconciliation batch via `gh pr list --state merged` | MEDIUM — copre gap merge-UI-no-push |
| 5 | Alert su dev outliers (es. `time_to_merge > p90`) | LOW — dopo 2+ settimane di dati |

## Contatti

- **Producer (DevForge) owner:** Lorenzo De Tomasi
- **Repo producer:** `siae-dev-forge` branch `feat/devforge-enrichment-commit-sha-plan-events`
- **PR:** apri con `gh pr view -w` su quel branch
- **Design doc eventi PR:** `docs/plans/2026-04-22-devforge-pr-lifecycle-events-design.md`

## Domande aperte per il team telemetry

1. Volete un ADR formale sul contratto evento (schema, retention, PII)?
2. Serve un canale di deprecazione per eventi legacy `pr_opened` (pre-idempotenza)?
3. Lo schema attuale JSONL è adatto all'ingestion Athena/Glue, o preferite convertirlo in Parquet in fase di upload?
