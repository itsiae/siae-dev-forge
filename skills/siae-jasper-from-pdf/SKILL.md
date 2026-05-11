---
name: siae-jasper-from-pdf
sdlc_phase: "4. Implementation"
description: >
  Use when reverse-engineering a PDF into a JasperReports JRXML template
  pixel-perfect. Iterazione automatica: estrae font, bbox, layout dal PDF,
  genera JRXML, renderizza, confronta pixel-per-pixel, corregge fino a
  soglia <2% diff.
  Trigger: "jrxml da pdf", "ricostruisci jasper", "pdf to jrxml", "genera template jasper",
  "replica pdf in jasper", "/forge-jasper", "jasper from pdf", "crea jrxml dal pdf",
  "reverse engineering pdf jasper", "JasperReports da pdf".
---

# SIAE Jasper From PDF — Ricostruzione JRXML da Reference PDF

```
+==============================================================+
|    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗   |
|    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║   |
|    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║   |
|    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝   |
|    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝    |
|    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝     |
|              Jasper From PDF                                  |
|         "Il codice si forgia. Il developer cresce."           |
+==============================================================+
```

> **Tipo:** Rigid | **Fase SDLC:** 4. Implementation

---

## Panoramica

Reverse-engineering di template JasperReports (JRXML) da PDF di riferimento. Usa **pdfplumber** come strumento primario per estrarre coordinate, font, colori, rettangoli con precisione sub-punto. Itera automaticamente con convergenza pixel-per-pixel.

**Principio fondamentale:** Il PDF reference e' la verita'. Misura, non stimare. Itera fino a convergenza.

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
Ogni valore nel JRXML deve essere DERIVATO da una misurazione oggettiva del PDF
(pdfplumber chars, rects, curves, images).

ITERA FINO AL RAGGIUNGIMENTO. Non fermarti a "abbastanza simile".
Se una iterazione non migliora il diff, CAMBIA STRATEGIA, non ripetere lo stesso approccio.
</EXTREMELY-IMPORTANT>

---

## Quando si Applica

**Sempre:**
- L'utente fornisce un PDF di riferimento e chiede di generare JRXML
- L'utente ha JRXML esistenti da allineare a un PDF reference
- Qualsiasi richiesta di reverse-engineering PDF → JasperReports

**NON usare se:**
- Il target non e' JRXML/JasperReports
- Il PDF e' protetto/crittografato
- L'utente chiede solo un'analisi del PDF senza generazione JRXML

---

## Istruzioni

### FASE 0 — Setup Ambiente e Dipendenze

<EXTREMELY-IMPORTANT>
QUESTA FASE E' BLOCCANTE. Se una dipendenza critica non si installa, FERMA TUTTO e segnala
all'utente con il messaggio esplicito dalla tabella sotto. NON procedere alla Fase 1 senza
aver verificato TUTTE le dipendenze.
</EXTREMELY-IMPORTANT>

#### Step 0.1 — Verifica dipendenze di sistema

Esegui TUTTI questi check in parallelo:

```bash
which java && java -version 2>&1 | head -1
which mvn && mvn -v 2>&1 | head -1
which pdftoppm && pdftoppm -v 2>&1 | head -1
which magick && magick -version 2>&1 | head -1
which xmllint
python3 --version 2>&1
```

#### Step 0.2 — Installa dipendenze mancanti (sistema)

Per ogni dipendenza mancante, installa con brew. Se brew non e' disponibile o l'utente nega
il permesso, fornisci il messaggio di fallback esplicito.

