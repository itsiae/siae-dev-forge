# Design: siae-qa — Decision Tables, Domain Extensions, Coverage Metrics

**Data:** 2026-03-30
**Autore:** DevForge AI Panel (4 giudici) + brainstorming
**Skill target:** `skills/siae-qa/`
**SP:** 5 SP-Umano / 3 SP-Augmented

---

## Contesto

Valutazione panel a 4 giudici sulla skill `siae-qa` ha identificato 3 gap prioritari
nella costruzione della test list:

1. **Decision Tables assenti** — gap che impatta ≥60% dei requisiti con 2+ condizioni
2. **Domain extensions mancanti** — la skill assume un contesto API/web sincrono e non
   si adatta a Mobile/Flutter, IaC/Terraform, Event-driven/Async
3. **Coverage metrics assenti** — nessuna misura quantitativa della completezza della test list

Questo design risolve i punti 1 e 2 con metriche di copertura (punto 3) integrate.

---

## Approccio scelto: B — Gate ortogonale + domain extensions additive

Tra 3 opzioni valutate:

| Opzione | Descrizione | Scartata perché |
|---------|-------------|-----------------|
| A — Additive flat | DT come Categoria 5 | Semanticamente errata: DT è tecnica, non categoria |
| **B — Gate ortogonale** | **DT come gate 4a-bis + nuovi tipi in question-trees** | **Scelta: semanticamente corretto, non rompe il workflow** |
| C — Refactoring ISTQB | Rimappa tutto sulla tassonomia ISTQB | Troppo invasivo, alto rischio di adozione nulla |

---

## Decisioni architetturali (ADR)

### ADR-1: Decision Tables come gate 4a-bis, non Categoria 5
Le Decision Tables sono una *tecnica di generazione* TC, non una categoria di scenari.
Inserirle come gate tra 4a e 4b mantiene la separazione semantica corretta:
- 4a = elicitazione scenari (cosa testare)
- 4a-bis = DT check (come strutturare i TC quando ci sono condizioni combinatorie)
- 4b = generazione TC (produzione step-based)

### ADR-2: 3 nuovi tipi in question-trees.md, non refactoring dei tipi esistenti
I tipi esistenti (FE, BE, ETL, DB, Auth, Integration) coprono bene il loro dominio.
Aggiungere Mobile, IaC, Event-driven segue lo stesso pattern L1/L2/L3 già consolidato.

### ADR-3: Coverage Score integrato nel Riepilogo Copertura esistente
Non creare una nuova sezione — il Riepilogo Copertura è già nel flusso obbligatorio.
Estenderlo con uno score calcolato è meno intrusivo e garantisce che venga effettivamente
visto dal developer.

### ADR-4: Score < 50 blocca l'export — soglie advisory sopra
La soglia bloccante è volutamente bassa (50): blocca solo le test list gravemente
incomplete. Le soglie 50-89 sono advisory per non creare friction eccessiva su casi
borderline legittimi.

---

## Specifiche di implementazione

### 1. Nuovo gate 4a-bis in `SKILL.md`

**Posizione:** tra la fine di Fase 4a e Fase 4b.

**Contenuto del gate:**
```
#### 4a-bis — Decision Table Check [AUTOMATICO — esegui sempre dopo 4a]

Dopo aver compilato la matrice scenari, verifica:
"Nella Req Profile Card o negli AC ci sono 2+ condizioni booleane/discrete
indipendenti la cui combinazione cambia il comportamento del sistema?"

Segnali tipici:
- Frasi del tipo "se [A] e [B] allora [X], altrimenti [Y]"
- Campi con valori discreti multipli (es. stato = {bozza, pubblicato, archiviato})
- Combinazioni ruolo × stato → comportamento diverso

SE SÌ → costruisci una mini Decision Table prima di generare i TC:
  1. Colonne = condizioni (max 4 per mantenibilità)
  2. Righe = combinazioni rilevanti (usa MC/DC: non serve 2^N — seleziona le combinazioni
     che cambiano l'output)
  3. Output = azione attesa del sistema per ogni combinazione
  4. Ogni riga della DT genera obbligatoriamente 1 TC con prefisso [DT]
  5. Mostra la tabella al developer per validazione prima di procedere a 4b

SE NO → procedi a 4b direttamente. Non forzare DT dove non ci sono condizioni booleane.
```

**Vincolo non negoziabile da aggiungere:**
> "La Decision Table deve essere mostrata e approvata dal developer prima di generare i TC da essa derivati."

---

