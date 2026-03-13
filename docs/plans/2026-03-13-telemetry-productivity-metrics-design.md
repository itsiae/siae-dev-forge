# Design: Telemetry Productivity Metrics — Approccio "Enrich & Measure"

**Data:** 2026-03-13
**Autore:** Lorenzo De Tomasi + DevForge AI
**Stato:** Approvato
**SP:** 5
**Approccio scelto:** A — Enrich & Measure (solo telemetria plugin)

---

## Contesto

Il plugin siae-dev-forge (v1.9.0-mvp) raccoglie già 3 event type via `logger.sh`:
`session_start`, `skill_invoked`, `pr_auto_review`. I dati vengono salvati in
`~/.claude/devforge-activity.jsonl` e uploadati su S3 (`siae-devforge-telemetry`)
via API Gateway + Lambda.

**Problema:** i dati attuali misurano solo l'adozione (chi usa cosa), non la
produttività (quanto è più efficace chi usa DevForge). Per dimostrare l'impatto
a management, tech lead e singoli developer servono metriche di throughput,
qualità e ciclo di vita.

**Decisione:** arricchire la telemetria plugin con 6 nuovi event type. Zero
modifiche infrastrutturali (S3, Lambda, API GW invariati). Il trend temporale
delle metriche è la misura di produttività — non serve baseline esplicita.

---

## Nuovi Event Type

### 1. `skill_completed`

**Trigger:** `hooks/post-skill` (hook esistente)
**Campi meta:**

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `skill_name` | string | Nome skill completata |
| `sdlc_phase` | string | Fase SDLC mappata |
| `duration_ms` | integer | Tempo dall'invocazione al completamento |
| `outcome` | string | `success` / `error` / `aborted` |

**Metrica:** tempo medio per skill, failure rate per skill.

### 2. `tdd_cycle`

**Trigger:** subagent implementer a fine ciclo RED→GREEN→REFACTOR
**Campi meta:**

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `task` | string | ID task dal piano (es. `task-3`) |
| `phase` | string | `red` / `green` / `refactor` / `complete` |
| `tests_passed` | integer | Numero test passati |
| `tests_failed` | integer | Numero test falliti |

**Metrica:** TDD compliance, quality proxy (test pass rate).

### 3. `commit_created`

**Trigger:** `hooks/pre-commit` (post-commit, hook esistente)
**Campi meta:**

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `files_changed` | integer | Numero file modificati |
| `insertions` | integer | Righe aggiunte |
| `deletions` | integer | Righe rimosse |
| `has_tests` | boolean | `true` se il commit include file di test |

**Detection `has_tests`:**
```bash
echo "$changed_files" | grep -qE '(Test\.|_test\.|\.test\.|\.spec\.|/test/|/tests/)' && has_tests=true
```

**Metrica:** throughput (commit/sessione), test inclusion rate.

### 4. `pr_opened`

**Trigger:** post-push, detection via `gh pr view`
**Campi meta:**

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `pr_number` | integer | Numero PR |
| `base_branch` | string | Branch target |
| `files_changed` | integer | File nella PR |
| `commits_count` | integer | Commit nella PR |

**Metrica:** lead time (timestamp di apertura).

### 5. `pr_merged`

**Trigger:** `hooks/session-start`, check PR merge nelle ultime 24h via `gh`
**Campi meta:**

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `pr_number` | integer | Numero PR |
| `review_cycle_hours` | float | Ore da creazione PR a primo approval |
| `reviewers_count` | integer | Numero reviewer |

**Metrica:** lead time (end), review cycle time.

### 6. `session_end`

**Trigger:** `trap EXIT` in `hooks/session-start` oppure `hooks/session-end`
**Campi meta:**

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `duration_ms` | integer | Durata totale sessione |
| `skills_used_count` | integer | Skill distinte usate nella sessione |
| `commits_count` | integer | Commit effettuati nella sessione |

