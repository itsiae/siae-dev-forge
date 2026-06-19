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

## Fattori di rischio disponibili (foglio Tabelle)

**Business**: B-01..B-08 (frequenza uso, danni immagine, perdita business, responsabilità economiche, sanzioni, licenze, workaround, visibilità negativa)
**Tecnici**: T-xx (interfacciamenti, complessità, dipendenze...)
**Qualità**: Q-xx (aderenza requisiti, funzionalità, performance...)

Vedi foglio "Tabelle" del template per la lista completa.

## Coerenza MTP ↔ PRA

| Sezione MTP | Campo PRA |
|---|---|
| 1.4 Performance test ("Si previsto") | `req_performance: "Si"` |
| 1.5 NRT ("Si previsto") | `req_nrt: "Si"` |
| 1.3 Livello T2 UAT | `req_e2e_uat: "Si"` |
| macro-scenari perimetro_test | un entry `pra_obiettivi` per ogni scenario |

## Convenzione nome file
`PRA_-_<CODICE>.xlsx`
