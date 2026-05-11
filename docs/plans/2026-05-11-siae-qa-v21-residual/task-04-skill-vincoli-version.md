# Task 04 — Anti-Razionalizzazione + Vincoli Non Negoziabili + version 2.1.0 + changelog

**Goal:** Aggiungere 2 nuove righe alla Tabella Anti-Razionalizzazione (riga 790-810), aggiungere 2 nuovi vincoli (#15 e #16) ai Vincoli Non Negoziabili (riga 821-838), bumpare il frontmatter SKILL.md a `version: 2.1.0` + changelog inline con tutti gli ADR.

**SP:** 1 (Umano) / 0.5 (Augmented)

**File coinvolti:**
- Modifica: `skills/siae-qa/SKILL.md` (frontmatter righe 1-20 + righe 790-810 + righe 821-838)

## Step 1 — Verifica riferimenti riga reali

```bash
grep -n "Anti-Razionalizzazione\|VINCOLI NON NEGOZIABILI" skills/siae-qa/SKILL.md
```

**Output atteso:** `790` (Anti-Raz header) e `821` (Vincoli header).

## Step 2 — Edit Anti-Razionalizzazione: aggiungi 2 righe alla tabella

Localizza la tabella Anti-Razionalizzazione (righe 790-810). Aggiungere alla fine della tabella (dopo l'ultima riga esistente, prima della chiusura sezione `---`):

```
| "Lo step 2 'verify response code' basta per i POST" | No. Per mutating 2xx serve read-back (GET/SELECT) o assert body fields. Response code da solo conferma che la chiamata e' arrivata, non che il record esista nello stato atteso. |
| "I lookup li espando tutti, e' piu' rigoroso" | Esplosione completa solo per spec con mapping esplicito campo→valore→esito. Per lookup senza esiti distinti documentati, una POS rappresentativa basta — risparmia 2-5 righe per campo senza perdere copertura semantica. |
```

## Step 3 — Edit Vincoli Non Negoziabili: aggiungi vincoli #15 e #16

Localizza la sezione "VINCOLI NON NEGOZIABILI" (riga 821) e aggiungi DOPO il vincolo #14 esistente, prima della chiusura sezione:

```
15. **Mutating TC con status 2xx ha minimo 2 step** — action + read-back/SELECT/audit. Response code da solo NON e' side-effect verification. Mutating 4xx/5xx ha minimo 3 step (terzo step = side-effect NOT occurred).
16. **B-001/B-002 composite generate SOLO se spec ha regole composite cross-field** — se la spec ha solo vincoli single-field, M_B non contiene composite_happy/composite_worst. Generare B-001/B-002 senza regole reali = falsi TC che non testano nulla.
```

## Step 4 — Edit frontmatter: version bump + changelog

Localizza il frontmatter (righe 1-20) — cerca:
```
version: 2.0.0
last_modified: 2026-05-11
```

Sostituire con:
```
version: 2.1.0
last_modified: 2026-05-11
```

E **estendere il changelog** esistente (dopo l'entry `2.0.0`) aggiungendo:

```
  2.1.0 (2026-05-11): Residual fixes post-simulazione end-to-end.
    - ADR-001: type-aware "frontiera bassa" in Matrix A (decimal/integer/date).
    - ADR-002: strict-bound (>, <) genera EDGE auto; non-strict (>=, <=) no EDGE.
    - ADR-003: string trim/NFC/max-length opt-in (keyword trigger esplicito).
    - ADR-004: entity naming gerarchia (SCREAMING_SNAKE_CASE per tabelle/section; PascalCase singolare altrove).
    - ADR-005: Phase 4b multi-step mutating obbligatorio (no response-code-only per 2xx).
    - ADR-006: validator WARN channel (exit 0 con [WARN] su stderr).
    - ADR-007: POS lookup unification + NEG per-field collapse + B-001/B-002 condizionale.
    - Vincoli #15 e #16 aggiunti.
```

## Step 5 — Verifica edits

```bash
grep "^version:" skills/siae-qa/SKILL.md
# Atteso: version: 2.1.0

grep -c "ADR-001\|ADR-002\|ADR-003\|ADR-004\|ADR-005\|ADR-006\|ADR-007" skills/siae-qa/SKILL.md
# Atteso: >= 7

grep -c "^15\.\|^16\." skills/siae-qa/SKILL.md
# Atteso: >= 2 (i vincoli #15 e #16 elencati come "15." e "16.")
```

## Step 6 — Verifica integrita' frontmatter YAML

```bash
python3 -c "
import yaml
with open('skills/siae-qa/SKILL.md') as f:
    content = f.read()
fm = content.split('---')[1]
parsed = yaml.safe_load(fm)
assert parsed['version'] == '2.1.0', f'Version mismatch: {parsed[\"version\"]}'
assert 'ADR-007' in parsed['changelog'], 'ADR-007 missing in changelog'
print('Frontmatter OK')
"
```

**Output atteso:** `Frontmatter OK`

## Step 7 — Commit

```bash
git add skills/siae-qa/SKILL.md
git commit -m "feat(siae-qa): version 2.1.0 — anti-razionalizzazione + vincoli + changelog completo

Closure di v2.1.0 residual fixes:
- 2 nuove righe Anti-Razionalizzazione (response code 2xx, lookup unification)
- 2 nuovi vincoli #15 (mutating multi-step) e #16 (B-rows condizionale)
- Frontmatter version 2.0.0 → 2.1.0
- Changelog inline con tutti gli ADR-001..007

Co-Authored-By: SIAE DevForge"
```

## Criteri di Accettazione

- [ ] `grep "^version: 2.1.0" skills/siae-qa/SKILL.md` trova 1 match
- [ ] Changelog frontmatter contiene tutti i 7 ADR **espansi esplicitamente** (NON come range "001..007"). Verifica robusta per ogni ADR singolarmente:
  ```bash
  for n in 001 002 003 004 005 006 007; do
    count=$(grep -c "ADR-${n}\b" skills/siae-qa/SKILL.md)
    echo "ADR-${n}: ${count} occorrenze (atteso ≥ 1)"
    [ "$count" -ge 1 ] || { echo "FAIL: ADR-${n} mancante"; exit 1; }
  done
  echo "All 7 ADR found in SKILL.md"
  ```
  Output atteso: 7 righe `ADR-NNN: ≥1 occorrenze` + `All 7 ADR found`.
- [ ] Vincoli #15 e #16 presenti (`grep "^15\. \*\*\|^16\. \*\*" skills/siae-qa/SKILL.md` trova 2 match)
- [ ] Anti-Razionalizzazione ha ≥ 17 righe (precedenti 15 + 2 nuove)
- [ ] Frontmatter YAML parsabile (Step 6 esce con `Frontmatter OK`)
- [ ] Commit conventional commits
