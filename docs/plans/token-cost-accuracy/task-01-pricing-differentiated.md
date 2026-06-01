# Task 01 — Pricing differenziato cache 5m/1h

**Stato:** [DONE]
**File:** `lib/token-collector.py` (MODIFICA), `tests/test_token_collector.py` (NUOVO)
**Dipende da:** nessuno

## Obiettivo

`cache_write_1h` prezzato 2× input invece di 1.25×. Tabella prezzi con rate separati.

## Red — Test prima

Creare `tests/test_token_collector.py`. Import del modulo (filename con trattino):

```python
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "lib" / "token-collector.py"
spec = importlib.util.spec_from_file_location("token_collector", SCRIPT)
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)
```

Test da scrivere (devono fallire prima del fix):

```python
def test_cache_write_1h_priced_2x_input():
    # sonnet input=3.0 → 1h rate deve essere 6.0 (2x), non 3.75
    metrics = {"input": 0, "output": 0, "cache_read": 0,
               "cache_write_5m": 0, "cache_write_1h": 1_000_000, "cache_write": 1_000_000}
    cost_eur = tc.usage_cost_eur(metrics, "claude-sonnet-4-6")
    # 1M * 6.0 / 1M = 6.0 USD * 0.91 = 5.46 EUR
    assert abs(cost_eur - 5.46) < 0.01

def test_cache_write_5m_priced_1_25x_input():
    metrics = {"input": 0, "output": 0, "cache_read": 0,
               "cache_write_5m": 1_000_000, "cache_write_1h": 0, "cache_write": 1_000_000}
    cost_eur = tc.usage_cost_eur(metrics, "claude-sonnet-4-6")
    # 1M * 3.75 / 1M = 3.75 USD * 0.91 = 3.4125 EUR
    assert abs(cost_eur - 3.4125) < 0.01

def test_mix_5m_1h_sums_both_rates():
    metrics = {"input": 0, "output": 0, "cache_read": 0,
               "cache_write_5m": 1_000_000, "cache_write_1h": 1_000_000, "cache_write": 2_000_000}
    cost_eur = tc.usage_cost_eur(metrics, "claude-sonnet-4-6")
    # (3.75 + 6.0) USD * 0.91 = 8.8725 EUR
    assert abs(cost_eur - 8.8725) < 0.01

def test_unknown_model_falls_back_to_default():
    metrics = {"input": 1_000_000, "output": 0, "cache_read": 0,
               "cache_write_5m": 0, "cache_write_1h": 0, "cache_write": 0}
    cost_eur = tc.usage_cost_eur(metrics, "gpt-nonexistent")
    # default input 3.0 USD * 0.91 = 2.73 EUR
    assert abs(cost_eur - 2.73) < 0.01
```

## Green — Implementazione

In `lib/token-collector.py`:

1. Sostituire `cache_write` con due chiavi in OGNI riga di `PRICING_USD_PER_1M`:

```python
PRICING_USD_PER_1M: dict[str, dict[str, float]] = {
    "claude-opus-4-6":    {"input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write_5m": 6.25, "cache_write_1h": 10.0},
    "claude-sonnet-4-6":  {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write_5m": 3.75, "cache_write_1h": 6.0},
    "claude-haiku-4-5":   {"input": 1.0, "output": 5.0,  "cache_read": 0.10, "cache_write_5m": 1.25, "cache_write_1h": 2.0},
    "default":            {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write_5m": 3.75, "cache_write_1h": 6.0},
}
```

2. In `usage_cost_eur()` (riga ~298-307), sostituire la riga `cache_write` aggregata:

```python
cost_usd = (
    metrics["input"] * rates["input"] / 1_000_000
    + metrics["output"] * rates["output"] / 1_000_000
    + metrics["cache_read"] * rates["cache_read"] / 1_000_000
    + metrics["cache_write_5m"] * rates["cache_write_5m"] / 1_000_000
    + metrics["cache_write_1h"] * rates["cache_write_1h"] / 1_000_000
)
```

NOTA: `metrics` deve contenere `cache_write_5m`/`cache_write_1h`. `usage_tokens()`
(riga 287-295) li produce già. Il campo aggregato `cache_write` resta nel dict dei
metrics (usato per il TOKEN total, non per il costo) — non rimuoverlo.

IMPORTANTE: la chiave `"cache_write"` va RIMOSSA dalla tabella `PRICING_USD_PER_1M`
(non serve più: il costo usa solo `cache_write_5m`/`cache_write_1h`). Lasciarla
genererebbe una chiave inerte fonte di confusione. La rimozione è verificata sotto.

## Verifica

- `python3 -m pytest tests/test_token_collector.py -v` → 4 test verdi
- Grep: `rates["cache_write"]` non deve più esistere nel codice (solo `_5m`/`_1h`).
- Grep: la chiave `"cache_write":` non deve più esistere in `PRICING_USD_PER_1M`
  (solo `"cache_write_5m":` e `"cache_write_1h":`).

## Criteri di accettazione

- [ ] AC1: cache_write_1h sonnet 1M = 5.46 EUR
- [ ] AC2: cache_write_5m sonnet 1M = 3.4125 EUR (invariato vs vecchio rate)
- [ ] AC3: tabella input/output/cache_read invariata
- [ ] Nessun riferimento residuo a `rates["cache_write"]`
