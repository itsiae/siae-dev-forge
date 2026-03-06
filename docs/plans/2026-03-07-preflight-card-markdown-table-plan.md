# Pre-Flight Card Markdown Table — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Sostituire tutte le pre-flight card bash (`generate-card.py`) con markdown table inline
**Architettura:** Modifica testuale di devforge-visual.md + 16 skill SKILL.md, sostituzione meccanica pattern bash → markdown table
**Stack:** Markdown, DevForge skill system
**SP:** 5

---

## Regola di Trasformazione — LEGGI PRIMA DI TUTTO

Ogni occorrenza di `generate-card.py` segue questo pattern nel file:

```
[riga opzionale: "🔴 ALTO — Pre-flight card obbligatoria"]
[riga opzionale: "Genera la pre-flight card con `design-system/generate-card.py`:"]

```bash
echo '{
  "level": "ALTO",
  "skill": "nome-skill",
  "context": [
    {"emoji": "🌿", "label": "Branch", "value": "feature/{JIRA-ID}"},
    ...
  ],
  "actions": [
    {"emoji": "🚀", "label": "Push branch", "path": "origin/feature/{JIRA-ID}"}
  ],
  "reason": "motivazione",
  "ifno": "alternativa"
}' | python3 design-system/generate-card.py
```
```

**Sostituire con** (estraendo i campi dal JSON):

```markdown
| LEVEL_EMOJI LEVEL (subtitle) — 🔨 DevForge · skill-name |
|:---|
| [⚠️ WARNING — solo se ALTO o CRITICO] |
| [CONTEXT_EMOJI Label: `valore`] |        <- una riga per ogni context item
| N. ACTION_EMOJI Azione: descrizione |    <- una riga per ogni action
| 📂 `path` |                              <- una riga 📂 per ogni action
| 💡 Perche': motivazione |
| 🚫 Se NO: alternativa |
```

**Mapping livello → subtitle + warning:**

| level JSON | LEVEL_EMOJI | subtitle | warning line |
|-----------|-------------|----------|-------------|
| MEDIO | 🟡 | reversibile | nessuna |
| ALTO | 🔴 | difficile da annullare | `⚠️ OPERAZIONE DIFFICILE DA ANNULLARE` |
| CRITICO | 🚨 | irreversibile | `⚠️ AZIONE IRREVERSIBILE — CONFERMA RICHIESTA` |

**Regole valori:**
- Valori tecnici (branch, path, ISRC, ARN, S3 URI, env): racchiudere in backtick
- Valori descrittivi (motivazioni, label generiche): testo plain
- Rimuovere anche le righe di contesto sopra il bash block ("🔴 ALTO — ..." e "Genera la pre-flight card con...")

---

## Task 1: Aggiorna devforge-visual.md

**File coinvolti:**
- Modifica: `design-system/devforge-visual.md`

**Step 1: Leggi il file**
```bash
cat design-system/devforge-visual.md
```

**Step 2: Sostituisci la sezione "Come generare una card" (sezione 0.3)**

Trova il blocco:
```
### Come generare una card

<EXTREMELY-IMPORTANT>
NON costruire le card a mano. Usa SEMPRE lo script `design-system/generate-card.py`.
...
</EXTREMELY-IMPORTANT>

**Uso da Bash (JSON su stdin):**
...
```bash
echo '{...}' | python3 design-system/generate-card.py
```

**Flags:**
...
```

