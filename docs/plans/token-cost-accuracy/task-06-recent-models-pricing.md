# Task 06 — Prezzi modelli recenti (opus 4.8 / 4.7)

**Stato:** [DONE]
**File:** `lib/token-collector.py` (MODIFICA), `tests/test_token_collector.py` (MODIFICA)
**Dipende da:** Task 01
**Requisito:** finding 2026-06-01 — opus-4-8/4-7 cadono in default pricing (sottostima)

## Obiettivo

`claude-opus-4-8` e `claude-opus-4-7` riconosciuti e prezzati come Opus ($5/$25),
non come default (Sonnet $3/$15). Prezzi verificati via web (giu 2026).
NOTA: `sonnet-4-7` NON esiste, non va aggiunto.

## Red — Test prima

```python
def test_opus_4_8_priced_as_opus_not_default():
    cost = tc.usage_cost_eur(_metrics(input=1_000_000), "claude-opus-4-8")
    # Opus input 5.0 USD * 0.91 = 4.55 EUR (NON default 3.0*0.91=2.73)
    assert abs(cost - 4.55) < 0.01

def test_opus_4_7_canonical_recognized():
    assert tc.canonical_model("claude-opus-4-7-20260416") == "claude-opus-4-7"
    assert tc.canonical_model("claude-opus-4-8") == "claude-opus-4-8"
```

## Green — Implementazione

In `lib/token-collector.py`:

1. `PRICING_USD_PER_1M` → aggiungere due entry Opus (stessi rate di opus-4-6):

```python
"claude-opus-4-8":    {"input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write_5m": 6.25, "cache_write_1h": 10.0},
"claude-opus-4-7":    {"input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write_5m": 6.25, "cache_write_1h": 10.0},
```

2. `MODEL_PREFIXES` → aggiungere i due prefissi PRIMA di `"claude-opus-4-6"`
   (l'ordine conta: il match è per `startswith`, i più specifici/recenti vanno prima):

```python
"claude-opus-4-8",
"claude-opus-4-7",
"claude-opus-4-6",
...
```

NOTA: anche senza entry esplicita in PRICING, il fallback `startswith("claude-opus")`
in `pricing_for_model()` userebbe i rate opus-4-6. Ma le entry esplicite rendono il
prezzo leggibile e robusto. Il bug reale era in `MODEL_PREFIXES` (canonical ritornava "").

## Verifica

- `python3 -m pytest tests/test_token_collector.py -v` → 17 test verdi (15 + 2)
- Smoke: `flush` su sessione opus-4-8 → cost_eur calcolato con rate Opus.

## Criteri di accettazione

- [ ] AC10: opus-4-8 prezzato $5 (4.55 EUR/1M input), non default
- [ ] AC11: canonical_model riconosce opus-4-8 e opus-4-7
