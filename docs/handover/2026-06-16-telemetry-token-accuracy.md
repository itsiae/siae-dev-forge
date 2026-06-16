# Handover consumer — Accuratezza token/costi (fix 2026-06-16)

**Per:** consumer telemetria a valle (Control Tower / developer analytics).
**Branch:** `fix/telemetry-token-accuracy`. **Design:** `docs/plans/2026-06-16-telemetry-token-accuracy-fix/design.md`.

Questo fix corregge 3 cause-radice dietro 5 anomalie osservate su token/costi. Cosa cambia per chi consuma gli eventi.

## 1. Nuovo campo `token_state_complete` su `session_end`

Booleano. **`true` solo se lo stato token è stato letto da una sessione risolta e `total_tokens > 0`.**

```jsonc
"session_end": {
  "meta": {
    "total_tokens": 1234567,
    "token_state_complete": true,   // ⬅ nuovo
    "by_model": { ... },
    ...
  }
}
```

**Regola consumer:** scartare i blocchi con `token_state_complete=false` (token a 0 / stato non ricostruibile) invece di contarli come reali. Prima del fix questi eventi emettevano zeri indistinguibili da valori veri → 33 dev a costo 0 e copertura `by_model` 904/96k. Durante il rollout mixed-version è atteso vedere ancora `false` su sessioni con hook pre-fix: NON è un nuovo bug.

## 2. `by_model` non è più cumulativo cross-sessione

Prima: in assenza di `DEVFORGE_SESSION_DIR` lo stato finiva in un file **globale per-progetto** che sopravviveva tra sessioni, congelando un blocco modello (es. Opus `cache_read:703803830` byte-identico ri-emesso su 36+ sessioni → costo ~5×).

Dopo: lo stato è **sempre per-sessione** (auto-derivato dal session id). `by_model`/`by_model_tokens` riflettono solo la sessione corrente e vengono azzerati al cambio di file `.jsonl`. **Il blocco congelato non comparirà più.** Eventuali dati storici già atterrati con il blocco duplicato vanno deduplicati a valle (per `sid`, valore-picco).

## 3. Semantica `total_tokens_delta` vs `session_tokens_cumulative` (`commit_created`/`pr_merged`)

Due campi distinti, **entrambi raw e corretti**:

| Campo | Significato |
|---|---|
| `session_tokens_cumulative` | totale token della sessione fino a questo commit/merge (cumulativo, monotòno) |
| `total_tokens_delta` / `output_tokens_delta` | incremento dal commit precedente |

**Al primo commit di sessione `total_tokens_delta == session_tokens_cumulative`** ed è **corretto**: l'intera sessione fino a quel punto è il primo delta. Dal secondo commit in poi `total_tokens_delta < session_tokens_cumulative`.

**Regole consumer:**
- token-per-sessione: usare `session_tokens_cumulative` **massimo** per `sid` (o `session_end.total_tokens`), **mai** la media/somma dei cumulativi (overcount).
- token-per-commit: sommare `total_tokens_delta` (già non sovrapposti tra commit).

## 4. Costo per-tipo (invariato, già disponibile)

`session_end` espone i 5 componenti come campi first-class — `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_5m_tokens`, `cache_write_1h_tokens` — e `by_model_tokens` con la stessa scomposizione per modello, più `pricing` (listino + tasso EUR). Il costo è ricostruibile a valle applicando qualsiasi listino; `cache_read` è ~1/50 dell'output, quindi `total_tokens` da solo sovrastima il costo. Usare la scomposizione, non il totale.
