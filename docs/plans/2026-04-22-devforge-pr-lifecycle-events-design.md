---
status: draft
owner: Lorenzo De Tomasi
created: 2026-04-22
topic: DevForge PR lifecycle events per KPI rework/review iterations
---

# PR Lifecycle Events — Design Doc

## Contesto

Rosario (CEO) vuole KPI di efficienza centrati sul ciclo di sviluppo, non
sull'adoption AI. Tre KPI richiesti:

1. **Lead time brainstorming → plan approvato** — coperto da `plan_metrics.duration_sec` (PR #212).
2. **Iterazioni di design** — coperto da `plan_metrics.iterations` (PR #212).
3. **Iterazioni tra fine sviluppo e chiusura PR** — **NON coperto** oggi. Obiettivo di questo design.

Il terzo KPI misura il rework post-PR: quanti commit aggiuntivi dopo l'apertura,
quanti cicli di review (CHANGES_REQUESTED), quanto tempo dal primo push al merge.

## Stato attuale

Eventi già emessi da `hooks/post-commit-review`:

- `commit_created` — ogni commit locale, con `commit_sha`, `files_changed`, `has_tests`.
- `pr_opened` — su `git push` se esiste PR, con `pr_number`, `base_branch`, `commits_count`.

Problema: `pr_opened` viene ri-emesso ad **ogni** push (non solo al primo).
Consumer downstream non possono distinguere "apertura PR" da "push successivo".

## Decisioni

**D1. Approccio hook-only + wrapper `gh pr merge` + catch-up polling.**

- Tutto dentro `hooks/post-commit-review` (no infra nuova, no webhook, no cron).
- `gh pr merge` detectato via `TOOL_COMMAND` matcher (stesso pattern di `gh pr create`).
- Catch-up per merge via UI web: ad ogni push, scansiona snapshot orfani e interroga `gh pr view` per state=MERGED.

**D2. Snapshot per-PR** (`$HOME/.claude/.devforge-pr-state-<pr_number>.json`).

- Un file per PR aperta.
- Scritto al primo `pr_opened`, aggiornato ad ogni push.
- Cancellato dopo `pr_merged`.
- Motivo: cleanup atomico, zero race tra push paralleli su branch diversi.

**D3. Scope bundle: PR separata.**

- Branch nuovo: `feat/devforge-pr-lifecycle-events`.
- Parte dopo il merge di PR #212.
- Motivo: nome branch #212 già descrittivo; allargare significa commit incoerenti.

## Eventi (schema JSONL)

| Evento | Payload | Quando |
|---|---|---|
| `pr_opened` | `{pr_number, base_branch, files_changed, commits_count}` | 1x per pr_number (idempotente via **assenza snapshot file** — vedi §Snapshot) |
| `pr_commit_after_open` | `{pr_number, commit_sha, commits_since_open}` | push successivo su branch con PR aperta |
| `pr_review_cycle` | `{pr_number, cycle_num, trigger:"changes_requested"}` | reviewDecision passa a CHANGES_REQUESTED (diverso da snapshot) |
| `pr_merged` | `{pr_number, merge_method: "cli"\|"web", total_commits, delta_from_open}` | `gh pr merge` CLI O catch-up su state=MERGED |
| `pr_metrics` | `{pr_number, rework_commits, review_cycles, time_to_merge_sec, first_push_to_merge_sec}` | subito dopo `pr_merged` |

## Architettura — detection logic

```
post-commit-review (PostToolUse su Bash)
  ├─ TOOL_COMMAND contiene "git push"
  │   ├─ gh pr view → PR esiste?
  │   │   NO  → exit silent
  │   │   YES →
  │   │     ├─ snapshot esiste? (.devforge-pr-state-<n>.json)
  │   │     │   NO  → pr_opened + crea snapshot (opened_ts, commits_at_open)
  │   │     │   YES → pr_commit_after_open (commits_since_open)
  │   │     └─ reviewDecision cambiata a CHANGES_REQUESTED? → pr_review_cycle
  │   └─ catch-up: per ogni snapshot orfano (branch diverso da corrente),
  │        gh pr view <n> → state=MERGED? → pr_merged (web) + pr_metrics + del snapshot
  │
  ├─ TOOL_COMMAND contiene "gh pr merge"
  │   └─ pr_merged (cli) + pr_metrics + del snapshot
  │
  └─ TOOL_COMMAND contiene "gh pr create"
      └─ (nessun cambio: pr_opened parte al primo push successivo)
```

## Snapshot schema

```json
{
  "pr_number": 213,
  "base_branch": "main",
  "opened_ts": "2026-04-22T08:15:23Z",
  "commits_at_open": 4,
  "last_review_decision": "REVIEW_REQUIRED"
}
```

## Calcolo metriche (pr_metrics)

| Campo | Formula |
|---|---|
| `rework_commits` | `grep -c "pr_commit_after_open.*pr_number:<n>" $DEVFORGE_LOG_FILE` |
| `review_cycles` | `grep -c "pr_review_cycle.*pr_number:<n>" $DEVFORGE_LOG_FILE` |
| `time_to_merge_sec` | `now - opened_ts` (da snapshot) |
| `first_push_to_merge_sec` | alias di time_to_merge_sec (pr_opened = primo push con PR) |

## Detection boundary — `pr_review_cycle` accetta under-count

`pr_review_cycle` è rilevato **solo quando coincide con un `git push`** dello sviluppatore
(momento in cui il hook parte e interroga `gh pr view --json reviewDecision`).

Implicazione accettata: se un reviewer richiede modifiche e il dev non pusha subito
(es. discute in commento), quel ciclo di review non viene contato. Rosario vuole
misurare "iterazioni di rework tra fine dev e merge" — il proxy naturale è il push,
non la pura notifica di review. Under-count sistematico ≈ cicli di review senza
azione dev, che per definizione non sono rework.

Alternative scartate:
- Polling idle → complessità sproporzionata (cron locale, wake-up, permission).
- Webhook GitHub → out of scope (vedi §Out of scope).

## Edge case — push pre-`gh pr create`

Se lo sviluppatore fa `git push` **prima** di `gh pr create`, `gh pr view` ritorna
vuoto → nessun evento emesso. Comportamento coerente con lo stato attuale
([post-commit-review:86-103](hooks/post-commit-review#L86-L103)). Documentato
come intenzionale: pr_opened misura "apertura PR", non "primo push".

## Cap catch-up — max 5 snapshot per push

Per evitare latenza con dev che hanno molte PR aperte, il catch-up scansiona
**al massimo 5 snapshot orfani per push** (ordinati per `opened_ts` crescente —
prima le PR più vecchie). Snapshot esclusi dalla scansione corrente restano
e verranno processati al push successivo.

Worst case overhead: 5 × 3s timeout = 15s. Tipico: 1-2 PR → < 1s.

## Scoping snapshot — pr_number è globale per repo GitHub

`pr_number` è univoco a livello di repo GitHub → snapshot `$HOME/.claude/.devforge-pr-state-<n>.json`
safe anche con worktree multipli sullo stesso repo (condividono lo stesso namespace PR).

## Error handling

- `gh` non installato → skip silent (comportamento esistente).
- `gh pr view` exit != 0 → skip silent.
- Timeout `gh`: 3s (evita blocco push).
- Snapshot corrotto (JSON invalido) → log warning, ricrea.
- Catch-up fallisce → snapshot resta orfano, ritentato al prossimo push.

## Testing

File nuovo: `tests/hooks/post-commit-pr-lifecycle.test.sh` — 7 scenari:

1. Primo push post `gh pr create` → `pr_opened` 1x, snapshot creato.
2. Secondo push stesso branch → `pr_commit_after_open`, NO altro `pr_opened`.
3. reviewDecision → CHANGES_REQUESTED → `pr_review_cycle` cycle_num=1.
4. `gh pr merge` CLI → `pr_merged` (cli) + `pr_metrics`, snapshot cancellato.
5. Merge da UI (fixture `state=MERGED`) → catch-up al push successivo → `pr_merged` (web).
6. `pr_metrics.review_cycles` conta solo cambi distinti (no doppio emit se decisione resta CHANGES_REQUESTED).
7. Dedup `pr_opened`: JSONL con `pr_opened` pre-esistente per pr_number → skip.

Mock `gh` via funzione shim che ritorna fixture JSON — stesso pattern di `tests/hooks/post-commit-review-sha.test.sh`.

## Criteri di accettazione

- [ ] 7/7 test nuovi passano.
- [ ] 2/2 test esistenti (`post-commit-review-sha`, `post-skill-plan-events`) restano verdi.
- [ ] `pr_opened` emesso esattamente 1x per pr_number.
- [ ] `pr_metrics.rework_commits` coincide con count `pr_commit_after_open`.
- [ ] `pr_metrics.review_cycles` coincide con count `pr_review_cycle`.
- [ ] Snapshot file rimosso dopo `pr_merged`.
- [ ] Catch-up overhead push ≤ 500ms (2 PR pendenti, timeout 3s per chiamata).
- [ ] Zero impatto su PR senza issue (happy path invariato).

## Trade-off e rischi

| Rischio | Mitigazione |
|---|---|
| `gh pr view` aggiunge latenza ogni push | Timeout 3s hard + background upload già esistente |
| Dev senza `gh` CLI | Hook skip silent (già pattern) — nessun evento emesso, degrada a commit_created only |
| Snapshot orfani permanenti (es. PR chiusa senza merge) | Cleanup anche su `state=CLOSED` nel catch-up (stesso codice path) |
| Breaking consumer esistenti di `pr_opened` (ora idempotente) | Nessun consumer ancora in prod — window safe |
| Review cycle non contati se dev non pusha | Accettato (vedi §Detection boundary) — proxy push = rework reale |
| Molte PR aperte → latenza catch-up | Cap 5 snapshot per push (vedi §Cap catch-up) |

## Stima SP

**3 SP-Umano / 1 SP-Augmented** — boilerplate hook + pattern già consolidato da plan_metrics.

## Out of scope

- Webhook GitHub remoto (scope esplode, richiede endpoint + auth + deploy).
- Metriche per-reviewer (chi richiede modifiche) — dato disponibile via `gh pr view --json reviews` ma non richiesto da Rosario.
- Dashboard / visualizzazione — producer only, downstream (siae-dev-analytics) consuma gli eventi.
