# Superpowers Quick Wins — Piano Implementativo

> **Per Claude:** Implementa i task in ordine. Sono indipendenti.

**Goal:** Aggiungere hook sharing nei worktree e placeholder scan gate in writing-plans
**Stack:** Markdown skill files
**SP:** 2 SP-Umano / 1 SP-Augmented
**Design doc:** `docs/plans/2026-03-29-superpowers-quick-wins-design.md`

---

## Indice Task

| # | Task | Stato |
|---|------|-------|
| 1 | Aggiungere Step 3b "Sync DevForge Config" in siae-git-worktrees | [PENDING] |
| 2 | Aggiungere Step 3b "Placeholder Scan" in siae-writing-plans | [PENDING] |

## Dipendenze

- Task 1 e Task 2 sono indipendenti

---

## Task 1 — Step 3b "Sync DevForge Config" in siae-git-worktrees [PENDING]

**File:** `skills/siae-git-worktrees/SKILL.md`
**Posizione:** dopo Step 3 "Auto-detect Setup" (riga ~128, dopo il blocco `# IaC — nessun setup necessario`), prima di Step 4 "Baseline Test Check"

**Azione:** Inserire il seguente blocco Markdown dopo la riga `# IaC — nessun setup necessario` e la tripla backtick di chiusura:

```markdown
### Step 3b — Sync DevForge Config

Dopo aver installato le dipendenze, sincronizza la configurazione DevForge
nel worktree tramite symlink. Senza questo step, l'agent nel worktree
non ha hook, settings, ne' CLAUDE.md.

```bash
cd .worktrees/{branch-name}

# Symlink .claude/ dal repo principale (hook, settings, CLAUDE.md)
MAIN_REPO=$(git worktree list | head -1 | awk '{print $1}')
[ -d "$MAIN_REPO/.claude" ] && ln -sfn "$MAIN_REPO/.claude" .claude

# Symlink CLAUDE.md root se esiste
[ -f "$MAIN_REPO/CLAUDE.md" ] && ln -sfn "$MAIN_REPO/CLAUDE.md" CLAUDE.md
```

**Se `.claude/` non esiste nel repo principale:** skip silenzioso — il repo
non usa DevForge hooks.
```

**Verifica:** leggere il file e confermare che Step 3b appare tra Step 3 e Step 4.

---

## Task 2 — Step 3b "Placeholder Scan" in siae-writing-plans [PENDING]

**File:** `skills/siae-writing-plans/SKILL.md`
**Posizione:** dopo Step 3 "Scrivi il Piano Bite-Sized" (dopo il blocco che descrive `task-NN-<nome>.md`), prima di Step 4 "Salva il Piano"

**Azione:** Inserire il seguente blocco Markdown prima di `### Step 4 — Salva il Piano`:

```markdown
### Step 3b — Placeholder Scan (Gate Obbligatorio)

Prima di salvare il piano, esegui un scan completo per placeholder e
riferimenti vaghi. Un piano con placeholder e' un piano che fallira'.

**Pattern vietati — il piano NON e' pronto se contiene:**

| Pattern | Esempio |
|---------|---------|
| `TBD` | "Formato TBD" |
| `TODO` | "TODO: definire schema" |
| `da definire` | "Endpoint da definire" |
| `da decidere` | "Approccio da decidere" |
| `similar to` / `simile a` | "Simile al Task 2" |
| `come sopra` / `vedi sopra` | "Come sopra ma per utenti" |
| `da completare` | "Implementazione da completare" |
| `[...]` / `...` in codice | `function validate(...) { ... }` |
| Riferimenti circolari | "Vedi Task N" senza contenuto inline |

**Procedura:**
1. Scansiona ogni `task-NN-*.md` per i pattern sopra
2. Se trovi match → lista i match con file e riga
3. Risolvi OGNI placeholder con contenuto concreto (path, codice, comando)
4. Ri-scansiona fino a zero match
5. Solo allora procedi a Step 4
6. Emetti checkpoint:

```
[WRITING-PLANS:PLACEHOLDER-SCAN] Scan completato
  File scansionati: {N}
  Pattern trovati: {0 = PASS / N = FAIL}
  Iterazioni: {N}
```

Un piano che passa questo gate ha zero ambiguita' per il subagent.
```

**Verifica:** leggere il file e confermare che Step 3b appare tra Step 3 e Step 4.
