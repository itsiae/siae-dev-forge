# Design — Telemetria & Identità cross-platform (parità Windows ≡ macOS ≡ Linux)

**Data:** 2026-06-18
**Autore:** Lorenzo De Tomasi (assistito)
**Branch target:** da creare via siae-git-workflow (feature branch da `feat/statusline-python-and-update-notice` o da main)
**Stato:** DRAFT — in attesa approvazione gate

---

## 1. Contesto e obiettivo

Verifica empirica (matrice interpreti, rotazione, identità, flock, curl) ha confermato che la
catena di durabilità telemetria (`python3 → node → perl → bash+sync`) **non perde righe** su
nessun tier, su Mac e Windows Git Bash. Restano però due gap rispetto al principio
**"nessuna degradazione della telemetria"** e all'obiettivo **"100% delle attività del
developer con il nome risolto correttamente"**:

1. **Identità developer incompleta.** Caso reale SIAE: *un solo profilo GitHub condiviso con
   tanti PAT*. Il campo git-derivato (`user`/`actor_canonical`) collassa tutti gli sviluppatori
   su un'unica identità (es. `45626810+lodetomasi@users.noreply.github.com`). L'unico
   disambiguatore già presente è `auth_email` (SSO `oauthAccount.emailAddress`). Serve
   arricchire con **segnali identità locali letti dal computer** per ridondanza e nome umano.

2. **Rotazione log python3-only.** La rotazione (rename a 5MB) vive solo in `atomic_write.py`.
   Su Windows senza python3 (tier node/perl) il log **cresce illimitato** e il cap 50MB non si
   applica mai (droppa solo `.archived.jsonl` che non vengono mai creati). Verificato:
   `node-only main_size=4191 archived_files=0` vs `python3 main_size=2100 archived_files=1`.

**Requisito hard utente:** *parità stretta Windows ≡ macOS (≡ Linux)*. Nessun ramo
"best-effort vuoto su Windows": ogni capability deve produrre lo **stesso campo con la stessa
semantica** su tutte le piattaforme, popolato col metodo corretto per OS. Un campo è vuoto solo
se il dato non esiste davvero (es. nessuna chiave SSH).

**Principi invarianti** (memory): zero-loss, additivo (mai rimuovere campi), mai abortire sotto
`set -euo pipefail`, raw-only (nessuno score derivato nel producer), nessuna rete nel path caldo.

---

## 2. Scope

In scope: `lib/logger.sh` (identity bundle + rotazione tier degradati) e `lib/telemetry-upload.sh`
(drain archivi globali — vedi BLOCK-1). Out of scope: consumer downstream (Lambda/analytics),
`atomic_write.py` (resta source-of-truth python3, invariato — ma la rotazione bash ne replica la
semantica E corregge un bug latente di cursore che oggi affligge anche il path python3, §4).

Decomposizione (3 sotto-aree, dominio coeso):
- **A** — Identità multi-segnale cross-platform (4 nuovi segnali)
- **B** — Rotazione cross-tier (bash, parità python3)
- **C** — Hardening edge-case/fallback (21 findings hunter)

---

## 3. Capability A — Identità multi-segnale

Nuova funzione `_devforge_local_identity_signals` chiamata da `devforge_identity_bundle`
(logger.sh:371). Campi additivi al JSON bundle (consumati a valle, mai dal path caldo
per-evento). Ogni segnale isolato, ogni ramo termina con `|| true`, ogni valore passa per
`devforge_sanitize_json_str` e `head -1`, troncato a 128 char.

### Matrice di parità (requisito)

| Campo JSON | macOS | Linux | Windows (Git Bash) |
|---|---|---|---|
| `os_full_name` | `id -F` | `getent passwd $USER \| cut -d: -f5 \| cut -d, -f1` | PowerShell `Get-CimInstance Win32_UserAccount … FullName` (non localizzato) |
| `os_login` | `${USER:-$(whoami)}` | `${USER:-$(whoami)}` | `${USERNAME:-${USER:-$(whoami)}}` |
| `os_domain` | `""` (non esiste — vedi ADR-5) | `""` | `${USERDOMAIN:-}` |
| `ssh_fingerprint` | `ssh-keygen -lf` prima `*.pub` ordinata | idem | idem |
| `npm_email` | `npm config get email` (filtra `undefined`/`null`) | idem | idem |
| `gh_email` | `gh api user` **opt-in** (`DEVFORGE_IDENTITY_GH=1`) | idem | idem |

