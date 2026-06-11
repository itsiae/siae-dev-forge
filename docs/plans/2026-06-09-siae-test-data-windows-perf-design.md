# Design: siae-test-data Windows Performance Fix

**Data:** 2026-06-09
**Branch:** fix/test-data-upgrade
**SP:** 5 Umano / 2 Augmented
**Complessità:** Media
**Tipo:** Refactoring/Ottimizzazione

---

## Contesto

La skill `siae-test-data` è lenta su Windows dopo il completamento del wizard.
Root cause identificati da 3 agenti ciechi × 4 round (Independent → Cross-pollination →
Fact-check → Sintesi), 9/9 claim CONFIRMED, 0 REFUTED.

---

## Root Cause Confermati (priorità decrescente)

| RC | File | Riga | Impatto Windows | Fix |
|---|---|---|---|---|
| RC1 | SKILL.md | 97-98 | 8 Read tool call sequenziali = 2.4-6.4s | Aggiungere hint lettura batch parallela |
| RC2 | SKILL.md | 37, 130 | Soglia N>50 forza path Claude-native per tutti i preset | Soglia → N>5 + hint generazione batch |
| RC3 | scripts/\* | vari | 10 open() su 6 file, 4 duplicati (+200-400ms Defender) | data_store.py lazy singleton |
| RC4 | generate_profiles.py | 91,123,154,210 | list comprehension O(N) per profilo | Pre-computed `_BELFIORE_COMUNI_KEYS` ecc. |
| RC5 | cf_calculator.py | 46-53 | str.maketrans ricreato ×N per profilo | `_NORMALIZE_TABLE` costante di modulo |
| RC6 | SKILL.md | 41 | `python3` non trovato su Windows → fallback path lento | Fallback `python`/`py` |
| RC7 | generate_profiles.py | 441 | valida_e_filtra O(N) su profili già corretti | `skip_validation=False` param |

---

## Approccio scelto: Fix chirurgico (Approccio A)

Modifiche mirate file:riga, nessun refactoring architetturale. Zero rischio di
regressione sul determinismo RNG (pre-computed lists usano insertion order invariante).

---

## File modificati

### Nuovo: `scripts/data_store.py`
Cache lazy singleton JSON. `get(name)` apre il file al primo accesso e restituisce
l'oggetto cached nelle chiamate successive. Elimina 4 open() duplicati.

### `scripts/cf_calculator.py`
- Importa `data_store`
- `_NORMALIZE_TABLE = str.maketrans({...25 entry...})` come costante di modulo
- `_normalize()` usa `s.translate(_NORMALIZE_TABLE)` invece di ricreare la table
- `carica_belfiore_comuni()` e `carica_belfiore_esteri()` usano `data_store.get()`

### `scripts/address_generator.py`
- Importa `data_store`
- `_carica_cap_citta()` restituisce `data_store.get("cap_citta.json")`

### `scripts/validators.py`
- Importa `data_store`
- `_carica_cap_citta()` restituisce `data_store.get("cap_citta.json")`

### `scripts/piva_calculator.py`
- Importa `data_store`
- `_carica_codici_provincia()` usa `data_store.get("forme_giuridiche.json")`

### `scripts/generate_profiles.py`
- Importa `data_store`
- `_carica_json(name)` restituisce `data_store.get(name)`
- Costanti pre-computed dopo riga 61: `_BELFIORE_COMUNI_KEYS`, `_CAP_ITALIA_KEYS`, `_STATI_UE`, `_STATI_EXTRA_UE`
- `_stato_random()`: usa `_STATI_UE` / `_STATI_EXTRA_UE` invece di list comprehension O(M)
- `_genera_anagrafica_persona_fisica()` righe 123/154: usa `_BELFIORE_COMUNI_KEYS` / `_CAP_ITALIA_KEYS`
- `_genera_soggetto_giuridico()` riga 210: usa `_CAP_ITALIA_KEYS`
- `valida_e_filtra()`: aggiunto `skip_validation=False`, return early se True
- Argparse: aggiunto `--skip-validation`

### `SKILL.md`
- Passo 0 riga 41: `python3 --version 2>/dev/null` → con fallback `python`/`py`
- Passo 2 riga 97: aggiunto hint lettura parallela
- Passo 3 riga 37: `50 profili` → `5 profili`
- Passo 3 pre-loop: aggiunto hint generazione batch unico

---

## Flusso open() con data_store

```
Ordine import: piva_calculator → address_generator → validators → generate_profiles

piva_calculator  → data_store.get("forme_giuridiche.json")  → open #1 ✓
address_generator → data_store.get("cap_citta.json")        → open #2 ✓
validators       → data_store.get("cap_citta.json")         → CACHE HIT
                 → carica_belfiore_comuni()                  → open #3 ✓
                 → carica_belfiore_esteri()                  → open #4 ✓
generate_profiles → data_store.get("nomi_italiani.json")    → open #5 ✓
                 → data_store.get("nomi_esteri.json")        → open #6 ✓
                 → data_store.get("forme_giuridiche.json")   → CACHE HIT
                 → carica_belfiore_comuni()                  → CACHE HIT
                 → carica_belfiore_esteri()                  → CACHE HIT

Totale: 10 open() → 6 open() — 4 duplicati eliminati
```

---

## Determinismo

Pre-computed lists (`_BELFIORE_COMUNI_KEYS` ecc.) sono calcolate al module load time
con lo stesso ordine di iterazione (`dict.keys()` = insertion order, invariante Python 3.7+).
Il seed RNG `profilo_id` produce lo stesso output prima e dopo il refactoring.

---

## Criteri di accettazione

- [ ] T01-T22 in SKILL.md passano (verifica determinismo output Python)
- [ ] `python3 generate_profiles.py --categorie PRIVATO --residenza IT --quantita 3 --formato JSON` output identico a prima
- [ ] Dopo import, `data_store._CACHE` contiene esattamente 6 chiavi
- [ ] `--skip-validation` non altera output JSON
- [ ] Smoke test `__main__` in cf_calculator, piva_calculator, address_generator, validators passano
- [ ] `_normalize("Müller") == "MULLER"` (verifica RC5)
- [ ] `(python3 ... || python ... || py ...) && echo OK` funziona in Git Bash Windows

---

## Decisioni architetturali

**ADR-1:** `data_store.get()` restituisce il dict grezzo (non una copia). Sicuro perché
nessun modulo muta i dict dei reference dopo il caricamento.

**ADR-2:** `carica_belfiore_comuni()` e `carica_belfiore_esteri()` in cf_calculator
continuano a filtrare le entry `_*` ad ogni chiamata (2 volte totali). Il costo è
trascurabile (O(n) dict comprehension) rispetto all'eliminazione del file I/O.

**ADR-3:** `skip_validation=False` è separato da `strict=True` perché hanno semantica
diversa: `strict` controlla il raise su invalidi, `skip_validation` salta il loop
intero. Combinarli violerebbe il principio di singola responsabilità.
