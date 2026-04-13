# Manual Verification Checklist — zero-loss

Edge case che non sono fedelmente automatizzabili in CI. Da eseguire manualmente
prima di una release.

## Edge #10 — Riavvio OS reale (Mac/Win)

**Mac:**
1. Aprire Claude Code, eseguire 5+ tool calls per generare eventi
2. Verificare `ls ~/.claude/devforge-state/*/activity.jsonl` non vuoto
3. **Cmd+Q forzato** Claude Code (non `/exit`)
4. **Apple Menu → Restart** (riavvio macOS)
5. Dopo login: `cat ~/.claude/devforge-state/*/activity.jsonl` deve contenere gli eventi pre-riavvio
6. Aprire Claude Code → verifica al prossimo `session-start` che il backlog viene uploadato
7. Verifica in S3 che gli eventi sono arrivati con `aws s3 ls s3://siae-devforge-telemetry/devforge-logs/year=YYYY/month=MM/day=DD/`

**Windows (Git Bash):**
Stessa procedura, sostituendo Cmd+Q con chiusura della finestra terminale + Restart Windows.

## Edge — disco pieno reale

1. `dd if=/dev/urandom of=/tmp/fill bs=1M count=$(( $(df -m /tmp | tail -1 | awk '{print $4}') - 50 ))` per riempire fino a <100MB liberi
2. Aprire Claude Code, eseguire tool calls
3. Verifica che `~/.claude/.devforge-disk-full-events.tmp` viene popolato
4. Liberare spazio: `rm /tmp/fill`
5. Triggera flush: prossimo session-start
6. Verifica in S3 evento `local_disk_full` arrivato

## Edge — clock skew reale

1. **NON FARE** in produzione (rompe certificati, kerberos, altre app)
2. Su VM/sandbox solo: `sudo date -u 010203041970` (porta data al 1970)
3. Apri Claude Code, verifica log `clock_skew_detected` emesso
4. Verifica in S3 che gli eventi del giorno hanno `received_at` Lambda invece di `ts` client
5. Ripristina data corretta

## Pre-release checklist completa

- [ ] Edge #10 Mac restart eseguito + verificato in S3
- [ ] Edge #10 Win restart eseguito + verificato in S3
- [ ] `make test-all` verde su CI
- [ ] `make test-acceptance` exit 0 (5 KPI gate PASS)
- [ ] DLQ vuota (CloudWatch alarm `devforge-telemetry-dlq-not-empty` not firing 7gg)
- [ ] Silent users report inviato + ≤2 dev silent
