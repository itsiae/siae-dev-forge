# Design — Installer network resilience (github su rete SIAE)

**Data:** 2026-06-13 · **Topic:** install.sh + README resilienti alla rete SIAE
**Relazione:** estende il tema "network resilience github" di PR #318 al path di
installazione/recovery del plugin.

## Contesto e problema

`install.sh` e la doc registrano il marketplace via **shorthand github**
(`itsiae/siae-dev-forge`). La CLI Claude Code risolve lo shorthand in **SSH**
(`git@github.com:`), che sulla rete SIAE è **bloccato** (`Permission denied
(publickey)`). Inoltre `gh auth status` / `gh repo view` / `gh api` e il clone
HTTPS instradano sul **proxy corporate** `10.255.1.241:8080` che **off-VPN è
irraggiungibile** (timeout 75s).

Conseguenza riprodotta: **prima installazione** e **recovery da cache-miss**
(`claude plugin marketplace update`) falliscono per ogni dev SIAE.

### Evidenza empirica (validata in questa sessione)
- `marketplace update` (sorgente shorthand→SSH) → fallisce SSH; dopo `insteadOf`
  + `http.<github>.proxy ""` → **✔ Successfully updated** (clone HTTPS direct).
- Clone HTTPS standalone con proxy morto in env + `-c http.https://github.com/.proxy=`
  → **direct, 3s, exit 0** (prova che l'override per-URL batte il proxy off-VPN).

## Decisione (ADR)

**Approccio scelto:** funzione `setup_github_network()` in `install.sh`, invocata
nei prerequisiti **prima** di qualsiasi chiamata `gh`/`git`/`marketplace`.

Scartati:
- *Solo URL HTTPS*: evita SSH ma non il proxy morto off-VPN (clone si appende).
- *Config git scoped (GIT_CONFIG_GLOBAL temp)*: niente side-effect ma il
  **recovery futuro** del dev (marketplace update su cache-miss) non avrebbe la
  config → problema ricorrente. Non risolve la causa.

## Componenti

### 1. `install.sh` — `setup_github_network()` (nuova, idempotente)
```bash
setup_github_network() {
  # github DIRECT: NO_PROXY per le call gh (auth/repo/api).
  # Append-safe su entrambe le var (NO_PROXY e no_proxy indipendenti) —
  # stessa forma di _devforge_no_proxy_github in lib/net-timeout.sh.
  local gh_domains="github.com,api.github.com,.github.com,codeload.github.com,objects.githubusercontent.com,uploads.github.com"
  case ",${NO_PROXY:-}," in *,github.com,*) : ;; *) export NO_PROXY="${NO_PROXY:+${NO_PROXY},}${gh_domains}" ;; esac
  case ",${no_proxy:-}," in *,github.com,*) : ;; *) export no_proxy="${no_proxy:+${no_proxy},}${gh_domains}" ;; esac
  # SSH→HTTPS: la CLI converte lo shorthand github in SSH (bloccato su rete SIAE)
  git config --global url."https://github.com/".insteadOf "git@github.com:"
  # github HTTPS DIRECT: bypassa il proxy corporate (irraggiungibile off-VPN)
  git config --global http."https://github.com/".proxy ""
  info "Rete github configurata (HTTPS direct) — git config globale aggiornata"
}
```
- Chiamata **subito dopo** la verifica `command -v claude/gh` (riga ~26), prima
  di `gh auth status`.
- `git config` idempotenti per natura (riscrivono la stessa chiave); NO_PROXY
  guardato per dominio (no duplicati).
- **Annuncio esplicito** all'utente (side-effect git globale visibile, non silente).

**Decisione riuso vs duplicazione (risolve spec-review MEDIO):** la logica NO_PROXY
**duplica** `_devforge_no_proxy_github` di `lib/net-timeout.sh` invece di
sourceizzarlo. Motivo: `install.sh` deve essere **self-contained** — viene
eseguito via `bash <(gh api .../install.sh)` o da copia, **prima** che il repo/
plugin sia presente sul disco, quindi `lib/net-timeout.sh` **non è disponibile**
a install-time. La sintassi `no_proxy` è allineata alla forma append-safe di
`net-timeout.sh` per evitare deriva semantica.

**Rollback (spec-review BASSO):** le 2 chiavi git globali si rimuovono con
`git config --global --unset url."https://github.com/".insteadOf` e
`git config --global --unset http."https://github.com/".proxy`. Documentato in README.

### 2. Call sites
Nessun cambio a `marketplace add` (riga 146): con `insteadOf` lo shorthand
funziona via HTTPS. Opzionale ma escluso per minimalità: cambiare l'URL.

### 3. `README.md` — sezione "Installazione" (righe ~57-75)
**(corregge spec-review ALTO: il vecchio target "riga ~160" era errato — a
README:160 c'è la tabella skill; il comando `gh api ... base64 -d` è in
`install.sh:160`, non nel README.)**
- riga ~63 (`/plugin marketplace add itsiae/siae-dev-forge`): aggiungere nota
  "su rete SIAE esegui prima `install.sh`, che configura github DIRECT
  (NO_PROXY + SSH→HTTPS); altrimenti l'add via SSH/proxy fallisce".
- aggiungere micro-sezione "Rete SIAE / rollback" con i 2 comandi `--unset`.
- `install.sh` riga ~160 (commento update via `gh api`): nessuna modifica
  necessaria — gira dopo `setup_github_network` (NO_PROXY già esportato).

## Comportamento on/off-VPN
- **Off-VPN:** NO_PROXY+no-proxy → gh e clone DIRECT (validato).
- **On-VPN:** github è DIRECT nel PAC; NO_PROXY/no-proxy sono no-op innocui.

## Error handling
- `setup_github_network` non deve mai abortire l'install: `git config` su git
  presente non fallisce; assenza di git è già coperta (git è prereq di gh/clone).
- Mantiene `set -euo pipefail` esistente.

## Testing
- **Empirico (fatto):** clone HTTPS direct sotto proxy morto (3s); recovery
  marketplace update OK post-config.
- **Strutturale (PR):** test che (a) `setup_github_network` esista e sia chiamata
  prima di `gh auth status`, (b) idempotenza NO_PROXY (no duplicati github),
  (c) `bash -n install.sh` pulito.

## Criteri di accettazione
1. Dev fresco **off-VPN** completa `install.sh` senza hang SSH/proxy.
2. Recovery `claude plugin marketplace update siae-devforge` clona HTTPS direct.
3. On-VPN invariato (nessuna regressione).
4. `setup_github_network` idempotente; side-effect git globale annunciato.
5. README allineato (no comandi che assumono SSH/proxy raggiungibile).

## Stima
- **SP (Umano):** 2 · **SP (Augmented):** 0.5
- Complessità MEDIA: 1 funzione + call site + 2 ritocchi README + 1 test strutturale.
