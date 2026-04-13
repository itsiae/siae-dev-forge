# DevForge Telemetry — Zero Data Loss + Blend Anthropic+Bedrock

**Data:** 2026-04-13
**Branch target:** feat/telemetry-zero-loss
**Stato:** Design proposto, in attesa approvazione
**Author:** Lorenzo De Tomasi (con Claude Code)

---

## 1. Contesto

Iniziativa post PR #185+#187 (telemetry-hardening + analytics-v2). Quei merge hanno
stabilizzato il write-side per le sessioni nuove (per-session dir, schema v2,
identity pinning), ma un audit dei dati S3 esistenti ha mostrato:

| Problema | Numero | Causa |
|---|---:|---|
| Parse error S3 | 6,612 righe (28%) | race scrittura concorrente su `activity.jsonl` shared (pre-PR #187) |
| Sessioni con `start` senza `end` | 1,531 / 2,666 (57%) | crash hook stop-gate, network down, App Nap macOS |
| `session_start` duplicati | 1,741 | hook `SessionStart` matcher su `startup/resume/clear/compact` ricorre |
| Dedup Lambda fallato | event_id `45bab25b-2 ×3` | dedup via S3 overwrite-by-key non gestisce client che rigenera stesso event_id |
| Token outlier | dopinto sid=293fcaf4 → 7.5M token | token-collector cumula cross-session quando `DEVFORGE_SESSION_DIR` non exported |
| Identità non normalizzata | 21 raw users vs ~14 persone reali | canonicalizzazione attiva solo nei v2 (oggi 19 eventi su 16,910) |
| Coverage parziale | 8 dev consumano API ma 0 eventi DevForge | plugin non installato — silent users invisibili |
| Backend blend invisibile | Bedrock usage non in S3 | DevForge cattura solo lato client, manca import CloudWatch Bedrock |

**Requisito utente (hard):** "non posso perdere niente nemmeno un dato".
**SLA:** eventi in S3 entro 1 ora dall'emissione lato client.
**Vincolo:** zero credenziali admin sulle macchine dev (Mac + Windows).

## 2. Obiettivi

1. **Durability locale** — write-side che resiste a race, crash, App Nap, disco pieno, clock skew
2. **Delivery garantita end-to-end** — exactly-once con DynamoDB dedup + DLQ + observability
3. **Recovery storico** — parser tollerante per i 6,612 errors esistenti
4. **Blend totale** — unificazione DevForge S3 + Anthropic console + CloudWatch Bedrock
5. **Discovery silent users** — report settimanale "consuma API ma DevForge silent"
6. **Test suite zero-loss** — 20 edge case + 5 KPI di acceptance

## 3. Decisioni architetturali (ADR)

| ID | Decisione | Alternative scartate | Motivo |
|---|---|---|---|
| ADR-1 | Hook-only flush (PostToolUse + Stop + UserPromptSubmit) | launchd/Task Scheduler OS-native | Cross-OS gratis, no installer, no admin. SLA <1h soddisfatta perché `Stop` flusha sync prima della chiusura |
| ADR-2 | flock cross-OS via Python `fcntl`/`msvcrt` + `fsync` per write | Solo flock Unix; line-per-file | Cross-OS, costo perf <2ms/write su SSD, durability su crash kernel |
| ADR-3 | Activity rotation a 5MB → `activity-<ts>.archived.jsonl` | No rotation (file unbounded) | Sessioni lunghe possono crescere a MB; cap 50MB per sessione safeguard disk |
| ADR-4 | Splitting batch <800KB lato client | Raise Lambda payload limit | Margine sotto 1MB Lambda, evita 400 + retry loop |
| ADR-5 | Lambda memory 128→256MB, payload 1→5MB, timeout 10→30s | Status quo | Margine OOM, gestisce batch più grandi, cold start S3 PUT lenti |
| ADR-6 | DynamoDB `devforge-event-dedup` (PK event_id, TTL 7gg) | S3 overwrite-by-key (status quo) | Vera exactly-once, risolve dup `45bab25b-2 ×3` |
| ADR-7 | DLQ via SQS per Lambda failure ripetuti | Retry eterno silenzioso | Visibilità + audit manuale, no loss |
| ADR-8 | Disk space gate + clock skew check + UTF-8 escape | Trust-and-pray | Edge case osservati o probabili |
| ADR-9 | Identity: regex GitHub-noreply + YAML alias map autoritativo | Solo YAML; SCIM | Copertura 90% automatica, YAML thin per residui |
| ADR-10 | Recovery one-shot script (parser tollerante) | Scartare; backfill schema v2 | Recupera ~3,000 eventi sui 6,612 corrotti senza forzare schema |
| ADR-11 | Importer Bedrock: Lambda nuova legge CloudWatch + scrive in S3 stesso bucket con prefix `bedrock-usage/` | Repo bedrock-aws-cap separato | Unifica analytics in S3 unico, scope blend |
| ADR-12 | Importer Anthropic console via API admin | Scraping HTML | API stabile, audit chiaro |
| ADR-13 | Test suite in `tests/zero-loss/` con 3 layer (unit+integration+chaos) | Solo unit | Garantisce KPI di acceptance prima di dichiarare "zero loss" |

## 4. Architettura componenti

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MACCHINA DEV (Mac/Win)                             │
│                                                                              │
│  Claude Code + DevForge plugin                                              │
│       │                                                                      │
│       ├─→ Hook (session-start, stop-gate, post-commit-review, ...)          │
│       │       │                                                              │
│       │       └─→ devforge_log() [flock + fsync] ──→ activity.jsonl         │
│       │                                                  │                   │
│       │                                                  └─→ rotate at 5MB  │
│       │                                                                      │
│       └─→ Trigger flush:                                                    │
│           - PostToolUse (cooldown 60s, background)                          │
│           - Stop (sync, prima di chiusura)                                  │
│           - UserPromptSubmit (background, opportunistic)                    │
│                  │                                                           │
│                  └─→ telemetry-upload.sh:                                   │
│                      - create_batch (split <800KB)                          │
│                      - POST API Gateway with x-api-key                      │
│                      - retry exponential backoff                            │
│                      - move to acked/ on 200/201                            │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTPS
                  ┌──────────────────────┐
                  │  API Gateway         │
                  │  POST /v1/logs       │
                  └─────────┬────────────┘
                            │
                            ▼
                  ┌──────────────────────┐         ┌──────────────────────┐
                  │  Lambda ingest       │←───────→│  DynamoDB            │
                  │  (256MB, 30s)        │  check  │  devforge-event-dedup│
                  │                      │  &set   │  PK: event_id        │
                  │  - parse JSONL       │         │  TTL: 7gg            │
                  │  - dedup on event_id │         └──────────────────────┘
                  │  - put_object S3     │
                  │  - return acked_ids  │
                  └─────────┬────────────┘
                            │
                            ├─→ S3 siae-devforge-telemetry/devforge-logs/...
                            │
                            └─→ on N failures → SQS DLQ → CloudWatch alarm

┌─────────────────────────────────────────────────────────────────────────────┐
│                       BLEND IMPORTER (nuovo)                                 │
│                                                                              │
│  Lambda devforge-bedrock-importer (cron daily)                              │
│       └─→ CloudWatch GetMetricData AWS/Bedrock                              │
│           per IAM user con prefix BedrockAPIKey                             │
│                                                                              │
│  Lambda devforge-anthropic-importer (cron daily)                            │
│       └─→ Anthropic admin API /v1/organizations/usage                       │
│                                                                              │
│  Output entrambi:                                                           │
│       └─→ S3 siae-devforge-telemetry/blend-usage/year=.../day=.../          │
│           schema: {actor_canonical, backend, model, input_tokens, ...}      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                       ANALYTICS / REPORTING                                  │
│                                                                              │
│  Athena queries:                                                            │
│  - dev usage totale per backend                                             │
│  - silent users (consumo blend > 0 AND devforge events = 0)                 │
│  - sessione → cost mapping                                                  │
│                                                                              │
│  (Dashboard estesa bedrock-aws-cap: OPZIONALE, fuori scope iniziativa)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 5. Componenti dettagliati

### 5.1 Write-side hardening (modifica `lib/logger.sh` + nuovo `lib/atomic_write.py`)

**Stato attuale REALE del codice (FIX BLOCK N1 iter-4):**

Una verifica grep su `lib/logger.sh` ha rivelato che le funzioni `devforge_with_lock`
e `devforge_append_jsonl` **NON esistono** (erano nomi inventati nelle iter precedenti
di questo design — errore documentale corretto in iter-4). Lo stato reale è:

- **`devforge_log()`** (`lib/logger.sh:252-307`): unica funzione di append. Fa
  `printf '%s\n' "$json_line" >> "$DEVFORGE_LOG_FILE"` **SENZA alcun lock** sull'append
- **`_devforge_check_rotation()`** (`lib/logger.sh:19-28`): rotation **già esistente**
  ma a 50MB con singolo backup `.1` (no timestamped archived files)
- **`devforge_log_timed()`** (`lib/logger.sh:307-...`): variante temporizzata, stesso
  pattern unlocked
- **`devforge_next_seq()`** (`lib/logger.sh:209-235`): unica funzione con `flock`, ma
  su file `seq.lock`, NON su `activity.jsonl`
- **`devforge_pending_count`** (`lib/telemetry-upload.sh:88-...`): conta batch un-acked
- **`devforge_create_batch`** (`lib/telemetry-upload.sh:18-50`): processa solo
  `${session_dir}/activity.jsonl` con singolo cursor `outbox/.cursor`

**Migration strategy (basata sulla realtà):**

1. **Fase 1** (PR-A): introdurre `lib/atomic_write.py` come nuova utility cross-OS
   con `fcntl.flock`/`msvcrt.locking` + `os.fsync`. Lock file path fisso:
   `${DEVFORGE_SESSION_DIR}/.activity.lock`.

2. **Fase 2** (stesso PR-A): refactor di `devforge_log()` e `devforge_log_timed()`:
   - Sostituire `printf '%s\n' "$line" >> "$DEVFORGE_LOG_FILE"` con
     `python3 "${PLUGIN_ROOT}/lib/atomic_write.py" append "$DEVFORGE_LOG_FILE" "$line"`
   - Append+fsync completamente in Python (single point of contention)
   - Bash diventa thin wrapper, no flock bash aggiuntivo necessario

3. **Fase 3** (stesso PR-A): estendere `_devforge_check_rotation`:
   - Soglia da 50MB → 5MB
   - Pattern da `.1` (single backup overwrite) → `activity-<unix_ts>.archived.jsonl`
     (timestamped multi-file)
   - Aggiungere enforce cap totale 50MB (activity + archived)

**Lock single-source garantito:** unico writer (`devforge_log` via Python), unico lock file
`.activity.lock`. No race condition: bash non scrive più direttamente. Vecchio path unlocked
viene completamente rimosso, no "live coexistence" da gestire.

**Backward compat:** la firma `devforge_log <event> <status> <meta>` resta invariata.
Tutti i 18 hook esistenti continuano a funzionare senza modifiche (solo l'implementazione
interna del log cambia).

**Modifiche concrete:**

- **fsync after write:** `devforge_log()` e `devforge_log_timed()` rimpiazzano il
  `printf >> file` raw con `python3 "${PLUGIN_ROOT}/lib/atomic_write.py" append "$DEVFORGE_LOG_FILE" "$json_line"` (single source of truth cross-OS).
  **NON si usa `dd if=/dev/null of=<file> conv=fsync`** perché tronca il file a 0 byte
  (apre in write mode, scrive 0 byte = truncate). Bug catastrofico per "zero data loss".
  Python single-fork ha overhead ~5-15ms su Mac SSD, accettabile per i volumi (~50KB/dev/giorno)
- **Activity rotation (FIX N9 iter-4):** estende `_devforge_check_rotation` esistente
  (`logger.sh:19-28`). Cambiamenti: soglia da 50MB→5MB, pattern da `.1` (singolo)
  →`activity-<unix_ts>.archived.jsonl` (timestamped multi-file), atomico via `mv` (rename)
- **Batcher esteso (`devforge_create_batch`, FIX N10 iter-4):** modifica significativa.
  Stato attuale: processa solo `activity.jsonl` con singolo cursor `outbox/.cursor`.
  Stato target: enumera `activity.jsonl + activity-*.archived.jsonl` in ordine crescente
  di timestamp file (parsing nome file). Per ogni file mantiene cursor separato in
  `outbox/.cursor-<basename>`. Quando un archived file è completamente uploaded
  (cursor == file size), può essere rimosso (cleanup). Garantisce no duplicati cross-file
- **Cap totale 50MB:** se somma `activity.jsonl + activity-*.archived.jsonl` > 50MB
  → `rm` archived più vecchio + log `local_quota_exceeded` (chiamando devforge_log
  ricorsivamente, sotto stesso lock)
- **Disk space gate:** prima di ogni `devforge_log()`, check via
  `df -k "$DEVFORGE_SESSION_DIR" | tail -1 | awk '{print $4}'`. Se <100MB (102400 KB),
  skip write + log a `~/.claude/.devforge-disk-full-events.tmp` per recovery al prossimo
  flush riuscito
- **NTP sanity:** session-start invoca `curl -sf -m 2 https://time.cloudflare.com/`
  (header `Date:`) e confronta con `date -u`. Se skew >3600s → log
  `clock_skew_detected` con valore skew + flag `force_received_at: true` nel session
  user.json. Lambda al ricevimento di un evento con quel flag usa `now()` come `ts`
  per partitioning S3 invece del client `ts`
- **UTF-8 escape (FIX WARN iter-3):** già presente in `devforge_sanitize_json_str`
  (`lib/logger.sh:239-247`, escapa `\`, `"`, newline, tab, control char).
  Test specifici in `tests/zero-loss/unit/test_atomic_write.py::test_utf8_roundtrip`
  (Python side, atomic_write.py preserva UTF-8 nativamente con `encoding="utf-8"`).
  **Da NON confondere con `escape_for_json`:** funzione locale presente solo nei
  singoli hook (`hooks/stop-gate:99`, `hooks/pre-commit:58`, ...), non in `lib/logger.sh`

### 5.2 Hook flush triggers (PARTE DI PR-A)

**Mapping a PR (CHIARIMENTO BLOCK-1):** questa sezione è inclusa nello scope di **PR-A**
(write-side hardening). Le modifiche tecniche sono:

**Modifiche a `hooks.json`** (file in `hooks/hooks.json` — FIX N4 iter-4, path corretto):

```jsonc
{
  "hooks": {
    "PostToolUse": [
      // entry esistenti per Skill (post-skill) e Bash (post-commit-review,
      // capture-test-result, batch-checkpoint) restano invariate.
      // NUOVA entry per flush:
      {
        "matcher": "*",
        "hooks": [{"type": "command",
                   "command": "bash hooks/devforge-flusher",
                   "async": true}]
      }
    ],
    "Stop": [
      // entry esistente per stop-gate (già fa flush async).
      // MODIFICA: spostare il flush PRIMA dei gate, in modalità sync.
      // NESSUN nuovo hook entry, solo edit di hooks/stop-gate
    ],
    "UserPromptSubmit": [
      // entry esistente per user-prompt-context, devforge-context-always.
      // MODIFICA: aggiungere flush opportunistico a devforge-context-always
      // (linea esistente fa già `source telemetry-upload.sh` per pending count;
      // estendere per chiamare `devforge_upload_logs &` se >0 pending)
    ]
  }
}
```

**Nuovo file `hooks/devforge-flusher`** (~30 righe bash):

```bash
#!/usr/bin/env bash
# Flusher invocato da PostToolUse — cooldown 60s per evitare flood
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAST_FLUSH_FILE="${HOME}/.claude/.devforge-last-flush"
COOLDOWN_SEC=60

NOW=$(date +%s)
LAST=$(cat "$LAST_FLUSH_FILE" 2>/dev/null || echo "0")
[ $((NOW - LAST)) -lt "$COOLDOWN_SEC" ] && exit 0

echo "$NOW" > "$LAST_FLUSH_FILE"
source "${PLUGIN_ROOT}/lib/telemetry-upload.sh" 2>/dev/null || exit 0
devforge_upload_logs 2>/dev/null &
exit 0
```

**Modifica `hooks/stop-gate`** (refactor minimo, ~5 righe — FIX WARN iter-3):

Stato attuale: `hooks/stop-gate:86` chiama `devforge_upload_logs 2>/dev/null || true`
**già sync**, ma all'interno di `_devforge_emit_session_end()` che viene invocata
SOLO se i gate (verification/retrospective) lasciano passare lo stop. Se un gate
blocca, il flush non avviene → backlog non risale.

Modifica: spostare `devforge_upload_logs` PRIMA dei gate, fuori da `_devforge_emit_session_end()`:

```bash
# Linea ~20 (dopo devforge_init_session, prima di leggere stdin)
source "${PLUGIN_ROOT}/lib/telemetry-upload.sh" 2>/dev/null || true
devforge_upload_logs 2>/dev/null  # SYNC, sempre, anche se gate blocca
```

Il flush dentro `_devforge_emit_session_end()` resta come secondo flush (catturare
gli ultimi eventi della session_end stessa). È un flush in più (idempotente),
non una sostituzione.

**Modifica `hooks/devforge-context-always`** (estensione, ~3 righe):

```bash
# Esistente: source telemetry-upload.sh per pending count
# AGGIUNGERE: se pending > 0, scatena upload background
PENDING=$(devforge_pending_count 2>/dev/null || echo "0")
if [ "$PENDING" -gt 0 ]; then
  devforge_upload_logs 2>/dev/null &
fi
```

**Verifica funzioni esistenti (FIX N5 iter-4):** `devforge_pending_count` è già
definita in `lib/telemetry-upload.sh:88-89` (verificata via grep — line corretto).
`devforge_upload_logs` è già definita stesso file. Nessuna nuova funzione da
introdurre, solo invocazione.

**Latency analysis (giustifica SLA <1h):**

| Trigger | Frequenza tipica | Garantisce flush in |
|---|---|---|
| PostToolUse (cooldown 60s) | Ogni tool call dopo cooldown | <1 min in sessione attiva |
| Stop (sync) | Fine sessione (Cmd+W, /exit) | 0s lag prima della chiusura |
| UserPromptSubmit | Inizio nuovo prompt | <5s al rientro dopo pausa |

Il caso "dev chiude Claude alle 19 con backlog" è coperto dal flush sync su Stop.
Il caso "dev offline >24h" rientra al rientro via UserPromptSubmit.

### 5.3 Telemetry-upload con splitting (`lib/telemetry-upload.sh`)

- `devforge_create_batch` modificato: invece di un singolo `batch-<ts>.jsonl`,
  spezza in N file da <800KB se necessario (`batch-<ts>-part01.jsonl`, ...)
- Cursor avanza solo dopo che TUTTI i part sono creati con successo
- Ogni POST è singolo file <800KB → no rischio Lambda payload limit

### 5.4 Lambda ingest (`infra/telemetry/lambda/handler.py`)

Modifiche:

```python
# 1. Memory bump (in lambda.tf)
memory_size = 256  # was 128
timeout     = 30   # was 10

# 2. Payload limit relax
if not body or len(body) > 5_242_880:  # 5MB, was 1MB

# 3. DynamoDB dedup integration
import boto3
ddb = boto3.client('dynamodb')

def dedup_check_and_set(event_id):
    """Returns True if NEW (insert succeeded), False if already exists."""
    try:
        ddb.put_item(
            TableName='devforge-event-dedup',
            Item={'event_id': {'S': event_id},
                  'ttl': {'N': str(int(time.time()) + 7*86400)}},
            ConditionExpression='attribute_not_exists(event_id)'
        )
        return True
    except ddb.exceptions.ConditionalCheckFailedException:
        return False

def handler(event, context):
    body = event.get("body", "")
    # ... validation ...

    lines = body.split('\n')
    new_lines, skipped_count = [], 0

    for line in lines:
        if not line.strip(): continue
        try:
            obj = json.loads(line)
            eid = obj.get('event_id')
            if eid and not dedup_check_and_set(eid):
                skipped_count += 1
                continue
            new_lines.append(line)
        except json.JSONDecodeError:
            new_lines.append(line)  # leave for parser-tolerant downstream

    if not new_lines:
        return {"statusCode": 200,
                "body": json.dumps({"status": "all_duplicates",
                                    "skipped": skipped_count})}

    new_body = '\n'.join(new_lines)
    key = _build_s3_key(new_body, datetime.now(timezone.utc))
    s3.put_object(Bucket=BUCKET, Key=key, Body=new_body,
                  ContentType="application/jsonl")

    return {"statusCode": 200,
            "body": json.dumps({"status": "ok",
                                "stored": len(new_lines),
                                "deduped": skipped_count,
                                "s3_key": key})}
```

### 5.4.bis API Gateway payload limit verification

Il payload di API Gateway sync invoke (default 10MB per `AWS_PROXY` integration) è
**superiore al nuovo limit Lambda 5MB**, quindi NON serve modifica infra API Gateway.
Verifica eseguita: il binding API Gateway → Lambda usa REST API standard (configurato
in `infra/telemetry/api_gateway.tf`) e non c'è un `request_validator` o request body
limit custom configurato. Il limit effettivo end-to-end resta 5MB lato Lambda.

Se in futuro Lambda payload aumenta >10MB, allora servirà migrare API Gateway a
HTTP API (limit 6MB sync) o usare invoke async via SNS/SQS. Fuori scope ora.

### 5.5 Infra additions (`infra/telemetry/`)

**Note FIX iter-3:**
- BLOCK N2: `dead_letter_config` su Lambda **non funziona con invocazioni sync** (API Gateway invoca sync). DLQ deve essere applicativo: il `handler.py` cattura le eccezioni e fa `sqs.send_message` PRIMA di restituire 5xx
- BLOCK N3: aggiunte IAM policy mancanti per DynamoDB (`PutItem`, `GetItem`) e SQS (`SendMessage`)
- WARN N6: aggiunti `aws_sns_topic.alerts` + subscription email
- WARN N9: chiarimento — ricezione SNS via email del primary owner, no PagerDuty/altro

```hcl
# dynamodb.tf (NEW)
resource "aws_dynamodb_table" "event_dedup" {
  name         = "devforge-event-dedup"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"

  attribute {
    name = "event_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

# sqs_dlq.tf (NEW)
resource "aws_sqs_queue" "telemetry_dlq" {
  name                      = "devforge-telemetry-dlq"
  message_retention_seconds = 1209600  # 14 days
}

# sns.tf (NEW — FIX WARN N6)
resource "aws_sns_topic" "alerts" {
  name = "devforge-telemetry-alerts"
}

resource "aws_sns_topic_subscription" "alerts_owner_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.primary_owner_email  # nuovo input variable
}

# Sezione 5.12 silent users report usa lo stesso topic alerts
# (un solo topic, due tipi di notifica: alert tecnici + report settimanale)

# lambda.tf (MODIFY)
resource "aws_lambda_function" "telemetry_ingest" {
  # ... existing ...
  memory_size = 256       # was 128
  timeout     = 30        # was 10

  # NO dead_letter_config: API Gateway invoca sync, dead_letter_config viene IGNORATA.
  # Il DLQ è applicativo: handler.py invia su SQS in caso di errore non recuperabile.

  environment {
    variables = {
      BUCKET_NAME    = aws_s3_bucket.telemetry.id
      DEDUP_TABLE    = aws_dynamodb_table.event_dedup.name  # NEW
      DLQ_QUEUE_URL  = aws_sqs_queue.telemetry_dlq.url       # NEW
    }
  }
}

# IAM policy aggiuntive (FIX BLOCK N3)
resource "aws_iam_role_policy" "lambda_dynamodb_dedup" {
  name = "devforge-telemetry-dynamodb-dedup"
  role = aws_iam_role.lambda_telemetry.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["dynamodb:PutItem", "dynamodb:GetItem"]
      Resource = aws_dynamodb_table.event_dedup.arn
    }]
  })
}

resource "aws_iam_role_policy" "lambda_sqs_dlq" {
  name = "devforge-telemetry-sqs-dlq-send"
  role = aws_iam_role.lambda_telemetry.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["sqs:SendMessage"]
      Resource = aws_sqs_queue.telemetry_dlq.arn
    }]
  })
}

# CloudWatch alarm (NEW)
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "devforge-telemetry-dlq-not-empty"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.telemetry_dlq.name
  }
}
```

**Modifica `handler.py` per DLQ applicativo (FIX BLOCK N2):**

```python
import boto3, os, json
sqs = boto3.client('sqs')
DLQ_URL = os.environ['DLQ_QUEUE_URL']

def handler(event, context):
    body = event.get("body", "")
    if not body or len(body) > 5_242_880:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid payload"})}

    try:
        # ... dedup + S3 put logic ...
        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}
    except Exception as e:
        # Ultima difesa: invia il payload su SQS prima di restituire errore.
        # Garantisce che il batch non sia perso anche se S3/DynamoDB sono down.
        try:
            sqs.send_message(QueueUrl=DLQ_URL,
                             MessageBody=body,
                             MessageAttributes={
                                 "error": {"DataType": "String", "StringValue": str(e)[:1000]},
                                 "request_id": {"DataType": "String",
                                                "StringValue": context.aws_request_id}
                             })
        except Exception as sqs_err:
            # Se anche SQS è giù: log e fail. Il client ritenta.
            print(json.dumps({"event": "dlq_send_failed", "error": str(sqs_err)}))
        return {"statusCode": 502, "body": json.dumps({"error": "Storage failure, queued in DLQ"})}
```

### 5.6 Identity alias map (`lib/identity-alias-map.yml`)

```yaml
# Autoritativa, committata, PR-reviewed
- canonical: lodetomasi
  raw:
    - 45626810+lodetomasi@users.noreply.github.com
    - lorenzo.detomasi@siae.it
    - lorenzo.detomasi@outlook.com
    - detomasi
  bedrock_iam: BedrockAPIKeyloto

- canonical: dpinto
  raw:
    - dopinto
    - domenico.pinto@siae.it
  bedrock_iam: BedrockAPIKeydomenico.pinto

- canonical: fvetrano
  raw:
    - fvetrano
    - francesco.vetrano@siae.it
  bedrock_iam: BedrockAPIKeyfrancesco.vetrano

# ... etc

# Regex fallback per GitHub noreply
fallback:
  - pattern: '^\d+\+(\w+)@users\.noreply\.github\.com$'
    extract: '\1'
```

Caricata da:
- Hook `session-start` per `actor_canonical` lato client
- Lambda ingest per validare `actor_canonical` server-side
- Importer Bedrock/Anthropic per mapping `BedrockAPIKey<x>` → canonical

### 5.7 Recovery script (`scripts/recovery-replay.py`)

**Esecuzione:**
- **Chi:** primary owner manualmente, post-merge PR-C
- **Dove:** locale (Mac), single-shot
- **Credenziali AWS:** profilo SSO `AdministratorAccess-613577363574` (account telemetria S3 verificato — vedi memoria reference)
- **Comando:** `python scripts/recovery-replay.py --bucket siae-devforge-telemetry --profile AdministratorAccess-613577363574 [--dry-run]`
- **Idempotenza:** SI. Lo script lista i file S3 corrotti, processa, scrive output con S3 key deterministica `devforge-logs-recovered/year=YYYY/month=MM/day=DD/recovered-<original-basename>.jsonl`. Re-esecuzioni sovrascrivono in modo atomico, no duplicati.

**Logica:**
1. Lista S3 `s3://siae-devforge-telemetry/devforge-logs/` con prefix corrotti
2. Per ogni file, parser tollerante:
   - `json.loads` per linea pulita
   - Se fallisce, regex `\{[^\{\}]*\}` per estrarre frammenti JSON-like, parsa quelli
   - Estrai campi essenziali: `event_id`, `sid`, `ts`, `user`, `event`
3. Scrive in `s3://siae-devforge-telemetry/devforge-logs-recovered/year=YYYY/month=MM/day=DD/recovered-<original-basename>.jsonl`
4. Marca ogni evento con `recovered: true`, `original_key: <s3-source-key>`, `recovery_method: "regex_fragment"|"clean_parse"`
5. **Output report:** `s3://siae-devforge-telemetry/devforge-logs-recovered/recovery-report.json`
   con `{total_input, total_recovered, recovery_rate, files_processed, run_at}`.
   **Path coerente con KPI G4 in §6.bis** (`acceptance test legge questa key esatta).

**Coordinamento con acceptance test:** il path del report è hardcoded nello script
e nel test (`devforge-logs-recovered/recovery-report.json`). Il test G4 fallisce con
messaggio "recovery-report.json missing" se lo script non è mai stato eseguito —
gate operativo: prima del PASS dell'acceptance test, lo script DEVE essere stato
eseguito almeno una volta.

### 5.8 Importer Bedrock — integrazione con bedrock-aws-cap esistente (CHIARIMENTO BLOCK-3)

**Sistema esistente `bedrock-aws-cap`** (locazione: `~/Documents/bedrock-aws-cap/` su iCloud
Drive del primary owner, vedi memoria `reference_bedrock_aws_cap.md`):

- **Cosa fa:** Lambda `spending_cap.py` invocata ogni 5 min via EventBridge.
  Legge CloudWatch `AWS/Bedrock` (`InputTokenCount`, `OutputTokenCount`) per `ModelId`,
  calcola costi (Haiku $1/$5, Sonnet $3/$15, Opus $5/$25 per MTok), salva
  aggregati in DynamoDB `bedrock-spending-cap-*` (TTL 7gg).
  A 80% budget mensile → SNS warning. A 100% → SNS + IAM deny `bedrock:InvokeModel`.
- **Dove scrive:** DynamoDB tabella interna a bedrock-aws-cap (NON in S3 oggi).
- **Account AWS:** stesso account dove gira Bedrock SIAE (eu-west-1, account ID
  da verificare; i 5 profili AdministratorAccess SSO disponibili includono
  613577363574 confermato per S3 telemetry — andrà verificato quale per Bedrock).
- **Naming convention IAM:** dev onboardati hanno IAM users con prefix
  `BedrockAPIKey<dev-name>` (vedi `bedrock-aws-cap/onboarding/<name>/`). Esempi:
  `BedrockAPIKeyfrancesco.vetrano`, `BedrockAPIKeydomenico.pinto`. Sono IAM users
  reali, NON role assumed via SSO — confermato leggendo `onboarding/onboard-developer.sh`.

**Strategia integrazione (NON duplica bedrock-aws-cap):**

Due opzioni considerate:

| Opzione | Pro | Contro | Decisione |
|---|---|---|---|
| **(a) Leggere CloudWatch in parallelo** | Indipendenza, no coupling con bedrock-aws-cap | Duplica chiamate `GetMetricData` (costo CW) | scartata |
| **(b) Leggere DynamoDB di bedrock-aws-cap** | Riusa il lavoro di aggregazione, no cost duplication | Coupling: schema DynamoDB diventa contratto | **scelta** |

**Implementazione (b):**

- Lambda `devforge-bedrock-importer` (cron daily 00:30 UTC)
- Cross-account read sulla DynamoDB `bedrock-spending-cap-*` (assume-role IAM)
- Per ogni dev e per ogni giorno trasforma riga DynamoDB → JSONL line con schema
  comune `blend-usage`:
  ```json
  {"event": "bedrock_usage", "actor_canonical": "fvetrano",
   "backend": "bedrock", "model": "claude-sonnet-4-6",
   "input_tokens": 50000, "output_tokens": 100000,
   "cost_eur": 1.95, "date": "2026-04-13",
   "source_system": "bedrock-aws-cap", "source_table": "bedrock-spending-cap-aggregates"}
  ```
- Mapping `BedrockAPIKey<name>` → `actor_canonical`: Lambda usa
  `identity-alias-map.yml` (caricata da S3, deploy via PR-C). Il map ha campo
  `bedrock_iam: BedrockAPIKey<name>` per ogni canonical user.
- Scrive in S3 `blend-usage/year=YYYY/month=MM/day=DD/bedrock-<canonical>.jsonl`
- Idempotente: chiave S3 deterministica `<canonical>-<date>.jsonl` (re-import
  overwrite atomico)

**Naming convention verificata:** prima di deploy, PR-D include uno script
`scripts/verify-bedrock-iam-users.sh` che lista IAM users sull'account Bedrock
e verifica che ALMENO 80% dei dev attivi (da bedrock-spending-cap aggregates)
abbiano un mapping `bedrock_iam` in `identity-alias-map.yml`. Se <80%, blocco
deploy con errore esplicito.

**Coordination con bedrock-aws-cap:**

- Lambda importer gira **dopo** che bedrock-aws-cap ha consolidato (cron 00:30
  vs bedrock-aws-cap che gira ogni 5 min — l'aggregato giornaliero in
  DynamoDB è stabile entro mezzanotte UTC + 30 min di buffer)
- Modifiche a `bedrock-aws-cap`: NESSUNA. Il repo resta autonomo. Nuovo importer
  è solo CONSUMER read-only della sua DynamoDB.
- Dashboard estesa: il punto Sez 4 "Dashboard estesa bedrock-aws-cap" è OPZIONALE
  e fuori scope da questa iniziativa. Rimosso da diagramma per coerenza scope.

**Setup IAM cross-account (FIX WARN N10 iter-3):**

Hyp scenario: account telemetria (`613577363574`, dove vive Lambda+S3 DevForge) ≠
account Bedrock (TBD, da identificare tra i 5 SSO; sospetti `100649704385` o
`134565215127`). Necessita assume-role.

```hcl
# Account BEDROCK (da deployare manualmente, una tantum):
resource "aws_iam_role" "devforge_bedrock_importer_xacc" {
  name = "DevForgeBedrockImporterCrossAccount"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { AWS = "arn:aws:iam::613577363574:role/devforge-blend-importer-role" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "devforge_bedrock_importer_xacc_dynamo" {
  role = aws_iam_role.devforge_bedrock_importer_xacc.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["dynamodb:Scan", "dynamodb:Query", "dynamodb:DescribeTable"]
      Resource = "arn:aws:dynamodb:eu-west-1:<bedrock-account-id>:table/bedrock-spending-cap-*"
    }]
  })
}

# Account TELEMETRIA (PR-D scope):
# NOTA FIX R1 iter-5: non creiamo un ruolo separato qui.
# Il ruolo viene definito una sola volta come `aws_iam_role.lambda_blend_importer`
# (name: "devforge-blend-importer-role") nella sezione successiva "IAM policies
# blend importers", e la policy sts:AssumeRole viene attachata a quello.
# Il trust policy sopra deve puntare a quel medesimo ruolo.
```

**Bedrock account ID (FIX N8 iter-4 — gate esplicito pre-deploy):**

Dependency esterna, da raccogliere dal primary owner prima del deploy PR-D. Salvato
come Terraform variable `var.bedrock_account_id` (non secret). Costo aggiuntivo: ZERO.

```hcl
variable "bedrock_account_id" {
  description = "AWS account ID ospitante Bedrock + DynamoDB bedrock-spending-cap-*"
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.bedrock_account_id))
    error_message = "bedrock_account_id must be a valid 12-digit AWS account ID."
  }
}
```

**Gate pre-PR-D:** `siae-writing-plans` deve bloccare la generazione del piano
implementativo PR-D finché `var.bedrock_account_id` non è definito in
`infra/blend/terraform.tfvars`. Il primo subtask di PR-D è "Risolvi Bedrock
account ID + popola tfvars", prerequisito hard per ogni altra attività.

**IAM policies blend importers + secrets + SNS (FIX N6 iter-4):**

```hcl
# Secret per Anthropic admin API key (account telemetria)
resource "aws_secretsmanager_secret" "anthropic_admin_api_key" {
  name = "devforge/anthropic-admin-api-key"
  description = "API key for Anthropic admin API — used by devforge-anthropic-importer"
}

