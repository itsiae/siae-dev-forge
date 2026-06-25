# PRA Structure — Product Risk Analysis SIAE

Fonte: analisi diretta di `PRA_-_DMND0099999.xlsx`.

---

## Fogli

| Foglio | Modificabile | Scopo |
|---|---|---|
| Copertina | Sì (R10 F) | Titolo documento + processo |
| Informazioni | Sì (R6) | Versione, data, autore |
| Obiettivi del Test | Sì (R5+) | Matrice rischio per obiettivo |
| Matrice Rischio | **NO** | Tabella di lookup — read-only |
| Tabelle | **NO** | Fattori di rischio e lookup — read-only |
| Piano | Sì (R2+) | Pianificazione sprint/team |

---

## Foglio "Copertina"
- R5 B: "Product Risk Analysis" (titolo fisso — NON modificare)
- R10 D: "Processo" (label — NON modificare)
- **R10 F**: nome processo = `meta.titolo`

## Foglio "Informazioni"
- R2 C: "Product Risk Analysis" (NON modificare)
- R3 C: "Versioni del documento..." (NON modificare)
- R5: riga header (NON modificare)
- **R6**: C=versione, D=data (YYYY-MM-DD), E=autore, F=validatore (vuoto ok), G="Prima Emissione"

## Foglio "Obiettivi del Test"

Dati a partire da **riga 5** (R1=header, R2-R4=spaziatura — non toccare).

| Col | Campo | Dominio valori |
|---|---|---|
| A | Obiettivo / macro-scenario | testo libero |
| B | Criticità — Danno in caso di fallimento | `Bassa` / `Media` / `Alta` / `Bloccante` |
| C | Fattore di Rischio | codici B-xx / T-xx / Q-xx (vedi foglio Tabelle) |
| D | Motivazione della criticità | prosa breve |
| E | Frequenza d'uso | `Bassa` / `Media` / `Alta` / `Molto Alta` |
| F | Requisito NRT | `Si` / `No` (coerente con sezione 1.5 MTP) |
| G | Requisito Performance | `Si` / `No` (coerente con sezione 1.4 MTP) |
| H | Requisito E2E UAT | `Si` / `No` (coerente con T2 in sezione 1.3 MTP) |
| I | **Rischio (calcolato)** | **FORMULA** — mai valore statico |

### Formula colonna I (Rischio)

Per ogni riga `R` (partendo da 5):
```
=IF(B{R}="Bassa",IF(E{R}="Bassa","Bassa",IF(E{R}="Media","Bassa",IF(E{R}="Alta","Media",IF(E{R}="Molto Alta","Alta","")))),IF(B{R}="Media",IF(E{R}="Bassa","Bassa",IF(E{R}="Media","Media",IF(E{R}="Alta","Media",IF(E{R}="Molto Alta","Alta",0)))),IF(B{R}="Alta",IF(E{R}="Bassa","Media",IF(E{R}="Media","Alta",IF(E{R}="Alta","Alta",IF(E{R}="Molto Alta","Molto Alta","")))),IF(B{R}="Bloccante",IF(E{R}="Bassa","Alta",IF(E{R}="Media","Alta",IF(E{R}="Alta","Molto Alta",IF(E{R}="Molto Alta","Molto Alta",""))))))))
```
`build_pra.py` genera questa formula automaticamente per ogni riga.

## Foglio "Piano"
- R1: header fisso (NON modificare)
- R2+: Team | Iterazione | Processo | Owner | (resto opzionale)

## Fattori di rischio — Tassonomia SIAE completa

I codici sono quelli del foglio "Tabelle" del template PRA. Nel campo `fattore_rischio` del JSON usa sempre `CODICE Nome breve` (es. `B-03 Perdita di incassi`).

### Business (B-xx) — Rischi di business SIAE

