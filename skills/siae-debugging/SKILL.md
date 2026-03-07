---
name: siae-debugging
description: >
  Use when encountering any bug, error, or unexpected behavior — before proposing fixes.
  Trigger: bug, errore, incident, test che fallisce, comportamento inatteso.
---

# SIAE Debugging Sistematico

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  SIAE Debugging Sistematico         ║
╚══════════════════════════════════════════════════════════════════╝
```

## Panoramica

I fix casuali sprecano tempo e creano nuovi bug. Le patch rapide mascherano problemi profondi.

**Principio fondamentale:** SEMPRE trovare la root cause prima di tentare fix. Risolvere i sintomi e' fallimento.

**Violare la lettera di questo processo significa violare lo spirito del debugging.**

---

## La Legge Ferrea

```
NESSUN FIX SENZA ROOT CAUSE INVESTIGATION COMPLETATA (FASE 1)
```

Se non hai completato la Fase 1, **non puoi proporre fix**. Punto.

---

## Quando Usare

Usa per QUALSIASI problema tecnico:
- Bug in produzione/collaudo/sviluppo
- Test che falliscono
- Comportamento inatteso
- Problemi di performance
- Build failure
- Errori di integrazione (Lambda, Glue, API Gateway, frontend)
- Incident in produzione

**Usa SOPRATTUTTO quando:**
- Sei sotto pressione di tempo (l'urgenza rende il guessing tentante)
- "Un fix veloce" sembra ovvio
- Hai gia' tentato piu' di un fix
- Il fix precedente non ha funzionato
- Non capisci completamente il problema

---

## Le 4 Fasi Obbligatorie

Devi completare ogni fase PRIMA di procedere alla successiva.

### Fase 1: Root Cause Investigation (HARD-GATE)

> **HARD-GATE**: Questa fase DEVE completarsi prima di qualsiasi tentativo di fix.
> Non esistono eccezioni. Nemmeno per P1 in produzione.

**PRIMA di tentare QUALSIASI fix:**

1. **Leggi i Messaggi di Errore con Attenzione**
   - Non saltare errori o warning
   - Spesso contengono la soluzione esatta
   - Leggi gli stack trace COMPLETAMENTE
   - Annota line numbers, file paths, error codes
   - **CloudWatch**: per Lambda/Glue, filtra per `ERROR` e `WARN`
   - **Console browser**: `console.error` per problemi frontend

2. **Riproduci in Modo Deterministico**
   - Puoi triggerarlo in modo affidabile?
   - Quali sono i passi esatti?
   - Succede ogni volta?
   - Se non riproducibile: raccogli piu' dati, NON tirare a indovinare

3. **Controlla i Cambiamenti Recenti**
   - Cosa e' cambiato che potrebbe causare questo?
   - `git diff`, commit recenti
   - Nuove dipendenze, cambi di configurazione
   - Differenze tra ambienti (sviluppo vs collaudo vs produzione)

4. **Traccia all'Indietro dal Sintomo alla Causa**
   - Dove origina il valore errato?
   - Chi ha chiamato questa funzione con dati sbagliati?
   - Continua a risalire finche' non trovi la sorgente
   - Correggi alla sorgente, non al sintomo

5. **Raccogli Evidenze nei Sistemi Multi-Componente**
   ```
   Per OGNI confine tra componenti:
     - Logga i dati in ingresso
     - Logga i dati in uscita
     - Verifica propagazione environment/config
     - Controlla lo stato a ogni livello

   Esegui una volta per raccogliere evidenze su DOVE si rompe
   POI analizza le evidenze per identificare il componente fallato
   POI investiga quel componente specifico
   ```

### Fase 2: Pattern Analysis

**Trova il pattern prima di fixare:**

1. **Bug Isolato o Sistemico?**
   - E' un caso singolo o un pattern ricorrente?
   - Cerca bug simili in altri moduli/servizi
   - Controlla se il bug esiste in altri ambienti

2. **Cerca Pattern Simili nel Repo**
   - `Grep("pattern_sospetto", "src/")` (tool nativo, permission-free)
   - `git log --oneline --all -S "stringa_rilevante"` (richiede Bash — se negato, chiedi all'utente di eseguire e incollare l'output)
   - Cerca issue JIRA correlate via MCP

3. **Confronta con Riferimenti Funzionanti**
   - Localizza codice simile che funziona
   - Cos'ha di diverso rispetto a cio' che e' rotto?
   - Elenca OGNI differenza, anche minima
   - Non assumere "questo non puo' importare"

4. **Comprendi le Dipendenze**
   - Quali altri componenti servono?
   - Quali settings, config, variabili d'ambiente?
   - Quali assunzioni implicite ci sono?

### Fase 3: Hypothesis Testing

**Metodo scientifico:**

1. **Formula Ipotesi Concrete**
   - Dichiara chiaramente: "Credo che X sia la root cause perche' Y"
   - Scrivila — non tenerla in testa
   - Sii specifico, non vago ("il database e' lento" NON e' un'ipotesi)

2. **Testa UNA Ipotesi alla Volta**
   - Fai il cambiamento PIU' PICCOLO possibile per testare
   - Una variabile alla volta
   - NON fixare piu' cose insieme

3. **Documenta Risultati di Ogni Test**
   - Ha funzionato? Si: procedi alla Fase 4
   - Non ha funzionato? Formula NUOVA ipotesi
   - NON aggiungere altri fix sopra

4. **Quando Non Sai**
   - Di' "Non capisco X"
   - Non fingere di sapere
   - Chiedi aiuto, ricerca di piu'

### Fase 4: Implementation

**Fixa la root cause, non il sintomo:**

🟡 MEDIO — Mostra pre-flight card prima di applicare il fix

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-debugging |
|:---|
| 🔑 Root cause: `<descrizione root cause identificata>` |
| 📊 Ipotesi: Confermata in Fase 3 |
| 1. 🧪 Azione: Scrivi test di regressione + fix minimale |
| 📂 `<file target>` |
| 💡 Perche': Root cause confermata, fix minimale pronto |
| 🚫 Se NO: Nessun fix applicato, torna a Fase 3 per nuova ipotesi |

1. **Test di Regressione Obbligatorio (TDD)**
   - Scrivi il test che riproduce il bug PRIMA del fix
   - Riproduzione piu' semplice possibile
   - Test automatizzato se possibile
   - DEVE esistere prima di fixare

2. **Fix Minimale (YAGNI)**
   - Indirizza la root cause identificata
   - UN cambiamento alla volta
   - Nessun "gia' che ci sono" improvement
   - Nessun refactoring incluso nel fix

3. **Verifica il Fix**
   - Il test passa ora?
   - Nessun altro test rotto?
   - Il problema e' effettivamente risolto?

4. **Commit con Riferimento al Bug/Ticket**
   - `fix(modulo): descrizione fix [PROJ-NNN]`
   - Collega al ticket JIRA se disponibile

---

## Regola dei 3 Tentativi

```
Se 3+ fix falliscono → STOP. Metti in discussione l'architettura.
```

**Pattern che indicano un problema architetturale:**
- Ogni fix rivela nuovo stato condiviso / coupling / problema in un punto diverso
- I fix richiedono "refactoring massiccio" per essere implementati
- Ogni fix crea nuovi sintomi altrove

**Quando scatta la regola:**
1. FERMA tutto
2. Non tentare il Fix #4 senza discussione architetturale
3. Metti in discussione i fondamentali:
   - Questo pattern e' fondamentalmente solido?
   - Stiamo insistendo per inerzia?
   - Dovremmo ristrutturare l'architettura?
4. Discuti con il team prima di procedere

Questo NON e' un'ipotesi fallita — e' un'architettura sbagliata.

---

## Anti-Rationalization Table

| Pensiero | Realta' |
|----------|---------|
| "So gia' cos'e'" | Probabilmente no. Investiga prima. |
| "E' un fix veloce" | I fix veloci diventano bug lenti. |
| "Funzionava ieri" | Qualcosa e' cambiato. Trova cosa. |
| "Non riesco a riprodurlo" | Non l'hai capito abbastanza. Continua a investigare. |
| "E' un problema di infrastruttura" | Verifica prima di scaricare la colpa. |
| "Aggiungo un try-catch" | Stai nascondendo il problema, non risolvendo. |
| "Riavvio e vedo se si risolve" | Hai rimosso l'evidenza diagnostica. |
| "Il codice sembra giusto" | Il codice mente. I log no. |
| "Fix multipli insieme per risparmiare tempo" | Non puoi isolare cosa ha funzionato. Causa nuovi bug. |
| "Emergenza, non c'e' tempo per il processo" | Il debug sistematico e' PIU' VELOCE del guess-and-check. |
| "Prima fixo poi investigo" | Il primo fix imposta il pattern. Fallo bene dall'inizio. |
| "Un altro tentativo" (dopo 2+ fallimenti) | 3+ fallimenti = problema architetturale. Non fixare ancora. |

---

## Integrazione SIAE

### CloudWatch — Lambda / Glue

```bash
# Filtra errori Lambda negli ultimi 30 minuti
aws logs filter-log-events \
  --log-group-name "/aws/lambda/NOME_FUNZIONE" \
  --start-time $(date -d '30 minutes ago' +%s000) \
  --filter-pattern "ERROR"