# Lambda role per entrambi gli importer
resource "aws_iam_role" "lambda_blend_importer" {
  name = "devforge-blend-importer-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

# S3 write su blend-usage/ (per ENTRAMBI gli importer)
resource "aws_iam_role_policy" "blend_importer_s3_put" {
  role = aws_iam_role.lambda_blend_importer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "s3:PutObject"
      Resource = "${aws_s3_bucket.telemetry.arn}/blend-usage/*"
    }]
  })
}

# Bedrock importer: assume-role cross-account
resource "aws_iam_role_policy" "bedrock_importer_assume" {
  role = aws_iam_role.lambda_blend_importer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Resource = "arn:aws:iam::${var.bedrock_account_id}:role/DevForgeBedrockImporterCrossAccount"
    }]
  })
}

# Anthropic importer: lettura secret
resource "aws_iam_role_policy" "anthropic_importer_secret_read" {
  role = aws_iam_role.lambda_blend_importer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "secretsmanager:GetSecretValue"
      Resource = aws_secretsmanager_secret.anthropic_admin_api_key.arn
    }]
  })
}

# Silent users report Lambda: SNS Publish
resource "aws_iam_role" "lambda_silent_users_report" {
  name = "devforge-silent-users-report-role"
  # ... assume_role_policy standard Lambda ...
}