**Metrica:** produttività per sessione, durata media sessione.

---

## Metriche Derivabili per Audience

### Management / Stakeholder — KPI Business

| KPI | Formula | Fonte eventi |
|-----|---------|-------------|
| Adoption rate | `COUNT(DISTINCT user) con skill_invoked / totale dev` per settimana | `skill_invoked` |
| Lead time medio | `AVG(pr_merged.ts - pr_opened.ts)` per settimana | `pr_opened` + `pr_merged` |
| Throughput | `COUNT(commit_created)` per developer per settimana | `commit_created` |
| Test inclusion rate | `COUNT(commit WHERE has_tests=true) / COUNT(commit)` | `commit_created` |
| SDLC funnel completion | % sessioni che toccano tutte le fasi | `skill_invoked` (sdlc_phase) |

### Tech Lead — Operativo

| KPI | Formula | Fonte eventi |
|-----|---------|-------------|
| Tempo medio per skill | `AVG(skill_completed.duration_ms)` per skill_name | `skill_completed` |
| Skill failure rate | `COUNT(outcome=error) / COUNT(*)` per skill | `skill_completed` |
| TDD compliance | `COUNT(tdd_cycle WHERE phase=complete) / COUNT(commit_created)` | `tdd_cycle` + `commit_created` |
| Review cycle time | `AVG(review_cycle_hours)` per settimana | `pr_merged` |
| Skill più usate | `COUNT(*) GROUP BY skill_name` ranking | `skill_invoked` |

### Drill-down per Developer

| KPI | Formula | Fonte eventi |
|-----|---------|-------------|
| Sessioni/settimana | `COUNT(session_start)` per user | `session_start` |
| Durata media sessione | `AVG(session_end.duration_ms)` per user | `session_end` |
| Skill diversity | `COUNT(DISTINCT skill_name)` per user | `skill_invoked` |
| Commit per sessione | `commits_count` da `session_end` per user | `session_end` |
| Fasi SDLC coperte | `COUNT(DISTINCT sdlc_phase)` per sessione | `skill_invoked` |

---

## Implementazione Tecnica

### Nessuna modifica strutturale

- Schema base JSONL invariato (ts, user, sid, branch, jira_id, project, event, status, duration_ms, meta)
- `telemetry-upload.sh` invariato
- Infra S3/Lambda/API GW invariata
- Partitioning S3 invariato

### Call site per evento

| Evento | File da modificare | Logica |
|--------|-------------------|--------|
| `skill_completed` | `hooks/post-skill` | Calcola duration_ms dal skill_invoked.ts, logga outcome |
| `tdd_cycle` | `skills/siae-subagent-development/implementer-prompt.md` | Già predisposto — subagent chiama devforge_log |
| `commit_created` | `hooks/pre-commit` | Post-commit: `git diff --stat HEAD~1`, detect has_tests |
| `pr_opened` | Post-push trigger | `gh pr view --json number,baseRefName,changedFiles,commits` |
| `pr_merged` | `hooks/session-start` | `gh pr list --state merged --json` per PR ultime 24h |
| `session_end` | `hooks/session-start` (trap EXIT) | Conta skill e commit della sessione |

### Detection `has_tests`

```bash
echo "$changed_files" | grep -qE '(Test\.|_test\.|\.test\.|\.spec\.|/test/|/tests/)' && has_tests=true
```

Copre: Java (`*Test.java`), Python (`*_test.py`, `test_*`), TypeScript (`*.test.ts`, `*.spec.ts`).

### Detection `review_cycle_hours`

```bash
created_at=$(gh pr view $pr --json createdAt -q '.createdAt')
first_review=$(gh pr view $pr --json reviews -q '.reviews[0].submittedAt')
# delta in ore
```

---

## Gestione Errori e Edge Case

