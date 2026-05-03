# Task 09 — Smoke test Test 1 + Test 2 + diff baseline

**Stato:** [PENDING]
**Owner:** human-in-the-loop (richiede dispatch live + interpretation)
**Dipende da:** Task 02-08

## Goal

Validare PR-A con 2 smoke test (mcp-impact-analyst + qa-investigator) e diff vs baseline (Task 01) per verificare AC-2 e AC-3.

## File coinvolti

- Nuovi: `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-03-mia-pagamento-post.md`
- Nuovi: `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-04-qa-apigateway-post.md`
- Nuovi: `docs/measurements/2026-05-03-pre-modifica-baseline/diff-pr-a-validation.md`

## Step 1 — Test 1 post-modifica: mcp-impact-analyst

Stesso dispatch di Task 01:

```
Agent({
  subagent_type: "mcp-impact-analyst",
  description: "Pre-flight licenze pagamento POST",
  prompt: "Devo aggiungere arricchimento profili locale alla conferma pagamento in PagamentoServiceImpl di sport-gestione-licenze-service. Esegui pre-flight."
})
```

Salva output in `snapshot-03-mia-pagamento-post.md`.

### Check binari Test 1 (dal design § 9.2)

Ogni assertion deve essere verificata via grep sull'output:

```bash
grep -c "Freshness:" snapshot-03-mia-pagamento-post.md
```
Atteso: ≥ 1 (riga `Freshness:` presente con observed_at + ttl_hint)

```bash
grep -c "Falsifiable_by:" snapshot-03-mia-pagamento-post.md
```
Atteso: ≥ 1 (campo presente, può essere vuoto ma c'è)

```bash
grep -c "Batch jobs:\|Business rules:" snapshot-03-mia-pagamento-post.md
```
Atteso: ≥ 1 (almeno una sezione presente — `sport-gestione-licenze-service` ha @Scheduled + Drools rules note)

```bash
grep -c -E "(CONFIRMED|PARTIAL|NOT_FOUND_IN_INDEX|PROVEN_ABSENT_UNDER_SCOPE|REFUTED)" snapshot-03-mia-pagamento-post.md
```
Atteso: ≥ 1 (almeno 1 occorrenza enum v2 nei vincoli)

## Step 2 — Test 2 post-modifica: qa-investigator

Stesso dispatch di Task 01:

```
Agent({
  subagent_type: "qa-investigator",
  description: "Caller apigateway-ext auth POST",
  prompt: "Quali sono i clienti che eseguono chiamate dei MS SPORT contattando apigateway-service-ext e che tipo di auth usano?"
})
```

Salva output in `snapshot-04-qa-apigateway-post.md`.

### Check binari Test 2

```bash
grep -c -E "(CONFIRMED|PARTIAL|NOT_FOUND_IN_INDEX|PROVEN_ABSENT_UNDER_SCOPE|REFUTED)" snapshot-04-qa-apigateway-post.md
```
Atteso: ≥ 2 (Confidence + Stato hint utente)

```bash
grep "who_authenticates" agents/qa-investigator.md | wc -l
```
Atteso: ≥ 2 (frontmatter tools + select bulk Step 0 — verifica che la fix di consistenza Task 05 sia ancora in posto)

## Step 3 — Diff baseline (AC-3 no-regression)

```bash
diff docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-01-mia-pagamento.md \
     docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-03-mia-pagamento-post.md \
  > /tmp/diff-mia.txt 2>&1 || true

diff docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-02-qa-apigateway.md \
     docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-04-qa-apigateway-post.md \
  > /tmp/diff-qa.txt 2>&1 || true
```

### Check no-regression

Per ogni diff:
- Tutte le righe `<` (rimosse) devono essere SOLO righe modificate (es. enum v1 → v2 nelle stringhe esistenti) o ZERO. Nessuna sezione legacy completamente rimossa.
- Tutte le righe `>` (aggiunte) sono accettabili (sono i campi nuovi del design).

### Pattern accettabili in righe rimosse:
- `< CONFIRMED | PARTIAL | REFUTED` → `> CONFIRMED | PARTIAL | NOT_FOUND_IN_INDEX | PROVEN_ABSENT_UNDER_SCOPE | REFUTED` (espansione enum)

### Pattern NON accettabili (= regressione):
- Sezioni intere rimosse (es. "Top vincoli" sparito)
- Campi base rimossi (es. "Confidence:" sparito)
- Ordine output cambiato (skill chiamanti potrebbero parsare regex)

## Step 4 — Documenta diff

Crea `diff-pr-a-validation.md`:

```markdown
# PR-A Validation — Diff baseline vs post-modifica

**Data:** 2026-05-03
**Snapshots:** snapshot-01..04

## Test 1 (mcp-impact-analyst)

### Check binari
- [x/✗] Freshness: presente
- [x/✗] Falsifiable_by: presente
- [x/✗] Batch jobs/Business rules: almeno 1 sezione
- [x/✗] Enum v2 presente nei vincoli

### Diff (AC-3)
- Righe rimosse: <N>
- Righe aggiunte: <M>
- Pattern rimossi accettabili: <lista>
- **No-regression: PASS / FAIL**

## Test 2 (qa-investigator)

### Check binari
- [x/✗] Enum v2 in Confidence + Stato hint
- [x/✗] who_authenticates in select bulk

### Diff (AC-3)
- Righe rimosse: <N>
- Righe aggiunte: <M>
- **No-regression: PASS / FAIL**

## Verdict overall PR-A

- AC-2 (smoke test): PASS / FAIL
- AC-3 (no-regression): PASS / FAIL
```

## Step 5 — Commit risultati

```bash
git add docs/measurements/2026-05-03-pre-modifica-baseline/
git commit -m "docs(measurements): smoke test PR-A post-modifica + diff validation

Test 1: mcp-impact-analyst su sport-gestione-licenze-service pagamento
Test 2: qa-investigator su apigateway-service-ext auth

AC-2 smoke test: <PASS/FAIL>
AC-3 no-regression: <PASS/FAIL>

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 9.2
Refs: docs/plans/agents-sport-kg-v2-recezione-pr-a/overview.md AC-2 + AC-3

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] Test 1: 4/4 check binari PASS
- [ ] Test 2: 2/2 check binari PASS
- [ ] Diff Test 1: solo aggiunte (o aggiunte + espansioni enum accettabili)
- [ ] Diff Test 2: solo aggiunte
- [ ] `diff-pr-a-validation.md` creato e committato
- [ ] Verdict overall: AC-2 PASS + AC-3 PASS

## Se FAIL

Se almeno 1 check fallisce:
- Identifica quale task ha introdotto la regressione (git bisect tra Task 02-08)
- Fixa il task specifico
- Ri-esegui smoke test
- Aggiorna `diff-pr-a-validation.md`
- Non procedere a PR fino a tutti PASS
