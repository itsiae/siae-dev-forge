# SIAE QA — Template Xray e Esempi Test Case

## Table of Contents

- [Tabella Segnali Req Typing](#tabella-segnali-req-typing)
- [Template Req Profile Card](#template-req-profile-card)
- [Formato Test Case Step-Based](#formato-test-case-step-based)
- [Prefissi di Categoria](#prefissi-di-categoria)
- [Regola Multi-Step](#regola-multi-step)
- [Riepilogo Copertura](#riepilogo-copertura)
- [Template Matrice Scenari](#template-matrice-scenari)
- [Domande Elicitazione per Categoria](#domande-elicitazione-per-categoria)
- [Mappatura ID Sequenziali e Chiavi Jira Xray](#mappatura-id-sequenziali-e-chiavi-jira-xray)
- [Tier 3 CSV Export](#tier-3-csv-export)
- [Checklist di Verifica](#checklist-di-verifica)

---

## Tabella Segnali Req Typing

| Tipo | Segnali (summary, AC, description, label, stack) |
|------|--------------------------------------------------|
| **Frontend (FE)** | "componente", "pagina", "form", "UI", "Vue", "Angular", "React", "click", "visualizza", "render", "responsive" |
| **Backend Microservice (BE)** | "API", "endpoint", "service", "REST", "controller", "Spring", "Lambda", "validazione", "business rule" |
| **ETL / Data Pipeline** | "Glue", "PySpark", "pipeline", "trasformazione", "bronze", "silver", "gold", "job", "ETL", "medallion" |
| **Database** | "migration", "schema", "query", "tabella", "indice", "DDL", "flyway", "liquibase" |
| **Auth / Security** | "login", "logout", "ruolo", "permesso", "token", "autenticazione", "RBAC", "JWT" |
| **Integration / External** | "webhook", "chiamata esterna", "API terza parte", "evento", "Kafka", "SQS", "notifica" |
| **Mobile / Flutter**       | "Flutter", "Dart", "Riverpod", "app mobile", "iOS", "Android", "widget", "schermata", "deep link", "notifica push", "ObjectBox", "Amplify", "offline" |
| **IaC / Terraform**        | "Terraform", "terragrunt", "modulo", "VPC", "ECS", "Lambda", "plan", "apply", "destroy", "IAM", "security group", "tfvars", "remote state" |
| **Event-driven / Async**   | "Kafka", "SQS", "SNS", "consumer", "producer", "DLQ", "dead letter", "Step Functions", "async", "messaggio", "topic", "coda", "EventBridge" |

**Confidence:**
- **HIGH (>= 90%):** 2+ segnali forti convergenti
- **MEDIUM (60-89%):** 1 segnale forte o 2+ deboli
- **LOW (< 60%):** segnali ambigui o assenti

---

## Template Req Profile Card

```
REQ PROFILE:
  Tipo:       [Frontend / BE / ETL / Database / Auth / Integration / Mobile / IaC / Event-driven]
  Confidence: [HIGH / MEDIUM / LOW]
  Segnali:    [elenco segnali usati dall'inferenza]
  Stack:      [tecnologie rilevate]
```

Dopo le domande del tree (0c), aggiorna la card:

```
REQ PROFILE (aggiornato):
  Tipo:       [tipo]
  Scenari L1: [lista scenari flusso principale]
  Scenari L2: [lista edge case contestuali]
  Scenari L3: [lista scenari integrazione/dipendenze]
```

---

## Formato Test Case Step-Based

Per ogni scenario della matrice (4a), genera 1+ Test Case con questo formato:

| Campo | Contenuto |
|-------|-----------|
| ID | Numero sequenziale (1, 2, 3...) |
| Test Type | `Manual` |
| Team Competenza | `QA` |
| ID JIRA Story | `{PROJ-XXX}` — **obbligatorio** |
| User Story Description | Summary della Story Jira |
| Scenario (descrizione) | Titolo del Test Case — includi la categoria: es. `[EDGE] ...`, `[NEG] ...`, `[PROFILO] ...` |
| Step scenario | Numero step (1, 2, 3...) |
| Action | Cosa fa l'utente/sistema in questo step |
| Expected Result | Risultato atteso per questo step — **nel CSV il nome colonna e' `Expceted Result`** (typo storico del template importatore Xray SIAE) |
| Data | Dati di test specifici (vuoto se non necessario) |
| Automazione | `Y` se esiste test automatizzato per questo TC, `N` altrimenti |
| NRT | `Y` (default — il TC e' un Non-Regression Test) |

---

## Prefissi di Categoria

- Nessun prefisso = scenario positivo (happy path)
- `[EDGE]` = edge case (limite, vuoto, volume estremo)
- `[NEG]` = scenario negativo / alternativo (errore, input non valido, dipendenza assente)
- `[PROFILO]` = scenario specifico di ruolo / profilazione
- `[DT]` = test case derivato da Decision Table (combinazione di 2+ condizioni indipendenti)

---

## Regola Multi-Step

Stesso ID = stesso Test Case con step multipli. I metadati (tipo, team, Jira, descrizione scenario) si ripetono **solo nella prima riga**. Le righe successive dello stesso TC hanno solo: ID, step numero, Action, Expected Result.

---

## Riepilogo Copertura

**Riepilogo prima dell'export:** mostra la tabella completa al developer con la distribuzione per categoria. Il developer puo' modificare i valori di `Automazione` e `NRT` prima di procedere all'export.

```
Riepilogo copertura:
  Positivi:     N TC
  Edge case:    N TC
  Negativi:     N TC
  Profilazioni: N TC
  [DT]:         N TC   (ometti la riga se il gate 4a-bis ha risposto NO)
  TOTALE:       N TC

  ─────────────────────────────────────
  Coverage Score: XX/100
    Breadth:   XX/40  (N/4 categorie con almeno 1 TC — 10 pt ciascuna)
    Depth:     XX/20  (negativi ≥ positivi: SI/NO +10 | 1 TC per ogni AC: SI/NO +10)
    Technique: XX/20  (DT applicata (gate=SI): +20 | DT non applicabile (gate=NO): +20 auto | DT applicabile ma omessa: +0)
    Domain:    XX/20  (L1 domande poste: SI/NO +10 | L2/L3 → ≥1 TC extra: SI/NO +10)

  Giudizio: OTTIMA (90-100) / BUONA (70-89) / PARZIALE (50-69) / INSUFFICIENTE (<50)
  ─────────────────────────────────────
```

**Soglie e azioni:**

| Score | Giudizio | Azione |
|-------|----------|--------|
| 90–100 | OTTIMA | Procedi all'export |
| 70–89 | BUONA | Accettabile — aggiungi note sui gap minori come commento nel TC |
| 50–69 | PARZIALE | Suggerisci integrazione su categorie deboli, ma non blocca |
| < 50 | **INSUFFICIENTE** | **EXPORT BLOCCATO** — torna a 4a; indica categoria con score più basso |

Se il giudizio è INSUFFICIENTE, mostra:
```
⛔ EXPORT BLOCCATO — Coverage Score: XX/100
   Categoria debole: {Breadth/Depth/Technique/Domain} ({XX}/{max} pt)
   Azione richiesta: {descrizione specifica — es. "aggiungere almeno 1 TC negativo"}
```

---

## Template Matrice Scenari

Output atteso della fase 4a — matrice scenari compilata prima della generazione:

```
Categoria              | Scenari identificati
-----------------------|-----------------------------------------------
Positivi (happy path)  | [lista da AC + eventuali varianti]
Edge case              | [lista da domande o da AC]
Alternativi/negativi   | [lista da domande o da AC]
Profilazioni/ruoli     | [lista da domande, o "N/A - nessun controllo ruolo"]
```

Se per una categoria il developer conferma che non ci sono scenari aggiuntivi, registra "N/A — confermato dal developer" e procedi.
**Non puoi procedere alla generazione con categorie non valutate.**

---

## Domande Elicitazione per Categoria

**Categoria 1 — Scenari positivi (happy path)**
Hai gia' questo dagli AC. Verifica solo che siano completi.
Domanda tipo: "L'AC descrive il caso principale. C'e' qualche variante del flusso positivo che vuoi coprire esplicitamente?"

**Categoria 2 — Edge case**
Valori limite, stati vuoti, volumi estremi, timing. Se non emergono dagli AC, chiedi:
- "Cosa succede con input al limite del range valido? (es. importo = 0, lista vuota, data = oggi)"
- "Ci sono condizioni di gara o sequenze di eventi inattesi da coprire?"
- "Il sistema e' idempotente? Cosa succede se l'operazione viene eseguita due volte?"

**Categoria 3 — Scenari alternativi / negativi**
Flussi di errore, input non validi, permessi mancanti. Se non emergono dagli AC, chiedi:
- "Quali input non validi deve rifiutare il sistema? Con quale messaggio/comportamento?"
- "Cosa succede se una dipendenza esterna e' assente o risponde con errore?"
- "Ci sono stati del sistema che impediscono l'operazione? (es. record gia' esistente, stato non compatibile)"

**Categoria 4 — Profilazioni / ruoli**
Utenti diversi con permessi o dati diversi. Se la Story tocca autorizzazioni o ruoli, chiedi:
- "Quale tipo di utente esegue questa operazione? Ci sono altri ruoli che possono o non possono farlo?"
- "Il comportamento cambia in base al profilo? (es. autore vs editore, admin vs operatore)"
- "Ci sono dati sensibili che solo alcuni ruoli possono vedere?"

---

## Mappatura ID Sequenziali e Chiavi Jira Xray

**Passo post-export — Mappatura ID sequenziali → chiavi Jira Xray [OBBLIGATORIO se si usa siae-automation]**

Dopo l'import del CSV (o la creazione MCP), Xray assegna a ogni TC una chiave Jira propria (`PROJ-XXX`).
Questa chiave e' diversa dall'ID sequenziale usato nel CSV (`1`, `2`, `3`).

Se prevedi di usare `siae-automation` per generare test Cypress o Appium, **devi raccogliere questa mappatura** prima di chiudere la skill:

```
Mappatura TC — {STORY_ID}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ID CSV  →  Chiave Xray   Scenario
  1       →  PROJ-456      Verifica login credenziali valide
  2       →  PROJ-457      [EDGE] Login con campo vuoto
  3       →  PROJ-458      [NEG] Login con password errata
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Tier 1 (MCP):** la chiave viene restituita dalla risposta del tool di creazione — raccoglila automaticamente.
**Tier 3 (CSV):** chiedi al developer di aprire Xray dopo l'import e comunicare le chiavi assegnate. Non procedere con siae-automation finche' non hai questa mappatura.

Salva la mappatura come output della skill: sara' l'input di Fase 1 di siae-automation.

---

## Tier 3 CSV Export

- Genera il file CSV con separatore `;` (semicolon) — **mai virgola**
- Formato esatto: vedi `reference/xray-csv-template.md`
- Header obbligatorio in prima riga
- Mostra il CSV all'utente e spiega come importarlo: Xray → Test → Import CSV

---

## Checklist di Verifica

Prima di dichiarare la skill completata:

- [ ] Phase 0 eseguita: tipo requisito inferito e Req Profile Card mostrata
- [ ] Confidence HIGH → tree lanciato senza conferma tipo | MEDIUM/LOW → conferma ricevuta
- [ ] Domande del tree skippate se risposta gia' presente in AC/description
- [ ] Req Profile Card aggiornata con scenari L1/L2/L3 prima di procedere a Phase 4a
- [ ] AC letti da Jira (o forniti esplicitamente dal developer)
- [ ] Test Strategy Confluence cercata (trovata o WARNING registrato)
- [ ] Test Plan generato/creato con campi obbligatori
- [ ] Matrice scenari compilata (4 categorie valutate: positivi, edge, negativi, profilazioni)
- [ ] Gate 4a-bis eseguito: Decision Table applicata (se 2+ condizioni booleane) o scartata con SE NO esplicito
- [ ] Ogni categoria ha scenari identificati o "N/A — confermato dal developer"
- [ ] Ogni AC ha almeno 1 Test Case step-based
- [ ] Presenti TC per scenari positivi, edge case, negativi e profilazioni (se applicabili)
- [ ] I titoli Scenario usano i prefissi `[EDGE]`, `[NEG]`, `[PROFILO]` dove appropriato
- [ ] Ogni step ha sia `Action` che `Expected Result` (nel CSV usa la colonna `Expceted Result` — typo template)
- [ ] Il campo `ID JIRA Story` e' presente in tutti i Test Case
- [ ] Riepilogo copertura per categoria mostrato al developer prima dell'export
- [ ] Coverage Score calcolato e giudizio mostrato al developer (se < 50: export bloccato)
- [ ] Campi `Automazione` e `NRT` verificati con il developer
- [ ] Export effettuato (MCP / CSV) o spiegato come farlo
- [ ] Mappatura ID sequenziali → chiavi Jira Xray raccolta (se si prevede di usare siae-automation)
- [ ] Tier usato annunciato nella pre-flight card di apertura

**Non riesci a spuntare tutte le caselle? Il workflow non e' completo. Ricomincia dalla fase bloccata.**
