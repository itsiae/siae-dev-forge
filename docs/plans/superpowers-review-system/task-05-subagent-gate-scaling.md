# Task 5 — GATE Scaling + Orchestrator Boundary in subagent-development

**File coinvolti:**
- `skills/siae-subagent-development/SKILL.md` (MODIFICA — 2 inserimenti)

---

## Step 1 — Leggi le sezioni rilevanti

Run: `grep -n "HARD-GATE\|EXTREMELY-IMPORTANT\|Step 3 — Dispatch Spec-Reviewer" skills/siae-subagent-development/SKILL.md`

Identifica:
- Dove finisce il blocco `</EXTREMELY-IMPORTANT>` del HARD-GATE (per orchestrator boundary)
- Dove inizia Step 3 (per GATE scaling)

## Step 2 — Aggiungi Orchestrator Boundary

Nel blocco `<EXTREMELY-IMPORTANT>` del HARD-GATE (righe 41-48 circa), dopo la riga
`"La review e' eccessiva per questo task" = i bug peggiori vengono dai task "semplici".`
e PRIMA di `</EXTREMELY-IMPORTANT>`, inserisci:

```markdown

**Orchestrator Boundary:**
L'orchestratore NON implementa codice, NON fa review di codice, NON modifica file
di produzione. Ruolo esclusivo: caricare task, dispatchare subagent, raccogliere
risultati, aggiornare stato piano.
"Posso farlo io velocemente" = bias accumulato = il motivo per cui esistono i subagent.
```

## Step 3 — Aggiungi GATE Scaling per review

Prima di `### Step 3 — Dispatch Spec-Reviewer` (riga 168 circa), inserisci:

```markdown
### Step 2b — GATE: Valuta Complessita' Task per Review Scaling

Prima di lanciare i reviewer, valuta la complessita' del task corrente.

| Complessita' | Segnali | Review |
|---|---|---|
| **Bassa** | config, rename, typo, 1-2 file, nessuna logica nuova | Solo code-quality-reviewer (spec-review elidibile con conferma utente) |
| **Media** | CRUD, refactoring, 3-5 file, logica moderata | Entrambi i reviewer (default, non elidibile) |
| **Alta** | Feature nuova, cross-module, integrazione, migrazione | Entrambi i reviewer (non elidibile) |

**Regole GATE:**
- Per complessita' bassa, CHIEDI all'utente: "Task '{nome}' e' a bassa complessita' (N file, nessuna logica nuova). Review completa (spec + code-quality) o ridotta (solo code-quality)?"
- Per complessita' media/alta, procedi con entrambi i reviewer senza chiedere
- L'utente decide SEMPRE — l'orchestratore non salta mai autonomamente
- Code-quality-reviewer non e' MAI elidibile (anche su task banali)
- Se in dubbio sulla complessita', tratta come media (entrambi i reviewer)

```

## Step 4 — Aggiungi alla tabella anti-razionalizzazione

Cerca la tabella anti-razionalizzazione in fondo al file (se esiste) e aggiungi:

```markdown
| "Questo task e' banale, posso implementarlo io" | L'orchestratore non implementa. Mai. Dispatcha un subagent. |
| "La review spec non serve per un rename" | Chiedi all'utente. Non decidere tu. GATE scaling. |
```

Se non esiste una tabella anti-razionalizzazione, non crearne una.

## Step 5 — Verifica

Run: `grep -c "Orchestrator Boundary" skills/siae-subagent-development/SKILL.md`
Output atteso: 1

Run: `grep -c "GATE.*Complessita'" skills/siae-subagent-development/SKILL.md`
Output atteso: almeno 1

Run: `grep -c "Step 2b" skills/siae-subagent-development/SKILL.md`
Output atteso: 1

## Step 6 — Commit

```bash
git add skills/siae-subagent-development/SKILL.md
git commit -m "feat(subagent-dev): add GATE scaling and orchestrator boundary

Adds review scaling by task complexity (low tasks can skip spec-review
with user confirmation). Adds explicit orchestrator boundary in HARD-GATE
section. Inspired by obra/superpowers PR #522."
```
