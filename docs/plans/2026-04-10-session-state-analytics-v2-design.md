# Design: Session State Isolation + Analytics V2 — PR2+PR3

**Data:** 2026-04-10
**Autore:** Lorenzo De Tomasi + DevForge AI
**Stato:** In review
**SP:** 8 SP-Umano / 5 SP-Augmented (PR2: 3, PR3: 5)
**Approccio scelto:** A — Refactor incrementale

---

## Contesto

Dopo PR1 (telemetry-hardening), restano 3 problemi strutturali:

1. **State globale condiviso** — tutti i file in `~/.claude/.devforge-*` sono globali.
   Sessioni concorrenti si pestano i piedi (user, sid, skill-start, counters).
2. **Upload best-effort** — `telemetry-upload.sh` fa un singolo POST in background
   da `post-commit-review`. Sessioni senza commit non uploadano nulla. Nessun retry/ack.
3. **Schema instabile** — nessun `event_id` per dedup server-side, nessun `schema_version`,
   identità utente inconsistente, token counter naive (no dedupe, pricing Opus hardcoded).

Questi problemi rendono impossibile: contare utenti unici, attribuire sessioni correttamente,
garantire che i dati arrivino su S3, calcolare costi token reali.

---

## Fase 1 — PR2: Session State Isolation

### 1.1 State directory per sessione

**Oggi:**
```
~/.claude/.devforge-session-commits
~/.claude/.devforge-session-skills
~/.claude/.devforge-session-start-ns
~/.claude/.devforge-skill-start
~/.claude/.devforge-user
~/.claude/.devforge-session-id
```

**Dopo:**
```
~/.claude/devforge-state/
  <sid>/
    activity.jsonl       # eventi di QUESTA sessione
    outbox/              # batch da uploadare
      batch-<ts>.jsonl   # batch pendente
      acked/             # batch uploadati con successo
    user.json            # identity pinnata
    counters.json        # commits, skills, messages, tokens
    skill-start          # timestamp chaining
    token-cursor         # token-collector cursor
```

**`session-start`** crea `~/.claude/devforge-state/<sid>/` e inizializza tutti i file.
**`stop-gate`** fa flush finale e upload.

### 1.2 Identity pinning

**Oggi:** `devforge_get_user()` (lib/logger.sh:61) ricalcola l'utente ad ogni evento.

**Dopo:** risolto UNA volta in `session-start`, salvato in `<sid>/user.json`:

```json
{
  "raw": "lorenzo.detomasi@siae.it",
  "source": "git-config-local",
  "canonical": "lorenzo.detomasi@siae.it"
}
```

`devforge_log` legge `user.json` dalla dir di sessione. Non ricalcola mai.

Il campo `source` traccia la provenienza:
- `git-config-local` — `git config user.email` (repo)
- `git-config-global` — `git config --global user.email`
- `session-cache` — file cache da sessione precedente
- `os-user` — `$USER` o `whoami`

### 1.3 Logger refactored

`lib/logger.sh` cambia:

- `devforge_log` scrive in `<sid>/activity.jsonl` (non più nel globale direttamente)
- Il sid è pinnato a init in una variabile bash (`DEVFORGE_CURRENT_SID`), non letto da file ogni volta
- L'utente è letto da `<sid>/user.json`, non ricalcolato
- **Backward compat:** dopo la scrittura in `<sid>/activity.jsonl`, appende ANCHE al file globale
  `~/.claude/devforge-activity.jsonl` per non rompere `forge-insights` e script esistenti

### 1.4 Upload in più punti

**Punti di upload (tutti con `devforge_upload_logs`):**

| Punto | Quando | Cosa uploada |
|-------|--------|-------------|
| `session-start` | Inizio sessione | Backlog di sessioni precedenti (outbox non acked) |
| `post-commit-review` | Dopo commit_created | Batch corrente (incluso commit_created appena scritto) |
| `stop-gate` | Fine sessione | Flush finale (incluso session_end) |