resource "aws_iam_role_policy" "silent_users_report_sns" {
  role = aws_iam_role.lambda_silent_users_report.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "sns:Publish",
        Resource = aws_sns_topic.alerts.arn },
      { Effect = "Allow", Action = ["athena:StartQueryExecution",
                                     "athena:GetQueryExecution",
                                     "athena:GetQueryResults"],
        Resource = "*" },
      { Effect = "Allow", Action = ["s3:GetObject", "s3:ListBucket"],
        Resource = [aws_s3_bucket.telemetry.arn,
                    "${aws_s3_bucket.telemetry.arn}/*"] }
    ]
  })
}
```

### 5.9 Importer Anthropic (`infra/blend/lambda-anthropic-importer/`)

- Lambda Python, cron daily 00:30 UTC
- Chiamata `https://api.anthropic.com/v1/organizations/{org_id}/usage_report?...`
- Auth via Anthropic admin API key (Secrets Manager)
- Stesso schema output, `backend: anthropic`

### 5.10 Test suite (`tests/zero-loss/`)

```
tests/zero-loss/
├── unit/
│   ├── test_atomic_write.py       # edge 1, 9, 13, 16, 17
│   ├── test_rotation.py           # edge 12
│   ├── test_disk_gate.py          # edge 3
│   ├── test_clock_skew.py         # edge 7, 18
│   ├── test_batch_split.py        # edge 6
│   ├── test_session_start_dedupe.py # edge 11
│   └── test_restart_simulation.py # edge 10 (subprocess kill+restart)
├── integration/
│   ├── docker-compose.yml         # LocalStack S3+Lambda+DynamoDB
│   ├── test_e2e_happy_path.py     # baseline
│   ├── test_network_failure.py    # edge 4, 5
│   ├── test_dedup_dynamodb.py     # edge 8
│   ├── test_concurrent_flush.py   # edge 15
│   ├── test_kill_during_write.py  # edge 2
│   └── test_app_nap_simulation.py # edge 14
├── chaos/
│   ├── conftest.py                # hypothesis profiles
│   └── test_random_failures.py    # property-based
├── replay/
│   └── test_recovery_replay.py    # edge 20 (replay storico)
├── acceptance/
│   └── test_zero_loss_certification.py  # 6.bis "conferma tutto" — KPI G1-G5 + deploy verification
├── manual-checklist.md            # edge 10 OS-level restart, manual procedures
└── Makefile                       # test-unit, test-integration, test-chaos, test-acceptance
```

