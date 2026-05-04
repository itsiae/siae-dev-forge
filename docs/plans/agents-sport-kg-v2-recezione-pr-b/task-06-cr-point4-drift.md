# Task 06 — code-reviewer: Point 4 sotto-checklist drift KG↔codice

**Stato:** [PENDING]
**Dipende da:** Task 05
**Blocca:** Task 07 (smoke test)

## Goal

Aggiungere al Point 4 (Architettura) della review checklist una sotto-checklist "Drift KG↔codice" che usa `graph_consistency_check` per cross-check additivo.

## File coinvolti

- `agents/code-reviewer.md` (sezione Point 4 — da identificare via grep)

## Step 1 — Identifica sezione Punto 4

```bash
grep -n "Punto 4\|Architettura\|architettura\|### 4" agents/code-reviewer.md | head -10
```

Output atteso: trova la sezione "Punto 4: Architettura" (italiano, riga ~227) nella review framework a 6 punti.

## Step 2 — TDD test pre-modifica

```bash
grep -c "Drift KG\|graph_consistency_check" agents/code-reviewer.md
```
Output atteso pre-modifica (post Task 05): 1 (solo nel select bulk).

## Step 3 — Aggiungi sotto-checklist Punto 4

Nella sezione "Punto 4: Architettura" (italiano), aggiungi una sotto-checklist:

```markdown
#### Sotto-checklist 4.X — Drift KG↔codice (D3, opzionale)

Se la review tocca un servizio SIAE mappato in sport-kg, esegui cross-check
drift architetturale:

```
mcp__sport-kg__graph_consistency_check(service=<service-name>)
```

**Interpretazione output**:

| Status | Significato | Azione review |
|---|---|---|
| `CONSISTENT` | KG e codice/runtime allineati | ✅ Nessuna azione |
| `INCONSISTENT` | Drift rilevato (auth/DTO/schedule) | ⚠️ Listare mismatch nei findings come **BLOCK** se drift è in scope della PR; come **WARN** se preesistente |
| `INSUFFICIENT_DATA` | KG non ha dati sufficienti per consistency check | 📝 Nota nei findings, no blocco |

**Pattern findings**:

```markdown
**4.X — Drift KG↔codice**: <CONSISTENT/INCONSISTENT/INSUFFICIENT_DATA>

[Se INCONSISTENT]
Mismatch rilevati:
- <signal_1>: KG dice <X>, codice/ES dice <Y>
- <signal_2>: ...

Severity: <BLOCK se drift introdotto da PR / WARN se preesistente>
```

**Fallback (no MCP)**:
Se `ToolSearch` non ha caricato `graph_consistency_check` o il tool ritorna
errore, **skip silenzioso**. La review continua senza cross-check (status:
"KG cross-check non disponibile" nei findings opzionale, mai bloccante).

**Quando NON eseguire**:
- Servizio non mappato in KG (prefissi non `sport-*/pop-*/pae-*/ciam-*/...`)
- PR su file non architetturali (es. solo test, solo docs, solo config minor)
- Review express/tactical (focus solo Point 1+2 per fix puntuali)
```

## Step 4 — Aggiungi anti-pattern

Identifica la sezione anti-pattern del code-reviewer (se esiste) o aggiungila al Punto 4. Aggiungi:

```markdown
**Anti-pattern**:
- ❌ Trattare `INCONSISTENT` come BLOCK automatico senza verificare se il drift è nello scope della PR. Una drift preesistente non bloccata da review precedenti non diventa colpa della PR corrente — segnalalo come WARN tracciabile.
- ❌ Ignorare `INSUFFICIENT_DATA` come "tutto ok". È un signal che il KG non sta osservando il servizio — vale la pena capire perché (refresh KG? servizio dormiente?).
- ❌ Skippare il check perché "MCP probabilmente non c'è" — tenta sempre `ToolSearch`, fallback solo se errore reale.
```

## Step 5 — TDD verify

```bash
grep -c "graph_consistency_check" agents/code-reviewer.md
```
Output atteso post-modifica: ≥ 3 (select bulk + Point 4 sotto-checklist + interpretazione)

```bash
grep -c "Drift KG\|drift KG" agents/code-reviewer.md
```
Output atteso post-modifica: ≥ 2

```bash
grep -c "INCONSISTENT\|INSUFFICIENT_DATA" agents/code-reviewer.md
```
Output atteso post-modifica: ≥ 3

## Step 6 — Commit

```bash
git add agents/code-reviewer.md
git commit -m "feat(agents): code-reviewer Point 4 sotto-checklist drift KG vs codice

Point 4 (Architettura):
- Nuova sotto-checklist Drift KG vs codice (D3 graph_consistency_check)
- Interpretazione 3 stati: CONSISTENT (no action), INCONSISTENT (BLOCK/WARN
  per drift in scope vs preesistente), INSUFFICIENT_DATA (note no blocco)
- Pattern findings documentato per output review
- Fallback silenzioso se MCP non disponibile

Skip rules esplicite:
- Servizio non mappato in KG
- PR non architetturale
- Review express/tactical

Anti-pattern documentati:
- INCONSISTENT auto-BLOCK senza verifica scope drift
- INSUFFICIENT_DATA ignorato come 'tutto ok'
- Skip ToolSearch a priori

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.4

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] Sotto-checklist 4.X presente in Point 4
- [ ] Interpretazione 3 stati documentata in tabella
- [ ] Pattern findings esempio markdown presente
- [ ] Fallback silenzioso documentato
- [ ] Skip rules esplicite (3 casi)
- [ ] Anti-pattern (3 casi) presenti
- [ ] grep checks passano
- [ ] Commit creato
