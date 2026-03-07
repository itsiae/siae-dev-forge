# Logic Map L3 + Documentation + CSO — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Aggiungere L3 (business rules, Drools, @Query) al flusso `/forge-logic-build`,
aggiungere Step 5 POST-BUILD con siae-documentation automatica, e ottimizzare i CSO
dell'intera catena skill.
**Architettura:** Modifica localizzata a 3 file Markdown (SKILL.md, template, forge-logic-build.md)
+ ottimizzazione frontmatter description di 3 skill correlate. L3 segue il pattern
anti-context-overflow esistente: parent pre-fetcha snippet grep L3, agenti scrivono sezione L3.
**Stack:** Markdown, YAML, Bash snippet (inline nella skill)
**SP:** 3

---

### Task 1: Aggiorna logic-catalog-template.yaml con sezione L3

**File coinvolti:**
- Modifica: `skills/siae-service-logic-map/reference/logic-catalog-template.yaml`

**Step 1: Verifica stato attuale (test)**

```bash
grep -c "L3\|Business Rules" skills/siae-service-logic-map/reference/logic-catalog-template.yaml
```
Output atteso: `0` (sezione L3 non esiste ancora)

**Step 2: Aggiungi sezione L3 nel template**

Modifica `skills/siae-service-logic-map/reference/logic-catalog-template.yaml`.
Dopo il blocco `### L2 — Workflow Map` aggiungere:

```yaml
# ### L3 — Business Rules
#
# - **{nomeMetodo}():** regola={condizione di dominio}
#   [CONFIRMED] src/main/java/.../Service.java:{riga}
# - **Drools:** KieSession.fireAllRules() [CONFIRMED] Service.java:{riga}
#   → src/main/resources/rules/{file}.drl [CONFIRMED] tree scan
# - **{NomeRepository}:** @Query("...") [CONFIRMED] Repository.java:{riga}
# - **{NomeEntity}:** @OneToMany → {TargetEntity} [CONFIRMED] Entity.java:{riga}
#
# Se nessun pattern L3 trovato nel repo:
# - [UNVERIFIED] nessun pattern L3 trovato (no Drools, no @Query, no condizioni dominio)
```

Aggiornare anche l'header del file: `# Template scheda evidenza L1+L2+L3 per siae-service-logic-map`
e la versione: `# Versione: 3.0`

**Step 3: Verifica**

```bash
grep -c "L3\|Business Rules\|Drools" skills/siae-service-logic-map/reference/logic-catalog-template.yaml
```
Output atteso: `>= 3`

**Step 4: Commit**

```bash
git add skills/siae-service-logic-map/reference/logic-catalog-template.yaml
git commit -m "feat(skill): aggiunge sezione L3 business rules in logic-catalog-template"
```

---

### Task 2: Aggiorna SKILL.md Step 4b — Pre-fetch L3

**File coinvolti:**
- Modifica: `skills/siae-service-logic-map/SKILL.md` (sezione Step 4b, attuale riga ~240)

**Step 1: Verifica stato attuale**

```bash
grep -c "KieSession\|@Query\|L3\|Business Rules" skills/siae-service-logic-map/SKILL.md
```
Output atteso: `0`

**Step 2: Estendi blocco pre-fetch nel Step 4b**

Nel blocco `### 4b — Pre-fetch Dati per Cluster`, dopo il blocco bash esistente
(riga ~252, dopo il commento `# 3. openapi*.yaml`), aggiungere:

```markdown
# 4. Pre-fetch L3 — Business Rules (per ogni *Service.java)
#    Grep snippet: KieSession/Drools, condizioni dominio, @Query
gh api /repos/itsiae/{repo}/contents/{ServiceFile} --jq '.content' | base64 -d \
  | grep -n "KieSession\|fireAllRules\|@Query\|@NamedQuery\|if.*[Ss]tato\|if.*[Tt]ipo\|if.*[Cc]ategoria" -A3 -B1

# 5. Pre-fetch L3 — Repository e DRL files (se esistono)
#    File target: *Repository.java, *.drl
#    (identificati al punto 1 del tree scan)
gh api /repos/itsiae/{repo}/contents/{RepositoryFile} --jq '.content' | base64 -d \
  | grep -n "@Query\|@NamedQuery\|@EntityGraph" -A2
```

**Step 3: Verifica**

```bash
grep -c "KieSession\|fireAllRules\|@Query" skills/siae-service-logic-map/SKILL.md
```
Output atteso: `>= 2`

**Step 4: Verifica line count (sotto 500)**

```bash
wc -l skills/siae-service-logic-map/SKILL.md
```
Output atteso: `<= 500`

**Step 5: Commit**

