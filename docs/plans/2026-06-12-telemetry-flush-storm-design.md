# Design — Fix storm flusher telemetria + backlog illimitato

**Data:** 2026-06-12 · **Complessità:** Media-Alta · **SP:** 4 (Umano) / 1 (Augmented)
**Scope:** producer-side flush (`lib/telemetry-upload.sh` + `hooks/devforge-flusher`). NON tocca endpoint/consumer.

## Contesto

Backlog cresciuto a **13.457 batch / 56MB su ~967 sessioni**. Sintomo utente: ogni
operazione resta "running", processi `curl`/`devforge-flusher` accumulati (visti 8+
in parallelo, 3 curl sullo **stesso** batch). Contenimento già fatto: backlog
archiviato in `~/.claude/devforge-state-archive/`.

## Cause radice (confermate nel codice)

1. **Dead-letter mancante** (`telemetry-upload.sh:153-157`) — IL MOTORE del backlog:
   il batch va in `acked/` SOLO su HTTP 200/201. Qualsiasi non-200 (rate-limit, 4xx,
   payload stale) lo lascia in outbox → **ritentato a ogni flush per sempre**.
2. **Nessun lock sull'upload** (`devforge_upload_backlog`) — `flock` esiste solo in
   `create_batch` (:37) ed è no-op su macOS (flock assente, verificato). Flush
   concorrenti inviano lo stesso batch in parallelo → curl duplicati.
   **Aggravante confermata (grep):** l'upload è invocato in background da 7 call-site
   (`devforge-flusher:45`, `post-commit-review:91/271/388`, `session-start:311`,
   `stop-gate:27/112`) ma il cooldown 60s (`.devforge-last-flush`) è controllato
   SOLO da `devforge-flusher`. Gli altri 6 lo bypassano: un singolo `git commit`
   lancia 3 upload background da `post-commit-review`, senza cooldown né lock, tutti
   sullo stesso backlog. → Il lock globale C1 è l'UNICO punto condiviso da tutti i
   caller: è load-bearing, non un nice-to-have.
3. **Nessun cap per invocazione** (`:142-159`) — itera TUTTI i batch di TUTTE le
   sessioni: 13k batch = 13k curl seriali `--max-time 10`.
4. **Nessun GC** — gli outbox di 967 sessioni morte vengono ri-scansionati in eterno.

## Approcci valutati

- **A — Hardening in-place** (lock mkdir globale + cap + dead-letter + GC): additivo,
  confined a 2 file, preserva il modello opportunistic e lo zero-loss. ✅ SCELTO.
- **B — Single drainer daemon** (1 processo con PID file): elimina lo spawn per-tool
  ma è nuova infrastruttura, più superficie di rischio, fuori scope. Scartato.
- **C — Solo config** (alza cooldown): non risolve né i non-200 né la concorrenza.
  Scartato in Option-Zero.

## Decisione (Approccio A) — 4 componenti additivi

### C1 — Lock globale mkdir-based su `devforge_upload_backlog`
`mkdir ~/.claude/.devforge-flush.lock` come mutex atomico cross-process. Se fallisce →
un flush è già in corso → `return 0` (no concorrenza). `trap` rimuove il lock all'uscita.
Stale-lock guard: se la dir è più vecchia di 120s (processo morto), rimuovila e riprova.
Sostituisce il flock no-op su macOS.

### C2 — Cap per invocazione
`DEVFORGE_FLUSH_MAX_BATCHES` (default 100): l'upload_backlog processa al massimo N
batch per chiamata, poi esce. Drain incrementale su più flush invece di storm unico.

### C3 — Dead-letter dopo K tentativi
Contatore tentativi via file sidecar `.tries-<batch>` (o suffisso). Dopo
`DEVFORGE_FLUSH_MAX_TRIES` (default 5) non-200 → `mv` in `outbox/failed/`.
**Zero-loss**: i dati non sono cancellati, isolati in `failed/` per ispezione/reinvio.
Risposte retriabili (timeout/000/5xx) incrementano il contatore; 4xx persistenti
finiscono in failed/ comunque dopo K (sono comunque non recuperabili così come sono).
**Dipendenza (WARN-3):** C3 è safe solo SOTTO il lock C1 — senza lock due flusher
concorrenti possono leggere lo stesso contatore e fare race sul mv + lasciare sidecar
orfani. C1 va applicato prima o insieme a C3, mai dopo.

### Cap ordering (WARN-2)
Il cap C2 processa i batch **oldest-first** (il nome contiene `epoch_ns` → ordinamento
lessicografico = cronologico). Drain del backlog corrente: ~13k/100 ≈ 130 cicli di
flush (cooldown 60s ⇒ ~2h a regime). Accettabile: è opportunistic, non SLA-critico.

### C4 — GC sessioni morte
`devforge_gc_dead_outboxes` opera sulla **directory-sessione come unità atomica**, MAI
sul singolo batch file (WARN-5 spec-review: un batch non-acked può avere età >GC_DAYS
se il drain è lento o l'endpoint è stato irraggiungibile — GCarlo per età-file
violerebbe zero-loss). Una sessione è eleggibile per GC SOLO se:
  (a) NON è la sessione corrente (`$DEVFORGE_SID`), E
  (b) l'`mtime` più recente nell'intero outbox è più vecchio di `DEVFORGE_FLUSH_GC_DAYS`
      (default 14) — proxy di "sessione morta, nessuna scrittura recente".
Eleggibile → l'intera outbox viene compattata in `devforge-state-archive/` (stessa
operazione fatta a mano oggi), non cancellata. Invocato 1×/giorno via sentinel separato.
Nota: il GC archivia, non droppa → zero-loss preservato anche su batch mai inviati.

### Refactor per testabilità
Estrarre la POST curl in `_devforge_post_batch <file>` → ritorna HTTP code.
Iniettabile nei test via override (pattern già usato in `lib/release_risk`), così i
test bash non fanno rete reale.

## Criteri di accettazione (tutti con test bash, no unit-only)

1. Backlog di N batch + endpoint mock 200 → tutti in `acked/`, **≤cap** per invocazione.
2. Endpoint mock 500 ripetuto → dopo K tentativi i batch finiscono in `failed/`, **non**
   più ritentati alle invocazioni successive.
3. Lock: due `devforge_upload_backlog` concorrenti → solo uno processa (l'altro
   `return 0` immediato). Stale lock >120s → recuperato.
4. GC: outbox di sessione NON corrente con mtime più vecchio di GC_DAYS → archiviato
   fuori da outbox (a livello sessione, non file).
4b. (negativo) outbox con scrittura recente (<GC_DAYS) → NON archiviato; sessione
   corrente → MAI archiviata anche se vecchia.
4c. (lock stale) lock dir di 119s → blocca; di 121s → recuperato e flush procede.
5. Cooldown flusher 60s invariato; zero-loss invariato (nessun `rm` cieco di batch:
   il test verifica che dopo un upload fallito i batch siano ANCORA presenti).
6. Suite telemetria esistente (`tests/` relativi) resta verde.
