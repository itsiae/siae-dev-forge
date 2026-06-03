# Design — Segnali raw su S3 per "chi produce di valore" + "dove finiscono i token" + pricing multi-vendor

**Data:** 2026-06-02 (pricing folded-in 2026-06-03)
**Autore:** Lorenzo De Tomasi (+ Claude)
**Stato:** APPROVATO (design) — IN CODA all'implementazione dietro il merge di PR #296
**Complessità:** Media-Alta
**Branch base:** PR #296 mergiata in `main` (dipende da `session_fields_line`/`by_model` di #296)
**⚠️ Vincolo di sequenza (I2):** NON implementare Comp.4/5 né il contratto f11-f13 prima che #296
sia visibile in `main` — il contratto f1..f10 è instabile finché #296 non è mergiata.
**Vincoli (durevoli):** SOLO dati raw ([[feedback_telemetry_raw_only_additive]]), NON cambiare il
pregresso (additivo, `schema_version` 2, eventi/campi esistenti immutati),
attribuzione token NON gonfiata ([[feedback_token_attribution_no_inflation]]).

**File coinvolti:**
- `lib/token-collector.py` (MODIFICA — by_skill, by_model_tokens, pricing snapshot; firma
  `add_usage_delta(..., skill=None)`)
- `hooks/stop-gate` (MODIFICA — nuovi campi nel contratto `fields` → `session_end`)
- `hooks/capture-test-result` (MODIFICA — emette `test_run_result` + `tdd_cycle`)
- `hooks/post-commit-review` (MODIFICA — `session_tokens_cumulative` su `pr_merged`)
- `lib/logger.sh` (MODIFICA — helper `devforge_session_token_total`)
- `hooks/tdd-gate`, `hooks/brainstorming-gate` (MODIFICA — `tokens_at_block`)
- `tests/*` (MODIFICA+AGGIUNTA)

## Componenti

### Comp.1 — `by_skill` token via `attributionSkill` nativo (anti-inflazione)
`update()` legge `attributionSkill` (top-level evento, una volta PER EVENTO, prima del loop
source). Firma estesa `add_usage_delta(stats, previous, current, skill=None)`: accumula in
`stats["by_skill"][skill]` le componenti `{output, input, cache_write_5m, cache_write_1h}`
ESCLUDENDO `cache_read` (contesto riletto → gonfia). Dedup ereditato da `usage_index`
(delta_total>0). `empty_stats`/`normalize_stats` default `{}`.

### Comp.2 — Eventi raw test/TDD da `capture-test-result`
`source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || true` + `devforge_init_session ... || true`
+ guard `command -v devforge_log`. Emette `test_run_result {status, exit_code, coverage_pct,
framework}` e `tdd_cycle {from_phase, to_phase, elapsed_sec, reason}` (epoch = fase CORRENTE,
elapsed ≥ 0). Falliscono soft, mai interrompono il test run.

### Comp.3 — Ancore token raw
3a: `session_tokens_cumulative` su `pr_merged` (2 punti) via helper
`devforge_session_token_total()`. 3b: `tokens_at_block` su `tdd_gate`/`brainstorming_gate`
blocked (stesso helper).