### 5.11 KPI di acceptance "zero data loss"

**5 KPI GATE (bloccanti per release)** — disambiguati per coerenza con Obiettivo §2 e JIRA §11:

| # | Metric | Target | Misurato dove |
|---|---|---|---|
| **G1** | Parse error rate su nuovi eventi v2 in S3 | 0% | test unit `test_atomic_write` + measure su 30gg post-deploy |
| **G2** | Duplicati event_id in S3 | 0% | test integration `test_dedup_dynamodb` |
| **G3** | Sessioni `start` senza `end` (escluso device offline confermato) | <5% | measure su 30gg post-deploy (baseline 57%) |
| **G4** | Recovery rate file rotti storici | ≥45% | test replay `test_recovery_replay` |
| **G5** | Coverage canonical user (raw → canonical mapping) | ≥95% | test unit identity map + measure su 30gg post-deploy |

**3 metriche secondarie (telemetria di salute, non bloccanti):**

| # | Metric | Target | Note |
|---|---|---|---|
| S1 | Eventi locali → S3 <5min (golden path, sessione attiva) | 99% (rilassato da 99.99% per significatività statistica sui volumi attuali) | `test_e2e_happy_path`; KPI con valore solo se volume cresce a >10K eventi/settimana |
| S2 | Eventi locali → S3 <1h (test integration only, non misurabile in produzione) | 100% nei test, N/A in prod | **Solo `test_network_failure`** in CI. Non misurato in produzione perché richiederebbe heartbeat `last_online` (fuori scope). Per stima qualitativa in prod: ratio (eventi recenti in S3 / sessioni v2 attive) calcolato weekly come metric informativa S2-prod (≥80% target soft, no gate) |
| S3 | Silent users (consumo blend > 0 AND devforge events = 0) report settimanale | report disponibile + ≤2 silent dev | Manuale: query Athena settimanale (vedi §5.12) |

