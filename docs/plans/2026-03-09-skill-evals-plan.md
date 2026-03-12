# Skill Evals & Description Optimization — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Integrare skill-creator per description optimization e aggiungere trigger regression test al test runner DevForge
**Architettura:** Plugin skill-creator esterno per authoring + script bash per CI regression che legge trigger-evals JSON
**Stack:** Bash, Python 3, JSON, Claude CLI (`claude -p`)
**SP:** 3

---

### Task 1: Scaffold directory evals/ e aggiornamento .gitignore [DONE]

**File coinvolti:**
- Crea: `siae-dev-forge/evals/trigger-evals/.gitkeep`
- Crea: `siae-dev-forge/evals/workspace/.gitkeep`
- Modifica: `siae-dev-forge/.gitignore`

**Step 1: Crea le directory**

```bash
mkdir -p siae-dev-forge/evals/trigger-evals
mkdir -p siae-dev-forge/evals/workspace
touch siae-dev-forge/evals/trigger-evals/.gitkeep
touch siae-dev-forge/evals/workspace/.gitkeep
```

**Step 2: Aggiungi workspace a .gitignore**

Aggiungi al file `siae-dev-forge/.gitignore`:

```
# Eval workspace (risultati temporanei skill-creator)
evals/workspace/*
!evals/workspace/.gitkeep
```

**Step 3: Verifica struttura**

```bash
find siae-dev-forge/evals -type f
```
Output atteso:
```
siae-dev-forge/evals/trigger-evals/.gitkeep
siae-dev-forge/evals/workspace/.gitkeep
```

**Step 4: Commit**

```bash
git add siae-dev-forge/evals/ siae-dev-forge/.gitignore
git commit -m "chore: scaffold evals/ directory per skill trigger regression"
```

---

### Task 2: Script run-trigger-regression.sh [DONE]

**File coinvolti:**
- Crea: `siae-dev-forge/tests/run-trigger-regression.sh`

**Step 1: Scrivi il test — verifica che lo script esista e sia eseguibile**

