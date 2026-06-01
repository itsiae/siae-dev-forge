# Task 04 — Dedup tool: analyze-token-usage.py delega al core

**Stato:** [PENDING]
**File:** `tests/analyze-token-usage.py` (MODIFICA), `tests/test_token_collector.py` (MODIFICA)
**Dipende da:** Task 01, Task 02

## Obiettivo

`tests/analyze-token-usage.py` non calcola più i prezzi localmente: delega a
`tc.usage_tokens()` + `tc.usage_cost_eur()` del core (single source of truth).
La colonna costo diventa EUR.

## Red — Test prima

```python
def test_tool_delegates_to_core():
    """Il tool produce lo stesso cost del core per lo stesso usage event."""
    import importlib.util
    from pathlib import Path
    tool_path = Path(__file__).parent / "analyze-token-usage.py"
    spec = importlib.util.spec_from_file_location("analyze_token_usage", tool_path)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)

    usage = {"input_tokens": 1000, "output_tokens": 500,
             "cache_creation_input_tokens": 2000, "cache_read_input_tokens": 300}
    event = {"type": "assistant", "message": {"model": "claude-sonnet-4-6", "usage": usage}}

    # il tool deve esporre una funzione che ritorna il cost_eur via core
    tool_cost = tool.cost_for_usage(event, usage)
    core_metrics = tc.usage_tokens(usage)
    core_cost = tc.usage_cost_eur(core_metrics, "claude-sonnet-4-6")
    assert abs(tool_cost - core_cost) < 1e-9

def test_tool_has_no_local_pricing():
    """Niente tabella PRICING né calculate_cost residui nel tool."""
    tool_src = (Path(__file__).parent / "analyze-token-usage.py").read_text()
    assert "PRICING = {" not in tool_src
    assert "def calculate_cost" not in tool_src
```

## Green — Implementazione

In `tests/analyze-token-usage.py`:

1. Aggiungere in testa l'import del core via importlib (filename con trattino):

```python
import importlib.util
from pathlib import Path

_core_path = Path(__file__).parent.parent / "lib" / "token-collector.py"
_spec = importlib.util.spec_from_file_location("token_collector", _core_path)
_tc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tc)
```

2. Rimuovere la tabella `PRICING` (riga 31-36) e la funzione `calculate_cost` (riga 69-82).

3. Aggiungere funzione di delega + usarla in `analyze_session`:

```python
def cost_for_usage(event: dict, usage: dict) -> float:
    """Costo in EUR via core token-collector (single source of truth)."""
    metrics = _tc.usage_tokens(usage)
    model = _tc.extract_model(event)
    return _tc.usage_cost_eur(metrics, model)
```

4. Nel loop di `analyze_session` (codice reale riga 120-146, `for event in events:`),
   la variabile `event` è già in scope. Modificare la riga 146:

   ```python
   # PRIMA:
   #   usage = extract_usage(event)
   #   if usage:
   #       ...
   #       agent["cost"] += calculate_cost(usage)
   # DOPO:
   usage = extract_usage(event)
   if usage:
       ...
       agent["cost"] += cost_for_usage(event, usage)
   ```

   `event` (non solo `usage`) va passato perché `cost_for_usage` ne estrae il modello
   via `_tc.extract_model(event)`.

5. Aggiornare label colonna costo e docstring da `$`/USD a `€`/EUR per coerenza
   (header `Cost` → `Cost(€)`, formato `${...}` → `€{...}`).

**Limitazione nota:** un evento con `cache_creation_input_tokens` flat (formato API legacy,
senza il dict `cache_creation` con `ephemeral_5m/1h`) viene prezzato come 5m ($3.75/M su
sonnet) dal fallback di `usage_tokens()`. È il comportamento del core, condiviso tra tool e
telemetria, quindi coerente; documentato qui per trasparenza.

## Verifica

- `python3 -m pytest tests/test_token_collector.py -v` → 11 test verdi (9 + 2)
- `grep -c "PRICING = {\|def calculate_cost" tests/analyze-token-usage.py` → 0
- Smoke: il tool gira ancora su un .jsonl reale senza errori di import.

## Criteri di accettazione

- [ ] AC5: tool produce stesso cost del core per stesso evento
- [ ] nessuna tabella PRICING né calculate_cost locale nel tool
- [ ] AC7: intera suite verde (11 test totali in test_token_collector.py)
