# Superpowers Review System — Design Doc

**Data:** 2026-03-30
**Autore:** DevForge brainstorming
**SP:** 3 SP-Umano / 1 SP-Augmented
**Ispirazione:** obra/superpowers PR #334, #522

---

## Goal

Portare in DevForge il document review system e il GATE scaling da obra/superpowers.
6 gap da chiudere su 3 skill (siae-brainstorming, siae-writing-plans, siae-subagent-development).

## Contesto

- **PR #462 (HARD-GATE, anti-pattern):** gia' implementata in commit `a0ca7ab` + `e40078c`
- **PR #334 (placeholder scan):** gia' implementato in commit `b44a3d6`
- **PR #334 (document review system):** NON ancora portato — spec/plan reviewer + loop iterativo
- **PR #522 (GATE scaling):** NON ancora portato — scaling review per complessita' task

## Gap identificati

| # | Gap | PR fonte | Skill target |
|---|-----|----------|-------------|
| 1 | Spec document reviewer automatico | #334 | siae-brainstorming |
| 2 | Plan document reviewer chunk-by-chunk | #334 | siae-writing-plans |
| 3 | Loop iterativo fix-re-review (max 5) | #334 | siae-brainstorming + siae-writing-plans |
| 4 | GATE keyword per elidere review | #522 | siae-subagent-development |
| 5 | Check-in prima di transizione skill | #522 | siae-brainstorming (Step 6b potenziato) |
| 6 | Orchestrator boundary esplicita | #522 | siae-subagent-development |

## Approccio scelto: Document Review Completo

### Modifica 1: Spec Reviewer in siae-brainstorming

**File coinvolti:**
- `skills/siae-brainstorming/SKILL.md` — modifica Step 6b
- `skills/siae-brainstorming/spec-reviewer-prompt.md` — nuovo file

**Comportamento:**
1. Dopo scrittura design doc (Step 6), PRIMA del gate utente (Step 6b), lancia subagent spec-reviewer
2. Il reviewer analizza il design doc cercando:
   - Requisiti incompleti o ambigui
   - Criteri di accettazione vaghi (non testabili)
   - Decisioni architetturali non motivate
   - Scope creep (il design copre piu' di quanto richiesto)
   - Placeholder residui (TBD, TODO, "da definire")
   - Stime SP non giustificate
3. Output: lista issue con severity BLOCK / WARN
4. BLOCK → fix obbligatorio, poi re-review (loop max 5 iterazioni)
5. WARN → presentato all'utente per decisione
6. Solo dopo PASS → gate utente (Step 6b attuale)
7. Checkpoint strutturato:

```
[BRAINSTORM:SPEC-REVIEW] Review completata
  Issue: {N BLOCK / N WARN}
  Iterazioni: {N}/5
  DECISIONE: {PASS / FIX NECESSARIO}
```

**Spec reviewer prompt** — il reviewer riceve:
- Il design doc completo
- Il messaggio originale dell'utente (goal)
- Istruzione di essere scettico e preciso

Distinto dal spec-reviewer in subagent-dev (che verifica codice vs spec post-implementazione).

### Modifica 2: Plan Reviewer in siae-writing-plans

**File coinvolti:**
- `skills/siae-writing-plans/SKILL.md` — nuovo Step 3c dopo placeholder scan
- `skills/siae-writing-plans/plan-reviewer-prompt.md` — nuovo file

**Comportamento:**
1. Dopo placeholder scan (Step 3b, pattern testuali), lancia subagent plan-reviewer
2. Il reviewer analizza ogni task del piano verificando:
   - Path file esistono nel codebase (Glob check)
   - Codice completo (no `...`, no pseudocodice)
   - Comandi con output atteso specificato
   - Coerenza con il design doc (nessun drift)
   - Dipendenze tra task corrette e non circolari
   - Ogni task e' atomico (completabile in < 30 min)
3. Review chunk-by-chunk: ogni task-NN viene reviewato singolarmente
4. Output: lista issue con severity BLOCK / WARN per task
5. BLOCK → fix obbligatorio, poi re-review (loop max 5 iterazioni)
6. WARN → presentato all'utente
7. Solo dopo PASS → procedi a Step 4 (salvataggio)
8. Checkpoint strutturato:

```
[WRITING-PLANS:REVIEW] Plan review completata
  Task reviewati: {N}
  Issue: {N BLOCK / N WARN}
  Iterazioni: {N}/5
  DECISIONE: {PASS / FIX NECESSARIO}
```

**Differenza col placeholder scan (Step 3b):**
- Placeholder scan: pattern matching testuale (TBD, TODO, ...)
- Plan reviewer: verifica semantica (path validi, codice completo, coerenza col design)

### Modifica 3: GATE Scaling + Orchestrator Boundary in siae-subagent-development

**File coinvolto:**
- `skills/siae-subagent-development/SKILL.md`

**3a — GATE Scaling per review:**

Prima di lanciare i reviewer per un task, l'orchestratore valuta la complessita':

| Complessita' task | Segnali | Review |
|---|---|---|
| Bassa | config, rename, typo, 1-2 file, nessuna logica nuova | Solo code-quality (spec-review elidibile con conferma utente) |
| Media | CRUD, refactoring, 3-5 file | Entrambi (default) |
| Alta | Feature nuova, cross-module, integrazione | Entrambi (non elidibile) |

Regole:
- L'orchestratore propone, l'utente decide
- Per complessita' media/alta la review completa e' il default non elidibile
- Per complessita' bassa, l'orchestratore CHIEDE all'utente prima di elidere spec-review
- Code-quality review non e' MAI elidibile (errori di qualita' anche su task banali)