L'upload è sempre **post-evento**: prima scrivi l'evento in `activity.jsonl`, poi copia in `outbox/batch-<ts>.jsonl`, poi uploada.

### 1.5 Cleanup sessioni vecchie

In `session-start`, dopo init della nuova sessione:

```bash
# Cleanup session state directories older than 48h (preserve pending outbox)
if [ -d "${HOME}/.claude/devforge-state" ]; then
    for session_dir in "${HOME}/.claude/devforge-state"/*/; do
        [ -d "$session_dir" ] || continue
        DIR_MTIME=$(stat -f%m "$session_dir" 2>/dev/null || stat -c%Y "$session_dir" 2>/dev/null || echo "0")
        DIR_AGE=$(( $(date +%s) - DIR_MTIME ))
        [ "$DIR_AGE" -lt 172800 ] && continue  # skip if < 48h
        # Check for pending (non-acked) batches before deleting
        PENDING_COUNT=$(find "$session_dir/outbox" -maxdepth 1 -name '*.jsonl' 2>/dev/null | grep -cv '/acked/' || echo "0")
        if [ "$PENDING_COUNT" -gt 0 ]; then
            continue  # preserve dir with pending uploads
        fi
        rm -rf "$session_dir"
    done
fi
```

Le directory con batch non-acked vengono preservate. Solo directory > 48h senza outbox pendente vengono rimosse.

### 1.6 File da modificare (PR2)

| File | Modifica |
|------|----------|
| `lib/logger.sh` | State per-sessione, identity pinning, dual write (sessione + globale) |
| `hooks/session-start` | Crea dir sessione, init user.json, cleanup vecchie sessioni, upload backlog |
| `hooks/stop-gate` | Flush finale in outbox, upload |
| `hooks/post-commit-review` | Upload post-evento (post commit_created) |
| `hooks/devforge-context-always` | Legge counters da dir sessione invece che da file globali |
| `statusline/devforge-statusline.sh` | Legge state da dir sessione, mostra telemetry status |
| `lib/telemetry-upload.sh` | Outbox-based: uploada batch da outbox/, sposta in acked/ |

---

## Fase 2 — PR3: Analytics V2

### 2.1 Schema versionato

Ogni evento ha campi fissi obbligatori:

```json
{
  "event_id": "a1b2c3d4-7",
  "schema_version": 2,
  "sid": "a1b2c3d4",
  "session_seq": 7,
  "hook_name": "post-commit-review",
  "actor_canonical": "lorenzo.detomasi@siae.it",
  "actor_raw": "lorenzo.detomasi@siae.it",
  "repo_root": "/Users/detomasi/.../siae-dev-forge",
  "project_canonical": "siae-dev-forge",
  "branch": "feat/telemetry-hardening",
  "ts": "2026-04-10T18:00:00.000Z",
  "event": "commit_created",
  "status": "success",
  "meta": {}
}
```

**`event_id`** = `{sid}-{session_seq}`. Globalmente unico. Usato per dedup server-side.

**`session_seq`** = contatore atomico in file intero dedicato `<sid>/seq` (non in counters.json).
Meccanismo di atomicità: file con un solo intero, incrementato con `flock` per prevenire
race condition tra hook concorrenti:

```bash
devforge_next_seq() {
    local seq_file="${DEVFORGE_SESSION_DIR}/seq"
    (
        flock -n 9 || return 1
        local current=$(cat "$seq_file" 2>/dev/null || echo "0")
        local next=$((current + 1))
        echo "$next" > "$seq_file"
        echo "$next"
    ) 9>"${seq_file}.lock"
}
```

Se `flock` non è disponibile (raro su macOS/Linux), fallback a read-increment-write
senza lock (rischio duplicati trascurabile per uso single-thread tipico degli hook).

**`project_canonical`** = `basename(repo_root)` — normalizzato, non il path completo.

