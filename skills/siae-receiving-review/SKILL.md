---
name: siae-receiving-review
description: >
  OBBLIGATORIA quando si riceve feedback di code review. Ogni commento richiede reazione esplicita.
  Trigger: ho ricevuto feedback su una PR, il reviewer ha lasciato commenti, CHANGES REQUESTED,
  commenti su PR, review ricevuta, fix richiesti dal reviewer, rispondi ai commenti,
  il reviewer ha chiesto modifiche.
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

## LA LEGGE DI FERRO

```
OGNI COMMENTO RICHIEDE UNA REAZIONE ESPLICITA — IL SILENZIO NON E' UNA RISPOSTA
```

<EXTREMELY-IMPORTANT>
Stai per pushare fix senza aver risposto a TUTTI i commenti del reviewer?
FERMATI. Ogni commento = una risposta. Il silenzio non e' una risposta.

Stai per implementare fix senza aver letto TUTTI i commenti prima?
FERMATI. Leggi tutto prima di agire. Un commento puo' chiarire o contraddire un altro.

Stai per rispondere "Ottimo punto!" o "Grazie per il feedback!"?
CANCELLALO. Performance emotiva, non tecnica. Descrivi il fix invece.
</EXTREMELY-IMPORTANT>

---

## Il Principio Fondamentale

La code review richiede **valutazione tecnica**, non performance emotiva.

**Mindset corretto:**
- Il reviewer ha visto qualcosa che tu non hai visto — ascolta prima di difenderti
- "Non sono d'accordo" è legittimo — ma richiede argomentazione tecnica, non emotiva
- Il silenzio non è una risposta — ogni commento richiede una reazione esplicita

---

## Risposte Vietate

**MAI:**
- `"Hai assolutamente ragione!"` — performance emotiva, non tecnica
- `"Ottimo punto!"` / `"Ottimo feedback!"` — performativo
- `"Lo implemento subito"` — prima di aver verificato
- Qualsiasi espressione di gratitudine (`"Grazie"`, `"Grazie per il feedback"`)

**INVECE:**
- Riformula il requisito tecnico: `"Capisco — il problema è X. Fix in corso."`
- Fai domande di chiarimento se non capisci
- Opponi resistenza tecnica argomentata se il suggerimento è sbagliato
- Inizia a lavorare (le azioni parlano più delle parole)

**Se stai per scrivere "Grazie": CANCELLALO.** Descrivi il fix invece.

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

🟡 MEDIO — Mostra pre-flight card prima di applicare i fix

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-receiving-review |
|:---|
| 🌿 Branch: `<branch-name>` |
| 📝 Fix da implementare: `<N> REQUIRED, <M> SUGGESTION` |
| 1. 📝 Azione: Modifica file per fix review |
| 📂 `<file/i coinvolti>` |
| 💡 Perche': Si stanno applicando modifiche al codice in risposta a feedback di review |
| 🚫 Se NO: I fix non vengono applicati — i commenti REQUIRED restano aperti |

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

**Quando i fix sono pronti e la checklist sopra è completa, mostra la pre-flight card PRIMA di pushare:**

🔴 ALTO — Mostra pre-flight card prima di push

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-receiving-review |
|:---|
| ⚠️ OPERAZIONE DIFFICILE DA ANNULLARE |
| 🌿 Branch: `<branch-name>` |
| 📝 Fix applicati: `<N> REQUIRED, <M> SUGGESTION` |
| 🧪 Test suite: `<risultato test>` |
| 1. 🚀 Azione: Push fix al branch della PR |
| 📂 `origin/<branch-name>` |
| 💡 Perche': Fix review completati, test verdi, pronto per re-review |
| 🚫 Se NO: I fix restano locali, il reviewer non vede le modifiche |

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
Per capire meglio: c'è un problema specifico che questo codice crea?
O è una preferenza stilistica? Così posso rispondere nel modo più utile.
```

(Niente "Grazie" — le azioni parlano, non le formule di cortesia.)

### Il reviewer chiede una feature "professionale"

```
SE il reviewer suggerisce "implementa correttamente" / "aggiungi X feature":
  grep nel codebase per utilizzi reali dell'endpoint/metodo

  SE non usato: "Questo non viene chiamato. Rimuoviamo (YAGNI)?"
  SE usato: implementa correttamente
