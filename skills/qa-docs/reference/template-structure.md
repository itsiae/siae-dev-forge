# Template Structure — MTP SIAE

Fonte: analisi diretta di `MTP DMND0006339 - Mora singola con PBL.docx` (unzippato e ispezionato).

---

## Struttura documento

### Copertina (pag. 1)
- Logo SIAE: `word/media/image1.png` (centrato in alto — NON ridisegnare, ereditato dal template)
- Titolo: codice DMND su riga 1, descrizione su riga/e successive, "Master Test Plan" corsivo
  - Stile: grassetto, blu scuro, centrato
- Tabella anagrafica 2×3: Compilato | Verificato | Versione
- Didascalia: "Tabella 1 - Registro delle modifiche"
- Tabella Registro: header grigio (F2F2F2) con colonne Vrs. | Data | Paragrafo | Autore | Descrizione della modifica
  - Prima riga dati: 1.0 | <data> | Tutti | <autore> | First release

### Sommario (pag. 2)
- Campo TOC Word (non testo statico)
- Voci: 1. Contesto del progetto → 1.9 Rischi...
- Colore voci TOC: `2F5496` (stili Sommario1/Sommario2)
- `word/settings.xml` deve contenere: `<w:updateFields w:val="true"/>`

---

## Sezione 1 — Contesto del progetto
Stile: Titolo1, grassetto, nessun colore esplicito (usa tema documento)

### 1.1 Obiettivi del Progetto
Stile heading: Titolo2, colore `2F5496`

Contenuto:
- Prosa con concetti chiave in grassetto
- Frase di chiusura: "Di seguito vengono indicate piattaforme e i sistemi impattati."
- **SmartArt "Piattaforme"** — posizione: **SEZIONE 1.1** (VERIFICATA spacchettando il template)

#### Tabella 3 colonne Piattaforme (sostituisce SmartArt nell'output)

Il template originale contiene uno SmartArt in `word/diagrams/data1.xml` con 11 nodi
e slot fissi (2 Piattaforme + 1 SI + 5 PM). Poiché il layout comprimeva le voci quando
erano molte, `build_mtp.py` **sostituisce il paragrafo SmartArt** con una tabella Word
3 colonne scalabile:

| Piattaforme | Piattaforme Modificate | Sistemi Impattati |
|---|---|---|
| (voce 1) | (voce 1) | (voce 1) |
| ... | ... | ... |

**Caratteristiche tabella generata:**
- Header riga: fill `#1F3864` (blu SIAE scuro), testo bianco grassetto, testo 11pt
- Righe dati: alternate `#F2F2F2` / nessun fill, testo 11pt centrato
- Bordi: `single` 0.5pt bianco (aspetto "card" pulito)
- Larghezza totale: 9638 dxa (~17 cm) con 3 colonne uguali da 3212 dxa
- Righe: `max(len(piattaforme), len(piattaforme_modificate), len(sistemi_impattati))` — nessun limite
- Celle vuote se una lista ha meno voci delle altre

**Anchor in document.xml:** il paragrafo da sostituire contiene `mc:AlternateContent`
(che avvolge lo SmartArt). `replace_smartart_with_table()` lo individua per tag e
sostituisce il nodo XML padre con `<w:tbl>`.

---

### 1.2 Test Design
Stile: Titolo2, colore `2F5496`

Contenuto: elenco con checkbox ☑:
- ☑ IL PERIMETRO DEL TEST — tutte le funzionalità introdotte o modificate
- ☑ I MACRO SCENARI DI TEST: (elenco sotto-punti con "o")
- ☑ LE TECNOLOGIE DI TEST CHE SARANNO ADOTTATE PER L'INTEGRATION TEST — test funzionale

#### 1.2.1 Perimetro
Stile: Titolo3 (no colore esplicito)

- **Perimetro di Progetto:** (grassetto sottolineato) → prosa sintetica
- **Perimetro di Test:** (grassetto sottolineato) → elenco numerato macro-scenari, ciascuno con sotto-punti puntati

---

### 1.3 Obiettivi e livelli del test
Stile: Titolo2, colore `2F5496`

