---
name: siae-service-logic-map
description: >
  Use when profiling what a microservice does (domain, entities, workflows).
  Trigger: "cosa fa questo servizio", "onboarding su sport-*", "quali servizi
  gestiscono X", /forge-logic-build, /forge-logic-search, impact analysis.
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

## Quando si Applica

**Sempre:**
- Onboarding su servizio sconosciuto: "cosa fa sport-X?"
- Impact analysis cross-repo: "quali servizi gestiscono Y?"
- Build catalogo logic: `/forge-logic-build`
- Ricerca concetti/workflow: `/forge-logic-search`

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

```bash
# Filtra repo per pattern (es. sport-*, musica-*, diritti-*)
gh repo list itsiae --limit 100 --json name --jq '[.[] | .name | select(test("{pattern}"))]'

# Per ogni repo: verifica branch default e struttura base
gh api /repos/itsiae/{repo}/branches --jq '[.[].name]'
```

**Output atteso:** lista ordinata di `{org}/{repo}` con branch default.

**Gap Report — repo non accessibili:**
```
[FILE_NOT_FOUND] itsiae/{repo}: accesso negato o repo non esistente
```

---

## Step 3 — BUILD CATALOG

### 3a — Setup Output Directory

```bash
OUTPUT_DIR="docs/logic-catalog"
mkdir -p "$OUTPUT_DIR"
echo "Logic catalog dir: $OUTPUT_DIR"
```

### 3b — Pre-fetch Dati (Parent via Bash)

Per ogni repo, il parent pre-fetcha prima di dispatchar gli agenti:

```bash
# 1. File tree per trovare *Service.java, *Entity.java, openapi*.yaml
gh api "/repos/itsiae/{repo}/git/trees/HEAD?recursive=1" \
  --jq '[.tree[].path | select(test("Service\\.java$|Entity\\.java$|Controller\\.java$|openapi.*\\.ya?ml$|Scheduler\\.java$"))] | .[0:20]'

# 2. Per ogni *Service.java: solo metodi public (firme, non body)
gh api /repos/itsiae/{repo}/contents/{path} --jq '.content' | base64 -d \
  | grep -E "^\s+(public|@Transactional|@Scheduled|@KafkaListener)"

# 3. openapi*.yaml (se esiste): prime 100 righe
gh api /repos/itsiae/{repo}/contents/{openapi-path} --jq '.content' | base64 -d | head -100
```

**Regola critica:** il parent esegue SEMPRE il pre-fetch via Bash. Gli agenti ricevono i dati inline nel prompt — non hanno permesso di usare Bash autonomamente.

### 3c — Pilot Test (OBBLIGATORIO su sistemi con 5+ repo)

