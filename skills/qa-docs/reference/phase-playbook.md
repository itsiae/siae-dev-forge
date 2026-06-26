# Phase Playbook — Regole operative per fase

---

## Fase 1 — Domande di apertura

Se l'utente non ha indicato un canale specifico, chiedi:
> "Come vuoi fornire il perimetro del progetto?
> 1. **JIRA** — dimmi uno o più issue key (es. DMND0006339)
> 2. **Chat** — descrivimi il progetto a parole
> 3. **Documenti** — carica i file di requisiti/specifica (PDF, DOCX, XLSX...)"

Ricorda che i canali sono combinabili: es. un issue JIRA + un PDF di specifiche + chiarimenti in chat.

---

## Fase 2 — Regole di analisi

### Obiettivo del progetto
- Stile prosa, concetti chiave in **grassetto**
- Struttura: cosa introduce il progetto, come funziona il nuovo flusso, quali sistemi coinvolge
- Chiudi con riferimento ai sistemi impattati

### Classificazione SmartArt (3 colonne)

| Colonna | Definizione | Esempi tipici SIAE |
|---|---|---|
| **Piattaforme** | Sistemi già esistenti che partecipano ma non ricevono modifiche sostanziali | SPORT, Portale Utente |
| **Piattaforme Modificate** | Sistemi che ricevono effettive modifiche / nuovi componenti | Mulesoft/ESB, Sistema Incassi, Cruscotto |
| **Sistemi Impattati** | Sistemi terzi o downstream che ricevono impatti indiretti | Sistema Pagamenti, Banche, CRM |

**Slot disponibili nel template**: 2 Piattaforme, 1 Sistemi Impattati, 5 Piattaforme Modificate (totale 8).
Se le voci da inserire eccedono gli slot → combina voci correlate (es. "Mule + ESB") o segnala all'utente.
Se le voci sono meno degli slot → lascia slot vuoti (`""`).

### Perimetro di Test
- Numerazione: 1. 2. 3. ... n.
- Ogni macro-scenario ha:
  - Un titolo descrittivo breve
  - Sotto-punti puntati con i punti di verifica specifici
  - Usa verbi di verifica: "verifica che…", "testa che…", "controlla che…"
- Tipici macro-scenari SIAE: Accesso e profilazione, Flusso principale, Integrazioni, Tracciabilità, Access Control, Edge Case
- **Granularità target**: **4–8 macro-scenari**. Meno di 4 è troppo generico (la PRA perde potere discriminante); più di 8 diluisce la prioritizzazione. Raggruppa scenari con lo stesso profilo di rischio in uno solo; separa funzionalità con rischi distinti (es. flusso di incasso separato da rendicontazione, anche se sullo stesso sistema).

### Obiettivi del test — come derivarli

Gli `obiettivi_test` nel JSON NON sono una copia dei macro-scenari del perimetro. Seguono questa regola:

1. **Per ogni livello di test presente** (T0, T1, T2), scrivi un obiettivo che esprime l'intento complessivo di quel livello applicato al progetto.
2. **Per macro-scenari ad alto rischio** (criticità Bloccante o Alta nella PRA), aggiungi un obiettivo specifico che nomina esplicitamente il rischio da mitigare.
3. **Struttura dell'obiettivo**: verbo di verifica + oggetto + livello. Esempi:
   - "Verificare la correttezza del calcolo royalties su tutti i casi d'uso previsti nel perimetro (T0)"
   - "Validare l'integrazione SPORT↔ESB sul flusso di emissione licenza, inclusi i casi di errore (T1)"
   - "Confermare con la BU Finance l'aderenza ai requisiti di accettazione del flusso principale (T2)"
   - "Garantire che i dati di rendicontazione prodotti siano coerenti con i valori attesi (T0/T1)"

**NON usare**: frasi generiche come "Verificare che tutto funzioni correttamente" o duplicati del titolo del macro-scenario.

### Livelli T0/T1/T2

| Livello | Tipo | Owner | Governance |
|---|---|---|---|
| T0 | Unit Test / System Test | Fornitore | QA |
| T1 | Integration Test | Fornitore | QA |
| T2 | UAT | BU/QA/Fornitore | QA |

