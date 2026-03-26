# siae-qa Enterprise Upgrade — Design Doc

> **Data:** 2026-03-26
> **Branch:** refactor/migrate-mermaid-to-plantuml → da creare: `feat/siae-qa-enterprise-upgrade`
> **Status:** APPROVATO
> **SP:** 13 SP-Umano / 5 SP-Augmented

---

## Contesto

Cinque AI-as-a-Judge hanno analizzato `siae-qa` in parallelo su 5 assi:
question tree completeness, domain coverage, user flow ordering, code-first derivation,
determinism & enterprise readiness. La valutazione ha prodotto 10 gap critici.

## Goal

Portare `siae-qa` da skill funzionale a skill enterprise-grade capace di:
1. Produrre output deterministici e riproducibili indipendentemente da chi la esegue
2. Coprire tutti i domini applicativi comuni in una IT factory
3. Derivare scenari di test anche dal codice sorgente (non solo dagli AC)
4. Proporre i test in ordine di flusso utente
5. Produrre classificazioni e metriche di coverage enterprise

## File Modificati

| File | Cluster | Tipo modifica |
|------|---------|--------------|
| `skills/siae-qa/SKILL.md` | A + B + C | Modifica strutturale |
| `skills/siae-qa/reference/question-trees.md` | A + B | Modifica strutturale |
| `skills/siae-qa/XRAY-TEMPLATES.md` | A + C | Modifica strutturale |
| `skills/siae-qa/reference/code-scan.md` | B | NUOVO file |

---

## Cluster A — Determinismo del Workflow

### A1 — Allineamento segnali (SKILL.md ↔ XRAY-TEMPLATES.md)

**Problema:** "upload", "drag", "SSO" sono nei question tree ma assenti dalla tabella segnali in XRAY-TEMPLATES.md.

**Fix:** aggiornare la tabella in XRAY-TEMPLATES.md sezione "Tabella Segnali Req Typing" aggiungendo i segnali mancanti per ogni tipo. Contestualmente aggiornare i segnali con tecnologie moderne non coperte (Next.js, GraphQL, dbt, OAuth2, EventBridge, ecc.).

### A2 — Skip-criteria espliciti

**Problema:** "salta domanda se già rispondibile dagli AC" è giudicato dall'LLM in real-time → output non deterministico.

**Fix:** in `question-trees.md`, per ogni domanda aggiungere un blocco `> SKIP SE:` con pattern espliciti (stringa o keyword) che devono essere presenti negli AC per qualificare lo skip. Se il pattern non è trovato testualmente, la domanda è obbligatoria.

### A3 — Cardinalità minima matrice scenari

**Problema:** un developer può chiudere tutte le categorie con 1 scenario o N/A senza giustificazione.

**Fix:** in `SKILL.md` sezione "Fase 4a", aggiungere tabella di minimi per tipo:

| Tipo | Positivi | Edge | Negativi | Profilazioni |
|------|----------|------|----------|--------------|
| FE   | 1 per AC | 2    | 2        | 0 (solo se Auth) |
| BE   | 1 per AC | 2    | 3        | 0 (solo se Auth) |
| ETL  | 1        | 3    | 2        | 0 |
| DB   | 1        | 2    | 1        | 0 |
| Auth | 1        | 2    | 2        | 2 |
| Integration REST | 1 | 2 | 2   | 0 |
| Integration Event | 1 | 3 | 2  | 0 |

N/A su categoria con minimo > 0 richiede giustificazione esplicita registrata nel piano.

### A4 — Regole granularità step

**Problema:** granularità step libera → TC non comparabili tra sprint.

**Fix:** in `SKILL.md` sezione "Fase 4b" e in `XRAY-TEMPLATES.md` sezione "Formato Test Case", aggiungere 3 regole obbligatorie:
- Regola A: 1 step = 1 interazione atomica
- Regola B: ogni navigazione è step distinto
- Regola C: Expected Result deve essere pass/fail senza giudizio

---

## Cluster B — Coverage Enterprise

### B1 — Domanda L4 performance/SLA

**Problema:** 0 domande su SLA/performance in tutti i 6 tipi.

**Fix:** aggiungere per ogni tipo in `question-trees.md` una domanda di livello L4 (performance):
- FE: "Ci sono soglie di performance definite (LCP, TTI)?"
- BE: "Qual è il throughput atteso e il p99 latency SLA?"
- ETL: "Qual è la finestra di completamento job e l'SLA di freshness downstream?"
- DB: "La migration è safe su tabelle large? Zero-downtime strategy?"
- Auth: "L'endpoint è soggetto a rate limiting con soglie definite?"
- Integration REST: "Qual è il timeout configurato e il p99 atteso?"
- Integration Event: "Qual è il throughput di messaggi atteso e il consumer lag max tollerato?"

### B2 — Phase 0-bis: Code Scan

**Problema:** la skill non legge mai il codice sorgente → perde il 65-85% degli scenari derivabili dal codice.

**Fix:** aggiungere in `SKILL.md` una nuova fase "Phase 0-bis — Code Scan" dopo Phase 0 e prima di Phase 1. Creare `reference/code-scan.md` con:
- Trigger: quando eseguire (repo disponibile + tipo in {BE, FE, ETL, Auth})
- Steps: Glob per file rilevanti → Grep selettivo → aggregazione Code Profile Card
- Output: Code Profile Card + lista "scenari candidati" da validare in 4a
- Integration con 4a: scenari candidati → confronto con matrice AC, il developer conferma o scarta

### B3 — Split Integration → REST sync + Event async

**Problema:** messaggistica async (Kafka, SQS) e chiamate sync REST hanno edge case incompatibili compressi in 5 domande.

