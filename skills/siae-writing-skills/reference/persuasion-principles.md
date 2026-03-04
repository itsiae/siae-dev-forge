# Principi di Persuasione per Skill DevForge

Adattamento dei 7 principi di Cialdini al contesto delle skill Claude Code.
Basato sulla ricerca Meincke et al. (2025): l'uso strutturato di principi di persuasione
in prompt engineering raddoppia la compliance (33% → 72%).

---

## I 7 Principi

### 1. Authority (Autorita')

**Principio:** Le persone seguono le istruzioni di fonti autorevoli.

**Applicazione DevForge:**
- Legge di Ferro: una dichiarazione assoluta e non negoziabile
- Riferimenti a standard SIAE documentati
- Banner DevForge come simbolo di autorita' istituzionale
- "Standard SIAE" come fonte di verita'

**Esempio:**
```
NESSUN CODICE DI PRODUZIONE SENZA UN TEST FALLENTE PRIMA
```

**Quando usarlo:** Skill Rigid. Sempre. E' il principio piu' efficace.

---

### 2. Commitment & Consistency (Impegno e Coerenza)

**Principio:** Una volta preso un impegno, le persone tendono a mantenerlo.

**Applicazione DevForge:**
- Checklist di verifica che Claude deve spuntare
- Step sequenziali dove ogni step presuppone il completamento del precedente
- "Hai scritto il test? Allora esegui il test. Hai eseguito il test? Allora leggi il risultato."
- HARD-GATE: punti dove non si puo' procedere senza aver completato

**Esempio:**
```
Prima di dichiarare il lavoro completato:
- [ ] Il test e' stato scritto PRIMA del codice?
- [ ] Il test ha fallito (RED)?
- [ ] Il codice implementato e' il MINIMO necessario?
```

**Quando usarlo:** Skill con workflow multi-step. Crea una catena di micro-impegni.

---

### 3. Scarcity (Scarsita')

**Principio:** Le cose rare o limitate nel tempo sono percepite come piu' preziose.

**Applicazione DevForge:**
- "Nessuna eccezione" / "Non negoziabile"
- Deadline implicite: "Prima di qualsiasi commit"
- Unicita' del contesto: "Ogni contesto e' diverso. Verifica questo specifico caso."
- Esclusivita': "Solo dopo il GREEN puoi fare refactoring"

**Esempio:**
```
Questa regola si applica SEMPRE. Non ci sono eccezioni. Non esistono scorciatoie.
```

**Quando usarlo:** Per regole che non ammettono eccezioni. Rafforza l'Authority.

---

### 4. Social Proof (Prova Sociale)

**Principio:** Le persone seguono il comportamento della maggioranza.

**Applicazione DevForge:**
- "Pattern osservati in 60+ repository SIAE"
- "Standard adottato da tutte le 4 factory"
- "Convenzione usata da ~20 developer"
- Riferimenti a best practice di settore (OWASP, 12-factor, etc.)

**Esempio:**
```
Il pattern Terragrunt live/modules e' usato in tutti i 44 repository IaC SIAE.
```

**Quando usarlo:** Skill Flexible e reference. Giustifica scelte di design.

---

### 5. Reciprocity (Reciprocita')

**Principio:** Chi riceve qualcosa si sente in debito e tende a ricambiare.

**Applicazione DevForge:**
- La skill "regala" struttura, template, checklist
- "Usa questo template: ti fa risparmiare tempo"
- Reference files come risorse gratuite e immediate
- Esempio di output corretto gia' pronto

**Esempio:**
```
Usa il template pronto in reference/skill-template.md — risparmia 30 minuti di setup.
```

**Quando usarlo:** Skill con template e risorse. Aumenta l'adozione.

---

### 6. Liking (Simpatia)

**Principio:** Le persone sono influenzate da chi trovano simpatico o familiare.

**Applicazione DevForge:**
- Tono diretto ma non aggressivo
- Linguaggio italiano familiare nel contesto SIAE
- Empatia con le difficolta' reali: "Non sai come testare questa cosa? Chiedi."
- Humor controllato nel banner: "Il codice si forgia. Il developer cresce."

**Esempio:**
```
Stai pensando "salto il TDD solo questa volta"? Fermati. Quella e' razionalizzazione.
```

**Quando usarlo:** Tabelle anti-razionalizzazione. Tono fermo ma comprensivo.

---

### 7. Unity (Unita')

**Principio:** Le persone sono influenzate da chi appartiene al loro gruppo.

**Applicazione DevForge:**
- "Standard SIAE" come identita' di gruppo
- "Il tuo team", "Il nostro processo"
- Factory-specific: "Se sei nella Factory XYZ, usa..."
- Brand DevForge come identita' condivisa

**Esempio:**
```
In SIAE, il branch naming segue il pattern feature/{JIRA-ID}-descrizione.
Tutti i team seguono questa convenzione.
```

**Quando usarlo:** Quando la conformita' al gruppo e' la motivazione principale.

---

## Combinazioni Efficaci

### Per Skill Rigid (compliance massima)

```
Authority + Commitment + Scarcity
= Legge di Ferro + Checklist sequenziale + Nessuna eccezione
```

Efficacia: massima. Usata in siae-tdd, siae-verification, siae-debugging.

### Per Skill Flexible (adozione morbida)

```
Social Proof + Authority + Reciprocity
= "Pattern osservato in N repo" + Standard SIAE + Template pronto
```

Efficacia: alta per adozione volontaria. Usata in siae-architecture, siae-code-standards.

### Per Meta-Skill (orchestrazione)

```
Authority + Unity + Commitment
= Banner DevForge + "Il nostro processo" + Regola dell'1%
```

Efficacia: crea il framework mentale. Usata in using-devforge.

---

## Ricerca di Supporto

**Meincke et al. (2025)** — Studio sull'uso di principi di persuasione nel prompt engineering:
- Baseline (prompt generico): 33% compliance
- Con principi di persuasione strutturati: 72% compliance
- Incremento: +118%
- I principi piu' efficaci: Authority, Commitment, Scarcity

**Implicazione per DevForge:** ogni skill Rigid deve usare almeno Authority + Commitment + Scarcity.
Ogni skill Flexible deve usare almeno Social Proof + Authority.
