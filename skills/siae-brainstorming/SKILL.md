---
name: siae-brainstorming
description: >
  Guida il processo di design da idea a design doc approvato, prima di QUALSIASI
  implementazione. Nessuna eccezione. Anche refactoring, bug fix, config change.
  Trigger: feature nuova, design, come procediamo, come progettiamo, quale approccio,
  valutare opzioni, trade-off, prima dell'implementazione, aggiungi feature,
  costruisci, crea componente, nuovo servizio, refactoring architetturale, migrazione,
  bug fix, refactoring, ottimizzazione, modifica codice, qualsiasi task implementativo.
validates_via:
  predicate: design_doc_produced
  evidence_type: file_pattern
  evidence_check: "docs/plans/*-design.md mtime > DEVFORGE_SESSION_START_S"
---

# SIAE Brainstorming — Da Idea a Design Validato

## LA LEGGE DI FERRO

```
NESSUNA IMPLEMENTAZIONE SENZA DESIGN APPROVATO DALL'UTENTE
```

> **Tipo:** Rigid | **Fase SDLC:** 2. Design

---

## HARD-GATE

<EXTREMELY-IMPORTANT>
NON invocare skill di implementazione, scrivere codice, o creare scaffold FINCHE'
non hai presentato il design e l'utente lo ha approvato. Questo si applica a OGNI
progetto, indipendentemente dalla semplicita' percepita.

Stai per scrivere codice, creare file, o invocare siae-tdd/siae-code-standards?
Hai completato TUTTI e 7 i punti della checklist brainstorming?
- NO → FERMATI. Torna al punto mancante. Nessun codice senza design approvato.
- SI → Procedi con siae-writing-plans.

Conseguenze documentate dello skip:
- 73% dei rework in SIAE derivano da design mancante o incompleto
- "So gia' cosa fare" → assunzioni non esaminate → codice da riscrivere
- Ogni ora risparmiata saltando il brainstorming costa 3-5 ore di rework
</EXTREMELY-IMPORTANT>

---

## Scaling — Adatta la Profondita', MAI il Processo

ZERO ECCEZIONI. I 7 step si eseguono SEMPRE. La complessita' determina la PROFONDITA', non se lo step si esegue. Ogni task produce SEMPRE un piano con subtask via siae-writing-plans.

| Complessita' | Segnali | Profondita' |
|-------------|---------|-------------|
| **Bassa** | Config change, typo, rename, fix isolato (<3 file) | Step brevi (poche frasi). Design doc 10-15 righe. Tutti i 7 step eseguiti. |
| **Media** | CRUD, refactoring, ottimizzazione, bug fix multi-file | Dettaglio moderato. Design doc 30-60 righe. |
| **Alta** | Feature nuova, cross-module, integrazione, migrazione | Checklist completa con massimo dettaglio. |
| **Anti-pattern** | "E' troppo semplice per un design" | I task semplici nascondono assunzioni non esaminate. Il design puo' essere breve, ma DEVI presentarlo e ottenere approvazione. |

<EXTREMELY-IMPORTANT>
NON saltare step. NON abbreviare. NON decidere autonomamente che un task e' "troppo semplice".
</EXTREMELY-IMPORTANT>

---

## Checklist — 7 Punti Obbligatori

### 1. Smart Intake — Inferisci il contesto dal codebase

**NON chiedere cio' che il codice sa gia'.** Leggi prima, chiedi dopo. Verifica prima se l'informazione e' gia' nella conversazione corrente.

**Fonti (in ordine):** (1) `CLAUDE.md` progetto (stack, regole); (2) manifest `pom.xml`/`package.json`/`requirements.txt`/`terragrunt.hcl` (dipendenze); (3) struttura directory via Glob (pattern architetturale); (4) `git log --oneline -10` (lavoro recente); (5) `docs/plans/` (design precedenti); (6) auto-memory `~/.claude/projects/<project>/memory/MEMORY.md` (lezioni cross-sessione); (6b) memoria episodica `project_session_*.md` (branch, PR, stato sessione precedente); (7) JIRA via MCP Atlassian (ticket correlati).