# Filtra errori Glue Job
aws logs filter-log-events \
  --log-group-name "/aws-glue/jobs/NOME_JOB" \
  --filter-pattern "?ERROR ?Exception ?Traceback"

# Cerca pattern specifico
aws logs filter-log-events \
  --log-group-name "/aws/lambda/NOME_FUNZIONE" \
  --filter-pattern '{ $.level = "ERROR" }'
```

### Qodana — Scan Statico

- Esegui scan Qodana per trovare pattern sospetti correlati al bug
- Controlla i risultati per code smells nella zona del bug
- Usa i finding come input per la Fase 2 (Pattern Analysis)

### Google Analytics — Error Tracking Frontend

- Controlla eventi di errore (5xx, 4xx, network errors)
- Verifica se il problema e' correlato a browser/dispositivo specifico
- Controlla la timeline degli errori per capire quando e' iniziato

### JIRA — Collegamento Ticket

- Cerca issue correlate via MCP Atlassian (`searchJiraIssuesUsingJql`)
- Collega il bug al ticket se disponibile
- Aggiorna lo stato del ticket durante l'investigazione
- Documenta la root cause nel ticket

---

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

## Vincoli Non Negoziabili

1. **Nessun fix senza root cause** — La Fase 1 e' un HARD-GATE
2. **Nessun try-catch "preventivo"** — Mascherare errori non e' risolvere
3. **Nessun revert senza capire perche'** — Il revert senza comprensione ricreera' il problema
4. **Nessun fix multiplo in un singolo commit** — Isola i cambiamenti
5. **Nessun "funziona sul mio PC"** — Se non funziona in un ambiente, c'e' un problema

---

## Template RCA

Per incident significativi (P1/P2), compila: `skills/siae-debugging/template/rca-template.md`

---

## Tecniche di Supporto

- **[defense-in-depth.md](defense-in-depth.md)** — Pattern a 4 layer per validare il fix (Entry Point, Business Logic, Environment Guards, Debug Instrumentation). Da applicare quando un bug riappare dopo il fix o quando opera su sistemi critici.

- **[find-polluter.sh](find-polluter.sh)** — Script per test bisection. Identifica quale test causa "pollution" (stato condiviso, file temporanei, modifiche globali). Uso: `./skills/siae-debugging/find-polluter.sh '<pattern>' '<glob>'`.

---

## Permission Denied Handling

**Fase 1-3 (investigazione):**
- Lettura codice: `Read(file)` — permission-free
- Ricerca pattern: `Grep(pattern, path)` — permission-free
- `git log`, `git diff`: richiedono Bash — se negato, chiedi all'utente di eseguire e incollare l'output
- CloudWatch/AWS CLI: richiedono Bash — se negato, fornisci i comandi esatti e chiedi l'output

**Fase 4 (fix):**
- Edit/Write: se negato, degrada come siae-tdd (codice in blocco fenced + path)
- Bash (test): se negato, fornisci comando test e chiedi all'utente di eseguire

**Fasi completabili senza permessi:** gran parte di Fase 1-3 (Read, Grep nativi)
**Fasi che richiedono permessi:** `git log/diff` (Bash), Fase 4 (Edit + Bash per test)

Se i permessi sono negati:
1. Completa l'investigazione con Read/Grep nativi
2. Presenta i comandi git/AWS che l'utente deve eseguire
3. Attendi l'output per procedere con l'analisi
4. NON entrare in loop di retry su tool negato
5. NON dichiarare completamento per fasi non eseguite

---

## Impatto Reale

Dai log di debugging sistematico vs casuale su incident SIAE:

| Approccio | Tempo medio a fix | First-time fix rate | Bug reintrodotti |
|-----------|-------------------|---------------------|-----------------|
| **Sistematico** (questa skill) | 15-30 min | ~90% | Quasi zero |
| **Guess-and-check** | 2-3 ore di thrashing | ~40% | Frequente |

**Da 24 sessioni di debugging documentate:**
- Ogni "quick fix" senza root cause investigation ha richiesto in media 2 ulteriori fix
- Il 95% dei "no root cause found" era investigazione incompleta
- Gli incident P1 risolti con metodo sistematico non si sono ripresentati

**La razionalizzazione piu' costosa:** *"E' urgente, non ho tempo per il processo"*
Il debug sistematico e' piu' veloce del thrashing. Sempre.

---

## Quick Reference

| Fase | Attivita' Chiave | Criterio di Successo |
|------|------------------|----------------------|
| **1. Root Cause** (HARD-GATE) | Leggi errori, riproduci, traccia, raccogli evidenze | Capisci COSA e PERCHE' |
| **2. Pattern** | Cerca pattern, confronta, analizza dipendenze | Identifichi differenze |
| **3. Hypothesis** | Formula ipotesi, testa minimamente, documenta | Confermata o nuova ipotesi |
| **4. Implementation** | Test TDD, fix minimale, verifica, commit | Bug risolto, test passano |
