# Task 01 — `siae-tdd` Trigger Keyword Reduction (20+ → 5-8)

**Goal:** Ridurre trigger keyword nella description di `siae-tdd` da 20+ a 5-8 mirate. Documenta keyword removed in CHANGELOG con migration path.

**File coinvolti:**
- `skills/siae-tdd/SKILL.md` (frontmatter description trigger)
- `CHANGELOG.md` (root, sezione [Unreleased] o nuova versione)

**RISCHIO ALTO** (memory `R5`): keyword removal può causare regressione attivazione su prompt che usavano vecchie keyword. Migration path obbligatorio.

## Step 1 — Identifica trigger attuali

```bash
sed -n '1,15p' skills/siae-tdd/SKILL.md
```

Estrai lista trigger keyword (>20 attesi).

## Step 2 — Selezione trigger ridotti (5-8)

Mantieni i più discriminanti:
1. `test-driven development`
2. `TDD per feature nuova`
3. `scrittura test prima del codice`
4. `Red-Green-Refactor`
5. `failing test before implementation`
6. `test unit`
7. `pytest/junit/jest scrittura`
8. (opzionale) `refactoring con test`

Rimuovi keyword troppo generiche:
- "implementa" / "codifica" / "sviluppa" / "scrivi funzione" / "aggiungi metodo" / "crea classe" / "modifica logica" / "nuovo endpoint"

Motivazione: queste sono keyword di skill generiche `siae-brainstorming` (design first) e potrebbero rubare attivazione a brainstorming.

## Step 3 — Edit description

Pattern target:

```yaml
---
name: siae-tdd
description: >
  Use when implementing production code following test-driven development:
  failing test BEFORE implementation, then Red-Green-Refactor cycle. Best
  after: siae-brainstorming + siae-writing-plans (design + plan approved).
  Examples: "TDD per feature nuova", "Red-Green-Refactor", "scrivo test
  prima del codice", "ciclo TDD".
---
```

Trigger keyword count: 4 esempi + "test-driven development" + "Red-Green-Refactor" = 6.

## Step 4 — Aggiungi entry CHANGELOG

In `CHANGELOG.md` (root):

```markdown
## [Unreleased] — 2026-05-XX

### Changed
- `siae-tdd` description trigger keyword ridotti da 20+ a 6 mirate
  (anti-dilution PR-6). Pattern Anthropic "Use when X".

### Removed
- `siae-tdd` trigger keyword: "implementa", "codifica", "sviluppa", "scrivi
  funzione", "aggiungi metodo", "crea classe", "modifica logica", "nuovo
  endpoint", "implementazione feature", "bug fix", "refactoring", "qualsiasi
  scrittura di codice".

### Migration path

Se invocavi `siae-tdd` con prompt come "implementa la funzione X" → ora il
prompt attiverà `siae-brainstorming` (design first per memory backbone). Per
forzare TDD direttamente: usa "TDD per implementare X" o "Red-Green-Refactor
sulla funzione X". Comunque siae-brainstorming → siae-writing-plans →
siae-tdd è il flusso canonico.
```

## Step 5 — Smoke test no-regression CRITICO

Test 10 prompt che usavano keyword removed:

| Prompt | Pre-Task | Post-Task expected |
|---|---|---|
| "implementa la funzione validateISRC" | siae-tdd | siae-brainstorming (canonico) |
| "scrivo nuovo metodo X" | siae-tdd | siae-brainstorming |
| "modifico la logica di calcolo" | siae-tdd | siae-brainstorming |
| "TDD per nuova feature pagamento" | siae-tdd | siae-tdd |
| "ciclo Red-Green-Refactor" | siae-tdd | siae-tdd |
| "scrivo test prima del codice" | siae-tdd | siae-tdd |
| "test-driven development" | siae-tdd | siae-tdd |
| "creo classe MyService" | siae-tdd | siae-brainstorming |
| "refactoring del modulo auth con test" | siae-tdd | siae-tdd |
| "pytest scrittura test isrc" | siae-tdd | siae-tdd |

**Aspettativa**:
- 6/10 prompt continuano ad attivare `siae-tdd` (TDD-specific keyword preserved)
- 4/10 prompt ora attivano `siae-brainstorming` (canonico per design first)

NB: questo NON è regressione — è il **comportamento atteso** post-task. La memory feedback "no-regression" si applica a skill che dovrebbero attivarsi sui loro trigger LEGITTIMI. Trigger di skill diversa (brainstorming) preempt è OK.

## Step 6 — Commit

```bash
git add skills/siae-tdd/SKILL.md CHANGELOG.md
git commit -m "refactor(skills): siae-tdd trigger reduction 20+ → 6 (anti-dilution PR-6)

Trigger generici ('implementa', 'scrivo funzione', 'modifico logica') rimossi —
ora attivano siae-brainstorming (design first canonico). Trigger TDD-specific
preserved: 'TDD per X', 'Red-Green-Refactor', 'test prima del codice'.

CHANGELOG documenta migration path per utenti che usavano vecchie keyword.
NO-REGRESSION: 10 smoke prompt → 6/10 ancora siae-tdd, 4/10 deviati a brainstorming
(comportamento atteso, allineato a design backbone)."
```

## Criteri accettazione

- Trigger keyword count ≤8
- CHANGELOG entry presente con sezione "Removed" + "Migration path"
- 6/10 smoke prompt TDD-specific ancora attivano siae-tdd
- 4/10 smoke prompt generici ora attivano siae-brainstorming (canonico)

## NO-REGRESSION (sfumato)

Per `siae-tdd`, no-regression NON significa "tutti i prompt pre-task continuano ad attivare la skill". Significa: "prompt TDD-specific (Red-Green, test prima del codice, ciclo TDD) continuano ad attivare la skill". Prompt generici di implementazione devono passare per brainstorming canonico — questo è **miglioramento**, non regressione.