```bash
git add skills/siae-service-logic-map/SKILL.md
git commit -m "feat(skill): pre-fetch L3 business rules in siae-service-logic-map Step 4b"
```

---

### Task 3: Aggiorna SKILL.md Step 4d — Istruzione L3 agli agenti

**File coinvolti:**
- Modifica: `skills/siae-service-logic-map/SKILL.md` (Step 4d, istruzione agenti)

**Step 1: Verifica stato attuale**

```bash
grep -n "ISTRUZIONE CRITICA\|L1+L2\|L1+L2+L3" skills/siae-service-logic-map/SKILL.md
```
Output atteso: riga con `L1+L2` senza menzione di `L3`

**Step 2: Aggiorna istruzione agenti in Step 4d**

Nel blocco `ISTRUZIONE CRITICA DA INCLUDERE IN OGNI AGENTE`, modificare:

```
# PRIMA (da sostituire):
1. Analizza i dati e compila la doc L1+L2 per ogni servizio del cluster
   (formato: reference/logic-catalog-template.yaml)

# DOPO:
1. Analizza i dati e compila la doc L1+L2+L3 per ogni servizio del cluster
   (formato: reference/logic-catalog-template.yaml v3.0)
   - L3 usa i snippet grep ricevuti inline: sezione "Business Rules"
   - Se snippet grep vuoto per un repo → [UNVERIFIED] nessun pattern L3 trovato
```

**Step 3: Aggiorna anche il formato output nella sezione "Formato Output per Cluster"**

Aggiungere la sezione L3 al template inline nello SKILL.md (dopo L2):

```markdown
### L3 — Business Rules
- {nomeMetodo}(): regola={condizione} [CONFIRMED] {Service.java:riga}
- Drools: KieSession.fireAllRules() [CONFIRMED] {Service.java:riga} → {rules.drl}
- {NomeRepository}: @Query("...") [CONFIRMED] {Repository.java:riga}
```

**Step 4: Verifica**

```bash
grep -c "L1+L2+L3\|L3 — Business Rules\|UNVERIFIED.*L3" skills/siae-service-logic-map/SKILL.md
```
Output atteso: `>= 2`

**Step 5: Commit**

```bash
git add skills/siae-service-logic-map/SKILL.md
git commit -m "feat(skill): aggiorna istruzione agenti e formato output per L3 in Step 4d"
```

---

### Task 4: Aggiunge Step 5 POST-BUILD siae-documentation (rinomina Step 5→6)

**File coinvolti:**
- Modifica: `skills/siae-service-logic-map/SKILL.md`

**Step 1: Verifica stato attuale**

```bash
grep -n "^## Step 5\|^## Step 6" skills/siae-service-logic-map/SKILL.md
```
Output atteso: solo `## Step 5 — QUERY` presente, no Step 6

**Step 2: Rinomina Step 5 QUERY in Step 6**

Sostituire `## Step 5 — QUERY (forge-logic-search)` con `## Step 6 — QUERY (forge-logic-search)`

**Step 3: Inserisce nuovo Step 5 POST-BUILD**

Tra la fine di Step 4f (Collect) e l'attuale Step 5 QUERY, inserire:

```markdown
## Step 5 — POST-BUILD: Documentazione Formale

Dopo COLLECT (Step 4f), eseguire automaticamente `siae-documentation`
sui cluster-*.md generati. Non proporre — eseguire.

```
REQUIRED SUB-SKILL: siae-documentation
Input: docs/logic-catalog/cluster-*.md + clusters.yaml + system-overview.md
Scope: documentazione tecnica del sistema (API guide per cluster, ADR, enriched overview)
```

Il sistema di documentazione riceve il catalogo L1+L2+L3 come input e produce
documentazione formale navigabile da altri developer del team.
```

**Step 4: Aggiorna Classificazione Rischio Operazioni**

Aggiungere alla tabella:
```
| POST-BUILD siae-documentation | 🟡 Medio | Si (nella skill siae-documentation) |
```

**Step 5: Verifica**

```bash
grep -n "^## Step 5\|^## Step 6\|POST-BUILD\|siae-documentation" skills/siae-service-logic-map/SKILL.md
```
Output atteso: `Step 5 POST-BUILD`, `Step 6 QUERY`, `siae-documentation` presenti

```bash
wc -l skills/siae-service-logic-map/SKILL.md
```
Output atteso: `<= 500`

**Step 6: Commit**

```bash
git add skills/siae-service-logic-map/SKILL.md
git commit -m "feat(skill): aggiunge Step 5 POST-BUILD siae-documentation in siae-service-logic-map"
```

---