Dettaglio T0: indica il sistema/modulo testato (es. "SPORT backend").
Dettaglio T1: indica l'integrazione specifica (es. "SPORT↔Mulesoft").
Dettaglio T2: indica chi conduce la validazione (es. "BU Finance + team QA").

### GANTT
- NON inventare date o sprint
- Se desumibili dall'intake (es. "Sprint 3 di Maggio") → inserisci con nota "[fonte: ...]"
- Resto: struttura `DA CONFERMARE`
- Formato entry: `{sprint: "Sprint N", date: "DD/MM/YYYY - DD/MM/YYYY", pct: 0}`

### Frequenza d'uso — come determinarla per la PRA

Quando valuti la frequenza d'uso di ogni macro-scenario (campo `frequenza_uso` in `pra_obiettivi`), cerca nei dati di intake:
- Volumi espliciti: "~500 licenze/giorno", "batch notturno con 10k record", "50 utenti concorrenti"
- Tipo di funzionalità: self-service licenziatari → Molto Alta; dashboard autori → Alta; report mensile → Media; configurazione → Bassa
- Periodicità: continuo/giornaliero → Molto Alta/Alta; mensile/trimestrale → Media; annuale/emergenziale → Bassa

Documenta sempre la fonte della frequenza nel campo `motivazione` della PRA. Es: "frequenza: Molto Alta — portale self-service con ~N operazioni/giorno da JIRA DMND-XXX" oppure "frequenza: Media — report trimestrale, stimata per tipo funzionale".

### Criticità e frequenza — Checklist decisionale per pra_obiettivi

Per ogni macro-scenario, esegui questi controlli **nell'ordine** prima di assegnare criticità e frequenza.

**Step 1 — Critica alta: verificare i 4 gate Bloccante**
Assegna Bloccante **solo se** almeno uno di questi è vero per questo specifico scenario:
- [ ] Un difetto blocca fisicamente l'incasso di diritti o il pagamento di royalties (es. PagoPA non funziona, batch royalties errato)
- [ ] Un difetto produce violazione normativa certa e immediata (GDPR art. 83, Direttiva Copyright UE, AML, obbligo rendicontazione MEF/AGCOM)
- [ ] Un difetto blocca l'emissione di licenze obbligatorie
- [ ] Un difetto espone SIAE a sanzione da autorità di vigilanza nella prossima scadenza

Se nessuno dei 4 si applica → considera Alta. La motivazione "potrebbe impattare autori" o "sistema critico" da sola non basta per Bloccante.

**Step 2 — Operazione una tantum: non abbassare la criticità per la bassa frequenza**
Se lo scenario è raro (firma mandato, migrazione, apertura esercizio fiscale) ma un errore ha conseguenze legali irreversibili → mantieni Bloccante. Scrivi nella motivazione: "frequenza Bassa ma criticità Bloccante — un singolo errore ha conseguenze legali/economiche indipendenti dalla cadenza". La formula produce `Alta` come rischio calcolato: è corretto.

**Step 3 — Interfaccia di gestione: non ereditare la criticità del sistema**
Se lo scenario riguarda una dashboard di monitoring, un form di configurazione, o una funzionalità di revisione (backoffice audit), verifica:
- Esiste un workaround operativo alternativo (accesso diretto a DB, tool alternativo, notifica email)? → Media
- L'assenza della funzionalità blocca qualcuno dal lavorare senza alternative? → Alta
- L'assenza blocca direttamente incassi/compliance? → Bloccante

**Step 4 — Frequenza: usare la fonte, non il giudizio soggettivo**
- Volume esplicito nel brief → usa quello, documenta in `motivazione`
- Tipo funzionale senza volume → usa i proxy dalla tabella in `pra-structure.md`
- Batch: usa la cadenza effettiva (giornaliero → Molto Alta; mensile → Media; annuale → Bassa)
- Se nessun dato disponibile → usa il proxy e scrivi "stimata per tipo funzionale — DA CONFERMARE con PM"