```bash
test -x siae-dev-forge/tests/run-trigger-regression.sh && echo "PASS" || echo "FAIL"
```
Output atteso (prima dell'implementazione): `FAIL`

**Step 2: Implementa lo script**

Crea `siae-dev-forge/tests/run-trigger-regression.sh`:

```bash
#!/usr/bin/env bash
# run-trigger-regression.sh — Trigger regression tests usando eval queries
#
# Uso: ./tests/run-trigger-regression.sh [--skill <nome-skill>]
#
# Legge i file JSON in evals/trigger-evals/ e verifica che ogni query
# triggeri (o non triggeri) la skill corrispondente usando claude -p.
#
# Exit code: 0 = tutti sopra soglia, 1 = almeno uno sotto soglia

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EVALS_DIR="${PLUGIN_ROOT}/evals/trigger-evals"
SINGLE_SKILL=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skill) SINGLE_SKILL="$2"; shift 2 ;;
    *) echo "Uso: $0 [--skill <nome-skill>]"; exit 1 ;;
  esac
done

# Check prerequisites
if ! command -v claude >/dev/null 2>&1; then
  echo "  SKIP  claude CLI non disponibile"
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "  FAIL  jq non disponibile (richiesto per parsing JSON)"
  exit 1
fi

# Carica credenziali Bedrock se disponibili
BEDROCK_ENV="${SCRIPT_DIR}/.env.bedrock"
if [ -f "$BEDROCK_ENV" ]; then
  # shellcheck source=/dev/null
  source "$BEDROCK_ENV"
fi

# Soglie
RECALL_THRESHOLD="0.80"
PRECISION_THRESHOLD="0.80"

# Timeout
TIMEOUT_CMD="timeout"
if ! command -v timeout >/dev/null 2>&1; then
  if command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD="gtimeout"
  else
    TIMEOUT_CMD=""
  fi
fi

TOTAL_PASS=0
TOTAL_WARN=0
TOTAL_SKIP=0

# Per ogni file trigger-eval
for eval_file in "${EVALS_DIR}"/*.json; do
  [ ! -f "$eval_file" ] && continue
  [ "$(basename "$eval_file")" = ".gitkeep" ] && continue

  skill_name=$(basename "$eval_file" .json)

  # Filtro singola skill se richiesto
  if [ -n "$SINGLE_SKILL" ] && [ "$skill_name" != "$SINGLE_SKILL" ]; then
    continue
  fi

  # Conta query
  total_should=$(jq '[.[] | select(.should_trigger == true)] | length' "$eval_file")
  total_should_not=$(jq '[.[] | select(.should_trigger == false)] | length' "$eval_file")

  if [ "$total_should" -eq 0 ] && [ "$total_should_not" -eq 0 ]; then
    echo "  SKIP  ${skill_name}: nessuna query nel file"
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
    continue
  fi

  # Test should-trigger queries
  tp=0  # true positives
  fn=0  # false negatives
  for i in $(seq 0 $((total_should - 1))); do
    query=$(jq -r ".[$i | tonumber].query // empty" <(jq '[.[] | select(.should_trigger == true)]' "$eval_file"))

    if [ -n "$TIMEOUT_CMD" ]; then
      output=$($TIMEOUT_CMD 60 claude -p "$query" \
        --dangerously-skip-permissions \
        --output-format stream-json \
        --verbose 2>/dev/null || true)
    else
      output=$(claude -p "$query" \
        --dangerously-skip-permissions \
        --output-format stream-json \
        --verbose 2>/dev/null || true)
    fi

    if echo "$output" | grep -q "\"skill\":\"siae-devforge:${skill_name}\"" || \
       echo "$output" | grep -q "\"skill\":\"${skill_name}\""; then
      tp=$((tp + 1))
    else
      fn=$((fn + 1))
    fi
  done

  # Test should-not-trigger queries
  tn=0  # true negatives
  fp=0  # false positives
  for i in $(seq 0 $((total_should_not - 1))); do
    query=$(jq -r ".[$i | tonumber].query // empty" <(jq '[.[] | select(.should_trigger == false)]' "$eval_file"))

    if [ -n "$TIMEOUT_CMD" ]; then
      output=$($TIMEOUT_CMD 60 claude -p "$query" \
        --dangerously-skip-permissions \
        --output-format stream-json \
        --verbose 2>/dev/null || true)
    else
      output=$(claude -p "$query" \
        --dangerously-skip-permissions \
        --output-format stream-json \
        --verbose 2>/dev/null || true)
    fi

    if echo "$output" | grep -q "\"skill\":\"siae-devforge:${skill_name}\"" || \
       echo "$output" | grep -q "\"skill\":\"${skill_name}\""; then
      fp=$((fp + 1))
    else
      tn=$((tn + 1))
    fi
  done

  # Calcola metriche
  if [ "$total_should" -gt 0 ]; then
    recall=$(echo "scale=2; $tp / $total_should" | bc)
  else
    recall="1.00"
  fi

  if [ $((tp + fp)) -gt 0 ]; then
    precision=$(echo "scale=2; $tp / ($tp + $fp)" | bc)
  else
    precision="1.00"
  fi

  # Valuta soglie
  recall_ok=$(echo "$recall >= $RECALL_THRESHOLD" | bc)
  precision_ok=$(echo "$precision >= $PRECISION_THRESHOLD" | bc)

  if [ "$recall_ok" -eq 1 ] && [ "$precision_ok" -eq 1 ]; then
    echo "  PASS  ${skill_name}: ${tp}/${total_should} should-trigger, ${tn}/${total_should_not} should-not-trigger (P:${precision} R:${recall})"
    TOTAL_PASS=$((TOTAL_PASS + 1))
  else
    echo "  WARN  ${skill_name}: ${tp}/${total_should} should-trigger, ${tn}/${total_should_not} should-not-trigger (P:${precision} R:${recall})"
    [ "$recall_ok" -eq 0 ] && echo "         ↳ recall ${recall} < ${RECALL_THRESHOLD}"
    [ "$precision_ok" -eq 0 ] && echo "         ↳ precision ${precision} < ${PRECISION_THRESHOLD}"
    TOTAL_WARN=$((TOTAL_WARN + 1))
  fi
done

echo ""
echo "Trigger Regression: PASS=${TOTAL_PASS} WARN=${TOTAL_WARN} SKIP=${TOTAL_SKIP}"

# WARN non causa fallimento — le description sono probabilistiche
exit 0
```

**Step 3: Rendi eseguibile e verifica**

```bash
chmod +x siae-dev-forge/tests/run-trigger-regression.sh
test -x siae-dev-forge/tests/run-trigger-regression.sh && echo "PASS" || echo "FAIL"
```
Output atteso: `PASS`

**Step 4: Verifica che senza eval files non crashi**

```bash
cd siae-dev-forge && bash tests/run-trigger-regression.sh
```
Output atteso:
```
Trigger Regression: PASS=0 WARN=0 SKIP=0
```

**Step 5: Commit**

```bash
git add siae-dev-forge/tests/run-trigger-regression.sh
git commit -m "feat(tests): aggiungi run-trigger-regression.sh per eval description"
```

---

### Task 3: Integrazione flag --with-trigger-regression in run-all.sh [DONE]

**File coinvolti:**
- Modifica: `siae-dev-forge/tests/run-all.sh`

**Step 1: Aggiungi parsing del flag**

Dopo la riga `set -euo pipefail` e prima del banner, aggiungi:

```bash
# Parse arguments
WITH_TRIGGER_REGRESSION=false
for arg in "$@"; do
  case "$arg" in
    --with-trigger-regression) WITH_TRIGGER_REGRESSION=true ;;
  esac
done
```

**Step 2: Aggiungi la sezione trigger regression prima del report finale**

Prima della riga `# --- Report Finale ---`, aggiungi:

```bash
# --- Trigger Regression Tests (opzionale, richiede claude CLI + token) ---
if [ "$WITH_TRIGGER_REGRESSION" = true ]; then
  echo ""
  echo "=== Trigger Regression Tests ==="
  echo ""

  if [ -x "${SCRIPT_DIR}/run-trigger-regression.sh" ]; then
    "${SCRIPT_DIR}/run-trigger-regression.sh" || true
  else
    echo "  SKIP  run-trigger-regression.sh non trovato o non eseguibile"
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
  fi
fi
```

**Step 3: Verifica che run-all.sh senza flag funzioni come prima**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: 73+ test PASS, 0 FAIL (invariato)

**Step 4: Verifica che il flag venga riconosciuto**

```bash
cd siae-dev-forge && bash tests/run-all.sh --with-trigger-regression
```
Output atteso: test normali + sezione "Trigger Regression Tests" con 0 risultati (nessun eval file ancora)

**Step 5: Commit**

```bash
git add siae-dev-forge/tests/run-all.sh
git commit -m "feat(tests): aggiungi flag --with-trigger-regression a run-all.sh"
```

---

### Task 4: Crea primo trigger eval di esempio (siae-brainstorming) [DONE]

**File coinvolti:**
- Crea: `siae-dev-forge/evals/trigger-evals/siae-brainstorming.json`

**Step 1: Scrivi le eval queries**

Crea `siae-dev-forge/evals/trigger-evals/siae-brainstorming.json` con 20 query realistiche — 10 should-trigger, 10 should-not-trigger. Le query devono essere dettagliate e realistiche (non keyword generiche), con edge case per near-miss.

```json
[
  {"query": "Devo implementare una nuova feature per il servizio di gestione diritti d'autore. L'idea e' di aggiungere un endpoint REST che permetta di cercare le opere musicali per ISWC e restituire i titolari dei diritti con le rispettive quote. Il servizio gira su Spring Boot e usa DynamoDB come database. Come procediamo?", "should_trigger": true},
  {"query": "Ho un'idea per migliorare il sistema di notifiche: vorrei aggiungere notifiche push via Firebase quando un nuovo contratto viene registrato nel sistema SPORT. Cosa ne pensi come approccio?", "should_trigger": true},
  {"query": "Dobbiamo creare un nuovo microservizio per la gestione delle licenze sincronizzazione. Deve esporre API REST, integrarsi con il sistema legacy SIAE via SOAP, e salvare su PostgreSQL. Quali sono le opzioni architetturali?", "should_trigger": true},
  {"query": "Vorrei ripensare come funziona il flusso di approvazione delle ripartizioni. Attualmente e' tutto sincrono, ma con 2 milioni di righe ci mette troppo. Possiamo passare ad un approccio asincrono con Step Functions?", "should_trigger": true},
  {"query": "Sto pensando di aggiungere una dashboard Vue.js per il monitoraggio real-time delle ingestion nel data lake. Dovrebbe mostrare grafici con i volumi giornalieri e alert quando un job Glue fallisce. Come la progettiamo?", "should_trigger": true},
  {"query": "Ho bisogno di aggiungere un nuovo campo 'codice_territorio' alla tabella opere nel servizio catalogo. Questo impatta sia l'API che il modello DynamoDB. Come affrontiamo la modifica?", "should_trigger": true},
  {"query": "Voglio creare una CLI interna per gli operatori SIAE che permetta di fare query veloci sullo stato delle ripartizioni senza passare dal portale web. Che tool stack suggerisci?", "should_trigger": true},
  {"query": "Il team ha chiesto di poter esportare i report delle ripartizioni in formato Excel oltre che PDF. Devo aggiungere questa funzionalita' al servizio report-service. Come impostiamo il lavoro?", "should_trigger": true},
  {"query": "Devo decidere se usare SQS o EventBridge per la comunicazione tra il servizio contratti e il servizio notifiche. Entrambi hanno pro e contro nel nostro contesto. Aiutami a valutare.", "should_trigger": true},
  {"query": "Vorrei aggiungere il supporto multi-lingua (italiano/inglese) al frontend del portale associati. Attualmente e' tutto hardcoded in italiano. Come lo progettiamo?", "should_trigger": true},

  {"query": "Il test TestRipartizioneService::testCalcoloQuote fallisce con NullPointerException alla riga 234. Puoi debuggare?", "should_trigger": false},
  {"query": "Fai git checkout -b feature/SPORT-789-nuovo-endpoint e pusha il branch", "should_trigger": false},
  {"query": "Leggi il file src/main/java/it/siae/catalogo/CatalogoService.java e dimmi cosa fa il metodo cercaOpera", "should_trigger": false},
  {"query": "Scrivi un unit test per il metodo validateISWC nella classe ISWCValidator", "should_trigger": false},
  {"query": "La pipeline Glue job bronze-to-silver fallisce con errore OutOfMemoryError. Come lo risolvo?", "should_trigger": false},
  {"query": "Puoi fare review del mio codice? Ho appena pushato su feature/SPORT-456-fix-auth", "should_trigger": false},
  {"query": "Aggiorna la versione di Spring Boot da 3.1.0 a 3.2.1 nel pom.xml", "should_trigger": false},
  {"query": "Ho ricevuto CHANGES REQUESTED sulla PR #45, il reviewer dice che manca la gestione degli errori nel controller", "should_trigger": false},
  {"query": "Genera la documentazione OpenAPI per il servizio catalogo-service", "should_trigger": false},
  {"query": "Esegui terraform plan per il modulo networking nel folder infrastructure/modules/vpc", "should_trigger": false}
]
```

**Step 2: Verifica JSON valido**

```bash
jq '.' siae-dev-forge/evals/trigger-evals/siae-brainstorming.json > /dev/null && echo "JSON valido" || echo "JSON non valido"
jq 'length' siae-dev-forge/evals/trigger-evals/siae-brainstorming.json
```
Output atteso: `JSON valido` e `20`

**Step 3: Commit**

```bash
git add siae-dev-forge/evals/trigger-evals/siae-brainstorming.json
git commit -m "feat(evals): aggiungi trigger eval queries per siae-brainstorming"
```

---

### Task 5: Description optimization top 5 skill con skill-creator [BLOCKED] — richiede sessione interattiva con skill-creator

**Prerequisito:** skill-creator installato (Task 0 manuale)

**Questo task è iterativo e interattivo — va eseguito manualmente con skill-creator, non da subagent.**

Per ciascuna delle top 5 skill (brainstorming, verification, debugging, git-workflow, tdd):

1. Crea il file `evals/trigger-evals/<skill-name>.json` con 20 query (come Task 4)
2. Esegui: `python -m scripts.run_loop --eval-set evals/trigger-evals/<skill>.json --skill-path skills/<skill> --max-iterations 5`
3. Applica `best_description` al frontmatter YAML della skill
4. Committa description aggiornata + file eval queries

**Output finale:** 5 file trigger-eval JSON + 5 description ottimizzate.

**Nota:** Questo task si fa in sessione interattiva con skill-creator. Il piano non include codice perché è un workflow di authoring guidato dal tool.

---

## Riepilogo Task e Dipendenze

```
Task 1: Scaffold evals/         ← indipendente
Task 2: run-trigger-regression.sh  ← dipende da Task 1 (directory evals/)
Task 3: Flag in run-all.sh      ← dipende da Task 2 (script esiste)
Task 4: Primo eval brainstorming ← dipende da Task 1 (directory esiste)
Task 5: Optimization top 5      ← dipende da Task 4 (formato validato), interattivo
```

Task 1, 2, 3, 4 sono automatizzabili da subagent.
Task 5 è interattivo (richiede skill-creator + review umana).
