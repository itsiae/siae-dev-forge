# Task 05 — Modello prevalente + token in telemetria

**Stato:** [PENDING]
**File:** `lib/token-collector.py` (MODIFICA), `hooks/stop-gate` (MODIFICA), `tests/test_token_collector.py` (MODIFICA)
**Dipende da:** Task 01, Task 02
**Requisito:** utente 2026-06-01 — "metterei anche il numero di token e il modello prevalentemente usato"

## Obiettivo

Tracciare nel `token-stats.json` il modello con più token cumulati (`model_prevalent`)
ed esporlo nella telemetria `session_end`. Il `total_tokens` è già emesso (stop-gate riga 90).

## Red — Test prima

```python
def test_model_prevalent_picks_max_tokens():
    stats = tc.empty_stats()
    # usage 1: sonnet, 1000 token
    s1 = {"input": 1000, "output": 0, "cache_read": 0, "cache_write_5m": 0,
          "cache_write_1h": 0, "cache_write": 0, "total": 1000,
          "model": "claude-sonnet-4-6", "cost_eur": 0.0}
    tc.add_usage_delta(stats, None, s1)
    # usage 2: opus, 5000 token
    s2 = {"input": 5000, "output": 0, "cache_read": 0, "cache_write_5m": 0,
          "cache_write_1h": 0, "cache_write": 0, "total": 5000,
          "model": "claude-opus-4-6", "cost_eur": 0.0}
    tc.add_usage_delta(stats, None, s2)
    tc.finalize_model_prevalent(stats)
    assert stats["model_prevalent"] == "claude-opus-4-6"
    assert stats["by_model"]["claude-sonnet-4-6"] == 1000
    assert stats["by_model"]["claude-opus-4-6"] == 5000

def test_model_prevalent_tiebreak_alphabetical():
    stats = tc.empty_stats()
    s1 = {"input": 1000, "output": 0, "cache_read": 0, "cache_write_5m": 0,
          "cache_write_1h": 0, "cache_write": 0, "total": 1000,
          "model": "claude-sonnet-4-6", "cost_eur": 0.0}
    s2 = {"input": 1000, "output": 0, "cache_read": 0, "cache_write_5m": 0,
          "cache_write_1h": 0, "cache_write": 0, "total": 1000,
          "model": "claude-opus-4-6", "cost_eur": 0.0}
    tc.add_usage_delta(stats, None, s1)
    tc.add_usage_delta(stats, None, s2)
    tc.finalize_model_prevalent(stats)
    # parità 1000 vs 1000 → ordine alfabetico → "claude-opus-4-6" < "claude-sonnet-4-6"
    assert stats["model_prevalent"] == "claude-opus-4-6"

def test_normalize_stats_without_by_model_no_crash():
    legacy = {"input": 100, "output": 50, "cache_read": 0, "cache_write_5m": 0,
              "cache_write_1h": 0, "cost_eur": 0.1}
    stats = tc.normalize_stats(legacy)
    assert stats["by_model"] == {}
    assert stats["model_prevalent"] == ""
```

## Green — Implementazione

In `lib/token-collector.py`:

1. `empty_stats()` (riga 100-111) → aggiungere due campi:

```python
"by_model": {},
"model_prevalent": "",
```

2. `add_usage_delta(stats, previous, current)` → dopo l'aggiornamento token, accumulare
   il delta totale nel modello corrente. Il delta token è la somma dei delta dei field
   già calcolati. Aggiungere alla fine, prima del `return changed`:

```python
model = current.get("model") or ""
if model:
    delta_total = sum(
        max(int(current.get(f, 0) or 0) - int((previous or {}).get(f, 0) or 0), 0)
        for f in ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")
    )
    if delta_total > 0:
        by_model = stats.setdefault("by_model", {})
        by_model[model] = int(by_model.get(model, 0)) + delta_total
        changed = True
```

3. Nuova funzione `finalize_model_prevalent(stats)`:

```python
def finalize_model_prevalent(stats: dict[str, Any]) -> None:
    by_model = stats.get("by_model") or {}
    if not by_model:
        stats["model_prevalent"] = ""
        return
    # max token; tie-break: ordine alfabetico (min nome) per determinismo
    stats["model_prevalent"] = min(
        by_model.items(), key=lambda kv: (-int(kv[1]), kv[0])
    )[0]
```

4. In `update()` (riga 437-442), prima di `write_stats(stats)`, chiamare
   `finalize_model_prevalent(stats)`.

5. `normalize_stats()` (riga 114-135) → aggiungere lettura safe dei nuovi campi:

```python
raw_by_model = raw.get("by_model")
stats["by_model"] = raw_by_model if isinstance(raw_by_model, dict) else {}
stats["model_prevalent"] = raw.get("model_prevalent") or ""
```

   POSIZIONE: inserire queste due righe DOPO la chiusura del loop `for key, default in
   stats.items():`, prima della riga `stats["cache_write"] = int(...)` (riga ~128). Il loop
   esistente passa già `by_model`/`model_prevalent` nel ramo `else` (`value or default`) senza
   crash, ma la riassegnazione esplicita post-loop garantisce il tipo corretto (dict/str)
   indipendentemente da `empty_stats()`.

In `hooks/stop-gate` (blocco python inline riga ~75-82): estendere la lettura e il JSON.

```bash
# nel python inline che legge token-stats.json, aggiungere model_prevalent:
print(f'{d.get("total",0)}\t{d.get("output",0)}\t{d.get("cost_eur",0)}\t{d.get("model_prevalent","")}')
# poi parsare il 4° campo in TOKEN_MODEL e aggiungerlo al JSON session_end:
```

Aggiungere `TOKEN_MODEL` (cut -f4) e nel JSON `session_end`:
`"model_prevalent":"${TOKEN_MODEL}"`.

## Verifica

- `python3 -m pytest tests/test_token_collector.py -v` → 14 test verdi (11 + 3)
- `grep -q model_prevalent hooks/stop-gate` → match
- Smoke: `python3 lib/token-collector.py flush` su sessione reale → output JSON con
  `by_model` e `model_prevalent` valorizzati.

## Criteri di accettazione

- [ ] AC7: `session_end` include `total_tokens` + `model_prevalent`
- [ ] AC8: model_prevalent = max token, tie-break alfabetico
- [ ] retrocompat: normalize_stats senza by_model → default safe
- [ ] stop-gate emette il nuovo campo