| Dipendenza | Check | Installazione | Fallback se non installabile |
|---|---|---|---|
| **Java (OpenJDK)** | `java -version` | `brew install openjdk` | `STOP: Java e' OBBLIGATORIO per compilare JRXML. Installa manualmente: https://adoptium.net/ poi rilancia.` |
| **Maven** | `mvn -v` | `brew install maven` | `STOP: Maven e' OBBLIGATORIO per scaricare JasperReports. Installa manualmente: https://maven.apache.org/download.cgi poi rilancia.` |
| **poppler** | `which pdftoppm` | `brew install poppler` | `STOP: poppler (pdftoppm, pdftotext, pdffonts, pdfinfo) e' OBBLIGATORIO per analizzare il PDF. Installa manualmente: https://poppler.freedesktop.org/ poi rilancia.` |
| **ImageMagick** | `which magick` | `brew install imagemagick` | `DEGRADATO: ImageMagick non disponibile. Il pixel-diff usera' solo Python/PIL (piu' lento). Per risultati migliori installa: https://imagemagick.org/script/download.php` |
| **mupdf-tools** | `which mutool` | `brew install mupdf-tools` | `DEGRADATO: mutool non disponibile. Estrazione font embedded dal PDF non possibile. I font verranno cercati nel sistema. Per risultati migliori installa: brew install mupdf-tools` |

**NOTA:** Se `brew` non e' disponibile:
```
ATTENZIONE: Homebrew non trovato. Installa le dipendenze manualmente:
- Java: https://adoptium.net/
- Maven: https://maven.apache.org/download.cgi
- poppler: https://poppler.freedesktop.org/
- ImageMagick: https://imagemagick.org/
- mupdf-tools: https://mupdf.com/releases/
Poi rilancia la skill.
```

#### Step 0.3 — Setup ambiente Python (CRITICO)

Crea un virtual environment dedicato nella directory di lavoro e installa le librerie Python.
Queste sono il cuore dell'analisi: senza pdfplumber la skill NON PUO' funzionare.

```bash
python3 -m venv tools/venv
tools/venv/bin/pip install pdfplumber pymupdf fonttools Pillow numpy scipy diff-pdf-visually
```

**Verifica installazione:**

```bash
tools/venv/bin/python3 -c "
import pdfplumber; print(f'pdfplumber {pdfplumber.__version__}')
import fitz; print(f'PyMuPDF {fitz.version[0]}')
from fontTools.ttLib import TTFont; print('fonttools OK')
from PIL import Image; print('Pillow OK')
import numpy; print(f'numpy {numpy.__version__}')
from scipy import ndimage; print('scipy OK')
"
```

**Tabella fallback librerie Python:**

| Libreria | Ruolo | Critica? | Fallback se non installa |
|---|---|---|---|
| **pdfplumber** | Estrazione chars, rects, curves, fonts con coordinate esatte | **SI — BLOCCANTE** | `STOP: pdfplumber e' OBBLIGATORIO. Senza di esso non e' possibile estrarre coordinate precise dal PDF. Errore: {errore_pip}. Prova: pip install pdfplumber --no-cache-dir. Se persiste, verifica che python3-dev sia installato.` |
| **pymupdf (fitz)** | Estrazione font embedded, text blocks, drawings | **SI — BLOCCANTE** | `STOP: PyMuPDF e' OBBLIGATORIO per estrarre font embedded e drawings dal PDF. Errore: {errore_pip}. Prova: pip install pymupdf --no-cache-dir` |
| **fonttools** | Confronto metriche font (advance widths, kerning) | No — degradato | `DEGRADATO: fonttools non disponibile. Il confronto metriche font non sara' possibile. Le differenze di rendering potrebbero non essere diagnosticabili.` |
| **Pillow** | Generazione heatmap, analisi immagini | **SI — BLOCCANTE** | `STOP: Pillow e' OBBLIGATORIO per l'analisi pixel-diff. Errore: {errore_pip}. Prova: pip install Pillow --no-cache-dir` |
| **numpy** | Calcolo differenze pixel, soglie, metriche | **SI — BLOCCANTE** | `STOP: numpy e' OBBLIGATORIO per l'analisi numerica. Errore: {errore_pip}. Prova: pip install numpy --no-cache-dir` |
| **scipy** | Connected components per blob detection | No — degradato | `DEGRADATO: scipy non disponibile. La blob detection sara' meno precisa (solo threshold semplice, nessun raggruppamento connesso).` |
| **diff-pdf-visually** | Confronto visivo rapido PDF | No — degradato | `DEGRADATO: diff-pdf-visually non disponibile. Il confronto usera' solo il metodo Python interno.` |