### Decisioni chiave

- **`os_full_name` Windows non localizzato**: si usa PowerShell `Get-CimInstance` (output campo
  `FullName`, indipendente dal locale) — NON parsing `net user` (etichetta localizzata
  "Full Name"/"Nome completo", fragile → CRITICAL-2). Guard `command -v powershell.exe` con
  fallback a vuoto. Selezione OS via `uname -s` (`Darwin`/`Linux`/`MINGW*|MSYS*|CYGWIN*`).
- **`gh_email` opt-in (default OFF)**: `gh api user` fa **rete** (CRITICAL-1) → bloccherebbe
  session-start su proxy SIAE. Default disattivato; quando attivo, wrappato con timeout portabile
  (`net-timeout.sh`/`perl alarm`, NON `timeout` puro → assente su BSD/Win, memory
  `feedback_macos_timeout_portability`). `npm_email` resta ON (locale, veloce) ma anch'esso
  timeout-guarded (MEDIUM-16).
- **`ssh_fingerprint` deterministico**: prima chiave `*.pub` in ordine `sort`, hash via
  `_devforge_shasum` (helper portabile esistente). Solo chiave **pubblica** — mai toccare chiavi
  private (CRITICAL-5, MEDIUM-18). **No `xargs -r`** (flag GNU-only, assente su BSD/macOS —
  BLOCK-4): si usa guard esplicita `key=$(ls -1 ~/.ssh/*.pub 2>/dev/null | sort | head -1);
  [ -n "$key" ] && [ -r "$key" ] && ssh_fp=$(ssh-keygen -lf "$key" 2>/dev/null | awk '{print $2}' || true)`.
- **`npm_email` guard esplicito** (WARN-6): `command -v npm >/dev/null 2>&1` **prima** della
  chiamata (npm spesso assente nel PATH di hook non-interattivi su macOS). `"undefined"`/`"null"`/`""`
  normalizzati a vuoto (CRITICAL-6) — evita email-fantasma nell'analytics.
- Tutti i nuovi campi sono **best-effort**: assenza tool/dato → stringa vuota, mai abort,
  mai degradazione della riga telemetria.

### Pin a session-start

`devforge_identity_bundle` gira **una volta** a session-start → confluisce in `user.json`.
I nuovi segnali NON sono nel path per-evento (`devforge_log` legge solo `DEVFORGE_AUTH_*`
pinnati). Costo rete/PowerShell pagato 1×/sessione, non per evento.

---

## 4. Capability B — Rotazione cross-tier (parità python3)

**Approccio scelto (post-hunter + post-spec-review):** rotazione **centralizzata in bash, dentro
il lockdir** del path degradato, con parità a `atomic_write.py._rotate_if_needed` MA
**cursor-aware** (corregge un bug latente che oggi affligge anche il path python3). NON rotazione
autonoma in node/perl (CRITICAL-7, CRITICAL-8).

### Architettura: due file, due lock (chiarimento BLOCK-1/BLOCK-2)

`devforge_log` scrive in DUE file via `_devforge_atomic_append`: il **globale**
(`~/.claude/devforge-activity.jsonl`, accumula tutte le sessioni → è quello che cresce illimitato
su Win) e il **di sessione** (`${SESSION_DIR}/activity.jsonl`). Entrambi devono ruotare per parità.
- **File di sessione**: archivi `${SESSION_DIR}/activity-<ts>.archived.jsonl`, drenati da
  `devforge_create_batch` (telemetry-upload.sh:44) che **già scansiona** `activity-*.archived.jsonl`. OK.
