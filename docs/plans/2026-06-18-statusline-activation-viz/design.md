# Design — Visualizzazione attivazione plugin + durabilità telemetria

**Data:** 2026-06-18
**Branch:** feat/statusline-python-and-update-notice (estende PR #339)
**Complessità:** Media-Alta (5 item, 2 file critici: statusline + logger.sh)
**Goal utente:** "non possiamo avere degradazione della telemetria" → durabilità preservata anche senza python3/node.

## Contesto (verificato)

- `statusline/devforge-statusline.sh`: label riga 1 è statico `🔨 DevForge`; versione mostrata solo nell'update notice; cache git è **globale** `~/.claude/.devforge-git-cache` → contaminazione cross-repo (osservata).
- `lib/logger.sh:116-187` `_devforge_lock_append`: path di scrittura telemetria `python3 (flock+fsync)` → `node (O_APPEND+fsync)` → **`bash (mkdir-lock, NO fsync)`**. Solo il path bash perde durabilità. Sentinel `~/.claude/.devforge-no-fsync-warned` + evento `telemetry_degraded` (reason `no_fsync_interpreter`) già emessi.
- Test zero-loss esistenti **asseriscono** l'emissione di `telemetry_degraded` nel path bash (`test_writepath_zeroloss_crossplatform.sh` T3b/9b, `test_json_field_portable.sh` T5) → D2 deve restare additivo.

## Item & ADR

### D2 — Eliminazione degradazione telemetria (tier perl con fsync reale)
**Goal forte utente: "non possiamo avere degradazione".** `sync` da solo RIDUCE ma non elimina (coarse, no fsync per-fd) → insufficiente. La soluzione che ELIMINA la degradazione è aggiungere un **tier `perl` con fsync reale** prima del fallback bash.

- **Fatto verificato:** `perl` è presente di default su macOS (`/usr/bin/perl`) e su quasi tutte le distro Linux, e fa fsync reale via `IO::Handle::sync` (testato: append + `$fh->sync` OK). `dd conv=fsync` funziona ma NON sa appendere portabilmente (`oflag=append` assente su BSD/macOS) → scartato.
- **ADR-D2:** in `_devforge_lock_append`, nuova catena di durabilità:
  `python3 (flock+fsync)` → `node (O_APPEND+fsync)` → **`perl (append + IO::Handle::sync)`** → `bash + sync 2>/dev/null||true` (ultima spiaggia).
  Con uno qualsiasi di python3/node/perl la durabilità **fsync per-file** è garantita → degradazione azzerata in ~100% degli ambienti reali.
- **Tier perl (forma):**
  ```bash
  if command -v perl >/dev/null 2>&1; then
    if printf '%s' "$line" | perl -e 'use IO::Handle; open(my $fh,">>",$ARGV[0]) or exit 1; local $/; my $d=<STDIN>; print $fh $d or exit 1; $fh->flush or exit 1; $fh->sync or exit 1; close($fh) or exit 1; exit 0' "$file" 2>/dev/null; then
      _fsync_ok=1
    fi
  fi
  ```
  Se `_fsync_ok=1` → durabile, `return 0` **senza** emettere `telemetry_degraded` (non è degradato!).
- **Ultima spiaggia (no python3+node+perl, patologico):** `printf >> "$file"; sync 2>/dev/null || true` + sentinel + evento `telemetry_degraded` (reason `no_fsync_interpreter` resta valido). Onestà: qui `sync` è coarse (flush OS-wide, no garanzia write-cache hardware) → best-effort; C lo segnala.
- **Esclusione (WARN-7a):** path `DEVFORGE_FORCE_BASH_FALLBACK` (logger.sh:75-83) è test-only → NON toccato.
- **Constraint snippet perl (WARN iter2):** legge stdin con `local $/` (slurp); i payload DevForge sono JSON puro UTF-8 senza null byte → ok. La directory del file è sempre pre-creata dai path a monte (`mkdir -p`).
- **AC-D2:**
  1. python3+node assenti, perl presente → usa perl, scrittura durabile (fsync), `telemetry_degraded` **NON** emesso.
  2. python3+node+perl tutti assenti → bash+`sync`, `telemetry_degraded` emesso + sentinel scritto (path patologico).
  3. La riga è sempre scritta nel file in ogni tier (no-regression zero-loss).
  4. Tier python3 e node invariati (no-regression: i loro test esistenti passano).
  5. **GATE BLOCCANTE pre-merge:** `test_writepath_zeroloss_crossplatform.sh` T3b e T9b aggiornati per mascherare anche `perl` (oltre python3+node) — altrimenti diventano rossi perché il path ora è durabile via perl. La suite zero-loss deve restare verde.

### A — Versione sempre visibile (riga 1)
- **ADR-A:** label diventa `🔨 DevForge v<VER>` quando `<VER>` è semver. Fonte: `basename "$PLUGIN_ROOT_SL"` (già calcolato, riga 132). Regex semver esatto (WARN-4): `^[0-9]+\.[0-9]+\.[0-9]+$`. Se non-semver → fallback B.
- **AC-A:** versione semver → riga 1 mostra `🔨 DevForge vX.Y.Z`.

### B — Indicatore dev-mode (riga 1)
- **ADR-B:** se `basename "$PLUGIN_ROOT_SL"` non matcha `^[0-9]+\.[0-9]+\.[0-9]+$` (repo, non cache versionata) → label `🔨 DevForge (dev)` (nessuna versione). A e B sono mutuamente esclusivi su un singolo `if/else`.
- **AC-B:** basename non-semver → riga 1 mostra `🔨 DevForge (dev)`; semver → mostra la versione (no "(dev)").

### #1 — Fix cache git per-repo (bug correttezza)
- **ADR-#1:** `CACHE_FILE` keyed per cwd: `CACHE_FILE="${DEVFORGE_DIR}/.devforge-git-cache-${KEY}"` con `KEY="$(printf '%s' "$PWD" | cksum | tr -dc '0-9' | cut -c1-12)"` (`cksum` POSIX). Elimina la contaminazione cross-repo, niente thrash.
- **AC-#1:** due cwd diversi usano file cache distinti; il branch in cache di un repo non appare mai per un altro cwd.

### C — Indicatore fallback telemetria (riga 1)
- **ADR-C:** se esiste il sentinel `~/.claude/.devforge-no-fsync-warned`, mostrare un pallino `🟡` nel label. **Posizione esatta (WARN-7b):** subito dopo la versione/`(dev)` e prima del primo `|` (cioè prima di `[SDLC_PHASE]`/branch). Composizione label iniziale = `🔨 DevForge {v<VER>|(dev)}{ 🟡 se sentinel}`. In modalità sana (python3/node con fsync) nessun pallino → rendering normale pulito. Non è allarme rosso di data-loss: con D2 la durabilità è ragionevolmente preservata; il giallo segnala "fallback, installa python3/node per modalità ottimale".
- **Co-presenza con warning python3 #339 (WARN-6):** sono complementari, NON sopprimere nessuno dei due. `python3 assente` (riga 2) = python3 non installato (impatta anche token-stats); `🟡` (riga 1) = path bash di `_devforge_lock_append` attivato (può accadere anche con python3 presente-ma-fallito + node assente). Scenario co-presenza: python3 assente → entrambi attivi (riga 1 "qualcosa non ottimale", riga 2 "cosa esattamente").
- **AC-C:** sentinel presente → riga 1 mostra `🟡` dopo il label; assente → nessun pallino.

### Impatto test esistenti (WARN-7b)
Aggiungere la versione al label cambia il testo iniziale di `LINE1`. Verificare che `tests/statusline/test_statusline_python_warning.sh` e `test_statusline_plugin_update.sh` (che asseriscono su riga 2, non sul label esatto) non regrediscano; se qualche asserzione fa match esatto sul label `🔨 DevForge` senza versione, aggiornarla al nuovo formato.

## File toccati
- `lib/logger.sh` (D2 — tier perl + sync ultima spiaggia)
- `statusline/devforge-statusline.sh` (A, B, #1, C)
- `tests/zero-loss/unit/test_logger_perl_fsync.sh` (nuovo, D2)
- `tests/zero-loss/unit/test_writepath_zeroloss_crossplatform.sh` (aggiorna T3b/T9b: maschera anche perl)
- `tests/statusline/` (test A/B/#1/C)

## Vincoli
- bash 3.2 compatibile, `set -euo pipefail` safe, additivo (no regressione rendering), nessuna call di rete.
- `cksum`, `sync` POSIX (presenti su macOS/Linux). Fallback graceful se assenti (improbabile): cache globale come oggi / no sync.

## Testing
- `test_logger_perl_fsync.sh` (nuovo): maschera python3+node (perl presente) → verifica scrittura durabile via perl + `telemetry_degraded` **NON** emesso (AC-D2.1). Maschera python3+node+perl → bash+sync, shim `sync` invocato (marker) + `telemetry_degraded` emesso (AC-D2.2).
- **Aggiornamento test zero-loss esistenti (NECESSARIO, non regressione ma cambio-comportamento intenzionale):** `test_writepath_zeroloss_crossplatform.sh` (T3b, T9b) e `test_json_field_portable.sh` (T5) oggi mascherano solo python3+node e asseriscono `telemetry_degraded`. Con il tier perl quel sentiero diventa durabile (perl) → l'evento NON è più emesso. Vanno aggiornati per mascherare **anche perl** per raggiungere il path patologico atteso. Il comportamento migliora (meno scenari degradati); l'aggiornamento riflette la nuova realtà, documentato esplicitamente.
- `test_statusline_version_label.sh`: PLUGIN_ROOT semver → `v<ver>`; non-semver → `(dev)`.
- `test_statusline_git_cache_perrepo.sh`: due cwd → due file cache distinti, nessuna contaminazione.
- `test_statusline_telemetry_health.sh`: sentinel presente → `🟡`; assente → no pallino.
- Re-run suite zero-loss completa (verifica no-regression sui tier python3/node).

## Stima SP
- D2: Umano ~2 · Augmented ~1
- A+B: Umano ~1 · Augmented ~0.5
- #1: Umano ~1 · Augmented ~0.5
- C: Umano ~0.5 · Augmented ~0.25
- **Totale: Umano ~4.5 · Augmented ~2.25**

## Out of scope
- Auto-install python3/node (roadmap separata in logger.sh).
- "Update disponibile" da marketplace remoto (richiede rete).
