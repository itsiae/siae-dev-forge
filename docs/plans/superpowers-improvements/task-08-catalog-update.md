# Task 8 — Aggiorna catalogo using-devforge

**Stato:** [PENDING]
**Dipendenze:** Task 4, Task 6 (le nuove skill devono esistere)
**File coinvolti:**
- `skills/using-devforge/SKILL.md`

---

## Step 1 — Aggiungi siae-blind-review al catalogo

Apri `skills/using-devforge/SKILL.md`.
Trova la tabella `**Dynamic Skill Catalog (auto-generated):**`.
Aggiungi nella posizione corretta per fase SDLC (dopo siae-debugging, nella sezione 6. QA Gate):

```markdown
| siae-blind-review | "blind review", "review cieca", "audit spec", "verifica spec vs codice", "review senza diff", /forge-blind-re... | Rigid | 6. QA Gate |
```

## Step 2 — Aggiungi siae-retrospective al catalogo

Nella stessa tabella, aggiungi nella sezione Cross-cutting (dopo siae-verification):

```markdown
| siae-retrospective | fine sessione, lezioni apprese, cosa ho imparato, retrospettiva, salva per la prossima volta, /forge-retro,... | Rigid | Cross-cutting |
```

## Step 3 — Aggiungi alla Skill Dependency Map

Nella sezione `## Skill Dependency Map`, aggiungi i nodi nel grafo graphviz:

```dot
    blind_review [label="siae-blind-review", fillcolor="#f8d7da"];
    retrospective [label="siae-retrospective", fillcolor="#f8d7da"];
```

Aggiungi le connessioni:
```dot
    verification -> blind_review [label="spec audit"];
    blind_review -> finishing [label="PASS"];
    // retrospective e' invocata da stop-gate, non ha dipendenze nel grafo
```

## Step 4 — Aggiungi alla disambiguazione

Nella sezione `**Disambiguazione skill (quando piu' skill matchano):**`, aggiungi:

```markdown
- Query su blind review, review cieca, audit spec, spec vs codice → `siae-blind-review` (NON code-reviewer)
- Query su retrospettiva, lezioni apprese, cosa ho imparato, fine sessione → `siae-retrospective` (NON brainstorming)
```

## Step 5 — Verifica

```bash
grep -c "siae-blind-review" skills/using-devforge/SKILL.md
grep -c "siae-retrospective" skills/using-devforge/SKILL.md
```
Output atteso: almeno 2 occorrenze ciascuna (catalogo + dependency map o disambiguazione).

## Step 6 — Commit

```bash
git add skills/using-devforge/SKILL.md
git commit -m "feat(skills): add blind-review and retrospective to using-devforge catalog"
```
