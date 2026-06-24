---
name: qa-docs
description: >
  Genera il Master Test Plan (MTP) in formato .docx e la Product Risk Analysis (PRA) in formato
  .xlsx conformi ai template SIAE, attraverso un flusso interattivo a 6 fasi.
  Orchestra: intake perimetro (3 canali: JIRA/chat/documenti), analisi funzionale,
  conferma sistemi impattati, discovery GitHub opzionale, produzione .docx e .xlsx via patch template.
  Lingua: italiano.
---

# QA-DOCS — Master Test Plan + Product Risk Analysis SIAE

> **Orchestratore**: questo file governa le 6 fasi. Dettagli strutturali → `reference/template-structure.md`.
> Regole operative → `reference/phase-playbook.md`. Canali intake → `reference/intake-channels.md`.

> ⚠️ **Attivazione**: invocare SOLO tramite il comando esplicito `/qa-docs` — non auto-triggerare su keyword come "Master Test Plan", "MTP", "piano di test", ecc.

**Lingua**: tutta l'interazione con l'utente e il contenuto del documento sono in italiano.

---

## STATO DI SESSIONE

Mantieni e aggiorna questo oggetto ad ogni turno:

```yaml
sessione:
  codice: ""                        # es. DMND0006339
  titolo: ""
  autore: ""
  versione: "1.0"
  data: ""                          # YYYY-MM-DD

intake_grezzo:
  jira: []                          # issue key + contenuto estratto
  chat: ""
  documenti: []                     # {nome_file, contenuto_estratto}

analisi:
  obiettivo_progetto: ""
  piattaforme: []
  piattaforme_modificate: []
  sistemi_impattati: []
  touch_point: []
  sistemi_impattati_confermati: false
  perimetro_progetto: ""
  perimetro_test: []                # [{num, titolo, punti:[]}]
  criteri_accettazione: []
  out_of_scope: []
  obiettivi_test: []
  livelli: []                       # [{livello, descrizione, dettaglio, owner, governance}]
  performance_test: "Non previsti."
  nrt: "Non previsti."
  test_automatici: "Non previsti."
  gantt: []                         # [{sprint, date, pct}] — solo se fornito dall'utente
  rischi: []

analisi_approvata: false

github:
  saltato: false
  repo: []
  servizi: []
  note: ""
  confermato: false

punti_da_confermare: []
```

---

## FASE 1 — Intake del perimetro

Invoca il **MODULO INTAKE** (→ `reference/intake-channels.md`).

Presenta i **3 canali** e lascia che l'utente ne scelga uno o più (combinabili):
- **Canale 1 — JIRA**: uno o più issue key (es. DMND0006339)
- **Canale 2 — Chat**: descrizione testuale / requisiti incollati
- **Canale 3 — Documenti**: file caricati (.docx/.pdf/.xlsx/.pptx/.txt/.md)

Applica i pre-check e fallback descritti in `reference/intake-channels.md`.

**Output di Fase 1**: `intake_grezzo` popolato con provenienza tracciata per ogni informazione.

---

## FASE 2 — Analisi funzionale (fonte primaria dei sistemi impattati)

A partire da `intake_grezzo`, produci:

1. **Obiettivo del progetto** — prosa con concetti chiave in grassetto
2. **Piattaforme / Piattaforme Modificate / Sistemi Impattati / touch point** — SEMPRE prodotti in questa fase dall'analisi funzionale. Dove certo → inserisci; dove dedotto o incerto → marca «DA CONFERMARE [fonte: ...]»
3. **Perimetro di Progetto** — prosa sintetica
4. **Perimetro di Test** — elenco numerato macro-scenari con sotto-punti puntati
   **Granularità**: punta a **4–8 macro-scenari**. Meno di 4 è troppo generico e perde valore nella PRA; più di 8 diluisce la prioritizzazione. Raggruppa scenari strettamente correlati in uno solo; separa funzionalità con profili di rischio distinti.
5. **Criteri di accettazione** per area
6. **Out of Scope** — esclusioni
7. **Obiettivi del test** — checklist stile MTP
   **Regola di derivazione**: gli `obiettivi_test` NON sono una copia dei macro-scenari. Esprimono l'*intento di verifica* ad alto livello: cosa si garantisce (correttezza, integrità, sicurezza, performance) e per quale livello (T0/T1/T2). Esempi: "Verificare la correttezza del calcolo royalties su tutti i casi d'uso principali (T0)", "Validare l'integrazione SPORT↔ESB su flusso emissione licenze (T1)", "Confermare l'aderenza ai requisiti con la BU di riferimento (T2)". Tipicamente 1 obiettivo per macro-scenario + 1 obiettivo trasversale per livello di test.