**Ogni inferenza:** Confidence HIGH (≥90%) / MEDIUM (60-89%) / LOW (<60%) + citation `file:riga`.

### 2. Scope Assessment — Valuta se decomporre

**Test:** dominio coeso o piu' sottosistemi indipendenti?

**Segnali scope troppo ampio:** 3+ domini, componenti potenzialmente repo separati, stack diversi, piu' team/factory.

**Se troppo ampio:** presenta decomposizione numerata, chiedi quale affrontare per primo, gli altri restano nel backlog.

**Se scope ok:** procedi a Step 3.

### 3. Presenta inferenze + domande mirate

Presenta le inferenze in tabella compatta `Campo | Valore | [Confidence] | file:riga` per conferma rapida.

**Regole:** conferma in blocco o correzioni puntuali. Domande SOLO per confidence LOW, campi non inferiti, scopo. Una alla volta. Scelta multipla preferita. Se tutto HIGH e confermato, procedi direttamente a Step 4.

### 3b. Option Zero Gate

Prima di proporre codice, verifica se il problema si risolve con configurazione, infrastruttura o processo.

**Verifiche:** AWS Parameter Store / SSM, Terraform variables, feature flag esistente, env var, ticket DevOps/infra, servizio o libreria SIAE esistente, config applicativa (`application.yml`, `.env`).

**Se applicabile:** presenta la soluzione config/infra, chiedi conferma. Anche config/infra passa per design doc (breve) e piano (anche 1-subtask). Emetti checkpoint `[BRAINSTORM:OPTION-ZERO]`.

**Se non applicabile:** documenta brevemente perche' ("non esiste parameter store per X") e procedi a Step 4.

### 4. Proponi 2-3 approcci con trade-off e raccomandazione

- Ogni approccio: descrizione, pro, contro, complessita'
- Raccomandazione tua + motivazione
- Stima SP doppia scala (SP-Umano / SP-Augmented) — vedi tabella "Integrazione JIRA"

### 5. Presenta design per sezioni, approvazione dopo ciascuna

- Scala la sezione alla complessita' (poche frasi → 200-300 parole)
- Approvazione incrementale dopo ciascuna sezione
- Copri: architettura, componenti, flusso dati, gestione errori, testing

### 6. Scrivi design doc in `docs/plans/YYYY-MM-DD-<topic>-design.md`

Salva il design validato. Includi contesto, decisioni, trade-off scelti, stima SP, criteri di accettazione. Committa con card 🟡 MEDIO (vedi `lib/risk-taxonomy.md`) — senza commit il design resta invisibile in git history.

### 6b. Spec Review Gate (con reviewer automatico)

Prima del gate utente, lancia subagent spec-reviewer con prompt in [design-reviewer-prompt.md](design-reviewer-prompt.md) passando `{design_doc_path}` e `{user_goal}`.

**Processo:**
1. Lancia reviewer, leggi report
2. Se BLOCK: fixa, ri-lancia (max 5 iterazioni); dopo 5 → escalation utente
3. Se solo WARN: presenta al gate utente
4. Se zero issue: gate standard

Emetti checkpoint `[BRAINSTORM:SPEC-REVIEW]`.

Dopo PASS reviewer, gate utente:
```
Design reviewato automaticamente (N iterazioni, 0 BLOCK).
Conferma:
- Requisiti completi?
- Criteri accettazione coprono tutti i casi?
- Decisioni architetturali corrette?
- Stime SP realistiche?
- Dominio focalizzato?
```

NON invocare siae-writing-plans senza conferma esplicita a questo gate.

### 7. REQUIRED: Transizione al piano implementativo

Design approvato, committato, Spec Review Gate confermato?

```
REQUIRED SUB-SKILL: siae-writing-plans
```

