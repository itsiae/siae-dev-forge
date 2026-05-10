# Task 07 — Smoke test Test 3 + Test 4 + diff baseline

**Stato:** [PENDING]
**Owner:** human-in-the-loop (richiede dispatch live)
**Dipende da:** Task 02-06

## Goal

Validare PR-B con 2 smoke test (doc-generator HLD + code-reviewer review) e diff vs baseline (Task 01) per verificare AC-5 e AC-6.

## File coinvolti

- Nuovi: `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-07-dg-hld-post.md`
- Nuovi: `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-08-cr-review-post.md`
- Nuovi: `docs/measurements/2026-05-03-pre-modifica-baseline/diff-pr-b-validation.md`

## Step 1 — Test 3 post-modifica: doc-generator HLD

Stesso dispatch di Task 01:

```
Agent({
  subagent_type: "doc-generator",
  description: "HLD sport-gestione-licenze POST",
  prompt: "Genera l'HLD per il servizio sport-gestione-licenze-service. Path repo: ${SPORT_KG_REPOS_DIR:-$HOME/sport-kg/data/repos}/sport-gestione-licenze-service/"
})
```

Salva output in `snapshot-07-dg-hld-post.md`.

### Check binari Test 3 (dal design § 9.3)

```bash
grep -c "Batch Schedulers\|swim lane.*Batch\|@Scheduled" snapshot-07-dg-hld-post.md
```
Atteso: ≥ 1 (sport-gestione-licenze-service ha @Scheduled noto)

```bash
grep -c "Authentication chain\|IdP primary" snapshot-07-dg-hld-post.md
```
Atteso: ≥ 1 (security section auth chain)

```bash
grep -c "Domain rules\|Drools\|Rule name" snapshot-07-dg-hld-post.md
```
Atteso: ≥ 1 (sport-gestione-licenze-service ha Drools rules)

```bash
grep -c "Topologia osservata\|observed_at" snapshot-07-dg-hld-post.md
```
Atteso: ≥ 1 (footer freshness)

## Step 2 — Test 4 post-modifica: code-reviewer

Stesso dispatch di Task 01 (o approccio alternativo se non c'era PR target):

```
Agent({
  subagent_type: "code-reviewer",
  description: "Review esempio sport-gestione POST",
  prompt: "Review della PR #<numero PR esistente> di sport-gestione-licenze-service. Focus su Point 4 (Architettura)."
})
```

Salva output in `snapshot-08-cr-review-post.md`.

### Check binari Test 4

```bash
grep -c "Drift KG\|graph_consistency_check\|CONSISTENT\|INCONSISTENT\|INSUFFICIENT_DATA\|KG cross-check non disponibile" snapshot-08-cr-review-post.md
```
Atteso: ≥ 1 (Point 4 cita risultato consistency_check OPPURE fallback "MCP non disponibile")

```bash
# Verifica review continua a funzionare se MCP down
grep -c "Point 1\|Point 2\|Point 3\|Point 5\|Point 6" snapshot-08-cr-review-post.md
```
Atteso: ≥ 5 (review completa anche se Point 4 ha solo fallback)

## Step 3 — Diff baseline (AC-6 no-regression)

```bash
diff docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-05-dg-hld-pre.md \
     docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-07-dg-hld-post.md \
  > /tmp/diff-dg.txt 2>&1 || true

diff docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-06-cr-review-pre.md \
     docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-08-cr-review-post.md \
  > /tmp/diff-cr.txt 2>&1 || true
```

### Check no-regression

Stesso pattern di PR-A Task 09:
- Righe rimosse (`<`): SOLO righe modificate accettabili (es. version bump in cover) o ZERO
- Righe aggiunte (`>`): tutte accettabili (campi nuovi del design)

Pattern accettabili rimossi: nessuno specifico per PR-B (sono tutte aggiunte additive).

Pattern NON accettabili: sezioni HLD esistenti (Domain model, Components, Security) rimosse o riordinate.

## Step 4 — Documenta diff

Crea `diff-pr-b-validation.md`:

```markdown
# PR-B Validation — Diff baseline vs post-modifica

**Data:** 2026-05-03
**Snapshots:** snapshot-05..08

## Test 3 (doc-generator HLD)

### Check binari
- [x/✗] Batch Schedulers swim lane presente
- [x/✗] Authentication chain block presente
- [x/✗] Domain rules section presente
- [x/✗] Footer freshness presente

### Diff (AC-6)
- Righe rimosse: <N>
- Righe aggiunte: <M>
- **No-regression: PASS / FAIL**

## Test 4 (code-reviewer)

### Check binari
- [x/✗] Point 4 cita drift result o fallback
- [x/✗] Review completa (5+ Point coperti)

### Diff (AC-6)
- Righe rimosse: <N>
- Righe aggiunte: <M>
- **No-regression: PASS / FAIL**

## Verdict overall PR-B

- AC-5 (smoke test): PASS / FAIL
- AC-6 (no-regression): PASS / FAIL
```

## Step 5 — Commit risultati

```bash
git add docs/measurements/2026-05-03-pre-modifica-baseline/
git commit -m "docs(measurements): smoke test PR-B post-modifica + diff validation

Test 3: doc-generator HLD sport-gestione-licenze-service
Test 4: code-reviewer review esempio

AC-5 smoke test: <PASS/FAIL>
AC-6 no-regression: <PASS/FAIL>

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 9.3
Refs: docs/plans/agents-sport-kg-v2-recezione-pr-b/overview.md AC-5 + AC-6

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] Test 3: 4/4 check binari PASS
- [ ] Test 4: 2/2 check binari PASS
- [ ] Diff Test 3: solo aggiunte
- [ ] Diff Test 4: solo aggiunte
- [ ] `diff-pr-b-validation.md` creato e committato
- [ ] Verdict overall: AC-5 PASS + AC-6 PASS

## Se FAIL

- Identifica task con regressione (git bisect tra Task 02-06)
- Fix + ri-esegui smoke test
- Aggiorna diff-pr-b-validation.md
- Non procedere a PR fino a tutti PASS
