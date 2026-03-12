# Citation-Based Verification — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Ogni claim di completamento e ogni finding di review deve citare `file:riga` come evidenza. Eliminare phantom completion.
**Architettura:** Edit a 3 file markdown: siae-verification SKILL.md, spec-reviewer-prompt.md, code-quality-reviewer-prompt.md
**Stack:** Markdown
**SP:** 2

---

## Task 1: siae-verification — Campo Evidenza in Step 5 + tabella NON conta [DONE]

**File coinvolti:**
- Modifica: `skills/siae-verification/SKILL.md`

**Step 1: Aggiorna formato obbligatorio in Step 5 AFFERMA**

Trova il blocco (circa riga 160):
```
VERIFICA COMPLETATA:
  Comandi:  [lista comandi eseguiti]
  Risultato: [output sintetico]
  Claim:    [la tua dichiarazione]
```

Sostituisci con:
```
VERIFICA COMPLETATA:
  Comandi:   [lista comandi eseguiti]
  Risultato: [output sintetico]
  Evidenza:
    - path/to/file.java:45 — metodo process() implementato
    - tests/test_file.py:12 — test should_validate_isrc passa
  Claim:     [la tua dichiarazione]
```

**Step 2: Aggiungi regola citazione dopo il formato**

Dopo il blocco formato, inserisci:
```markdown
**Regola citazione:** minimo 1 citazione `file:riga` per ogni requisito verificato.
Se non puoi citare `file:riga`, non puoi dichiarare quel requisito completato.
Formato standard: `path/to/file.ext:NN — descrizione breve`
```

**Step 3: Aggiungi riga alla tabella "Cosa NON Conta Come Verifica"**

Trova l'ultima riga della tabella:
```
| "Ho copiato da codice che funziona" | Il contesto e' diverso. Verifica nel nuovo contesto. |
```

Inserisci DOPO:
```
| "Ho verificato che funziona" (senza citare file:riga) | Prose senza citazione non sono evidenza. Cita file:riga o non e' verifica. |
```

**Step 4: Verifica**
```bash
grep "Evidenza:" skills/siae-verification/SKILL.md
grep "Prose senza citazione" skills/siae-verification/SKILL.md
```

**Step 5: Commit**
```bash
git add skills/siae-verification/SKILL.md
git commit -m "feat(verification): add citation-based evidence field to Step 5 AFFERMA"
```

---

## Task 2: spec-reviewer-prompt — CITATION RULE [DONE]

**File coinvolti:**
- Modifica: `skills/siae-subagent-development/spec-reviewer-prompt.md`

**Step 1: Aggiungi sezione CITATION RULE dopo DISTRUST PATTERN**

Trova (circa riga 59):
```
- Non fidarti delle assenze: cerca cio' che manca.

---

## Workflow
```

Inserisci tra `- Non fidarti delle assenze: cerca cio' che manca.` e `---`:
```markdown

---

## CITATION RULE

```
Ogni affermazione nel tuo report DEVE citare file:riga come evidenza.
Prose senza citazione = finding invalido.
```

**Per ogni [DONE]:**
- Cita `file:riga` dove l'implementazione esiste
- Esempio: `[DONE] Validazione ISRC — File: src/validator/IsrcValidator.java:34, Test: tests/IsrcValidatorTest.java:12`

**Per ogni [MISSING]:**
- Cita dove hai cercato e **non** trovato
- Esempio: `[MISSING] Endpoint /api/v1/obras — Cercato in: src/controller/ (0 match), src/routes/ (non esiste)`

**Per ogni [YAGNI]:**
- Cita il file e la riga dove il codice non richiesto esiste
- Esempio: `[YAGNI] Cache layer non nel design — File: src/service/CacheService.java:1`

**Nessuna prosa senza evidenza.** "Sembra implementato" senza file:riga = FAIL del reviewer.

```

**Step 2: Verifica**
```bash
grep "CITATION RULE" skills/siae-subagent-development/spec-reviewer-prompt.md
```

**Step 3: Commit**
```bash
git add skills/siae-subagent-development/spec-reviewer-prompt.md
git commit -m "feat(spec-reviewer): add CITATION RULE — every finding must cite file:line"
```

---

## Task 3: code-quality-reviewer-prompt — CITATION RULE [DONE]

**File coinvolti:**
- Modifica: `skills/siae-subagent-development/code-quality-reviewer-prompt.md`

**Step 1: Aggiungi sezione CITATION RULE dopo DISTRUST PATTERN**

Trova (circa riga 54):
```
Presumi che qualcosa sia stato saltato fino a prova contraria.

---

## Framework di Review — 6 Punti SIAE
```

Inserisci tra `Presumi che qualcosa sia stato saltato fino a prova contraria.` e `---`:
```markdown

---

## CITATION RULE

```
Ogni issue e ogni PASS nel tuo report DEVE citare file:riga verificato.
Nessuna affermazione positiva o negativa senza citazione.
```

**Per ogni issue (CRITICAL/MAJOR/MINOR/INFO):**
- Il campo `File: path/file.ext:NN` DEVE essere verificato (non inventato)
- Apri il file, leggi la riga, conferma che il problema esiste a quella riga
- Se non puoi verificare la riga, non segnalare l'issue

**Per ogni PASS nella CHECKLIST CONFORMITA':**
- Cita almeno 1 file come evidenza del PASS
- Esempio: `1. Standard SIAE: ✅ — src/service/UserService.java:1 (package it.siae.*, naming OK)`
- "Sembra conforme" senza citazione = il punto non e' stato verificato

**Formato citazione standard:** `path/to/file.ext:NN — descrizione breve`

```

**Step 2: Verifica**
```bash
grep "CITATION RULE" skills/siae-subagent-development/code-quality-reviewer-prompt.md
```

**Step 3: Commit**
```bash
git add skills/siae-subagent-development/code-quality-reviewer-prompt.md
git commit -m "feat(code-quality-reviewer): add CITATION RULE — every finding must cite file:line"
```

---

## Checklist Accettazione

- [ ] Step 5 AFFERMA in siae-verification include campo Evidenza obbligatorio
- [ ] Regola citazione con formato standard `file:riga — descrizione`
- [ ] spec-reviewer-prompt ha sezione CITATION RULE dopo DISTRUST PATTERN
- [ ] code-quality-reviewer-prompt ha sezione CITATION RULE dopo DISTRUST PATTERN
- [ ] Tabella "Cosa NON conta" aggiornata con "prose senza citazione"
