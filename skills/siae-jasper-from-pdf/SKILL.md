---
name: siae-jasper-from-pdf
description: >
  Ricostruisce template JasperReports (JRXML) identici a un PDF di riferimento.
  Iterazione automatica: estrae font, bbox, layout dal PDF, genera JRXML,
  renderizza, confronta pixel-per-pixel, corregge fino a soglia <2% diff.
  Trigger: "jrxml da pdf", "ricostruisci jasper", "pdf to jrxml", "genera template jasper",
  "replica pdf in jasper", "/forge-jasper", "jasper from pdf", "crea jrxml dal pdf",
  "reverse engineering pdf jasper", "JasperReports da pdf".
---

# SIAE Jasper From PDF — Ricostruzione JRXML da Reference PDF

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  Jasper From PDF                    ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 4. Implementation

---

## LA LEGGE DI FERRO

```
IL PDF DI RIFERIMENTO E' LA VERITA' ASSOLUTA. OGNI PIXEL CONTA.
```

**Violare la lettera di questa regola significa violare lo spirito della regola.**

<EXTREMELY-IMPORTANT>
Stai per dichiarare "fatto" o "completato"?
Hai evidenza numerica dal pixel-diff (< 2% per OGNI pagina)?
- NO → FERMATI. Torna al loop di convergenza (Fase 3).
- SI → Procedi alla validazione finale (Fase 4).

Stai pensando "e' abbastanza simile", "il diff e' trascurabile", "solo il footer e' diverso"?
Stai razionalizzando. Il PDF reference e' l'unica verita'. Misura, non stimare.

ZERO ASSUNZIONI: estrai TUTTO dal PDF (font, coordinate, colori, dimensioni).
NON indovinare font sizes, NON stimare posizioni, NON approssimare larghezze.
Ogni valore nel JRXML deve essere DERIVATO da una misurazione oggettiva del PDF.

ITERA FINO AL RAGGIUNGIMENTO. Non fermarti a "abbastanza simile".
Se una iterazione non migliora il diff, CAMBIA STRATEGIA, non ripetere lo stesso approccio.
</EXTREMELY-IMPORTANT>

---

## Quando si Applica

**Sempre:**
- L'utente fornisce un PDF di riferimento e chiede di generare JRXML
- L'utente ha JRXML esistenti da allineare a un PDF reference
- Qualsiasi richiesta di reverse-engineering PDF → JasperReports

**Prerequisiti:**
- PDF di riferimento presente nel filesystem
- Java (OpenJDK) disponibile (verifica con `java -version`)
- Maven disponibile (per dipendenze JasperReports)
- poppler-utils installato (pdftoppm, pdftotext, pdffonts)
- ImageMagick installato (magick compare)

**NON usare se:**
- Il target non e' JRXML/JasperReports
- Il PDF e' protetto/crittografato
- L'utente chiede solo un'analisi del PDF senza generazione JRXML

---

## Istruzioni

### FASE 0 — Setup Ambiente (una tantum) 🟢 Sicuro

Verifica e installa i prerequisiti:

```bash
java -version && mvn -v && pdftoppm -v && magick -version
```

Se manca qualcosa: `brew install openjdk maven poppler imagemagick`

Setup renderer Maven se non esiste:

1. Crea `tools/renderer/pom.xml` con dipendenza `net.sf.jasperreports:jasperreports:6.21.3`
2. Crea `tools/renderer/src/main/java/Renderer.java` — classe che:
   - Compila JRXML → .jasper
   - Riempie con parametri di test (estratti dal PDF)
   - Esporta in PDF (SENZA PDF/A per test, disabilitare via removeProperty)
3. Scarica font dal PDF di riferimento (pdffonts → cerca nel sistema)
4. Configura font extension JasperReports (fonts.xml + jasperreports_extension.properties)
5. `mvn dependency:copy-dependencies` + `javac` per compilare

### FASE 1 — Analisi del PDF Reference 🟢 Sicuro

**Step 1.1 — Metadati PDF:**
```bash
pdfinfo reference.pdf       # Dimensioni pagina, producer, creator
pdffonts reference.pdf      # Font usati (nome, tipo, encoding, embedded)
```

**Step 1.2 — Estrazione Bounding Box:**
```bash
pdftotext -bbox-layout reference.pdf ref-bbox.html
```
Parsa ref-bbox.html per estrarre:
- Ogni blocco di testo: (page, x, y, width, height, text)
- Font size inferito da bbox height
- Allineamento (left, center, right) inferito da x-position

