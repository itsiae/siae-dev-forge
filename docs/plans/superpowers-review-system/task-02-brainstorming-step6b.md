# Task 2 — Potenzia Step 6b in brainstorming con review automatica

**Dipendenza:** Task 1 (spec-reviewer-prompt.md deve esistere)

**File coinvolti:**
- `skills/siae-brainstorming/SKILL.md` (MODIFICA — Step 6b, righe 275-295)

---

## Step 1 — Leggi il file attuale

Run: `sed -n '270,300p' skills/siae-brainstorming/SKILL.md`

Verifica che Step 6b "Spec Review Gate" inizi intorno a riga 275.

## Step 2 — Sostituisci Step 6b

Sostituisci il blocco corrente di Step 6b (da `### 6b. Spec Review Gate` fino a
`Se l'utente chiede modifiche, aggiorna il design doc e ripresenta il gate.`)
con questo contenuto:

```markdown
### 6b. Spec Review Gate (con reviewer automatico)

Prima di chiedere conferma all'utente, lancia un subagent spec-reviewer
che analizza il design doc automaticamente.

**Processo:**

1. Lancia subagent con il prompt in [spec-reviewer-prompt.md](spec-reviewer-prompt.md)
   passando `{design_doc_path}` e `{user_goal}` (il messaggio originale dell'utente)
2. Leggi il report del reviewer
3. Se ci sono issue BLOCK:
   a. Fixa le issue nel design doc
   b. Ri-lancia il reviewer (loop max 5 iterazioni)
   c. Se dopo 5 iterazioni ci sono ancora BLOCK → escalation all'utente
4. Se ci sono solo WARN (zero BLOCK):
   a. Presenta i WARN all'utente insieme al gate di conferma
5. Se zero issue: presenta il gate di conferma standard

**Checkpoint:**

```
[BRAINSTORM:SPEC-REVIEW] Review completata
  Issue: {N BLOCK / N WARN}
  Iterazioni: {N}/5
  DECISIONE: {PASS / FIX NECESSARIO}
```

Dopo il PASS del reviewer, presenta il gate utente:

```
Il design doc e' stato reviewato automaticamente (N iterazioni, 0 BLOCK).
{Se WARN presenti: "N avvertimenti non bloccanti:
- [WARN] descrizione
"}
Prima di passare al piano implementativo, conferma:

- I requisiti sono completi? Non manca nulla?
- I criteri di accettazione coprono tutti i casi?
- Le decisioni architetturali sono corrette?
- Le stime SP sono realistiche?
- La spec e' focalizzata su un singolo dominio? Non copre troppi sottosistemi?

Se tutto e' corretto, procedo con siae-writing-plans.
Se qualcosa non torna, dimmi cosa modificare.
```

NON invocare siae-writing-plans senza conferma esplicita a questo gate.
Se l'utente chiede modifiche, aggiorna il design doc e ri-esegui il reviewer.
```

## Step 3 — Aggiungi checkpoint a sezione "Output Strutturato Obbligatorio"

Dopo il checkpoint `[BRAINSTORM:DESIGN]` (circa riga 355), aggiungi:

```markdown
**Dopo Spec Review automatica (Step 6b):**
```
[BRAINSTORM:SPEC-REVIEW] Review completata
  Issue: {N BLOCK / N WARN}
  Iterazioni: {N}/5
  DECISIONE: {PASS / FIX NECESSARIO}
```
```

## Step 4 — Verifica

Run: `grep -c "spec-reviewer-prompt.md" skills/siae-brainstorming/SKILL.md`
Output atteso: almeno 1 match

Run: `grep -c "BRAINSTORM:SPEC-REVIEW" skills/siae-brainstorming/SKILL.md`
Output atteso: almeno 2 match (uno nel processo, uno nei checkpoint)

## Step 5 — Commit

```bash
git add skills/siae-brainstorming/SKILL.md
git commit -m "feat(brainstorming): add automated spec review before user gate

Step 6b now launches a spec-reviewer subagent that checks design docs
for completeness and ambiguity before asking user confirmation.
Iterative fix loop (max 5). Inspired by obra/superpowers PR #334."
```