### 5.12 Silent users Athena query (PARTE DI PR-D)

Tabella Athena su `s3://siae-devforge-telemetry/blend-usage/`:

```sql
CREATE EXTERNAL TABLE blend_usage (
  event string, actor_canonical string, backend string,
  model string, input_tokens bigint, output_tokens bigint,
  cost_eur double, date string, source_system string
)
PARTITIONED BY (year int, month int, day int)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://siae-devforge-telemetry/blend-usage/'
TBLPROPERTIES ('projection.enabled'='true',
               'projection.year.type'='integer','projection.year.range'='2026,2030',
               'projection.month.type'='integer','projection.month.range'='1,12',
               'projection.day.type'='integer','projection.day.range'='1,31',
               'storage.location.template'='s3://siae-devforge-telemetry/blend-usage/year=${year}/month=${month}/day=${day}/')
```

**Tabella DevForge events (FIX WARN N7 iter-3):**

```sql
CREATE EXTERNAL TABLE devforge_events (
  event_id string, schema_version int, session_seq int, hook_name string,
  actor_canonical string, repo_root string, project_canonical string,
  ts string, user string, user_raw string, user_source string,
  sid string, branch string, jira_id string, project string,
  event string, status string, duration_ms bigint,
  meta map<string,string>
)
PARTITIONED BY (year int, month int, day int)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://siae-devforge-telemetry/devforge-logs/'
TBLPROPERTIES ('projection.enabled'='true',
               'projection.year.type'='integer','projection.year.range'='2026,2030',
               'projection.month.type'='integer','projection.month.range'='1,12',
               'projection.day.type'='integer','projection.day.range'='1,31',
               'storage.location.template'='s3://siae-devforge-telemetry/devforge-logs/year=${year}/month=${month}/day=${day}/')
```