**Logica fallback:**
1. Se UNA libreria BLOCCANTE non si installa → mostra il messaggio esplicito con l'errore pip, suggerisci fix, e FERMA la skill
2. Se una libreria DEGRADATA non si installa → mostra il messaggio, continua con funzionalita' ridotta
3. Se NESSUNA libreria si installa (venv non creabile) → `STOP: Impossibile creare virtual environment Python. Verifica che python3 sia installato con: python3 --version. Se presente, prova: python3 -m ensurepip --default-pip && python3 -m venv tools/venv`

#### Step 0.4 — Setup renderer JasperReports

1. Crea `tools/renderer/pom.xml` con dipendenze:
   - `net.sf.jasperreports:jasperreports:6.21.3`
   - `org.apache.xmlgraphics:batik-bridge:1.17`
   - `org.apache.xmlgraphics:batik-transcoder:1.17`

2. Scarica dipendenze: `mvn -q dependency:copy-dependencies -DoutputDirectory=lib`

3. Se Maven fallisce:
   ```
   DEGRADATO: Maven dependency resolution fallita. Errore: {errore}.
   Il rendering di test non sara' possibile in questa sessione.
   Puoi comunque generare i JRXML e testarli su un ambiente con JasperReports.
   Per fixare: verifica connessione internet e proxy Maven (~/.m2/settings.xml).
   ```

4. Crea `tools/renderer/src/main/java/Renderer.java` (compila JRXML, riempie parametri, esporta PDF)

5. Estrai font del reference e configura font extension:
   - `pdffonts reference.pdf` → identifica font usati
   - Cerca font nel sistema (`/System/Library/Fonts/`, `/Library/Fonts/`)
   - Se `mutool` disponibile: `mutool extract reference.pdf` per estrarre font embedded
   - Crea `fonts/fonts.xml` + `fonts/jasperreports_extension.properties`

6. Compila: `javac -d classes -cp "lib/*" src/main/java/Renderer.java`

---

### FASE 1 — Analisi del PDF Reference con pdfplumber

**Questo e' il passo piu' importante. Da qui derivano TUTTE le coordinate del JRXML.**

#### Step 1.1 — Estrazione completa con pdfplumber

Per OGNI pagina del PDF, estrai:

```python
import pdfplumber

pdf = pdfplumber.open("reference.pdf")
for page in pdf.pages:
    # Ogni carattere con posizione, font, size, colore
    page.chars    # → x0, top, fontname, size, text, color

    # Parole raggruppate con font info
    page.extract_words(extra_attrs=["fontname", "size"])

    # Rettangoli (box scuri, bordi, separatori)
    page.rects    # → x0, top, x1, bottom, fill color, stroke color

    # Curve (bordi arrotondati, icone vettoriali)
    page.curves   # → bbox, fill, stroke, points

    # Immagini (logo, icone)
    page.images   # → x0, top, x1, bottom
```

**Output critico di questa fase:**
- Font ESATTI: `{fontname: size}` per ogni blocco di testo
- Coordinate ESATTE: `(x, y, width, height)` per ogni elemento
- Colori ESATTI: fill e stroke per rettangoli e curve
- Dimensioni tabella: posizione separatori, larghezza colonne

#### Step 1.2 — Confronto metriche font (se fonttools disponibile)

```python
from fontTools.ttLib import TTFont
# Confronta advance widths tra font sistema e font embedded nel PDF
# Se le metriche sono identiche → il floor tecnico e' il text shaper
# Se le metriche differiscono → usa il font estratto dal PDF
```

