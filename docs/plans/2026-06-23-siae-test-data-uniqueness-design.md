# siae-test-data — Unicità Nomi Cross-Run — Design Doc

> **Data:** 2026-06-23
> **Status:** APPROVATO (brainstorming 3 agenti ciechi)
> **Skill:** `skills/siae-test-data/`

---

## Problema

La skill `siae-test-data` genera nomi, cognomi e ragioni sociali deterministici sul
`profilo_id`. Lo stesso set di parametri CLI/config produce **identici** profili tra
run successive — `P-IT-001` genera sempre "Mario Rossi", "P-IT-002" sempre "Luca
Esposito", ecc.

Pool attuale: 31 nomi M + 30 nomi F + 51 cognomi = **3.111 combinazioni**. Probabilità
di collisione al 50% già dopo 65 generazioni (problema del compleanno). Con stesso
config: **collisione garantita al 100%** da run 1.

---

## Vincolo critico (Agente 3)

`_normalize()` in `cf_calculator.py` usa `re.sub(r"[^A-Z]", "", s)`: qualunque cifra
o underscore viene eliminato silenziosamente **prima** del calcolo del CF. Embeddare
l'epoch nel campo `nome`/`cognome` produrrebbe lo stesso CF del nome-base — incoerenza
grave. **Il nome/cognome rimane "pulito"; l'epoch agisce sul seed RNG, non sul campo.**

---

## Soluzione

### Principio

Rendere `id_tag` auto-generato da epoch (5 cifre mod 100.000) quando non fornito
esplicitamente. Questo cambia il `profilo_id` (es. `P-IT-001` → `P-83421-IT-001`),
cambia il seed del `random.Random`, e produce nomi genuinamente diversi tra run.

- **Nome/cognome**: invariati nel campo — CF calcolato correttamente.
- **Ragione sociale**: il suffisso corrente `profilo_id[-4:]` viene esteso con `id_tag`.
- **Output JSON**: nuovo campo `meta.generated_at_epoch` (epoch Unix intero) per audit.

### Schema data-flow

```
genera_dataset(config)
  ├── id_tag = config["id_tag"] OR str(int(time.time()) % 100_000)
  ├── run_epoch = int(time.time())   ← epoch completo per meta
  ├── tag_suffix = f"-{id_tag}"
  ├── pid = f"P{tag_suffix}-IT-001"  →  seed RNG diverso → nome diverso
  └── _mk_profilo(pid, ..., run_epoch)
        └── genera_profilo(profilo_id, ..., run_epoch)
              ├── profilo["meta"]["generated_at_epoch"] = run_epoch
              └── _genera_soggetto_giuridico(..., run_epoch)
                    └── ragione = f"{ragione} {profilo_id[-4:]}-{id_tag_suffix}"
```

---

## File modificati

| File | Tipo modifica |
|------|--------------|
| `skills/siae-test-data/scripts/generate_profiles.py` | Auto-generate id_tag, propagare run_epoch, aggiornare ragione sociale, aggiungere meta.generated_at_epoch, aggiungere --id-tag CLI |
| `skills/siae-test-data/scripts/generate_profiles.js` | Aggiungere epoch tag al pid, aggiornare ragione sociale, propagare in module.exports |
| `skills/siae-test-data/references/output_schema.md` | Documentare meta.generated_at_epoch |
| `skills/siae-test-data/tests/test_perf_windows_fixes.py` | Aggiungere test cross-run uniqueness (Python) |
| `skills/siae-test-data/tests/test_node_fallback.py` | Aggiungere test cross-run uniqueness (Node.js) |

---

## Modifiche dettagliate

### `generate_profiles.py` — `genera_dataset()` (righe 387–444)

```python
import time  # aggiungere in testa al file

def genera_dataset(config: dict) -> list[dict]:
    # ... (invariato fino a riga 408)
    id_tag = config.get("id_tag", "")
    if not id_tag:                                              # NUOVO
        id_tag = str(int(time.time()) % 100_000)               # NUOVO
    run_epoch = int(time.time())                               # NUOVO
    tag_suffix = f"-{id_tag}"                                   # era: f"-{id_tag}" if id_tag else ""

    def _mk_profilo(pid: str, cat: str, ruoli: list[str], fg: str | None):
        return genera_profilo(
            pid, cat, ruoli, area, fg, edge,
            edge_pattern_filter=edge_pattern_filter,
            edge_probability=edge_probability,
            run_epoch=run_epoch,                               # NUOVO parametro
        )
```

