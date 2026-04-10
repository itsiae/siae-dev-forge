# Task 8 — Token collector: session dir + dedupe alignment

**Stato:** [PENDING]
**File coinvolti:** `lib/token-collector.py` (MODIFICA)
**AC coperti:** AC-12, AC-13
**Fase:** PR3
**Dipende da:** Task 2 (session dir)

---

## Contesto

Il token-collector attuale (`lib/token-collector.py`) ha già dedupe via `usage_identity()` e multi-model pricing. Le modifiche necessarie per PR3 sono:

1. Leggere/scrivere state dalla dir di sessione (`DEVFORGE_SESSION_DIR`) anziché `~/.claude/`
2. Allineare pricing table ai valori corretti

## Step 1 — Cambia path state files

Modifica le funzioni `cursor_file()` e `stats_file()` per usare la dir di sessione:

```python
def session_dir():
    """Get session state directory from environment."""
    sd = os.environ.get("DEVFORGE_SESSION_DIR", "")
    if sd and os.path.isdir(sd):
        return sd
    # Fallback to legacy per-project-hash files
    return None

def cursor_file():
    sd = session_dir()
    if sd:
        return os.path.join(sd, "token-cursor")
    return os.path.join(STATE_DIR, f".devforge-token-cursor-{project_hash()}")

def stats_file():
    sd = session_dir()
    if sd:
        return os.path.join(sd, "token-stats.json")
    return os.path.join(STATE_DIR, f".devforge-token-stats-{project_hash()}")
```

## Step 2 — Allinea pricing table

Aggiorna la pricing table ai valori corretti:

```python
PRICING_USD_PER_1M = {
    "claude-opus-4-6":    {"input": 5.0,   "output": 25.0,  "cache_read": 0.50,  "cache_write": 6.25},
    "claude-sonnet-4-6":  {"input": 3.0,   "output": 15.0,  "cache_read": 0.30,  "cache_write": 3.75},
    "claude-haiku-4-5":   {"input": 1.0,   "output": 5.0,   "cache_read": 0.10,  "cache_write": 1.25},
    "default":            {"input": 3.0,   "output": 15.0,  "cache_read": 0.30,  "cache_write": 3.75},
}
```

## Step 3 — Verifica

```bash
DEVFORGE_SESSION_DIR=/tmp/test-session mkdir -p /tmp/test-session
python3 lib/token-collector.py init
ls /tmp/test-session/token-cursor /tmp/test-session/token-stats.json
```
Output atteso: entrambi i file esistono nella dir di sessione.