#### Step 1.3 — Analisi complementare (poppler)

```bash
pdfinfo reference.pdf       # Dimensioni pagina, producer (Chrome? Jasper? altro?)
pdffonts reference.pdf      # Font con tipo, encoding, embedded status
pdftotext -layout ref.pdf   # Testo per verifica contenuti
pdftoppm -r 150 -png ref.pdf out/ref   # Rasterizzazione baseline
```

**Il producer del PDF e' informazione critica:**
- `Skia/PDF` o `Chrome` → generato da browser, floor tecnico ~5-10% con JasperReports
- `iText` o `JasperReports` → stesso engine, convergenza a <1% possibile
- Altro → valutare caso per caso

---

### FASE 2 — Generazione JRXML basata su pdfplumber

Per OGNI pagina del PDF, genera il JRXML usando SOLO dati misurati:

1. **Report setup:**
   - pageWidth/pageHeight da `pdfinfo`
   - margins = 0
   - style default: fontName dal font piu' usato (da `page.chars`)

2. **Rettangoli e forme (da `page.rects` + `page.curves`):**
   - Per ogni rect con fill non-bianco → `<rectangle>` con x, y, width, height, backcolor
   - Per ogni curve con molti punti (>10) → `<rectangle radius="14">` (bordi arrotondati)
   - Colori: converti da (r,g,b) float a hex `#RRGGBB`

3. **Blocchi di testo (da `page.extract_words`):**
   - Raggruppa parole per y-proximity (stessa riga) e fontname/size
   - Per ogni blocco: `<staticText>` o `<textField>` con:
     - x, y = coordinate pdfplumber (arrotondati a int)
     - width = xMax_blocco - xMin_blocco (+ padding 5pt)
     - height = righe * line_height
     - fontSize = `size` da pdfplumber (ESATTO, non stimato)
     - isBold = "Bold" in fontname

4. **Tabelle (da pattern rects + words):**
   - Identifica separatori orizzontali (rects sottili, stessa y, fill grigio)
   - Calcola colonne dalla x dei separatori verticali
   - `<jr:table>` con column widths = distanza tra separatori

5. **Immagini (da `page.images`):**
   - `<image>` con coordinate esatte da pdfplumber

---

### FASE 3 — Loop di Convergenza

```
REPEAT:
  1. Render JRXML → PDF (Renderer.java o fallback manuale)
  2. Rasterizza output a 150dpi (pdftoppm)
  3. Calcola pixel diff per pagina (threshold 30, Python + PIL)
  4. SE diff < 2% per TUTTE le pagine → STOP (successo)
  5. SE diff non migliora per 3 iterazioni consecutive → CAMBIA STRATEGIA
  6. Analizza con pdfplumber ANCHE l'output corrente
  7. Calcola delta per-elemento: pdfplumber(reference) vs pdfplumber(output)
  8. Per ogni elemento con delta > 1pt:
     a. Font size sbagliato? → Correggi con valore esatto da pdfplumber
     b. Posizione Y sbagliata? → Applica offset dal delta
     c. Posizione X sbagliata? → Correggi x nel reportElement
     d. Width sbagliata (wrapping diverso)? → Correggi width
     e. Testo troncato (height insufficiente)? → Aumenta height
     f. Elemento mancante? → Aggiungi
  9. Applica TUTTE le correzioni in un batch
  10. GOTO 1
```

| 🟡 MEDIO (reversibile) — DevForge · siae-jasper-from-pdf |
|:---|
| Iterazione convergenza · diff pixel attuale: `XX%` → target: `<2%` |
| **Azione:** Applica N correzioni batch al JRXML |
| Se il diff aumenta: revert e analizza |