### 2. Nuovo prefisso `[DT]` in `XRAY-TEMPLATES.md`

Nella sezione "Prefissi di Categoria", aggiungere:
```
- `[DT]` = test case derivato da Decision Table (combinazione di condizioni)
```

---

### 3. Nuovi 3 alberi in `reference/question-trees.md`

#### Mobile / Flutter
**Segnali:** "Flutter", "Dart", "Riverpod", "app mobile", "iOS", "Android",
"widget", "schermata", "notifica push", "deep link", "ObjectBox", "Amplify"

L1 — Flusso principale:
1. "Questa schermata richiede permessi OS (camera, location, notifiche, contatti)?
   Cosa mostra l'app se l'utente nega il permesso al primo lancio? E se lo revoca successivamente?"
2. "La schermata ha stati di caricamento? Cosa mostra mentre aspetta dati dal backend
   (skeleton, spinner, empty state)? Cosa mostra in caso di errore di rete?"

L2 — Edge case specifici Mobile:
3. "Cosa succede se l'utente manda l'app in background durante questa operazione
   (es. form non salvato, upload in corso) e torna in foreground dopo 5+ minuti?"
4. "Il comportamento cambia se il dispositivo è offline o passa da WiFi a 4G/5G
   durante l'operazione? C'è gestione offline o si mostra un errore?"

L3 — Integrazioni / dipendenze:
5. "La schermata è raggiungibile tramite deep link o notifica push?
   Come si comporta se l'app non è in memoria (cold start) vs già aperta?"

#### IaC / Terraform
**Segnali:** "Terraform", "terragrunt", "modulo", "VPC", "ECS", "Lambda",
"plan", "apply", "destroy", "IAM", "security group", "S3 bucket", "RDS"

L1 — Flusso principale:
1. "Il modulo è idempotente? `terraform apply` eseguito due volte su stato identico
   produce zero diff? Ci sono risorse che cambiano ad ogni apply (es. timestamp)?"
2. "Quali variabili di input sono obbligatorie? Ci sono valori di default che
   potrebbero essere accettati silenziosamente ma scorretti per certi ambienti?"

L2 — Edge case specifici IaC:
3. "Cosa succede se una risorsa è stata modificata manualmente fuori da Terraform
   (configuration drift)? Il plan rileva la differenza e la corregge?"
4. "Il destroy del modulo lascia risorse orfane (S3 bucket con dati, snapshot RDS,
   log group CloudWatch)? Ci sono risorse che richiedono `prevent_destroy`?"

L3 — Integrazioni / dipendenze:
5. "Il modulo dipende da output di altri moduli tramite remote state?
   Se il modulo upstream non è ancora applicato, il plan fallisce o degrada gracefully?"

#### Event-driven / Async
**Segnali:** "Kafka", "SQS", "SNS", "consumer", "producer", "evento",
"coda", "DLQ", "Step Functions", "async", "messaggio", "topic", "subscription"

L1 — Flusso principale:
1. "Il consumer è idempotente? Se lo stesso messaggio arriva due volte
   (at-least-once delivery), il sistema produce effetti doppi o li deduplica?
   Qual è la chiave di deduplication usata?"
2. "Qual è il comportamento atteso in caso di successo?
   Il messaggio viene ACKato/eliminato dalla coda? Viene prodotto un evento downstream?"

L2 — Edge case specifici Event-driven:
3. "Cosa finisce in Dead Letter Queue (DLQ)? Dopo quanti retry falliti?
   Chi monitora la DLQ e con quale procedura di recovery (reprocess manuale, alert, auto-retry)?"
4. "Il comportamento è corretto se i messaggi arrivano out-of-order?
   Il consumer assume un ordinamento implicito sugli eventi?"

L3 — Integrazioni / dipendenze:
5. "Esiste un ambiente di test con il broker reale (Kafka, SQS) o si usa un mock/LocalStack?
   I test di integrazione girano su infrastruttura dedicata o condivisa?"

---

### 4. Aggiornamento Tabella Segnali Req Typing in `XRAY-TEMPLATES.md`

Aggiungere 3 righe alla tabella esistente:
```
| **Mobile / Flutter**       | "Flutter", "Dart", "Riverpod", "app mobile", "iOS", "Android", "widget", "deep link", "notifica push", "ObjectBox", "Amplify" |
| **IaC / Terraform**        | "Terraform", "terragrunt", "modulo", "VPC", "ECS", "Lambda", "plan", "apply", "destroy", "IAM", "security group" |
| **Event-driven / Async**   | "Kafka", "SQS", "SNS", "consumer", "producer", "DLQ", "Step Functions", "async", "messaggio", "topic", "coda" |
```

