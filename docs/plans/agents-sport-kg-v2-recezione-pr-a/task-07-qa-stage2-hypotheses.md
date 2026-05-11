# Task 07 — qa-investigator: Stage 2 alternate_hypotheses per evidence ambigua

**Stato:** [PENDING]
**Dipende da:** Task 06
**Blocca:** Task 08

## Goal

Aggiungere allo Stage 2 (ES runtime) la chiamata `alternate_hypotheses(claim)` quando l'evidence è ambigua (sample-based, cap raggiunto, signal multipli divergenti).

## File coinvolti

- `agents/qa-investigator.md` (sezione "### Stage 2 — ES runtime" riga ~165-185)

## Step 1 — TDD test pre-modifica

```bash
grep -c "alternate_hypotheses" agents/qa-investigator.md
```
Output atteso pre-modifica (post Task 05): `1` (solo nel select bulk Step 0).

## Step 2 — Modifica Stage 2

Trova la sezione esistente "### Stage 2 — ES runtime" (riga ~165). Dopo la sub-sezione "**Pattern Q&A comuni**" e prima di "**Fail-fast**", inserisci:

```markdown
#### Disambiguazione evidence ambigua (alternate_hypotheses)

Se Stage 2 produce evidence ambigua (almeno uno dei seguenti):
- ES ritorna sample con cap=200 raggiunto e i campioni non concordano
- Multipli sourceSystem candidati per uno stesso caller M2M
- KG e ES divergono su attribution (es. KG dice IdP=AAS, ES log mostrano CIAM)

Chiama:

```
mcp__sport-kg__alternate_hypotheses(claim="<claim oggetto della Q&A>")
```

Output atteso: 2-3 ipotesi ranked con `plausibility_score` (0.0-1.0) e
`falsifiable_by` per ognuna. **NON sostituire il tuo reasoning** — usa il
ranking come input per arricchire il report:

- Ipotesi #1 (top score): claim primario, status `PARTIAL` con plausibility=<X>
- Ipotesi #2: claim alternativo nel "Gap residui" come "ipotesi non scartata"
- Ipotesi #3: claim alternativo nel "Gap residui" se plausibility ≥ 0.3

Il report finale cita esplicitamente "alternate_hypotheses ha suggerito N ipotesi
con scores [X, Y, Z]" come evidence_type=`inference` (non come fatto).
```

## Step 3 — Aggiorna sezione "Output — REQUIRED FORMAT"

Nella sezione "### Evidenze per claim" (template tabella, riga ~222), aggiungi nota dopo la tabella:

```markdown
**Note evidence_type aggiuntivi (Stage 2 v2)**:
- `alternate_hypotheses` → evidence_type = `inference` con score esplicitato (es. "plausibility=0.72 da alternate_hypotheses")
- `graph_consistency_check INCONSISTENT` → evidence_type = `KG-drift` (nuovo) per signal di drift KG↔ES
```

## Step 4 — Aggiorna anti-razionalizzazione

Nella sezione "## Anti-razionalizzazione" (riga ~314), aggiungi righe:

```markdown
| "Top hypothesis di alternate_hypotheses è la verità" | NO — è un primitivo MCP-side che ranks ipotesi. La verità si stabilisce con evidence concorrenti, non con score. Cita score come `inference`, non come fatto. |
| "Posso skip alternate_hypotheses se il sample concorda" | OK skip se evidence è univoca. Usa solo se ambigua (cap raggiunto, sourceSystem multipli, KG↔ES divergenti). |
```

## Step 5 — TDD verify

```bash
grep -c "alternate_hypotheses" agents/qa-investigator.md
```
Output atteso post-modifica: ≥ 5 (select bulk + Stage 2 + output evidence + 2 anti-razionalizzazione)

```bash
grep -c "plausibility_score\|plausibility=" agents/qa-investigator.md
```
Output atteso post-modifica: ≥ 2

```bash
grep -c "KG-drift" agents/qa-investigator.md
```
Output atteso post-modifica: ≥ 1

## Step 6 — Commit

```bash
git add agents/qa-investigator.md
git commit -m "feat(agents): qa-investigator Stage 2 alternate_hypotheses per evidence ambigua

Stage 2 (ES runtime):
- Nuova sub-sezione 'Disambiguazione evidence ambigua' (cap raggiunto,
  sourceSystem multipli, KG vs ES divergenti)
- Chiamata alternate_hypotheses(claim) con score ranking
- Pattern: top hypothesis -> claim primario PARTIAL; altre nel Gap residui

Output REQUIRED FORMAT:
- Aggiunto evidence_type 'inference' con plausibility score esplicitato
- Aggiunto evidence_type 'KG-drift' per graph_consistency_check INCONSISTENT

Anti-razionalizzazione:
- Top hypothesis non e verita (e' inference, cita come tale)
- Skip OK se evidence e univoca

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.2

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] Stage 2 ha sotto-sezione "Disambiguazione evidence ambigua"
- [ ] Output evidence_type include `inference` con plausibility score
- [ ] Anti-razionalizzazione ha 2 righe nuove
- [ ] grep checks passano
- [ ] Commit creato
