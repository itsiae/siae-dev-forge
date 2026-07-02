---
name: siae-brainstorming
description: >
  Use when designing any implementation task before writing code (feature, bug
  fix, refactor, config change). Forces 7-step process: intake → scope → options →
  design → review → approval → handoff to siae-writing-plans. Mandatory before any
  code change. Trigger: feature nuova, design, come procediamo, come progettiamo,
  quale approccio, valutare opzioni, trade-off, prima dell'implementazione,
  aggiungi feature, costruisci, crea componente, nuovo servizio, refactoring
  architetturale, migrazione, bug fix, refactoring, ottimizzazione, modifica
  codice, qualsiasi task implementativo, config change.
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
non hai presentato il design e l'utente lo ha approvato. Per i task complessi
questo vincolo e' assoluto, indipendentemente dalla semplicita' percepita.

Per i cambiamenti trivial (1 file, poche righe, path non-sensibile, non-IaC — vedi
tabella Scaling sotto) il gate hook `brainstorming-gate` non forza nudge/block: la
profondita' del design collassa a un tier "Bassa" quasi-istantaneo, MA il
ragionamento sui 7 punti resta implicito nel flusso, non eliminato.

Stai per scrivere codice, creare file, o invocare siae-tdd/siae-code-standards su
un task complesso?
Hai completato TUTTI e 7 i punti della checklist brainstorming?
- NO → FERMATI. Torna al punto mancante. Nessun codice senza design approvato.
- SI → Procedi con siae-writing-plans.

Conseguenze documentate dello skip:
- 73% dei rework in SIAE derivano da design mancante o incompleto
- "So gia' cosa fare" → assunzioni non esaminate → codice da riscrivere
- Ogni ora risparmiata saltando il brainstorming costa 3-5 ore di rework
</EXTREMELY-IMPORTANT>

---

## Scaling — La PROFONDITA' Scala Sempre, il Gate Scala sui Trivial

La complessita' determina SEMPRE la PROFONDITA' del ragionamento. Per i task
complessi il processo e' obbligatorio end-to-end (nessuna eccezione). Per i task
**trivial** (1 file, righe cambiate sotto soglia configurabile, path non-sensibile,
non-IaC — `DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES`, default 15, vedi
`hooks/ENV_VARS.md`) il tier "Bassa" e' quasi-istantaneo e `hooks/brainstorming-gate`
non emette nudge/block: il gate non forza il processo, ma la profondita' minima
(poche frasi di intento) resta la pratica raccomandata. Ogni task non-trivial
produce SEMPRE un piano con subtask via siae-writing-plans.

| Complessita' | Segnali | Profondita' | Gate hook |
|-------------|---------|-------------|-----------|
| **Trivial** | 1 file, ≤soglia righe, path non-sensibile, non-IaC | Quasi-istantanea (poche frasi di intento, no design doc formale richiesto) | Silente — nessun nudge/block |
| **Bassa** | Config change, typo, rename, fix isolato (<3 file) | Step brevi (poche frasi). Design doc 10-15 righe. Tutti i 7 step eseguiti. | Nudge progressivo (invariato) |
| **Media** | CRUD, refactoring, ottimizzazione, bug fix multi-file | Dettaglio moderato. Design doc 30-60 righe. | Nudge progressivo (invariato) |
| **Alta** | Feature nuova, cross-module, integrazione, migrazione | Checklist completa con massimo dettaglio. | Enforcement pieno (invariato) |
| **Anti-pattern** | "E' troppo semplice per un design" | Se il task NON e' trivial per la definizione sopra, il design puo' essere breve ma DEVI presentarlo e ottenere approvazione — non decidere autonomamente il bypass. | Enforcement pieno |