- **File globale** (BLOCK-1): archivi `~/.claude/devforge-activity-<ts>.archived.jsonl`. Oggi
  `devforge_batch_global` (telemetry-upload.sh:100) **NON** li scansiona → righe stranded.
  **Questo è un bug già presente nel path python3** (che ruota il globale a 5MB). **Fix in scope**:
  estendere `devforge_batch_global` per scansionare anche `devforge-activity-*.archived.jsonl`
  (cursore per-basename in `.global-outbox`), simmetrico a `devforge_create_batch`.

### Bug latente del cursore (BLOCK-2) e fix cursor-aware

Oggi (anche python3): dopo rename `activity.jsonl → archived`, il cursore `.cursor-activity.jsonl`
resta al vecchio valore (es. 5MB). Il file fresco riparte piccolo → `file_size < cursor` → il
batcher **non** lo batcha finché non risupera 5MB. Bug latente di ritardo/stuck. Fix: la rotazione
**sposta il cursore** atomicamente col rename:
- `mv "${outbox}/.cursor-${base}.jsonl" "${outbox}/.cursor-${archived_basename}"` → l'archivio
  riprende esattamente da dove il file live si era fermato (**zero duplicati, zero perdita**), e il
  file fresco non ha cursore → riparte da 0 → tutti i nuovi eventi batchati.
- Residuo race writer-vs-batcher (lock distinti: lockdir vs batch.lock): finestra microscopica tra
  rename e mv-cursore. Worst-case = **ri-upload idempotente** lato Lambda, mai perdita. Documentato.

### Modifiche concrete

1. **`_devforge_rotate_inline "$file" "$rotate_bytes" "$outbox_dir"`** (nuova helper bash):
   - size via `stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0`
     (portabile; file mancante → 0 → no-op, C-14)
   - `size <= rotate_bytes` → no-op (return 0)
   - `ts=$(date +%s)`; `archived="${dir}/${base}-${ts}.archived.jsonl"`; collisione →
     loop suffisso `-1..-999` (HIGH-13, parità `range(1,1000)` python3)
   - `mv "$file" "$archived" 2>/dev/null || return 0` (rename atomico; già ruotato da altro
     processo → mv fallisce → return, HIGH-10)
   - **cursor-move** (se `$outbox_dir` fornito e cursore live esiste): `mv` cursore live → cursore
     archivio (BLOCK-2)
   - fallimento permessi su `mv` (C-21): return 0, riga verrà comunque scritta dall'append; il cap
     resta gestito da `_devforge_check_rotation`; nessun abort
2. **`_devforge_lock_append "$file" "$line" "${rotate_bytes:-0}" "${outbox_dir:-}"`** (BLOCK-5,
   firma esplicita): `$1`=file, `$2`=line (con `\n`), `$3`=rotate_bytes (default 0 = no rotazione),
   `$4`=outbox_dir (default vuoto = no cursor-move). Chiama `_devforge_rotate_inline` **dentro il
   lockdir, prima** dell'append node/perl/bash. Writer del path degradato condividono `${file}.lockdir`
   → race-safe tra loro (macchina python3-less: nessun writer usa flock → no cross-lock race, C-8).
3. **`_devforge_atomic_append`**: passa `rotate_bytes` E `outbox_dir` (derivato da
   `${DEVFORGE_SESSION_DIR}/outbox` per il file di sessione, `${state_root}/.global-outbox` per il
   globale) a `_devforge_lock_append` (oggi passa solo file+line).
4. **`_devforge_check_rotation`** (cap 50MB) invariato: ora node/perl **creano** archivi → cap
   effettivo su Win. La sua lettura cursori fuori-lock è safe (C-15/WARN-3): se trova un archivio
   senza cursor file (cursor=0 < size) non lo droppa — corretto, mai perdita.

### Routing outbox_dir e cursori archivi globali (GAP-A / GAP-B — chiude BLOCK-1/BLOCK-5)

