# Task 01 — Estendere tabella regole di esplosione (ADR-001/002/003)

**Goal:** Aggiungere 3 nuove righe alla tabella "Regole di esplosione (da campo a righe di matrice)" in `SKILL.md` per coprire strict-bound numerico (ADR-002 con type-aware ADR-001), non-strict-bound numerico, e string length/encoding opt-in (ADR-003).

**SP:** 2 (Umano) / 1 (Augmented)

**File coinvolti:**
- Modifica: `skills/siae-qa/SKILL.md` righe 297-306 (tabella esplosione)

## Step 1 — Read del file SKILL.md per localizzare la tabella

```bash
sed -n '295,310p' skills/siae-qa/SKILL.md
```

**Output atteso:** righe 297-306 mostrano la tabella attuale con 8 righe (Lookup enumerato, Booleano/flag, Obbligatorio, Opzionale, Formato, Valore fisso, Regola composita, Cross-sezione).

## Step 2 — Edit: inserire 3 nuove righe DOPO "Formato (data/regex/ISO)" e PRIMA di "Valore fisso business"

Cerca la riga esatta in `SKILL.md`:
```
| **Formato (data/regex/ISO)** | POS(corretto) + NEG(formato errato) + EDGE(null se optional) | RELEASED ISO8601 |
```

Aggiungi SUBITO DOPO (3 nuove righe), prima di "Valore fisso business":

```
| **Strict-bound numerico** (`>`, `<`, `> X AND < Y`) | POS(valore tipico) + NEG(violazione) + EDGE(frontiera bassa type-aware) | `importo > 0` decimal → `0.01` EDGE; `quantita > 0` integer → `1` EDGE |
| **Non-strict-bound numerico** (`>=`, `<=`, BETWEEN inclusivo) | POS(valore tipico) + NEG(violazione). **NO EDGE auto** (frontiera già in POS) | `DURATION >= 0` mandatory → 2 righe (POS valido + NEG assente) |
| **String con vincolo length/encoding** (opt-in) | POS + NEG(>max length) + EDGE(trim/NFC) **solo se** spec menziona `trim`, `whitespace`, `NFC`, `max length`, `255 char` | `TITLE max 255 char` → POS + NEG(>255). Senza menzione esplicita: solo POS |
```

**Type-aware "frontiera bassa" (ADR-001):**

Inferire il tipo del campo dalla serializzazione Phase 1.5 (blocco `ENTITA E CAMPI`):

| Tipo dedotto | `> 0` produce | `> 1000` produce | `> '2020-01-01'` produce |
|---|---|---|---|
| `decimal/float` | `0.01` | `1000.01` | — |
| `integer/long` | `1` | `1001` | — |
| `date` | — | — | `2020-01-02` |
| `timestamp` | — | — | `ts + 1s` |

Se la spec NON specifica il tipo: WARNING al developer + default `integer` (più conservativo).

## Step 3 — Verifica edit con grep

```bash
grep -c "Strict-bound numerico\|Non-strict-bound numerico\|String con vincolo length" skills/siae-qa/SKILL.md
```

**Output atteso:** `3`

## Step 4 — Verifica integrità tabella

```bash
sed -n '297,313p' skills/siae-qa/SKILL.md
```

**Output atteso:** la tabella ora ha 11 righe (8 originali + 3 nuove). Le 3 nuove sono posizionate tra "Formato (data/regex/ISO)" e "Valore fisso business". Pipe `|` allineati.

## Step 5 — Commit

```bash
git add skills/siae-qa/SKILL.md
git commit -m "feat(siae-qa): ADR-001/002/003 — estendi tabella esplosione (strict/non-strict numerico + string opt-in)

Aggiunge 3 nuove righe alla tabella regole di esplosione di Phase 1.5:
- strict-bound numerico (>, <) genera EDGE alla frontiera bassa type-aware
- non-strict-bound (>=, <=) NON genera EDGE auto (frontiera già in POS)
- string length/encoding opt-in con keyword trigger (trim/NFC/max length)

ADR-001/002/003 di docs/plans/2026-05-11-siae-qa-v21-residual-design.md.

Co-Authored-By: SIAE DevForge"
```

## Criteri di Accettazione

- [ ] `grep -c "Strict-bound numerico" skills/siae-qa/SKILL.md` = 1
- [ ] `grep -c "Non-strict-bound numerico" skills/siae-qa/SKILL.md` = 1
- [ ] `grep -c "String con vincolo length" skills/siae-qa/SKILL.md` = 1
- [ ] Tabella ha 11 righe nel range linee 297-313 (verifica robusta con range esplicito):
  ```bash
  awk 'NR>=297 && NR<=315 && /^\| \*\*[A-Z]/' skills/siae-qa/SKILL.md | wc -l
  ```
  Output atteso: `11` (8 righe originali + 3 nuove)
- [ ] Commit creato con messaggio conforme conventional commits
- [ ] Nessuna altra modifica accidentale (`git diff HEAD~1 skills/siae-qa/SKILL.md | grep "^[+-]" | wc -l` ≤ 30 righe)
