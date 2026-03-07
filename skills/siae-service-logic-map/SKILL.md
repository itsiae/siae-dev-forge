---
name: siae-service-logic-map
description: >
  Use when profiling what microservices do: domain, entities, workflows, business
  rules, clusters. Trigger: "cosa fa {servizio}", "lanciamo su {pattern}",
  "analizziamo {sistema}", "mappa la logica", "build catalogo L1/L2/L3",
  "regole business di", "Drools in", "quali servizi gestiscono X",
  impact analysis, /forge-logic-build, /forge-logic-search.
---

# SIAE Service Logic Map — Domain Profile e Workflow Map

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║         🗂️  DevForge  ·  SIAE Service Logic Map                  ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 1. Init & Setup

---

## ANTI-HALLUCINATION PROTOCOL — NON NEGOZIABILE

MAI descrivere cosa fa un servizio senza citare il file sorgente.
SE NON HAI LETTO IL FILE, IL WORKFLOW NON ESISTE.

### Confidence Tag Obbligatori

| Tag | Significato |
|-----|-------------|
| `[CONFIRMED]` | evidenza letta direttamente dal file |
| `[INFERRED]` | dedotto da nome classe/metodo — DEVI citare file:riga |
| `[UNVERIFIED]` | nessuna evidenza — nel Gap Report, MAI rimosso |
| `[FILE_NOT_FOUND]` | file non accessibile — documenta il gap |

---

## Step 0 — SYSTEM_MAP.md: Discovery o Auto-Generate

`SYSTEM_MAP.md` e' l'input per la cluster detection (Step 3).
Questa skill lo cerca automaticamente — **non serve generarlo prima.**

```bash
# Cerca SYSTEM_MAP.md in ordine di priorita'
SYSTEM_MAP=""
for CANDIDATE in \
  "docs/SYSTEM_MAP.md" \
  "docs/systems/"*"/SYSTEM_MAP.md" \
  /tmp/siae-sysmap-*/SYSTEM_MAP.md; do
  FOUND=$(ls $CANDIDATE 2>/dev/null | sort | tail -1)
  if [ -n "$FOUND" ]; then
    SYSTEM_MAP="$FOUND"
    echo "[FOUND] SYSTEM_MAP.md: $SYSTEM_MAP"
    break
  fi
done
```

**Se trovato:** usa il file trovato → procedi al Step 1.

**Se non trovato:** genera automaticamente eseguendo `siae-microservices-map`
sul pattern di repo specificato dall'utente, poi riprendi da Step 3.

```
REQUIRED SUB-SKILL: siae-microservices-map
```

Non chiedere all'utente di eseguire un comando separato.
L'output di `siae-microservices-map` viene passato direttamente al Step 3
senza richiedere commit intermedio — usa il path `/tmp/siae-sysmap-*/SYSTEM_MAP.md`.

---

## Quando si Applica

**Sempre:**
- Onboarding su servizio sconosciuto: "cosa fa sport-X?"
- Impact analysis cross-repo: "quali servizi gestiscono Y?"
- Build catalogo logic per cluster: `/forge-logic-build`
- Ricerca concetti/workflow: `/forge-logic-search`

**Output:** un documento per cluster (non per singolo servizio) che descrive
il dominio funzionale e i workflow di tutti i servizi del cluster.

---

## Step 1 — PRE-FLIGHT: Verifica Accesso GitHub

Prima di procedere, verifica che l'accesso ai repo sia disponibile.

```bash
# Verifica autenticazione GitHub
gh auth status

# Verifica accesso all'organizzazione SIAE
gh api /orgs/itsiae --jq '.login'

# Lista repo disponibili nel namespace rilevante
gh repo list itsiae --limit 20 --json name,isPrivate --jq '.[] | [.name, .isPrivate] | @csv'
```

🟢 SICURO — Nessuna pre-flight card necessaria.

