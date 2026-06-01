# Task 03 — Retrocompat snapshot legacy

**Stato:** [PENDING]
**File:** `tests/test_token_collector.py` (MODIFICA). Codice: verifica, modifica solo se test rosso.
**Dipende da:** Task 01

## Obiettivo

Garantire che snapshot storici con solo `cache_write` aggregato (senza `cache_write_5m`/
`cache_write_1h`) non causino crash e preservino `cost_eur`.

## Red — Test prima

```python
def test_legacy_snapshot_no_crash():
    # snapshot vecchio formato: solo cache_write, niente 5m/1h
    legacy = {"input": 100, "output": 50, "cache_read": 10,
              "cache_write": 200, "cost_eur": 0.123, "model": "claude-sonnet-4-6"}
    normalized = tc.normalize_usage_snapshot(legacy)
    # non crasha, cost_eur preservato
    assert normalized["cost_eur"] == 0.123
    # i nuovi field assenti → 0 (la distinzione 5m/1h storica è persa, accettato)
    assert normalized["cache_write_5m"] == 0
    assert normalized["cache_write_1h"] == 0

def test_legacy_stats_normalize_no_crash():
    legacy_stats = {"input": 100, "output": 50, "cache_read": 10,
                    "cache_write": 200, "cost_eur": 0.5}
    stats = tc.normalize_stats(legacy_stats)
    assert stats["cost_eur"] == 0.5
    # cache_write ricalcolato da 5m+1h (entrambi 0 nel legacy) → 0
    assert stats["cache_write"] == 0
```

## Green — Implementazione

Verificare `normalize_usage_snapshot()` (riga 310-324) e `normalize_stats()` (riga 114-135).
Entrambe leggono `cache_write_5m`/`cache_write_1h` con default 0 e ricalcolano l'aggregato.
Atteso: i test passano SENZA modifiche al codice (comportamento già corretto).

Se un test fallisce → la funzione va resa robusta (es. `snapshot.get(field, 0) or 0`).
Documentare nel commit quale funzione è stata toccata, se alcuna.

## Verifica

- `python3 -m pytest tests/test_token_collector.py -v` → 9 test verdi (7 + 2)

## Criteri di accettazione

- [ ] AC6 (parziale): snapshot legacy non crasha, cost_eur preservato
- [ ] cache_write_5m/1h = 0 per snapshot legacy