Sostituisci con:
```markdown
### Come generare una card

<EXTREMELY-IMPORTANT>
Costruisci la card come MARKDOWN TABLE direttamente nella risposta testuale.
NON usare Bash. NON usare generate-card.py. Il renderer di Claude Code gestisce
automaticamente l'allineamento.
</EXTREMELY-IMPORTANT>

**Template:**

\`\`\`markdown
| LEVEL_EMOJI LEVEL (subtitle) — 🔨 DevForge · skill-name |
|:---|
| [⚠️ WARNING_LINE — solo per ALTO e CRITICO] |
| CONTEXT_EMOJI Label: `valore` |
| N. ACTION_EMOJI Azione: descrizione |
| 📂 `path/al/file` |
| 💡 Perche': motivazione |
| 🚫 Se NO: alternativa |
\`\`\`

**Mapping livello:**

| Livello | Emoji | Subtitle | Warning line |
|---------|-------|----------|-------------|
| MEDIO | 🟡 | reversibile | — |
| ALTO | 🔴 | difficile da annullare | `⚠️ OPERAZIONE DIFFICILE DA ANNULLARE` |
| CRITICO | 🚨 | irreversibile | `⚠️ AZIONE IRREVERSIBILE — CONFERMA RICHIESTA` |

**Regole:**
- Valori tecnici (branch, path, ARN, URI): in backtick
- Una riga `📂 path` per ogni file di ogni azione
- La stessa azione su piu' file: ripetere le righe 📂
- `generate-card.py` rimane nel repo per uso manuale ma non e' richiesto dalle skill
```

**Step 3: Aggiorna anche la tabella "Trigger obbligatori" (sezione al fondo)**

Verifica che menzioni ancora che la card e' obbligatoria per rischio >= MEDIO,
rimuovi qualsiasi riferimento a generate-card.py come strumento obbligatorio.

**Step 4: Commit**
```bash
git add design-system/devforge-visual.md
git commit -m "feat(design-system): sostituisci generate-card.py con markdown table inline"
```

---

## Task 2: siae-git-workflow + siae-git-worktrees

**File coinvolti:**
- Modifica: `skills/siae-git-workflow/SKILL.md` (1 occorrenza)
- Modifica: `skills/siae-git-worktrees/SKILL.md` (2 occorrenze)

**Step 1: Leggi entrambi i file**
```bash
cat skills/siae-git-workflow/SKILL.md
cat skills/siae-git-worktrees/SKILL.md
```

**Step 2: Applica la regola di trasformazione** a ogni occorrenza di `generate-card.py` trovata.

Per ogni blocco bash trovato:
1. Estrai level, skill, context items, actions, reason, ifno dal JSON
2. Costruisci la markdown table corrispondente
3. Sostituisci il blocco bash (incluse le righe di contesto sopra: "🔴 ALTO — ..." e "Genera la pre-flight card con...")
4. Mantieni tutto il contenuto DOPO il blocco bash invariato

**Step 3: Verifica** che non rimanga nessun `generate-card.py` nei file:
```bash
grep "generate-card" skills/siae-git-workflow/SKILL.md skills/siae-git-worktrees/SKILL.md
```
Output atteso: nessun output

**Step 4: Commit**
```bash
git add skills/siae-git-workflow/SKILL.md skills/siae-git-worktrees/SKILL.md
git commit -m "feat(skills): migra pre-flight card a markdown table in siae-git-workflow e siae-git-worktrees"
```

---

## Task 3: siae-finishing-branch + siae-requesting-review + siae-receiving-review

**File coinvolti:**
- Modifica: `skills/siae-finishing-branch/SKILL.md` (1 occorrenza)
- Modifica: `skills/siae-requesting-review/SKILL.md` (1 occorrenza)
- Modifica: `skills/siae-receiving-review/SKILL.md` (1 occorrenza)

**Step 1: Leggi i file**
```bash
cat skills/siae-finishing-branch/SKILL.md
cat skills/siae-requesting-review/SKILL.md
cat skills/siae-receiving-review/SKILL.md
```

**Step 2: Applica la regola di trasformazione** a ogni occorrenza.

**Step 3: Verifica**
```bash
grep "generate-card" skills/siae-finishing-branch/SKILL.md skills/siae-requesting-review/SKILL.md skills/siae-receiving-review/SKILL.md
```
Output atteso: nessun output

**Step 4: Commit**
```bash
git add skills/siae-finishing-branch/SKILL.md skills/siae-requesting-review/SKILL.md skills/siae-receiving-review/SKILL.md
git commit -m "feat(skills): migra pre-flight card a markdown table in siae-finishing-branch, siae-requesting-review, siae-receiving-review"
```

