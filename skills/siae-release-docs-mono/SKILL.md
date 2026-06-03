---
name: siae-release-docs-mono
description: >
  Use when devi generare in un colpo solo TUTTI i documenti di un rilascio EDW
  SIAE (NDR DL, NDR RS, GDC, slide architettura, DDE) partendo da un singolo
  YAML manifesto. Versione "mono/monolitica": tutta la logica di
  orchestrazione e generazione vive in questa skill, senza dipendenze da
  altre skill. Trigger: genera tutti i documenti, suite rilascio EDW,
  EDW_XX.XX docs completi, full release docs, DMND000XXXX documenti,
  /forge-release-docs-mono.
---

# Release Docs Mono (Monolithic) - DevForge

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║         🔨 DevForge · RELEASE DOCS MONO (MONOLITHIC)            ║
║         "Il codice si forgia. Il developer cresce."             ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Monolithic generator | **Fase SDLC:** Rilascio EDW completo

---

## Obiettivo

Generare in **una singola invocazione self-contained** l'intera suite
documentale di un rilascio EDW SIAE — NDR DL, NDR RS, GDC, slide
architettura DL/RS + PNG, DDE cumulativo — leggendo **un solo YAML
manifesto** e producendo tutti gli output con un workflow integrato.

A differenza di `siae-release-docs-pack` (che delega a 5 sub-skill via
Skill tool), questa skill **incorpora tutta la logica direttamente**:
- Tutti i workflow step sono documentati qui
- Tutti gli LL/vincoli specifici sono richiamati qui
- Le reference dettagliate (snippet python-docx/pptx) restano nei file
  delle 5 skill esistenti come "deep dive technical reference", ma il
  workflow operativo e tutti i punti di decisione sono in questa skill

Output prodotti (max 5 file + 2 PNG):
1. NDR DL `.docx`
2. NDR RS `.docx`
3. GDC `.pptx`
4. Architettura `.pptx` (file master aggiornato)
5. DDE `.docx` (file master cumulativo aggiornato)
6. `architettura_DL.png` + `architettura_RS.png`

---

## Quando si Applica

