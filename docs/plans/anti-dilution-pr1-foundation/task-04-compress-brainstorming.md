# Task 04 — Comprimere skills/siae-brainstorming/SKILL.md (652→220 righe)

**Stato:** [PENDING]
**Execution:** subagent (parallel-safe con T03,T05-T08)
**Dipendenze:** T01
**Durata stimata:** 12-15 min

## Goal

Comprimere `skills/siae-brainstorming/SKILL.md` da 652 a ≤220 righe. Tutte le regole di enforcement restano intoccate.

## Classificazione K/M/D (verificata via header extraction turno precedente)

| Sezione | Riga | Classe | Azione |
|---|---|---|---|
| `## LA LEGGE DI FERRO` | 27 | K | Verbatim |
| `## HARD-GATE` | 37 | K | Verbatim (EXTREMELY-IMPORTANT block) |
| `## Anti-Pattern: "troppo semplice"` | 60 | M | Fondi con Scaling in 1 tabella 4 righe |
| `## Scaling` | 70 | M | Fondi con "Anti-Pattern troppo semplice" (riga 60) in 1 tabella 4 righe |
| `## Checklist — 7 Punti Obbligatori` | 93 | K | Verbatim |
| `### 1-7 dettagli` | 97-324 | K | Mantieni ma riduci 3b Option Zero checklist (elimina tabella 7 esempi, tieni la lista) |
| `## Output Strutturato Obbligatorio` | 344 | K | Mantieni ma referenzia `lib/checkpoint-schema.md` per formato generale, mantieni solo i checkpoint specifici brainstorm (INTAKE, SCOPE, OPTION-ZERO, DESIGN, SPEC-REVIEW, GATE) |
| `## Flusso del Processo` | 408 | D | Elimina (graph dot non renderizzato) |
| `## Integrazione SIAE / JIRA` | 452 | M | Comprimi: mantieni stima SP tabella, elimina esempi ridondanti, mantieni output JIRA block |
| `## Il Processo nel Dettaglio` | 538 | D | Elimina (duplica i 7 punti) |
| `## Principi Chiave` | 563 | D | Elimina (ridondante con checkpoint) |
| `## Stato Terminale` | 574 | K | Mantieni condensato in 5 righe |
| `## Limiti Operativi` | 590 | M | Sostituisci con: "Vedi `lib/operational-limits.md`. Override: step max = 7." |
| `## Tabella Anti-Razionalizzazione` | 600 | D | Elimina (retorica, non cambia comportamento) |
| `## Classificazione Rischio` | 619 | M | Sostituisci con: "Vedi `lib/risk-taxonomy.md`. Extra: JIRA ticket = ALTO." |
| `## Permission Denied Handling` | 633 | M | Sostituisci con: "Vedi `lib/permission-denied-handling.md`. Extra: Steps 1-4 completabili senza permessi." |

## Stima riduzione

652 righe → mantenute K ~ 180, merged M ~ 30, eliminato D ~ 430 → ≤220 ✓

## Step

### Step 1 — Wc baseline

```bash
wc -l skills/siae-brainstorming/SKILL.md
```
Output atteso: `652 skills/siae-brainstorming/SKILL.md`

### Step 2 — Rewrite applicando K/M/D

Regole cardinali (non derogabili):
- Frontmatter YAML invariato (name + description)
- `## LA LEGGE DI FERRO` + `## HARD-GATE` verbatim (con EXTREMELY-IMPORTANT tag)
- Checklist "7 Punti Obbligatori" con checkpoint mantieniti integri
- Sezioni M referenziano `lib/*.md` invece di duplicare
- Sezioni D vengono ELIMINATE (non commentate)

### Step 3 — Verifica target

```bash
wc -l skills/siae-brainstorming/SKILL.md
```
Output atteso: `<=220`

### Step 4 — Smoke test frontmatter

```bash
head -10 skills/siae-brainstorming/SKILL.md | grep -cE "^name:|^description:"
```
Output atteso: `2`

### Step 5 — Verifica preservation dei 7 checkpoint

```bash
for cp in INTAKE SCOPE OPTION-ZERO DESIGN SPEC-REVIEW GATE; do
  grep -q "\[BRAINSTORM:$cp\]" skills/siae-brainstorming/SKILL.md && echo "PASS $cp" || echo "FAIL $cp"
done
```
Output atteso: 6 PASS.

### Step 6 — Catalog re-generation

```bash
node lib/skills-core.js "$(pwd)" 2>&1 | grep -A1 "siae-brainstorming" | head -3
```
Output atteso: riga skill presente nel catalog.

### Step 7 — Commit

```bash
git add skills/siae-brainstorming/SKILL.md
git commit -m "refactor(skills): compress siae-brainstorming SKILL.md (652->220 lines)

Part of PR #1 anti-dilution (ADR-003).
K preserved verbatim: Legge di Ferro, Hard-Gate, Checklist 7 punti, Checkpoint.
M merged/referenced: Scaling+AntiPattern unificati; risk-taxonomy, operational-limits, permission-denied-handling riferiti da lib/*.md.
D removed: Flusso dot graph, Processo Dettaglio (duplicato), Principi Chiave, Tabella Anti-Razionalizzazione.
Behaviour-impacting rules: ZERO changes."
```

## Acceptance

- [ ] `wc -l` ≤ 220
- [ ] 6 checkpoint brainstorm presenti (verificato via grep)
- [ ] `node lib/skills-core.js` include siae-brainstorming
- [ ] Legge di Ferro invariata verbatim
- [ ] Hard-Gate block con EXTREMELY-IMPORTANT presente
- [ ] Referenze a `lib/*.md` presenti per le sezioni M

## Safeguard

Se dopo rewrite il count supera 220 righe:
- Prima rimuovi esempi inline (preferisci mantenere regole)
- Poi riduci didattica in sezioni M
- **NON** rimuovere regole K
- Se non riesci a scendere sotto 230, STOP e riporta al chiamante