### Task 5: Aggiorna forge-logic-build.md con L3 e Step 5

**File coinvolti:**
- Modifica: `commands/forge-logic-build.md`

**Step 1: Verifica stato attuale**

```bash
grep -c "L3\|POST-BUILD\|siae-documentation" commands/forge-logic-build.md
```
Output atteso: `0`

**Step 2: Aggiorna sezione Comportamento**

Nel blocco `## Comportamento`, aggiornare:
- Step 5 (PRE-FETCH): aggiungere `- Snippet L3 → grep KieSession, @Query, if condizioni dominio`
- Aggiungere dopo step 8 (COLLECT):
  ```
  9. **POST-BUILD** — Esegue siae-documentation sui cluster-*.md generati
  ```

**Step 3: Aggiorna sezione Output**

Aggiungere nota: `- Ogni cluster-{nome}.md include sezione L3 — Business Rules`

**Step 4: Verifica**

```bash
grep -c "L3\|POST-BUILD" commands/forge-logic-build.md
```
Output atteso: `>= 2`

**Step 5: Commit**

```bash
git add commands/forge-logic-build.md
git commit -m "docs(commands): aggiorna forge-logic-build con L3 e Step POST-BUILD"
```

---

### Task 6: Ottimizza CSO dell'intera catena skill

**File coinvolti:**
- Modifica: `skills/siae-service-logic-map/SKILL.md` (frontmatter description)
- Modifica: `skills/siae-microservices-map/SKILL.md` (frontmatter description)
- Modifica: `commands/forge-logic-build.md` (frontmatter description)

**Step 1: Leggi i CSO attuali**

```bash
head -8 skills/siae-service-logic-map/SKILL.md
head -8 skills/siae-microservices-map/SKILL.md
head -5 commands/forge-logic-build.md
```

**Step 2: Aggiorna CSO siae-service-logic-map**

Il CSO attuale descrive il workflow invece di trigger naturali.
Sostituire la `description` frontmatter con:

```yaml
description: >
  Use when profiling what microservices do: domain, entities, workflows, business rules,
  clusters. Trigger: "cosa fa {servizio}", "lanciamo su {pattern}", "analizziamo {sistema}",
  "mappa la logica", "build catalogo L1/L2/L3", "quali servizi gestiscono X",
  "regole business di", "Drools in", impact analysis, /forge-logic-build, /forge-logic-search.
```

**Step 3: Aggiorna CSO siae-microservices-map**

Leggere il CSO attuale e verificare che copra i trigger naturali:
- frasi come "mappa SPORT", "chi chiama chi", "dipendenze tra servizi"
- se mancano aggiungere: "come sono collegati i servizi", "grafo dipendenze {sistema}"

**Step 4: Aggiorna description forge-logic-build.md**

```yaml
description: >
  Costruisce il catalogo L1+L2+L3 (domain profile + workflow map + business rules)
  per cluster di microservizi. Flusso automatico: trova o genera SYSTEM_MAP.md,
  detecta cluster, pre-fetcha dati, dispatcha agenti per cluster, esegue siae-documentation.
  Prerequisiti: gh auth; pattern repo GitHub.
```

**Step 5: Verifica CSO**

```bash
grep -A5 "^description:" skills/siae-service-logic-map/SKILL.md
grep -A5 "^description:" skills/siae-microservices-map/SKILL.md
grep -A5 "^description:" commands/forge-logic-build.md
```

Verifica che ogni description contenga almeno 3 trigger naturali in italiano.

**Step 6: Commit**

```bash
git add skills/siae-service-logic-map/SKILL.md skills/siae-microservices-map/SKILL.md commands/forge-logic-build.md
git commit -m "feat(cso): ottimizza description trigger per siae-service-logic-map, siae-microservices-map, forge-logic-build"
```

---

### Task 7: Aggiorna tests suite per riflettere L3

**File coinvolti:**
- Modifica: `tests/` — file test della skill (se esistono)

**Step 1: Verifica test esistenti**

```bash
ls tests/ && grep -r "service-logic-map\|logic-build" tests/ -l
```

**Step 2: Se esistono test di struttura o triggering**

Aggiungere asserzione che `skills/siae-service-logic-map/SKILL.md` contenga:
- `L3`
- `Business Rules`
- `KieSession`
- `Step 5.*POST-BUILD`

**Step 3: Esegui test suite**

```bash
bash tests/run-all.sh 2>&1 | tail -20
```
Output atteso: `All tests passed` o nessun FAIL legato alle modifiche

**Step 4: Commit (solo se test modificati)**

```bash
git add tests/
git commit -m "test: aggiorna asserzioni per L3 e POST-BUILD in siae-service-logic-map"
```
