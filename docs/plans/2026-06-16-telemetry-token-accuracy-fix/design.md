# Design — Accuratezza telemetria token/costi DevForge

**Data:** 2026-06-16
**Branch proposto:** `fix/telemetry-token-accuracy`
**Stato:** DESIGN (pre-impl)
**Origine:** analisi a valle su 96.261 eventi / 88 dev — 5 finding su token e costi gonfiati/mancanti.

---

## 1. Contesto

Un'analisi sui dati di telemetria già atterrati (96.261 eventi, 88 dev) ha rilevato 5 anomalie su token e costi. I nomi-campo dell'analisi erano abbreviati; mappati ai nomi reali del codice:

| Analisi | Campo reale | Evento | Emesso da |
|---|---|---|---|
| `by_model_json` | `by_model` / `by_model_tokens` | `session_end` | `hooks/stop-gate` + `lib/token-collector.py` |
| `tokens_delta` | `output_tokens_delta` / `total_tokens_delta` | `commit_created` | `hooks/post-commit-review` |
| `session_tokens_cum` | `session_tokens_cumulative` | `commit_created` / `pr_merged` | `hooks/post-commit-review` |
| `cost_eur_accurate` | `cost_estimate_eur` / `cost_delta_eur` | `session_end` / `commit_created` | idem |

**I 5 finding collassano su 3 cause reali.**

---

## 2. Root-cause analysis (verificata sul codice)

### Causa A — Scoping di sessione inaffidabile 🔴 (copre #1, #3, #5)

Tre difetti che si combinano:

1. **Stato globale per-progetto come fallback.** `lib/token-collector.py:82-100` (`cursor_file`/`stats_file`/`usage_index_file`): se `DEVFORGE_SESSION_DIR` non è settato/esistente, lo stato NON è per-sessione ma globale per-directory:
   ```python
   def stats_file() -> Path:
       sd = session_dir()  # DEVFORGE_SESSION_DIR
       if sd:
           return Path(os.path.join(sd, "token-stats.json"))
       return STATE_DIR / f".devforge-token-stats-{project_hash()}"   # GLOBALE, persiste tra sessioni
   ```
   Questo stato sopravvive tra sessioni della stessa cwd.

2. **No-reset di `by_model` sul cambio file.** `update()` (`token-collector.py:520-533`): a `file_size == offset` con `total>0` ritorna early tenendo le stats; quando rileva un `.jsonl` più recente (riga 525-529) resetta `offset=0` ma **non azzera `stats["by_model"]`/`by_model_tokens"`** → continua ad accumulare sul dict precedente.

3. **Guardia a `stop-gate`.** L'emissione dei token in `hooks/stop-gate` è dietro `[ -n "$DEVFORGE_SESSION_DIR" ] && [ -f token-stats.json ]`. Se non valgono, `session_end` emette token a **zero** e niente `by_model` (root di #5: copertura 904/96.261).