**Se l'accesso e' negato:**
- Verifica le credenziali con `gh auth login`
- Se persiste, documenta i repo non accessibili come `[FILE_NOT_FOUND]`
- NON procedere assumendo l'accesso

---

## Step 2 — ENUMERATE: Inventario Repo

Identifica i repo target per il dominio richiesto.

### 2a — Disambiguazione Pattern (se l'utente usa un nome semantico)

Se l'utente ha descritto il sistema con un nome semantico (es. "filiera del credito",
"sistema abbonamenti") invece di un prefisso tecnico, prova SEMPRE multiple varianti
prima di dichiarare "nessun repo trovato":

```bash
# Testa varianti: nome esteso, acronimo, abbreviazione
# Es. "filiera del credito" → credito, fdc, filiera
for PATTERN in "{variante1}" "{variante2}" "{acronimo}"; do
  echo -n "$PATTERN: "
  gh repo list itsiae --limit 500 --json name \
    --jq "[.[] | .name | select(test(\"$PATTERN\"))] | length"
done
```

**Regola:** zero risultati su una variante NON significa "nessun repo".
Prova almeno 3 varianti prima di chiedere conferma all'utente.

Mostra i candidati trovati e chiedi conferma:
```
Repo trovati per "{dominio}":
  sport-fdc-evidenza-service, sport-fdc-fascicolo-service, sport-fdc-documento-service
Sono questi i repo target? (si / aggiungi altri / rimuovi)
```

### 2b — Fetch Lista Confermata

```bash
# Fetch con il pattern confermato
gh repo list itsiae --limit 500 --json name --jq '[.[] | .name | select(test("{pattern}"))]'

# Per ogni repo: verifica branch default e struttura base
gh api /repos/itsiae/{repo}/branches --jq '[.[].name]'
```

**Output atteso:** lista ordinata di `{org}/{repo}` confermata dall'utente.

**Gap Report — repo non accessibili:**
```
[FILE_NOT_FOUND] itsiae/{repo}: accesso negato o repo non esistente
```

---

## Step 3 — CLUSTER DETECTION

Legge `docs/SYSTEM_MAP.md` ed estrae i cluster dal grafo delle dipendenze.

🟢 SICURO — Nessuna pre-flight card necessaria.

### 3a — Estrai il Grafo

```bash
cat docs/SYSTEM_MAP.md
```

Analizza il blocco Mermaid in SYSTEM_MAP.md:
1. Estrai le edge `A --> B` (dipendenze dirette tra servizi)
2. Raggruppa per connettivita': servizi con dipendenze reciproche o path condivisi = stesso cluster
3. Servizi isolati (nessuna edge) = cluster singleton

**Regola di evidenza:** usa SOLO le dipendenze documentate in SYSTEM_MAP.md.
MAI inferire cluster dal nome del servizio o dal dominio percepito.

### 3b — Proponi Cluster all'Utente

Presenta i cluster proposti prima di procedere:

```
Cluster proposti da docs/SYSTEM_MAP.md:

  cluster-abbonamenti (3 servizi):
    sport-gestione-abbonamento, sport-contabilita, sport-pagamenti
    [CONFIRMED] da SYSTEM_MAP.md: dipendenze reciproche

  cluster-iscrizioni (2 servizi):
    sport-iscrizioni, sport-atleti
    [CONFIRMED] da SYSTEM_MAP.md: sport-iscrizioni --> sport-atleti

  cluster-standalone (1 servizio):
    sport-notifiche
    [CONFIRMED] da SYSTEM_MAP.md: nessuna dipendenza rilevata

Confermi questi cluster prima del build? (si / no / modifica)
```

🟡 MEDIO — Attendere conferma utente prima di procedere al Step 4.

**Se l'utente modifica i cluster:**
- Aggiorna la mappa manualmente e documenta la modifica come `[INFERRED]`
- Motivo della modifica va documentato in `clusters.yaml`

---

## Step 4 — BUILD CATALOG

### 4a — Setup Output Directory

