---
name: siae-autoresearch
description: >
  Ottimizza iterativamente una skill DevForge usando il metodo autoresearch (Karpathy).
  Trigger: ottimizza skill, migliora description, autoresearch, migliora trigger,
  ottimizza prompt, /forge-autoresearch, analizza performance skill.
  NON usare per: scrivere nuove skill (usa siae-writing-skills), eseguire eval singoli
  (usa runner.py direttamente), debug skill (usa siae-debugging).
backbone_role: support
backbone_stage: null
hard_gate: false
---

# SIAE Autoresearch — Ottimizzazione Iterativa Skill

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · AUTORESEARCH                        ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** Cross-cutting

---

## Cosa FA vs cosa NON FA

| Autoresearch FA | Autoresearch NON FA |
|---|---|
| Ottimizza skill **esistenti** iterativamente | Scrive nuove skill (→ `siae-writing-skills`) |
| Usa `evals/autoresearch.py` con Bedrock diretto | Duplica logica di eval/grading |
| Genera varianti description e le testa con A/B | Modifica direttamente SKILL.md senza misurare |
| Produce changelog + regole universali | Sostituisce test strutturali (`tests/run-all.sh`) |

---

## Quando si Applica

**Sempre:**
- Developer vuole migliorare precision/recall di una skill esistente
- Description di una skill produce troppi falsi positivi/negativi
- Dopo aver notato che una skill non triggera quando dovrebbe (o triggera quando non dovrebbe)

**Eccezioni (chiedi esplicitamente al partner umano):**
- Skill appena creata senza eval set (prima servono le 20 query in `evals/eval-sets/`)
- Ottimizzazione di tutte le 33 skill in batch (costo Bedrock elevato — conferma budget)

---

## Pre-requisiti

Prima di iniziare, verifica che la skill target abbia:

1. **Eval set trigger** in `evals/eval-sets/<skill-name>/trigger.json` (minimo 20 query)
2. **SKILL.md** con frontmatter `name` e `description` validi
3. **Accesso Bedrock** configurato (`AWS_REGION`, credenziali attive)

Se manca il trigger.json, fermati e chiedi all'utente se vuole generarlo prima.

---

## Istruzioni

### Step 1 — Verifica Pre-requisiti e Lancia

🟢 SICURO

1. Chiedi all'utente quale skill vuole ottimizzare (o inferisci dal contesto)
2. Verifica pre-requisiti:
   - Eval set esiste: `evals/eval-sets/<skill-name>/trigger.json`
   - SKILL.md ha frontmatter con description
   - Credenziali Bedrock attive (`AWS_REGION` impostato)