**`hook_name`** = il nome dell'hook che ha generato l'evento (session-start, post-skill, etc.).

**Backward compat:** `schema_version: 1` = formato vecchio. Lambda accetta entrambi.
Query Athena filtrano per `schema_version >= 2` per le nuove metriche.

### 2.2 Upload affidabile (outbox + retry + ack)

**Outbox model:**

1. `devforge_log` scrive in `<sid>/activity.jsonl`
2. Ai punti di upload, le righe nuove vengono copiate in `<sid>/outbox/batch-<ts>.jsonl`
3. `devforge_upload_logs` itera su `outbox/*.jsonl`:
   - POST al server
   - Se 200: `mv batch.jsonl outbox/acked/`
   - Se errore: il batch resta in `outbox/` per il prossimo tentativo
4. Al prossimo punto di upload, i batch pendenti vengono ritentati

**Idempotenza server-side:** Lambda scrive su S3 con key che include `event_id`.
Se lo stesso batch viene uploadato due volte, il secondo upload sovrascrive con gli stessi dati.

**Visibilità:** la statusline mostra:
- `telemetry=ok` — nessun batch pendente
- `telemetry=pending:3` — 3 batch in attesa di upload
- `telemetry=offline` — ultimo tentativo fallito

### 2.3 Token/cost con dedupe multi-model

Il token-collector (`lib/token-collector.py`) viene riscritto con:

1. **Dedupe** via `usage_identity()` — `message.id` → `requestId` → `uuid`
   (pattern già validato in `tests/analyze-token-usage.py:156`)
2. **Multi-model pricing:**

```python
# Prices per 1M tokens (USD). Source: anthropic.com/pricing as of 2026-04.
# Update when new models are released or prices change.
PRICING = {
    "claude-opus-4-6":    {"input": 5.0,   "output": 25.0,  "cache_read": 0.50,  "cache_write": 6.25},
    "claude-sonnet-4-6":  {"input": 3.0,   "output": 15.0,  "cache_read": 0.30,  "cache_write": 3.75},
    "claude-haiku-4-5":   {"input": 1.0,   "output": 5.0,   "cache_read": 0.10,  "cache_write": 1.25},
    "default":            {"input": 3.0,   "output": 15.0,  "cache_read": 0.30,  "cache_write": 3.75},
}
USD_TO_EUR = 0.91
```

3. **Model detection:** legge `message.model` o `model` dal JSONL. Se assente, usa `default`.
4. **Stats arricchite:** `counters.json` include breakdown per modello.
5. **Integrazione:** stop-gate arricchisce `session_end` con token totali + costo EUR.

### 2.4 File da modificare (PR3)

| File | Modifica |
|------|----------|
| `lib/logger.sh` | Aggiunge event_id, schema_version, session_seq, hook_name, actor/project canonical |
| `lib/token-collector.py` | Riscrittura: dedupe, multi-model pricing, state in dir sessione |
| `lib/telemetry-upload.sh` | Idempotenza (event_id nel payload) |
| `infra/telemetry/lambda/handler.py` | Dedup su event_id, accetta schema v1 e v2 |
| `hooks/stop-gate` | Arricchisce session_end con token stats |
| `hooks/post-commit-review` | Arricchisce commit_created con token delta |
| `statusline/devforge-statusline.sh` | Mostra token + costo + telemetry status |
| `hooks/devforge-context-always` | Mostra token nel context |

---

## Gestione errori e edge case

