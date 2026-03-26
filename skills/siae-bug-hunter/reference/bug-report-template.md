# Bug Report Template — siae-bug-hunter

## Struttura Report Completo

```markdown
# Bug Hunter Report — {nome_repo}

**Data:** {YYYY-MM-DD HH:MM}
**Stack:** {framework/linguaggio rilevato}
**Repos scansionati:** {lista path/URL}
**File analizzati:** {N} file
**Moduli eseguiti:** M1, M2, M3, M4, M5

---

## Riepilogo

| Livello | Count |
|---|---|
| CONFIRMED | {N} |
| PROBABLE | {M} |
| SUSPECT | {K} (appendice) |

**Priorità immediata:** {titolo del primo bug CONFIRMED CRITICAL/HIGH}

---

## Bugs Confermati

{BUG-001 ... BUG-NNN — ordinati: CRITICAL → HIGH → MEDIUM → LOW}

---

## Bugs Probabili
{solo se $CONFIDENCE include PROBABLE}

---

## Appendice — Sospetti (review manuale)
{inclusa se $CONFIDENCE = CONFIRMED+PROBABLE o ALL — omessa solo se $CONFIDENCE = CONFIRMED}
```

---

## Template Singolo Bug

```markdown
---

## BUG-{NNN}: [{CONFIDENZA}] [{MODULO}]

### {VERBO} + {OGGETTO} + {CONTESTO}
> Il titolo deve descrivere l'azione concreta che fallisce. Max 12 parole.
> Es: "GET /api/users/{id} crasha su name=null senza null-check nel FE"
> Es: "Carrello mostra item ma API ha rifiutato il salvataggio (optimistic no-rollback)"
> Es: "Enum PENDING non renderizzato nel badge status dopo aggiornamento admin"

| Campo | Valore |
|---|---|
| **Confidenza** | CONFIRMED / PROBABLE / SUSPECT |
| **Severità** | CRITICAL / HIGH / MEDIUM / LOW |
| **Modulo** | M1-API / M2-Logic / M3-ErrorH / M4-Async / M5-DataVal |
| **File FE** | `src/pages/UserProfile.tsx:42` |
| **File BE** | `src/main/java/.../UserController.java:87` *(se applicabile)* |
| **File BFF** | `src/gateway/UserGateway.ts:15` *(se applicabile)* |

### Evidenza
```{linguaggio}
// Snippet LETTERALE dal codice — max 5 righe
// Annotare la riga critica con un commento ← BUG HERE
const name = response.data.user.name;  // ← riga 42: no null-check, response tipizzato any
```

### Impatto Utente
{Cosa vede o sperimenta l'utente in linguaggio naturale. Max 2 frasi.}
Es: "L'utente con profilo incompleto vede un crash 500 invece della pagina profilo.
     Il messaggio di errore non fornisce indicazioni su come risolvere."

### Precondizioni
- [ ] {stato del sistema verificabile — es. "Esiste almeno un utente senza campo email nel DB"}
- [ ] {autenticazione necessaria — es. "Utente autenticato come ruolo USER (non ADMIN)"}
- [ ] {dato di test disponibile — es. "Ambiente di test con ID utente 9007199254740993"}

### Passi per Riprodurre
1. {azione atomica con dato specifico — es. "Navigare a `http://localhost:3000/profile`"}
2. {azione atomica — es. "Aprire DevTools → tab Network"}
3. {azione atomica — es. "Cliccare su 'Modifica profilo'"}
4. {azione atomica — es. "Nel campo 'Email' inserire esattamente: `user@localhost` (senza TLD)"}
5. {azione atomica — es. "Cliccare 'Salva'"}
6. {cosa osservare — es. "Osservare: BE risponde HTTP 400 con body `{error: 'Invalid email'}`
    mentre FE non mostra alcun messaggio di errore"}

### Comportamento Atteso
{Descrizione breve del comportamento corretto}
Es: "Il FE mostra un messaggio di errore inline: 'Formato email non valido'"

### Comportamento Effettivo
{Descrizione di cosa succede realmente}
Es: "Il FE non mostra alcun feedback. La form appare inviata con successo ma il dato non è salvato."

### Fix Suggerito *(opzionale — solo se ovvio dal codice)*
```{linguaggio}
// Max 5 righe — solo il pattern corretto, non l'implementazione completa
const name = response.data?.user?.name ?? 'N/A';
```

---
```

---

## Guida Compilazione — Regole di Scrittura

### Titolo (obbligatorio)
- Formato: **VERBO + OGGETTO + CONTESTO**
- Il VERBO descrive cosa fa di sbagliato: "crasha", "mostra", "ignora", "tronca", "sovrascrive"
- L'OGGETTO è l'entità coinvolta: "il campo email", "la response API", "il carrello"
- Il CONTESTO specifica quando: "dopo navigazione rapida", "con profilo incompleto", "su input > 255 char"

### Evidenza (obbligatoria)
- Solo codice LETTERALE dal file, mai parafrasato
- Massimo 5 righe — mostra solo il punto critico
- Annota la riga problematica con `← BUG: spiegazione`

### Impatto Utente (obbligatorio)
- Scrivi dal punto di vista dell'utente, non del developer
- NON: "NullPointerException a riga 42"
- SÌ: "L'utente vede una pagina bianca senza spiegazione"

### Precondizioni (obbligatorie)
- Ogni precondizione con checkbox `[ ]`
- Devono essere **verificabili** — una query SQL, un URL, un ruolo utente
- NON: "Sistema in stato consistency" → troppo vago
- SÌ: "Tabella `users` contiene almeno un record con `email = null`"

### Passi per Riprodurre (obbligatori)
- 1 passo = 1 azione dell'utente (atomica)
- Il dato di test deve essere **specifico**: non "inserisci un valore invalido"
  ma "inserisci `' OR '1'='1' --`"
- L'ultimo passo dice COSA OSSERVARE (risposta HTTP, UI, console, network)
- Se il timing è critico: "Entro 200ms" / "Senza attendere"
- Se il test modifica stato persistente, aggiungere step di cleanup:
  "Cleanup: eseguire `DELETE FROM cart WHERE user_id = {test_user_id}`"

### Severità (obbligatoria)

| Livello | Criteri |
|---|---|
| **CRITICAL** | Crash applicativo, data loss irreversibile, security breach |
| **HIGH** | Feature inutilizzabile, stato UI incoerente, dato errato in output business |
| **MEDIUM** | Campo mostra valore sbagliato (non critico), UX degradata senza crash |
| **LOW** | Cosmetic issue, comportamento non documentato ma non dannoso |

---

## Esempi di Titoli Corretti vs Errati

| Errato | Corretto |
|---|---|
| "NullPointerException in UserService" | "GET /api/users/{id} crasha se l'utente non ha email impostata" |
| "Manca validazione email" | "Form accetta `user@localhost` (no TLD) che BE rifiuta con 400 non gestito" |
| "Race condition in useEffect" | "Navigazione rapida tra pagine mostra dati della pagina precedente" |
| "Float per currency" | "Totale fattura con 100+ prodotti accumula errore centesimale (IEEE754)" |
| "Missing @Transactional" | "Ordine con item fallito lascia ordine orfano nel DB senza items" |