| Codice | Nome | Quando usarlo |
|---|---|---|
| B-01 | Alta frequenza d'uso | Funzionalità ad alto traffico: portale self-service licenze, API partner streaming/broadcasting, autenticazione CIAM. Degrado → SLA violati o perdita incassi per indisponibilità |
| B-02 | Danni di immagine | Impatto mediatico o reputazionale su autori, licenziatari, stampa. Es: blocco visibile di licenze su eventi di rilievo pubblico |
| B-03 | Perdita di incassi | Mancato incasso diritti, pagamenti errati ad autori/editori, rimborsi forzati per errori di sistema. Rischio diretto sui flussi economici SIAE |
| B-04 | Responsabilità economiche | Penali contrattuali, contenziosi con autori o licenziatari, rimborsi per errori imputabili al sistema |
| B-05 | Sanzioni normative | Violazioni GDPR (art. 5, 32, 83), D.Lgs 68/2003, Direttiva UE 2019/790 (diritto d'autore nel mercato unico digitale), obblighi AML, rendicontazioni obbligatorie verso MEF/AGCOM |
| B-06 | Impatto su mandati e licenze | Errori su contratti con autori, editori, licenziatari (eventi live, broadcast, streaming, TV, radio). Rischio invalidazione mandati o contenziosi |
| B-07 | Necessità di workaround manuali | Intervento manuale del backoffice SIAE per correggere dati, compensare funzionalità mancanti o sbloccare flussi interrotti |
| B-08 | Visibilità istituzionale negativa | Impatto su stakeholder istituzionali: MEF, PCM, AGCOM, Parlamento, audizioni parlamentari, stampa specializzata |

### Tecnici (T-xx) — Rischi tecnici specifici SIAE

| Codice | Nome | Quando usarlo |
|---|---|---|
| T-01 | Interfacciamento ESB/Mulesoft | Modifiche a contratti API ESB, routing, trasformazioni, timeout, duplicazione messaggi. Impatta tutti i flussi che transitano per lo strato di integrazione SIAE |
| T-02 | Drools / regole di business | Modifiche al motore di regole per calcolo diritti, licenze, tariffe. Rischio di regressione silenziosa su logiche complesse con casistiche numerose |
| T-03 | Database Oracle / transazionale | Query su tabelle di grandi dimensioni (repertori, mandati, movimenti economici): lock, performance degradate, inconsistenza in concorrenza |
| T-04 | Integrazione pagamenti | PagoPA, circuiti bancari, Sistema Incassi SIAE: rischio mancato incasso, doppio addebito, riconciliazione errata tra sistemi |
| T-05 | Autenticazione e sicurezza | CIAM, SSO, SPID/CIE, gestione profili e ruoli: rischio accesso non autorizzato a dati personali o finanziari di autori e licenziatari |
| T-06 | Pipeline dati ETL/DWH | Glue AWS, Medallion architecture, data lake SIAE: aggregazioni errate, ritardi nella rendicontazione, inconsistenza tra layer bronze/silver/gold |
| T-07 | Performance sotto carico stagionale | Picchi a fine anno (pagamento royalties annuali), estate (eventi live), scadenze fiscali: rischio SLA violati, time-out utenti, code di elaborazione |
| T-08 | Retrocompatibilità API esterne | Contratti API con partner (piattaforme streaming, TV, radio, eventi, agenzie): breaking change su consumer non aggiornati o con cicli di rilascio indipendenti |
| T-09 | Deploy e rollback | Pipeline CI/CD su sistemi mission-critical (licenze, incassi): rischio downtime durante deploy, impossibilità di rollback rapido su sistemi in produzione attiva |
| T-10 | Dipendenze da terze parti esterne | PagoPA, banche, piattaforme streaming (Spotify, YouTube, DAZN), sistemi di ticketing: indisponibilità upstream che blocca flussi SIAE senza possibilità di fallback interno |

### Qualità (Q-xx) — Rischi di qualità SIAE

| Codice | Nome | Quando usarlo |
|---|---|---|
| Q-01 | Aderenza ai requisiti funzionali | Funzionalità non conforme alle specifiche DMND o ai criteri di accettazione approvati dalla BU |
| Q-02 | Accuratezza calcolo diritti/royalties | Calcoli royalties, tariffe licenze o compensi errati: impatto diretto e misurabile su autori ed editori, con rilevanza legale |
| Q-03 | Integrità dati anagrafici | Opere, autori, mandati, licenziatari: dati corrotti o inconsistenti che si propagano a sistemi downstream (DWH, rendicontazione, sistemi partner) |
| Q-04 | Usabilità e UX | Portale self-service per licenziatari, dashboard autori, backoffice operatori SIAE: degrado operativo e aumento del carico di supporto |
| Q-05 | Compliance GDPR e normativa settoriale | Gestione dati personali, consensi, diritti dell'interessato (art. 15-22 GDPR), trattamento dati finanziari, normativa diritti d'autore |
| Q-06 | Tracciabilità e audit trail | Log di operazioni per contenzioso legale, ispezioni fiscali, reportistica regolamentare verso AGCOM/MEF, difesa in giudizio |
| Q-07 | Performance e tempi di risposta | SLA su portali pubblici, API partner, elaborazioni batch notturne: degrado misurabile rispetto a soglie definite nei requisiti |
| Q-08 | Sicurezza applicativa | OWASP Top 10, gestione dati finanziari e personali, requisiti pen-test, vulnerability scanning, segregazione dei ruoli |
| Q-09 | Copertura scenari edge e casi speciali | Licenze speciali, mandati con clausole particolari, gestione eccezioni nel calcolo diritti, casistiche CISAC per repertori esteri |
| Q-10 | Reportistica e rendicontazione | Output per autori (estratto conto royalties), BU SIAE, MEF, AGCOM, rendicontazioni annuali e periodiche obbligatorie |
| Q-11 | Gestione stati e workflow | Correttezza delle transizioni di stato (es. licenza: bozza→attiva→scaduta→revocata), gestione concorrenza, rollback di operazioni parziali |
| Q-12 | Repertori esteri e mandati internazionali | Gestione repertori CISAC, mandati con collecting societies estere (SACEM, GEMA, PRS...), valute, normative internazionali |

## Rubrica operativa criticità — Contesto SIAE

Usa questa rubrica per assegnare la criticità a ogni obiettivo di test. **La criticità misura il danno in caso di fallimento**, non la probabilità. Scegli il livello più alto che si applica ad almeno uno dei criteri elencati.

| Criticità | Quando assegnare | Esempi concreti SIAE |
|---|---|---|
| **Bloccante** | Il difetto: (1) blocca l'incasso di diritti o il pagamento di royalties; oppure (2) genera violazioni normative certe (GDPR, Direttiva Copyright UE, AML); oppure (3) blocca l'emissione di licenze obbligatorie; oppure (4) espone SIAE a sanzioni immediate da parte di autorità di vigilanza (AGCOM, MEF, Garante Privacy) | Calcolo royalties errato nel batch mensile; blocco emissione licenze durante evento di rilievo; data breach GDPR con notifica obbligatoria; PagoPA non funzionante durante scadenza di pagamento; errore sistematico nel calcolo tariffe diffuso su larga scala |
| **Alta** | Il difetto: (1) causa perdita parziale di incassi o ritardi significativi nei pagamenti; oppure (2) genera dati inconsistenti su mandati/opere con propagazione a sistemi downstream; oppure (3) richiede intervento manuale del backoffice su larga scala; oppure (4) danneggia la reputazione istituzionale di SIAE | Errore in rendicontazione autori (senza blocco totale); import repertori parzialmente fallito; performance degradata sul portale in periodo di picco; reportistica verso AGCOM con dati errati; integrazione ESB interrotta su flusso secondario; tracciabilità compromessa su operazioni finanziarie |
| **Media** | Il difetto: (1) degrada l'esperienza utente con workaround disponibili; oppure (2) introduce inefficienze operative limitate; oppure (3) impatta funzionalità non direttamente collegate agli incassi o alla compliance; oppure (4) richiede correzione nella prossima release senza urgenza | Report secondario con ritardo non critico; errore di visualizzazione su dashboard non finanziaria; funzionalità backoffice con workaround manuale semplice; notifiche email con contenuto parzialmente errato ma non bloccante; prestazioni degradate su funzionalità non core |
| **Bassa** | Il difetto: (1) è cosmetico; oppure (2) riguarda funzionalità di nicchia; oppure (3) nessun impatto su incassi, pagamenti o compliance; oppure (4) workaround immediato e senza costi; oppure (5) utenti impattati < 5% della base utente attiva | Testo UI non aggiornato; ordinamento non corretto su lista non finanziaria; funzionalità amministrativa raramente usata; help text non corretto; tooltip mancante |

### Casi limite e decisioni ambigue

Questi pattern emergono con frequenza in produzione e causano allucinazioni o assegnazioni errate se non gestiti esplicitamente.

---

#### 1. Alta criticità + Bassa frequenza — operazioni una tantum legalmente critiche

**Regola**: per operazioni rare ma con conseguenze legali irreversibili, assegna la criticità in base al **danno del singolo errore**, non alla frequenza. La formula produce `Alta` su `Bloccante × Bassa` — è il risultato corretto.

| Scenario | Criticità | Frequenza | Rischio calcolato | Motivazione corretta da scrivere |
|---|---|---|---|---|
| Firma digitale mandato autore | Bloccante | Bassa (~2.000/anno) | Alta | "Errore invalida il mandato dell'autore con effetti legali indipendenti dalla frequenza (D.Lgs 68/2003 art. 32). Rischio Alta è corretto anche con frequenza Bassa." |
| Migrazione dati storici repertori | Bloccante | Bassa (una tantum) | Alta | "Corruzioni su repertori propagano a DWH e rendicontazioni downstream. Operazione una tantum non abbassa il danno potenziale." |
| Apertura esercizio fiscale annuale | Bloccante | Bassa (1×/anno) | Alta | "Errore blocca pagamenti royalties annuali e reportistica MEF. Frequenza bassa ma impatto economico-legale su tutti gli autori SIAE." |
| Revoca mandato per contenzioso | Alta | Bassa (decine/anno) | Media | "Impatta il singolo autore, non il sistema. Workaround manuale disponibile via backoffice. Rischio Media è corretto." |

**Segnale d'allarme**: se stai assegnando Bloccante a più di 4 scenari su 8 **e** tutti hanno frequenza Bassa/Media, verifica che ogni Bloccante sia giustificato da almeno uno dei 4 criteri della rubrica (blocco incassi / violazione normativa / blocco licenze / sanzione). Se la motivazione è "potrebbe impattare autori" senza specificare come, considera di scalare ad Alta.

---

#### 2. Interfaccia di gestione vs. funzione core — non ereditare la criticità del sistema

**Regola**: la criticità del sistema sottostante **non si trasferisce automaticamente** all'interfaccia di monitoraggio o revisione. Valuta il danno della singola funzionalità in scope.

| Funzione | Sistema | Criticità corretta | Perché |
|---|---|---|---|
| Elaborazione antifrode (rilevazione) | Antifrode ML | Bloccante | Un falso negativo blocca un pagamento illecito o lascia passare frode su royalties reali |
| Dashboard revisione falsi positivi (backoffice) | Antifrode ML | Media | Operatore può rivedere via DB/tool alternativo. Workaround disponibile; non blocca incassi |
| Calcolo royalties (batch core) | DWH Royalties | Bloccante | Errore diretto su importi corrisposti ad autori |
| Visualizzazione stato batch in dashboard | DWH Royalties | Media | Monitoring; l'assenza non blocca il calcolo, solo la visibilità operativa |
| Emissione licenza PagoPA | Pagamenti | Bloccante | Blocco diretto incasso |
| Log transazioni PagoPA (audit read-only) | Pagamenti | Alta | Dati per audit trail, non per incasso. Perdita temporanea impatta tracciabilità ma non l'incasso in corso |

**Anti-pattern**: classificare ogni scenario legato a un sistema critico come Bloccante o Alta — compreso il form di configurazione, la pagina di help, e le funzionalità di esportazione dati secondarie.

---

#### 3. Frequenza di un batch notturno — non usare "Alta" come default

**Regola**: un batch è classificato in base alla sua **cadenza effettiva**, non alla criticità dei dati che elabora.

| Batch | Cadenza | Frequenza corretta |
|---|---|---|
| Batch giornaliero incassi SIAE | Ogni notte (365×/anno) | Molto Alta |
| Batch settimanale import repertori CISAC | 1×/settimana | Alta |
| Batch mensile estratto conto royalties | 1×/mese | Media |
| Batch annuale chiusura esercizio | 1×/anno | Bassa |
| Batch trimestrale rendicontazione AGCOM | 4×/anno | Media |

> Se il dato non è disponibile nel brief, usa il proxy della sezione "Criteri frequenza d'uso". **Non usare Alta come default per i batch** — è il errore più comune in simulazione.

---

#### 4. Anti-pattern frequenti — cosa evitare in produzione

| Anti-pattern | Segnale | Correzione |
|---|---|---|
| **Inflazione Bloccante** | Più di 5 scenari su 8 classificati Bloccante | Rivaluta ogni Bloccante: almeno 1 dei 4 criteri deve applicarsi letteralmente. "Potrebbe impattare" non è sufficiente. |
| **Assenza di Media** | Tutti gli scenari Alta o Bloccante | Verifica se ci sono interfacce di gestione, funzionalità secondarie o scenari con workaround disponibile. Quasi ogni progetto ha almeno 1 scenario Media. |
| **Frequenza Alta per tutto** | Tutti gli scenari con frequenza Alta o Molto Alta | Verifica cadenza reale. Report, configurazioni e funzionalità amministrative sono raramente Alta. |
| **req_nrt inferito dal dominio** | req_nrt=Si su progetto senza SLA NRT espliciti nel brief | req_nrt deve essere dichiarato esplicitamente nel brief o nella JIRA. Non inferire dal fatto che il sistema è "real-time" per natura. |
| **Codice Q-xx generico su ogni riga** | Q-01 "aderenza requisiti" usato come catch-all | Q-01 va usato solo quando il rischio specifico è la non-conformità ai criteri di accettazione. Ogni altro rischio qualità ha il suo codice specifico. |
| **Cardinalità PRA < perimetro_test** | Meno `pra_obiettivi` dei macro-scenari | Ogni macro-scenario produce esattamente 1 entry PRA. Se hai 7 scenari → 7 righe PRA, senza eccezioni. |

---

**Regola fondamentale**: la frequenza è un fatto empirico, non un giudizio soggettivo. Ricavala sempre dai dati raccolti in Fase 1/2 (JIRA, documenti, chat). Documenta la fonte nel campo `motivazione` della PRA (es. "frequenza Alta — ~200 rinnovi/settimana da JIRA DMND-123"). MAI assegnare frequenza arbitraria senza fonte o ragionamento esplicito.

| Frequenza | Definizione | Esempi SIAE | Proxy se dato non disponibile |
|---|---|---|---|
| **Molto Alta** | Usata più volte al giorno da molti utenti (indicativamente >100 sessioni/giorno) o da processi automatici continuativi | Emissione/verifica licenze self-service, autenticazione CIAM, ricerca repertori, API partner streaming/broadcasting attive in produzione, elaborazioni batch giornaliere di incasso | Funzionalità core del portale self-service esposta a licenziatari; API con SLA contrattuali verso partner; processi automatici su dati di repertorio o finanziario |
| **Alta** | Usata quotidianamente o più volte a settimana da utenti regolari | Rinnovo licenze periodiche, caricamento dichiarazioni eventi, dashboard autori, import batch giornaliero repertori, gestione mandati attivi, monitoraggio operativo backoffice | Funzionalità operative principali del backoffice SIAE; dashboard di monitoraggio quotidiano; elaborazioni con cadenza giornaliera o settimanale |
| **Media** | Usata mensilmente, trimestralmente o solo in determinati periodi dell'anno | Generazione estratto conto royalties (mensile/trimestrale), rendicontazione AGCOM, onboarding nuovi mandanti, generazione report annuali, licenze speciali per grandi eventi periodici | Funzionalità di reporting periodico obbligatorio; processi legati a scadenze fiscali o contrattuali fisse; operazioni con cadenza mensile o stagionale |
| **Bassa** | Usata raramente, in occasioni straordinarie o da un numero molto limitato di utenti (es. solo amministratori di sistema) | Configurazione parametri di sistema, migrazione dati storici, gestione eccezioni normative speciali, funzionalità di emergenza backoffice, correzioni manuali su repertori esteri | Configurazione di sistema; funzionalità amministrative di emergenza; processi una tantum o di bootstrap |

---

## Note sulla matrice di rischio

La matrice Criticità × Frequenza ha un comportamento documentato che riflette il contesto SIAE:

- **Bloccante × Bassa = Alta** (non "Molto Alta"): anche con frequenza bassissima, un difetto Bloccante produce sempre rischio "Alta". Questo è corretto per SIAE: un calcolo royalties sbagliato, anche su un solo autore, ha rilevanza legale indipendente dalla frequenza.
- **Il livello "Molto Alta"** nel rischio calcolato si raggiunge solo con `Alta × Molto Alta` oppure `Bloccante × Alta/Molto Alta`.
- **Se trovi rischio "Alta" o "Molto Alta" su criticità "Media"**: rivaluta la frequenza assegnata — probabilmente è sovrastimata, o la criticità dovrebbe essere alzata.
- **Obiettivi con rischio "Bassa"**: verificare che non siano stati classificati con criticità troppo bassa rispetto all'impatto reale su incassi SIAE o su autori.

---

## Garanzia fogli invariati — Whitelist write-targets

`build_pra.py` scrive **esclusivamente** su questi target:

| Foglio | Celle/range modificate |
|---|---|
| Copertina | R10 F (solo questa cella) |
| Informazioni | R6 C, D, E, F, G (solo questa riga) |
| Obiettivi del Test | R5+ — tutte le colonne A–I, sole righe dati; formula in I con row-index corretto per ogni riga |
| Piano | R2+ — colonne A–D, sole righe dati — solo se `pra_piano` non vuoto nel JSON |

I fogli **"Matrice Rischio"** e **"Tabelle"** non vengono mai aperti in scrittura da `build_pra.py`.

**Regola Foglio Piano con GANTT DA CONFERMARE**: se `pra_piano: []` o `gantt: []` nel JSON (dati non ancora forniti dall'utente), il foglio Piano viene lasciato **vuoto** — solo header fisso R1 invariato. Non inventare iterazioni, team o owner. Segnalare in Fase 6.5: "Foglio Piano: non popolato — dati GANTT DA CONFERMARE".

## Coerenza MTP ↔ PRA

| Sezione MTP | Campo PRA |
|---|---|
| 1.4 Performance test ("Si previsto") | `req_performance: "Si"` |
| 1.5 NRT ("Si previsto") | `req_nrt: "Si"` |
| 1.3 Livello T2 UAT | `req_e2e_uat: "Si"` |
| macro-scenari perimetro_test | un entry `pra_obiettivi` per ogni scenario |

## Convenzione nome file
`PRA_-_<CODICE>.xlsx`