| Edge case | Gestione |
|-----------|----------|
| python3 non disponibile | Token tracking disabilitato. Tutti gli altri eventi funzionano. |
| Sessione senza commit | Upload in stop-gate cattura session_end. |
| Crash sessione (no stop-gate) | Backlog rigiocato al prossimo session-start. |
| Sessioni concorrenti | Ognuna ha la sua dir `<sid>/`. Zero collision. |
| Network down | Batch restano in outbox/. Retry a ogni punto di upload. |
| Lambda riceve duplicati | Dedup su event_id (overwrite su S3 con stessi dati). |
| Modello Claude non riconosciuto | Pricing `default` (Sonnet). |
| Disco pieno | `devforge_log` fallisce silenziosamente (|| true). |
| Dir sessione orfana | Cleanup 48h in session-start. Non pulisce dir con outbox pendente. |
| Schema v1 vs v2 | Lambda accetta entrambi. Query Athena filtrano per version. |
| DEVFORGE_CURRENT_SID in subshell | Variabile `export`-ata + fallback a lettura file `<sid>/sid` per robustezza. |
| hook_name passaggio | Ogni hook setta `export DEVFORGE_CURRENT_HOOK=<nome>` prima di `source logger.sh`. |
| Dual write fallimento | Il secondo append (globale) è fire-and-forget (`|| true`). Verrà rimosso in PR futura quando forge-insights migra a leggere dir sessione. |
| Rename user → actor_canonical | Schema v2 include ENTRAMBI: `user` (backward compat) + `actor_canonical` (nuovo). Query Athena esistenti non si rompono. |
| Migrazione file state globali | Durante PR2, i file globali continuano a essere alimentati in parallelo. Hook non ancora migrati leggono dai globali. PR futura rimuoverà i file globali dopo migrazione completa. |
| Token-collector "riscrittura" | Il codice attuale ha già dedupe e multi-model. PR3 cambia solo: (a) state in dir sessione, (b) allineamento pricing table. Non è una riscrittura totale. |
| Log rotation per sessione | No rotation su `<sid>/activity.jsonl` — la vita della sessione è limitata (cleanup 48h). |

---

## Criteri di Accettazione

### PR2 — Session State Isolation

| # | Criterio |
|---|----------|
| AC-1 | Ogni sessione scrive state in `~/.claude/devforge-state/<sid>/` |
| AC-2 | Due sessioni concorrenti non condividono state files |
| AC-3 | Identity pinnata a session_start, mai ricalcolata |
| AC-4 | Upload avviene in session-start (backlog), post-commit, stop-gate |
| AC-5 | Sessione senza commit: session_end viene uploadato |
| AC-6 | Batch pendenti ritentati automaticamente |
| AC-7 | Cleanup sessioni > 48h (ma non con outbox pendente) |
| AC-8 | Backward compat: JSONL globale ancora alimentato |

### PR3 — Analytics V2

| # | Criterio |
|---|----------|
| AC-9 | Ogni evento ha event_id, schema_version, session_seq |
| AC-10 | event_id globalmente unico (sid + seq) |
| AC-11 | Lambda dedup su event_id (no duplicati su S3) |
| AC-12 | Token deduplicated via message.id/requestId/uuid |
| AC-13 | Pricing multi-model (Opus, Sonnet, Haiku) |
| AC-14 | session_end include total_tokens, output_tokens, cost_estimate_eur |
| AC-15 | commit_created include token delta |
| AC-16 | Statusline mostra token + costo + telemetry status |

---

## Trade-off

| Decisione | Alternativa scartata | Motivo |
|-----------|---------------------|--------|
| Dir per-sessione | DB locale (SQLite) | Bash-native, zero dipendenze, file flat leggibili |
| Dual write (sessione + globale) | Solo sessione | Backward compat con forge-insights e script |
| Outbox con file batch | Queue (Redis/SQS) | Zero infra aggiuntiva, file flat su disco |
| event_id = sid + seq | UUID v4 | Deterministico, più corto, deducibile |
| Cleanup 48h | Cleanup immediato post-upload | Permette debug post-mortem |
| Pricing table hardcoded | API lookup | Zero dipendenze, aggiornabile con plugin |
| Default pricing = Sonnet | Nessun pricing se modello sconosciuto | Meglio una stima approssimata che nessuna |