**Sempre:**
- Hai un rilascio EDW pronto (DMND, EDW release, CHG assegnati)
- YAML manifesto compilato e validato
- I template/master precedenti sono disponibili:
  - `<base>/NDR DL/<piu' recente>.docx`
  - `<base>/NDR/<piu' recente>.docx`
  - `<base>/GDC/<piu' recente o _TEST>.pptx`
  - `<base>/DDE/DDE-DataPlatform-Ingestion-<versione>.docx`
  - `<base>/Architettura DDE/DdE - Architettura - New.pptx`

  dove `<base>` = `C:\Users\frmonaco\Downloads\Claude documentazione\`

**Eccezioni (chiedi al partner):**
- Solo un sottoinsieme di documenti richiesto → usa la skill specifica
  esistente (es. `gdc-generator` standalone)
- YAML incompleto / valori `null` / `TBD` → fermati e chiedi
- Generazione gia' iniziata manualmente → conferma sovrascrittura
- Multi-Wave dello stesso rilascio in un colpo → due invocazioni separate,
  una per Wave (i CHG e i path NAS sono diversi)

---

## Legge di Ferro

> **Una sola fonte di verita' YAML, una sola invocazione, 5 output coerenti.**
>
> Tutti i parametri condivisi (`dmnd_id`, `edw_release`, `titolo_progetto`,
> `chg_id_*`, `oggetti_redshift`) devono essere identici nei 5 documenti.
> Coerenza cross-doc e' obbligatoria — se anche una sola riga del DDE
> cita un conteggio diverso da quello della GDC, il rilascio si blocca
> in call con SIAE.
>
> **Conteggi, lista oggetti, lista tabelle, host sorgenti**: SEMPRE
> dal partner via YAML. Mai dedurre, mai inferire, mai lasciare `TBD`.

---

## Istruzioni

### Step 0 - Carica YAML e validazione

🟡 MEDIO - Mostra pre-flight card prima di eseguire

| 🟡 MEDIO (reversibile) - 🔨 DevForge · siae-release-docs-mono |
|:---|
| 🛠️ Operazione: `Carica YAML + validazione semantica` · 📁 Scope: `YAML manifesto` |
| **▼ Azione** |
| 1. ✏️ Verifica path YAML esistente e parsabile. |
| 2. ✏️ Valida sezioni obbligatorie: `release.*`, `layer_impattati.*`, `chg_numbers.*`, `sorgente.*`, `narrativa.*`. |
| 3. ✏️ Valida campi cross-sezione condivisi (vedi LL "no count inference", LL ARCH-10 host). |
| 4. ✏️ Stampa la matrice "quali documenti verranno generati". |
| 💡 Perche': YAML invalido = fallimento a meta' flusso. Investa 2 minuti ora per non perdere 30 minuti dopo. |
| 🚫 Se NO: Output parziali, debugging confuso, rollback manuale. |

**Validazioni semantiche obbligatorie** (vedi
[reference/yaml-schema-validation.md](reference/yaml-schema-validation.md)
per la lista completa):

| Campo | Regola | LL riferimento |
|---|---|---|
| `release.dmnd_id` | formato `DMND\d{7}` | - |
| `release.edw_release` | formato `\d{2}\.\d{2}` | - |
| `layer_impattati.*` | almeno uno true tra DL/RS | - |
| `sorgente.new_sources[*].host` | NON null, NON `TBD` (esplicito `N.A.` ok per on-prem) | LL ARCH-10, LL DL-N |
| `dde.lista_tabelle_rilascio` | non vuota se DDE da generare | LL DDE-22 |
| `chg_numbers.<layer>` | popolato per ogni layer impattato | - |
| `pacchetto_software.etl_glue` | conteggio coerente con `oggetti_redshift` length | - |

Se una validazione fallisce, **fermati** e chiedi al partner di sistemare
il YAML.

**Matrice generazione**:

```
Layer DL:    NDR DL   GDC sez DL    DDE cap DL    Arch slide DL    Arch PNG DL
Layer RS:    NDR RS   GDC sez RS    DDE cap RS    Arch slide RS    Arch PNG RS
Sempre:               GDC base       DDE revisioni
```

### Step 1 - Localizza master files + crea cartelle output

🟢 SICURO

Path standard (override possibili nello YAML):

```python
BASE = Path(r"C:\Users\frmonaco\Downloads\Claude documentazione")
NDR_DL_REF  = pick_latest(BASE / "NDR DL", "*.docx")
NDR_RS_REF  = pick_latest(BASE / "NDR", "*.docx")
GDC_REF     = BASE / "GDC" / "DMND000XXXXX - GDC - AWS Data Platform - EDW_XX_XX_TEST.pptx"
GDC_PREV    = pick_latest(BASE / "GDC", "DMND0*.pptx")  # GDC precedente per cumulativa
DDE_MASTER  = pick_latest(BASE / "DDE", "DDE-DataPlatform-Ingestion-*.docx")
ARCH_PPTX   = BASE / "Architettura DDE" / "DdE - Architettura - New.pptx"