**Step 1.3 — Estrazione Testo:**
```bash
pdftotext -layout reference.pdf ref.txt
```

**Step 1.4 — Rasterizzazione Reference:**
```bash
pdftoppm -r 150 -png reference.pdf ref
```

**Step 1.5 — Identificazione Parametri:**
Analizza il PDF per identificare:
- Testi statici (titoli, label, disclaimer) → `<staticText>`
- Testi dinamici (importi, date, nomi) → `<textField>` con `$P{param}`
- Immagini/icone → `<image>` con `$P{icon_xxx}`
- Forme geometriche (rettangoli, linee) → `<rectangle>`, `<line>`
- Tabelle con dati variabili → `<componentElement>` con `<jr:table>`

**Step 1.6 — Mappa Parametri:**
Crea README.md con lista parametri JRXML e dataset, basato su cosa e' statico e cosa dinamico nel PDF.

### FASE 2 — Generazione JRXML Iniziale 🟢 Sicuro

Per OGNI pagina del PDF:

1. Crea `<jasperReport>` con:
   - pageWidth/pageHeight da pdfinfo
   - leftMargin/rightMargin/topMargin/bottomMargin = 0
   - style default con fontName dal font primario del PDF

2. Per ogni blocco di testo dal bbox:
   - Crea `<staticText>` o `<textField>` con:
     - x, y, width, height ESATTI dalla bbox (arrotondati al pt intero)
     - fontSize ESATTO inferito dalla bbox height (h_bbox / 1.2 circa per ascender+descender)
     - isBold=true se il font nel PDF e' Bold
     - markup="styled" se contiene formattazione mista

3. Per forme geometriche:
   - Analizza aree colorate nel PDF (zone scure, bordi)
   - Crea `<rectangle>` con coordinate, backcolor, radius se arrotondati

4. Per tabelle:
   - Crea `<subDataset>` con i campi
   - Crea `<jr:table>` con colonne dal bbox (width = differenza tra center colonne consecutive)

5. Per icone/immagini:
   - Crea `<image>` con scaleImage="RetainShape"

### FASE 3 — Loop di Convergenza 🟡 Medio

Questo e' il cuore della skill. ITERA fino a convergenza:

```
REPEAT:
  1. Render JRXML → PDF
  2. Rasterizza output a 150dpi
  3. Calcola pixel diff per pagina (threshold 30)
  4. SE diff < 2% per TUTTE le pagine → STOP (successo)
  5. SE diff non migliora per 3 iterazioni consecutive → CAMBIA STRATEGIA
  6. Analizza bbox delta (per-elemento) tra reference e output
  7. Identifica i 5 blob piu' grandi nel heatmap
  8. Per ogni blob, diagnosi:
     a. Font size sbagliato? → Correggi (inferisci da bbox height)
     b. Posizione Y sbagliata? → Applica offset dal delta
     c. Posizione X sbagliata? → Correggi x nel reportElement
     d. Width sbagliata? → Correggi (causa wrapping diverso)
     e. Testo troncato? → Aumenta height
     f. Elemento mancante? → Aggiungi
  9. Applica TUTTE le correzioni in un batch
  10. GOTO 1
```

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-jasper-from-pdf |
|:---|
| 🔄 Iterazione convergenza · 📊 diff pixel attuale: `XX%` → target: `<2%` |
| **▼ Azione** |
| 1. 🎯 Applica N correzioni batch al JRXML → `<path jrxml>` |
| 💡 Perche': Ogni iterazione modifica il JRXML. Se il diff aumenta, revert necessario. |
| 🚫 Se NO: L'iterazione si ferma. Il JRXML rimane allo stato precedente. |

**IRON RULE DEL LOOP:**
- Ogni iterazione deve ridurre il diff O cambiare strategia
- Log il diff % ad ogni iterazione
- Se il diff AUMENTA, revert e analizza perche'
- MAX 20 iterazioni. Se non convergente, segnala il floor tecnico

### FASE 4 — Validazione Finale 🟢 Sicuro

REQUIRED SUB-SKILL: siae-verification

1. `xmllint --noout *.jrxml` per validare XML
2. Render con dati di test edge-case (nomi lunghi, importi grandi)
3. Verifica che `pdffonts output.pdf` mostri font embedded
4. Confronto finale pixel-diff con evidenza numerica
5. Genera report:

