# Task 2 — Option Zero Gate in siae-brainstorming

**Stato:** [PENDING]
**Dipendenze:** nessuna
**File coinvolti:**
- `skills/siae-brainstorming/SKILL.md`

---

## Step 1 — Inserisci Step 3b

Apri `skills/siae-brainstorming/SKILL.md`.
Trova la fine di `### 3. Presenta inferenze + domande mirate` — il punto e':

```
**Se tutto e' HIGH e l'utente conferma**, procedi direttamente a Step 4 (Approcci).
Questo elimina le 5-10 domande ripetitive sui dati gia' nel codice.
```

Inserisci **dopo** quel paragrafo e **prima di** `### 4. Proponi 2-3 approcci`:

```markdown
### 3b. Option Zero Gate

Prima di proporre soluzioni che richiedono codice, verifica se il problema
si risolve con una modifica di configurazione, infrastruttura, o processo.

**Checklist Option Zero:**

| # | Verifica | Esempio SIAE |
|---|----------|-------------|
| 1 | AWS Parameter Store / SSM | Cambiare un valore in parameter store risolve? |
| 2 | Terraform variables / tfvars | Basta un tfvar diverso per ambiente? |
| 3 | Feature flag esistente | C'e' gia' un flag che abilita/disabilita questo? |
| 4 | Environment variable | Una env var risolve senza toccare codice? |
| 5 | Ticket DevOps / infra | Basta chiedere al team DevOps un cambio infra? |
| 6 | Servizio/libreria esistente | Un altro repo SIAE fa gia' questo? Riusalo. |
| 7 | Config applicativa | application.yml, .env, config file risolvono? |

**Se Option Zero si applica:**

Presenta la soluzione config/infra, chiedi conferma, e chiudi il brainstorming
senza design doc. Non serve piano implementativo per un cambio config.

Emetti checkpoint:
```
[BRAINSTORM:OPTION-ZERO] Soluzione senza codice identificata
  Tipo: {config/infra/processo}
  Azione: {descrizione}
  Motivo: {perche' non serve codice}
```

**Se Option Zero non si applica:**

Documenta brevemente perche' ("Verificato: non esiste parameter store per X,
il comportamento richiede logica nuova") e procedi a Step 4.
```

## Step 2 — Aggiorna il flowchart graphviz

Nella sezione `## Flusso del Processo`, aggiungi il nodo `option_zero` nel grafo.

Dopo il nodo `ask` e prima di `approaches`, aggiungi:

```dot
    option_zero [label="3b. Option Zero?\nconfig/infra basta?", shape=diamond, fillcolor="#fff3cd"];
```

Modifica le connessioni:
- `need_questions -> approaches` diventa `need_questions -> option_zero`
- `ask -> approaches` diventa `ask -> option_zero`
- Aggiungi: `option_zero -> approaches [label="no, serve codice"];`
- Aggiungi: `option_zero -> doc [label="si, chiudi\nsenza design", style=dashed];`

## Step 3 — Aggiungi checkpoint strutturato

Nella sezione `## Output Strutturato Obbligatorio — Checkpoint`, dopo il checkpoint
`[BRAINSTORM:SCOPE]` e prima di `[BRAINSTORM:DESIGN]`, aggiungi:

```markdown
**Dopo Option Zero Gate (Step 3b):**
```
[BRAINSTORM:OPTION-ZERO] Valutazione senza codice
  Applicabile: {SI/NO}
  Se SI — Tipo: {config/infra/processo}
  Se NO — Motivo: {perche' serve codice}
```
```

## Step 4 — Aggiungi riga anti-razionalizzazione

Nella sezione `## Tabella Anti-Razionalizzazione`, aggiungi la riga:

```
| "Serve per forza codice nuovo" | Nel 30% dei casi, una config change basta. Verifica Option Zero prima. |
```

## Step 5 — Verifica

```bash
grep -c "Option Zero" skills/siae-brainstorming/SKILL.md
```
Output atteso: almeno 5 occorrenze (Step 3b titolo, checklist, flowchart nodo, checkpoint, anti-razionalizzazione).

## Step 6 — Commit

```bash
git add skills/siae-brainstorming/SKILL.md
git commit -m "feat(skills): add Option Zero gate to brainstorming (#878)"
```