**Fix:** in `question-trees.md` e `XRAY-TEMPLATES.md`, dividere il tipo "Integration / External" in due tipi distinti:
- "Integration REST / Sync" — chiamate HTTP/gRPC sincrone verso sistemi esterni
- "Integration Event / Async" — messaggistica asincrona (Kafka, SQS, SNS, EventBridge)

Ogni tipo avrà i propri segnali di inferenza e le proprie 6 domande specializzate.

### B4 — 5 nuovi tipi applicativi

**Problema:** 11 domini applicativi comuni in IT factory non coperti da nessun tipo.

**Fix:** aggiungere in `question-trees.md` e `XRAY-TEMPLATES.md` i top 5 tipi per frequenza:

1. **Notification / Messaging** — email, push, SMS, in-app
2. **Batch / Scheduler** — cron, Quartz, EventBridge rule, elaborazione notturna
3. **Report / Export** — PDF, Excel, CSV export, rendiconto
4. **Feature Flag / Configuration** — LaunchDarkly, Unleash, canary, rollout progressivo
5. **File Processing / Async Upload** — chunked upload, import massivo, SFTP

Ogni tipo: segnali di inferenza, confidence trigger, 6 domande L1/L2/L3.

---

## Cluster C — Output Enterprise

### C1 — Ordinamento per flusso utente (Fase 4c)

**Problema:** TC raggruppati per categoria → QA deve backtracking cognitivo continuo.

**Fix:** aggiungere in `SKILL.md` una Fase 4c "Riordinamento per flusso" con:
- Algoritmo estrazione tappe dagli AC (pattern Given/When/Then, verbi sequenziali)
- Domande L0 trasversali da aggiungere in `question-trees.md`
- Ordinamento: per tappa → interno alla tappa: positivo → edge → negativo → profilazione
- Condizione di attivazione: solo se ≥ 2 tappe identificabili
- Formato output con header di sezione per tappa

### C2 — Primary Type + Secondary Tags

**Problema:** story multi-dominio assegnate a 1 tipo → perdita di domande L2 specializzate.

**Fix:** aggiungere in `SKILL.md` sezione Phase 0:
- Algoritmo: scan tutti i tipi → rank per score → PRIMARY (max score) + SECONDARY (score ≥ 1)
- Per ogni tag secondario: inietta 1-2 domande di triage (non tree completo)
- Soglia split: 3+ tag secondari → avvisa e raccomanda split story
- Req Profile Card aggiornata con sezione `Tag secondari`

### C3 — Schema classificazione TC (5 campi enterprise)

**Problema:** TC senza priority, test level, classification, timing, owner → coverage non misurabile.

**Fix:** aggiungere in `XRAY-TEMPLATES.md` sezione "Formato Test Case Step-Based" 5 campi opzionali retrocompatibili con il CSV Xray (colonne in coda):

| Campo CSV | Valori | Derivazione |
|-----------|--------|-------------|
| `Test Level` | Unit/Integration/System/E2E/Performance/Security | Automatica da tipo+categoria |
| `Priority` | P1-Critical/P2-High/P3-Medium/P4-Low | Regole esplicite per tipo+categoria |
| `Classification` | Functional/Non-Functional/Security/Regression | Automatica |
| `Exec Timing` | Pre-Deploy/Nightly/Sprint/Release | Automatica da NRT+Automazione |
| `Owner` | QA-Manual/QA-Automated/Dev-Auto/DevOps | Automatica da Automazione+Level |

Aggiungere in `SKILL.md` le regole di derivazione automatica per ogni campo.

### C4 — Release Readiness Score

**Problema:** nessun exit criteria calcolabile → go/no-go soggettivo e non difendibile.

**Fix:** aggiungere in `SKILL.md` dopo la Fase 4b una sezione "Release Readiness Score (RRS)":

```
RRS = (0.25 * Coverage_Score) + (0.35 * Critical_Coverage_Score) + (0.30 * Execution_Score) + (0.10 * Defect_Score)
```

Con gate: RRS ≥ 0.90 = Go | 0.75-0.89 = Go condizionale | 0.60-0.74 = No-Go raccomandato | < 0.60 = Hard No-Go.

La skill mostra il RRS parziale (Coverage + Critical) al termine di 4b prima dell'export.

---

## Criteri di Accettazione

- [ ] Tutti i 6 tipi esistenti hanno skip-criteria espliciti per ogni domanda
- [ ] Tutti i 6 tipi hanno cardinalità minima per categoria nella matrice
- [ ] 3 regole di granularità step documentate e obbligatorie
- [ ] Tabella segnali XRAY-TEMPLATES.md allineata con question-trees.md
- [ ] Domanda L4 performance presente in tutti i tipi (inclusi i nuovi)
- [ ] Phase 0-bis Code Scan documentata con Trigger, Steps, Code Profile Card
- [ ] `reference/code-scan.md` creato con extraction rules per tipo
- [ ] Integration split in REST/sync e Event/async con tree separati
- [ ] 5 nuovi tipi presenti in question-trees.md e XRAY-TEMPLATES.md
- [ ] Fase 4c algoritmo ordinamento flusso in SKILL.md
- [ ] Domande L0 trasversali in question-trees.md
- [ ] Primary Type + Secondary Tags in SKILL.md con algoritmo e soglia split
- [ ] 5 campi enterprise in XRAY-TEMPLATES.md con regole derivazione
- [ ] RRS formula e gate in SKILL.md

## Stima

**13 SP-Umano / 5 SP-Augmented**
Tipo dominante: modifica skill DevForge (Markdown strutturato, regole esplicite) — accelerazione ~3x.
