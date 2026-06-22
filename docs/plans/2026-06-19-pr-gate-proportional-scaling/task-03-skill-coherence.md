# Task 03 — Allineamento SKILL.md (coerenza skill↔hook, ADR-4)

**Goal:** aggiornare `siae-premortem` e `siae-blind-review` SKILL.md così che NON
contraddicano il nuovo comportamento advisory dei gate su `risk=low`.

**File:** modifica `skills/siae-premortem/SKILL.md` + `skills/siae-blind-review/SKILL.md`.
**Copre:** Criterio #7 del design. **Tipo:** documentale (no TDD — è prosa skill).

---

## Step 1 — Verifica testo attuale (RED-equivalente: grep deve trovare la contraddizione)

```bash
grep -n "Nessun bypass discrezionale" skills/siae-premortem/SKILL.md
grep -n "esclusivamente documentali" skills/siae-blind-review/SKILL.md
```
Atteso: match presenti (la contraddizione esiste oggi).

## Step 2 — Modifica `skills/siae-premortem/SKILL.md` (DUE occorrenze)

**2a — righe 50-52** (sezione "Quando si applica"). old_string ESATTO (3 righe + parentetica):
```
**Nessun bypass discrezionale:** il gate `pr-premortem-gate` non è più
aggirabile. Anche per hotfix P1, bump meccanici o revert va invocata la skill
(per questi casi il premortem è breve: poche righe sulle top cause).
```
new_string:
```
**Scaling sul rischio del diff:** il gate `pr-premortem-gate` blocca per diff
`risk=code`. Per diff `risk=low` (doc-only / manifest plugin, classificato da
`lib/diff-risk-classifier.sh`) il gate è advisory automatico — il premortem resta
consigliato (breve) ma non obbligatorio. Per qualsiasi diff che tocca codice/config
eseguibile la skill va invocata.
```

**2b — riga 175** (sezione "Vincoli", WARN-3 plan-review). old_string:
```
6. **Nessun bypass discrezionale:** il gate non è aggirabile; anche hotfix/bump/revert richiedono un premortem (breve)
```
new_string:
```
6. **Scaling sul rischio:** il gate blocca per diff `risk=code`; per `risk=low` (doc/manifest, via `lib/diff-risk-classifier.sh`) è advisory. Nessun bypass discrezionale oltre questo.
```

## Step 3 — Modifica `skills/siae-blind-review/SKILL.md`

Nella sezione "Eccezioni", la voce "Modifiche esclusivamente documentali (nessun codice
di produzione)" che richiede "chiedi esplicitamente al partner umano" → aggiorna a:

```
- Modifiche esclusivamente documentali / manifest plugin (`risk=low` via
  `lib/diff-risk-classifier.sh`): il gate `pr-blind-review-gate` è advisory automatico,
  nessuna conferma umana manuale richiesta. Per qualsiasi diff `risk=code` la blind
  review resta obbligatoria.
```

## Step 4 — Verifica (GREEN)

```bash
# Nessuna contraddizione residua (cattura ENTRAMBE le occorrenze, con/senza "più"):
grep -c "aggirabile" skills/siae-premortem/SKILL.md   # atteso 0
grep -c "risk=low" skills/siae-premortem/SKILL.md      # atteso >=1
grep -c "risk=low" skills/siae-blind-review/SKILL.md   # atteso >=1
```
Atteso: `0` "aggirabile" (entrambe le occorrenze sostituite), `>=1` `risk=low` in entrambe.

## Step 5 — Commit
```bash
git add skills/siae-premortem/SKILL.md skills/siae-blind-review/SKILL.md
git commit -m "docs(skills): allinea premortem+blind-review allo scaling gate risk=low (task-03)"
```

## Criteri di accettazione
- [ ] `siae-premortem` SKILL.md: ZERO occorrenze di "aggirabile" (entrambe righe 50-52 e 175 sostituite).
- [ ] Entrambe le SKILL.md citano `risk=low` + `lib/diff-risk-classifier.sh` come condizione advisory.
- [ ] Nessuna contraddizione residua skill↔hook (la skill descrive lo stesso comportamento del gate).
- [ ] Il count "45/62 skill" NON cambia (modifica in-place, nessuna dir skill aggiunta/rimossa).
