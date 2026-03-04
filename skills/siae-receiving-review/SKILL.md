---
name: siae-receiving-review
description: >
  Elaborazione strutturata di feedback di code review ricevuto.
  Trigger: ho ricevuto feedback su una PR, il reviewer ha lasciato commenti, CHANGES REQUESTED.
---

# SIAE Receiving Review — Elaborare il Feedback di Code Review

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · RECEIVING CODE REVIEW                 ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 4. Implementation (iterazione post-review)

---

## Il Principio Fondamentale

Il feedback di code review è un **regalo**, non un attacco.
Il reviewer ha investito tempo e attenzione. Merita una risposta strutturata.

**Mindset corretto:**
- Il reviewer ha visto qualcosa che tu non hai visto — ascolta prima di difenderti
- "Non sono d'accordo" è legittimo — ma richiede argomentazione tecnica, non emotiva
- Il silenzio non è una risposta — ogni commento richiede una reazione esplicita

---

## Processo in 4 Step

### Step 1 — Leggi Tutto Prima di Agire

🟢 SICURO

Leggi TUTTI i commenti prima di toccare il codice.

**Perché è importante:**
- Un commento può chiarire un altro
- Potresti rispondere al primo e scoprire che il quinto lo contraddice
- La visione d'insieme cambia le priorità

**Durante la lettura:**
- Non rispondere ancora
- Non aprire l'IDE
- Annota mentalmente: "capisco cosa intende?" per ogni punto

---

### Step 2 — Categorizza il Feedback

🟢 SICURO

Per ogni commento, classifica:

| Categoria | Definizione | Azione |
|-----------|-------------|--------|
| **REQUIRED** | Blocca il merge, errore o violazione standard | Fix obbligatorio prima del re-review |
| **SUGGESTION** | Miglioramento valido ma non bloccante | Valuta, implementa se hai senso |
| **QUESTION** | Il reviewer non capisce il codice | Rispondi con spiegazione o migliora il codice per renderlo autoesplicante |
| **NITPICK** | Preferenza stilistica non critica | Segnala come "nitpick" nella risposta, implementa a discrezione |
| **DISCUSSION** | Scelta architetturale aperta a dibattito | Risposta tecnica argomentata, allineati con il reviewer |

**Template di categorizzazione:**
```
Commento 1 [file:riga]: [REQUIRED] — "Manca gestione NPE in processPayment()"
Commento 2 [file:riga]: [SUGGESTION] — "extract method per maggiore leggibilità"
Commento 3 [file:riga]: [QUESTION] — "perché usi Optional qui invece di null check?"
Commento 4 [file:riga]: [NITPICK] — "preferisci camelCase per questa variabile"
```

---

### Step 3 — Pianifica e Implementa i Fix

🟡 MEDIO

**Ordine di implementazione:**

1. **REQUIRED** prima di tutto
2. **SUGGESTION** con giudizio (implementa se aggiunge valore reale)
3. **QUESTION** → scegli: fix il codice (meglio) o spiega nel commento
4. **NITPICK** → a tua discrezione

**Per ogni REQUIRED:**
- Se capisci il problema → fix con `siae-tdd` (RED prima del fix)
- Se non capisci → chiedi chiarimento PRIMA di implementare

```
REQUIRED SUB-SKILL: siae-tdd
```

Per ogni fix non banale, segui il ciclo RED-GREEN-REFACTOR.

**Per DISCUSSION:**

Non implementare subito. Prima rispondi con la tua posizione tecnica.
Se il reviewer risponde e hai torto, implementa con grazia.
Se hai ragione, documentalo (commento PR o ADR) e vai avanti.

---

### Step 4 — Rispondi a Ogni Commento

🟢 SICURO

Non lasciare nessun commento senza risposta. Ogni commento = una risposta.

**Template di risposta:**

```
✅ Fixato in commit abc1234 — ho aggiunto gestione NPE con Optional.ofNullable()

✅ D'accordo, ho estratto il metodo in calculateDiscount() per chiarezza.

💬 Ho lasciato Optional perché il valore può legittimamente essere assente
   secondo il dominio (un autore può non avere codice ISWC). Aggiungo un
   commento nel codice per chiarire.

🎨 [Nitpick] Preferisco mantenere la naming convention esistente nel file
   per consistenza. Se è uno standard di progetto, aggiorno volentieri.
```

**Convenzioni risposta:**
- `✅` — implementato
- `💬` — spiegazione / non implementato con motivazione
- `🎨` — nitpick, a discrezione

**Prima di richiedere il re-review:**
- [ ] Tutti i REQUIRED fixati
- [ ] Tutti i commenti hanno una risposta
- [ ] Test passano (`mvn test` / `yarn test` / `pytest`)
- [ ] Nessun nuovo file di debug introdotto

---

## Casi Speciali

### "Non sono d'accordo con questo commento"

Non ignorarlo. Non implementarlo in silenzio.

1. Rispondi con la tua posizione: "Non implemento perché [ragione tecnica]"
2. Cita riferimenti se hai: pattern del codebase, ADR esistente, documentazione
3. Proponi un'alternativa se ne hai una
4. Chiedi un allineamento sincrono se il disaccordo è importante

Il reviewer può insistere — ha questo diritto. Se insiste, allineati o escalate al team lead.

### Il feedback è vago o non costruttivo

"Questo non mi piace" non è un feedback actionable.

Risposta consigliata:
```
Grazie per il feedback. Per capire meglio: c'è un problema specifico
che questo codice crea? O è una preferenza stilistica? Così posso
rispondere nel modo più utile.
```

### Il reviewer ha torto

Capita. Rispondi con evidenza, non con certezza.

```
Ho verificato: il metodo X garantisce Y per via di Z (vedi javadoc).
Il comportamento che descrivi non dovrebbe accadere perché [ragione].
Puoi confermare di aver visto il test TestClass#testMethod che
dimostra questo comportamento?
```

---

## Anti-Rationalization Table

| Pensiero | Realta' |
|----------|---------|
| "Il reviewer non capisce il contesto" | Forse hai ragione, ma la spiegazione e' tua. |
| "Sono commenti minori, li ignoro" | Ogni commento richiede risposta esplicita. |
| "Implemento tutto senza rispondere" | Il reviewer non sa cosa hai fatto. Rispondi sempre. |
| "E' solo un nitpick, devo farlo?" | Devi rispondere. Non necessariamente implementarlo. |
| "Ho gia' risposto verbalmente" | Le risposte verbali non restano nella storia. Scrivi. |
| "Il reviewer e' pignolo" | La pignoleria in review e' una virtu'. Rispondi con rispetto. |
| "Fixo solo i REQUIRED e basta" | Le SUGGESTION di qualita' migliorano il codice nel tempo. |

---

## Classificazione Rischio

| Operazione | Livello | Note |
|-----------|---------|------|
| Lettura commenti | 🟢 Sicuro | Solo lettura |
| Categorizzazione | 🟢 Sicuro | Solo analisi |
| Fix codice | 🟡 Medio | Segui siae-tdd |
| Push aggiornamento branch | 🔴 Alto | Pre-flight: test verdi |
| Risposta ai commenti | 🟢 Sicuro | Comunicazione asincrona |