Stesso schema di partition projection per `blend_usage`. Entrambe le tabelle vanno
create da PR-D come parte del setup Athena (database `devforge_telemetry`).

Query "silent users" (settimanale, eseguita dal report Lambda PR-D):

```sql
WITH blend AS (
  SELECT actor_canonical, SUM(cost_eur) AS spend_eur
  FROM blend_usage
  WHERE year=2026 AND month=4 AND day BETWEEN 6 AND 13
  GROUP BY actor_canonical
),
devforge AS (
  SELECT actor_canonical, COUNT(*) AS event_count
  FROM devforge_events
  WHERE year=2026 AND month=4 AND day BETWEEN 6 AND 13
  GROUP BY actor_canonical
)
SELECT b.actor_canonical, b.spend_eur, COALESCE(d.event_count, 0) AS dev_events
FROM blend b LEFT JOIN devforge d ON b.actor_canonical = d.actor_canonical
WHERE COALESCE(d.event_count, 0) = 0 AND b.spend_eur > 0
ORDER BY b.spend_eur DESC
```

Output report → SNS topic **`aws_sns_topic.alerts`** (riusa il topic definito in §5.5,
no nuovo topic) → email a primary owner via subscription già configurata.
Subject email: `[DevForge] Silent users weekly report - <date>`.

### 5.13 CI gating GitHub Actions (PARTE DI PR-E)

Repo `siae-dev-forge` oggi non ha CI. PR-E introduce `.github/workflows/zero-loss-ci.yml`:

```yaml
name: Telemetry Zero-Loss CI
on:
  pull_request:
    paths:
      - 'lib/**'
      - 'hooks/**'
      - 'infra/telemetry/**'
      - 'tests/zero-loss/**'
  schedule:
    - cron: '0 2 * * *'  # nightly chaos at 02:00 UTC

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install pytest hypothesis
      - run: pytest tests/zero-loss/unit -x -v
    # GATING RULE: required check per merge in main

  integration:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    services:
      localstack:
        image: localstack/localstack:3
        env: { SERVICES: s3,lambda,dynamodb,sqs }
        ports: [4566:4566]
    steps:
      - uses: actions/checkout@v4
      - run: pip install pytest awscli-local
      - run: cd tests/zero-loss/integration && make test
    # GATING RULE: required check per merge in main

  chaos:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - run: pip install pytest hypothesis
      - run: pytest tests/zero-loss/chaos --hypothesis-profile=ci
    # NON BLOCCANTE PR; failure crea issue automatica via gh issue create

  windows-smoke:
    runs-on: windows-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pytest tests/zero-loss/unit/test_atomic_write.py -v
    # GATING RULE: required check; verifica fcntl/msvcrt fallback su Windows
```

**Branch protection rule** (richiesta a admin GitHub repo): `main` richiede check
"Telemetry Zero-Loss CI / unit", "/ integration", "/ windows-smoke" come required
prima del merge. Chaos nightly è informativo (apre issue ma non blocca).

**Transport layer su Windows (CHIARIMENTO ALTO):** il job `windows-smoke` verifica
solo `atomic_write.py` Python perché è cross-OS gratis. I 18 hook bash + `telemetry-upload.sh`
girano su Windows tramite **Git Bash** (l'utente conferma di avere installato Git Bash
sui dev Win — check via `hooks/run-hook.cmd` esistente nel repo, che è il bridge
PowerShell → Git Bash). Le funzioni bash usate (`flock`, `mkdir`, `stat`, `df`)
hanno tutte equivalenti in Git Bash o fallback già implementati in `lib/logger.sh`.
PR-A include un test smoke aggiuntivo che esegue `bash -c "source lib/logger.sh && devforge_log ..."`
in CI Windows runner per verificare end-to-end.

## 6. Edge case coperti (mappa a test)

| # | Edge case | Test |
|---|---|---|
| 1 | Hook concorrenti race write | `test_atomic_write::test_concurrent_threads_no_truncation` |
| 2 | kill -9 mid-write | `test_kill_during_write` |
| 3 | Disco pieno | `test_disk_gate::test_aborts_below_100mb` |
| 4 | Network down durante POST | `test_network_failure::test_outbox_persists` |
| 5 | Lambda 5xx | `test_network_failure::test_retry_succeeds` |
| 6 | Batch >1MB | `test_batch_split::test_splits_at_800kb` |
| 7 | Clock skew >1h | `test_clock_skew::test_uses_received_at` |
| 8 | event_id duplicato | `test_dedup_dynamodb::test_3x_post_one_row` |
| 9 | Crash mid-upload | `test_atomic_write::test_cursor_not_advanced_on_failure` |
| 10 | Mac/Win restart (= riavvio processo Claude) | `test_restart_simulation`: spawn subprocess che scrive 50 eventi, kill SIGTERM mid-stream, riavvia, verifica activity.jsonl + cursor sopravvivono e nessun evento è lost. Riavvio OS reale: checklist manuale `tests/zero-loss/manual-checklist.md` |
| 11 | session_start ricorsivo (clear/compact) | `test_session_start_dedupe` |
| 12 | activity.jsonl >5MB | `test_rotation::test_rotates_at_5mb` |
| 13 | truncate accidentale | `test_atomic_write::test_handles_size_decrease` |
| 14 | macOS App Nap | `test_app_nap_simulation` |
| 15 | Outbox flush concorrenti (PostToolUse + Stop) | `test_concurrent_flush::test_lock_prevents_double_post` |
| 16 | Filesystem case-insensitive | `test_atomic_write::test_case_sensitive_event_id` |
| 17 | UTF-8 (emoji, accenti) | `test_atomic_write::test_utf8_roundtrip` |
| 18 | NTP irraggiungibile | `test_clock_skew::test_fallback_local_time` |
| 19 | DynamoDB throttling | `test_dedup_dynamodb::test_handles_429` |
| 20 | Replay file rotti storici | `test_recovery_replay::test_recovery_rate_45pct` |

