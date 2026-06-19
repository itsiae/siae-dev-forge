# Design — Plugin Update Safety (auto-update affidabile, zero azione utente)

**Data:** 2026-06-19 · **Autore:** Lorenzo De Tomasi · **Stato:** in review
**Obiettivo utente (verbatim):** «tutti hanno l'ultima versione sempre, e non devono fare niente, tutto dietro le quinte»

## Contesto e scoperta chiave

L'aggiornamento "automatico" attuale è composto da DUE pezzi:
1. Un **meccanismo nativo Claude Code** (`autoUpdate: true`) — **già configurato org-wide** in
   `remote-settings.json` → `extraKnownMarketplaces.siae-devforge.autoUpdate: true` +
   `enabledPlugins`. A ogni startup Claude Code aggiorna marketplace+plugin e notifica. **Funziona**:
   ha portato i seat da 1.91.0 → 1.93.0 dietro le quinte.
2. Un **blocco custom** in `hooks/session-start:154-193` (git pull clone + `rm -rf` cache +
   `claude plugin update`) — **rotto e ridondante** col nativo.

**Conclusione**: l'obiettivo "tutti sempre l'ultima dietro le quinte" è già garantito dal nativo.
Il compito NON è costruirlo, ma **smettere di romperlo** e **renderlo osservabile**. Doc Claude Code:
`discover-plugins.md` (Configure auto-updates / managed scope / `/reload-plugins`).

## Difetti verificati empiricamente (2026-06-19)

Blocco custom session-start — 11 casi + 2 Windows (tutti confermati, vedi
`project_autoupdate_managed_broken` in auto-memory):
1. `claude plugin update` inerte su scope managed ("not installed at scope user", rc=0) — **by design** del CLI.
2. Falso successo: rc=0 → ramo `&&` → "✅ aggiornato. Riavvia" anche se non ha fatto nulla.
3. Stato corrotto: `rm -rf cache` cancella, il re-install non ripopola → installPath registry inesistente.
4. Zero telemetria update_*.  5. Nessun marker dedup → churn ogni sessione.
6. Background `( ) &` orfano (kill al ritorno hook).  7. Dipendenza `gh` + keyring timeout.
8. Prerelease non escluse (`--limit 1`, regex accetta `-rc`).  9. Detection legge il clone già git-pullato (versione eager ≠ effettiva).
10. Zero test sulla logica.  11. `sort -V` tratta `1.94.0-rc1` > `1.94.0` (non-semver, BSD+GNU).
W1. `pgrep` assente in Git Bash → net_run non killa i figli.  W2. `kill` MSYS inaffidabile su `.exe` nativi → timeout non enforced (rischio hang SessionStart su Windows).

