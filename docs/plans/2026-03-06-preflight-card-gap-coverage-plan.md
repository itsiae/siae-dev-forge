# Pre-Flight Card Gap Coverage — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` per implementare questo piano task per task.

**Goal:** Aggiungere 20 pre-flight card mancanti a 13 skill del plugin siae-devforge.
**Architettura:** Edit inline nei SKILL.md — blocco `generate-card.py` + aggiornamento tabella rischio. Pattern identico alle card esistenti.
**Stack:** Markdown (SKILL.md files), Python (generate-card.py per verifica)
**SP:** 5

**Nota:** Tutti i file da modificare sono in `skills/<skill-name>/SKILL.md` nella directory del plugin. Il path base del plugin è recuperabile con:
```bash
PLUGIN_ROOT=$(find ~/.claude/plugins/cache/siae-devforge -maxdepth 2 -name "skills" -type d | head -1 | xargs dirname)
```

**Convenzione per ogni task:**
- "Inserisci PRIMA di" = il nuovo blocco va immediatamente sopra la riga indicata
- "Inserisci DOPO" = il nuovo blocco va immediatamente sotto la riga indicata
- Ogni blocco card è preceduto da una riga vuota e seguito da una riga vuota
- Il blocco `EXTREMELY-IMPORTANT` va incluso solo la PRIMA volta che appare nella skill; se la skill lo ha già altrove, non duplicarlo

---

## Task 1: siae-git-worktrees — 2 card (Gap #1, #2)

**File:** `skills/siae-git-worktrees/SKILL.md`

**Step 1: Leggi il file corrente**

```bash
cat "$PLUGIN_ROOT/skills/siae-git-worktrees/SKILL.md" | head -5
```
Verifica che il file esista e sia la versione corrente.

**Step 2: Aggiungi card Gap #1 — `git worktree remove --force`**

Trova la riga:
```
# Forza rimozione (se ci sono file non committati)
git worktree remove --force .worktrees/{branch-name}
```

Inserisci PRIMA di `# Forza rimozione` il seguente blocco:

```markdown
**⚠️ Operazione rischiosa — mostra pre-flight card PRIMA di eseguire:**

​```bash
echo '{
  "level": "ALTO",
  "skill": "siae-git-worktrees",
  "context": [
    {"emoji": "📁", "label": "Worktree", "value": "<path worktree>"},
    {"emoji": "🌿", "label": "Branch", "value": "<branch-name>"}
  ],
  "actions": [
    {"emoji": "🗑️", "label": "Rimozione forzata worktree (file non committati persi)", "path": "<path worktree>"}
  ],
  "reason": "Worktree non rimovibile normalmente (file non committati presenti)",
  "ifno": "Il worktree resta attivo, commit o stash prima di rimuovere"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiungi card Gap #2 — rebase su branch condiviso**

Trova la sezione `## Integrazione con il Workflow SIAE`. Inserisci PRIMA di essa una nuova sezione:

```markdown
---

## Warning: Rebase su Branch Condivisi

🚨 CRITICO — Mostra pre-flight card OBBLIGATORIA prima di eseguire

Se stai per fare `git rebase` su un branch che altri developer usano, questa operazione riscrive la history e può corrompere il lavoro altrui.

<EXTREMELY-IMPORTANT>
NON costruire card a mano. Usa SEMPRE `design-system/generate-card.py`.
Vedi `design-system/devforge-visual.md` sezione 0.3 per il template a 4 zone.
</EXTREMELY-IMPORTANT>

​```bash
echo '{
  "level": "CRITICO",
  "skill": "siae-git-worktrees",
  "context": [
    {"emoji": "🌿", "label": "Branch", "value": "<branch-name>"},
    {"emoji": "🎯", "label": "Target rebase", "value": "<base-branch>"},
    {"emoji": "👥", "label": "Condiviso", "value": "Si — altri developer usano questo branch"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Rebase interattivo su branch condiviso (riscrive history)", "path": "<branch-name>"}
  ],
  "reason": "Rebase necessario per allineare al branch base",
  "ifno": "STOP — usa merge invece di rebase su branch condivisi"
}' | python3 design-system/generate-card.py
​```

**Regola:** Se il branch è condiviso (altri developer ci lavorano), preferisci SEMPRE `git merge` a `git rebase`. Il rebase è sicuro solo su branch personali.
```

**Step 4: Aggiorna tabella Classificazione Rischio**

Sostituisci la tabella attuale con (aggiungendo colonna Card):