Contenuto:
- "Di seguito viene definito l'**OBIETTIVO** del test:"
- Checklist macro-scenari con ☑ (uno per scenario)
- "A seguire i **LIVELLI** di Test previsti:"
- Tabella livelli: 5 colonne — Livello | Descrizione | Dettaglio | Owner | Governance
  - Header riga: gestito da cnfStyle firstRow=1 (stile tabella — NON aggiungere `w:shd` esplicito)
  - Fill righe alternate: F2F2F2 / FFFFFF
  - Righe tipiche: T0 Unit/System Test, T1 Integration Test, T2 UAT

---

### 1.4 Performance test
Stile: Titolo2 — default: "Non previsti."

### 1.5 NRT
Stile: Titolo2 — default: "Non previsti."

### 1.6 Test Automatici
Stile: Titolo2 — default: "Non previsti."

### 1.7 GANTT
Stile: Titolo2 — cronoprogramma sprint con % avanzamento e date
- Dati: SOLO da utente (raccolti/confermati in Fase 3); mai inventati
- Se non forniti: struttura «DA CONFERMARE»

### 1.8 Out of Scope
Stile: Titolo2 — elenco esclusioni

### 1.9 Rischi, Problemi, Azioni e decisioni per le attività di test
Stile: Titolo2

---

## Colori verificati (da styles.xml e document.xml)

| Elemento | Hex | Nota |
|---|---|---|
| Heading subsections 1.1–1.9 | `2F5496` | stile Titolo2, themeColor accent1, themeShade BF |
| Heading sezione 1 | theme | stile Titolo1, grassetto, nessun colore esplicito |
| TOC voci | `2F5496` | stili Sommario1/Sommario2 |
| Fill righe alternate tabelle | `F2F2F2` | grigio chiaro |
| Fill celle bianche tabelle | `FFFFFF` | |
| Header tabelle | via cnfStyle | firstRow=1, gestito dallo stile tabella |

## Font verificati

| Elemento | Font |
|---|---|
| Heading subsections (Titolo2) | majorHAnsi theme (Calibri Light equivalente) |
| Testo tabelle | majorHAnsi theme, sz 22 (11pt) |
| Corpo documento | minorHAnsi theme |

---

## Anchor per build_mtp.py (patch-by-anchor)

Il template NON contiene segnaposto nominati (`{{campo}}`). Il meccanismo è **anchor-based**:
lo script individua i nodi-bersaglio tramite pattern di testo/stile documentati qui.

**Regola di sicurezza**: se un anchor non è trovato in modo univoco → fallisce con errore chiaro,
non patcha il nodo sbagliato silenziosamente.

| Sezione | Anchor | Metodo |
|---|---|---|
| Codice DMND copertina | Paragrafo con testo che matcha `DMND\d+` (tra i primi 20) | Sostituisci testo run |
| Titolo copertina | Paragrafo dopo codice DMND, non "Master Test Plan", non vuoto | Sostituisci testo run |
| Compilato (autore) | Cella adiacente a cella con testo "Compilato" | Sostituisci run |
| Versione | Cella adiacente a cella con testo "Versione" | Sostituisci run |
| Registro modifiche | Prima tabella con header "Vrs." o "Data", riga 1 | Sostituisci celle dati |
| Obiettivo 1.1 | Paragrafi dopo heading "Obiettivi del Progetto" (Titolo2) | Sostituisci testo |
| Tabella Piattaforme | Paragrafo con `mc:AlternateContent` (SmartArt) → sostituito con `<w:tbl>` | `replace_smartart_with_table()` |
| Perimetro 1.2.1 | Paragrafi dopo heading "Perimetro" (Titolo3) | Sostituisci testo |
| Tabella livelli 1.3 | Prima tabella con cella header testo "Livello" | Sostituisci righe T0/T1/T2 |
| Performance 1.4 | Paragrafi dopo heading "Performance test" | Sostituisci testo |
| NRT 1.5 | Paragrafi dopo heading "NRT" | Sostituisci testo |
| Test Auto 1.6 | Paragrafi dopo heading "Test Automatici" | Sostituisci testo |
| GANTT 1.7 | Paragrafi dopo heading "GANTT" | Sostituisci/inserisci |
| Out of Scope 1.8 | Paragrafi dopo heading "Out of Scope" | Sostituisci testo |
| Rischi 1.9 | Paragrafi dopo heading "Rischi, Problemi" | Sostituisci testo |