```bash
OUTPUT_DIR="docs/logic-catalog"
mkdir -p "$OUTPUT_DIR"
echo "Logic catalog dir: $OUTPUT_DIR"
```

### 4b — Pre-fetch Dati per Cluster (Parent via Bash)

Per ogni cluster, pre-fetcha i dati di TUTTI i repo del cluster prima di dispatchar l'agente:

```bash
# Per ogni repo nel cluster:

# 1. File tree per trovare *Service.java, *Entity.java, openapi*.yaml
gh api "/repos/itsiae/{repo}/git/trees/HEAD?recursive=1" \
  --jq '[.tree[].path | select(test("Service\\.java$|Entity\\.java$|Controller\\.java$|openapi.*\\.ya?ml$|Scheduler\\.java$"))] | .[0:20]'

# 2. Per ogni *Service.java: solo metodi public (firme, non body)
gh api /repos/itsiae/{repo}/contents/{path} --jq '.content' | base64 -d \
  | grep -E "^\s+(public|@Transactional|@Scheduled|@KafkaListener)"

# 3. openapi*.yaml (se esiste): prime 100 righe
gh api /repos/itsiae/{repo}/contents/{openapi-path} --jq '.content' | base64 -d | head -100

# 4. Pre-fetch L3 — Business Rules (per ogni *Service.java)
#    Grep snippet: KieSession/Drools, condizioni dominio, @Query
gh api /repos/itsiae/{repo}/contents/{ServiceFile} --jq '.content' | base64 -d \
  | grep -n "KieSession\|fireAllRules\|@Query\|@NamedQuery\|if.*[Ss]tato\|if.*[Tt]ipo\|if.*[Cc]ategoria" -A3 -B1

# 5. Pre-fetch L3 — Repository e DRL files (se esistono nel tree scan)
gh api /repos/itsiae/{repo}/contents/{RepositoryFile} --jq '.content' | base64 -d \
  | grep -n "@Query\|@NamedQuery\|@EntityGraph" -A2
```

**Regola critica:** il parent pre-fetcha SEMPRE via Bash. Gli agenti ricevono i dati inline — non hanno permesso di usare Bash autonomamente.

### 4c — Pilot Test (OBBLIGATORIO su sistemi con 3+ cluster)

🟡 MEDIO — Mostra pre-flight card prima del pilot test.

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-service-logic-map",
  "context": [
    {"emoji": "🔬", "label": "Pilot test", "value": "1 cluster su N totali"},
    {"emoji": "📦", "label": "Dati pre-fetchati", "value": "Service.java + Entity.java + openapi"}
  ],
  "actions": [
    {"emoji": "🤖", "label": "Dispatch 1 agente pilot (cluster piu piccolo)", "path": "docs/logic-catalog/"},
    {"emoji": "📄", "label": "Scrittura 1 file cluster", "path": "docs/logic-catalog/cluster-{nome}.md"}
  ],
  "reason": "Validazione pipeline prima del full run",
  "ifno": "Pilot annullato, full run non garantito senza validazione"
}' | python3 design-system/generate-card.py
```

Procedura pilot:
1. Pre-fetcha dati per il cluster piu' piccolo (meno repo)
2. Dispatcha 1 agente con dati inline nel prompt
3. Verifica output: `ls docs/logic-catalog/cluster-*.md | wc -l` → deve essere `1`
4. Se OK → procedi con full run (Step 4d)
5. Se file mancante → STOP, diagnostica istruzioni agente prima di continuare

### 4d — Dispatch Agenti per Cluster (Full Run)

🟡 MEDIO — Mostra pre-flight card prima del full run.

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-service-logic-map",
  "context": [
    {"emoji": "🤖", "label": "Agenti", "value": "K agenti (1 per cluster) in parallelo"},
    {"emoji": "📦", "label": "Cluster", "value": "lista cluster confermati al Step 3"},
    {"emoji": "✅", "label": "Pilot", "value": "1/1 file verificato"}
  ],
  "actions": [
    {"emoji": "⚡", "label": "Dispatch tutti gli agenti in parallelo", "path": "docs/logic-catalog/"},
    {"emoji": "📄", "label": "Scrittura K file cluster", "path": "docs/logic-catalog/cluster-*.md"}
  ],
  "reason": "Pilot OK, full run pronto",
  "ifno": "Full run annullato, catalogo parziale"
}' | python3 design-system/generate-card.py
```

