# Pre-Flight Card — Migrazione a Markdown Table

**Data:** 2026-03-07
**Autore:** SIAE DevForge
**Story Points:** 5
**Stato:** Design approvato

---

## Contesto e Problema

Le pre-flight card in v1.3.0-mvp usano `design-system/generate-card.py` eseguito via
Bash tool. Questo approccio ha due difetti:

1. **Bash richiede approval per ogni esecuzione** — Claude evita la chiamata per non
   interrompere il flusso, oppure l'utente nega/ignora il prompt. Risultato: le card
   non vengono mostrate.

2. **Path relativo** — `design-system/generate-card.py` funziona solo se la CWD e'
   la repo `siae-dev-forge`. In altri progetti il comando fallisce silenziosamente.

In v1.2.0-mvp le card erano template statici embedded nel markdown delle skill.
Funzionavano perche' Claude le copiava direttamente nell'output senza eseguire codice.
Sono state sostituite con lo script per gestire l'allineamento emoji, ma questo ha
introdotto la dipendenza da Bash.

---

## Decisione

Sostituire la generazione Bash con **markdown table inline** prodotte da Claude
direttamente nella risposta testuale.

**Motivazione:**
- Il markdown renderer di Claude Code calcola automaticamente l'allineamento
- Nessun calcolo di larghezza emoji necessario
- Funziona in qualsiasi progetto, senza dipendenze
- Zero Bash, zero approval, sempre visibile
- Stesso contenuto dell'originale (stessi campi, stesse emoji)

`generate-card.py` rimane nel repo per uso manuale/documentazione ma non e' piu'
richiesto dalle skill.

---

## Specifica del Nuovo Formato

### Struttura generale

```markdown
| LEVEL_EMOJI LEVEL (subtitle) — DevForge · SKILL_NAME |
|:---|
| [⚠️ WARNING_LINE — solo per ALTO e CRITICO] |
| [CONTEXT_EMOJI Label: Value] |
| N. ACTION_EMOJI Azione: descrizione |
| FILE_EMOJI `path/al/file` |
| REASON_EMOJI Perche': motivazione |
| IFNO_EMOJI Se NO: alternativa |
```

### Regole strutturali

**Header (prima riga, sempre presente):**
```
| LEVEL_EMOJI LEVEL (subtitle) — 🔨 DevForge · skill-name |
```
- `LEVEL_EMOJI`: 🟡 MEDIO / 🔴 ALTO / 🚨 CRITICO
- Subtitle: reversibile / difficile da annullare / irreversibile

**Warning line (solo ALTO e CRITICO, subito dopo header):**
```
| ⚠️ OPERAZIONE DIFFICILE DA ANNULLARE |       <- ALTO
| ⚠️ AZIONE IRREVERSIBILE — CONFERMA RICHIESTA | <- CRITICO
```

**Context rows (Z2 — se presenti):**
```
| 🌿 Branch: `feature/PROJ-123` |
| 🎯 Target: sviluppo |
```
Usare backtick per valori tecnici (branch, path, versioni).

**Action rows (Z3 — una riga per azione, poi una riga 📂 per file):**
```
| 1. 🚀 Azione: Push branch + apertura PR |
| 📂 `origin/feature/PROJ-123` |
```

Stessa azione su piu' file — ripetere le righe 📂:
```
| 2. ✏️ Azione: Aggiorna configurazione |
| 📂 `src/main/resources/application-dev.properties` |
| 📂 `src/main/resources/application-collaudo.properties` |
| 📂 `src/main/resources/application-prod.properties` |
```

**Footer (Z4 — sempre presente):**
```
| 💡 Perche': motivazione specifica |
| 🚫 Se NO: cosa succede se l'utente rifiuta |
```

### Esempi completi

**MEDIO:**
```markdown
| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-tdd |
|:---|
| 🎫 Story: PROJ-1234 · 🌿 Branch: `feature/PROJ-1234-royalty-calculation` |
| 1. 🧪 Azione: Scrivi test di regressione |
| 📂 `src/main/java/it/siae/distribution/service/RoyaltyCalculationServiceImplTest.java` |
| 2. ✏️ Azione: Implementa fix |
| 📂 `src/main/java/it/siae/distribution/service/RoyaltyCalculationServiceImpl.java` |
| 💡 Perche': Root cause confermata, fix minimale pronto |
| 🚫 Se NO: Nessuna modifica applicata, bug resta in sviluppo |
```

