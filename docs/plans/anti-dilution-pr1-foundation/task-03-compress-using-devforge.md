# Task 03 — Comprimere skills/using-devforge/SKILL.md (139→90 righe)

**Stato:** [PENDING]
**Execution:** subagent (parallel-safe con T04-T08)
**Dipendenze:** T01 (centralizations esistono)
**Durata stimata:** 8-12 min

## Goal

Comprimere `skills/using-devforge/SKILL.md` da 139 a ≤90 righe preservando ogni **regola comportamentale**. Rimuovere solo ridondanza didattica.

## Classificazione K/M/D

Ho già ispezionato il file (turno precedente). Headers attuali:

| Riga | Sezione | Classe | Azione |
|---|---|---|---|
| 9 | SUBAGENT-STOP — Gate Check | K | Mantieni verbatim |
| 21 | Come Accedere Alle Skill | D | Riduci a 1 riga: "Invoca via Skill tool. Non leggere i file skill con Read." |
| 28 | La Regola | K | Mantieni verbatim (backbone rule) |
| 46 | DevForge Backbone Core | K | Mantieni verbatim |
| 66 | Always-On Companion Skills | K | Mantieni verbatim |
| 81 | Skill Priority | M | Merge con "Regole Operative Brevi" in unica sezione "Priority & Rules" |
| 101 | Gate Operativi | K | Mantieni verbatim (regole di enforcement esplicite) |
| 126 | Regole Operative Brevi | M | Merge con "Skill Priority" (riga 81) in unica sezione "Priority & Rules" |
| 133 | Istruzioni Utente | D | Rimuovi se vuota/ridondante |

## Step

### Step 1 — Read file attuale

```bash
wc -l skills/using-devforge/SKILL.md
```
Output atteso: `139 skills/using-devforge/SKILL.md`

### Step 2 — Rewrite con classe K intoccata

Regole:
- Frontmatter YAML invariato (name, description)
- Sezioni K: copia-incolla senza modifica
- Sezioni M: fondi in unica sezione `## Priority & Rules` (merge Skill Priority + Regole Operative Brevi)
- Sezioni D: elimina completamente O riduci a 1-2 righe dentro una sezione esistente

### Step 3 — Verifica target

```bash
wc -l skills/using-devforge/SKILL.md
```
Output atteso: `<=90 skills/using-devforge/SKILL.md`

### Step 4 — Smoke test

Il frontmatter `name:` e `description:` devono restare invariati perché `lib/skills-core.js` li legge per il catalog:

```bash
head -10 skills/using-devforge/SKILL.md | grep -E "^name:|^description:"
```
Output atteso: 2 righe (name + description) invariate.

### Step 5 — Verifica che lo skill-catalog si rigenera correttamente

```bash
node lib/skills-core.js "$(pwd)" 2>&1 | head -5
```
Output atteso: output tabella catalog (nessun errore).

### Step 6 — Commit

```bash
git add skills/using-devforge/SKILL.md
git commit -m "refactor(skills): compress using-devforge SKILL.md (139->90 lines)

Part of PR #1 anti-dilution (ADR-003 Radical Compression).
K sections preserved verbatim: La Regola, Backbone Core, Always-On, Gate Operativi.
M sections merged: Skill Priority + Regole Operative Brevi.
D sections removed: redundant 'Come Accedere' + empty 'Istruzioni Utente'.
Behaviour-impacting rules: ZERO changes."
```

## Acceptance

- [ ] `wc -l skills/using-devforge/SKILL.md` ≤ 90
- [ ] Frontmatter `name` + `description` invariati (verificato via head)
- [ ] `node lib/skills-core.js` genera catalog senza errori
- [ ] Sezioni K ("La Regola", "Backbone Core", "Always-On Companion", "Gate Operativi") testualmente identiche al pre-compression (verifica con diff su blocchi K)
- [ ] Commit conventional `refactor(skills):`

## Contratto con il regression test (T10)

T10 verifica che:
- Il backbone rule "Se pensi che ci sia anche l'1% di probabilità..." sia presente
- I checkpoint schema siano rispettati
- Il catalog si generi

La tua compression deve mantenere questi invarianti.
