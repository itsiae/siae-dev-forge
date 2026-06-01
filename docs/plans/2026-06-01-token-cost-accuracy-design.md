# Design — Accuratezza calcolo costi token DevForge

**Data:** 2026-06-01
**Autore:** Lorenzo De Tomasi (+ Claude)
**Stato:** APPROVATO
**Complessità:** Media
**File coinvolti:** `lib/token-collector.py` (MODIFICA), `tests/analyze-token-usage.py` (MODIFICA), `tests/test_token_collector.py` (NUOVO), `hooks/ENV_VARS.md` (MODIFICA), `hooks/stop-gate` (MODIFICA)

## Contesto

`lib/token-collector.py` traccia incrementalmente input/output/cache token dal `.jsonl`
di sessione e ne stima il costo in EUR, emesso in telemetria via `hooks/stop-gate`
(evento `session_end`, campo `cost_estimate_eur`). Dedup via `usage_index` su `message.id`,
multi-model pricing, scritture atomiche: tutto corretto.

## Problema

Prezzi cache write Anthropic verificati (giugno 2026):
- 5-min cache write = **1.25×** base input
- 1-hour cache write = **2×** base input
- cache read = **0.1×** base input

`token-collector.py` traccia separatamente `cache_write_5m` e `cache_write_1h`
(`usage_tokens()` riga 271-295) ma poi li **somma** in `cache_write` e applica un
**rate unico** in `usage_cost_eur()` (riga 305):

```python
metrics["cache_write"] * rates["cache_write"] / 1_000_000
```

Il rate `cache_write` in tabella = 1.25× input (corretto solo per il 5m).
→ I token `cache_write_1h` sono prezzati 1.25× invece di 2× → **costo 1h sottostimato del 37,5%**.

Problemi secondari:
- `USD_TO_EUR = 0.91` hardcoded, nessun override.
- `tests/analyze-token-usage.py` ha una tabella `PRICING` duplicata (solo Sonnet, solo USD),
  non sincronizzata con la tabella core → due fonti di verità divergenti.

NOTA: la tabella `PRICING_USD_PER_1M` per input/output/cache_read è **corretta**
(verificata: Opus 4.6 $5/$25, Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5). Non va cambiata,
solo estesa con i due rate cache differenziati.

## Decisione (Approccio A + dedup)

1. **Estendere `PRICING_USD_PER_1M`**: sostituire `cache_write` con `cache_write_5m` e
   `cache_write_1h` per ogni modello.

   | modello | input | output | cache_read | cw_5m (1.25×) | cw_1h (2×) |
   |---|---|---|---|---|---|
   | opus-4-6 | 5.0 | 25.0 | 0.50 | 6.25 | 10.0 |
   | sonnet-4-6 | 3.0 | 15.0 | 0.30 | 3.75 | 6.0 |
   | haiku-4-5 | 1.0 | 5.0 | 0.10 | 1.25 | 2.0 |
   | default | 3.0 | 15.0 | 0.30 | 3.75 | 6.0 |

2. **`usage_cost_eur()`**: prezzare i due field separatamente:
   ```python
   + metrics["cache_write_5m"] * rates["cache_write_5m"] / 1_000_000
   + metrics["cache_write_1h"] * rates["cache_write_1h"] / 1_000_000
   ```

3. **Tasso EUR via env var**: `USD_TO_EUR = float(os.environ.get("DEVFORGE_USD_EUR_RATE", "0.91"))`
   con guard su parse error (fallback 0.91).

4. **Dedup tool (single source of truth)**: `tests/analyze-token-usage.py` deve caricare
   il core. Il filename `lib/token-collector.py` ha un trattino → import diretto impossibile.
   Meccanismo: `importlib.util.spec_from_file_location("token_collector", <path>)`,
   pattern già usato in `tests/test_anti_bloat_lint.py:46`. Path risolto relativo allo
   script: `Path(__file__).parent.parent / "lib" / "token-collector.py"`.
   Il tool **delega completamente** a `usage_cost_eur()` del core (rimuove la propria
   `calculate_cost()` e la tabella `PRICING` locale). Conseguenza: il tool diventa
   EUR-aware come il core; la colonna "Cost" passa da USD a EUR per coerenza (header e
   docstring aggiornati). Nessun calcolo di pricing residuo nel tool.

5. **Documentazione env var**: aggiungere `DEVFORGE_USD_EUR_RATE` a `hooks/ENV_VARS.md`
   (default 0.91, descrizione, settabile a livello shell/CI). Nota: `test_env_vars_doc_sync.py`
   verifica solo i prefissi `DEVFORGE_EVIDENCE_*`, quindi non fallirà — ma ENV_VARS.md è la
   sede canonica per coerenza documentale.

