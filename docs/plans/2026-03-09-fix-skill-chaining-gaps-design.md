# Fix Skill Chaining Gaps — Design Doc

> **Data:** 2026-03-09
> **Autore:** DevForge AI CC
> **SP:** 1 (triviale)

## Contesto

Audit del flusso SDLC ha rivelato 3 skill con 0 referenze da altre skill:

| Skill | Fase | Referenze |
|-------|------|-----------|
| `siae-executing-plans` | 4. Implementation | 0 |
| `siae-git-worktrees` | 1. Init | 0 |
| `siae-service-logic-map` | 1. Init | 0 |

## Approccio scelto

Aggiungere i collegamenti mancanti nei SKILL.md delle skill "parent" che dovrebbero referenziarle.

## Modifiche

### 1. `siae-writing-plans/SKILL.md`
- Aggiungere `REQUIRED SUB-SKILL: siae-executing-plans` nell'opzione "sessione separata" (Step 5)
- Aggiornare diagramma integrazione SDLC
- Aggiungere `siae-executing-plans` nelle skill correlate

### 2. `siae-executing-plans/SKILL.md`
- Aggiungere Step 0 opzionale per `siae-git-worktrees` (workspace isolato)
- Aggiungere `siae-git-worktrees` nelle skill correlate

### 3. `siae-microservices-map/SKILL.md`
- Aggiungere sezione "Step Successivo" con `REQUIRED SUB-SKILL: siae-service-logic-map`

## Criteri di accettazione
- [ ] Le 3 skill hanno almeno 1 referenza da altre skill
- [ ] `bash tests/run-all.sh` passa
- [ ] Nessuna skill rimane orfana (escluse entry-point intenzionali)