| Edge case | Gestione |
|-----------|----------|
| `gh` CLI non disponibile | Skip eventi `pr_opened`/`pr_merged`, logga gli altri |
| Sessione interrotta (kill, crash) | No `session_end` — query Athena trattano `duration=NULL` |
| Commit fuori da DevForge | Non catturato — misuriamo solo sessioni assistite |
| Branch senza JIRA ID | `jira_id=null` come oggi |
| `git diff --stat` fallisce | `files_changed=0, insertions=0, deletions=0` |
| Skill invocata mai completata | `skill_completed` con `outcome=aborted` |
| PR aperta da altro tool | Catturata al session-start successivo via `gh pr list` |
| Rate limit GitHub API | Timeout 5s, skip silenzioso |

**Non-goal:**
- NON tracciamo keystroke, idle time, o metriche invasive
- NON blocchiamo mai il workflow per telemetria
- NON logghiamo contenuto del codice, solo metadata numerici

---

## Testing

### Test unitari

| Test | Cosa verifica |
|------|--------------|
| `test_skill_completed_event` | post-skill emette evento con duration_ms > 0 e outcome valido |
| `test_commit_created_event` | Post-commit emette files_changed, insertions, deletions, has_tests |
| `test_has_tests_detection` | Pattern regex riconosce *Test.java, *_test.py, *.spec.ts, test_*.py |
| `test_pr_opened_no_gh` | Senza gh CLI, evento skippato senza errore |
| `test_pr_merged_cycle_hours` | review_cycle_hours calcolato correttamente |
| `test_session_end_counters` | skills_used_count e commits_count consistenti |
| `test_jsonl_format_unchanged` | Nuovi eventi rispettano schema base |

### Test integrazione

| Test | Cosa verifica |
|------|--------------|
| `test_full_session_lifecycle` | session_start → skill_invoked → skill_completed → commit_created → session_end produce JSONL valido |
| `test_upload_with_new_events` | telemetry-upload.sh carica file con mix vecchi e nuovi event type |

Estensione della suite `tests/run-all.sh`. Test bash con stub per `gh` e `git`.

---

## Criteri di Accettazione

| # | Criterio |
|---|----------|
| AC-1 | Ogni skill invocata produce coppia skill_invoked + skill_completed nel JSONL |
| AC-2 | skill_completed.duration_ms > 0 per ogni skill completata |
| AC-3 | Ogni git commit in sessione DevForge produce commit_created con files_changed, insertions, deletions, has_tests |
| AC-4 | has_tests=true se commit include file matching pattern test (Java/Python/TS) |
| AC-5 | pr_opened emesso dopo push con PR attiva (richiede gh) |
| AC-6 | pr_merged emesso al session-start se PR merge nelle ultime 24h |
| AC-7 | session_end emesso con duration_ms, skills_used_count, commits_count corretti |
| AC-8 | Senza gh CLI: eventi pr_* skippati, tutti gli altri funzionano |
| AC-9 | Nessun evento blocca il workflow — timeout max 5s su operazioni esterne |
| AC-10 | Schema JSONL invariato — vecchi e nuovi eventi coesistono nello stesso file |
| AC-11 | Tutti i test in tests/run-all.sh passano (esistenti + nuovi) |

---

## Trade-off Scelti

| Decisione | Alternativa scartata | Motivo |
|-----------|---------------------|--------|
| Solo telemetria plugin | Mining git history + JIRA | Effort 5 SP vs 13 SP, dati git estraibili in futuro |
| Trend temporale come misura | Baseline esplicita pre-DevForge | I dati git storici non scappano, gli eventi non loggati sì |
| has_tests con regex | Parsing AST o coverage tool | Regex copre 95% dei casi, zero dipendenze |
| pr_merged al session-start | Webhook GitHub | Zero infra aggiuntiva, delay max 24h accettabile |
| session_end via trap EXIT | Hook dedicato session-end | trap è più robusto, non richiede supporto Claude Code |