6. **Modello prevalente + token nella telemetria** (requisito utente 2026-06-01): oggi
   `token-stats.json` aggrega i token ma NON traccia il modello; `empty_stats()` non ha campo
   model. La telemetria `session_end` (stop-gate riga 90) emette già `total_tokens` e
   `output_tokens`, ma non il modello. Aggiungere:
   - `empty_stats()` → campo `by_model: {}` (dict modello→token totali accumulati) e
     `model_prevalent: ""` (derivato).
   - `add_usage_delta()` → accumulare il delta token nel `by_model[model]` usando il modello
     dello snapshot corrente.
   - In `update()` (dopo l'accumulo) → `model_prevalent` = chiave di `by_model` col massimo
     totale token (tie-break: ordine alfabetico per determinismo).
   - `normalize_stats()` → leggere `by_model`/`model_prevalent` con default safe (retrocompat
     snapshot privi del campo).
   - `stop-gate` → estendere il JSON `session_end` con `model_prevalent` (e `total_tokens`
     resta, già presente). Il blocco python inline in stop-gate (riga ~75-82) legge già
     `total`/`output`/`cost_eur` da token-stats.json: aggiungere lettura di `model_prevalent`.

## Flusso dati (invariato)

`.jsonl` → `usage_tokens()` (già separa 5m/1h) → `usage_cost_eur()` (FIX qui) →
`add_usage_delta()` → `token-stats.json` → `stop-gate` → telemetria.
Nessun cambio di schema `token-stats.json`: i field `cache_write_5m`/`cache_write_1h`
esistono già. Solo il `cost_eur` diventa accurato.

## Gestione errori / retrocompatibilità

- Snapshot storici in `usage_index` con solo `cache_write` aggregato: `normalize_usage_snapshot`
  ricostruisce 5m/1h dai field salvati; se assenti → 0, nessun crash.
- `DEVFORGE_USD_EUR_RATE` malformato → fallback silente 0.91 (no break sessione).
- Cost storici già loggati restano nei dati passati: il fix corregge solo le sessioni future
  (atteso, non è una regressione — accuratezza ↑).

## Testing

`tests/test_token_collector.py` (nuovo, import core via `importlib` pattern `test_anti_bloat_lint.py`):
1. `cache_write_1h` prezzato 2× input (era 1.25×) — il bug regression test
2. `cache_write_5m` prezzato 1.25× input — no regression
3. mix 5m+1h → somma corretta dei due rate
4. fallback modello sconosciuto → default rates
5. `DEVFORGE_USD_EUR_RATE` override + fallback su valore malformato
6. dedup invariato (stesso message.id → delta 0)
7. migrazione snapshot legacy: snapshot storico con solo `cache_write` non-zero
   (senza `cache_write_5m`/`cache_write_1h`) → `normalize_usage_snapshot` non crasha,
   `cost_eur` preservato, nuovi field a 0
8. delega tool: `analyze-token-usage.py` produce, per lo stesso evento .jsonl, lo stesso
   `cost_eur` di `usage_cost_eur()` del core (verifica che non esista calcolo locale residuo)
9. model prevalente: due usage con modelli diversi → `model_prevalent` = quello con più token
10. model prevalente tie-break: parità token → ordine alfabetico deterministico
11. retrocompat: `normalize_stats` su stats senza `by_model`/`model_prevalent` → default safe, no crash

## Criteri di accettazione

- [ ] AC1: 1M token cache_write_1h su sonnet = $6.00 (era $3.75) → €5.46
- [ ] AC2: 1M token cache_write_5m su sonnet = $3.75 (invariato)
- [ ] AC3: tabella input/output/cache_read invariata per i 3 modelli
- [ ] AC4: `DEVFORGE_USD_EUR_RATE=1.0` → cost_eur == cost_usd
- [ ] AC5: dato lo stesso evento .jsonl, `analyze-token-usage.py` (che delega a `usage_cost_eur()`)
      produce esattamente lo stesso `cost_eur` del core; nessuna tabella `PRICING` né
      `calculate_cost()` locale residua nel tool
- [ ] AC6: snapshot legacy non crasha; dedup invariato; campi token-stats.json estesi
      (additivi: `by_model`, `model_prevalent`) senza rompere i consumer esistenti
- [ ] AC7: `session_end` telemetria include `total_tokens` (già presente) + `model_prevalent` (nuovo)
- [ ] AC8: `model_prevalent` = modello con più token; tie-break alfabetico deterministico
- [ ] AC9: test suite verde (14 casi in `tests/test_token_collector.py`)

## Stima SP

| Scala | SP |
|---|---|
| Umano | 5 |
| AI-augmented | 2 |

Nota: SP rivisti al rialzo (era 3/1) per il requisito aggiuntivo "modello prevalente +
token in telemetria" (2026-06-01), che tocca anche `hooks/stop-gate`.