### `generate_profiles.py` — `genera_profilo()` firma (riga 309)

```python
def genera_profilo(
    profilo_id: str,
    macro_categoria: str,
    ruoli: list[str],
    area_residenza: str,
    forma_giuridica: str | None,
    edge_case_flag: bool,
    edge_pattern_filter: list[str] | None = None,
    edge_probability: float = 0.6,
    run_epoch: int = 0,                                        # NUOVO
) -> dict:
```

### `generate_profiles.py` — `profilo["meta"]` (righe 357–382)

Aggiungere `"generated_at_epoch": run_epoch` a entrambi i blocchi meta (persona fisica
riga 357 e giuridica riga 375):

```python
profilo["meta"] = {
    "residenza_it": ...,
    "edge_case": ...,
    "calcolo_cf": ...,
    "note": "",
    "generated_at_epoch": run_epoch,                           # NUOVO
}
```

### `generate_profiles.py` — `_genera_soggetto_giuridico()` (riga 212)

La funzione riceve già `profilo_id`. Il `profilo_id` include già il nuovo `id_tag`
nel path `P-83421-IT-001`, quindi `profilo_id[-4:]` diventa `"001"` (invariato).
Per la ragione sociale aggiungere un'ulteriore differenziazione visiva estraendo
il tag dal `profilo_id`:

```python
# Riga 212 — PRIMA:
ragione = f"{ragione} {profilo_id[-4:]}"

# DOPO: estrai id_tag dal profilo_id (es. "83421" da "B-SDC-83421-IT-001")
_parts = profilo_id.split("-")
_epoch_suffix = _parts[2] if len(_parts) >= 4 else profilo_id[-4:]
ragione = f"{ragione} {profilo_id[-4:]}-{_epoch_suffix}"
```

### `generate_profiles.py` — CLI `main()` (riga 671)

```python
parser.add_argument(
    "--id-tag", dest="id_tag", default=None,
    help="Tag univoco nel profilo_id (default: auto-generato da epoch 5 cifre)"
)
# In config build (riga ~688):
"id_tag": args.id_tag or "",   # None → genera_dataset auto-genera
```

### `generate_profiles.js` — `main()` (righe 488–507)

```javascript
// Prima del loop — riga ~487
const idTag = args['id-tag'] || String(Math.floor(Date.now() / 1000) % 100000).padStart(5, '0');

// pid PRIVATO/AUTORE/EDITORE (riga 503):
const pid = `${pre}-${idTag}-${nazRaw[ni]}-${String(i).padStart(3,'0')}`;

// pid BUSINESS (riga 496):
const pid = `B-${fg}-${idTag}-${nazRaw[ni]}-${String(i).padStart(3,'0')}`;
```

---

## Criteri di accettazione

1. Due run successive senza `--id-tag` producono `profilo_id` diversi (epoch diverso).
2. Due run successive senza `--id-tag` producono almeno 1 nome/cognome diverso su 5 profili.
3. Il CF calcolato rimane formalmente valido (16 char, checksum corretto) indipendentemente dall'epoch.
4. Con `--id-tag FIXED` esplicito il comportamento deterministico è preservato (backward compat).
5. Il campo `meta.generated_at_epoch` è presente nell'output JSON per ogni profilo.
6. La ragione sociale include il suffisso epoch (non solo il progressivo run-level).
7. Tutti i test esistenti passano senza modifiche (il contratto di determinismo è testato a livello `genera_profilo()` diretto, non `genera_dataset()`).

---

## Considerazioni sicurezza

- Nessuna PII aggiuntiva introdotta: `generated_at_epoch` è solo un timestamp Unix.
- Il pool di nomi non cambia: i dati rimangono inequivocabilmente fittizi.
- L'epoch a 5 cifre (mod 100.000) non è tracciabile a un'ora specifica della giornata.

---

## Non in scope

- Ampliamento del pool `nomi_italiani.json` (migliora la cardinalità ma non risolve
  il determinismo — problema ortogonale).
- Registry persistente cross-run (complessità sproporzionata, rotto dal path Claude-native).
- Modifiche a `cf_calculator.py` o `piva_calculator.py`.