### 6.bis Acceptance test finale "conferma tutto" (PARTE DI PR-E)

**Test richiesto dall'utente:** un meta-test end-to-end che CONFERMA esplicitamente
che TUTTI i 5 KPI gate sono soddisfatti dopo deploy completo. È diverso dai test unit/
integration: gira **post-deploy in produzione** (non in CI), su dati reali S3, e produce
un report PASS/FAIL.

**File:** `tests/zero-loss/acceptance/test_zero_loss_certification.py`

**Cosa fa:**

```python
"""Certifica che l'iniziativa zero-loss è completa.
Eseguito post-deploy con credenziali AWS read-only sul bucket telemetria.
Output: report markdown + exit code 0=PASS / 1=FAIL."""

import boto3, json, sys, datetime as dt
from collections import Counter


# FIX N3 iter-4: helper list_recent_v2_objects definito esplicitamente
def list_recent_v2_objects(s3, bucket, days=30):
    """List S3 objects in devforge-logs/ modified in the last `days` days.
    Yields dicts {Key, LastModified, Size}. Only v2 objects (schema_version=2).
    """
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=days)
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix='devforge-logs/year='):
        for obj in page.get('Contents', []):
            # Filter by modification time
            lm = obj['LastModified'].replace(tzinfo=None)
            if lm < cutoff:
                continue
            # Filter out sidecar/index files (if any). Schema v2 uses
            # deterministic keys of form year=.../sid-XXX/batch-YYY-to-ZZZ.jsonl.
            if '/sid-' not in obj['Key'] or not obj['Key'].endswith('.jsonl'):
                continue
            yield obj

# ----- KPI G1: Parse error rate v2 = 0% -----
def check_g1_parse_errors(s3, bucket, days=30):
    errors = total = 0
    for obj in list_recent_v2_objects(s3, bucket, days):
        body = s3.get_object(Bucket=bucket, Key=obj['Key'])['Body'].read().decode()
        for line in body.split('\n'):
            if not line.strip(): continue
            total += 1
            try: json.loads(line)
            except: errors += 1
    rate = errors / total if total else 0
    return ('G1', errors == 0, f'{errors}/{total} parse errors ({rate:.4%})')

# ----- KPI G2: Duplicati event_id = 0% -----
def check_g2_duplicates(s3, bucket, days=30):
    eids = Counter()
    for obj in list_recent_v2_objects(s3, bucket, days):
        body = s3.get_object(Bucket=bucket, Key=obj['Key'])['Body'].read().decode()
        for line in body.split('\n'):
            try:
                eid = json.loads(line).get('event_id')
                if eid: eids[eid] += 1
            except: pass
    dups = {k:v for k,v in eids.items() if v > 1}
    return ('G2', len(dups) == 0, f'{len(dups)} duplicate event_ids')

# ----- KPI G3: Sessioni start senza end <5% -----
def check_g3_session_completeness(s3, bucket, days=30):
    starts, ends = set(), set()
    for obj in list_recent_v2_objects(s3, bucket, days):
        for line in s3.get_object(Bucket=bucket, Key=obj['Key'])['Body'].read().decode().split('\n'):
            try:
                e = json.loads(line)
                sid, evt = e.get('sid'), e.get('event')
                if evt == 'session_start': starts.add(sid)
                elif evt == 'session_end': ends.add(sid)
            except: pass
    incomplete = starts - ends
    rate = len(incomplete) / len(starts) if starts else 0
    return ('G3', rate < 0.05, f'{len(incomplete)}/{len(starts)} incomplete ({rate:.2%})')

# ----- KPI G4: Recovery rate >=45% -----
def check_g4_recovery_rate(s3, bucket):
    report_key = 'devforge-logs-recovered/recovery-report.json'
    try:
        rep = json.loads(s3.get_object(Bucket=bucket, Key=report_key)['Body'].read())
        rate = rep['total_recovered'] / rep['total_input']
        return ('G4', rate >= 0.45, f'recovery_rate={rate:.2%} (target >=45%)')
    except s3.exceptions.NoSuchKey:
        return ('G4', False, 'recovery-report.json missing — recovery script non eseguito')

# ----- KPI G5: Coverage canonical >=95% -----
def check_g5_canonical_coverage(s3, bucket, days=30):
    # FIX N7 iter-4: la logica precedente contava `canonical==user_raw` come missing,
    # falso negativo quando il canonical coincide col raw (caso legittimo per
    # dev con username già canonical come `lodetomasi`). Correzione: verifica solo
    # la presenza (non-empty) di actor_canonical.
    canonical_present = canonical_missing = 0
    for obj in list_recent_v2_objects(s3, bucket, days):
        for line in s3.get_object(Bucket=bucket, Key=obj['Key'])['Body'].read().decode().split('\n'):
            try:
                e = json.loads(line)
                if e.get('actor_canonical'):  # non-empty = mapping applicato
                    canonical_present += 1
                else:
                    canonical_missing += 1
            except: pass
    total = canonical_present + canonical_missing
    rate = canonical_present / total if total else 0
    return ('G5', rate >= 0.95, f'canonical_coverage={rate:.2%} (target >=95%)')

# ----- Componenti deploy verification -----
def check_deploy_components(aws_session):
    checks = []
    # DynamoDB table esiste
    ddb = aws_session.client('dynamodb')
    try:
        ddb.describe_table(TableName='devforge-event-dedup')
        checks.append(('DEPLOY-DDB', True, 'devforge-event-dedup table exists'))
    except: checks.append(('DEPLOY-DDB', False, 'devforge-event-dedup table missing'))
    # SQS DLQ esiste
    sqs = aws_session.client('sqs')
    try:
        sqs.get_queue_url(QueueName='devforge-telemetry-dlq')
        checks.append(('DEPLOY-DLQ', True, 'devforge-telemetry-dlq exists'))
    except: checks.append(('DEPLOY-DLQ', False, 'devforge-telemetry-dlq missing'))
    # Lambda config corretta
    lam = aws_session.client('lambda')
    try:
        cfg = lam.get_function_configuration(FunctionName='devforge-telemetry-ingest')
        ok = cfg['MemorySize'] >= 256 and cfg['Timeout'] >= 30
        checks.append(('DEPLOY-LAMBDA', ok, f'memory={cfg["MemorySize"]}MB timeout={cfg["Timeout"]}s'))
    except: checks.append(('DEPLOY-LAMBDA', False, 'Lambda not found'))
    # Blend importer Lambdas
    for fn in ['devforge-bedrock-importer', 'devforge-anthropic-importer']:
        try:
            lam.get_function_configuration(FunctionName=fn)
            checks.append((f'DEPLOY-{fn}', True, f'{fn} deployed'))
        except: checks.append((f'DEPLOY-{fn}', False, f'{fn} missing'))
    # blend-usage/ contiene almeno 7gg di dati
    s3 = aws_session.client('s3')
    objs = s3.list_objects_v2(Bucket='siae-devforge-telemetry', Prefix='blend-usage/').get('Contents', [])
    days_present = len({o['Key'].split('day=')[1][:2] for o in objs if 'day=' in o['Key']})
    checks.append(('DEPLOY-BLEND', days_present >= 7, f'{days_present} days di blend data'))
    return checks

# ----- Main -----
def main():
    aws = boto3.Session(profile_name='AdministratorAccess-613577363574', region_name='eu-west-1')
    s3 = aws.client('s3')
    bucket = 'siae-devforge-telemetry'

    results = [
        check_g1_parse_errors(s3, bucket),
        check_g2_duplicates(s3, bucket),
        check_g3_session_completeness(s3, bucket),
        check_g4_recovery_rate(s3, bucket),
        check_g5_canonical_coverage(s3, bucket),
    ] + check_deploy_components(aws)

    print('# Zero-Loss Certification Report')
    print(f'Date: {dt.datetime.utcnow().isoformat()}Z')
    print()
    print('| Check | PASS | Details |')
    print('|---|---|---|')
    failed = 0
    for name, ok, details in results:
        icon = 'PASS' if ok else 'FAIL'
        print(f'| {name} | {icon} | {details} |')
        if not ok: failed += 1
    print()
    print(f'**Verdict: {"ALL PASS" if failed == 0 else f"{failed} FAILED"}**')
    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    main()
```

