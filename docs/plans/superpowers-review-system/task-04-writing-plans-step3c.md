# Task 4 — Aggiungi Step 3c Plan Review in writing-plans

**Dipendenza:** Task 3 (plan-reviewer-prompt.md deve esistere)

**File coinvolti:**
- `skills/siae-writing-plans/SKILL.md` (MODIFICA — inserire Step 3c tra Step 3b e Step 4)

---

## Step 1 — Leggi il file attuale

Run: `grep -n "Step 3b\|Step 4\|Placeholder Scan\|Salva il Piano" skills/siae-writing-plans/SKILL.md`

Identifica dove finisce Step 3b (Placeholder Scan) e dove inizia Step 4 (Salva il Piano).

## Step 2 — Inserisci Step 3c dopo Step 3b

Dopo la riga `Un piano che passa questo gate ha zero ambiguita' per il subagent.`
(fine di Step 3b) e prima di `### Step 4 — Salva il Piano`, inserisci:

```markdown
### Step 3c — Plan Review (Gate Obbligatorio)

Dopo il placeholder scan (pattern testuali), lancia un subagent plan-reviewer
che verifica la qualita' semantica del piano.

**Differenza col placeholder scan (Step 3b):**
- Step 3b: pattern matching testuale (TBD, TODO, ...)
- Step 3c: verifica semantica (path validi, codice completo, coerenza col design)

**Processo:**

1. Lancia subagent con il prompt in [plan-reviewer-prompt.md](plan-reviewer-prompt.md)
   passando `{plan_directory}` e `{design_doc_path}`
2. Il reviewer analizza ogni task-NN-*.md singolarmente (chunk-by-chunk)
3. Leggi il report del reviewer
4. Se ci sono issue BLOCK:
   a. Fixa le issue nei task file
   b. Ri-lancia il reviewer (loop max 5 iterazioni)
   c. Se dopo 5 iterazioni ci sono ancora BLOCK → escalation all'utente
5. Se ci sono solo WARN (zero BLOCK):
   a. Presenta i WARN all'utente
6. Se zero issue: procedi a Step 4

**Checkpoint:**

```
[WRITING-PLANS:REVIEW] Plan review completata
  Task reviewati: {N}
  Issue: {N BLOCK / N WARN}
  Iterazioni: {N}/5
  DECISIONE: {PASS / FIX NECESSARIO}
```
```

## Step 3 — Verifica

Run: `grep -c "plan-reviewer-prompt.md" skills/siae-writing-plans/SKILL.md`
Output atteso: almeno 1 match

Run: `grep -c "Step 3c" skills/siae-writing-plans/SKILL.md`
Output atteso: almeno 1 match

Run: `grep -c "WRITING-PLANS:REVIEW" skills/siae-writing-plans/SKILL.md`
Output atteso: almeno 1 match

## Step 4 — Commit

```bash
git add skills/siae-writing-plans/SKILL.md
git commit -m "feat(writing-plans): add Step 3c plan review with semantic verification

Adds automated plan reviewer after placeholder scan. Checks path validity,
code completeness, design coherence, and dependency correctness per task.
Iterative fix loop (max 5). Inspired by obra/superpowers PR #334."
```
