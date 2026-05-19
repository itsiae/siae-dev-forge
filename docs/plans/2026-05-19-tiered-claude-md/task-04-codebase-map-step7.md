---
task: 04
title: Modifica siae-codebase-map Step 7 — invocazione sub-skill condizionale
status: PENDING
estimate_min: 30
type: edit
depends_on: [02, 03]
---

# Task 04 — Modifica `siae-codebase-map` Step 7

## Obiettivo

Aggiungere a `skills/siae-codebase-map/SKILL.md` la logica di invocazione
condizionale della sub-skill `siae-codebase-map-tiered` quando flag `--tiered`
è presente. Modifica minimale, zero-regression.

## File da modificare

1. `skills/siae-codebase-map/SKILL.md` — Step 7 esistente (~15 righe aggiunte)

## Modifica esatta

**Prima** (Step 7 attuale, riga 212-238 circa):

```markdown
## Step 7 — Aggiorna `CLAUDE.md`

🟡 MEDIO — Mostra pre-flight card prima di aggiornare
...
```

**Dopo** (aggiungere SOPRA lo Step 7 esistente):

```markdown
## Step 7a — Tiered mode (opt-in)

Se l'utente ha invocato `/forge-map --tiered` o ha richiesto esplicitamente
CLAUDE.md gerarchici:

```
REQUIRED SUB-SKILL: siae-codebase-map-tiered
```

La sub-skill genera L1 root + L2 per package + L3 opzionali secondo best
practice Anthropic (post "How Claude Code works in large codebases", 14 mag 2026).

Se NON in tiered mode → procedi a Step 7b (comportamento esistente invariato).

## Step 7b — Aggiorna `CLAUDE.md` (mono-file, default)
```

Rinominare lo Step 7 esistente in **Step 7b** per chiarezza.

## Criteri di accettazione

1. ✅ Step 7a presente con riferimento `REQUIRED SUB-SKILL: siae-codebase-map-tiered`
2. ✅ Step 7b = Step 7 originale (zero cambiamento comportamento default)
3. ✅ Trigger esplicito documentato (`--tiered` flag o richiesta utente)
4. ✅ Lint markdown OK (nessun broken link)
5. ✅ Backward compatible: invocazione skill senza flag → comportamento identico a prima

## Test

- Test e2e: invocare skill senza `--tiered` su fixture → no CLAUDE.md L2/L3 generati
- Test e2e: invocare skill con `--tiered` → sub-skill triggered (mock verifica)

## Definition of Done

- SKILL.md modificato
- Markdown lint clean
- Test e2e PASS (mock sub-skill)
- Commit: `feat(skills): siae-codebase-map Step 7a tiered mode opt-in`