OUTPUT_DIR  = Path(yaml["release"]["output_dir"])
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "architettura").mkdir(exist_ok=True)
```

**Backup automatico** del DDE master e dell'architettura pptx (entrambi
modificati in-place): copia in `<dir>/file storici/<file>_backup_<ts>.<ext>`.

### Step 2 - Genera NDR DL (se DL impattato)

🟢 SICURO - Workflow inline, riusa pattern documentati in `ndr-generator-dl`

**Flow**:
1. Copia `NDR_DL_REF` in `<output>/DMND<N> - NDR - EDW Data Lake - EDW_<X.YY>_DL[ - WAVE N].docx`
2. Apri con `python-docx`, applica modifiche:
   - Front-matter: dmnd_id, chg_id_dl, edw_release, titolo, date
   - Sez 1.1: testo scopo + tabella pacchetto software (LL DL-H)
   - Sez 2.8.2: clona blocco template, preserva indentazioni numbered/bullet
     (LL DL-A + **LL DL-L rafforzata**), sostituisci solo `<w:t>`
   - Sez 3.1 TABLE #12: append filtro per nuova sorgente (LL DL-F + LL DL-J)
   - Sez 4.1 TABLE #13 + #14: censimento sorgente + DMS task
   - Table 10 monitoraggio: **clona dalla NDR DL piu' recente** preservando
     filtri precedenti, appendi nuovi (LL DL-M)
3. Applica page break standard (LL2)
4. Verifica post-save: re-leggi, controlla numero tabelle (12-13), placeholder
   residui (`CHG00XXXXX`, `XX/XX/2026`, `TBD`)

**Dettagli tecnici**: vedi
[ndr-generator-dl/reference/docx-generation.md](../ndr-generator-dl/reference/docx-generation.md)
per gli snippet python-docx (LL1-LL12 + LL DL-A → LL DL-N).

### Step 3 - Genera NDR RS (se RS impattato)

🟢 SICURO - Workflow inline, riusa pattern documentati in `ndr-generator`

**Flow**:
1. Copia `NDR_RS_REF` in `<output>/DMND<N> - NDR - EDW Redshift - EDW_<X.YY>_RS[ - Wave N].docx`
2. Apri con `python-docx`, applica modifiche:
   - Front-matter, sezioni boilerplate, sez 2.5.x varianti condizionali
   - Sez 1.1: tabella pacchetto software + **tabella QVD sempre presente
     anche se tutti `N.A.`** (LL13)
   - Sez 4.2: tabella oggetti Redshift con shading alternato (LL7)
3. Applica page break (LL6) + verifica visiva PDF render (LL6.bis)
4. Verifica post-save

**Dettagli tecnici**: vedi
[ndr-generator/reference/docx-generation.md](../ndr-generator/reference/docx-generation.md)
(LL5-LL13).

### Step 4 - Genera GDC

🟡 MEDIO - Mostra pre-flight card

| 🟡 MEDIO (reversibile) - 🔨 DevForge · siae-release-docs-mono → GDC |
|:---|
| 🛠️ Operazione: `Genera GDC PowerPoint` · 📁 File: `<output>/DMND<N> - GDC - ... .pptx` |
| **▼ Azione** |
| 1. ✏️ Copia template `GDC_REF` (o `GDC_PREV` per la lista cumulativa schemi DB Glue + stg). |
| 2. ✏️ Applica modifiche 13 slide secondo `slide-placeholders.md`. |
| 3. ✏️ Rispetta ordine slide 5/6 (Rilasci propedeutici PRIMA di N/A firewall - LL33). |
| 4. ✏️ Slide 3 testo `(RIC):` con due punti (LL34). |
| 5. ✏️ Slide 13 path NAS Qlik formato `-Qlik` compatto (LL32). |
| 6. ✏️ Rimuovi highlight giallo residui (LL4). |
| 💡 Perche': La GDC e' presentata in call con SIAE — placeholder o slide invertite sono visibili. |
| 🚫 Se NO: Imbarazzo in call + ridiscussione del rilascio. |

**Dettagli tecnici**: vedi
[gdc-generator/reference/pptx-generation.md](../gdc-generator/reference/pptx-generation.md)
(LL1-LL34, in particolare LL33-LL34 nuovi dalla review 2026-05-20).

### Step 5 - Genera slide architettura + PNG export

🟡 MEDIO - Mostra pre-flight card

| 🟡 MEDIO (reversibile) - 🔨 DevForge · siae-release-docs-mono → Arch |
|:---|
| 🛠️ Operazione: `Slide arch + esporta PNG per DDE` · 📁 Scope: `arch pptx + 2 PNG` |
| **▼ Azione** |
| 1. ✏️ Verifica `architecture.new_sources[*].host` valorizzato (LL ARCH-10). Se `null`/`TBD` → ferma. |
| 2. ✏️ Backup `ARCH_PPTX` in `file storici/`. |
| 3. ✏️ Clona slide template DL (es. `EDW_XX.YY_DL - WAVE 1`) e modifica: release code, acquisizione, clona group Vlz Performing (`aurora_rds`) o Sport (`external`), riposiziona oval. |
| 4. ✏️ Idem per RS, oval RS resta su Redshift (LL ARCH pattern fisso). |
| 5. ✏️ **Inserisci slide nuove in fondo al blocco layer**, NON in coda al pptx (LL ARCH-9). Default: subito dopo W1 della stessa release. |
| 6. ✏️ Esporta PNG via PowerPoint COM (`width=1920px`). |
| 💡 Perche': I PNG sono input obbligatori per Step 6 (DDE embed). |
| 🚫 Se NO: DDE con placeholder testuale (LL DDE-23 violato). |

**Dettagli tecnici**: vedi
[architecture-slides-generator/reference/lessons-learned.md](../architecture-slides-generator/reference/lessons-learned.md)
(LL ARCH-1 → LL ARCH-10).

### Step 6 - Genera capitoli DDE (con embed PNG)

🟡 MEDIO - Mostra pre-flight card

| 🟡 MEDIO (reversibile) - 🔨 DevForge · siae-release-docs-mono → DDE |
|:---|
| 🛠️ Operazione: `Append capitoli DDE + embed PNG arch + tabelle cumulative` · 📁 File: `<DDE_MASTER>` |
| **▼ Azione** |
| 1. ✏️ Backup `DDE_MASTER` in `file storici/`. |
| 2. ✏️ **Verifica gap capitoli** vs documenti su disco (LL DDE-24): se mancano cap di rilasci precedenti, ferma e chiedi. |
| 3. ✏️ Determina prossimi N capitoli (max 2: cap N=DL, cap N+1=RS). |
| 4. ✏️ Clona cap DL template (es. `EDW_01.21_DL`), sostituisci stringhe variabili. |
| 5. ✏️ **Tabella monitoraggio cap DL**: clona dalla cap DL precedente del DDE (LL DDE-21), appendi righe per nuova sorgente. NON ricostruire. |
| 6. ✏️ **Embed PNG architettura DL** al posto di `[placeholder architettura]` (LL DDE-23). |
| 7. ✏️ Idem cap RS con PNG `architettura_RS.png`. |
| 8. ✏️ **Tabella finale cumulativa**: append 1 riga per ogni entry in `dde.lista_tabelle_rilascio` (LL DDE-22). Fermati se la sezione manca nel YAML. |
| 9. ✏️ Aggiungi righe tabella revisioni (1 per cap aggiunto). |
| 💡 Perche': Il DDE e' la verita' storica del Data Platform — errori restano per anni nel documento. |
| 🚫 Se NO: DDE inconsistente, capitoli con placeholder o tabelle obsolete. |

**Dettagli tecnici**: vedi
[dde-generator/reference/docx-append.md](../dde-generator/reference/docx-append.md)
(LL DDE-1 → LL DDE-24, in particolare LL DDE-21/22/23/24 dalla review 2026-05-20).

### Step 7 - Verifica cross-doc + report finale

🟡 MEDIO - Mostra pre-flight card

| 🟡 MEDIO (reversibile) - 🔨 DevForge · siae-release-docs-mono → Verify |
|:---|
| 🛠️ Operazione: `Coerenza cross-documento + report` · 📁 Scope: `5 output files` |
| **▼ Azione** |
| 1. ✏️ Riapri tutti i file, estrai metadati chiave. |
| 2. ✏️ Verifica `dmnd_id`, `edw_release`, `titolo_progetto` identici nei 5. |
| 3. ✏️ Verifica conteggi coerenti GDC slide 1 = NDR DL Table 4 = DDE cap DL. |
| 4. ✏️ Verifica lista oggetti NDR RS sez 4.2 = DDE cap RS Riepilogo (count + names). |
| 5. ✏️ Verifica nessun placeholder residuo: `CHG00XXXXX`, `XX/XX/2026`, `TBD`, `«Titolo Progetto»`, `EDW_XX.XX`. |
| 6. ✏️ Verifica numero entry `lista_tabelle_rilascio` YAML = numero righe aggiunte in tabella finale DDE. |
| 7. ✏️ Produci report markdown con path output, dimensioni, eventuali warning. |
| 💡 Perche': Un'incoerenza tra documenti scoperta in call SIAE blocca il rilascio. Scoprila ora. |
| 🚫 Se NO: Errori scoperti tardi, ripetizione del rilascio. |

**Report finale**: sezione promemoria unificato con tutte le operazioni
manuali residue:
- GDC: rivedere slide 2 architettura (manuale, sempre)
- Arch pptx: disegnare connettori DMS → nuova sorgente (LL ARCH-1)
- DDE: aggiornare TOC (click destro → Aggiorna campo), compilare colonna
  "Pagina" tabella revisioni (post-render PDF)
- NDR DL/RS: rimuovere highlight giallo residui (se restano)

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Carica YAML + validazione | 🟡 Medio | Si |
| Localizza master + backup | 🟢 Sicuro | No |
| Genera NDR DL | 🟢 Sicuro | No |
| Genera NDR RS | 🟢 Sicuro | No |
| Genera GDC | 🟡 Medio | Si |
| Genera architettura + PNG | 🟡 Medio | Si |
| Append DDE + embed PNG | 🟡 Medio | Si |
| Verifica cross-doc + report | 🟡 Medio | Si |

---

## Vincoli

1. **Ordine fisso** Step 1 → 7. NDR genera input per GDC; architettura
   genera input per DDE. Non scambiare.
2. **YAML unico = fonte di verita'**. Ogni step legge la propria sezione.
   Se mancano campi, ferma e chiedi al partner — non inferire.
3. **Backup automatico** dei file modificati in-place: DDE master e
   architettura pptx. Mai sovrascrivere senza copia di sicurezza.
4. **Skip layer non impattato**: salta NDR DL + cap DL DDE + slide arch DL
   se `layer_impattati.data_lake=false`. Stesso per RS.
5. **Errore step = stop globale**: non procedere ai successivi se uno step
   fallisce. Output parziali sono peggio di nessun output.
6. **PRE-FLIGHT OBBLIGATORIA** per Step 0, 4, 5, 6, 7 (operazioni con scrittura).
7. **Coerenza cross-doc**: i 5 documenti devono concordare su tutti i
   parametri condivisi. Step 7 e' un gate, non un nice-to-have.
8. **Convenzione naming**:
   - NDR DL: `DMND<N> - NDR - EDW Data Lake - EDW_<X.YY>_DL[ - WAVE N].docx`
   - NDR RS: `DMND<N> - NDR - EDW Redshift - EDW_<X.YY>_RS[ - Wave N].docx`
     (NB: `WAVE` maiuscolo per DL/DDE, `Wave` mixed-case per RS/GDC —
     convenzione storica SIAE)
   - GDC: `DMND<N> - GDC - AWS Data Platform - EDW_<X.YY>[ - Wave N].pptx`
   - DDE: `DDE-DataPlatform-Ingestion-<versione>.docx` (in-place)
   - Arch: `DdE - Architettura - New con <release> Wave <N>.pptx`

---

## Tabella Anti-Razionalizzazione

| Tentazione | Realta' | Azione corretta |
|-----------|---------|-----------------|
| "Salto Step 5 (architettura) se i PNG li ho gia'" | I PNG vecchi mostrano la sorgente vecchia, il DDE diventa sbagliato. | Rigenera sempre se il rilascio cambia sorgente. |
| "Genero tutto in parallelo per velocita'" | Dipendenze esistono: GDC ha bisogno dei conteggi NDR, DDE ha bisogno dei PNG arch. | Sequenziale rigoroso. La velocita' viene dall'automazione, non dal parallelismo. |
| "Salto verifica cross-doc Step 7 perche' il rilascio e' urgente" | Discrepanze scoperte in call con SIAE = rilascio bloccato. Step 7 dura 30s. | Sempre Step 7 prima di consegnare. |
| "Ricomputo i conteggi dal repo invece di chiederli al partner" | Vietato per `feedback_no_count_inference`. Il partner sa lo scope reale. | Chiedi. Sempre. |
| "Lascio host=null nell'architettura perche' tanto lo metto a mano" | LL ARCH-10: skill si ferma se host non valorizzato. Nessuna manualita' tollerata in output. | Compila lo YAML prima di lanciare. |

---

## Risorse Aggiuntive

- [reference/yaml-schema-validation.md](reference/yaml-schema-validation.md) - Schema YAML unificato + tutte le validazioni semantiche.
- [reference/workflow-detailed.md](reference/workflow-detailed.md) - Workflow dettagliato step-by-step con snippet di codice.
- [reference/cross-doc-coherence.md](reference/cross-doc-coherence.md) - Checklist coerenza cross-documento + script di verifica.

Per i dettagli implementativi profondi (snippet python-docx/pptx, LL
specifiche di formattazione), questa skill rimanda alle reference delle
5 skill esistenti come "deep technical reference":
- [ndr-generator-dl/reference/](../ndr-generator-dl/reference/)
- [ndr-generator/reference/](../ndr-generator/reference/)
- [gdc-generator/reference/](../gdc-generator/reference/)
- [architecture-slides-generator/reference/](../architecture-slides-generator/reference/)
- [dde-generator/reference/](../dde-generator/reference/)

Questo riuso e' **per documentazione**, non per delega di esecuzione:
la mono **esegue inline** tutta la logica documentata in quei file, non
invoca le 5 skill.

---

## Differenze vs `siae-release-docs-pack`

| Aspetto | Mono (questa skill) | Pack |
|---------|---------------------|------|
| Logica | Inline | Delegata via Skill tool |
| Dipendenze | Self-contained | Richiede le 5 skill installate |
| LL aggiornate | Modificando direttamente questa | Solo modificando le 5 skill |
| Riga di codice | ~1500 (orchestratore + reference) | ~400 (controller compatto) |
| Velocita' | Piu' veloce (1 sola skill) | Piu' lenta (5 invocazioni) |
| Manutenibilita' | Media (file lungo, single source) | Alta (single responsibility per skill) |
| Quando preferire | Vuoi un singolo punto di gestione | Hai le 5 skill aggiornate e vuoi orchestrarle |