**IRON RULE DEL LOOP:**
- Ogni iterazione DEVE ridurre il diff OPPURE cambiare strategia
- Log il diff % ad ogni iterazione con tabella progressiva
- Se il diff AUMENTA → revert immediato e diagnosi
- Escalation a 10 iterazioni (vedi Strategie di Escalation). Hard stop a 20

---

### FASE 4 — Validazione Finale

REQUIRED SUB-SKILL: siae-verification

1. `xmllint --noout *.jrxml` per validare XML
2. Render con dati di test edge-case (nomi lunghi, importi grandi)
3. Verifica `pdffonts output.pdf` → font embedded
4. Pixel-diff finale con evidenza numerica
5. Report convergenza:

```
=== REPORT CONVERGENZA ===
Pagina 1: XX.XX% → YY.YY% (N iterazioni)
Pagina 2: XX.XX% → YY.YY% (N iterazioni)
Font: [lista font embedded]
Parametri: [lista parametri]
Producer reference: [Chrome/Jasper/altro]
Soglia raggiunta: SI/NO
Floor tecnico documentato: [se applicabile]
```

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "E' abbastanza simile" | "Abbastanza" non supera il gate del 2%. Misura. |
| "Solo il footer e' diverso" | Un footer diverso e' un pixel diff. Correggi. |
| "I font sono quasi uguali" | "Quasi" = hinting diverso = cascata di differenze. Usa il font esatto. |
| "Conosco gia' le coordinate" | Le conosci? pdfplumber le ha confermate? |
| "Una iterazione in piu' non serve" | Se il diff e' > 2%, serve. Non decidere tu, decide il numero. |
| "Stimo la font size a occhio" | L'occhio sbaglia di 1-2pt. pdfplumber no. |
| "Il rendering JasperReports non puo' fare meglio" | Documenta il floor tecnico con evidenza, non con opinione. |
| "Il PDF originale e' fatto male" | Il reference e' la verita'. Replica, non giudicare. |
| "Compilo e vedo se sembra ok" | "Sembra ok" non e' una metrica. pixel-diff lo e'. |
| "Manca poco, dichiaro completato" | <2% per OGNI pagina, o non e' completato. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura/analisi PDF reference | SICURO | No |
| Installazione brew packages | SICURO | No |
| Creazione venv Python + pip install | SICURO | No |
| Rasterizzazione PDF (pdftoppm) | SICURO | No |
| Creazione/modifica JRXML | SICURO | No |
| Rendering JRXML → PDF | SICURO | No |
| Pixel diff (Python/magick) | SICURO | No |
| Iterazione batch correzioni | MEDIO | Si |
| Copia font di sistema | MEDIO | Verifica licenza |
| Pubblicazione su repo | ALTO | Chiedi conferma |

---

## Strategie di Escalation

Se dopo 10 iterazioni il diff e' ancora > 2%:

1. **Floor tecnico engine diverso**: se `pdfinfo` mostra producer Chrome/Skia/WeasyPrint:
   - Il text shaper di JasperReports/iText (Java AWT) differisce da HarfBuzz/Skia
   - Anche con font identici (verificato con fonttools), il posizionamento sub-pixel diverge
   - Floor tipico: ~5-10% per pagine dense, ~3-5% per pagine semplici
   - **Azione:** documenta con evidenza, proponi soglia alternativa

2. **Fine-tuning per-elemento**:
   - Usa pdfplumber su ENTRAMBI i PDF (reference + output)
   - Calcola delta per-parola (non per-blocco)
   - Applica offset Y individuali per gli elementi con delta > 1pt

3. **Cambio engine**: se il reference e' HTML→PDF:
   - Converti layout in HTML+CSS template
   - Genera PDF con Puppeteer/Playwright (stesso engine del reference)
   - Mantieni JRXML come fallback per sistemi JasperReports

---

## Vincoli

