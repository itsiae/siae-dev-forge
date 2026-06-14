# Task 09 — Write-path zero-loss cross-platform + suite data-loss esaustiva

**Stato:** PENDING
**Dipende da:** task-02 (helper/chain interprete), task-01 (caso 6 della suite: assenza CR negli hook)
**File:** `lib/logger.sh`, `lib/atomic_append.js` (nuovo), `tests/zero-loss/` (estensione)
**Priorità:** ALTA — requisito esplicito utente: "non possiamo perderci dati".

## Problema (vettore di perdita introdotto dal cross-platform)
`lib/atomic_write.py` (lock `flock` + `fsync`) è **python3-only**. Su Windows senza python3 il writer
cade sul fallback `printf >>` (`logger.sh:62-90`) **senza lock né fsync** → perdita dati sotto
concorrenza (hook/subagent paralleli) o crash. F2 espone questo path: va chiuso.

**Discovery task-02 (allarga il vettore):** l'attuale `_devforge_atomic_append` fa il fallback bash SOLO
quando `command -v python3` NON trova nulla. Se `python3` ESISTE ma **fallisce** (binario rotto, JSON env
corrotto, `return 127`), NON cade sul fallback → **la riga può andare persa in silenzio**. Esiste già
`DEVFORGE_FORCE_BASH_FALLBACK=1` come override. Il wrapper di questo task DEVE trattare "interprete presente
ma exit≠0" come fall-through (python3→node→bash), non solo "interprete assente". Caso di test dedicato sotto.

## Fix — fallback chain durabile (ADDITIVO, NON tocca il path python3 shipped)
**Il lock è UNO solo, acquisito dal wrapper bash** `_devforge_atomic_append` PRIMA di scegliere
l'interprete (no doppio lock — BLOCK-1). Mutua esclusione per-interprete: il path python3 (flock
DENTRO `atomic_write.py`) e i path node/bash (mkdir-lock del wrapper) non girano concorrenti sullo
stesso host (l'interprete disponibile è uno e fisso per sessione).

Ordine di scrittura, dal più al meno durabile:
1. **python3** `atomic_write.py` (flock LOCK_EX + fsync) — invariato, primario. Gestisce il lock
   internamente → in questo ramo il wrapper NON acquisisce il mkdir-lock.
2. **node** `lib/atomic_append.js` (NUOVO): il wrapper acquisisce il mkdir-lock, node fa append
   `O_APPEND` + `fs.fsyncSync`, il wrapper rilascia.
   ```js
   // lib/atomic_append.js — append durevole una-riga (lock già acquisito dal wrapper bash).
   const fs = require('fs');
   const file = process.argv[2];
   let data = '';
   process.stdin.on('data', c => (data += c));
   process.stdin.on('end', () => {
     const fd = fs.openSync(file, 'a');
     try { fs.writeSync(fd, data); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
   });
   ```
3. **bash degradato:** mkdir-lock + `printf >>` (no fsync) + evento `telemetry_degraded`
   (`reason="no_fsync_interpreter"`) → perdita potenziale OSSERVABILE, mai silente.

### Wrapper bash con lock portabile + STALE-GUARD (chiude BLOCK-2 — il vettore data-loss di kill -9)
```bash
# Rami node/bash (il ramo python3 esce prima via atomic_write.py).
# DEVFORGE_LIB = dir di questo lib; _devforge_dir_age_secs usa stat -f%m (BSD) || stat -c%Y (GNU).
_devforge_lock_append() {
    local file="$1" line="$2" lockdir="${file}.lockdir" waited=0 age
    while ! mkdir "$lockdir" 2>/dev/null; do
        # Stale-guard: kill -9 lascia il lockdir orfano (no trap su SIGKILL). Modello: telemetry-upload.sh:163-170.
        age=$(_devforge_dir_age_secs "$lockdir" 2>/dev/null || echo 0)
        if [ "${age:-0}" -gt 30 ]; then rmdir "$lockdir" 2>/dev/null || true; continue; fi
        waited=$((waited+1))
        if [ "$waited" -gt 50 ]; then            # 5s: MAI perdere la riga → append best-effort senza lock
            printf '%s' "$line" >> "$file"; return 0
        fi
        sleep 0.1
    done
    trap 'rmdir "'"$lockdir"'" 2>/dev/null || true' EXIT
    if command -v node >/dev/null 2>&1; then
        printf '%s' "$line" | node "$DEVFORGE_LIB/atomic_append.js" "$file" 2>/dev/null || printf '%s' "$line" >> "$file"
    else
        printf '%s' "$line" >> "$file"
        devforge_log "telemetry_degraded" "warning" '{"reason":"no_fsync_interpreter"}' 2>/dev/null || true
    fi
    rmdir "$lockdir" 2>/dev/null || true
    trap - EXIT
}
```
Principi zero-loss: (a) **stale-guard** rimuove il lock orfano da kill -9 entro 30s; (b) **timeout 5s** →
append diretto best-effort (preferiamo una riga non-fsync a una riga PERSA); (c) **trap EXIT** rilascia il
lock su uscita normale. Il mkdir-lock serializza i writer concorrenti su node/bash anche su Windows-senza-python3.

## Suite data-loss esaustiva — `tests/zero-loss/`
Estendere la suite esistente con i casi cross-platform (eseguibili anche forzando l'interprete):
1. **Concorrenza:** 50 writer paralleli emettono 1 evento ciascuno → file finale ha esattamente 50 righe
   JSON valide, zero righe interlacciate/troncate. Ripetere per i 3 path (python3 / node / bash).
2. **Crash mid-write:** uccidere il writer tra due eventi (`kill -9`) → nessuna riga parziale corrompe il
   file; gli eventi committati prima del kill ci sono tutti.
3. **No-interprete:** node+python3 mascherati → eventi comunque appesi via bash + `telemetry_degraded` emesso.
4. **node-only:** python3 mascherato → durabilità via `atomic_append.js` (fsync presente).
5. **Outbox replay:** upload S3 fallito → eventi restano in outbox, al retry caricati, conteggio invariato
   (ri-eseguire la suite zero-loss esistente: cursor, dead-letter, GC).
6. **CRLF (link task-01):** un hook CRLF-corrotto NON gira → con `.gitattributes` (task-01) il caso è prevenuto;
   test che verifica l'assenza di CR negli hook installati.
7. **Cursor integrity:** il byte-cursor del batching non salta né duplica eventi su file in append concorrente.
8. **Stale lock da kill -9 (BLOCK-2):** creare manualmente `${file}.lockdir` con mtime vecchio (> 30s),
   poi lanciare un writer → la stale-guard rimuove il lock orfano e l'evento viene scritto (NON perso, NON bloccato).
   Variante: lock recente tenuto da un PID vivo → il writer attende e poi scrive (nessuna perdita).
9. **python3 presente ma fallisce (discovery task-02):** shim `python3` che esce 127 mentre `node` è
   disponibile → l'evento viene comunque scritto via node (fall-through), NON perso. Variante: sia python3
   (shim 127) sia node (shim 127) presenti-ma-rotti → scrittura via bash `printf` + `telemetry_degraded`.

## Criteri di accettazione (design AC 14)
- Tutti e 9 i casi verdi sui path applicabili.
- La suite zero-loss esistente resta verde (no-regression sul path python3).
- Conteggio righe = conteggio eventi emessi in OGNI scenario (zero perdita verificata numericamente).
- Lock orfano da kill -9 NON causa perdita né deadlock (caso 8).

## No-regression
Path python3 (`atomic_write.py`) NON modificato. Solo rami fallback aggiunti.