4. **Ordering export in `session-start` (trigger #1 verificato in review).** `hooks/session-start` assegna `DEVFORGE_SESSION_DIR` a **riga 28** ma lo **esporta solo a riga 80**, mentre chiama `python3 token-collector.py init` a **riga 77**. Il sottoprocesso python eredita solo le variabili `export`-ate → al momento di `init()` l'env var NON è esportata → `session_dir()` ritorna `None` → **`init()` scrive nel path GLOBALE, non per-sessione**. Questo spiega perché la copertura per-sessione è così bassa (904/96.261): nelle sessioni `startup` lo stato finisce sistematicamente nel file globale, dove poi si congela. È la causa-radice meccanica del difetto #1+#5, non un semplice rischio.

**Effetto osservato e spiegato:** quando lo stato è globale e un `.jsonl` raggiunge EOF, il blocco di un modello (Opus) si **congela byte-identico** (`cache_read:703803830` ecc.) e viene **ri-emesso su decine di `session_end`** (carry-forward dello stato globale + early-return), mentre i modelli aggiunti dai `.jsonl` più recenti (Sonnet) **crescono** (offset resettato a 0 sul nuovo file, accumulo sullo stesso dict). Costo gonfiato ~5×.

**`cost=0` (#3)** è la stessa causa: senza `DEVFORGE_SESSION_DIR`/`token-stats.json`, `cost_estimate_eur` esce a 0. Non esiste alcun campo `cost_eur_accurate` non popolato: il campo è `cost_estimate_eur` e a volte è 0 perché lo stato non è stato letto.

### Causa B — Semantica delta al primo commit 🟡 (copre #2)

`hooks/post-commit-review:79-88`:
```python
do=curr.get('output',0)-prev.get('output',0)
dt=curr.get('total',0)-prev.get('total',0)
cum=curr.get('total',0)
```
`prev` viene da `token-at-last-commit.json`. Al **primo commit di sessione** il file non esiste → `prev={}` → `dt = curr.total - 0 == cum`. Le sessioni con un solo commit (maggioranza) mostrano `total_tokens_delta == session_tokens_cumulative`. Il delta è genuino dal secondo commit in poi.

### Causa C — Scomposizione per-tipo 🟢 (copre #4, in gran parte già fatto)

`session_end` emette **già** i 5 componenti come campi first-class (`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_5m_tokens`, `cache_write_1h_tokens`) e `by_model_tokens` con tutti e 5 i componenti per modello (Comp.4, PR #296). Il gap dell'analisi è la copertura parziale di `by_model` — che è la Causa A, non una mancanza di scomposizione. Resta solo da garantire che i campi per-tipo siano emessi anche quando per-modello manca, e che il consumer li usi.

---

## 3. Decisioni (brainstorming 2026-06-16)

- **Causa A → Fail-closed + reset su switch.** Lo stato è SEMPRE per-sessione; il path si auto-deriva dal `sid` quando l'env var manca; mai fallback globale silenzioso. `by_model`/`by_model_tokens` azzerati quando `update()` cambia `.jsonl`. Quando lo stato non è ricostruibile, `session_end` emette un flag esplicito di incompletezza invece di zeri o di un blocco congelato.
- **Causa B → Fix producer (delta reale).** Al primo commit il baseline è lo snapshot di init (token a inizio sessione = 0), non `{}` ambiguo, così `total_tokens_delta` è il vero incremento. `session_tokens_cumulative` resta separato e non ambiguo. Coerente con il principio "telemetria raw-only additive": un delta corretto è dato raw, non uno score composito.
- **Causa C → Verifica + cintura.** Confermare che i 5 campi per-tipo siano sempre presenti in `session_end`; nessuna nuova feature.

---

## 4. Design per causa

### 4.A — Scoping fail-closed

**A1. Auto-derivazione del session dir nel token-collector.**
Nuova funzione `resolve_session_dir()` in `token-collector.py`:
1. se `DEVFORGE_SESSION_DIR` è settato ed esiste → usalo;
2. altrimenti leggi `sid` da `${HOME}/.claude/.devforge-session-id` (`DEVFORGE_SID_FILE`) e componi `${HOME}/.claude/devforge-state/${sid}`; se la dir esiste → usala;
3. altrimenti → `None` (stato non risolvibile).
`cursor_file`/`stats_file`/`usage_index_file` usano `resolve_session_dir()`. **Rimosso il fallback globale `STATE_DIR/.devforge-token-*-{project_hash()}`.**

**A1-bis. Fix ordering export in `session-start` (defense-in-depth).**
Spostare `export DEVFORGE_SESSION_DIR ...` PRIMA della chiamata a `init()` (riga 77), oppure passare il path come argomento esplicito a `token-collector.py init <dir>`. Con A1 il token-collector si auto-deriva il path dal sid-file (scritto a riga 25, prima di `init()`), quindi A1 da solo è già corretto; A1-bis è la cintura: garantisce il path per-sessione anche se il sid-file non fosse leggibile. Senza A1-bis, il `2>/dev/null || true` che avvolge `init()` maschererebbe un fallimento del sid-file facendo ricadere lo stato nel (rimosso) globale → con A2 diventerebbe no-op silenzioso, perdendo i token di sessione.

**A2. Fail-closed quando il dir non è risolvibile.**
Se `resolve_session_dir()` è `None`:
- `init`/`update` non scrivono stato globale; `update` è no-op.
- `fields` emette un marker di incompletezza (vedi A4).

**A3. Reset di `by_model` sul cambio `.jsonl`.**
In `update()`, quando si passa a un file diverso (rami `file_size < offset` con path cambiato, e `newer != jsonl_path` a riga 525-529), azzerare `by_model`, `by_model_tokens`, `by_tool`, `by_skill` e i contatori per-tipo nello `stats` prima di riprocessare. Lo stato per-sessione deve riflettere solo il `.jsonl` corrente della sessione. *(Nota: con A1 lo stato è già per-sessione, ma il reset chiude il caso di rotazione `.jsonl` intra-sessione.)*

**A4. Flag di completezza su `session_end`.**
Nuovo campo `token_state_complete` (bool) nell'evento `session_end`:
- `true` quando lo stato è stato letto da un dir di sessione risolto e `total > 0`;
- `false` quando il dir non è risolvibile o `token-stats.json` manca.
`hooks/stop-gate`: invece di saltare silenziosamente l'emissione token quando la guardia fallisce, emette `session_end` con i token a 0 **e** `token_state_complete:false`, così il consumer scarta il blocco invece di contarlo. Mai più zeri "indistinguibili" da valori reali.

### 4.B — Delta reale al primo commit

`hooks/post-commit-review`: quando `token-at-last-commit.json` non esiste, usare come `prev` un baseline a zero esplicito (`{"output":0,"total":0,"cost_eur":0}`) — già il comportamento di `.get(...,0)`, ma il punto è che **a inizio sessione `init()` azzera lo stato**, quindi `curr - 0` al primo commit È il vero incremento di sessione. Nessun cambiamento di formula necessario una volta che A1/A2 garantiscono che `curr` parta da uno stato resettato per-sessione. **Verifica esplicita** che `init()` sia sempre chiamato a session-start (lo è: `hooks/session-start:77`) e che `token-stats.json` sia per-sessione (garantito da A1). `session_tokens_cumulative` resta `curr.total` e non è ambiguo perché distinto da `total_tokens_delta`. Documentare la semantica dei due campi nel contratto eventi.

### 4.C — Verifica scomposizione

Test che asseriscono la presenza dei 5 campi per-tipo in `session_end` anche con `by_model` vuoto. Nessuna modifica di codice prevista; se un test fallisce, fix mirato.

---

## 5. Task breakdown (TDD)

| # | Task | File | Tipo |
|---|---|---|---|
| 01 | `resolve_session_dir()` con auto-derivazione da `DEVFORGE_SID_FILE` + rimozione fallback globale | `lib/token-collector.py` | TDD |
| 01b | Fix ordering: `export DEVFORGE_SESSION_DIR` prima della chiamata `init()` (riga 77) | `hooks/session-start` | TDD |
| 02 | Fail-closed: `update`/`init` no-op quando dir non risolvibile | `lib/token-collector.py` | TDD |
| 03 | Reset `by_model`/`by_model_tokens`/`by_tool`/`by_skill` sul cambio `.jsonl` in `update()` | `lib/token-collector.py` | TDD |
| 04 | Campo `token_state_complete` in `fields`/`session_fields_line` | `lib/token-collector.py` | TDD |
| 05 | `stop-gate`: emette `session_end` con `token_state_complete:false` invece di skip silenzioso | `hooks/stop-gate` | TDD |
| 06 | Verifica delta primo-commit reale (test end-to-end init→commit→commit) | `hooks/post-commit-review` + test | TDD |
| 07 | Test presenza 5 campi per-tipo con `by_model` vuoto | test | TDD |
| 08 | Doc contratto eventi: semantica `total_tokens_delta` vs `session_tokens_cumulative` + `token_state_complete` | `docs/handover/` | DOC |
| 09 | Migrazione/cleanup file stato globale legacy `.devforge-token-*-{hash}` residui | `lib/token-collector.py` (one-shot) | TDD |

---

## 6. Acceptance Criteria

- **AC1:** Con `DEVFORGE_SESSION_DIR` non settato ma `.devforge-session-id` presente, `token-collector.py` scrive/legge lo stato in `${HOME}/.claude/devforge-state/${sid}`, MAI in un file globale per-progetto.
- **AC2:** Con nessun session dir risolvibile, `update` è no-op e `fields` ritorna `token_state_complete=false` con token a 0; nessuno stato globale creato.
- **AC3:** Due sessioni distinte sulla stessa cwd producono `by_model` indipendenti; nessun blocco byte-identico ri-emesso (test che simula 2 `.jsonl` con offset/EOF).
- **AC4:** Su rotazione `.jsonl` intra-sessione, `by_model` riflette solo il file corrente (no carry-forward).
- **AC5:** `session_end` contiene sempre `token_state_complete` (bool) e i 5 campi per-tipo.
- **AC6:** In una sessione con 2 commit, `total_tokens_delta` del 2° commit < `session_tokens_cumulative` (delta ≠ cumulativo); al 1° commit `total_tokens_delta == session_tokens_cumulative` è documentato come corretto (intera sessione fin lì).
- **AC7:** Nessuna regressione sulla suite token-collector esistente (delta vs baseline committato).
- **AC8 (E2E session-start):** Simulando la sequenza reale `devforge_new_sid()` → `token-collector.py init`, lo stato è scritto in `${HOME}/.claude/devforge-state/${sid}/token-stats.json` e MAI in `${HOME}/.claude/.devforge-token-stats-{hash}`. Copre il bug di ordering export.
- **AC9 (consumer lettura diretta):** Il calcolo delta in `hooks/post-commit-review` (lettura diretta di `token-stats.json`, righe 79-88) usa lo stato per-sessione corretto, non un blocco congelato globale.

---

## 7. Edge cases da coprire (pre-impl hunt)

- `.devforge-session-id` esiste ma la dir `devforge-state/${sid}` no (sessione vecchia/pulita) → fail-closed, non creare.
- `DEVFORGE_SESSION_DIR` settato a dir inesistente → cade su derivazione da sid, non su globale.
- File stato globale legacy già presente da run precedenti → task 09 cleanup; non leggerlo più.
- `.jsonl` ruotato a EOF + nessun file più recente → return senza congelare (no ri-emissione).
- `sid` corrotto/vuoto nel file → trattare come non risolvibile.
- Concorrenza: due hook (`stop-gate` + `post-commit-review`) scrivono lo stesso `token-stats.json` → `write_atomic` già usa `os.replace`; verificare nessuna race su `by_model` reset.
- CRLF / `python3`-only su Windows (vedi memoria identità cross-platform) → la lettura di `DEVFORGE_SID_FILE` deve gestire newline trailing (`.strip()`).
- **Rollout incrementale (mixed-version):** durante il rollout, sessioni con `session-start` pre-fix scrivono ancora nel globale mentre quelle post-fix usano il per-sessione. Il task 09 rimuove i file globali legacy ma deve farlo in modo idempotente e non distruttivo per sessioni in corso; documentare che `token_state_complete=false` durante la finestra è atteso e non un nuovo bug.
- `resume`/`clear`/`compact` con sid-file cancellato manualmente: `devforge_get_sid()` bash genera un nuovo sid, ma `resolve_session_dir()` python vede il file vuoto → discrepanza bash/python sulla sessione. Documentare; fail-closed lato python è il comportamento corretto.

---

## 8. Non-goals

- Non si introducono score compositi né backfill (principio raw-only additive).
- Non si ridisegna il consumer a valle (Control Tower); si documenta la semantica.
- Non si tocca il pricing per-modello (già corretto, PR #295/#296).
