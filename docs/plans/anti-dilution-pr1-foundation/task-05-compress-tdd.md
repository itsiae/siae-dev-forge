# Task 05 — Comprimere skills/siae-tdd/SKILL.md (578→180 righe)

**Stato:** [PENDING]
**Execution:** subagent (parallel-safe)
**Dipendenze:** T01
**Durata stimata:** 10-12 min

## Goal

Comprimere `skills/siae-tdd/SKILL.md` da 578 a ≤180 righe preservando tutte le regole TDD.

## Classificazione K/M/D

| Sezione | Riga | Classe | Azione |
|---|---|---|---|
| `## LA LEGGE DI FERRO` | 30 | K | Verbatim |
| `## Quando si applica` | 69 | K | Verbatim (compatto) |
| `## Scaling` | 86 | K | Verbatim (compatto) |
| `## Rilevamento Tipo Codice` | 105 | K | Verbatim (Context-First + Detection mapping) |
| `### Codice Frontend` | 129 | M | Merge in "Detection" come riga tabella |
| `## Workflow RED-GREEN-REFACTOR` | 147 | K | Verbatim per i 4 step (RED/GREEN/REFACTOR/COMMIT) |
| `## Permission Denied Handling` | 223 | M | Sostituisci con ref a `lib/permission-denied-handling.md` |
| `## Framework per Linguaggio` | 259-392 | D | **Riduci drasticamente**: tabella 8 righe con 1 esempio-tipo per linguaggio (Java JUnit, TS Vitest, Python pytest, HCL terraform-test). Elimina esempi inline estesi. |
| `## Classificazione Rischio` | 393 | M | Ref a `lib/risk-taxonomy.md` |
| `## Limiti Operativi` | 406 | M | Ref a `lib/operational-limits.md` |
| `## Tabella Anti-Razionalizzazione` | 422 | D | Elimina |
| `## Red Flags — FERMATI` | 446 | K | Verbatim (regole hard) |
| `## Coverage Target` | 467 | M | Comprimi a tabella 3 righe: feature=80%, bugfix=70%, config=n/a |
| `## Output Strutturato Obbligatorio` | 484 | K | Verbatim checkpoint (RED, GREEN, REFACTOR, COMMIT) |
| `## Checklist di Verifica` | 533 | D | Elimina (ridondante con Output Strutturato) |
| `## Quando sei bloccato` | 552 | D | Elimina (didattica) |
| `## Regola Finale` | 563 | K | Verbatim |
| `## Tecniche di Supporto` | 574 | D | Elimina (didattica) |

## Step

Stessi 7 step di T04 (baseline → rewrite → verifica target → smoke frontmatter → checkpoint preservation → catalog → commit).

Check specifici TDD:
```bash
# Step 5 variant: verifica checkpoint TDD
for cp in RED GREEN REFACTOR COMMIT; do
  grep -q "\[TDD:$cp\]" skills/siae-tdd/SKILL.md && echo "PASS $cp" || echo "FAIL $cp"
done
```
Output atteso: 4 PASS.

```bash
# Verifica Red Flags presente
grep -q "## Red Flags" skills/siae-tdd/SKILL.md && echo "PASS red_flags"
```

## Commit message

```
refactor(skills): compress siae-tdd SKILL.md (578->180 lines)

Part of PR #1 anti-dilution (ADR-003).
K preserved: Legge di Ferro, Workflow RED-GREEN-REFACTOR, Red Flags, Checkpoint.
M referenced: framework-per-lingua compressa a tabella; risk/limits/permission referenced via lib/*.md.
D removed: esempi framework estesi, Tabella Anti-Razionalizzazione, Checklist Verifica, Tecniche Supporto.
Behaviour-impacting rules: ZERO changes.
```

## Acceptance

- [ ] `wc -l` ≤ 180
- [ ] 4 checkpoint TDD presenti (RED/GREEN/REFACTOR/COMMIT)
- [ ] `## Red Flags` mantenuto
- [ ] Legge di Ferro invariata
- [ ] Commit conventional