**Step 5 — Sanity check distribuzione**
Prima di chiudere pra_obiettivi, verifica:
- Almeno 1 scenario Media o Bassa (quasi ogni progetto ne ha almeno 1 — eccezione: progetti con perimetro 100% core finanziario)
- Bloccante ≤ 5/8 scenari — se superiore, rivaluta quelli con frequenza più bassa
- Almeno 1 scenario con Molto Alta o Alta frequenza — rarissimo che un progetto SIAE non abbia nulla ad alta cadenza
- Tutti i `req_nrt` / `req_performance` = "Si" hanno corrispondenza esplicita nel brief

### Performance test / NRT / Test Automatici
- Default «Non previsti.» se non menzionati nei requisiti
- Attiva se: requisiti di carico, soglie di risposta, automazione CI/CD espliciti

---

## Fase 3 — Gate questions

### Approvazione analisi (3a)
Mostra l'analisi in blocchi leggibili. Poi chiedi:
> "L'analisi funzionale è corretta?
> 1. **Approva** → confermo i sistemi impattati e passo al GANTT
> 2. **Modifica** → dimmi cosa correggere (puoi anche caricare un documento con le correzioni)
> 3. **Rifai** → torno all'analisi da capo"

### Conferma sistemi impattati (3b)
Mostra sempre questo blocco con evidenza dei punti incerti:
```
SmartArt "Piattaforme" — BOZZA (2+1+5 slot):

Piattaforme (slot 1-2):
  ✓ [certezza alta] SPORT
  ? [DA CONFERMARE] <voce incerta>

Sistemi Impattati (slot 1):
  ✓ Sistema Pagamenti

Piattaforme Modificate (slot 1-5):
  ✓ Mule
  ✓ Sistema Incassi
  ○ [vuoto]
  ○ [vuoto]
  ○ [vuoto]

Touch point / integrazioni identificate:
  - SPORT → Mulesoft (refreshQuote sincrono)
  - ...
```

### GANTT (3c)
> "Puoi fornirmi sprint, date previste e percentuale di avanzamento?
> Se non sono ancora definiti, inserirò 'DA CONFERMARE' — non inventarò date."

---

## Fase 4 — Discovery GitHub

Regole:
- Non inventare mai nomi di repository o servizi
- Marca «DA CONFERMARE» qualunque repo/servizio non verificato con l'utente
- Aggiorna SOLO i contenuti già esistenti in 1.1 (SmartArt) e 1.7 (GANTT)
- In caso di discrepanza con quanto confermato in Fase 3, segnala esplicitamente prima di sovrascrivere

---

## Fase 6 — Checklist pre-generazione

Prima di eseguire `build_mtp.py`, verifica:
- [ ] `analisi_approvata: true`
- [ ] `sistemi_impattati_confermati: true`
- [ ] JSON `mtp_data.json` assemblato con tutti i campi obbligatori
- [ ] Template presente: `~/.claude/skills/qa-docs/assets/MTP_template.docx`
- [ ] python-docx installato (`python3 -c "import docx; print('OK')"`)

Se uno dei check fallisce, risolvi prima di procedere.

---

## Gestione punti DA CONFERMARE

Mantieni una lista `punti_da_confermare[]` aggiornata:
- Aggiungi un item ogni volta che usi «DA CONFERMARE» nel documento
- Includi: quale sezione, quale informazione, quale fonte sarebbe necessaria
- Mostra la lista completa nel report finale (Fase 6.5)

**Comportamento nel .docx generato**: i marker «DA CONFIRMARE [...]» rimangono come testo visibile nel documento. `build_mtp.py` non li rimuove né li evidenzia automaticamente. Prima della distribuzione ufficiale del MTP, il responsabile QA deve completare o eliminare ogni item dalla lista.

**Struttura item consigliata**:
```yaml
- sezione: "1.7 GANTT"
  informazione: "Sprint 2 — date di inizio/fine"
  fonte_necessaria: "Piano di progetto approvato dal PM"
  priorità: "Alta"  # Alta se bloccante per l'approvazione del documento
```

**Regola per la PRA**: se un macro-scenario ha criticità o frequenza marcate «DA CONFERMARE», NON produrre la PRA finché non sono definite. Valori placeholder in pra_obiettivi producono un documento non audit-proof.
