# Skill Visual Completeness — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Aggiungere Legge di Ferro, Risk Table e Anti-Razionalizzazione a 12 skill mancanti.
**Architettura:** 1 subagent per skill (12 in parallelo), ogni agente legge la skill, scrive
contenuto contestuale al dominio, verifica con grep, committa.
**Stack:** Markdown, DevForge Visual Design System
**SP:** 5

**Skill di riferimento per formato:**
- `skills/siae-debugging/SKILL.md` — Anti-Razi + Risk Table completi
- `skills/siae-subagent-development/SKILL.md` — Legge di Ferro + tutte le tabelle
- `skills/siae-writing-skills/SKILL.md` — Risk Table + Anti-Razi per Flexible

---

## ISTRUZIONI PER OGNI SUBAGENT

Ogni subagent deve:
1. Leggere il SKILL.md della skill assegnata
2. Capire il dominio e il processo che la skill gestisce
3. Scrivere contenuto **contestuale** — non generico
4. Posizionare gli elementi nel punto corretto del file
5. Verificare con grep che gli elementi siano presenti
6. Committare con `git commit -m "feat(skill): aggiunge visual completeness a {nome-skill}"`

### Posizione degli elementi nel file:
- **Legge di Ferro**: subito dopo il banner ASCII (prima del "Quando si Applica" o del primo step)
- **Tabella Anti-Razionalizzazione**: prima della sezione "Classificazione Rischio Operazioni" (o prima dei Vincoli se Risk Table non c'è)
- **Classificazione Rischio Operazioni**: subito prima dei Vincoli Non Negoziabili (o alla fine del file se non ci sono Vincoli)

### Formato Legge di Ferro (solo Rigid):
```
## LA LEGGE DI FERRO

```
[PRINCIPIO IN MAIUSCOLO — 1 RIGA — SPECIFICO PER IL DOMINIO DELLA SKILL]
```
```

### Formato Risk Table:
```
## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| [operazione 1 della skill] | 🟢 Sicuro | No |
| [operazione 2 della skill] | 🟡 Medio | Si |
```

### Formato Anti-Razionalizzazione:
```
## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "[scusa tipica nel contesto della skill]" | [risposta diretta] |
```
(minimo 6 righe, massimo 10 — specifiche per il dominio)

---

### Task 1: siae-brainstorming — Legge di Ferro + Risk Table + Anti-Razi

**File:** `skills/siae-brainstorming/SKILL.md`
**Gap:** tutti e 3 gli elementi mancanti

**Legge di Ferro suggerita:**
`NESSUNA IMPLEMENTAZIONE SENZA DESIGN APPROVATO DALL'UTENTE`

**Risk Table** (operazioni tipiche del brainstorming):
- Esplorazione contesto/JIRA → 🟢
- Domande chiarificatrici → 🟢
- Proposta approcci → 🟢
- Presentazione design per sezioni → 🟢
- Scrittura design doc → 🟢
- Git commit design doc → 🟡 Si
- Creazione ticket JIRA → 🔴 Si

**Anti-Razi** (razionalizzazioni tipiche per saltare il brainstorming):
- "È semplice, so già cosa fare"
- "Il design lo faccio nella testa"
- "Non serve JIRA per questo"
- "Iniziamo a codare e vediamo"
- "Ho già fatto qualcosa di simile"
- "Il design blocca la velocità"

**Verifica:**
```bash
grep -c "LA LEGGE DI FERRO\|Classificazione Rischio\|Anti-Razionalizzazione" skills/siae-brainstorming/SKILL.md
wc -l skills/siae-brainstorming/SKILL.md
```
Output atteso: >= 3 | <= 300

---

### Task 2: siae-qa — Legge di Ferro + Risk Table

**File:** `skills/siae-qa/SKILL.md`
**Gap:** Legge di Ferro + Risk Table mancanti

**Legge di Ferro suggerita:**
`NESSUN CASO DI TEST SENZA CRITERIO DI ACCETTAZIONE VERIFICABILE`

**Risk Table** (operazioni tipiche del QA):
- Analisi requisiti/Acceptance Criteria → 🟢
- Scrittura test cases → 🟢
- Creazione test plan → 🟢
- Export Xray → 🟡 Si
- Esecuzione test su ambiente → 🟡 Si
- Apertura bug su JIRA → 🟡 Si

**Verifica:**
```bash
grep -c "LA LEGGE DI FERRO\|Classificazione Rischio" skills/siae-qa/SKILL.md
wc -l skills/siae-qa/SKILL.md
```
Output atteso: >= 2 | <= 400

---

### Task 3: siae-tdd — Risk Table

**File:** `skills/siae-tdd/SKILL.md`
**Gap:** solo Risk Table mancante

**Risk Table** (operazioni tipiche del TDD):
- Scrittura test fallente → 🟢
- Esecuzione test (RED) → 🟢
- Implementazione minimale → 🟢
- Esecuzione test (GREEN) → 🟢
- Refactor → 🟡 Si
- Git commit → 🟡 Si (da hook pre-commit)

**Verifica:**
```bash
grep -c "Classificazione Rischio" skills/siae-tdd/SKILL.md
wc -l skills/siae-tdd/SKILL.md
```
Output atteso: >= 1 | <= 400

---

### Task 4: siae-automation — Risk Table

**File:** `skills/siae-automation/SKILL.md`
**Gap:** solo Risk Table mancante

**Risk Table** (operazioni tipiche automation):
- Setup framework E2E → 🟢
- Scrittura test automatizzati → 🟢
- Esecuzione test E2E in locale → 🟡 Si
- Configurazione CI pipeline → 🟡 Si
- Push configurazione CI → 🔴 Si
- Report risultati → 🟢

**Verifica:**
```bash
grep -c "Classificazione Rischio" skills/siae-automation/SKILL.md
wc -l skills/siae-automation/SKILL.md
```
Output atteso: >= 1 | <= 400

---

### Task 5: siae-git-workflow — Legge di Ferro

**File:** `skills/siae-git-workflow/SKILL.md`
**Gap:** solo Legge di Ferro mancante

**Legge di Ferro suggerita:**
`NESSUN COMMIT SU MAIN DIRETTO — SEMPRE FEATURE BRANCH + PR + REVIEW`

**Verifica:**
```bash
grep -c "LA LEGGE DI FERRO" skills/siae-git-workflow/SKILL.md
wc -l skills/siae-git-workflow/SKILL.md
```
Output atteso: >= 1 | <= 400

---

### Task 6: siae-architecture — Risk Table + Anti-Razi

**File:** `skills/siae-architecture/SKILL.md`
**Gap:** Risk Table + Anti-Razi mancanti

**Risk Table** (operazioni architettura):
- Analisi requisiti non funzionali → 🟢
- Proposta pattern architetturale → 🟢
- Scrittura ADR → 🟢
- Presentazione HLD → 🟢
- Scelta tecnologie/librerie → 🟡 Si
- Pubblicazione ADR su Confluence → 🟡 Si

**Anti-Razi** (razionalizzazioni tipiche per saltare l'architettura):
- "Abbiamo già un pattern uguale altrove"
- "È solo un CRUD, non serve architettura"
- "Lo decidiamo durante l'implementazione"
- "Il team conosce già il sistema"
- "Aggiorniamo l'ADR dopo"
- "Non abbiamo tempo per HLD"

**Verifica:**
```bash
grep -c "Classificazione Rischio\|Anti-Razionalizzazione" skills/siae-architecture/SKILL.md
wc -l skills/siae-architecture/SKILL.md
```
Output atteso: >= 2 | <= 400

---

### Task 7: siae-code-standards — Anti-Razi

**File:** `skills/siae-code-standards/SKILL.md`
**Gap:** solo Anti-Razi mancante

**Anti-Razi** (razionalizzazioni per deviare dagli standard):
- "Questo naming è più chiaro per me"
- "I test rallentano la delivery"
- "Il logging lo aggiungo dopo"
- "Questa classe fa due cose ma è piccola"
- "Gli altri nel team capiscono lo stesso"
- "PascalCase o camelCase è lo stesso"
- "L'exception handler non serve qui"
- "Questo metodo ha 200 righe ma è leggibile"

**Verifica:**
```bash
grep -c "Anti-Razionalizzazione" skills/siae-code-standards/SKILL.md
wc -l skills/siae-code-standards/SKILL.md
```
Output atteso: >= 1 | <= 400

---

### Task 8: siae-codebase-map — Anti-Razi

**File:** `skills/siae-codebase-map/SKILL.md`
**Gap:** solo Anti-Razi mancante

**Anti-Razi** (razionalizzazioni per non mappare il codebase):
- "Conosco già il codice"
- "La mappa diventa subito stale"
- "Il README è sufficiente"
- "Non ho tempo per la documentazione"
- "Il team sa come è fatto"
- "Mappa solo i file che modifico"

**Verifica:**
```bash
grep -c "Anti-Razionalizzazione" skills/siae-codebase-map/SKILL.md
wc -l skills/siae-codebase-map/SKILL.md
```
Output atteso: >= 1 | <= 400

---

### Task 9: siae-data-engineering — Anti-Razi

**File:** `skills/siae-data-engineering/SKILL.md`
**Gap:** solo Anti-Razi mancante

**Anti-Razi** (razionalizzazioni per deviare dai pattern data engineering):
- "Il job funziona, non serve il Medallion"
- "I test sui Glue job sono lenti"
- "Lo schema lo valido a runtime"
- "La pipeline è semplice, non serve Step Functions"
- "Il checkpoint lo aggiungo se serve"
- "I log sono nel CloudWatch, non nel job"
- "La partizione non serve per questo volume"

**Verifica:**
```bash
grep -c "Anti-Razionalizzazione" skills/siae-data-engineering/SKILL.md
wc -l skills/siae-data-engineering/SKILL.md
```
Output atteso: >= 1 | <= 500

---

### Task 10: siae-documentation — Anti-Razi

**File:** `skills/siae-documentation/SKILL.md`
**Gap:** solo Anti-Razi mancante

**Anti-Razi** (razionalizzazioni per non documentare):
- "Il codice è la documentazione"
- "Lo aggiorneremo dopo il rilascio"
- "Il team sa già come funziona"
- "L'HLD è eccessivo per questa feature"
- "Confluence è sempre stale"
- "I developer non leggono la doc"
- "OpenAPI si genera automaticamente"

**Verifica:**
```bash
grep -c "Anti-Razionalizzazione" skills/siae-documentation/SKILL.md
wc -l skills/siae-documentation/SKILL.md
```
Output atteso: >= 1 | <= 400

---

### Task 11: siae-frontend — Anti-Razi

**File:** `skills/siae-frontend/SKILL.md`
**Gap:** solo Anti-Razi mancante

**Anti-Razi** (razionalizzazioni per deviare dai pattern frontend SIAE):
- "Questo componente è solo per questa pagina"
- "I test Vitest rallentano il build"
- "Il CSS lo sistemo dopo"
- "Non serve il brand SIAE per questo prototipo"
- "Firebase config la metto nel codice"
- "L'error tracking lo aggiungo in produzione"
- "Vue 2 funziona ancora, non migro"

**Verifica:**
```bash
grep -c "Anti-Razionalizzazione" skills/siae-frontend/SKILL.md
wc -l skills/siae-frontend/SKILL.md
```
Output atteso: >= 1 | <= 400

---

### Task 12: siae-iac — Anti-Razi

**File:** `skills/siae-iac/SKILL.md`
**Gap:** solo Anti-Razi mancante

**Anti-Razi** (razionalizzazioni per deviare dai pattern IaC SIAE):
- "È solo un ambiente di test, non serve Terragrunt"
- "Il modulo è piccolo, metto tutto in main.tf"
- "Il remote state lo configuro dopo"
- "Non serve il lock del provider"
- "Le variabili le hardcodo per ora"
- "L'IAM policy la faccio admin per semplicità"
- "Il `terraform apply` lo faccio senza plan"
- "Encryption at rest non serve in dev"

**Verifica:**
```bash
grep -c "Anti-Razionalizzazione" skills/siae-iac/SKILL.md
wc -l skills/siae-iac/SKILL.md
```
Output atteso: >= 1 | <= 400

---

## Task 13: Commit Finale + Test Suite

Dopo tutti i task:

**Step 1: Test suite**
```bash
bash tests/run-all.sh 2>&1 | tail -10
```
Output atteso: PASS >= 39, FAIL: 0

**Step 2: Commit batch**
```bash
git add skills/*/SKILL.md
git commit -m "feat(skills): aggiunge visual completeness (Legge di Ferro + Risk Table + Anti-Razi) a 12 skill"
```

**Step 3: Push**
```bash
git push origin feature/service-logic-map-skill
```