**Routing in `_devforge_atomic_append`** (GAP-B): la funzione riceve `target_file`. Deriva
`outbox_dir` per confronto esplicito:
```
if [ "$target_file" = "$DEVFORGE_LOG_FILE" ]; then
    outbox_dir="${HOME}/.claude/devforge-state/.global-outbox"
else                       # è ${DEVFORGE_SESSION_DIR}/activity.jsonl
    outbox_dir="${DEVFORGE_SESSION_DIR}/outbox"
fi
```
Passato come 4° arg a `_devforge_lock_append`. Sul path python3 (atomic_write.py) il cursor-move
NON avviene (ADR-6, accettato): lo recupera il primo evento bash/node/perl successivo.

**Cursori archivi globali** (GAP-A): oggi `devforge_batch_global` usa un cursore fisso
`.global-outbox/.cursor-global`. Va rifattorizzato a **per-basename**, simmetrico a
`devforge_create_batch`:
- scansiona `~/.claude/devforge-activity-*.archived.jsonl` (ordinati) + `devforge-activity.jsonl`
- cursore per-file: `.global-outbox/.cursor-<basename>` (es. `.cursor-devforge-activity-<ts>.archived.jsonl`)
- **migrazione**: al primo run, se esiste il vecchio `.cursor-global`, viene rinominato in
  `.cursor-devforge-activity.jsonl` (preserva l'offset già drenato → zero ri-upload del backlog)
- **cleanup**: `_devforge_maybe_remove_archived` generalizzata ad accettare il prefisso base come
  arg (`activity` per sessione, `devforge-activity` per globale) invece dell'hardcoded
  `activity-*.archived.jsonl`; rimuove l'archivio quando `cursor >= size`.

Il cursor-move della rotazione globale usa quindi lo stesso schema per-basename in `.global-outbox`.

### CRLF guard (HIGH-12)

Ogni lettura di file cursore/stato numerico in `logger.sh` e `telemetry-upload.sh` normalizzata
con `| tr -d '\r'` prima dei confronti aritmetici (Windows `core.autocrlf`): include i `cat
"$cursor_file"` in `devforge_create_batch`, `devforge_batch_global`, `_devforge_check_rotation`,
`_devforge_rotate_inline`.

---

## 5. Capability C — Hardening (mappa findings → fix)

| Finding | Severità | Fix |
|---|---|---|
| C-1 `gh api user` rete blocca hook | CRITICAL | opt-in + timeout portabile (§3) |
| C-2 `net user` localizzato | CRITICAL | PowerShell `Get-CimInstance` (§3) |
| C-3 `id -F` Unicode/quote | CRITICAL | `devforge_sanitize_json_str` + `head -1` + trunc 128 |
| C-4 guard piattaforma `getent`/`id -F` | CRITICAL | switch `uname -s` + `|| true` ogni ramo |
| C-5 glob SSH 0 file/SIGPIPE | CRITICAL | guard `[ -d ~/.ssh ]`, `ls\|sort\|head -1\|xargs -r`, `|| true` |
| C-6 `npm` → `"undefined"` | CRITICAL | normalizza a vuoto |
| C-7 cursore batcher vs rename | CRITICAL | rotazione bash **cursor-aware** (mv cursore) + drain archivi globali in `devforge_batch_global` (§4) |
| C-8 lock flock vs lockdir | CRITICAL | rotazione solo nel path lockdir; python3 path invariato; no writer-mix su macchina stabile (§4) |
| C-9 `stat` portabile | CRITICAL | pattern `-f%z\|\|-c%s\|\|0` esistente |
| C-10 doppia rotazione concorrente | HIGH | `mv … \|\| return 0` + loop suffisso |
| C-11 cursore a metà file | HIGH | **cursor-move** elimina lo stuck; residuo = ri-upload idempotente (§4) |
| C-12 CRLF cursore Windows | HIGH | `tr -d '\r'` su tutte le letture cursore |
| C-13 clock-backward collisione | HIGH | loop suffisso `-1..-999` |
| C-14 `activity.jsonl` inesistente | HIGH | size→0 → no-op (parità perl `-s`) |
| C-15 race check_rotation/append | HIGH | append crea file se assente (già vero) — nessuna azione |
| C-16 `npm` lento | MEDIUM | timeout portabile + `command -v` |
| C-17 `USERDOMAIN` unbound `set -u` | MEDIUM | sempre `${USERDOMAIN:-}` |
| C-18 SSH non deterministico | MEDIUM | `sort \| head -1` |
| C-19 `id -F` AD multiriga | MEDIUM | `head -1` |
| C-20 iCloud cache rotazione | MEDIUM | known limitation documentata |
| C-21 rotazione fallita → no cap | MEDIUM | `telemetry_degraded` one-shot (sentinel), riga comunque scritta |

---

## 5bis. Capability D — `event_id` collision-resistant (finding verifica finale)

**Scoperto dalla verifica finale cross-platform** (non in scope iniziale): `flock` **binario è
assente** su macOS E Windows Git Bash → `devforge_next_seq` (logger.sh:574) cade nel path
non-lockato (logger.sh:590-593). Sotto concorrenza reale (hook paralleli) due processi leggono lo
stesso `current` → stesso `seq` → **`event_id` duplicato** (verificato: 22-24 unici su 25,
intermittente, su entrambe le piattaforme). Rischio diretto al goal **100% attività**: dedup
downstream su `event_id` scarterebbe eventi distinti.

**Fix:** rendere `devforge_next_seq` atomico **senza dipendere dal binario `flock`**, via
**mkdir-lock** portabile (stesso pattern già usato in `_devforge_lock_append`/telemetry-upload.sh):
acquisizione `${seq_file}.lockdir`, read-increment-write, rilascio. Stale-guard analogo. Fallback
ulteriore: se anche mkdir-lock fallisce, suffisso ad alta entropia su `event_id`
(`${sid}-${seq}-$$-${RANDOM}`) per garantire unicità anche con `seq` in tie. Il campo `seq` resta
per l'ordinamento; `event_id` resta la chiave di dedup, ora collision-resistant.

Parità: il fix è bash puro → identico su mac/Linux/Windows (nessuno dipende più dal binario `flock`).

## 6. Testing

Tutti i test in `tests/zero-loss/unit/` con tecnica shim-PATH (`make_mask`) già usata in
`test_logger_perl_fsync.sh`. Simulazione cross-platform via mascheramento interpreti + `uname`
override.

1. **`test_logger_identity_signals.sh`** (nuovo): per ogni segnale, presenza/assenza tool →
   campo popolato/vuoto, mai abort, JSON valido. Casi: `undefined` npm, SSH 0 chiavi, SSH N
   chiavi (determinismo), Unicode in nome, `USERDOMAIN` unset sotto `set -u`, `gh` opt-in OFF
   (nessuna chiamata rete).
2. **`test_logger_rotation_crosstier.sh`** (nuovo): matrice interpreti (python3/node/perl/bash)
   → rotazione a soglia bassa produce archivio su OGNI tier; collisione nome → suffisso; file
   inesistente → no-op; cap 50MB droppa archivio consumato anche su node-only; **cursor-move**:
   dopo rotazione il file fresco riparte da cursor 0 e l'archivio eredita il vecchio cursore.
3. **`test_logger_crlf_cursor.sh`** (nuovo): cursore con `\r` → confronto aritmetico OK, nessun
   abort.
4. **`test_batch_global_archives.sh`** (nuovo): `devforge_batch_global` drena anche
   `devforge-activity-*.archived.jsonl` del globale (BLOCK-1) → nessuna riga stranded dopo
   rotazione del file globale.
5. **`test_logger_event_id_concurrency.sh`** (nuovo, Capability D): 50 `devforge_log` concorrenti
   con `flock` mascherato (simula mac/Win) → 50 `event_id` distinti (zero collisioni), `seq`
   monotono senza duplicati.
4. Regressione: `test_logger_perl_fsync.sh`, `test_logger_uses_atomic_write.sh`,
   `test_telemetry_fixes.sh`, `test_telemetry_flush_storm.sh` devono restare verdi (no-regression).

---

## 7. Criteri di accettazione

- [ ] AC1: `devforge_identity_bundle` emette i 6 campi nuovi su mac/Linux/Win con metodo corretto per OS; parità di campi.
- [ ] AC2: nessun segnale fa rete nel path caldo; `gh_email` opt-in default OFF; `npm_email` timeout-guarded.
- [ ] AC3: rotazione a 5MB scatta su tier node E perl E bash — verificato da
      `test_logger_rotation_crosstier.sh` (`archived_files >= 1` su ogni tier).
- [ ] AC4: cap 50MB effettivo su node-only (archivio consumato droppato) — stesso test.
- [ ] AC5: nessun abort sotto `set -euo pipefail` in alcun ramo (tutti i 21 findings coperti).
- [ ] AC6: `event_id` resta unico; nessuna perdita riga in alcun tier (no-regression durabilità).
- [ ] AC7: suite zero-loss + telemetria esistente resta verde (no-regression).
- [ ] AC8: valori `undefined`/`null`/CRLF normalizzati; JSON sempre valido (parse 100% righe).
- [ ] AC9: dopo rotazione, cursor-move → file fresco da cursor 0, archivio senza duplicati né
      perdita — verificato da `test_logger_rotation_crosstier.sh`.
- [ ] AC10: `devforge_batch_global` drena gli archivi del file globale (BLOCK-1) — verificato da
      `test_batch_global_archives.sh`.
- [ ] AC11: `event_id` unico al 100% sotto 50 hook concorrenti senza `flock` binario (Capability D)
      — verificato da `test_logger_event_id_concurrency.sh`; nessuna dipendenza dal binario `flock`.

---

## 8. Stima

- Umano: ~6 SP · Augmented: ~2.5 SP
- Rischio: MEDIO (telemetria critica) — mitigato da no-regression gate + parità esatta python3.

---

## 9. ADR sintetici

- **ADR-1**: rotazione cross-tier in **bash centralizzato** (non node/perl autonomo) — evita
  doppio sistema di lock e race col batcher; parità semantica con python3.
- **ADR-2**: `gh_email` **opt-in** — la rete non entra mai nel session-start di default; la
  capability esiste ("voglio tutto") ma protetta.
- **ADR-3**: nessun seeding cursore in rotazione — parità con python3; ri-upload idempotenti
  lato Lambda.
- **ADR-4**: identità nuova solo a session-start (pin in `user.json`), mai per-evento — costo
  pagato 1×/sessione.
- **ADR-5**: `os_domain` sempre **stringa vuota** (mai `null`) dove non applicabile (Unix) —
  semplicità di contratto JSON; il consumer interpreta `""` come "non applicabile/non letto"
  (WARN-5). Coerente con gli altri campi best-effort del bundle.
- **ADR-6**: rotazione **cursor-aware** (mv del cursore col rename) — supera la parità "solo
  rename" di python3 e corregge il bug latente di cursore stuck per TUTTI i tier; il path python3
  resta invariato nel codice ma beneficia indirettamente quando il cursore viene spostato dal
  prossimo evento bash/node/perl. Residuo race writer-vs-batcher = ri-upload idempotente, mai
  perdita (BLOCK-2).

## File modificati (manifest implementazione)

File di produzione toccati da questa PR (per drift detection — base = branch parent statusline):

- `lib/logger.sh` — Cap. A (identità), B (rotazione), D (event_id mkdir-lock)
- `lib/telemetry-upload.sh` — Cap. B (drain archivi globali), C (CRLF guard)
- `tests/run-all.sh` — wiring delle nuove suite

Test (Cap. A/B/C/D):
- `tests/zero-loss/unit/test_logger_event_id_concurrency.sh`
- `tests/zero-loss/unit/test_logger_identity_signals.sh`
- `tests/zero-loss/unit/test_logger_rotation_crosstier.sh`
- `tests/zero-loss/unit/test_batch_global_archives.sh`
- `tests/zero-loss/unit/test_logger_crlf_cursor.sh`
- `tests/zero-loss/integration/test_crossplatform_no_degradation.sh`
- `tests/test_telemetry_fixes.sh`