8. **Livelli di test** — tabella T0/T1/T2 (Livello | Descrizione | Dettaglio | Owner | Governance)
9. **Performance test / NRT / Test Automatici** — default «Non previsti.» se non desumibili
10. **GANTT** — struttura compilabile; popola SOLO ciò che emerge dall'intake; lascia il resto «DA CONFERMARE»
11. **Rischi/Problemi/Azioni/Decisioni** — se desumibili

Non usare placeholder vuoti: deduci con criterio, marca esplicitamente i gap.

---

## FASE 3 — Gate di approvazione — BLOCCANTE

Presenta l'analisi in forma leggibile (in chat, non nel docx ancora). Il gate copre **3 conferme contestuali**:

### 3a — Approvazione analisi funzionale
Mostra: obiettivo, perimetri, macro-scenari, livelli, performance/NRT/UAT, out of scope.

### 3b — Conferma sistemi impattati e touch point
Mostra la bozza con i nodi SmartArt proposti:
- Piattaforme: [lista]
- Piattaforme Modificate: [lista]
- Sistemi Impattati: [lista]
- Touch point/integrazioni: [lista]

Evidenzia i punti «DA CONFERMARE». Chiedi conferma/correzione via MODULO INTAKE.
Aggiorna `sistemi_impattati_confermati: true` quando confermato.

> **Nota**: il template SmartArt ha 8 slot contenuto (2 Piattaforme + 1 Sistemi Impattati + 5 Piattaforme Modificate).
> Se il numero di voci da inserire differisce dagli slot disponibili, segnalalo e chiedi come adattare.

### 3c — Dati GANTT
Chiedi esplicitamente sprint, date e % mancanti. Se l'utente non li fornisce, lascia struttura «DA CONFERMARE». Non inventare mai date.

### Opzioni gate
Chiedi una delle tre:
1. **Approva** → Fase 4
2. **Modifica** → correggi via MODULO INTAKE e ripresenta
3. **Rifai** → torna a Fase 2

**NON avanzare senza risposta esplicita. `analisi_approvata` deve essere `true` prima di proseguire.**

---

## FASE 4 — Discovery GitHub (OPZIONALE, SALTABILE, SOLA VALIDAZIONE)

> I sistemi impattati sono già stati prodotti in Fase 2 e confermati in Fase 3. GitHub è solo
> validazione/arricchimento tecnico. Saltando questa fase il documento non perde affidabilità.

Chiedi all'utente: **(a) saltare**, **(b) fornire manualmente repo/servizi**, o **(c) discovery automatica**.

### Se (c) — discovery automatica:
Pre-check (fermati al primo successo):
```bash
gh auth status 2>/dev/null && echo "gh OK"
echo "GITHUB_TOKEN: ${GITHUB_TOKEN:+presente}"
git remote -v 2>/dev/null | head -3
```
- `gh` disponibile → usa `gh repo list`, `gh search repos`
- Solo token → GitHub REST API
- Nessun accesso → informa, proponi (a) o (b)

**Destinazione esiti**: aggiorna solo i contenuti già esistenti di 1.1 (SmartArt piattaforme) e 1.7 (GANTT).
Non sovrascrivere silenziosamente voci già confermate: segnala discrepanze come «DA CONFERMARE».
Non creare sezioni nuove.

Se scelta (a), imposta `github.saltato: true` e salta direttamente a Fase 6.

---

## FASE 5 — Gate GitHub — BLOCCANTE solo se Fase 4 eseguita

Se `github.saltato: true` → salta a Fase 6 direttamente.

Altrimenti presenta repo/servizi individuati, mappatura su 1.1/1.7, eventuali discrepanze.

Chiedi:
1. **Completo** → Fase 6
2. **Da integrare** → raccogli via MODULO INTAKE e ripresenta

---

## FASE 6 — Produzione .docx (PERCORSO UNICO: PATCH DEL TEMPLATE)

### 6.1 — Assembla JSON strutturato