**3b — Orchestrator Boundary:**

Aggiungere al HARD-GATE di subagent-development:

> L'orchestratore NON implementa codice, NON fa review di codice, NON modifica file di produzione.
> Ruolo esclusivo: caricare task, dispatchare subagent, raccogliere risultati, aggiornare stato piano.
> "Posso farlo io velocemente" = bias accumulato = il motivo per cui esistono i subagent.

## Criteri di accettazione

- [ ] `siae-brainstorming/SKILL.md` Step 6b potenziato con spec-reviewer automatico prima del gate utente
- [ ] `siae-brainstorming/spec-reviewer-prompt.md` nuovo file con prompt del reviewer
- [ ] Loop iterativo max 5 in brainstorming con checkpoint strutturato
- [ ] `siae-writing-plans/SKILL.md` nuovo Step 3c Plan Review dopo placeholder scan
- [ ] `siae-writing-plans/plan-reviewer-prompt.md` nuovo file con prompt del reviewer
- [ ] Loop iterativo max 5 in writing-plans con checkpoint strutturato
- [ ] `siae-subagent-development/SKILL.md` GATE scaling per review con tabella complessita'
- [ ] `siae-subagent-development/SKILL.md` orchestrator boundary nel HARD-GATE
- [ ] Nessun breaking change alle skill esistenti

## Rischi

| Rischio | Mitigazione |
|---------|-------------|
| Review loop infinito (reviewer trova sempre qualcosa) | Max 5 iterazioni, poi escalation all'utente |
| Overhead su task semplici | GATE scaling in subagent-dev; brainstorming scaling gia' esistente |
| Spec reviewer troppo aggressivo (BLOCK su dettagli minori) | WARN vs BLOCK severity — solo issue strutturali sono BLOCK |

## File modificati (sommario)

| File | Azione |
|------|--------|
| `skills/siae-brainstorming/SKILL.md` | MODIFICA — Step 6b potenziato |
| `skills/siae-brainstorming/spec-reviewer-prompt.md` | NUOVO |
| `skills/siae-writing-plans/SKILL.md` | MODIFICA — nuovo Step 3c |
| `skills/siae-writing-plans/plan-reviewer-prompt.md` | NUOVO |
| `skills/siae-subagent-development/SKILL.md` | MODIFICA — GATE scaling + orchestrator boundary |