```

Non implementare mai "perché si fa così" senza verificare se la feature è realmente usata.

---

### Il reviewer ha torto

Capita. Rispondi con evidenza, non con certezza.

```
Ho verificato: il metodo X garantisce Y per via di Z (vedi javadoc).
Il comportamento che descrivi non dovrebbe accadere perché [ragione].
Puoi confermare di aver visto il test TestClass#testMethod che
dimostra questo comportamento?
```

---

### Risposta ai Commenti Inline su GitHub

Quando il reviewer lascia commenti inline su righe specifiche di codice,
rispondi nel thread del commento — **non** come commento top-level alla PR.

```bash
# Rispondi a un commento inline (mantieni il thread)
# Esegui manualmente da terminale — non automatizzare senza revisione del body
gh api \
  repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies \
  -f body="[tua risposta]"

# Ottieni l'ID del commento inline
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments | jq '.[].id'
```

Rispondere come commento top-level rompe il thread e rende il review difficile
da seguire per il reviewer. Usa sempre il thread corretto.

**Eccezione:** commenti generali sulla PR (non legati a righe specifiche) vanno
come commento top-level via `gh pr comment {pr_number} --body "[testo]"`.

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Il reviewer non capisce il contesto" | Forse hai ragione, ma la spiegazione e' tua. |
| "Sono commenti minori, li ignoro" | Ogni commento richiede risposta esplicita. |
| "Implemento tutto senza rispondere" | Il reviewer non sa cosa hai fatto. Rispondi sempre. |
| "E' solo un nitpick, devo farlo?" | Devi rispondere. Non necessariamente implementarlo. |
| "Ho gia' risposto verbalmente" | Le risposte verbali non restano nella storia. Scrivi. |
| "Il reviewer e' pignolo" | La pignoleria in review e' una virtu'. Rispondi con rispetto. |
| "Fixo solo i REQUIRED e basta" | Le SUGGESTION di qualita' migliorano il codice nel tempo. |
| "Rispondo 'Ottimo punto' e implemento" | Performance emotiva. Di' cosa hai fatto, non come ti senti. |
| "Aggiungo la feature, il reviewer ha esperienza" | Verifica prima se e' usata. YAGNI vale anche in review. |

---

## Signal Phrase — Discomfort nel Pushback

Se sei a disagio nel pushback su un suggerimento del reviewer (senti pressione
a non contestare, la situazione è ambigua, il reviewer è senior) ma non
riesci a dirlo direttamente:

```
"Situazione insolita al Circle K."
```

Questa frase segnala al tech lead che hai bisogno di un allineamento sincrono
prima di procedere. Il significato è noto al team.

**Non usarla per evitare pushback legittimo.** Usala quando il contesto
interpersonale rende il pushback tecnico difficile da articolare in chat.

Per la gestione della PR prima che il reviewer risponda, vedi `siae-requesting-review`.

---

## Permission Denied Handling

**Step 1-2 (Lettura e Categorizzazione) — permission-free:**
Questi step usano solo Read/Grep per leggere i commenti e il codice. Nessun permesso richiesto.

**Step 3 (Fix codice) — Edit/Write/Bash richiesti:**
- **Se Edit/Write negato:** degrada come siae-tdd — presenta il codice fix in blocco code fenced con path e istruzioni
- **Se Bash negato (test):** fornisci il comando test e chiedi all'utente di eseguire e riportare l'output

**Step 4 (Rispondi ai commenti) — permission-free:**
Le risposte ai commenti PR sono output testuale — nessun permesso richiesto.

**Fasi completabili senza permessi:** Step 1, 2, 4 (lettura, categorizzazione, risposte)
**Fasi che richiedono permessi:** Step 3 (Edit per fix, Bash per test)

Se i permessi sono negati:
1. Completa categorizzazione e analisi
2. Presenta il codice fix come output testuale
3. Fornisci comandi test per esecuzione manuale
4. NON entrare in loop di retry su tool negato
5. NON dichiarare completamento per fasi non eseguite

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card | Note |
|-----------|---------|------|------|
| Lettura commenti | 🟢 Sicuro | No | Solo lettura |
| Categorizzazione | 🟢 Sicuro | No | Solo analisi |
| Fix codice | 🟡 Medio | No | Coperto da siae-tdd |
| Push aggiornamento branch | 🔴 Alto | Si | Pre-flight: test verdi |
| Risposta ai commenti | 🟢 Sicuro | No | Comunicazione asincrona |