Costruisci `mtp_data.json`:
```json
{
  "meta": {"codice": "...", "titolo": "...", "autore": "...", "versione": "1.0", "data": "..."},
  "obiettivo_progetto": "...",
  "piattaforme": ["SPORT"],
  "piattaforme_modificate": ["Mule", "Sistema Incassi"],
  "sistemi_impattati": ["Sistema Pagamenti"],
  "perimetro_progetto": "...",
  "perimetro_test": [{"num": 1, "titolo": "...", "punti": ["..."]}],
  "criteri_accettazione": [
    {"area": "nome macro-scenario", "criteri": ["Criterio di accettazione 1", "Criterio 2"]}
  ],
  "obiettivi_test": [
    "Verificare la correttezza del flusso principale su tutti i casi d'uso previsti (T0)",
    "Validare le integrazioni con i sistemi downstream (T1)",
    "Confermare l'aderenza ai requisiti con la BU di riferimento (T2)"
  ],
  "livelli": [
    {"livello": "T0", "descrizione": "Unit Test/System Test", "dettaglio": "...", "owner": "Fornitore", "governance": "QA"},
    {"livello": "T1", "descrizione": "Integration Test", "dettaglio": "...", "owner": "Fornitore", "governance": "QA"},
    {"livello": "T2", "descrizione": "UAT", "dettaglio": "...", "owner": "BU/QA/Fornitore", "governance": "QA"}
  ],
  "performance_test": "Non previsti.",
  "nrt": "Non previsti.",
  "test_automatici": "Non previsti.",
  "gantt": [],
  "out_of_scope": ["..."],
  "rischi": [
    {"rischio": "...", "probabilita": "Media", "impatto": "Alto", "mitigazione": "...", "owner": "QA"}
  ]
}
```

> **Livelli opzionali**: ometti dalla lista un livello se non applicabile al progetto (es. nessuna riga T2 per un progetto puramente tecnico senza UAT). `build_mtp.py` genera solo le righe presenti nell'array. Non inserire righe con valori vuoti o "N/A".

> **`criteri_accettazione`**: raccolti in Fase 2, restano nel JSON per riferimento. `build_mtp.py` non li scrive nel .docx (sezione non presente nel template MTP); sono disponibili per il team QA come allegato all'analisi.

### 6.2 — Esegui build_mtp.py

```bash
python3 ~/.claude/skills/qa-docs/scripts/build_mtp.py mtp_data.json output_dir/
```

> **Policy marker DA CONFERMARE**: i placeholder «DA CONFERMARE [...]» rimangono nel .docx come testo visibile — `build_mtp.py` non li rimuove né li evidenzia automaticamente. La lista `punti_da_confermare[]` mostrata in Fase 6.5 è l'inventario di tutto ciò che va completato prima della distribuzione ufficiale del documento.

### 6.3 — Esegui build_pra.py

```bash
python3 ~/.claude/skills/qa-docs/scripts/build_pra.py mtp_data.json output_dir/
```

Output: `PRA_-_<CODICE>.xlsx`

Verifica:
- Foglio "Obiettivi del Test": righe dati da R5, colonna I con formula `=IF(B{R}=...` dove `{R}` è il numero di riga corretto per ogni riga (R5, R6, R7...) — non valore statico, non formula con riga fissa
- Fogli "Matrice Rischio" e "Tabelle": **invariati** — `build_pra.py` scrive solo su Copertina R10F, Informazioni R6, Obiettivi R5+, Piano R2+
- Copertina R10 F e Informazioni R6 compilati

**Passo 6.3b — Diff check cardinalità (obbligatorio prima di produrre il file):**
```
len(perimetro_test) == N scenari
len(pra_obiettivi) == N scenari  ← deve essere uguale
```
Se diversi: mostra il diff in chat (quali scenari MTP mancano dalla PRA o viceversa) e chiedi conferma prima di procedere.