1. **Font**: usa SOLO font presenti nel sistema o embedded nel PDF reference. NON scaricare font da internet.
2. **Coordinate**: SEMPRE in punti PDF (1pt = 1/72 inch). pdfplumber e JRXML usano la stessa unita'.
3. **PDF/A**: disabilita per rendering di test. Riabilita nel JRXML finale se richiesto.
4. **Parametri**: ogni valore dinamico → `$P{nome_parametro}`.
5. **Encoding**: UTF-8 everywhere. Identity-H per font CID TrueType.
6. **NO hallucination**: se non riesci a estrarre un valore dal PDF, chiedi all'utente. NON inventare.

---

## Strumenti

### Obbligatori (BLOCCANTI)

| Strumento | Uso | Installazione | Check |
|---|---|---|---|
| Java (OpenJDK) | Compilare/eseguire JRXML | `brew install openjdk` | `java -version` |
| Maven | Dipendenze JasperReports | `brew install maven` | `mvn -v` |
| poppler | pdftoppm, pdftotext, pdffonts, pdfinfo | `brew install poppler` | `which pdftoppm` |
| **pdfplumber** | **Estrazione coordinate, font, rects, curves** | `pip install pdfplumber` | `python3 -c "import pdfplumber"` |
| **PyMuPDF** | **Estrazione font embedded, drawings** | `pip install pymupdf` | `python3 -c "import fitz"` |
| **Pillow** | Analisi immagini, heatmap | `pip install Pillow` | `python3 -c "from PIL import Image"` |
| **numpy** | Calcolo pixel-diff, metriche | `pip install numpy` | `python3 -c "import numpy"` |

### Opzionali (DEGRADATI se assenti)

| Strumento | Uso | Installazione | Check |
|---|---|---|---|
| ImageMagick | Pixel diff veloce (`magick compare`) | `brew install imagemagick` | `which magick` |
| mupdf-tools | Estrazione font embedded (`mutool extract`) | `brew install mupdf-tools` | `which mutool` |
| fonttools | Confronto metriche font | `pip install fonttools` | `python3 -c "from fontTools.ttLib import TTFont"` |
| scipy | Blob detection (connected components) | `pip install scipy` | `python3 -c "from scipy import ndimage"` |
| diff-pdf-visually | Confronto visivo rapido | `pip install diff-pdf-visually` | `python3 -c "import diff_pdf_visually"` |
| qpdf | Merge PDF multipagina | `brew install qpdf` | `which qpdf` |

---

## Gestione Errori Installazione

Se `pip install` fallisce per una libreria:

```
ERRORE INSTALLAZIONE: {libreria} non installabile.
Errore pip: {messaggio_errore}

Tentativi di recovery:
1. pip install {libreria} --no-cache-dir
2. pip install {libreria} --user
3. pip install {libreria} --no-binary :all:

Se nessuno funziona:
- Verifica che python3-dev/python3-devel sia installato
- Verifica che pip sia aggiornato: pip install --upgrade pip
- Verifica connessione internet e proxy

Stato skill: {BLOCCATA se critica | DEGRADATA se opzionale}
```

Se `brew install` fallisce:

```
ERRORE INSTALLAZIONE: {pacchetto} non installabile via brew.
Errore: {messaggio_errore}

Alternative:
1. brew update && brew install {pacchetto}
2. Installa manualmente da {url_download}
3. Usa un package manager alternativo (port, nix)

Se su Linux: apt-get install {pacchetto_apt} / yum install {pacchetto_yum}
Se su Windows: choco install {pacchetto_choco} / scoop install {pacchetto_scoop}

Stato skill: {BLOCCATA | DEGRADATA}
```

---

## Permission Denied Handling

Se l'utente nega un tool:
- `brew install` negato → mostra comando esatto, chiedi di eseguire manualmente con `! brew install ...`
- `pip install` negato → mostra il pip install completo per copia manuale
- Rendering negato → fornisci i comandi esatti da eseguire fuori dalla sessione
- Scrittura file negata → mostra il contenuto JRXML per copia manuale
