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
- Mostra la lista completa nel report finale (Fase 6.4)
