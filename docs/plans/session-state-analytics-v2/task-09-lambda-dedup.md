# Task 9 — Lambda dedup: idempotenza su event_id

**Stato:** [PENDING]
**File coinvolti:** `infra/telemetry/lambda/handler.py` (MODIFICA)
**AC coperti:** AC-11
**Fase:** PR3
**Dipende da:** nessuno (infra indipendente)

---

## Step 1 — Aggiungi dedup su event_id nella Lambda

Modifica `infra/telemetry/lambda/handler.py` per usare `event_id` come parte della S3 key.

Oggi la Lambda scrive con key:
```
year=YYYY/month=MM/day=DD/<uuid>.jsonl
```

Dopo: se il batch contiene eventi con `event_id` (schema v2), usa una key deterministica:
```
year=YYYY/month=MM/day=DD/sid-<sid>/batch-<first_event_id>-<last_event_id>.jsonl
```

Questo rende l'upload idempotente: lo stesso batch uploadato 2 volte sovrascrive lo stesso file S3.

Per eventi schema v1 (senza event_id), mantieni il comportamento attuale con UUID.

## Step 2 — Verifica

```bash
cd infra/telemetry
python3 -m py_compile lambda/handler.py
```
Output atteso: nessun errore.

Test funzionale: inviare lo stesso batch 2 volte, verificare che su S3 c'è un solo file (non duplicato).
