# Task 01 — Baseline pre-modifica PR-B: snapshot HLD + review

**Stato:** [PENDING]
**Owner:** human-in-the-loop (richiede dispatch live)
**Dipende da:** nessuno
**Blocca:** Task 02-07

## Goal

Salvare snapshot output corrente di `doc-generator` e `code-reviewer` su 2 dispatch noti, da usare come baseline per AC-6 no-regression diff.

## File coinvolti

- Nuovi: `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-05-dg-hld-pre.md`
- Nuovi: `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-06-cr-review-pre.md`

## Step 1 — Snapshot HLD pre-modifica

Dispatcha:

```
Agent({
  subagent_type: "doc-generator",
  description: "HLD sport-gestione-licenze",
  prompt: "Genera l'HLD per il servizio sport-gestione-licenze-service. Path repo: ${SPORT_KG_REPOS_DIR:-$HOME/sport-kg/data/repos}/sport-gestione-licenze-service/"
})
```

Salva l'output completo in `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-05-dg-hld-pre.md`.

## Step 2 — Snapshot review pre-modifica

Per il code-reviewer serve un cambio reale. Approccio: prendi una PR esistente del repo siae-dev-forge che non ha ancora review, oppure simula con un diff fittizio.

**Approccio semplice**: prendi il diff dell'ultimo commit dello sport-gestione-licenze-service repo:

```
Agent({
  subagent_type: "code-reviewer",
  description: "Review esempio sport-gestione-licenze",
  prompt: "Review della PR #<numero PR esistente> di sport-gestione-licenze-service. Focus su Point 4 (Architettura)."
})
```

Se non c'è una PR adatta, salta lo snapshot review pre-modifica e usa solo grep diff su `agents/code-reviewer.md` per AC-6 (verifica che la sezione esistente non sia stata rimossa). Documenta la scelta nel snapshot file.

Salva in `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-06-cr-review-pre.md`.

## Step 3 — Verifica e commit

```bash
ls -la docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-05-dg-hld-pre.md docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-06-cr-review-pre.md
```

Output atteso: 2 file presenti (anche se il secondo è una nota di "skipped per assenza PR target").

```bash
git add docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-05-dg-hld-pre.md docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-06-cr-review-pre.md
git commit -m "docs(measurements): baseline pre-modifica agents PR-B (HLD + review)

Snapshot 5: doc-generator HLD sport-gestione-licenze-service pre-mod
Snapshot 6: code-reviewer review pre-mod (o skip note)

Baseline per AC-6 no-regression diff dopo PR-B.

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 9.1

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] 2 file snapshot creati
- [ ] Snapshot 5 contiene HLD output completo (non vuoto)
- [ ] Snapshot 6 contiene review output o skip note documentata
- [ ] Commit creato
