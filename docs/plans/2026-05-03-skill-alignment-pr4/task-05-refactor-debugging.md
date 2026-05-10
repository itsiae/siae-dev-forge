# Task 05 — Refactor `siae-debugging` (Progressive Disclosure + Description Rewrite)

**Goal:** Ridurre `siae-debugging/SKILL.md` da 428 a <200 righe via extract in `reference/` + riscrivere description in pattern Anthropic "Use when X".

**File coinvolti:**
- `skills/siae-debugging/SKILL.md` (refactor)
- `skills/siae-debugging/reference/debugging-phases.md` (nuovo)
- `skills/siae-debugging/reference/debugging-anti-rationalization.md` (nuovo)
- `skills/siae-debugging/reference/debugging-cloudwatch.md` (nuovo)

## Step 1 — Leggi e classifica sezioni esistenti

```bash
wc -l skills/siae-debugging/SKILL.md
sed -n '1,30p' skills/siae-debugging/SKILL.md  # frontmatter + intro
grep -n '^##\|^###' skills/siae-debugging/SKILL.md  # heading map
```

Identifica le sezioni candidate all'extract:
- 4 fasi RCA dettagliate → `reference/debugging-phases.md`
- Tabella anti-rationalization → `reference/debugging-anti-rationalization.md`
- Integration CloudWatch (AWS-bias eliminato) → `reference/debugging-cloudwatch.md`

## Step 2 — Crea directory reference

```bash
mkdir -p skills/siae-debugging/reference
```

## Step 3 — Estrai 4 fasi RCA in `reference/debugging-phases.md`

Sposta integralmente la sezione "4 fasi" (linee tipiche 87-238) nel nuovo file:

```markdown
# siae-debugging — 4 Fasi RCA Dettagliate

> Reference linked da `../SKILL.md`. Contenuto operativo dettagliato delle 4 fasi.

## Fase 1: Reproduce
[contenuto originale]

## Fase 2: Hypothesize
[contenuto originale]

## Fase 3: Verify
[contenuto originale]

## Fase 4: Fix
[contenuto originale]
```

## Step 4 — Estrai anti-rationalization

Sposta tabella anti-rationalization in `reference/debugging-anti-rationalization.md`:

```markdown
# siae-debugging — Tabella Anti-Razionalizzazione

> Reference linked da `../SKILL.md`. Use when troubleshooting your own debug bias.

[contenuto tabella originale]
```

## Step 5 — Estrai integration CloudWatch (e generalizza)

In `reference/debugging-cloudwatch.md`:

```markdown
# siae-debugging — Integration con observability

> Reference linked da `../SKILL.md`. Esempio AWS CloudWatch + generale.

## AWS CloudWatch (esempio SIAE)

[contenuto originale CloudWatch]

## Generalizzazione

Pattern applicabile a qualsiasi observability stack: errori di integrazione
(compute, data pipeline, API, frontend) richiedono correlazione con logs.
```

NB: rimuovi AWS-bias ("Lambda, Glue, API Gateway") nel SKILL.md principale.

## Step 6 — Rewrite SKILL.md (target <200 righe)

Struttura target:
1. Frontmatter (description "Use when X" pattern + 5-8 keyword)
2. HARD-GATE
3. 4 fasi summary (1 riga ciascuna con link a reference)
4. Legge di ferro
5. Output checkpoint format
6. Anti-razionalizzazione (1 riga link)
7. Integration observability (1 riga link)

Esempio frontmatter target:

```yaml
---
name: siae-debugging
description: >
  Use when investigating a bug, error, or unexpected behaviour before proposing
  a fix. Forces 4-phase root cause analysis (reproduce → hypothesize → verify →
  fix). Examples: "NPE su /endpoint", "test fallisce in CI", "comportamento non
  atteso in produzione", "stacktrace 500".
---
```

Body con link a reference:

```markdown
## 4 Fasi RCA

1. **Reproduce** — riproduci l'errore in modo deterministico → vedi `reference/debugging-phases.md#fase-1`
2. **Hypothesize** — formula 2-3 ipotesi → `reference/debugging-phases.md#fase-2`
3. **Verify** — testa ipotesi con evidenza → `reference/debugging-phases.md#fase-3`
4. **Fix** — applica correzione mirata → `reference/debugging-phases.md#fase-4`

## Legge di ferro

NESSUN FIX SENZA ROOT CAUSE COMPRESO E DOCUMENTATO. Mantenere inline.

## Output checkpoint format

Mantenere inline il formato `[DEBUG:PHASE-N] ...` esistente.

## Anti-razionalizzazione

Vedi `reference/debugging-anti-rationalization.md` per la tabella completa.

## Integration observability

Vedi `reference/debugging-cloudwatch.md` per esempi (AWS CloudWatch SIAE) +
pattern generale.
```

## Step 7 — Verifica line count

```bash
wc -l skills/siae-debugging/SKILL.md
```

Output atteso: <200 righe.

## Step 8 — Verifica reference esistono

```bash
ls -la skills/siae-debugging/reference/
# Atteso: 3 file (debugging-phases.md, debugging-anti-rationalization.md, debugging-cloudwatch.md)
```

## Step 9 — Verifica nessun link rotto

```bash
grep -n 'reference/' skills/siae-debugging/SKILL.md | while read line; do
  ref=$(echo "$line" | grep -oE 'reference/[a-z-]+\.md' | head -1)
  [ -f "skills/siae-debugging/$ref" ] && echo "OK: $ref" || echo "MISSING: $ref"
done
```

Output atteso: tutti `OK`.

## Step 10 — Smoke test attivazione (manuale)

Apri Claude Code session test, prompt: "ho un bug NPE su /detailLocale, fixiamo".

Verifica: skill `siae-debugging` ancora invocata. Se NO → analizza description rewritten, rollback parziale.

## Step 11 — Commit atomico

```bash
git add skills/siae-debugging/
git commit -m "refactor(skills): siae-debugging progressive disclosure + 'Use when X' description

- Body 428 → ~180 righe
- Estratte: 4 fasi RCA dettagliate, tabella anti-rationalization, observability
  integration in skills/siae-debugging/reference/
- Description riscritta in pattern Anthropic 'Use when X'
- AWS-bias rimosso dal SKILL.md principale (esempi SIAE in reference)
- NO-REGRESSION verificata via smoke test 'NPE su /endpoint'"
```

## Criteri accettazione

- `wc -l skills/siae-debugging/SKILL.md` < 200
- 3 file in `skills/siae-debugging/reference/`
- 0 link rotti `reference/*.md`
- Description in pattern "Use when X" con 5-8 keyword
- Smoke test prompt "NPE/error/bug" attiva ancora `siae-debugging`

## NO-REGRESSION reference

Test prompt obbligatorio post-task:
- "ho un NPE su /detailLocale, fixiamo" → skill attivata: SI/NO
- "il test fallisce in CI con stacktrace" → skill attivata: SI/NO
- "comportamento inatteso in prod" → skill attivata: SI/NO

Se ≥1 NO, rollback granulare description (mantieni progressive disclosure).
