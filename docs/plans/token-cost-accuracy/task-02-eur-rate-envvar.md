# Task 02 — Tasso EUR via env var + doc

**Stato:** [PENDING]
**File:** `lib/token-collector.py` (MODIFICA), `hooks/ENV_VARS.md` (MODIFICA), `tests/test_token_collector.py` (MODIFICA)
**Dipende da:** Task 01

## Obiettivo

`USD_TO_EUR` configurabile via `DEVFORGE_USD_EUR_RATE`, default 0.91, fallback su valore malformato.

## Red — Test prima

Aggiungere a `tests/test_token_collector.py`. NOTA: `USD_TO_EUR` è valutato a import-time;
il test deve verificare la funzione di parsing, non la costante già caricata. Quindi il
fix deve esporre una funzione `resolve_eur_rate()` testabile.

```python
def test_eur_rate_override(monkeypatch):
    monkeypatch.setenv("DEVFORGE_USD_EUR_RATE", "1.0")
    assert tc.resolve_eur_rate() == 1.0

def test_eur_rate_default(monkeypatch):
    monkeypatch.delenv("DEVFORGE_USD_EUR_RATE", raising=False)
    assert tc.resolve_eur_rate() == 0.91

def test_eur_rate_malformed_falls_back(monkeypatch):
    monkeypatch.setenv("DEVFORGE_USD_EUR_RATE", "not-a-number")
    assert tc.resolve_eur_rate() == 0.91
```

## Green — Implementazione

In `lib/token-collector.py`, sostituire la costante (riga 37) con funzione + costante derivata:

```python
def resolve_eur_rate() -> float:
    raw = os.environ.get("DEVFORGE_USD_EUR_RATE", "")
    if not raw:
        return 0.91
    try:
        value = float(raw)
        return value if value > 0 else 0.91
    except (ValueError, TypeError):
        return 0.91


USD_TO_EUR = resolve_eur_rate()
```

In `usage_cost_eur()` usare `resolve_eur_rate()` invece della costante globale, così
l'override env var ha effetto anche se il modulo è già importato:

```python
def usage_cost_eur(metrics: dict[str, int], model: str | None) -> float:
    rates = pricing_for_model(model)
    cost_usd = (...)  # come Task 01
    return round(cost_usd * resolve_eur_rate(), 6)
```

NOTA: i test del Task 01 assumono rate 0.91 → non settano l'env var, quindi
`resolve_eur_rate()` ritorna 0.91. Coerente.

## Doc — hooks/ENV_VARS.md

Aggiungere una voce (leggere il file esistente per replicarne il formato esatto):

```
### DEVFORGE_USD_EUR_RATE

Tasso di conversione USD→EUR usato da `lib/token-collector.py` per stimare
`cost_estimate_eur` nella telemetria di sessione. Default `0.91`. Valore malformato
o ≤0 → fallback al default. Settabile a livello shell/CI per allineare al cambio reale.
```

## Verifica

- `python3 -m pytest tests/test_token_collector.py -v` → 7 test verdi (4 + 3)
- `grep -q DEVFORGE_USD_EUR_RATE hooks/ENV_VARS.md` → match

## Criteri di accettazione

- [ ] AC4: `DEVFORGE_USD_EUR_RATE=1.0` → cost_eur == cost_usd
- [ ] fallback 0.91 su env assente o malformato
- [ ] `hooks/ENV_VARS.md` documenta la var