---

### 5. Coverage Score nel Riepilogo Copertura (`XRAY-TEMPLATES.md`)

**Formula (0–100):**

```
Score = Breadth + Depth + Technique + Domain

Breadth (0–40 pt):
  +10 pt per ogni categoria non-N/A con almeno 1 TC (max 4 categorie × 10)

Depth (0–20 pt):
  +10 pt se TC negativi ≥ TC positivi
  +10 pt se ogni AC esplicito ha almeno 1 TC

Technique (0–20 pt):
  Se DT applicabile e applicata: +20 pt
  Se DT non applicabile (SE NO al gate 4a-bis): +20 pt automatici
  Se DT applicabile ma NON applicata: +0 pt

Domain (0–20 pt):
  +10 pt se almeno le domande L1 del question tree per il tipo rilevato sono state poste
  +10 pt se almeno 1 domanda L2 o L3 ha prodotto ≥ 1 TC aggiuntivo
```

**Soglie:**

| Score | Giudizio | Azione |
|-------|----------|--------|
| 90–100 | OTTIMA | Procedi all'export |
| 70–89 | BUONA | Accettabile — segnala gap minori come note |
| 50–69 | PARZIALE | Advisory: suggerisci integrazione su categorie deboli, ma non blocca |
| < 50 | INSUFFICIENTE | Blocca export — torna a 4a con motivazione specifica |

**Nuovo template Riepilogo Copertura:**
```
Riepilogo copertura:
  Positivi:     N TC
  Edge case:    N TC
  Negativi:     N TC
  Profilazioni: N TC
  [DT]:         N TC   (ometti se non applicato)
  TOTALE:       N TC

  ─────────────────────────────────────
  Coverage Score: XX/100
    Breadth:   XX/40  (N/4 categorie con almeno 1 TC)
    Depth:     XX/20  (negativi ≥ positivi: SI/NO | 1 TC per AC: SI/NO)
    Technique: XX/20  (DT applicata: SI / NO / N-A)
    Domain:    XX/20  (L1 risposto: SI/NO | L2/L3 → TC aggiuntivi: SI/NO)

  Giudizio: OTTIMA / BUONA / PARZIALE / INSUFFICIENTE
  ─────────────────────────────────────
  [Se < 50]: EXPORT BLOCCATO — categoria debole: {nome categoria}
             Azione richiesta: {cosa fare per sbloccare}
```

---

## File da modificare

| File | Tipo modifica | Sezione |
|------|--------------|---------|
| `skills/siae-qa/SKILL.md` | Aggiunta | Nuovo gate 4a-bis tra Fase 4a e 4b |
| `skills/siae-qa/SKILL.md` | Aggiunta | Vincolo non negoziabile n.9 (DT approvata prima di generare TC) |
| `skills/siae-qa/XRAY-TEMPLATES.md` | Aggiunta | Prefisso `[DT]` nella sezione Prefissi di Categoria |
| `skills/siae-qa/XRAY-TEMPLATES.md` | Modifica | Tabella Segnali Req Typing (+3 righe) |
| `skills/siae-qa/XRAY-TEMPLATES.md` | Modifica | Template Riepilogo Copertura (Coverage Score) |
| `skills/siae-qa/reference/question-trees.md` | Aggiunta | 3 nuovi alberi: Mobile/Flutter, IaC/Terraform, Event-driven/Async |

---

## Criteri di accettazione

- [ ] Gate 4a-bis presente in SKILL.md con segnali di rilevamento e istruzione SE SÌ / SE NO
- [ ] Prefisso `[DT]` documentato in XRAY-TEMPLATES.md sezione Prefissi
- [ ] 3 nuovi alberi in question-trees.md con struttura L1/L2/L3 e segnali di inferenza
- [ ] Tabella Segnali Req Typing aggiornata con Mobile, IaC, Event-driven
- [ ] Coverage Score formula documentata con i 4 componenti (Breadth, Depth, Technique, Domain)
- [ ] Soglie documentate con azione per ogni livello
- [ ] Template Riepilogo Copertura aggiornato con lo score
- [ ] Score < 50 blocca export con motivazione specifica
- [ ] Checklist di verifica in XRAY-TEMPLATES.md aggiornata (+2 voci: DT check, Coverage Score)

## REQUIRED SUB-SKILL: siae-writing-plans