---

## Task 4: siae-debugging + siae-verification

**File coinvolti:**
- Modifica: `skills/siae-debugging/SKILL.md` (1 occorrenza)
- Modifica: `skills/siae-verification/SKILL.md` (1 occorrenza)

**Step 1: Leggi i file**
```bash
cat skills/siae-debugging/SKILL.md
cat skills/siae-verification/SKILL.md
```

**Step 2: Applica la regola di trasformazione.**

Nota per siae-debugging: la card e' in "Fase 4: Implementation" con level MEDIO.
Il JSON ha: level MEDIO, skill siae-debugging, context con root cause e ipotesi,
action con scrivi test + fix, reason e ifno.

**Step 3: Verifica**
```bash
grep "generate-card" skills/siae-debugging/SKILL.md skills/siae-verification/SKILL.md
```
Output atteso: nessun output

**Step 4: Aggiorna anche la tabella "Classificazione Rischio Operazioni"** in siae-debugging
per riflettere che la card ora si mostra inline (non piu' via Bash).

**Step 5: Commit**
```bash
git add skills/siae-debugging/SKILL.md skills/siae-verification/SKILL.md
git commit -m "feat(skills): migra pre-flight card a markdown table in siae-debugging e siae-verification"
```

---

## Task 5: siae-qa + siae-automation

**File coinvolti:**
- Modifica: `skills/siae-qa/SKILL.md` (1 occorrenza)
- Modifica: `skills/siae-automation/SKILL.md` (2 occorrenze)

**Step 1: Leggi i file**
```bash
cat skills/siae-qa/SKILL.md
cat skills/siae-automation/SKILL.md
```

**Step 2: Applica la regola di trasformazione** a tutte e 3 le occorrenze.

**Step 3: Verifica**
```bash
grep "generate-card" skills/siae-qa/SKILL.md skills/siae-automation/SKILL.md
```
Output atteso: nessun output

**Step 4: Commit**
```bash
git add skills/siae-qa/SKILL.md skills/siae-automation/SKILL.md
git commit -m "feat(skills): migra pre-flight card a markdown table in siae-qa e siae-automation"
```

---

## Task 6: siae-documentation + siae-codebase-map

**File coinvolti:**
- Modifica: `skills/siae-documentation/SKILL.md` (1 occorrenza)
- Modifica: `skills/siae-codebase-map/SKILL.md` (2 occorrenze)

**Step 1: Leggi i file**
```bash
cat skills/siae-documentation/SKILL.md
cat skills/siae-codebase-map/SKILL.md
```

**Step 2: Applica la regola di trasformazione** a tutte e 3 le occorrenze.

**Step 3: Verifica**
```bash
grep "generate-card" skills/siae-documentation/SKILL.md skills/siae-codebase-map/SKILL.md
```
Output atteso: nessun output

**Step 4: Commit**
```bash
git add skills/siae-documentation/SKILL.md skills/siae-codebase-map/SKILL.md
git commit -m "feat(skills): migra pre-flight card a markdown table in siae-documentation e siae-codebase-map"
```

---

## Task 7: siae-security + siae-iac

**File coinvolti:**
- Modifica: `skills/siae-security/SKILL.md` (2 occorrenze)
- Modifica: `skills/siae-iac/SKILL.md` (2 occorrenze)

**Step 1: Leggi i file**
```bash
cat skills/siae-security/SKILL.md
cat skills/siae-iac/SKILL.md
```

**Step 2: Applica la regola di trasformazione** a tutte e 4 le occorrenze.

Nota: siae-security e siae-iac hanno spesso card CRITICO con path AWS lunghi
(ARN, S3 URI). Racchiuderli sempre in backtick.

**Step 3: Verifica**
```bash
grep "generate-card" skills/siae-security/SKILL.md skills/siae-iac/SKILL.md
```
Output atteso: nessun output

**Step 4: Commit**
```bash
git add skills/siae-security/SKILL.md skills/siae-iac/SKILL.md
git commit -m "feat(skills): migra pre-flight card a markdown table in siae-security e siae-iac"
```

---

## Task 8: siae-data-engineering

**File coinvolti:**
- Modifica: `skills/siae-data-engineering/SKILL.md` (4 occorrenze)

**Step 1: Leggi il file**
```bash
cat skills/siae-data-engineering/SKILL.md
```

**Step 2: Applica la regola di trasformazione** a tutte e 4 le occorrenze.

**Step 3: Verifica**
```bash
grep "generate-card" skills/siae-data-engineering/SKILL.md
```
Output atteso: nessun output

**Step 4: Commit**
```bash
git add skills/siae-data-engineering/SKILL.md
git commit -m "feat(skills): migra pre-flight card a markdown table in siae-data-engineering"
```

---

## Task 9: siae-executing-plans + siae-parallel-agents + siae-writing-plans

**File coinvolti:**
- Modifica: `skills/siae-executing-plans/SKILL.md` (1 occorrenza)
- Modifica: `skills/siae-parallel-agents/SKILL.md` (2 occorrenze)
- Modifica: `skills/siae-writing-plans/SKILL.md` (1 occorrenza)

**Step 1: Leggi i file**
```bash
cat skills/siae-executing-plans/SKILL.md
cat skills/siae-parallel-agents/SKILL.md
cat skills/siae-writing-plans/SKILL.md
```

**Step 2: Applica la regola di trasformazione** a tutte e 4 le occorrenze.

**Step 3: Verifica**
```bash
grep "generate-card" skills/siae-executing-plans/SKILL.md skills/siae-parallel-agents/SKILL.md skills/siae-writing-plans/SKILL.md
```
Output atteso: nessun output

**Step 4: Commit**
```bash
git add skills/siae-executing-plans/SKILL.md skills/siae-parallel-agents/SKILL.md skills/siae-writing-plans/SKILL.md
git commit -m "feat(skills): migra pre-flight card a markdown table in siae-executing-plans, siae-parallel-agents, siae-writing-plans"
```

---

## Task 10: Verifica finale + version bump + release

**File coinvolti:**
- Verifica: tutti i SKILL.md
- Modifica: `.claude-plugin/marketplace.json`
- Modifica: `README.md` (se menziona generate-card.py)

**Step 1: Verifica globale — zero occorrenze rimanenti**
```bash
grep -r "generate-card" skills/
```
Output atteso: nessun output

**Step 2: Verifica che devforge-visual.md sia aggiornato**
```bash
grep "generate-card\|Usa SEMPRE lo script" design-system/devforge-visual.md
```
Output atteso: nessun output (o solo menzione come strumento opzionale)

**Step 3: Bump version a 1.4.0-mvp**

Leggi marketplace.json:
```bash
cat .claude-plugin/marketplace.json
```

Aggiorna `version` da `1.3.0-mvp` a `1.4.0-mvp`.

**Step 4: Commit version bump**
```bash
git add .claude-plugin/marketplace.json
git commit -m "chore(release): bump version a 1.4.0-mvp"
```

**Step 5: Tag**
```bash
git tag v1.4.0-mvp
```

**Step 6: Verifica tag**
```bash
git log --oneline -5
git tag | grep mvp
```
Output atteso: tag v1.4.0-mvp presente

---

## Checklist Accettazione

- [ ] `design-system/devforge-visual.md` aggiornato con template markdown table
- [ ] `grep -r "generate-card" skills/` → nessun output
- [ ] Ogni skill ha pre-flight card come markdown table con contenuto corretto
- [ ] MEDIO: header 🟡, no warning line
- [ ] ALTO: header 🔴, warning line ⚠️
- [ ] CRITICO: header 🚨, warning line ⚠️ con testo IRREVERSIBILE
- [ ] Valori tecnici in backtick
- [ ] Version bump a 1.4.0-mvp committato e taggato