<EXTREMELY-IMPORTANT>
Multi-file, IaC (.tf/.hcl), path-sensibile (hooks/, lib/*gate*,
lib/review_evidence/) o multi-repo sono SEMPRE complessi, mai trivial,
indipendentemente dalle dimensioni del diff. NON decidere autonomamente che un
task complesso e' "troppo semplice" per saltare il processo.
</EXTREMELY-IMPORTANT>

---

## Checklist — 7 Punti Obbligatori (summary)

Dettaglio operativo completo: [reference/brainstorming-checklist.md](reference/brainstorming-checklist.md).

1. **Smart Intake** — Inferisci contesto da CLAUDE.md, manifest, struttura, git log, docs/plans, auto-memory, JIRA. Confidence HIGH/MEDIUM/LOW + citation `file:riga`. NON chiedere cio' che il codice sa gia'.
2. **Scope Assessment** — Dominio coeso o piu' sottosistemi? Se 3+ domini / repo separati / stack diversi → presenta decomposizione numerata, gli altri restano nel backlog.
3. **Inferenze + domande mirate** — Tabella `Campo | Valore | Confidence | file:riga`. Domande SOLO per LOW / non inferiti / scopo. Una alla volta, scelta multipla.
4. **2-3 approcci con trade-off** — Per ogni approccio: descrizione, pro, contro, complessita'. Raccomandazione + motivazione. Stima SP doppia scala (vedi [reference/brainstorming-jira.md](reference/brainstorming-jira.md)).
5. **Design per sezioni, approvazione incrementale** — Architettura, componenti, flusso dati, errori, testing. Scala alla complessita'.
6. **Salva design doc** — `docs/plans/YYYY-MM-DD-<topic>-design.md`. Contesto, decisioni, trade-off, SP, criteri accettazione. Commit 🟡 MEDIO.
7. **REQUIRED SUB-SKILL: siae-writing-plans** — handoff a piano implementativo. NON scrivere il piano qui.

---

## Step 3b — Option Zero Gate (INLINE, critico)

Prima di proporre codice, verifica se il problema si risolve con configurazione, infrastruttura o processo.

**Verifiche:** AWS Parameter Store / SSM, Terraform variables, feature flag esistente, env var, ticket DevOps/infra, servizio o libreria SIAE esistente, config applicativa (`application.yml`, `.env`).

**Se applicabile:** presenta la soluzione config/infra, chiedi conferma. Anche config/infra passa per design doc (breve) e piano (anche 1-subtask). Emetti checkpoint `[BRAINSTORM:OPTION-ZERO]`.

**Se non applicabile:** documenta brevemente perche' ("non esiste parameter store per X") e procedi a Step 4.

---

## Step 3c — Placeholder Scan (INLINE, critico)

Prima di scrivere il design doc, scansiona inferenze e bozze per placeholder TBD/TODO/`<...>`/"da definire". Ogni placeholder deve diventare valore concreto o domanda esplicita all'utente. Nessun design viene salvato con TBD residui.

---

## Step 6b — Spec Review Gate (INLINE, critico)

Prima del gate utente, lancia subagent spec-reviewer con prompt in [design-reviewer-prompt.md](design-reviewer-prompt.md) passando `{design_doc_path}` e `{user_goal}`.

**Processo:**
1. Lancia reviewer, leggi report.
2. Se BLOCK: fixa, ri-lancia (max 5 iterazioni); dopo 5 → escalation utente.
3. Se solo WARN: presenta al gate utente.
4. Se zero issue: gate standard.

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

## Stato Terminale

Output brainstorming: (1) design doc approvato in `docs/plans/`, (2) piano con header `REQUIRED SUB-SKILL`, (3) scelta esecuzione offerta (subagent o sessione separata).

NON invocare siae-tdd o skill implementative senza offrire la scelta di esecuzione. L'implementazione inizia SOLO dopo feature branch via `siae-git-workflow`.

---

## Limiti, Rischio, Permission

- **Limiti operativi:** vedi `lib/operational-limits.md`. Override: step totali = 7 (se ne servono di piu', task troppo grande → decomponi).
- **Classificazione rischio:** vedi `lib/risk-taxonomy.md`. Extra: creazione ticket JIRA = 🔴 ALTO (dettagli in [reference/brainstorming-jira.md](reference/brainstorming-jira.md)).
- **Permission denied:** vedi `lib/permission-denied-handling.md`. Step 1-4 completabili senza permessi. Step 5-6 degradano a output testuale se Write/Bash negati.