Dispatcha TUTTI i cluster in un blocco parallelo (1 agente per cluster).

**ISTRUZIONE CRITICA DA INCLUDERE IN OGNI AGENTE:**

```
Hai tutti i dati nel prompt per il cluster {nome} ({lista servizi}).
NON usare Bash. Usa SOLO il Write tool.
1. Analizza i dati e compila la doc L1+L2+L3 per ogni servizio del cluster
   - L3 usa i snippet grep ricevuti inline: sezione "Business Rules"
   - Se snippet grep vuoto per un repo → [UNVERIFIED] nessun pattern L3 trovato
   (formato: reference/logic-catalog-template.yaml)
2. Scrivi in: docs/logic-catalog/cluster-{nome}.md
3. Rispondi con UNA SOLA RIGA: "OK cluster-{nome} salvato"
4. NON includere Markdown nel corpo della risposta
```

### 4e — Genera clusters.yaml (Parent)

Dopo che tutti gli agenti hanno scritto i file cluster, il parent genera il file indice:

```bash
# Verifica file cluster scritti
ls docs/logic-catalog/cluster-*.md | wc -l   # deve == K cluster
```

Il parent scrive `docs/logic-catalog/clusters.yaml`:

```yaml
generated_at: YYYY-MM-DDTHH:MM:SSZ
source: docs/SYSTEM_MAP.md
clusters:
  - name: "{cluster-name}"
    services: ["{repo1}", "{repo2}"]
    domain: "{dominio funzionale — da cluster-{nome}.md}"
    confidence: CONFIRMED | INFERRED
```

E `docs/logic-catalog/system-overview.md` con la visione d'insieme di tutti i cluster.

### 4f — Collect: Verifica File Scritti

```bash
ls docs/logic-catalog/cluster-*.md | wc -l   # deve == K cluster
ls docs/logic-catalog/clusters.yaml           # deve esistere
ls docs/logic-catalog/system-overview.md      # deve esistere
```

Se mancano file → re-dispatcha solo i cluster mancanti (non tutto il batch).

---

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

---

## Step 6 — QUERY (forge-logic-search)

Riceve keyword dall'utente, cerca nel catalogo locale.

```bash
# Cerca nei file cluster (Markdown)
grep -ri "{keyword}" docs/logic-catalog/ --include="*.md" -l

# Cerca nel catalogo cluster
grep -ri "{keyword}" docs/logic-catalog/clusters.yaml

# Per ogni file con match: mostra contesto
grep -ri "{keyword}" docs/logic-catalog/{file} -B2 -A2
```

**Output atteso:** tabella con colonne `cluster | servizio | layer | campo | valore | source`

Esempio:
| cluster | servizio | layer | campo | valore | source |
|---------|----------|-------|-------|--------|--------|
| cluster-abbonamenti | sport-gestione-abbonamento | l2.workflow | name | calcolaPreventivo | `[CONFIRMED]` GestioneAbbonamentoService.java:45 |
| cluster-abbonamenti | sport-contabilita | l2.workflow | name | elaboraPreventivo | `[CONFIRMED]` ContabilitaService.java:12 |

---

## Formato Output per Cluster

**`docs/logic-catalog/cluster-{nome}.md`** — documento tecnico-funzionale del cluster:

```markdown
# Cluster: {nome}

Servizi: {lista repo}
Dominio: {dominio funzionale} [CONFIRMED] docs/SYSTEM_MAP.md

## {repo-1}

### L1 — Domain Profile
- Domain: {nome dominio} [CONFIRMED] {Entity.java:riga}
- Entities: {ClassName1}, {ClassName2} [CONFIRMED] {Entity.java:riga}
- Exposes: {/api/v1/...} [CONFIRMED] {openapi.yaml:riga}

### L2 — Workflow Map
- {nomeMetodo}(): trigger=REST [CONFIRMED] {Service.java:riga}
- {nomeScheduled}(): trigger=SCHEDULED [CONFIRMED] {Scheduler.java:riga}

### L3 — Business Rules
- {nomeMetodo}(): regola={condizione dominio} [CONFIRMED] {Service.java:riga}
- Drools: KieSession.fireAllRules() [CONFIRMED] {Service.java:riga} → {rules.drl}
- {NomeRepository}: @Query("...") [CONFIRMED] {Repository.java:riga}

## {repo-2}
...

## Gap Report
- [FILE_NOT_FOUND] {repo}: Service.java non trovato
```

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Dal nome del metodo capisco cosa fa" | Il nome non e' evidenza. Leggi la firma. |
| "Questo servizio probabilmente gestisce X" | Probabilmente = allucinazione. Leggi il file. |
| "I workflow si capiscono dal dominio" | Solo firme @Service con source:riga sono evidenza. |
| "Ho gia' visto servizi simili" | Ogni repo e' diverso. Analizza questo specifico. |
| "Non trovo il Service.java, ma fa sicuramente X" | `[FILE_NOT_FOUND]`. Documenta il gap. |
| "Il pilot e' lento, salto al full run" | Senza pilot, non sai se gli agenti scrivono i file. |
| "I cluster si capiscono dal nome dei servizi" | Solo edge in SYSTEM_MAP.md sono evidenza. |
| "Questo cluster mi sembra ovvio" | Ovvio non e' CONFIRMED. Leggi SYSTEM_MAP.md. |
| "Salto la conferma cluster, e' chiaro" | La conferma protegge da cluster sbagliati nel catalogo. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|------------|---------|------|
| Verifica accesso GitHub (`gh auth status`) | 🟢 Sicuro | No |
| Enumerate repo (`gh repo list`) | 🟢 Sicuro | No |
| Lettura SYSTEM_MAP.md + estrazione cluster | 🟢 Sicuro | No |
| Proposta cluster all'utente | 🟢 Sicuro | No |
| Pre-fetch file via Bash (parent) | 🟢 Sicuro | No |
| Pilot test — dispatch 1 agente | 🟡 Medio | Si |
| Full run — dispatch K agenti in parallelo | 🟡 Medio | Si |
| Query catalogo locale (`grep`) | 🟢 Sicuro | No |
| Scrittura `docs/logic-catalog/` | 🟡 Medio | Si |
| POST-BUILD siae-documentation | 🟡 Medio | Si (nella skill siae-documentation) |

---

## Vincoli Non Negoziabili

1. MAI procedere senza `docs/SYSTEM_MAP.md` — prerequisito assoluto
2. MAI assegnare un servizio a un cluster senza evidenza da SYSTEM_MAP.md
3. MAI descrivere workflow senza firma metodo reale con `source:riga`
4. MAI inferire entita' dal nome del servizio — solo `@Entity` class names
5. SEMPRE conferma utente sui cluster prima del build (Step 3b)
6. SEMPRE Gap Report per ogni repo, anche se vuoto
7. SEMPRE pilot test con 1 cluster prima del full run (su sistemi con 3+ cluster)
8. Gli agenti usano SOLO Write tool — il parent pre-fetcha i dati via Bash
9. I Confidence Tag sono obbligatori su ogni voce del catalogo

```
REQUIRED SUB-SKILL: siae-verification
```

Prima di dichiarare il build del catalogo completato, invoca `siae-verification`
con evidenza: `ls docs/logic-catalog/cluster-*.md | wc -l` deve corrispondere
al numero di cluster confermati al Step 3b.