```
=== REPORT CONVERGENZA ===
Pagina 1: XX.XX% → YY.YY% (N iterazioni)
Pagina 2: XX.XX% → YY.YY% (N iterazioni)
Font: [lista font embedded]
Parametri: [lista parametri]
Soglia raggiunta: SI/NO
```

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "E' abbastanza simile" | "Abbastanza" non supera il gate del 2%. Misura. |
| "Solo il footer e' diverso" | Un footer diverso e' un pixel diff. Correggi. |
| "I font sono quasi uguali" | "Quasi" = hinting diverso = cascata di differenze. Usa il font esatto. |
| "Conosco gia' le coordinate" | Le conosci? pdftotext -bbox-layout le ha confermate? |
| "Una iterazione in piu' non serve" | Se il diff e' > 2%, serve. Non decidere tu, decide il numero. |
| "Il rendering JasperReports non puo' fare meglio" | Documenta il floor tecnico con evidenza, non con opinione. |
| "Stimo la font size a occhio" | L'occhio sbaglia di 1-2pt. La bbox no. |
| "Questo blocco non e' importante" | Ogni blocco contribuisce al diff totale. Nessuno e' trascurabile. |
| "Il PDF originale e' fatto male" | Il reference e' la verita'. Replica, non giudicare. |
| "Provo a rifare da zero" | Analizza cosa non converge prima. Rifare = perdere calibrazioni buone. |
| "Compilo e vedo se sembra ok" | "Sembra ok" non e' una metrica. `magick compare` lo e'. |
| "Manca poco, dichiaro completato" | <2% per OGNI pagina, o non e' completato. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura/analisi PDF reference | 🟢 Sicuro | No |
| Installazione brew packages | 🟢 Sicuro | No |
| Rasterizzazione PDF (pdftoppm) | 🟢 Sicuro | No |
| Creazione/modifica JRXML | 🟢 Sicuro | No |
| Rendering JRXML → PDF | 🟢 Sicuro | No |
| Pixel diff (magick compare) | 🟢 Sicuro | No |
| Iterazione batch correzioni | 🟡 Medio | Si |
| Copia font di sistema | 🟡 Medio | Verifica licenza |
| Pubblicazione su repo | 🔴 Alto | Chiedi conferma |

---

## Strategie di Escalation

Se dopo 10 iterazioni il diff e' ancora > 2%:

1. **Floor tecnico**: se il PDF e' generato da un engine diverso (Chrome/Skia, WeasyPrint), il floor di JasperReports/iText potrebbe essere > 2% per font hinting. In questo caso:
   - Segnala il floor con evidenza numerica
   - Proponi soglia alternativa o engine alternativo
   - Documenta nel report finale

2. **Fine-tuning per-elemento**: se il diff e' concentrato in pochi blob:
   - Estrai bbox delta per ogni elemento
   - Applica offset Y individuali (non globali)
   - Calibra width di ogni textField per matchare il wrapping

3. **Cambio approccio**: se il reference e' HTML→PDF, considera HTML template + Chrome headless.

---

## Vincoli

1. **Font**: usa SOLO font presenti nel sistema o embedded nel PDF reference. NON scaricare font da internet.
2. **Coordinate**: SEMPRE in punti PDF (1pt = 1/72 inch). JRXML usa la stessa unita'.
3. **PDF/A**: disabilita per il rendering di test. Riabilita nel JRXML finale se richiesto.
4. **Parametri**: ogni valore dinamico nel PDF deve diventare un `$P{nome_parametro}` nel JRXML.
5. **Encoding**: UTF-8 everywhere. Identity-H per font CID TrueType.
6. **NO hallucination**: se non riesci a estrarre un valore dal PDF, chiedi all'utente. NON inventare.

---

## Strumenti Richiesti

| Strumento | Uso | Installazione |
|---|---|---|
| Java (OpenJDK) | Compilare/eseguire JRXML | `brew install openjdk` |
| Maven | Dipendenze JasperReports | `brew install maven` |
| poppler | Analisi PDF (pdftoppm, pdftotext, pdffonts, pdfinfo) | `brew install poppler` |
| ImageMagick | Pixel diff (compare) | `brew install imagemagick` |
| Python 3 + PIL + numpy | Analisi blob, heatmap | `pip install Pillow numpy scipy` |
| xmllint | Validazione XML | Built-in macOS |

---

## Permission Denied Handling

Se l'utente nega un tool:
- `brew install` negato → chiedi all'utente di installare manualmente e verifica con `which <tool>`
- Rendering/compare negato → fornisci i comandi esatti da eseguire manualmente
- Scrittura file negata → mostra il contenuto JRXML per copia manuale
