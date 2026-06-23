# Task 06 — Aggiornare output_schema.md con generated_at_epoch

**Goal:** Documentare il nuovo campo `meta.generated_at_epoch` in `output_schema.md`, sia per profili persona fisica che giuridica.

**File coinvolti:**
- Modifica: `skills/siae-test-data/references/output_schema.md`

**Dipende da:** nessuno (documentazione pura)

---

## Step 1 — Leggi lo schema attuale

Run: `grep -n "meta\|generated_at" /Users/mazzacuv/Git/siae-dev-forge/skills/siae-test-data/references/output_schema.md`

Individua le righe dove è definito il blocco `meta` per:
1. Profilo persona fisica
2. Profilo soggetto giuridico

---

## Step 2 — Non c'è test per questo task (documentazione)

Verifica che il file esiste e ha la sezione `meta`:

Run: `grep -c "meta" /Users/mazzacuv/Git/siae-dev-forge/skills/siae-test-data/references/output_schema.md`

Output atteso: numero > 0

---

## Step 3 — Implementa la modifica

Apri `skills/siae-test-data/references/output_schema.md`.

Trova i blocchi `meta:` nell'output schema. Per ogni blocco `meta`, aggiungi la riga `generated_at_epoch` con descrizione.

Esempio: se il blocco attuale è:

```yaml
meta:
  residenza_it: bool
  edge_case: str | null
  calcolo_cf: str
  note: str
```

Diventa:

```yaml
meta:
  residenza_it: bool
  edge_case: str | null
  calcolo_cf: str
  note: str
  generated_at_epoch: int  # epoch Unix al momento della generazione del dataset (0 se generato via genera_profilo() diretto)
```

Aggiungi anche una nota in fondo al file (o nella sezione Note/Changelog se esiste):

```markdown
## Changelog

### 2026-06-23
- `meta.generated_at_epoch` (int): timestamp Unix della run di `genera_dataset()`.
  Usato per audit e per verificare l'unicità cross-run dei profili generati.
  Valore `0` indica profili generati direttamente via `genera_profilo()` (path di test diretto).
```

---

## Step 4 — Verifica che il file è aggiornato

Run: `grep -n "generated_at_epoch" /Users/mazzacuv/Git/siae-dev-forge/skills/siae-test-data/references/output_schema.md`

Output atteso: almeno 1 match con la descrizione del campo.

---

## Step 5 — Commit

```
git add skills/siae-test-data/references/output_schema.md
git commit -m "docs(test-data): documenta meta.generated_at_epoch in output_schema.md"
```

## Criteri di accettazione

- [ ] `generated_at_epoch` presente in almeno 1 blocco `meta` di `output_schema.md`
- [ ] Descrizione include il tipo (`int`) e il significato semantico
- [ ] Nota changelog presente con data 2026-06-23