**Struttura `pra_obiettivi`** (aggiungi al JSON in 6.1 — un entry per ogni macro-scenario, stessa cardinalità di `perimetro_test`):
```json
"pra_obiettivi": [
  {
    "obiettivo": "Flusso principale — emissione licenza",
    "criticita": "Bloccante",
    "fattore_rischio": "B-03 Perdita di incassi",
    "motivazione": "Blocco dell'emissione licenze impatta direttamente gli incassi SIAE — frequenza: Molto Alta su ~N licenze/giorno",
    "frequenza_uso": "Molto Alta",
    "req_nrt": "No",
    "req_performance": "No",
    "req_e2e_uat": "Si"
  },
  {
    "obiettivo": "Integrazione ESB/Mulesoft",
    "criticita": "Alta",
    "fattore_rischio": "T-01 Interfacciamento ESB/Mulesoft",
    "motivazione": "Regressione sull'integrazione ESB blocca tutti i flussi downstream",
    "frequenza_uso": "Alta",
    "req_nrt": "No",
    "req_performance": "No",
    "req_e2e_uat": "No"
  },
  {
    "obiettivo": "Reportistica e rendicontazione",
    "criticita": "Media",
    "fattore_rischio": "Q-10 Reportistica e rendicontazione",
    "motivazione": "Errori nei report hanno impatto differito — non bloccano gli incassi ma richiedono correzione manuale",
    "frequenza_uso": "Media",
    "req_nrt": "No",
    "req_performance": "No",
    "req_e2e_uat": "Si"
  }
]
```
Valori criticità: `Bassa / Media / Alta / Bloccante` (vedi rubrica → `reference/pra-structure.md`)
Valori frequenza: `Bassa / Media / Alta / Molto Alta` (vedi criteri → `reference/pra-structure.md`)
Fattori di rischio: codici B-xx / T-xx / Q-xx con nome breve (vedi tassonomia SIAE → `reference/pra-structure.md`)

**Regola cardinalità**: `len(pra_obiettivi)` deve essere uguale a `len(perimetro_test)`. Verifica prima di produrre il file.

**Derivazione req_nrt / req_performance / req_e2e_uat dal JSON MTP (obbligatorio):**
- Leggi `performance_test` dal JSON: se ≠ `"Non previsti."` → `req_performance: "Si"` sugli obiettivi con requisiti di performance
- Leggi `nrt` dal JSON: se ≠ `"Non previsti."` → `req_nrt: "Si"` sugli obiettivi con requisiti NRT
- Leggi `livelli`: se contiene una riga `"T2"` → `req_e2e_uat: "Si"` sugli obiettivi che richiedono UAT
- NON re-inferire questi valori dal contesto conversazionale: leggi sempre dal JSON già costruito in 6.1.

**Struttura `pra_piano`** (opzionale, da Fase 3c GANTT):
```json
"pra_piano": [
  {"team": "Team A", "iterazione": "Sprint 1", "processo": "...", "owner": "..."}
]
```

### 6.4 — Verifica fedeltà MTP

```bash
python3 ~/.claude/skills/qa-docs/scripts/check_fidelity.py output_dir/MTP_*.docx ~/.claude/skills/qa-docs/assets/MTP_template.docx
```

Se la verifica rileva scostamenti non attesi → mostrali all'utente e chiedi se accettare o rigenerare.

### 6.5 — Output finale

Presenta **entrambi i file**:
- Path MTP: `MTP_<CODICE>_-_<titolo>.docx`
- Path PRA: `PRA_-_<CODICE>.xlsx`
- Riepilogo macro-scenari (numero e titoli)
- Elenco punti «DA CONFERMARE»
- Esito verifica fedeltà MTP
- **Checklist coerenza MTP ↔ PRA** (derivata dal JSON, non dall'analisi):
  - [ ] `len(perimetro_test)` == `len(pra_obiettivi)` — se diversi mostra il diff
  - [ ] `nrt` nel JSON == "Non previsti." → tutti `req_nrt: "No"` (o viceversa: almeno uno "Si")
  - [ ] `performance_test` nel JSON == "Non previsti." → tutti `req_performance: "No"` (o viceversa)
  - [ ] presenza riga T2 in `livelli` → almeno un `req_e2e_uat: "Si"` (o viceversa: nessuna riga T2 → tutti "No")

---

## Fallback e degradazione elegante

| Dipendenza | Fallback |
|---|---|
| MCP Atlassian assente | API REST JIRA con token, poi fallback a chat |
| Token JIRA assente | Chiedi di incollare contenuto issue |
| Skill di estrazione file assente | Usa Read diretto per .txt/.md; per .pdf/.docx avvisa e chiedi testo incollato |
| GitHub non accessibile | Proponi (a) salta o (b) riferimenti manuali |
| `python-docx` non installato | `pip3 install python-docx` prima di eseguire |
| Template non trovato | Usa path assoluto `~/.claude/skills/qa-docs/assets/MTP_template.docx` |

---

## File di riferimento (carica on-demand)

- `reference/template-structure.md` — struttura sezione per sezione, hex, SmartArt, anchor
- `reference/phase-playbook.md` — domande standard e regole per ogni fase
- `reference/intake-channels.md` — specifica 3 canali MODULO INTAKE
