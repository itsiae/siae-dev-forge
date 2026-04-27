# Task 15 — In-session testability protocol

**Stato:** [PENDING]
**Execution:** in-session (è LA guida per testare da dentro Claude Code)
**Dipendenze:** nessuna (protocollo applicabile a ogni altro task)
**Durata stimata:** 10 min setup + applicato durante T02-T14

## Contesto

Siamo dentro una sessione Claude Code. Significa:
- **SÌ** possiamo: eseguire shell (Bash tool), leggere/scrivere file, lanciare agent (Agent tool), invocare skill via Skill tool
- **NO** possiamo: simulare "apri nuova sessione Claude", osservare come il modello reagisce al prompt injection in una sessione vergine, misurare latency real-world utente-to-response

Questo task definisce **come testare i deliverables PR #1 con i tool disponibili**, dimostrando sia non-regression sia miglioramento.

## Classificazione: cosa è testabile in-session, cosa richiede proxy

| Deliverable | Testabile in-session? | Metodo |
|---|---|---|
| lib/evidence-check.sh | SÌ diretto | bash test suite (T02 step 4) |
| validates_via frontmatter | SÌ diretto | python3 yaml.safe_load (T09 step 3) |
| Centralizations lib/*.md | SÌ diretto | file exists + wc -l |
| SKILL.md compression targets | SÌ diretto | wc -l determinstico |
| Catalog generation post-compression | SÌ diretto | node lib/skills-core.js + grep |
| K sections preserved | SÌ diretto | grep pattern (assert_behavioral_invariants.sh) |
| devforge-context budget | SÌ diretto | bash hook + wc -c sull'output |
| devforge-context diff-dedup | SÌ diretto | invoca 2x, check output |
| Tier policy (EXTREMELY_IMPORTANT) | SÌ diretto | grep sull'output |
| Telemetry prompt_injection_emitted | SÌ diretto | check log file post-run |
| Baseline test suite preserved | SÌ diretto | bash tests/run-all.sh + count |
| **"Il modello ora rispetta meglio i gate"** | **NO diretto** | **Proxy 1 (eval set)** |
| **"Adoption reale migliora"** | **NO diretto** | **Proxy 2 (telemetry post-merge)** |

## Proxy 1 — Eval set per comportamento modello

Simula "modello in sessione fresca" con un eval set statico: prompt fisso → output atteso.
Non misura il modello reale, ma verifica che **l'infrastruttura fornisca al modello gli input corretti**.

### Struttura

File: `evals/anti-dilution-pr1/`

```
evals/anti-dilution-pr1/
├── case-01-budget-2kb.md         # prompt: analizza output devforge-context; expect: size <2KB
├── case-02-no-wolf-cry.md        # prompt: analizza output default; expect: no EXTREMELY_IMPORTANT
├── case-03-checkpoint-schema.md  # prompt: cerca checkpoint in SKILL.md; expect: formati canonici
├── case-04-K-preservation.md     # prompt: cerca "Legge di Ferro"; expect: presente verbatim
└── run-eval.sh                    # script che lancia tutti + report
```

Ogni eval case è un bash script che:
1. Prepara uno stato controllato (mktemp HOME, set env vars)
2. Esegue il deliverable (hook, skill file, lib)
3. Verifica l'output con assert
4. Produce PASS/FAIL deterministico

### Differenza dal regression test T10

- **T10**: verifica che il codice esista e risponda come atteso (unit test)
- **T15 proxy 1**: verifica che l'output prodotto da quel codice **sia utilizzabile dal modello** (simulazione del prompt injection pipeline)

### Esempio: case-01-budget-2kb.md

```bash
#!/usr/bin/env bash
# Case: first injection deve rispettare budget 2KB E contenere backbone sufficiente.
set -eu
cd "$(git rev-parse --show-toplevel)"

export HOME=$(mktemp -d); mkdir -p "$HOME/.claude"; trap 'rm -rf "$HOME"' EXIT

OUTPUT=$(echo '{}' | bash hooks/devforge-context 2>/dev/null || true)
SIZE=$(printf '%s' "$OUTPUT" | wc -c | tr -d ' ')

# Assertion 1: size budget
if [ "$SIZE" -le 2048 ]; then PASS1=1; else PASS1=0; fi

# Assertion 2: contiene riferimento al backbone (serve al modello per skill selection)
if echo "$OUTPUT" | grep -qE "brainstorm|skill"; then PASS2=1; else PASS2=0; fi

# Assertion 3: Backbone reminder contains the 1% rule semantics (survived compression)
if echo "$OUTPUT" | grep -qE "invoke|applic"; then PASS3=1; else PASS3=0; fi

if [ $PASS1 -eq 1 ] && [ $PASS2 -eq 1 ] && [ $PASS3 -eq 1 ]; then
    echo "case-01 PASS (size=$SIZE, backbone=yes, rule=yes)"
    exit 0
else
    echo "case-01 FAIL (size=$SIZE budget_ok=$PASS1 backbone=$PASS2 rule=$PASS3)"
    exit 1
fi
```

Similmente per gli altri case.

## Proxy 2 — Dogfooding in-session

**Il test definitivo**: quando PR #1 è merged, apri una nuova sessione Claude Code e osserva:
- Il context injection è effettivamente <2KB?
- I reinject sono spariti (hash dedup funziona)?
- Il modello vede ancora il catalog correttamente?

Questo test non è automatizzabile **dentro la stessa sessione** (il modello non vede gli hook come farebbe in una sessione fresca — sono già stati applicati i merge automatici di context).

Procedura documentata in `docs/plans/anti-dilution-pr1-foundation/dogfooding-protocol.md` (da creare se non esiste):

1. Merge PR #1
2. Chiudi la sessione Claude Code corrente
3. Apri una nuova sessione
4. Esegui `bash docs/measurements/dogfooding-capture.sh` che:
   - Triggera 5 `UserPromptSubmit` simulati via script
   - Cattura output del hook chain
   - Genera `docs/measurements/post-pr1-session-capture.json`
5. Confronta con `baseline-metrics.json`

Il confronto before/after è **l'improvement dimostrato**.

### dogfooding-capture.sh

```bash
#!/usr/bin/env bash
# Capture hook chain behavior in a simulated session (post-PR #1 verification)
set -eu
OUTPUT_DIR="docs/measurements/post-pr1-capture-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUTPUT_DIR"

for i in 1 2 3 4 5; do
    RESULT=$(echo '{}' | bash hooks/run-hook.cmd devforge-context 2>/dev/null || true)
    SIZE=$(printf '%s' "$RESULT" | wc -c | tr -d ' ')
    echo "{\"iteration\":$i,\"size_bytes\":$SIZE}" >> "$OUTPUT_DIR/iterations.jsonl"
done

# Summary: first iteration should be >0 (first emission), subsequent should be <20 bytes (dedup)
python3 <<PY
import json
lines = open('$OUTPUT_DIR/iterations.jsonl').readlines()
sizes = [json.loads(l)['size_bytes'] for l in lines]
print(f"First iteration: {sizes[0]} bytes")
print(f"Subsequent avg: {sum(sizes[1:])/len(sizes[1:]):.1f} bytes")
print(f"Dedup effective: {'YES' if sizes[0] > 100 and all(s < 20 for s in sizes[1:]) else 'NO'}")
PY
```

## Summary protocol per ogni task

Durante l'esecuzione dei task PR #1, applica questo protocollo:

1. **Dopo ogni task (T01-T13)**: esegui il blocco "Step verifica" del task (sono tutti bash determinstici)
2. **Dopo T10**: esegui `bash tests/compression-regression/run-all.sh`
3. **Prima di T14 (PR)**: esegui `bash tests/run-all.sh` per baseline preservation
4. **Durante T14**: esegui `bash evals/anti-dilution-pr1/run-eval.sh` (proxy 1)
5. **Post-merge**: dogfooding capture (proxy 2)

Nessuno di questi richiede "uscire dalla sessione". Tutti sono comandi bash che possiamo eseguire qui.

## Acceptance

- [ ] Documento esiste e descrive cosa è testabile in-session
- [ ] Eval set directory `evals/anti-dilution-pr1/` pianificato (creato in T14 pre-PR)
- [ ] Dogfooding protocol documentato per post-merge
- [ ] Ogni altro task (T02, T10, T11) ha step verifica determinstici eseguibili in questa sessione

## Principio guida

Separa:
- **Ciò che possiamo testare ora** (codice, contenuto file, comportamento bash) → test automatici
- **Ciò che richiede sessione fresca** (comportamento modello davanti all'injection ridotta) → dogfooding post-merge con capture script

Non bloccare PR #1 sul secondo. Il primo dimostra che l'infrastruttura è corretta; il secondo dimostra il lift nell'ambiente reale.
