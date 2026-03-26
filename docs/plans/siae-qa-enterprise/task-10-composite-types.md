# Task 10 — Primary Type + Secondary Tags [PENDING]

**File:** `skills/siae-qa/SKILL.md`
**Sezione:** "Phase 0 — Smart Req Typing" → aggiungere sezione 0d
**Cluster:** C — Output enterprise

---

## Obiettivo

Gestire story multi-dominio con Primary Type + Secondary Tags:
- 1 tree completo per il tipo primario
- 1-2 domande di triage per ogni tag secondario
- Avviso e raccomandazione split se 3+ tag secondari

---

## Step 1 — Aggiungi sezione 0d in SKILL.md

Leggi `skills/siae-qa/SKILL.md`. Individua la sezione `### 0c — Lancia le domande del tree contestuale`.

Aggiungi DOPO 0c:

```markdown
### 0d — Gestione story multi-dominio (Primary Type + Secondary Tags)

Dopo l'inferenza del tipo in 0a, controlla se la story ha segnali convergenti su più tipi.

**Algoritmo:**
1. Calcola lo score per ogni tipo (numero di segnali matchati nel testo della story)
2. Il tipo con score più alto = **tipo primario** (HIGH confidence se 2+ segnali forti)
3. Ogni altro tipo con score ≥ 1 = **tag secondario**
4. Aggiorna la Req Profile Card con la sezione Tag secondari

**Soglie:**
- **0 tag secondari** → workflow standard (un solo tipo)
- **1-2 tag secondari** → inietta domande aggiuntive dopo il tree primario (vedi tabella)
- **3+ tag secondari** → emetti avviso SCOPE COMPOSITO e raccomanda split story

**Avviso SCOPE COMPOSITO:**
```
⚠️ SCOPE COMPOSITO: questa story copre {N} domini ({lista tipi}).
Raccomando di splitarla in {N/2} story atomiche prima di procedere con il QA.
Se non è possibile (constraint di sprint/deadline), procedo con:
  - Tree completo: {tipo primario}
  - Domande aggiuntive ({N-1} tag secondari × 2 domande = max 4 domande extra)
Vuoi procedere lo stesso o preferisci splitare la story?
```

**Tabella domande di triage secondario (2 per tag):**

| Tag secondario | Domanda 1 | Domanda 2 |
|----------------|-----------|-----------|
| [FE] | "Il file viene validato lato client prima dell'invio? Cosa mostra l'UI se il file è troppo grande o formato errato?" | "Ci sono stati di caricamento/errore da mostrare all'utente durante questa operazione?" |
| [BE] | "L'endpoint chiamato da questa feature è già documentato in OpenAPI? Ha validazioni Bean Validation da considerare?" | "L'operazione è idempotente? Cosa succede se viene chiamata due volte?" |
| [Integration REST] | "Cosa succede se il servizio esterno non risponde? C'è un fallback o comportamento degradato?" | "Il timeout è configurato adeguatamente per questa chiamata?" |
| [Integration Event] | "La notifica/evento viene inviato anche se il processing fallisce parzialmente?" | "C'è un meccanismo di retry per delivery fallito dell'evento?" |
| [Auth] | "L'operazione composta richiede che il token sia ancora valido per tutta la durata?" | "Ci sono ruoli diversi che vedono subset diversi di dati in questa feature?" |
| [Notification] | "La notifica viene inviata in doppio se l'operazione è ritentata?" | "L'utente può fare opt-out da questa specifica notifica?" |
| [Batch] | "Se questa operazione viene triggerata due volte in rapida successione, è idempotente?" | "C'è un lock per prevenire esecuzioni concorrenti?" |
| [ETL] | "I dati prodotti da questa feature vengono consumati da una pipeline ETL downstream?" | "Il formato dei dati scritti è compatibile con lo schema del layer ETL?" |
| [DB] | "Questa feature implica una migration di schema? È stata pianificata la strategia zero-downtime?" | "I servizi che leggono questa tabella sono backward compatible con il nuovo schema?" |
| [File Processing] | "Il file viene processato sincronamente o asincrono con polling/notifica?" | "C'è una policy di retry se il file processing fallisce?" |
| [Report] | "Il report è generato sincrono o asincrono rispetto all'operazione principale?" | "Il volume del report è bounded o potenzialmente illimitato?" |
| [Feature Flag] | "Questa feature è protetta da un flag? Cosa vede l'utente con flag OFF?" | "Il rollback del flag è data-safe se la feature ha scritto dati?" |

**Req Profile Card aggiornata con tag secondari:**

```
REQ PROFILE (multi-dominio):
  Tipo primario:      {tipo}   [{HIGH/MEDIUM} — {N} segnali]
  Tag secondari:      [{tipo}] [{MEDIUM/LOW} — {N} segnali]
                      [{tipo}] [{MEDIUM/LOW} — {N} segnali]
  Segnali primari:    {lista segnali matchati per tipo primario}
  Segnali secondari:  {segnale} → [{tipo}]
  Note composito:     {N} tag — {N*2} domande aggiuntive iniettate dopo tree primario
```
```

---

## Step 2 — Aggiorna VINCOLI NON NEGOZIABILI in SKILL.md

Individua la sezione `## VINCOLI NON NEGOZIABILI`. Aggiungi alla lista:

```markdown
9. **Primary Type + Secondary Tags obbligatorio su story multi-segnale** — se la story
   ha segnali convergenti su 2+ tipi distinti, Phase 0d deve essere eseguita.
   Una story con segnali per BE + Auth + Integration non può essere processata
   come puro BE senza considerare i tag secondari.
```

---

## Step 3 — Aggiorna Anti-Razionalizzazione in SKILL.md

Nella tabella Anti-Razionalizzazione, aggiungi:

```markdown
| "Ha solo segnali BE, è chiaramente solo Backend" | La story può avere segnali Auth o Integration impliciti non evidenti dal solo titolo. Esegui 0d prima di concludere che è un tipo puro. |
| "Il tag secondario aggiunge solo 2 domande, non vale" | Le 2 domande di triage secondario producono in media 3-4 scenari aggiuntivi. Su 20 story/sprint = 60-80 TC che altrimenti non esistono. |
```

---

## Step 4 — Commit

```bash
git add skills/siae-qa/SKILL.md
git commit -m "feat(siae-qa): add Phase 0d composite type handling with Primary+Secondary Tags"
```