**Esecuzione (FIX WARN N9 iter-3):**
- **Manuale**, eseguito da primary owner con credenziali AWS read-only sul bucket telemetria:
  `python tests/zero-loss/acceptance/test_zero_loss_certification.py`
- **NON gira in CI** (richiede AWS credentials su account produzione 613577363574 — fuori scope CI public)
- **Pre-release gate:** prima di ogni tag/release del plugin DevForge, l'owner esegue manualmente
  e verifica exit 0
- (Eventuale automazione futura: workflow GHA dedicato con OIDC + IAM role read-only, fuori scope iniziativa)

**Output esempio:**
```
| Check | PASS | Details |
|---|---|---|
| G1 | PASS | 0/2384 parse errors (0.0000%) |
| G2 | PASS | 0 duplicate event_ids |
| G3 | PASS | 12/450 incomplete (2.67%) |
| G4 | PASS | recovery_rate=52.3% (target >=45%) |
| G5 | PASS | canonical_coverage=97.1% (target >=95%) |
| DEPLOY-DDB | PASS | devforge-event-dedup table exists |
| DEPLOY-DLQ | PASS | devforge-telemetry-dlq exists |
| DEPLOY-LAMBDA | PASS | memory=256MB timeout=30s |
| DEPLOY-devforge-bedrock-importer | PASS | deployed |
| DEPLOY-devforge-anthropic-importer | PASS | deployed |
| DEPLOY-BLEND | PASS | 9 days di blend data |

**Verdict: ALL PASS**
```

Questo è il "test che conferma che abbiamo fatto tutto" — copre KPI gate + deployment
artifacts. Senza questo PASS, l'iniziativa zero-loss NON è dichiarabile completa.

## 7. Decomposizione in PR (handoff a `siae-writing-plans`)

Il design verrà decomposto in **5 PR sequenziali** (A→B→C→D→E garantisce backward compat):

| PR | Topic | SP-Augmented | Branch | Componenti coperti (§5.x) |
|---|---|---|---|---|
| **PR-A** | Write-side hardening + hook flush triggers | 6 SP (incluso 1 SP per §5.2 hook flush) | `feat/telemetry-write-hardening` | §5.1, §5.2 |
| **PR-B** | Transport-side (Lambda mem+payload+timeout, DynamoDB dedup, SQS DLQ applicativo, batch split, SNS alerts) | 5 SP | `feat/telemetry-transport-hardening` | §5.3, §5.4, §5.4.bis, §5.5 |
| **PR-C** | Identity + recovery (alias map + GitHub noreply regex + recovery script + replay one-shot) | 3 SP | `feat/telemetry-identity-recovery` | §5.6, §5.7 |
| **PR-D** | Blend importers (Bedrock + Anthropic + silent users query Athena) | 5 SP | `feat/telemetry-blend-importers` | §5.8, §5.9, §5.12 |
| **PR-E** | Test suite + CI gating GitHub Actions + KPI dashboard + acceptance certification | 3 SP | `feat/telemetry-zero-loss-tests` | §5.10, §5.11, §5.13, §6.bis |

**Totale:** 22 SP-Augmented (6+5+3+5+3) / ~44 SP-Umano.

Test suite (PR-E) può girare in parallelo con A/B/C/D durante develop, ma il
gate di acceptance KPI viene applicato dopo merge di tutte e 5 le PR funzionali.

## 8. Costi infra incrementali

| Risorsa | Costo/mese |
|---|---:|
| Lambda 128→256MB (volume basso) | +$0.005 |
| DynamoDB on-demand event-dedup | <$0.50 |
| SQS DLQ | <$0.01 |
| Lambda Bedrock importer (1 invoc/giorno) | <$0.01 |
| Lambda Anthropic importer (1 invoc/giorno) | <$0.01 |
| Cross-account read DynamoDB bedrock-aws-cap (sts:AssumeRole + read) | <$0.01 |
| Storage S3 (blend-usage/) | <$0.10 |
| Secrets Manager (Anthropic admin API key, 1 secret) | $0.40 |
| Athena queries (silent users weekly + ad-hoc) | <$0.20 |
| **Totale** | **<$1.50/mese** |

(Soglia revisionata da $1 a $1.50 includendo Secrets Manager e Athena, omessi nella v1
del design — feedback spec-reviewer)

## 9. Rollback strategy

Ogni PR rollback-able indipendentemente:

- **PR-A**: revert commit, write-side torna a flock-less. Gli edge case osservati
  riemergono ma nessuna regressione su S3 (i nuovi dati v2 erano già OK)
- **PR-B**: revert commit Terraform → Lambda config rollback automatico, dedup
  via S3 overwrite-by-key (status quo PR #187)
- **PR-C**: revert script + alias map rinominato, identity torna allo stato attuale
- **PR-D**: revert Lambda importers, blend non più aggiornato. DevForge-only invariato
- **PR-E**: nessun rollback necessario (test suite, no impact prod)

DynamoDB table e SQS DLQ vanno mantenute anche post-rollback per evitare data loss.

## 10. Criteri di accettazione

- [ ] PR-A merged: zero parse error in eventi v2 nuovi (verificare 7gg post-merge)
- [ ] PR-B merged: DynamoDB dedup attivo, zero duplicati in S3 (verificare 7gg)
- [ ] PR-C merged: recovery script eseguito, ≥45% recovery rate sui 6,612 errors
- [ ] PR-C merged: alias map copre ≥95% degli user_raw osservati negli ultimi 30gg
- [ ] PR-D merged: blend-usage/ contiene almeno 7 giorni di dati Bedrock + Anthropic
- [ ] PR-E merged: tutti i 20 edge case test passano; CI gating attivo (unit + integration + windows-smoke required); chaos nightly green
- [ ] Report "silent users" disponibile e mostra ≤2 dev silent (target: tutti DevForge-attivi)
- [ ] Sessioni `start` senza `end` <5% (misurato 30gg post-merge tutte le PR)
- [ ] DLQ resta vuoto (verificato CloudWatch alarm zero trigger in 30gg)
- [ ] **Acceptance test finale `test_zero_loss_certification.py` esce 0 (ALL PASS) — gate manuale pre-release**

## 11. JIRA Ticket Output

```
Tipo:        Epic
Sommario:    DevForge Telemetry — Zero Data Loss + Blend Anthropic+Bedrock
Story Points: 22 SP-Augmented (44 SP-Umano)
Labels:      telemetry, observability, hardening, blend
Acceptance Criteria:
  - [ ] 5 PR (A/B/C/D/E) tutte mergiate
  - [ ] 5 KPI gate soddisfatti: G1 (parse=0%), G2 (dup=0%), G3 (incomplete<5%), G4 (recovery>=45%), G5 (canonical>=95%)
  - [ ] Costo infra confermato <$1.50/mese
  - [ ] Test suite zero-loss verde su CI (unit + integration + windows-smoke + chaos)
  - [ ] Acceptance test test_zero_loss_certification.py exit 0
```

---

## Stato approvazione

- [ ] Design approvato dall'utente
- [ ] Spec review automatica passata
- [ ] Pronto per `siae-writing-plans` decomposizione in 5 PR
