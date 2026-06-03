# Design — Espansione capacità telemetria: token esatti + "cosa hanno fatto"

**Data:** 2026-06-01
**Autore:** Lorenzo De Tomasi (+ Claude)
**Stato:** APPROVATO (via direttiva autonoma `/goal` 2026-06-01; default raccomandati adottati:
MCP collassato a `mcp__<server>`, scope producer-only, 3 dimensioni; spec-review 2 iter, 0 BLOCK)
**Complessità:** Media
**Branch base:** `fix/token-cost-accuracy` (l'accuratezza pricing è già implementata qui)
**File coinvolti:**
- `lib/token-collector.py` (MODIFICA — tally tool + persistenza by_tool)
- `hooks/stop-gate` (MODIFICA — breakdown token completo in `session_end`)
- `hooks/post-skill` (MODIFICA — token delta per skill in `skill_completed`)
- `tests/test_token_collector.py` (MODIFICA — nuovi casi tool tally)
- `tests/test_telemetry_fixes.sh` (MODIFICA + AGGIUNTA — i test breakdown/delta sono nuovi
  casi ex-novo: il file oggi copre solo canonicalize_user/init_session/next_seq/create_batch,
  nessun test esistente verifica il `meta` di `session_end`/`skill_completed`)

## Contesto

L'obiettivo (`/goal` 2026-06-01) è **misurare esattamente i token usati E cosa ci hanno
fatto gli utenti**, aumentando la capacità di telemetria.

La prima metà — **accuratezza del costo** — è già stata risolta sul branch
`fix/token-cost-accuracy`: pricing cache differenziato 5m (1.25×) / 1h (2×), tasso EUR
via env var, `model_prevalent` + `by_model` in `token-stats.json`, granularità
`canonical_model` opus-4-8/4-7. 17/17 test verdi
(`tests/test_token_collector.py`).

Restano scoperte due dimensioni:

1. **Breakdown token incompleto in telemetria.** `hooks/stop-gate:80,91` emette in
   `session_end` solo `total_tokens`, `output_tokens`, `cost_estimate_eur`,
   `model_prevalent`. I campi `input`, `cache_read`, `cache_write_5m`, `cache_write_1h`
   e il dict `by_model` esistono già in `token-stats.json` (`empty_stats()`
   `lib/token-collector.py:116-129`) ma **non vengono propagati**.

2. **"Cosa hanno fatto" non tracciato.** Nessun dato su quali tool gli utenti hanno
   usato (Bash/Read/Edit/Write/Task/mcp__*) né su quanti token ha consumato ogni skill
   invocata. `hooks/post-skill` traccia `skill_invoked`/`skill_completed` con durata
   (`post-skill:99-106`) ma **senza token**.

PR3 (`session-state-analytics-v2` task 10) pianificava un enrichment parziale di
`session_end`: è stato **assorbito** dal branch corrente per i campi base. Questo design
**completa** quel task e aggiunge le dimensioni tool + token-per-skill.

## Scope

In scope: **solo il producer DevForge** (hook + collector). Il consumer
`siae-telemetry-control-tower` e le aggregazioni S3 restano fuori (vedi
[[feedback_scope_devforge_vs_downstream]]). Tutte le modifiche allo schema eventi sono
**additive** (campi nuovi nel `meta`), retrocompatibili con lo schema_version=2 esistente
(`lib/logger.sh:468`).

## Decisione

### Componente 1 — Uso tool via piggyback sul reader `.jsonl` (Approccio B approvato)

Il `.jsonl` di sessione contiene già i blocchi `tool_use` (con campo `name`) negli eventi
`assistant`. `token-collector.py::update()` (`:451-480`) **itera già** quelle righe per i
token. Nello stesso passaggio si conteggiano i tool, **senza nuovi hook e senza overhead
per-call**.

- Nuova funzione `iter_tool_names(source)`: **riceve il `source` già estratto dal loop di
  `update()`** (NON l'`event` grezzo, NON chiama `iter_usage_sources` internamente — sarebbe
  un secondo loop non sincronizzato col dedup). Legge `source.get("message", {}).get("content")`
  (verificato su 1045 eventi reali: i `tool_use` stanno **sempre e solo** lì; mai in
  `source["content"]` né in `event.data.message.content`); se è una lista, per ogni item con
  `type == "tool_use"` restituisce `canonical_tool(item["name"])`. Per il secondo source
  yieldato da `iter_usage_sources` (`event.data.message`) il path è assente → no-op.
- Normalizzazione cardinalità: i tool MCP (`mcp__<server>__<tool>`) vengono collassati a
  `mcp__<server>` per evitare esplosione di chiavi; i tool built-in (Bash, Read, Edit,
  Write, Task, Glob, Grep, WebFetch, …) restano invariati. Helper `canonical_tool(name)`
  (split su `__`, prende `mcp__<parts[1]>`; edge case: <3 segmenti o server vuoto → nome
  invariato).
- **Dedup (gate esplicita).** Il flag di novità va calcolato PRIMA dell'accumulo delta, e il
  tally condizionato su quel flag — **indipendentemente dal ramo `if`/`elif`** di `update()`
  (`:473-478`). Un `usage_id` nuovo con delta>0 entra nel ramo `if` (`:473`), non nell'`elif`:
  legare il tally al solo `elif` lo perderebbe. Pseudocodice corretto da implementare in
  `update()`:

  ```python
  is_new = usage_id not in usage_index           # calcolato PRIMA
  if add_usage_delta(stats, previous_snapshot, current_snapshot):
      usage_index[usage_id] = current_snapshot
      index_changed = True
  elif is_new:
      usage_index[usage_id] = current_snapshot
      index_changed = True
  if is_new:                                     # tally una sola volta per usage_id
      tally_tools(stats, source)                 # iter_tool_names(source) → by_tool[name]+=1
  ```

  Così un re-read da reset cursore (`file_size < offset` → `offset=0`, `:432-433`) non
  raddoppia i conteggi (l'usage_id è già in index → `is_new` False), e uno streaming update
  dello stesso usage_id (delta>0 ma già visto) non riconteggia. Verificato su 1045 eventi
  reali: ogni `assistant` con `tool_use` ha **sempre** anche `usage` → il gate su usage_id è
  fondato (zero tool_use orfani).
- Persistenza: nuovo campo `by_tool: {}` in `empty_stats()`, gestito da `normalize_stats()`
  con default safe (retrocompat snapshot privi del campo, come già fatto per `by_model`
  `:146-148`).

### Componente 2 — Breakdown token completo in `session_end`

Estendere il blocco python inline di `hooks/stop-gate` (`:73-82`) per leggere da
`token-stats.json` anche `input`, `cache_read`, `cache_write_5m`, `cache_write_1h`, e per
serializzare `by_model` e `by_tool` come JSON compatto (`json.dumps(..., separators=(",",
":"))` — niente tab/newline, quindi sicuro nella riga tab-separated già usata). Bash li
inserisce **verbatim** nel `meta` (sono già JSON valido — verificato: model/tool names reali
non contengono mai tab).

**Ordine campi della riga `print()` tab-separated (contratto esplicito).** L'attuale riga
emette `total \t output \t cost_eur \t model_prevalent`; va estesa preservando i primi 4 e
aggiungendo in coda. Mappatura `print()` ↔ `cut -fN` (qualsiasi disallineamento produce
valori errati silenti, non un crash → contratto vincolante):

| campo `cut -fN` | sorgente token-stats.json | meta key |
|---|---|---|
| f1 | `total` | `total_tokens` (invariato) |
| f2 | `output` | `output_tokens` (invariato) |
| f3 | `cost_eur` | `cost_estimate_eur` (invariato) |
| f4 | `model_prevalent` | `model_prevalent` (invariato) |
| f5 | `input` | `input_tokens` |
| f6 | `cache_read` | `cache_read_tokens` |
| f7 | `cache_write_5m` | `cache_write_5m_tokens` |
| f8 | `cache_write_1h` | `cache_write_1h_tokens` |
| f9 | `json.dumps(by_model)` | `by_model` (JSON object verbatim) |
| f10 | `json.dumps(by_tool)` | `by_tool` (JSON object verbatim) |

`session_end.meta` passa da:
```json
{"skills_used_count":N,"commits_count":N,"total_tokens":N,"output_tokens":N,
 "cost_estimate_eur":N,"model_prevalent":"..."}
```
a (additivo):
```json
{"skills_used_count":N,"commits_count":N,"total_tokens":N,"output_tokens":N,
 "cost_estimate_eur":N,"model_prevalent":"...",
 "input_tokens":N,"cache_read_tokens":N,"cache_write_5m_tokens":N,
 "cache_write_1h_tokens":N,"by_model":{"claude-opus-4-8":N,...},
 "by_tool":{"Bash":N,"Read":N,"Edit":N,"mcp__sport-kg":N,...}}
```

### Componente 3 — Token delta per skill in `skill_completed`

Estendere lo stato di chaining `SKILL_TS_FILE` di `hooks/post-skill` (`:112`) da
`START_NS|SKILL|PHASE` a `START_NS|SKILL|PHASE|TOKEN_TOTAL|TOKEN_OUTPUT` (additivo: i
reader esistenti usano `cut -f1..3`, restano validi; file legacy a 3 campi → campi 4/5
vuoti → trattati come 0).

Flusso:
1. All'invocazione skill, dopo `devforge_log "skill_invoked"`: se
   `DEVFORGE_SESSION_DIR` + `token-stats.json` esistono, esegui
   `python3 lib/token-collector.py update` (refresh) e leggi `total`/`output` correnti →
   `TOKEN_NOW_TOTAL`/`TOKEN_NOW_OUTPUT`. Persisti nella nuova riga di `SKILL_TS_FILE`.
2. Alla chiusura del ciclo precedente (`:90-102`): leggi `PREV_TOKEN_TOTAL`/`PREV_TOKEN_OUTPUT`
   dai campi 4/5; `delta = max(TOKEN_NOW - PREV, 0)` (clamp anti-reset). Aggiungi al `meta`
   di `skill_completed`: `tokens_total_delta`, `tokens_output_delta`.

`skill_completed.meta` passa da:
```json
{"skill_name":"...","sdlc_phase":"...","outcome":"success"}
```
a (additivo): `+ "tokens_total_delta":N, "tokens_output_delta":N`.

Semantica: il delta tra `skill_invoke[i]` e `skill_invoke[i+1]` = token spesi mentre la
skill `i` era il contesto attivo = "quanto è costata questa skill". Costo accettabile: le
skill sono invocate poche volte per sessione (non per-tool-call).

## Flusso dati

```
.jsonl ── update() ──┬─ usage_tokens (token, già) ──┐
                     └─ iter_tool_names (NUOVO) ─────┴─> token-stats.json
                                                          {…, by_model, by_tool}
                                                              │
                          ┌───────────────────────────────────┤
                  stop-gate (Comp.2)                  post-skill (Comp.3)
                  session_end.meta += breakdown        skill_completed.meta += delta
                          │                                   │
                          └──────────► logger.sh (schema v2) ─┴─► outbox ─► S3
```

## Gestione errori / retrocompatibilità

- `by_tool` assente in snapshot storici → `normalize_stats()` default `{}`, nessun crash.
- `iter_tool_names` su evento senza `content`/senza `tool_use` → nessun yield, no-op.
- `token-stats.json` mancante in post-skill → delta omessi (campi a 0), nessun crash, skill
  funziona comunque.
- delta negativo (reset cursore mid-skill) → clamp a 0.
- `SKILL_TS_FILE` legacy a 3 campi → campi token vuoti → 0 (additivo).
- JSON `by_model`/`by_tool` embedded verbatim: prodotti con `json.dumps` compatto (no tab),
  sicuri nella riga tab-separated di stop-gate.
- Eventi storici già loggati restano invariati (additività, non regressione).

## Testing

`tests/test_token_collector.py` (estensione, import core via `importlib`):
1. `iter_tool_names` estrae i nomi dai blocchi `tool_use` di un evento assistant.
2. `canonical_tool("mcp__sport-kg__who_calls")` == `"mcp__sport-kg"`; built-in invariati.
3. `update()` su `.jsonl` fixture con 3 tool_use → `by_tool` corretto.
4. dedup tool: stesso `usage_id` letto due volte (reset cursore) → conteggi NON raddoppiati.
5. evento senza `tool_use` → `by_tool` invariato; nessun crash.
6. `normalize_stats` su stats senza `by_tool` → default `{}` safe.
7. no-regression: i 17 test pricing/model esistenti restano verdi.

`tests/test_telemetry_fixes.sh` (estensione bash):
8. `session_end` include `input_tokens`/`cache_read_tokens`/`cache_write_5m_tokens`/
   `cache_write_1h_tokens`/`by_model`/`by_tool` con JSON valido.
9. `skill_completed` include `tokens_total_delta`/`tokens_output_delta` (delta ≥ 0).
10. `SKILL_TS_FILE` legacy a 3 campi non rompe la chiusura ciclo (delta=0, no crash).

## Criteri di accettazione

- [ ] AC1: dato un `.jsonl` con N eventi `assistant` distinti, ciascuno con un blocco
      `tool_use`, `token-stats.json.by_tool` conta **ogni occorrenza** (frequenza per tool;
      più `tool_use` nello stesso turn sommano, anche se sui dati reali non si osserva >1/turn).
- [ ] AC2: tool MCP collassati a `mcp__<server>`; tool built-in invariati.
- [ ] AC3: re-read da reset cursore NON raddoppia `by_tool` (dedup via usage_id).
- [ ] AC4: `session_end.meta` include `input_tokens`, `cache_read_tokens`,
      `cache_write_5m_tokens`, `cache_write_1h_tokens`, `by_model` (dict), `by_tool` (dict)
      — tutti JSON validi, campi esistenti invariati.
- [ ] AC5: `skill_completed.meta` include `tokens_total_delta` e `tokens_output_delta`,
      pari ai token spesi tra l'invoke della skill e quello della successiva, clamp ≥ 0.
- [ ] AC6: tutte le modifiche additive — schema_version resta 2, consumer ignora campi
      nuovi; snapshot/file di stato legacy non crashano.
- [ ] AC7: i 17 test esistenti restano verdi; nuovi test (≥10 casi) verdi.

## Stima SP

| Scala | SP |
|---|---|
| Umano | 5 |
| AI-augmented | 2 |

3 componenti, 3 file core + 2 test. Componente 1 (tool tally) è il cuore; 2 e 3 sono
propagazioni a basso rischio di dati già calcolati.
