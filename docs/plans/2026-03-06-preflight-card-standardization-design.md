# Standardizzazione Pre-Flight Card — Design Doc

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` per implementare questo piano task per task.

**Goal:** Unificare il template pre-flight card in un unico design adattivo, eliminando le 5 varianti inconsistenti attuali.
**Architettura:** Template unico a 4 zone (Header, Contesto, Operazioni, Footer) con larghezza adattiva (min 60, max 100), bordo colorato per livello rischio, emoji contestuali per ogni riga.
**Stack:** Markdown (SKILL.md files), design-system/devforge-visual.md

---

## Contesto

### Problema

L'audit delle skill ha rivelato **5 varianti diverse** di pre-flight card:

| Skill | Header | Conforme? |
|-------|--------|-----------|
| devforge-visual.md (template) | `🔨 DevForge — [EMOJI] [LIVELLO]...` | Riferimento |
| siae-finishing-branch | `PRE-FLIGHT CARD — Apertura PR` + `Rischio: 🔴 ALTO` | NO |
| siae-qa | `🔨 DevForge — SIAE QA · Pre-flight Check` | PARZIALE |
| siae-automation | `🔨 DevForge — SIAE Automation · Pre-flight Check` | PARZIALE |
| siae-security | `🔨 DevForge — 🚨 CRITICO · Secret rilevato` | SI |
| siae-documentation | `🔨 DevForge — 🔴 RISCHIO ALTO · 1 operazione` | QUASI |

### Problemi principali

1. Header non standardizzato (4 formati diversi)
2. Card "informativa" vs "permissiva" non distinte
3. Campi body arbitrari per skill
4. Bordo sbagliato (QA/Automation usano `╔══╗` senza livello rischio)
5. Footer mancante in 3 skill su 5
6. Larghezza fissa (68 char) troppo stretta, card spesso disallineate

---

## Design Approvato

### Approccio: Template Unico Flessibile a 4 Zone

Un singolo template con **4 zone** in ordine fisso. L'header e il footer sono obbligatori. Le zone centrali (Contesto e Operazioni) sono opzionali.

### Le 4 Zone

| Zona | Nome | Contenuto | Obbligatoria? |
|------|------|-----------|---------------|
| Z1 | **Header** | Branding + livello rischio + nome skill | SEMPRE |
| Z2 | **Contesto** | Righe key:value con stato/ambiente rilevato | Se la skill ha info di contesto |
| Z3 | **Operazioni** | Lista numerata di azioni con file/path | Se ci sono azioni da eseguire |
| Z4 | **Footer** | 💡 Perché + 🚫 Se NO | SEMPRE |

### Griglia Adattiva

```
Larghezza:     adattiva al contenuto
Min:           60 caratteri (bordi inclusi)
Max:           100 caratteri (bordi inclusi)
Margine sx:    2 spazi sempre
Label column:  allineata a ":" + spazi
Valore:        riempie lo spazio restante
Emoji:         contano 2 char di larghezza
```

### Wrapping

- Testo lungo: wrap su confini di parola (spazi)
- Path lunghi: wrap su `/` (token senza spazi)
- Righe di continuazione: indent allineato al valore (dopo `:`)
- Bordi: MAI sfondati — il contenuto si adatta, non il bordo

### Bordo per Livello di Rischio

| Livello | Bordo | Caratteri | Colore ANSI |
|---------|-------|-----------|-------------|
| 🟢 SICURO | Nessuna card | — | — |
| 🟡 MEDIO | Doppio | `╔═╗ ║ ╠ ╚╝` | `\e[33m` giallo |
| 🔴 ALTO | Pesante | `┏━┓ ┃ ┣ ┗┛` | `\e[31m` rosso |
| 🚨 CRITICO | Pesante | `┏━┓ ┃ ┣ ┗┛` | `\e[1;31m` rosso bold |

### Regola ANSI

Ogni riga intera della card e' wrappata nel colore del livello:

```
[COLORE]bordo_sx[RESET]  contenuto paddato  [COLORE]bordo_dx[RESET]
```

### Header — Formato Fisso

```
  🔨 DevForge — [EMOJI] [LIVELLO] ([sottotitolo]) · [skill-name]
```

Dove:
- `[EMOJI]` = 🟡 / 🔴 / 🚨
- `[LIVELLO]` = MEDIO / ALTO / CRITICO
- `([sottotitolo])` = `(reversibile)` / `(difficile da annullare)` / `(irreversibile)`
- `[skill-name]` = nome della skill che genera la card

### Emoji Contestuali

**Z2 Contesto** — emoji che descrivono il campo:

| Emoji | Uso |
|-------|-----|
| 📡 | Tier/connessione |
| 🎫 | Ticket Jira/Story |
| ✅ | Disponibilita'/check |
| 📚 | Confluence/docs |
| 🌿 | Branch git |
| 🎯 | Target/base |
| 📝 | Commit/note |
| 🧪 | Test suite |
| 📋 | Piano/modulo |
| 🔢 | Task/numerazione |
| 🤖 | Subagent/bot |
| 📱 | Canale mobile |
| ☁️ | Cloud/BrowserStack |
| 🔄 | Sync/tipo |
| 📦 | Package/dipendenza |
| 📁 | Directory/working dir |
| 🔧 | Comando/config |
| 🔑 | Pattern/secret |
| 📊 | Confidence/stats |
| 🗄️ | Database |
| 🔐 | Credenziali/rotazione |
| 🌍 | Scope/ambiente |
| 🏗️ | Ambiente infra |

**Z3 Operazioni** — emoji che descrivono l'azione:

| Emoji | Uso |
|-------|-----|
| ✏️ | Creazione file |
| 📝 | Modifica file |
| 🗑️ | Eliminazione |
| 📥 | Installazione dipendenza |
| 🔀 | Refactoring/rinomina |
| 🖥️ | Esecuzione shell |
| 🔧 | Modifica schema/config |
| 📌 | Git commit |
| 🚀 | Git push / PR |
| 📤 | Pubblicazione esterna |
| ⚡ | Dispatch subagent |
| 🧪 | Test |
| ⚠️ | Alert critico |

**Z3 Path + Z4 Footer** — fissi:

| Emoji | Uso |
|-------|-----|
| 📂 | File/Path (sempre) |
| 💡 | Perche' (sempre) |
| 🚫 | Se NO (sempre) |

### Combinazioni Zone Valide

| Caso d'uso | Z1 | Z2 | Z3 | Z4 |
|------------|----|----|----|----|
| Contesto puro (QA/Automation apertura) | ✅ | ✅ | — | ✅ |
| Operazioni pure (documentation publish) | ✅ | — | ✅ | ✅ |
| Contesto + operazioni (finishing-branch, security) | ✅ | ✅ | ✅ | ✅ |

### Esempi Canonici per Livello

#### 🟡 MEDIO — Card di contesto (siae-qa)

```
╔═══════════════════════════════════════════════════════════════════╗
║  🔨 DevForge — 🟡 MEDIO (reversibile) · siae-qa                   ║
╠═══════════════════════════════════════════════════════════════════╣
║  📡 Tier attivo:    Tier 1 MCP                                    ║
║  🎫 Story Jira:     PROJ-456                                      ║
║  ✅ AC disponibili: Si — 5 AC in description                       ║
║  📚 Confluence:     Spazio QA trovato                              ║
╠═══════════════════════════════════════════════════════════════════╣
║  💡 Perche':        Il tier determina come si sincronizzano TC     ║
║  🚫 Se NO:          Workflow QA non inizia                         ║
╚═══════════════════════════════════════════════════════════════════╝
```

#### 🔴 ALTO — Card completa (siae-finishing-branch)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔨 DevForge — 🔴 ALTO (difficile da annullare) · siae-finishing-branch    ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  🌿 Branch:         feature/PROJ-123-add-login                             ┃
┃  🎯 Target:         sviluppo                                               ┃
┃  📝 Commit:         4 commit                                               ┃
┃  🧪 Test suite:     12/12 passed                                           ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  1. 🚀 Azione:      Push branch + apertura PR via gh                       ┃
┃     📂 File/Path:   origin/feature/PROJ-123-add-login → sviluppo           ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  💡 Perche':        Branch pronto, test verdi, diff pulito                 ┃
┃  🚫 Se NO:          Il branch resta locale, nessun PR creato               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

#### 🚨 CRITICO — Card allarme (siae-security)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔨 DevForge — 🚨 CRITICO (irreversibile) · siae-security             ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  🔑 Pattern:        AWS_SECRET_ACCESS_KEY                             ┃
┃  📊 Confidence:     Alta — match regex completo                       ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  1. ⚠️  Azione:      Rilevato secret nel file sorgente                ┃
┃     📂 File/Path:   src/config/aws-config.ts:14                       ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  💡 Perche':        Credenziali in chiaro nel codice sorgente         ┃
┃  🚫 Se NO:          STOP — il secret va rimosso prima di procedere    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

#### 🟡 MEDIO — Card minima (siae-tdd)

```
╔══════════════════════════════════════════════════════════╗
║  🔨 DevForge — 🟡 MEDIO (reversibile) · siae-tdd         ║
╠══════════════════════════════════════════════════════════╣
║  1. 📝 Azione:      Modifica file test                   ║
║     📂 File/Path:   src/test.ts                          ║
╠══════════════════════════════════════════════════════════╣
║  💡 Perche':        Fase RED del TDD                     ║
║  🚫 Se NO:          Il ciclo non inizia                  ║
╚══════════════════════════════════════════════════════════╝
```

---

## Trade-off Scelti

| Decisione | Alternativa scartata | Motivazione |
|-----------|---------------------|-------------|
| Template unico flessibile | Due template (permesso vs contesto) | Meno regole da ricordare, un solo layout |
| Larghezza adattiva 60-100 | Larghezza fissa 68 | Le card corte restano compatte, quelle lunghe hanno spazio |
| Wrap su `/` per path | Troncamento con `…` | I path devono essere leggibili per intero |
| Z4 Footer sempre obbligatorio | Footer opzionale per card informative | Perche' e Se NO danno sempre valore |
| Emoji contestuali per riga | Nessuna emoji / emoji solo header | Scannabilita' visiva migliore |

---

## Stima

**Story Points: 3** — modifiche al design system + allineamento 6 skill + skill-template

---

## Criteri di Accettazione

- [ ] `devforge-visual.md` aggiornato con il nuovo template a 4 zone
- [ ] Tutte le skill con pre-flight card allineate al nuovo template
- [ ] Nessuna card usa il vecchio formato (header `PRE-FLIGHT CARD —`, `RISCHIO ALTO`, ecc.)
- [ ] `skill-template.md` aggiornato con il nuovo template
- [ ] Emoji catalog documentato nel design system
- [ ] Regole di wrapping (spazi + `/`) documentate
- [ ] Regole ANSI colore per bordo documentate

---

# Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` per implementare questo piano task per task.

**Goal:** Sostituire tutte le varianti di pre-flight card con il template unificato a 4 zone.
**Architettura:** Aggiornamento design-system (source of truth) → aggiornamento skill-template → allineamento skill individuali.
**Stack:** Markdown

---

## Task 1 — Aggiornare `design-system/devforge-visual.md`

**File:** `design-system/devforge-visual.md`

Sostituire le sezioni 0.3 (Pre-flight Card) e le 3 card template (MEDIO, ALTO, CRITICO) con:
- Template unificato a 4 zone (Z1 Header, Z2 Contesto, Z3 Operazioni, Z4 Footer)
- Regole griglia adattiva (min 60, max 100)
- Regole wrapping (spazi + `/`)
- Regola ANSI colore per riga
- Emoji catalog completo (Z2 contesto, Z3 azioni, Z4 footer)
- Combinazioni zone valide
- 4 esempi canonici (MEDIO contesto, MEDIO minima, ALTO completa, CRITICO allarme)
- Rimuovere la vecchia sezione "Come costruire una card raggruppata" e i vecchi template

## Task 2 — Aggiornare `skills/siae-writing-skills/reference/skill-template.md`

**File:** `skills/siae-writing-skills/reference/skill-template.md`

Aggiornare il template skill con:
- Riferimento al nuovo template pre-flight card
- Esempio di card nel template step (usando il formato Z1+Z3+Z4 minimo)

## Task 3 — Allineare `skills/siae-finishing-branch/SKILL.md`

**File:** `skills/siae-finishing-branch/SKILL.md`

Sostituire la card vecchia (linee ~188-205, formato `PRE-FLIGHT CARD — Apertura PR` con `Rischio: 🔴 ALTO` e checklist interna) con il nuovo template ALTO a 4 zone con Z2 contesto (Branch/Target/Commit/Test suite) + Z3 operazione (Push + PR) + Z4 footer.

## Task 4 — Allineare `skills/siae-qa/SKILL.md`

**File:** `skills/siae-qa/SKILL.md`

Sostituire la card vecchia (linee ~72-84, formato `🔨 DevForge — SIAE QA · Pre-flight Check` senza livello rischio) con il nuovo template MEDIO a 4 zone con Z2 contesto (Tier/Story/AC/Confluence) + Z4 footer.

## Task 5 — Allineare `skills/siae-automation/SKILL.md`

**File:** `skills/siae-automation/SKILL.md`

Sostituire la card di apertura (linee ~62-76, formato `🔨 DevForge — SIAE Automation · Pre-flight Check`) e la card di report (linee ~492-508) con il nuovo template MEDIO a 4 zone.

## Task 6 — Allineare `skills/siae-security/SKILL.md`

**File:** `skills/siae-security/SKILL.md`

La card attuale (linea ~172) e' quasi conforme. Aggiungere:
- Emoji contestuali su Z2 e Z3
- Z4 footer con 💡 e 🚫

## Task 7 — Allineare `skills/siae-documentation/SKILL.md`

**File:** `skills/siae-documentation/SKILL.md`

Sostituire la card (linee ~114-126, formato `🔴 RISCHIO ALTO`) con il nuovo template. Header: `🔴 ALTO (difficile da annullare)`. Aggiungere emoji contestuali.
