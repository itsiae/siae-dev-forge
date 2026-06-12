---
name: siae-premortem
description: >
  Use BEFORE opening a Pull Request on itsiae/* repos. Applies Gary Klein's
  premortem method (HBR 2007): imagine the PR has failed badly 3 months from
  now, brainstorm concrete failure causes, top-3 with mitigations. Catches
  failure modes that post-implementation review misses due to hindsight bias.
  Trigger: prima di gh pr create, prima di merge significativi, audit finale
  pre-deploy, "che cosa puo' andare storto", premortem, pre-mortem, project
  premortem, Klein method, failure modes analysis.
validates_via:
  predicate: premortem_executed
  evidence_type: session_skill
  evidence_path: ~/.claude/.devforge-session-skills
  evidence_check: "grep -qF siae-premortem"
---

# SIAE Premortem — Audit Prospettico Pre-PR

> **Tipo:** Rigid | **Fase SDLC:** 6. QA Gate (chiusura)
> **Required by hook:** `pr-premortem-gate` (PreToolUse Bash, blocca `gh pr create|edit` senza evidenza)

---

## LA LEGGE DI FERRO

```
NESSUNA PR APERTA SENZA AVER IMMAGINATO IL SUO FALLIMENTO
```

<EXTREMELY-IMPORTANT>
Il post-mortem analizza un fallimento avvenuto. Il premortem lo previene.
Gary Klein (HBR 2007): immaginare che l'evento sia gia' accaduto aumenta del
30% l'identificazione delle cause rispetto a "cosa potrebbe andare storto".

Sei tentato di saltare ("PR piccola", "modifica banale", "documentazione")?
Le PR piccole sono quelle dove il bias di familiarita' e' piu' forte.
Esegui sempre il premortem prima di gh pr create — il costo e' 2-3 minuti,
il guadagno e' identificare il failure mode che ti farebbe rollback.
</EXTREMELY-IMPORTANT>

---

> 📊 **Fonte metodo:** Gary Klein, "Performing a Project Premortem", Harvard Business Review, Settembre 2007. Adattato per LLM single-agent workflow SIAE.

## Quando si applica

**Sempre, prima di `gh pr create` su `itsiae/*`.** Il hook `pr-premortem-gate` blocca la creazione PR se non c'e' evidenza di invocazione.

**Nessun bypass discrezionale:** il gate `pr-premortem-gate` non è più
aggirabile. Anche per hotfix P1, bump meccanici o revert va invocata la skill
(per questi casi il premortem è breve: poche righe sulle top cause).

---

## Metodo Klein adattato per LLM single-agent

### Step 1 — Set the Premise

Costruisci il prompt mentale, scrivilo esplicitamente nel checkpoint:

> "Siamo a **3 mesi** dal merge di questa PR. Il risultato e' un fallimento conclamato:
> rollback in produzione, bug critico cronico, design abbandonato e riscritto da zero,
> adozione zero, audit esterno fallito, incident in produzione. NON un sotto-performante:
> un disastro. Quali sono le ragioni concrete del fallimento?"

Anti-pattern: "il rischio principale e' che ci siano bug" → vuoto, scarta.

### Step 2 — Brainstorm Failure Causes

Lista **5-10 cause concrete e specifiche**. Livello giusto: ogni causa deve essere
falsificabile e identificare un meccanismo. Esempi:

| Sbagliato (vago) | Giusto (concreto) |
|---|---|
| "edge case non coperto" | "lo schema DB sceglie un INDEX su una colonna nullable, query a 50M righe va in seq scan e batch notturno esplode" |
| "potrebbe non scalare" | "il pool di connessioni Postgres e' 20 ma la lambda invocations/min picco e' 200; saturazione a settimana 4" |
| "dipendenza fragile" | "la libreria xyz e' al maintainer solo, ultimo release 18 mesi fa; CVE pubblico in 3 mesi e nessuno la patcha" |
| "bug" | "il contract Feign con `sport-gestione-licenze-service` non e' versionato; modifica DTO rompe 4 caller in produzione" |

### Step 3 — Categorize

Ogni causa va in una di queste 4 categorie:

| Categoria | Esempi |
|---|---|
| **Tecnica** | Scaling, performance, contract drift, dipendenza fragile, race condition, leak |
| **Operativa** | Deploy rotto, rollback impossibile, monitoraggio assente, runbook mancante, on-call non sa fixare |
| **Adozione** | Team non capisce il pattern, troppo onboarding, friction UX, doc inadeguata, alternativa migliore esiste |
| **Esterna** | Dipendenza terza scompare, regolamento cambia, ground-truth non c'e', stakeholder cambia priorita' |

**Guard anti-bias implementer:** se hai solo failure mode Tecniche, stai pensando da implementer. Forza almeno 1 causa per ciascuna delle 4 categorie (anche se sembra debole). Aiuta a uscire dal tunnel mentale.

### Step 4 — Top-3 + Mitigazioni

Seleziona le **3 cause** che combinano:
- Probabilita' (likelihood) alta o media
- Impatto (devastazione) alto

Per ciascuna scrivi **una mitigazione concreta** nello scope della PR:

| Mitigazione valida | Mitigazione invalida |
|---|---|
| "Aggiunto test contract Pact su Feign client → break detection in CI" | "Faremo attenzione" |
| "ADR-NN documentato + telemetria su query latency p99 con alert >2s" | "Monitorato in produzione" |
| "Fallback su libreria stdlib se xyz non risponde in 5s, smoke test settimanale" | "Valuteremo alternative" |
| "Doc README + esempio funzionante + demo team session calendarizzata" | "Comunicato al team" |

Se una causa critica NON ha mitigazione realistica nello scope corrente:
**flag come rischio residuo accettato** nel PR body, esplicitamente. Non nasconderlo.

### Step 5 — Decisione di rotta

| Stato | Azione |
|---|---|
| 0-1 cause critiche con mitigazione chiara nello scope | ✅ **PROCEDI** con `gh pr create` |
| 2-3 cause critiche tutte mitigabili nello scope | ✅ **PROCEDI**, integra mitigazioni nel PR body |
| ≥1 causa critica **non mitigabile** nello scope, rischio residuo alto | ⚠️ **RIVISITA** il design → torna a `siae-brainstorming` Step 4 (opzione alternativa) o chiedi all'utente di accettare il rischio residuo esplicitamente |
| Premortem genericato ("bug", "potrebbe non funzionare") | 🔴 **REJECT premortem** → ripeti Step 2 con livello di concretezza adeguato |

---

## Output strutturato obbligatorio

Emetti checkpoint `[PREMORTEM]` con questo formato minimo:

```
[PREMORTEM]
  PR target:     <branch> → <base>
  Cause totali:  N (Tecnica:T, Operativa:O, Adozione:A, Esterna:E)
  Top-3:
    1. <causa> — mitigazione: <mitigazione concreta>
    2. <causa> — mitigazione: <mitigazione concreta>
    3. <causa> — mitigazione: <mitigazione concreta>
  Rischi residui accettati:
    - <descrizione + rationale> (oppure: nessuno)
  Decisione: PROCEDI | RIVISITA | REJECT
```

Il PR body **deve includere** la sezione "## Premortem" con almeno le top-3 cause +
mitigazioni. Il reviewer le legge per fare audit prospettico ostile.

---

## Anti-pattern (NON valgono come premortem)

| Pensiero | Realta' |
|---|---|
| "Lo faccio dopo se serve" | Il premortem post-PR e' un post-mortem. Hai gia' fallito a prevenire. |
| "PR piccola, 13 righe, non serve" | Le PR piccole rompono produzione quanto le grandi. Il file size non protegge. |
| "Documentazione, niente puo' andare storto" | La doc sbagliata fa scrivere codice sbagliato a 50 persone. |
| "Ho gia' fatto code review, basta" | Code review trova bug nel diff. Premortem trova bug nel **design** che il diff implementa. |
| "Top-3 cause sono tutte tecniche" | Bias da implementer. Forza Adozione + Operativa + Esterna. |
| "Mitigazione: faremo attenzione" | Non e' una mitigazione, e' un wishful thinking. |

---

## Classificazione rischio / Limiti / Permission

- **Step 1-5:** 🟢 Sicuro (analisi mentale, no file modificati)
- **Output checkpoint:** 🟢 Sicuro (testo)
- **Decisione REJECT/RIVISITA:** 🟡 Medio (blocca apertura PR — comportamento corretto)
- **Permission denied:** N/A — la skill non richiede tool, solo ragionamento + output testuale
- **Limiti:** Step 2 max 10 cause (oltre = analysis paralysis). Step 4 sempre top-3, mai top-1 o top-5.

---

## Vincoli

1. **SEMPRE** eseguire prima di `gh pr create` (hook lo enforça)
2. **SEMPRE** prefissare le cause con la categoria (Tecnica/Operativa/Adozione/Esterna)
3. **SEMPRE** scrivere mitigazione concreta, mai wishful thinking
4. **NON** sostituire premortem con code review o spec review (sono complementari, non ridondanti)
5. **NON** generare cause vaghe ("bug", "potrebbe rompersi") — il hook chiama l'output e l'utente lo legge
6. **Nessun bypass discrezionale:** il gate non è aggirabile; anche hotfix/bump/revert richiedono un premortem (breve)

---

## Riferimenti

- Gary Klein, "Performing a Project Premortem", HBR Settembre 2007 — https://hbr.org/2007/09/performing-a-project-premortem
- Gary Klein blog — https://www.gary-klein.com/premortem
- Pattern complementare: `siae-blind-review` (audit ostile spec↔codice), `siae-finishing-branch` (checklist pre-PR)
