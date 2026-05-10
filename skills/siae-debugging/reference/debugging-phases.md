# siae-debugging — 4 Fasi RCA Dettagliate

> Reference linked da `../SKILL.md`. Contenuto operativo dettagliato delle 4 fasi obbligatorie di Root Cause Analysis.

## Le 4 Fasi Obbligatorie

Devi completare ogni fase PRIMA di procedere alla successiva.

Copia questa checklist e traccia il progresso:

```
Debug Progress:
- [ ] Fase 1: Root Cause Investigation (reproduci + raccogli contesto)
- [ ] Fase 2: Formula ipotesi di root cause
- [ ] Fase 3: Verifica ipotesi (test mirato)
- [ ] Fase 4: Applica fix + regression test
```

### Fase 1: Root Cause Investigation (HARD-GATE)

> **HARD-GATE**: Questa fase DEVE completarsi prima di qualsiasi tentativo di fix.
> Non esistono eccezioni. Nemmeno per P1 in produzione.

### Context-First Rule

Prima di leggere file, eseguire comandi, o fare domande all'utente,
verifica se l'informazione e' gia' presente nella conversazione corrente
(messaggi precedenti, output di tool, skill gia' invocate).
Non chiedere cio' che e' gia' stato detto. Non rileggere cio' che e' gia' stato letto.

**PRIMA di tentare QUALSIASI fix:**

1. **Leggi i Messaggi di Errore con Attenzione**
   - Non saltare errori o warning
   - Spesso contengono la soluzione esatta
   - Leggi gli stack trace COMPLETAMENTE
   - Annota line numbers, file paths, error codes
   - **Logs di osservabilita'**: filtra per `ERROR` e `WARN` (es. CloudWatch per Lambda/Glue, vedi `debugging-cloudwatch.md`)
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
| 🔑 Root cause: `<descrizione root cause identificata>` · 📊 Ipotesi: Confermata in Fase 3 |
| **▼ Azione** |
| 1. 🧪 Azione: Scrivi test di regressione + fix minimale → `<file target>` |
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