`siae-writing-plans` gestisce decomposizione task, template TDD, execution handoff (subagent o sessione separata). NON scrivere il piano in questa skill.

---

## Output Strutturato Obbligatorio — Checkpoint

Formato generale: vedi `lib/checkpoint-schema.md`. Per OGNI step emetti il checkpoint corrispondente (no parafrasi, no campi omessi).

```
[BRAINSTORM:INTAKE]       Stack · Pattern · Confidence · File analizzati · Lacune
[BRAINSTORM:SCOPE]        Livello · Dominio · Decomposizione · Rischi
[BRAINSTORM:OPTION-ZERO]  Applicabile {SI/NO} · Tipo {config/infra/processo} o Motivo
[BRAINSTORM:DESIGN]       File · Approcci valutati · Scelto · ADR · SP (Umano/Augmented)
[BRAINSTORM:SPEC-REVIEW]  Issue (BLOCK/WARN) · Iterazioni N/5 · DECISIONE
[BRAINSTORM:GATE]         Requisiti · Criteri · Stime · Dominio · DECISIONE {PROCEDI/MODIFICA}
```

---

## Integrazione SIAE / JIRA

Se MCP Atlassian disponibile, cerca ticket correlati all'inizio (JQL: `project = <KEY> AND summary ~ "<keyword>" ORDER BY updated DESC`).

### Stima Story Points — Doppia Scala

| SP | SP-Umano (senza AI) | SP-Augmented (dev + Claude) |
|----|---------------------|------------------------------|
| 1  | Triviale, zero rischio | Config, typo, rename |
| 2  | Semplice, <1 giorno | CRUD endpoint, test unitario, IaC isolato |
| 3  | Moderato, 1-2 gg | Feature con 2-3 componenti |
| 5  | Significativo, 2-4 gg | Feature cross-module, pipeline ETL |
| 8  | Complesso, ~1 settimana | Nuovo microservizio, refactoring architetturale |
| 13 | Molto complesso, >1 settimana | Migrazione sistema, nuovo dominio |

**Accelerazione AI per tipo:** boilerplate/CRUD ~5-10x · test+refactor meccanico ~3-5x · feature con spec chiare ~2-3x · integrazione API ~1.5-2x · logica di dominio ambigua ~1-1.5x · debug prod ~1-1.5x.

**Come stimare:** identifica tipo dominante, applica moltiplicatore, arrotonda al Fibonacci piu' vicino. Presenta SEMPRE entrambi: `Story Points: 5 SP-Umano / 3 SP-Augmented`.

### Output JIRA ticket

A fine design produci blocco `JIRA TICKET OUTPUT` con campi: Tipo (Story/Task/Bug), Sommario, Descrizione (da design doc), Story Points (doppia scala), Labels, Acceptance Criteria (lista).

Creazione ticket = 🔴 ALTO (vedi `lib/risk-taxonomy.md`; extra: JIRA ticket = ALTO). Mostra pre-flight card, attendi conferma esplicita (silenzio ≠ consenso), poi `createJiraIssue`.

---

## Stato Terminale

Output brainstorming: (1) design doc approvato in `docs/plans/`, (2) piano con header `REQUIRED SUB-SKILL`, (3) scelta esecuzione offerta (subagent o sessione separata).

NON invocare siae-tdd o skill implementative senza offrire la scelta di esecuzione. L'implementazione inizia SOLO dopo feature branch via `siae-git-workflow`.

---

## Limiti Operativi

Vedi `lib/operational-limits.md`. Override: step totali del brainstorming = 7 (se ne servono di piu', il task e' troppo grande → decomponi).

## Classificazione Rischio Operazioni

Vedi `lib/risk-taxonomy.md`. Extra: creazione ticket JIRA = 🔴 ALTO.

## Permission Denied Handling

Vedi `lib/permission-denied-handling.md`. Extra: Step 1-4 completabili senza permessi (conversazione). Step 5-6 degradano a output testuale se Write/Bash negati.