### Comp.4 — `by_model_tokens`: componenti token per modello (RAW per pricing multi-vendor)
Oggi `by_model` (PR #296) = `{model: total}` → insufficiente per applicare listini diversi
(ogni componente ha tariffa diversa). Aggiungere campo NUOVO `by_model_tokens` =
`{model: {input, output, cache_read, cache_write_5m, cache_write_1h}}` (additivo; `by_model`
total resta invariato). Accumulo dentro `add_usage_delta` usando `extract_model(source)`, stesso
dedup (guard `delta_total > 0`; NB: `delta_total` include `cache_read`, coerente con
`by_model_tokens` che lo include — documentare nel codice, I5). NB: qui `cache_read` È incluso
(serve a valle per applicare la sua tariffa 0.1x); non è attribuzione "lavoro" ma dato grezzo per
il ricalcolo costo. **`empty_stats` E `normalize_stats` DEVONO includere `by_model_tokens` (e
`by_skill`) con default `{}`** — altrimenti un ciclo `write_stats`+`read_stats` tra due `update`
li azzera silenziosamente (I3, vedi AC13).

### Comp.5 — `pricing`: rate-table applicato + eur_rate (trasparenza + ricalcolo)
Nuova funzione `pricing_snapshot(models: set[str]) -> dict` (deliverable, non esiste ancora): per
ogni modello usato nella sessione (chiavi di `by_model`), restituisce `pricing_for_model(model)`
(le 5 tariffe USD/1M) + `eur_rate` = `resolve_eur_rate()`. `unit` = nuova costante
`PRICING_UNIT = "usd_per_1m_tokens"` nel modulo (I4, contratto stabile per il consumer). Emesso in
`session_end.meta` come `pricing`:
```json
"pricing": {
  "unit": "usd_per_1m_tokens",
  "eur_rate": 0.91,
  "by_model": {"claude-opus-4-8": {"input":5.0,"output":25.0,"cache_read":0.5,"cache_write_5m":6.25,"cache_write_1h":10.0}, ...}
}
```
Raw: sono le tariffe applicate, non un costo composto. Insieme a `by_model_tokens` permette al
consumer di ricalcolare il costo con QUALSIASI listino (Bedrock, Anthropic diretto, altri vendor):
`cost_vendor = Σ_model Σ_componente by_model_tokens[model][comp] × vendor_rate[model][comp] / 1e6`.
`cost_eur` esistente resta (non cambia il pregresso).

## Contratto `session_fields_line` (esteso da #296)
#296 termina a f10 (by_tool). Aggiungere IN CODA: f11=`json(by_skill)`, f12=`json(by_model_tokens)`,
f13=`json(pricing)`. `cut -f1..f10` di stop-gate invariati. Aggiornare docstring a f1..f13.

## Gestione errori / retrocompatibilità
- Campi nuovi assenti in snapshot storici → `normalize_stats` default `{}`/omesso, no crash.
- JSON embedded compatto (`json.dumps separators=(",",":")`), no tab/newline → safe verbatim.
- Tutto additivo: `schema_version` 2; consumer ignora campi ignoti; nessun backfill.

## Criteri di accettazione
- [ ] AC1: `by_skill` accumula `{output,input,cache_write_5m,cache_write_1h}` per skill da `attributionSkill`.
- [ ] AC2: evento senza `attributionSkill` → bucket `""`.
- [ ] AC3: `session_end.meta` include `by_skill`; f1..f10 e campi esistenti invariati.
- [ ] AC4: `capture-test-result` emette `test_run_result`, mai interrompe il test run (source `|| true`).
- [ ] AC5: `tdd_cycle` con `elapsed_sec` ≥ 0 (epoch fase corrente).
- [ ] AC6: `pr_merged` include `session_tokens_cumulative`; `tdd_gate`/`brainstorming_gate` blocked includono `tokens_at_block`.
- [ ] AC7: additivo, `schema_version` 2, legacy non crasha.
- [ ] AC8: suite verde (esistenti invariati + nuovi).
- [ ] AC9: dedup `by_skill` via `usage_index` (re-read non raddoppia).
- [ ] AC10 (anti-inflazione): `by_skill` NON include `cache_read`.
- [ ] AC11 (pricing): `by_model_tokens` = componenti `{input,output,cache_read,cache_write_5m,cache_write_1h}` per modello (additivo; `by_model` total invariato).
- [ ] AC12 (pricing): `session_end.meta.pricing` = `{unit:"usd_per_1m_tokens", eur_rate, by_model:{model:rates}}` per i modelli usati; `cost_eur` esistente invariato. Dato `by_model_tokens` + `pricing`, il consumer ricalcola il costo per qualsiasi vendor.
- [ ] AC13 (persistenza, I3-BLOCK): `empty_stats` e `normalize_stats` includono `by_skill` e `by_model_tokens` con default `{}`; un ciclo `write_stats` + `read_stats` NON perde i valori accumulati (test persist-reload dedicato, non solo unit in-memory).

## Out of scope
- `by_agent` (token subagent assenti dal .jsonl) → backlog d'indagine.
- Derivazioni a valle: by_phase, produttivo/overhead, token→outcome, costo per-vendor, "chi produce meglio".
- Listini dei vendor alternativi (vivono nel consumer; il producer emette solo le tariffe Anthropic applicate + i token raw).

## Stima SP
| Scala | SP |
|---|---|
| Umano | 8 (era 8; +pricing assorbito) |
| AI-augmented | 3 |