```markdown
| Operazione | Rischio | Card |
|------------|---------|------|
| `git worktree list` | 🟢 Sicuro | No |
| `git worktree add` | 🟡 Medio | No |
| `git worktree remove` | 🟡 Medio | No |
| `git worktree remove --force` | 🔴 Alto | Si |
| `git rebase` su branch condiviso | 🚨 Critico | Si |
```

**Step 5: Verifica JSON card**

```bash
echo '{"level":"ALTO","skill":"siae-git-worktrees","context":[{"emoji":"📁","label":"Worktree","value":"test"}],"actions":[{"emoji":"🗑️","label":"Rimozione forzata","path":"test"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card renderizzata con bordo pesante rosso, nessun errore.

**Step 6: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-git-worktrees/SKILL.md"
git commit -m "feat(git-worktrees): add pre-flight cards for force remove and shared rebase"
```

---

## Task 2: siae-git-workflow — 1 card (Gap #3)

**File:** `skills/siae-git-workflow/SKILL.md`

**Step 1: Leggi il file e trova la sezione rollback**

Cerca la sezione che descrive il rollback tramite cancellazione tag (`git push origin :refs/tags/`).

**Step 2: Aggiungi card Gap #3 — rollback tag PRODUZIONE**

Inserisci PRIMA del comando `git push origin :refs/tags/` il blocco:

```markdown
**🚨 Operazione CRITICA — mostra pre-flight card OBBLIGATORIA:**

​```bash
echo '{
  "level": "CRITICO",
  "skill": "siae-git-workflow",
  "context": [
    {"emoji": "🏷️", "label": "Tag da eliminare", "value": "<tag-name>"},
    {"emoji": "🌍", "label": "Ambiente", "value": "PRODUZIONE"},
    {"emoji": "📝", "label": "Commit stabile", "value": "<commit-hash>"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Cancellazione tag remoto (trigga rollback deploy)", "path": "origin/refs/tags/<tag-name>"}
  ],
  "reason": "Rollback necessario per incident/bug critico in produzione",
  "ifno": "Il tag resta, nessun rollback — il deploy corrente rimane attivo"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiorna tabella Classificazione Rischio**

Aggiungi alla tabella esistente la riga:

```markdown
| `git push origin :refs/tags/*` (rollback) | 🚨 Critico | Si |
```

**Step 4: Verifica JSON card**

```bash
echo '{"level":"CRITICO","skill":"siae-git-workflow","context":[{"emoji":"🏷️","label":"Tag","value":"PROD-v1.0"}],"actions":[{"emoji":"⚠️","label":"Cancellazione tag","path":"origin/refs/tags/PROD"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo pesante rosso bold, nessun errore.

**Step 5: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-git-workflow/SKILL.md"
git commit -m "feat(git-workflow): add pre-flight card for production tag rollback"
```

---

## Task 3: siae-debugging — 1 card (Gap #4)

**File:** `skills/siae-debugging/SKILL.md`

**Step 1: Leggi il file e trova Fase 4**

Cerca `### Fase 4: Implementation`.

**Step 2: Aggiungi card Gap #4**

Inserisci DOPO la riga `### Fase 4: Implementation` e DOPO la riga `**Fixa la root cause, non il sintomo:**` il blocco:

```markdown
🟡 MEDIO — Mostra pre-flight card prima di applicare il fix

​```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-debugging",
  "context": [
    {"emoji": "🔑", "label": "Root cause", "value": "<descrizione root cause identificata>"},
    {"emoji": "📊", "label": "Ipotesi", "value": "Confermata in Fase 3"}
  ],
  "actions": [
    {"emoji": "🧪", "label": "Scrivi test di regressione + fix minimale", "path": "<file target>"}
  ],
  "reason": "Root cause confermata, fix minimale pronto",
  "ifno": "Nessun fix applicato, torna a Fase 3 per nuova ipotesi"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiungi sezione Classificazione Rischio**

La skill NON ha una tabella rischio. Aggiungi PRIMA di `## Vincoli Non Negoziabili`:

```markdown
## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura messaggi di errore / log | 🟢 Sicuro | No |
| Ricerca pattern nel repo | 🟢 Sicuro | No |
| `git log`, `git diff` | 🟢 Sicuro | No |
| Formula e test ipotesi (Fase 3) | 🟢 Sicuro | No |
| Implementazione fix (Fase 4) | 🟡 Medio | Si |
| Commit fix | 🟡 Medio | No (commit locale) |

---
```

**Step 4: Verifica JSON card**

```bash
echo '{"level":"MEDIO","skill":"siae-debugging","context":[{"emoji":"🔑","label":"Root cause","value":"NPE in line 42"}],"actions":[{"emoji":"🧪","label":"Test regressione","path":"src/test.java"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo doppio giallo, nessun errore.

**Step 5: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-debugging/SKILL.md"
git commit -m "feat(debugging): add pre-flight card for Phase 4 implementation"
```

---

## Task 4: siae-requesting-review — 1 card (Gap #5)

**File:** `skills/siae-requesting-review/SKILL.md`

**Step 1: Leggi il file e trova Step 2**

Cerca `### Step 2 — Apri la PR e Assegna il Reviewer`.

**Step 2: Aggiungi card Gap #5**

Inserisci DOPO la riga `Una volta che la PR esiste, assegna il reviewer corretto:` e PRIMA del blocco `gh pr edit`:

```markdown
🟡 MEDIO — Mostra pre-flight card prima di assegnare

​```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-requesting-review",
  "context": [
    {"emoji": "🌿", "label": "Branch", "value": "<branch-name>"},
    {"emoji": "🎯", "label": "Target", "value": "sviluppo"},
    {"emoji": "📝", "label": "Commit", "value": "<N> commit"}
  ],
  "actions": [
    {"emoji": "🚀", "label": "Assegnazione reviewer alla PR", "path": "PR #<number>"}
  ],
  "reason": "PR pronta, reviewer da assegnare",
  "ifno": "La PR resta senza reviewer assegnato"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiorna tabella Classificazione Rischio**

Aggiungi colonna Card alla tabella esistente:

```markdown
| Operazione | Livello | Card | Note |
|-----------|---------|------|------|
| Scrivere PR description | 🟢 Sicuro | No | Solo testo |
| Push branch | 🟡 Medio | No | Coperto da siae-finishing-branch |
| Creare PR su GitHub | 🟡 Medio | No | Coperto da siae-finishing-branch |
| Assegnare reviewer | 🟡 Medio | Si | Notifica visibile al reviewer |
```

**Step 4: Verifica JSON card**

```bash
echo '{"level":"MEDIO","skill":"siae-requesting-review","context":[{"emoji":"🌿","label":"Branch","value":"feat/test"}],"actions":[{"emoji":"🚀","label":"Assegnazione reviewer","path":"PR #42"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo doppio giallo, nessun errore.

**Step 5: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-requesting-review/SKILL.md"
git commit -m "feat(requesting-review): add pre-flight card for reviewer assignment"
```

---

## Task 5: siae-receiving-review — 1 card (Gap #6)

**File:** `skills/siae-receiving-review/SKILL.md`

**Step 1: Leggi il file e trova Step 3**

Cerca `### Step 3 — Pianifica e Implementa i Fix`. Trova la checklist `**Prima di richiedere il re-review:**`.

**Step 2: Aggiungi card Gap #6**

Inserisci DOPO la checklist `Prima di richiedere il re-review:` (dopo l'ultimo `- [ ]`) e PRIMA della sezione `---` successiva:

```markdown
**Quando i fix sono pronti e la checklist sopra è completa, mostra la pre-flight card PRIMA di pushare:**

🔴 ALTO — Mostra pre-flight card prima di push

​```bash
echo '{
  "level": "ALTO",
  "skill": "siae-receiving-review",
  "context": [
    {"emoji": "🌿", "label": "Branch", "value": "<branch-name>"},
    {"emoji": "📝", "label": "Fix applicati", "value": "<N> REQUIRED, <M> SUGGESTION"},
    {"emoji": "🧪", "label": "Test suite", "value": "<risultato test>"}
  ],
  "actions": [
    {"emoji": "🚀", "label": "Push fix al branch della PR", "path": "origin/<branch-name>"}
  ],
  "reason": "Fix review completati, test verdi, pronto per re-review",
  "ifno": "I fix restano locali, il reviewer non vede le modifiche"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiorna tabella Classificazione Rischio**

Aggiungi colonna Card:

```markdown
| Operazione | Livello | Card | Note |
|-----------|---------|------|------|
| Lettura commenti | 🟢 Sicuro | No | Solo lettura |
| Categorizzazione | 🟢 Sicuro | No | Solo analisi |
| Fix codice | 🟡 Medio | No | Coperto da siae-tdd |
| Push aggiornamento branch | 🔴 Alto | Si | Pre-flight: test verdi |
| Risposta ai commenti | 🟢 Sicuro | No | Comunicazione asincrona |
```

**Step 4: Verifica JSON card**

```bash
echo '{"level":"ALTO","skill":"siae-receiving-review","context":[{"emoji":"🌿","label":"Branch","value":"feat/test"}],"actions":[{"emoji":"🚀","label":"Push fix","path":"origin/feat/test"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo pesante rosso, nessun errore.

**Step 5: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-receiving-review/SKILL.md"
git commit -m "feat(receiving-review): add pre-flight card for post-fix push"
```

---

## Task 6: siae-verification — 1 card (Gap #7)

**File:** `skills/siae-verification/SKILL.md`

**Step 1: Leggi il file e trova Step 2 — ESEGUI**

Cerca `### Step 2 — ESEGUI`.

**Step 2: Aggiungi card Gap #7**

Inserisci DOPO `### Step 2 — ESEGUI` e PRIMA di `Lancia i comandi`:

```markdown
🟡 MEDIO — Mostra pre-flight card prima di eseguire la suite di verifica

​```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-verification",
  "context": [
    {"emoji": "🔧", "label": "Comandi", "value": "<lista comandi identificati in Step 1>"},
    {"emoji": "📁", "label": "Working dir", "value": "<directory>"}
  ],
  "actions": [
    {"emoji": "🧪", "label": "Esecuzione suite di verifica", "path": "<comandi>"}
  ],
  "reason": "Verifica necessaria prima di qualsiasi claim di completamento",
  "ifno": "Nessuna verifica eseguita — non puoi dichiarare completamento"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiorna tabella Classificazione Rischio**

Aggiungi colonna Card alla tabella esistente:

```markdown
| Operazione | Livello | Card |
|-----------|---------|------|
| Identificare comandi di verifica | 🟢 Sicuro | No |
| Eseguire test (`mvn test`, `npm test`, `pytest`, `vitest`) | 🟡 Medio | Si |
| Eseguire build/compilazione | 🟡 Medio | Si |
| Eseguire `terraform validate` / `terraform plan` | 🟡 Medio | Si |
| Eseguire lint/format | 🟡 Medio | Si |
| Leggere output | 🟢 Sicuro | No |
| Generare report verifica | 🟢 Sicuro | No |
```

**Step 4: Verifica JSON card**

```bash
echo '{"level":"MEDIO","skill":"siae-verification","context":[{"emoji":"🔧","label":"Comandi","value":"npm test"}],"actions":[{"emoji":"🧪","label":"Suite verifica","path":"npm test"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo doppio giallo, nessun errore.

**Step 5: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-verification/SKILL.md"
git commit -m "feat(verification): add pre-flight card for test/build execution"
```

---

## Task 7: siae-writing-plans — 1 card (Gap #8)

**File:** `skills/siae-writing-plans/SKILL.md`

**Step 1: Leggi il file e trova Step 4**

Cerca `### Step 4 — Salva il Piano`.

**Step 2: Aggiungi card Gap #8**

Inserisci PRIMA del blocco `git add docs/plans/` e DOPO `Committa il file piano:`:

```markdown
🟡 MEDIO — Mostra pre-flight card prima del commit

​```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-writing-plans",
  "context": [
    {"emoji": "📋", "label": "Piano", "value": "<filename>.md"},
    {"emoji": "🔢", "label": "Task", "value": "<N> task definiti"}
  ],
  "actions": [
    {"emoji": "📌", "label": "Commit piano implementativo", "path": "docs/plans/<filename>.md"}
  ],
  "reason": "Piano validato, pronto per commit",
  "ifno": "Il piano resta non committato"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiorna tabella Classificazione Rischio**

```markdown
| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura design doc | 🟢 Sicuro | No |
| Scrittura piano su file | 🟢 Sicuro | No |
| Git commit piano | 🟡 Medio | Si |
| Execution handoff → subagent | 🟡 Medio | Si (in siae-subagent-development) |
```

**Step 4: Verifica JSON card**

```bash
echo '{"level":"MEDIO","skill":"siae-writing-plans","context":[{"emoji":"📋","label":"Piano","value":"plan.md"}],"actions":[{"emoji":"📌","label":"Commit piano","path":"docs/plans/plan.md"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo doppio giallo, nessun errore.

**Step 5: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-writing-plans/SKILL.md"
git commit -m "feat(writing-plans): add pre-flight card for plan commit"
```

---

## Task 8: siae-executing-plans — 1 card (Gap #9)

**File:** `skills/siae-executing-plans/SKILL.md`

**Step 1: Leggi il file e trova Step 2**

Cerca `### Step 2 — Esegui Batch`.

**Step 2: Aggiungi card Gap #9**

Inserisci DOPO `🟡 MEDIO — Pre-flight prima di ogni task con modifica file` e PRIMA di `Per ogni task nel batch:`:

```markdown
​```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-executing-plans",
  "context": [
    {"emoji": "📋", "label": "Piano", "value": "<filename>.md"},
    {"emoji": "🔢", "label": "Batch", "value": "Task <N>-<M> di <totale>"}
  ],
  "actions": [
    {"emoji": "✏️", "label": "Implementazione batch con TDD", "path": "<file coinvolti>"}
  ],
  "reason": "Batch pronto, piano validato",
  "ifno": "Il batch non viene eseguito, attende feedback"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiorna tabella Classificazione Rischio**

```markdown
| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura e revisione piano | 🟢 Sicuro | No |
| Implementazione task (scrittura file) | 🟡 Medio | Si |
| Esecuzione verifica (test, build) | 🟡 Medio | Si |
| Git commit post-task | 🟡 Medio | No (commit locale) |
| Report batch e attesa feedback | 🟢 Sicuro | No |
```

**Step 4: Verifica JSON card**

```bash
echo '{"level":"MEDIO","skill":"siae-executing-plans","context":[{"emoji":"📋","label":"Piano","value":"plan.md"}],"actions":[{"emoji":"✏️","label":"Batch TDD","path":"src/"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo doppio giallo, nessun errore.

**Step 5: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-executing-plans/SKILL.md"
git commit -m "feat(executing-plans): add pre-flight card for batch execution"
```

---

## Task 9: siae-parallel-agents — 2 card (Gap #10, #11)

**File:** `skills/siae-parallel-agents/SKILL.md`

**Step 1: Leggi il file e trova Step 3 e Step 4**

Cerca `### Step 3 — Dispatch` e `### Step 4 — Review e Integrazione`.

**Step 2: Aggiungi card Gap #10 — Dispatch**

Inserisci DOPO `### Step 3 — Dispatch` e PRIMA di `Usa il tool Agent`:

```markdown
🟡 MEDIO — Mostra pre-flight card prima del dispatch

​```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-parallel-agents",
  "context": [
    {"emoji": "🤖", "label": "Agenti", "value": "<N> agenti paralleli"},
    {"emoji": "🔢", "label": "Domini", "value": "<lista domini>"}
  ],
  "actions": [
    {"emoji": "⚡", "label": "Dispatch agenti in parallelo", "path": "<scope per agente>"}
  ],
  "reason": "Task indipendenti confermati, nessuno stato condiviso",
  "ifno": "Dispatch annullato, esecuzione sequenziale"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiungi card Gap #11 — Integrazione**

Inserisci DOPO `### Step 4 — Review e Integrazione` e PRIMA di `Dopo che tutti gli agenti completano:`:

```markdown
🔴 ALTO — Mostra pre-flight card prima di integrare

​```bash
echo '{
  "level": "ALTO",
  "skill": "siae-parallel-agents",
  "context": [
    {"emoji": "🤖", "label": "Agenti completati", "value": "<N>/<N>"},
    {"emoji": "📁", "label": "File modificati", "value": "<lista file>"}
  ],
  "actions": [
    {"emoji": "🔀", "label": "Integrazione output agenti + risoluzione conflitti", "path": "<file coinvolti>"}
  ],
  "reason": "Tutti gli agenti completati, integrazione necessaria",
  "ifno": "Output agenti non integrati, verifiche manuali necessarie"
}' | python3 design-system/generate-card.py
​```
```

**Step 4: Aggiorna tabella Classificazione Rischio**

```markdown
| Operazione | Rischio | Card |
|------------|---------|------|
| Analisi dipendenze tra task | 🟢 Sicuro | No |
| Dispatch agente singolo | 🟡 Medio | Si |
| Dispatch agenti multipli in parallelo | 🟡 Medio | Si |
| Integrazione output (risoluzione conflitti) | 🔴 Alto | Si |
| Suite test completa post-integrazione | 🟡 Medio | No (coperta da siae-verification) |
```

**Step 5: Verifica JSON card**

```bash
echo '{"level":"ALTO","skill":"siae-parallel-agents","context":[{"emoji":"🤖","label":"Agenti","value":"3/3"}],"actions":[{"emoji":"🔀","label":"Integrazione","path":"src/"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo pesante rosso, nessun errore.

**Step 6: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-parallel-agents/SKILL.md"
git commit -m "feat(parallel-agents): add pre-flight cards for dispatch and integration"
```

---

## Task 10: siae-codebase-map — 2 card (Gap #12, #13)

**File:** `skills/siae-codebase-map/SKILL.md`

**Step 1: Leggi il file e trova Step 6 e Step 7**

Cerca `## Step 6 — Scrivi` e `## Step 7 — Aggiorna`.

**Step 2: Aggiungi card Gap #12 — Scrittura CODEBASE_MAP.md**

Inserisci DOPO `## Step 6 — Scrivi \`docs/CODEBASE_MAP.md\`` e DOPO il blocco `date -u`, PRIMA di `Struttura del file:`:

```markdown
🟡 MEDIO — Mostra pre-flight card prima di scrivere

​```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-codebase-map",
  "context": [
    {"emoji": "📊", "label": "File analizzati", "value": "<N> file, <N> token"},
    {"emoji": "🤖", "label": "Subagent", "value": "<N> report sintetizzati"}
  ],
  "actions": [
    {"emoji": "✏️", "label": "Scrittura mappa codebase", "path": "docs/CODEBASE_MAP.md"}
  ],
  "reason": "Analisi completa, mappa pronta per scrittura",
  "ifno": "La mappa non viene scritta, analisi disponibile solo in chat"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiungi card Gap #13 — Aggiornamento CLAUDE.md**

Inserisci DOPO `## Step 7 — Aggiorna \`CLAUDE.md\`` e PRIMA di `Aggiungi o aggiorna la sezione`:

```markdown
🟡 MEDIO — Mostra pre-flight card prima di aggiornare

​```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-codebase-map",
  "context": [
    {"emoji": "📋", "label": "Sezione", "value": "Architettura Codebase"},
    {"emoji": "🔄", "label": "Tipo", "value": "<nuovo | aggiornamento>"}
  ],
  "actions": [
    {"emoji": "📝", "label": "Aggiornamento sezione architettura", "path": "CLAUDE.md"}
  ],
  "reason": "Mappa aggiornata, CLAUDE.md da sincronizzare",
  "ifno": "CLAUDE.md non aggiornato, future sessioni usano info vecchie"
}' | python3 design-system/generate-card.py
​```
```

**Step 4: Aggiungi sezione Classificazione Rischio**

La skill NON ha una tabella rischio. Aggiungi PRIMA di `## Permission Denied Handling`:

```markdown
---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Controllo mappa esistente | 🟢 Sicuro | No |
| Scansione codebase (scanner) | 🟢 Sicuro | No |
| Dispatch subagent Explore | 🟡 Medio | No |
| Scrittura `docs/CODEBASE_MAP.md` | 🟡 Medio | Si |
| Aggiornamento `CLAUDE.md` | 🟡 Medio | Si |
| Git commit | 🟡 Medio | No (commit locale) |
```

**Step 5: Verifica JSON card**

```bash
echo '{"level":"MEDIO","skill":"siae-codebase-map","context":[{"emoji":"📊","label":"File","value":"120 file"}],"actions":[{"emoji":"✏️","label":"Scrittura mappa","path":"docs/CODEBASE_MAP.md"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo doppio giallo, nessun errore.

**Step 6: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-codebase-map/SKILL.md"
git commit -m "feat(codebase-map): add pre-flight cards for map and CLAUDE.md writes"
```

---

## Task 11: siae-security — 1 card (Gap #14)

**File:** `skills/siae-security/SKILL.md`

**Step 1: Leggi il file**

Identifica la sezione più appropriata per aggiungere una sezione "Operazioni Attive" (rotazione credenziali). Cerca la fine delle checklist passive e prima dei vincoli.

**Step 2: Aggiungi nuova sezione con card Gap #14**

Inserisci PRIMA della sezione `## Vincoli` (o equivalente sezione finale):

```markdown
---

## Operazioni Attive — Rotazione Credenziali

Quando Claude gestisce direttamente la rotazione di credenziali o l'aggiornamento di secret:

🚨 CRITICO — Pre-flight card OBBLIGATORIA

<EXTREMELY-IMPORTANT>
NON costruire card a mano. Usa SEMPRE `design-system/generate-card.py`.
Vedi `design-system/devforge-visual.md` sezione 0.3 per il template a 4 zone.
</EXTREMELY-IMPORTANT>

​```bash
echo '{
  "level": "CRITICO",
  "skill": "siae-security",
  "context": [
    {"emoji": "🔐", "label": "Secret", "value": "<secret-name>"},
    {"emoji": "🌍", "label": "Ambiente", "value": "<dev|collaudo|produzione>"},
    {"emoji": "📦", "label": "Servizi dipendenti", "value": "<lista servizi>"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Rotazione credenziale / aggiornamento secret", "path": "aws secretsmanager update-secret --secret-id <id>"}
  ],
  "reason": "Secret scaduto/compromesso, rotazione necessaria",
  "ifno": "STOP — il secret resta invariato, valuta rischio manuale"
}' | python3 design-system/generate-card.py
​```

**Checklist pre-rotazione:**
- [ ] Backup del secret corrente
- [ ] Lista servizi dipendenti verificata
- [ ] Strategia di rollout definita (rolling restart / blue-green)
- [ ] Monitoring attivo per errori post-rotazione
```

**Step 3: Aggiungi/aggiorna tabella Classificazione Rischio**

Se la skill non ha una tabella, aggiungila. Se ce l'ha, aggiungi la riga:

```markdown
| Rotazione credenziali / Secrets Manager | 🚨 Critico | Si |
```

**Step 4: Verifica JSON card**

```bash
echo '{"level":"CRITICO","skill":"siae-security","context":[{"emoji":"🔐","label":"Secret","value":"db-password"}],"actions":[{"emoji":"⚠️","label":"Rotazione secret","path":"aws secretsmanager"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo pesante rosso bold, nessun errore.

**Step 5: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-security/SKILL.md"
git commit -m "feat(security): add pre-flight card for credentials rotation"
```

---

## Task 12: siae-iac — 2 card (Gap #15, #16)

**File:** `skills/siae-iac/SKILL.md`

**Step 1: Leggi il file**

Trova la sezione dove viene descritto `terraform apply` e le operazioni IAM.

**Step 2: Aggiungi card Gap #15 — terraform apply**

Trova il punto dove viene descritto o menzionato `terraform apply`. Inserisci PRIMA del comando:

```markdown
**🚨 Operazione CRITICA — pre-flight card OBBLIGATORIA prima di `terraform apply`:**

​```bash
echo '{
  "level": "CRITICO",
  "skill": "siae-iac",
  "context": [
    {"emoji": "🏗️", "label": "Ambiente", "value": "<dev|collaudo|produzione>"},
    {"emoji": "📋", "label": "Plan output", "value": "<N> to add, <N> to change, <N> to destroy"},
    {"emoji": "🎫", "label": "Ticket", "value": "<PROJ-NNN>"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Applicazione modifiche infrastruttura AWS", "path": "<modulo terraform>"}
  ],
  "reason": "Plan verificato, risorse da creare/modificare",
  "ifno": "STOP — nessuna modifica applicata all infrastruttura"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiungi card Gap #16 — Modifica IAM policy**

Trova la sezione dove si parla di IAM/security group. Inserisci il blocco:

```markdown
**🚨 Quando la risorsa modificata è IAM — pre-flight card CRITICO aggiuntiva:**

​```bash
echo '{
  "level": "CRITICO",
  "skill": "siae-iac",
  "context": [
    {"emoji": "🔐", "label": "Risorsa IAM", "value": "<role/policy name>"},
    {"emoji": "🌍", "label": "Ambiente", "value": "<ambiente>"},
    {"emoji": "📦", "label": "Servizi impattati", "value": "<lista servizi>"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Modifica policy IAM (impatta accesso risorse)", "path": "<file .tf>"}
  ],
  "reason": "Modifica necessaria per <motivazione>",
  "ifno": "STOP — policy invariata, accessi non modificati"
}' | python3 design-system/generate-card.py
​```
```

**Step 4: Aggiorna tabella Classificazione Rischio**

Aggiungi le righe mancanti:

```markdown
| `terraform apply` | 🚨 Critico | Si |
| Modifica IAM policy / security group | 🚨 Critico | Si |
```

**Step 5: Verifica JSON card**

```bash
echo '{"level":"CRITICO","skill":"siae-iac","context":[{"emoji":"🏗️","label":"Ambiente","value":"produzione"}],"actions":[{"emoji":"⚠️","label":"terraform apply","path":"modules/vpc"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo pesante rosso bold, nessun errore.

**Step 6: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-iac/SKILL.md"
git commit -m "feat(iac): add pre-flight cards for terraform apply and IAM modifications"
```

---

## Task 13: siae-data-engineering — 4 card (Gap #17, #18, #19, #20)

**File:** `skills/siae-data-engineering/SKILL.md`

**Step 1: Leggi il file**

Identifica le sezioni per: deploy Glue, operazioni S3, schema Glue Catalog, esecuzione manuale job.

**Step 2: Aggiungi card Gap #17 — Deploy Glue job**

Trova la sezione deploy. Inserisci PRIMA del comando terraform apply per Glue:

```markdown
**🚨 Operazione CRITICA — pre-flight card OBBLIGATORIA prima di deploy Glue job:**

​```bash
echo '{
  "level": "CRITICO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "🏗️", "label": "Ambiente", "value": "<ambiente>"},
    {"emoji": "📋", "label": "Job", "value": "<job-name>"},
    {"emoji": "🔄", "label": "Layer", "value": "<bronze|silver|gold>"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Deploy Glue job via terraform apply", "path": "<modulo terraform>"}
  ],
  "reason": "Job aggiornato, test locali verdi",
  "ifno": "STOP — job non deployato, versione precedente resta attiva"
}' | python3 design-system/generate-card.py
​```
```

**Step 3: Aggiungi card Gap #18 — Cancellazione dati S3**

Trova la sezione operazioni dati. Inserisci:

```markdown
**🚨 Operazione CRITICA — pre-flight card OBBLIGATORIA prima di cancellazione S3:**

​```bash
echo '{
  "level": "CRITICO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "🗄️", "label": "Bucket", "value": "<bucket-name>"},
    {"emoji": "📁", "label": "Prefix", "value": "<s3-prefix>"},
    {"emoji": "📊", "label": "File coinvolti", "value": "<N> file, <size>"}
  ],
  "actions": [
    {"emoji": "🗑️", "label": "Cancellazione dati S3 (irreversibile senza backup)", "path": "s3://<bucket>/<prefix>"}
  ],
  "reason": "Dati obsoleti/corrotti da rimuovere",
  "ifno": "STOP — dati preservati, nessuna cancellazione"
}' | python3 design-system/generate-card.py
​```
```

**Step 4: Aggiungi card Gap #19 — Modifica schema Glue Catalog**

```markdown
**🔴 Operazione ALTO rischio — pre-flight card prima di modifica schema:**

​```bash
echo '{
  "level": "ALTO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "🗄️", "label": "Database", "value": "<glue-database>"},
    {"emoji": "🔧", "label": "Tabella", "value": "<table-name>"},
    {"emoji": "📦", "label": "Downstream", "value": "<query/job dipendenti>"}
  ],
  "actions": [
    {"emoji": "🔧", "label": "Modifica schema Glue Catalog (backward compatibility)", "path": "<file schema/terraform>"}
  ],
  "reason": "Schema da aggiornare per nuovi requisiti dati",
  "ifno": "Schema invariato, downstream non impattati"
}' | python3 design-system/generate-card.py
​```
```

**Step 5: Aggiungi card Gap #20 — Esecuzione manuale Glue job**

```markdown
**🔴 Operazione ALTO rischio — pre-flight card prima di esecuzione manuale:**

​```bash
echo '{
  "level": "ALTO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "📋", "label": "Job", "value": "<job-name>"},
    {"emoji": "🏗️", "label": "Ambiente", "value": "<ambiente>"},
    {"emoji": "🔧", "label": "Parametri", "value": "<parametri input>"}
  ],
  "actions": [
    {"emoji": "🖥️", "label": "Esecuzione manuale Glue job (consuma risorse, scrive S3)", "path": "aws glue start-job-run --job-name <name>"}
  ],
  "reason": "Esecuzione manuale necessaria per <motivazione>",
  "ifno": "Job non eseguito, nessun dato processato"
}' | python3 design-system/generate-card.py
​```
```

**Step 6: Aggiorna tabella Classificazione Rischio**

Aggiungi le righe mancanti alla tabella:

```markdown
| Deploy Glue job (`terraform apply`) | 🚨 Critico | Si |
| Cancellazione dati S3 | 🚨 Critico | Si |
| Modifica schema Glue Catalog | 🔴 Alto | Si |
| `aws glue start-job-run` manuale | 🔴 Alto | Si |
```

**Step 7: Verifica JSON card**

```bash
echo '{"level":"CRITICO","skill":"siae-data-engineering","context":[{"emoji":"📋","label":"Job","value":"etl-bronze"}],"actions":[{"emoji":"⚠️","label":"Deploy Glue","path":"modules/glue"}],"reason":"test","ifno":"test"}' | python3 design-system/generate-card.py
```
Output atteso: card con bordo pesante rosso bold, nessun errore.

**Step 8: Commit**

```bash
git add "$PLUGIN_ROOT/skills/siae-data-engineering/SKILL.md"
git commit -m "feat(data-engineering): add pre-flight cards for deploy, S3 delete, schema change, manual run"
```
