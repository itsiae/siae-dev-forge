# Task 19 — `references/phase-5-parallel.md`

**Goal:** Creare il reference che descrive l'orchestrazione multi-agente (caricato SOLO quando `parallel_mode == enabled`): trigger, assegnazione batch→agente, prompt template del subagent, OUTPUT CONTRACT, protocollo di dispatch (P1-P5), join, fallback, Phase 7 parallel. Questo è il cuore della feature richiesta dall'utente (≤4 subagent Sonnet).

**WS:** WS-5 · **Dipendenze:** Task 18 (schema batch-plan).

## File coinvolti
- Crea: `skills/code-coverage/references/phase-5-parallel.md`
- Modifica: `skills/code-coverage/references/index.md` (aggiungi la riga del nuovo reference)

## Step 1 — Crea `references/phase-5-parallel.md`

````markdown
# Phase 5 — Parallel Multi-Agent Dispatch

> Caricato SOLO quando `parallel_mode == enabled` (size_class LARGE/VERY_LARGE,
> pending_batches >= 2). NON caricare in sessioni single-agent.

## Trigger
parallel_mode = enabled se:
- VERY_LARGE e pending_batches >= 2
- LARGE e pending_batches >= 2
- MEDIUM e loc > 15000 e pending_batches >= 3
Altrimenti single-agent (flusso standard invariato).
n_agents = min(4, len(pending_batches)).

Disattiva (fallback single-agent) se: pending_batches == 1; env CC_NO_PARALLEL_AGENTS=1;
overrides.json.force_sequential=true; Agent tool non disponibile; batch tutti T3/T4 ceiling=1.

## Assegnazione batch → agente
Default round-robin: batch[i] → agent[i % n_agents].
Se deviazione di sum(file.loc) tra i bucket > 40% → bin-packing greedy first-fit per LOC.
Ceiling totale per agente: <= 10 file. Log in decisions.log la mappa di assegnazione.

## Dispatch Protocol
P1 — ASSIGN: calcola n_agents e la mappa batch→agente.
P2 — DISPATCH: emetti TUTTE le Agent tool-call nello STESSO turno (parallel tool use).
     Ogni call: model=claude-sonnet-4-6, prompt=build_subagent_prompt(...), run_in_background=true.
     Passa all'agente SOLO: file list del batch, repo_path, framework, stack language,
     reference phase-5-generation.md, path template da template-cache.
     NON passare: SKILL.md intero, phase-3/7/4b, contesto sessione.
P3 — WAIT: attendi tutti i risultati (timeout 20 min/agente; timeout → status agent-timeout).
P4 — JOIN: per ogni risultato parsare l'OUTPUT CONTRACT, append decisions_log_fragment a
     decisions.log, aggiorna status batch in batch-plan.json, aggrega intractable_flags in
     intractable.json, files_skipped_preserve in deferred_files.json.
P5 — RE-QUEUE: batch partial/failed → ripassati in fallback sequenziale (max 1 retry).
     Poi → Phase 6 (SOLO coordinatore, 1 solo vitest run --coverage).

## build_subagent_prompt (template)
Il prompt del subagent DEVE contenere: i file del batch (path/tier/priority/loc/coverage_mode),
le istruzioni Phase 5 (PRESERVE_EXISTING, placeholder-check, AAA, batch ceiling, branch-matrix
se coverage_mode=branch-priority), e l'OUTPUT CONTRACT. CONSTRAINTS espliciti:
- DO NOT run vitest/coverage. Generation ONLY.
- DO NOT modify package.json/vitest.config.ts/production source.
- DO NOT write to batch-plan.json/decisions.log (usa decisions_log_fragment nel return).
- DO NOT load other phase refs. Phase 5 only.

## OUTPUT CONTRACT (return JSON del subagent)
```json
{
  "batch_id": 2, "agent_id": "agent-1", "status": "completed|partial|failed",
  "files_written": [{"spec_path":"...","source_path":"...","tier":"T2","test_count":18}],
  "files_skipped_preserve": ["..."],
  "files_failed": [{"path":"...","reason":"...","category":"..."}],
  "intractable_flags": [{"path":"...","reason":"...","suggested_strategy":"..."}],
  "decisions_log_fragment": ["[phase5][agent-1] wrote ... tier=T2", "..."]
}
```
NON ritornare coverage report. Se l'agente include un coverage report → il coordinatore lo ignora e logga warning.

## Isolation
Path-disgiunti (ogni agente scrive solo gli spec del suo batch). NO worktree.
Il coordinatore è l'UNICO writer di stato condiviso (batch-plan.json, decisions.log) e l'UNICO
a eseguire Phase 4 (env/install/config/helpers) e Phase 6 (coverage).

## Phase 7 parallel repair
Systemic fix (config condiviso) → sequenziale (coordinatore).
Per-file fix con >= 2 file di categorie diverse → fino a 4 repair-agent in parallelo (1 file/agente),
OUTPUT CONTRACT {test_path, status: fixed|unfixable, edit_summary, decisions_log_fragment}.
Full coverage run → sempre coordinatore, 1/iter. Ortogonale a max_iter scaling (Task 15).
````

## Step 2 — Aggiorna `references/index.md`
Aggiungi una riga alla tabella dei reference:
```markdown
| `references/phase-5-parallel.md` | 5 | Multi-agent dispatch (≤4 Sonnet): trigger, assegnazione, prompt, OUTPUT CONTRACT, join |
```

## Step 3 — Verifica
Run: `test -f skills/code-coverage/references/phase-5-parallel.md && echo OK` → `OK`.
Run: `for s in "Trigger" "Dispatch Protocol" "OUTPUT CONTRACT" "Isolation" "Phase 7 parallel"; do grep -q "$s" skills/code-coverage/references/phase-5-parallel.md && echo "$s OK"; done` → 5 righe `... OK`.
Run: `grep -q "phase-5-parallel.md" skills/code-coverage/references/index.md && echo OK` → `OK`.

## Step 4 — Commit
```
git add skills/code-coverage/references/phase-5-parallel.md skills/code-coverage/references/index.md
git commit -m "feat(code-coverage): add phase-5-parallel reference (multi-agent dispatch protocol)"
```

## Criteri di accettazione
- [ ] Reference contiene: Trigger, Assegnazione, Dispatch P1-P5, build_subagent_prompt, OUTPUT CONTRACT, Isolation, Phase 7 parallel.
- [ ] Model dichiarato `claude-sonnet-4-6`, max 4 agenti.
- [ ] Vincoli espliciti: subagent NON lancia coverage, NON tocca sorgente/config, NON scrive stato condiviso.
- [ ] Censito in `index.md`.