3. Lancia lo script autoresearch:
   ```bash
   cd <plugin-root> && python3 evals/autoresearch.py --skill <skill-name>
   ```

   Opzioni disponibili:
   | Flag | Default | Descrizione |
   |------|---------|-------------|
   | `--max-iter N` | 6 | Max iterazioni del loop |
   | `--target X.XX` | 0.90 | Target accuracy |
   | `--runs N` | 1 | Run per query (piu' = piu' stabile, piu' lento) |
   | `--dry-run` | — | Solo validazione struttura, nessun eval |
   | `--validate` | — | Dopo il loop, lancia validazione finale con `claude -p` |
   | `--no-color` | — | Output senza colori |

### Step 2 — Monitora il Loop

🟢 SICURO

Lo script esegue autonomamente:
1. **Baseline** — valuta precision/recall/accuracy correnti via Bedrock
2. **Identifica punto debole** — recall basso? precision bassa?
3. **Genera variante** — un solo cambio alla description per iterazione
4. **A/B test via Bedrock** — confronta description corrente vs candidata
5. **Keep/Revert** — se migliora la tiene, se peggiora fa revert
6. **Ripete** fino a target (Acc >= 0.90) o max iterazioni o plateau

Output visuale in tempo reale:
```
🔬 AUTORESEARCH — siae-brainstorming
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Iter  Cambio                           P     R     Acc    Δ      Progresso          Esito
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  0   — (baseline)                     0.80  0.60  0.70   —      ▪▪▪▪▪▪▪░░░         base
  1   +keyword "architettura"          0.80  0.70  0.75  +0.05   ▪▪▪▪▪▪▪▪░░         ✓ WIN
  2   +esclusione "NON code review"    0.90  0.70  0.80  +0.05   ▪▪▪▪▪▪▪▪░░         ✓ WIN
  3   -"design" (troppo generico)      0.85  0.70  0.78  -0.02   ▪▪▪▪▪▪▪▪░░         ⟲ REVERT
  4   +"approcci possibili"            0.90  0.80  0.85  +0.05   ▪▪▪▪▪▪▪▪▪░         ✓ WIN
  5   +"trade-off alternative"         0.90  0.90  0.90  +0.05   ▪▪▪▪▪▪▪▪▪▪         🎯 TARGET
```

### Step 3 — Applica e Verifica

🟡 MEDIO — Modifica il frontmatter SKILL.md della skill target

Quando lo script termina, mostra:
- **Confronto finale** description originale vs ottimizzata
- **Delta metriche** (P, R, Acc)
- **Regole estratte** dal changelog

Se il loop ha prodotto un miglioramento:

1. Lo script salva changelog e regole in `evals/workspace/`
2. **Chiedi conferma** all'utente prima di applicare la description
3. Se confermato, aggiorna il campo `description` nel frontmatter di `skills/<skill-name>/SKILL.md`
4. **(Opzionale)** Valida con il vero router Claude Code:
   ```bash
   python3 evals/runner.py --skill <skill-name> --ab-test \
     --description-b "<description ottimizzata>" --runs 3 --verbose
   ```

Se il loop NON ha prodotto miglioramenti:
- Suggerisci di ampliare l'eval set
- Rivedere la struttura della skill (non solo description)
- Aprire una issue per analisi manuale

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "La description attuale va bene, non serve ottimizzarla" | Se non hai misurato precision e recall, non sai se va bene. Misura prima, giudica dopo. |
| "Cambio due cose insieme cosi' vado piu' veloce" | Cambiando due variabili non sai quale ha avuto effetto. Un cambio alla volta, sempre. |
| "Il risultato e' peggiorato, ma la nuova description mi sembra migliore" | I numeri vincono sulle impressioni. Se A vince, tieni A. |
| "Faccio ancora un'iterazione, sicuramente migliora" | Se 3 iterazioni consecutive non migliorano, sei in plateau. Fermati e ripensa l'approccio. |
| "Non serve loggare il revert, tanto non ha funzionato" | I revert sono dati preziosi. Sapere cosa NON funziona e' meta' dell'ottimizzazione. |
| "Applico la description senza ri-testare, tanto ho visto i risultati del loop" | Il test post-applicazione conferma che il cambio nel file reale produce gli stessi risultati del --description-b. Mai saltarlo. |
| "L'eval set e' troppo piccolo, i risultati non contano" | 20 query con 3 run ciascuna sono 60 data point. Non perfetto, ma statisticamente informativo. Se vuoi di piu', amplia l'eval set prima. |
| "Posso ottimizzare a occhio senza baseline" | Senza baseline non sai se hai migliorato o peggiorato. Il baseline e' il punto zero non negoziabile. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura frontmatter e eval set | 🟢 Sicuro | No |
| Esecuzione baseline (runner.py L1) | 🟢 Sicuro | No |
| Analisi punto debole | 🟢 Sicuro | No |
| A/B test con description candidata | 🟡 Medio | No (non modifica file) |
| Applicazione description a SKILL.md | 🟡 Medio | Si |
| Estrazione regole | 🟢 Sicuro | No |

---

## Vincoli

1. **NON** modificare SKILL.md durante il loop — usa solo `--description-b` per testare
2. **NON** fare piu' di un cambio per iterazione — isola le variabili
3. **NON** superare 6 iterazioni per sessione senza consenso utente
4. **SEMPRE** loggare ogni iterazione con cambio, motivo, risultato ed esito
5. **SEMPRE** chiedere conferma prima di applicare la description finale a SKILL.md
6. **SEMPRE** eseguire un baseline prima e dopo per confermare il miglioramento
7. **PRE-FLIGHT OBBLIGATORIA** per applicazione description finale (Step 4)

---

## Risorse Aggiuntive

- [reference/autoresearch-loop.md](reference/autoresearch-loop.md) — Dettaglio tecnico del loop e integrazione con evals/