Statusline (stessa radice, già mitigata a runtime dall'utente):
S1. `statusline/install.sh:12` deriva il path da `PLUGIN_ROOT` (= cache **versionata** `cache/.../X.Y.Z`).
    L'auto-update cambia la versione → il path scritto in `settings.json` non esiste più → statusline
    vuota in silenzio. **Verificato**: le skill girano da `cache/.../1.91.0` (cache versionata).
S2. Risovrascrittura: al prossimo `session-start`, install.sh vedrebbe il fix utente (path stabile) come
    "diverso" e lo riscriverebbe col path versionato (install.sh:41-44). Il fix runtime NON è durevole
    finché install.sh non è reso canonico.

## Approccio scelto — A+ "Trust-native, fail-safe" (Option Zero potenziato)

Affidarsi al nativo (già org-wide), eliminare il custom rotto, rendere durevoli gli artefatti e osservabile la convergenza. Nessun comando fragile/non-portabile, nessuna azione utente.

### Parte 1 — `hooks/session-start` (sostituzione blocco 154-193)
- **Rimuovere** completamente: `claude plugin update`, `rm -rf cache`, `git pull` in background, messaggi ✅/⚠️ fuorvianti.
- **Mantenere** solo un blocco *notice-only osservabile*:
  - `VERSION_STATUS` informativo basato sulla versione **effettiva** (no call-to-action manuale: il nativo aggiorna dietro le quinte). Fallback alla versione locale se la latest non è disponibile.
  - (best-effort) confronto vs ultima release **escludendo prerelease**. Degrada in silenzio senza `gh`.
  - **Telemetria** `plugin_version_observed` a ogni session-start → verifica convergenza org-wide su S3.

#### Algoritmo confronto versioni (chiude BLOCK1, sostituisce `sort -V` sui suffissi)
La latest è recuperata già senza prerelease, quindi entrambe le versioni sono `X.Y.Z` pure. Confronto
numerico per campi (no dipendenza da `sort -V`, no string-compare che sbaglia `1.9` vs `1.10`):
```bash
# gh: --exclude-pre-releases se supportato, con fallback a filtro --jq su isPrerelease
LATEST_TAG=$(net_run 5 gh release list --repo itsiae/siae-dev-forge --exclude-pre-releases \
  --limit 1 --json tagName --jq '.[0].tagName' 2>/dev/null \
  || net_run 5 gh release list --repo itsiae/siae-dev-forge --limit 20 \
       --json tagName,isPrerelease --jq 'map(select(.isPrerelease|not))|.[0].tagName' 2>/dev/null \
  || echo "")
# _ver_lt A B → vero se A < B, confronto numerico per campi (suffissi scartati)
_ver_lt() {
  local a="${1%%-*}" b="${2%%-*}" IFS=.
  local -a A=($a) B=($b); local i
  for i in 0 1 2; do
    local x=$((10#${A[i]:-0})) y=$((10#${B[i]:-0}))
    [ "$x" -lt "$y" ] && return 0; [ "$x" -gt "$y" ] && return 1
  done
  return 1   # uguali → non minore
}
```
Validazione tag con regex `^[0-9]+\.[0-9]+\.[0-9]+$` (post-strip `v`). Se la latest non è un semver
puro o `gh` fallisce → `status=unavailable`, nessun confronto.

#### Schema evento telemetria (chiude BLOCK2)
Event type `plugin_version_observed`, payload minimo:
```json
{"installed":"1.93.0","latest":"1.94.0","status":"behind"}
```
`status ∈ {up_to_date, behind, unavailable}`. `latest` = `null` quando `status=unavailable` (gh assente/fallito).
Emesso **sempre** a ogni session-start (anche in fallback, con `status=unavailable`) via `devforge_log`.
`installed` = versione **effettiva** (vedi sotto). Consumo a valle: query S3 `status=behind` per seat non convergenti.

#### Versione "effettiva" vs clone (chiude caso 9)
Il design legge la versione da `PLUGIN_ROOT/.claude-plugin/plugin.json`. Poiché il nativo fa git-pull
in-place del clone *prima* del confronto, questa può essere "eager". Si usa la versione registrata in
`~/.claude/plugins/installed_plugins.json` (versione realmente caricata da Claude) se presente e leggibile;
fallback a `plugin.json`. Niente call-to-action: il notice è informativo, quindi una versione eager al più
mostra "up_to_date" un avvio prima — accettabile, nessun rischio di azione errata.

#### Dedup notice (chiude minore #6)
La telemetria è emessa a ogni session-start (per osservabilità). Il **testo** del notice è informativo, non
un call-to-action: è accettabile mostrarlo a ogni sessione, nessun marker dedup necessario.

### Parte 2 — `statusline/install.sh` (root cause S1/S2)
- Calcolare un **path canonico STABILE**: preferire il clone marketplace
  `~/.claude/plugins/marketplaces/siae-devforge/statusline/devforge-statusline.sh` (invariante agli update,
  git pull in-place) **se il file esiste**; fallback a `PLUGIN_ROOT` solo se il clone (o il file) non esiste.
- Effetto: `DESIRED_COMMAND` non contiene mai la versione → idempotente e durevole, non risovrascrive il fix.
- **Fresh-install (chiude minore #5)**: su un seat al primissimo avvio il clone potrebbe non esistere ancora
  → fallback `PLUGIN_ROOT` accettabile; il path versionato si auto-corregge al primo session-start successivo
  al git-pull nativo (quando il clone esiste, install.sh lo riscrive stabile). Nessuna regressione vs oggi.

### Parte 3 — Test (`tests/run-all.sh`) — un test per AC (chiude BLOCK3)
- **T-AC1**: il path runtime di session-start NON esegue `claude plugin update` né `rm -rf` cache
  (grep assenza nei comandi eseguiti, non solo nel sorgente commentato).
- **T-AC2**: l'output additional_context NON contiene `"Esegui:"` né `"aggiornato a"` (no falso successo / call-to-action).
- **T-AC3**: con stub `gh` che ritorna una prerelease `X.Y.Z-rc1` come unica recente, il notice NON la propone;
  `_ver_lt 1.9.0 1.10.0` = vero (confronto numerico corretto).
- **T-AC4**: session-start emette un evento `plugin_version_observed` con `status` ∈ {up_to_date,behind,unavailable}
  e payload conforme allo schema; in fallback (gh assente) `status=unavailable`, `latest=null`.
- **T-AC5**: `install.sh` scrive in settings.json un path **non-versionato** (no `cache/.../<semver>/`);
  seconda esecuzione idempotente (non modifica un path stabile già presente).
- **T-AC6**: VERSION_STATUS presente (preserva test esistente riga 1002); suite esistente verde (no regressioni).
- **T-AC7**: `_ver_lt` e la derivazione del path canonico non usano `pgrep`/`kill` su processi nativi
  (verifica statica: il path update non invoca net_run con comandi da terminare forzatamente).

## Trade-off onesto

L'attivazione **nella sessione corrente** richiede un cold start naturale: un hook non può invocare
`/reload-plugins`. L'utente però **non fa nulla** — al prossimo avvio ha l'ultima versione. È il massimo
"dietro le quinte" raggiungibile senza azione utente, e già oggi è così (1.91→1.93 è avvenuto così).

- **Versione target del nativo (chiude minore #4)**: il meccanismo nativo `autoUpdate` aggiorna il clone
  marketplace via git pull e legge il `marketplace.json` *del clone* (su `main`, già a 1.93.0). Il
  `marketplace.json` nel working checkout del repo è a 1.90.2 (tracciato in `project_version_hygiene_followup`)
  ma è irrilevante per il rollout — non è la fonte che il nativo legge. Va comunque allineato in quel follow-up.
- **Seat senza remote-settings ancora sincronizzato (chiude minore #7)**: su un seat che non ha ancora
  ricevuto `remote-settings.json`, l'auto-update nativo non è attivo, ma il blocco custom era già rotto →
  **nessuna regressione** rispetto a oggi; la convergenza parte appena il remote-settings arriva.

## Criteri di accettazione
- AC1: nessun `claude plugin update` / `rm -rf cache` / update in background nell'hook.
- AC2: nessun messaggio di falso successo; nessun call-to-action manuale.
- AC3: notice basato sulla versione effettiva; prerelease escluse; nessun `sort -V` sui suffissi.
- AC4: telemetria `plugin_version_observed` emessa a ogni session-start.
- AC5: `install.sh` scrive sempre un path non-versionato (stabile) e non risovrascrive il fix.
- AC6: zero regressioni sulla suite esistente (test riga 1002 incluso); nuovi test verdi.
- AC7: cross-platform safe (nessuna dipendenza da pgrep/kill su processi nativi nel path update).

## Stima (SP doppia scala)
Umano: 5 · Augmented: 2. Domini: 1 (update safety). File: 3 (session-start, install.sh, run-all.sh).