🟡 MEDIO — Mostra pre-flight card prima del pilot test.

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-service-logic-map",
  "context": [
    {"emoji": "🔬", "label": "Pilot test", "value": "2 repo su N totali"},
    {"emoji": "📦", "label": "Dati pre-fetchati", "value": "Service.java + Entity.java + openapi"}
  ],
  "actions": [
    {"emoji": "🤖", "label": "Dispatch 2 agenti pilot", "path": "docs/logic-catalog/"},
    {"emoji": "📄", "label": "Scrittura 2 file YAML", "path": "docs/logic-catalog/{repo1}.yaml, {repo2}.yaml"}
  ],
  "reason": "Validazione pipeline prima del full run",
  "ifno": "Pilot annullato, full run non garantito senza validazione"
}' | python3 design-system/generate-card.py
```

Procedura pilot:
1. Pre-fetcha dati per 2 repo scelti a campione
2. Dispatcha 2 agenti con dati inline nel prompt
3. Verifica output: `ls docs/logic-catalog/*.yaml | wc -l` → deve essere `2`
4. Se OK → procedi con full run (Step 3d)
5. Se file mancanti → STOP, diagnostica istruzioni agente prima di continuare

### 3d — Dispatch Agenti in Parallelo (Full Run)

🟡 MEDIO — Mostra pre-flight card prima del full run.

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-service-logic-map",
  "context": [
    {"emoji": "🤖", "label": "Agenti", "value": "N agenti in parallelo"},
    {"emoji": "📦", "label": "Repo", "value": "lista repo target"},
    {"emoji": "✅", "label": "Pilot", "value": "2/2 file verificati"}
  ],
  "actions": [
    {"emoji": "⚡", "label": "Dispatch tutti gli agenti in parallelo", "path": "docs/logic-catalog/"},
    {"emoji": "📄", "label": "Scrittura N file YAML", "path": "docs/logic-catalog/*.yaml"}
  ],
  "reason": "Pilot OK, full run pronto",
  "ifno": "Full run annullato, catalogo parziale"
}' | python3 design-system/generate-card.py
```

Dispatcha TUTTI in un blocco parallelo.

**ISTRUZIONE CRITICA DA INCLUDERE IN OGNI AGENTE:**

```
Hai tutti i dati nel prompt. NON usare Bash. Usa SOLO il Write tool.
1. Analizza i dati e compila la scheda L1+L2 YAML
   (formato: reference/logic-catalog-template.yaml)
2. Scrivi in: docs/logic-catalog/{repo-name}.yaml
3. Rispondi con UNA SOLA RIGA: "OK {repo-name} salvato"
4. NON includere YAML nel corpo della risposta
```

### 3e — Collect: Verifica File Scritti

```bash
ls docs/logic-catalog/*.yaml | wc -l   # deve == N repo dispatchati
```

Se mancano file → re-dispatcha solo i repo mancanti (non tutto il batch).

---

## Step 4 — QUERY (forge-logic-search)

Riceve keyword dall'utente, cerca nel catalogo locale.

```bash
# Cerca nei file YAML del catalogo
grep -ri "{keyword}" docs/logic-catalog/ --include="*.yaml" -l

# Per ogni file con match: mostra contesto
grep -ri "{keyword}" docs/logic-catalog/{file}.yaml -B2 -A2
```

**Output atteso:** tabella con colonne `repo | layer | campo | valore | source`

Esempio:
| repo | layer | campo | valore | source |
|------|-------|-------|--------|--------|
| sport-iscrizioni | domain | entity | Iscrizione, Atleta | `[CONFIRMED]` SportService.java:42 |
| sport-pagamenti | domain | workflow | pagamento-quota | `[CONFIRMED]` PagamentoService.java:78 |

---

## Formato Output YAML (L1+L2)

Ogni agente produce un file `docs/logic-catalog/{repo-name}.yaml` con questo schema:

```yaml
repo: itsiae/{repo-name}
generated_at: YYYY-MM-DDTHH:MM:SSZ
domain:
  name: "{dominio principale}"
  description: "{descrizione breve}"
entities:
  - name: "{EntityName}"
    source: "{path/to/Entity.java}:{riga}"
    confidence: CONFIRMED | INFERRED | UNVERIFIED
workflows:
  - name: "{nome-workflow}"
    entry_point: "{ClassName}.{methodName}()"
    source: "{path/to/Service.java}:{riga}"
    trigger: REST | KAFKA | SCHEDULED | INTERNAL
    confidence: CONFIRMED | INFERRED | UNVERIFIED
api_endpoints:
  - path: "{/api/v1/...}"
    method: GET | POST | PUT | DELETE
    source: "{openapi.yaml}:{riga} | {Controller.java}:{riga}"
    confidence: CONFIRMED | INFERRED | UNVERIFIED
gap_report:
  - type: FILE_NOT_FOUND | UNVERIFIED
    description: "{cosa manca o non e' stato possibile verificare}"
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
| "Posso inferire le entita' dal nome del repo" | Solo `@Entity` class names letti da file sono evidenza. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|------------|---------|------|
| Verifica accesso GitHub (`gh auth status`) | 🟢 Sicuro | No |
| Enumerate repo (`gh repo list`) | 🟢 Sicuro | No |
| Pre-fetch file via Bash (parent) | 🟢 Sicuro | No |
| Pilot test — dispatch 2 agenti | 🟡 Medio | Si |
| Full run — dispatch N agenti in parallelo | 🟡 Medio | Si |
| Query catalogo locale (`grep`) | 🟢 Sicuro | No |
| Scrittura `docs/logic-catalog/` | 🟡 Medio | Si |

---

## Vincoli Non Negoziabili

1. MAI descrivere workflow senza firma metodo reale con `source:riga`
2. MAI inferire entita' dal nome del servizio — solo `@Entity` class names
3. SEMPRE Gap Report per ogni repo, anche se vuoto
4. SEMPRE pilot test con 2 repo prima del full run (su sistemi con 5+ repo)
5. Gli agenti usano SOLO Write tool — il parent pre-fetcha i dati via Bash
6. I Confidence Tag sono obbligatori su ogni voce del catalogo YAML

```
REQUIRED SUB-SKILL: siae-verification
```

Prima di dichiarare il build del catalogo completato, invoca `siae-verification`
con evidenza: `ls docs/logic-catalog/*.yaml | wc -l` deve corrispondere al numero
di repo enumerati al Step 2.