**ALTO:**
```markdown
| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-finishing-branch |
|:---|
| ⚠️ OPERAZIONE DIFFICILE DA ANNULLARE |
| 🌿 Branch: `feature/PROJ-1234-migrate-legacy-authentication-service-to-oauth2` |
| 🎯 Target: sviluppo · 📝 Commit: 14 commit |
| 1. 🚀 Azione: Push branch + apertura PR |
| 📂 `origin/feature/PROJ-1234-migrate-legacy-authentication-service-to-oauth2` |
| 💡 Perche': Branch pronto, test verdi, diff revisionato |
| 🚫 Se NO: Il branch resta locale, nessuna PR aperta |
```

**CRITICO:**
```markdown
| 🚨 CRITICO (irreversibile) — 🔨 DevForge · siae-iac |
|:---|
| ⚠️ AZIONE IRREVERSIBILE — CONFERMA RICHIESTA |
| 🏗️ Ambiente: `production/eu-west-1/data-platform` |
| 1. 🗑️ Azione: Destroy Glue job |
| 📂 `aws/production/eu-west-1/data-platform/glue/royalty-etl-pipeline-v2` |
| 2. 🗑️ Azione: Drop S3 bucket |
| 📂 `s3://siae-prod-eu-west-1-royalty-processed-data-lake-archive-2024` |
| 💡 Perche': Migrazione a pipeline v3, risorse v2 non piu' necessarie |
| 🚫 Se NO: Risorse restano attive, costi invariati |
```

---

## Differenze rispetto all'originale

| Aspetto | v1.3.0-mvp (generate-card.py) | Nuovo (markdown table) |
|---------|-------------------------------|------------------------|
| Colori ANSI | Si (giallo/rosso/rosso bold) | No |
| Bordi | Box completo con ╔═╗ ║ ╚═╝ | Markdown table renderer |
| Allineamento | Script Python | Renderer automatico |
| Dipendenze | Bash + Python + path relativo | Nessuna |
| Affidabilita' | Spesso saltata | Sempre mostrata |
| Contenuto | Identico | Identico |

---

## File da Aggiornare

### 1. `design-system/devforge-visual.md`
- Rimuovere sezione "Come generare una card" con istruzioni Bash
- Sostituire con nuovo template markdown table
- Aggiornare esempi nelle sezioni 0.3 e 0.4
- Mantenere nota su generate-card.py come strumento opzionale

### 2. Skill con pre-flight card (31 occorrenze in 16 file)

| Skill | Occorrenze |
|-------|-----------|
| siae-git-workflow | 1 |
| siae-git-worktrees | 2 |
| siae-finishing-branch | 1 |
| siae-debugging | 1 |
| siae-verification | 1 |
| siae-requesting-review | 1 |
| siae-receiving-review | 1 |
| siae-qa | 1 |
| siae-automation | 2 |
| siae-documentation | 1 |
| siae-codebase-map | 2 |
| siae-security | 2 |
| siae-iac | 2 |
| siae-data-engineering | 4 |
| siae-executing-plans | 1 |
| siae-parallel-agents | 2 |
| siae-writing-plans | 1 |

---

## Trade-off

**Perso:**
- Colori ANSI (giallo per MEDIO, rosso per ALTO/CRITICO)

**Mantenuto:**
- Stesso contenuto (tutti i campi, tutte le emoji di contesto)
- Progressivita' visiva (emoji livello + riga warning per ALTO/CRITICO)
- Struttura a zone (header / context / actions / footer)

**Guadagnato:**
- Affidabilita' totale (sempre mostrata, zero Bash)
- Funziona in qualsiasi progetto
- Allineamento sempre perfetto

---

## Criteri di Accettazione

- [ ] `devforge-visual.md` aggiornato con nuovo formato markdown table
- [ ] Tutti i 31 `generate-card.py` rimossi dalle skill
- [ ] Ogni skill mostra pre-flight card come markdown table con contenuto corretto
- [ ] Formato MEDIO: header con 🟡, no warning line
- [ ] Formato ALTO: header con 🔴, warning line ⚠️
- [ ] Formato CRITICO: header con 🚨, warning line ⚠️ con testo "IRREVERSIBILE"
- [ ] Azioni multiple su stesso file: righe 📂 multiple sotto stessa azione
- [ ] Valori tecnici (path, branch, ISRC) sempre in backtick
- [ ] Plugin version bump a 1.4.0-mvp

---

## REQUIRED SUB-SKILL: siae-writing-plans
