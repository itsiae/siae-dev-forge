# Design — GitHub Network Resilience negli hook DevForge

- **Data:** 2026-06-12
- **Autore:** Lorenzo De Tomasi (+ DevForge)
- **Branch corrente:** feat/remove-discretionary-skip-bypasses
- **Tipo:** Fix di resilienza cross-cutting (network) — Medio-Alto
- **SP:** 4 (Umano) / 2 (Augmented) — scope ridotto da 7 a 3 hook dopo inventario reale

---

## 1. Contesto e problema

Alcuni hook DevForge effettuano chiamate `gh`/`git` di rete verso github.com.
Su macchine SIAE queste chiamate **bloccano la sessione**:

- **`session-start` impiega ~744s (~12 min)** prima del primo prompt (misurato).
- Ogni singola chiamata `gh`/`git` esposta resta appesa **~30s** sull'`i/o
  timeout` del proxy SIAE.

### Inventario REALE delle call di rete (ground-truth, verificato via grep)

Una prima stima parlava di "~48 call su 7 hook": era **errata** — contava
riferimenti stringa `gh` dentro heredoc letterali e token-matcher su
`TOOL_COMMAND`, non chiamate eseguite. Inventario corretto:

| Hook | Call di rete REALI | Guardia attuale |
|------|--------------------|------------------|
| `session-start` | `gh release list` (1) | **perl-fork 5s** (:155-157) |
| `session-start` | `gh repo view` ×2, `gh pr list` ×2 (branching + merge-detect) | **nessuna → ESPOSTE** |
| `session-start` | `git pull` (marketplace) | in `( ) &` async, non blocca il main flow |
| `pr-release-gate` | `git fetch origin main` (:49), `gh pr list` (:54), `gh api` (:88) | **nessuna → ESPOSTE** |
| `post-commit-review` | `gh pr view` ×3 (:100/102, :167/169, :218) | `timeout 3`/else-bare → **bare su macOS** |
| `pr-gate` | 0 | `gh release list`:248 è dentro heredoc `INSTRUCTIONS_EOF` |
| `pr-premortem-gate` | 0 | solo token-match su `TOOL_COMMAND` |
| `pr-blind-review-gate` | 0 | solo token-match |
| `review-evidence` | 0 | solo match su payload PreToolUse |

**Scope reale: 3 hook** (`session-start`, `pr-release-gate`, `post-commit-review`).

### Causa radice (doppia, verificata empiricamente)

1. **Routing proxy errato.** `NO_PROXY` sulle macchine SIAE include
   `*.siae.it`, `anthropic.com`, `claude.ai`, `*.amazonaws.com` ma **NON
   github.com**. Quindi `gh`/`git` instradano github attraverso il proxy
   corporate (`10.255.1.241:8080`) che non raggiunge github → `dial tcp ...:
   i/o timeout` dopo ~30s per chiamata.
   - Verifica: `NO_PROXY="github.com,api.github.com,.github.com" gh release list ...`
     → risponde `v1.86.0` in **0s** (vs 30s con proxy).
   - github.com è **DIRECT** nel PAC SIAE (memory `github-proxy-bypass`).

2. **Timeout non uniforme e non garantito.** `session-start` protegge solo la
   prima call (`gh release list`) con una catena `timeout`/`gtimeout`/`perl`-fork:
   su macOS BSD `timeout`/`gtimeout` sono assenti → si usa il ramo **perl** (5s).
   Ma le call **realmente responsabili del blocco** — `gh repo view`×2 e
   `gh pr list`×2 (branching compliance + merge-detect) — **non hanno alcuna
   guardia** (bare). Idem `pr-release-gate` (git fetch/gh pr list/gh api) e
   `post-commit-review` (`gh pr view` con `timeout 3`/else-bare → bare su macOS).
   Inoltre il perl-fork è fragile: dipende dalla presenza di perl (deprecato da
   Apple in macOS Catalina+) e `kill TERM` non garantisce la terminazione di un
   processo Go come `gh`. Serve un timeout **uniforme, portabile e con
   `SIGKILL` finale** su tutte le call di rete.

### Requisito utente (letterale)

> La connessione con GitHub non deve andare **MAI** in timeout/blocco, sia su
> OS (macOS/Linux) che su **Windows**.

### Vincoli

- **Cross-platform.** Gli hook girano come script bash anche su Windows, via
  il polyglot `hooks/run-hook.cmd` → Git Bash (`C:\Program Files\Git\bin\bash.exe`).
  Confermato in `docs/plans/2026-04-13-telemetry-zero-loss-design.md:1013`.
- **Zero admin / zero install.** Non si può assumere `coreutils` (`gtimeout`)
  né modificare i profili shell di ogni dev. La soluzione vive nel plugin.
- **No-regression.** Le call protette devono restituire lo stesso output in caso
  di successo; in caso di timeout/errore degradano a output vuoto + rc non-zero,
  già gestito dai `|| echo ""` esistenti ai call-site.

---

## 2. Decisione architetturale (ADR)

**Approccio scelto: C — `lib/net-timeout.sh` esteso (NO_PROXY-github + net_run),
sourced dai 3 hook con call reali.** Due layer ortogonali, entrambi portabili:

| Layer | Meccanismo | Garanzia |
|-------|-----------|----------|
| **Correttezza/velocità** | Arricchimento idempotente di `NO_PROXY`/`no_proxy` con i domini github, **esportato** → ereditato da ogni sottoprocesso `gh` **e** `git` dell'hook | github torna DIRECT → call in ~1s |
| **Garanzia "mai blocco"** | `net_run <budget> <cmd...>` — timeout hard portabile (bash puro, niente `timeout` binary) attorno alle call critiche | la call non appende mai oltre il budget, anche se la rete è giù |

### Alternative scartate

- **A — Wrapper `devforge_gh` solo gh:** non copre le chiamate `git`
  (es. `git pull` in `session-start:168`). Scartato.
- **B — NO_PROXY a livello OS + coreutils timeout:** non soddisfa "mai blocco"
  (offline appende ancora), richiede admin/install su Windows, e l'export in un
  hook non si propaga agli altri (ogni hook è subprocess fresco con l'env di
  Claude Code, non di session-start). Scartato.

### Perché NO_PROXY e non `env -u proxy`

`env -u HTTP_PROXY ...` disabilita il proxy per **tutta** la call; arricchire
`NO_PROXY` è **chirurgico** (bypassa solo github, eventuali altri host restano
proxati) ed è idiomatico per Go (gh) e libcurl (git), che entrambi onorano
`NO_PROXY` via suffix-match.

---

## 3. Componenti

### 3.1 `lib/net-timeout.sh` (esteso)

Il file esiste già con `net_run` (testato 4/4). Si aggiunge **al top del file**,
eseguito una volta per ogni `source`, un blocco idempotente di hardening NO_PROXY:

```bash
# --- DevForge: github DIRECT (fuori dal proxy) ---
# Idempotente + exported: ereditato da gh (Go) e git (libcurl), che onorano
# entrambi NO_PROXY via suffix-match. Copre i domini github reali.
_devforge_no_proxy_github() {
    local domains="github.com,api.github.com,.github.com,codeload.github.com,objects.githubusercontent.com,uploads.github.com"
    case ",${NO_PROXY:-}," in
        *,github.com,*) return 0 ;;   # già presente: no-op
    esac
    export NO_PROXY="${NO_PROXY:+${NO_PROXY},}${domains}"
    export no_proxy="${no_proxy:+${no_proxy},}${domains}"
}
_devforge_no_proxy_github
```

Esistente, invariato: `net_run <secs> <cmd...>` → entro budget rc reale + stdout;
oltre budget rc=124 + stdout parziale + albero processi terminato (`pgrep -P`
guarded → su Git Bash, dove `pgrep` manca, termina il pid diretto: `gh`/`git`
sono figli diretti, nessun nipote da reapare).

### 3.2 I 3 hook con call reali — wiring

Solo i 3 hook con call di rete reali vengono modificati. Per ciascuno:

1. **Source del lib**, da posizionare **PRIMA della prima chiamata `gh`/`git`
   di rete** dell'hook (il source applica già il fix NO_PROXY — layer 1):
   ```bash
   source "${PLUGIN_ROOT}/lib/net-timeout.sh" \
       || { echo "[devforge] net-timeout.sh non sourcabile" >&2; }
   ```
   Punti di inserimento esatti (BLOCK-3):
   - `session-start`: dopo `logger.sh` (:19), prima del blocco version-check (:146).
   - `pr-release-gate`: dopo `logger.sh` (:34), **prima della `git fetch` a :49**.
   - `post-commit-review`: a **top-level incondizionato**, NON dentro i branch
     `if/elif` (il logger lì è sourcato condizionalmente :46/:96/:214).

2. **Avvolgere le call di rete reali** con `net_run <budget>`:
   ```bash
   LATEST_TAG=$(net_run 5 gh release list --repo ... --json tagName --jq '...' || echo "")
   ```

Budget per tipologia (config via env opzionale `DEVFORGE_NET_BUDGET`, default sotto):

| Tipo call | Budget default |
|-----------|----------------|
| `gh release/repo/pr list/pr view` (read) | 5s |
| `gh pr list` merge-detect, `gh api` | 8s |
| `git fetch/pull/ls-remote` | 8s |

Call da avvolgere, per hook (ground-truth sezione 1):

| Hook | Call → `net_run` |
|------|-------------------|
| `session-start` | `gh release list` (sostituisce la catena perl), `gh repo view` ×2, `gh pr list` ×2 |
| `pr-release-gate` | `git fetch` (:49), `gh pr list` (:54), `gh api` (:88) |
| `post-commit-review` | `gh pr view` ×3 (:100, :167, :218 — rimuovere il `timeout 3`/else-bare) |

`pr-gate`, `pr-premortem-gate`, `pr-blind-review-gate`, `review-evidence`:
**nessuna modifica** (0 call di rete reali).

### 3.3 Rimozione guardie obsolete

- `session-start:151-160`: rimuovere l'intera catena `if timeout / elif gtimeout
  / elif perl / else`; sostituire con `net_run 5 gh release list ...`.
- `post-commit-review:100-102, 167-169, 218-220`: rimuovere i `timeout 3`/
  else-bare; sostituire con `net_run 5 gh pr view ...`.

---

## 4. Flusso dati

```
hook avvio
  └─ source lib/net-timeout.sh
       └─ _devforge_no_proxy_github  →  export NO_PROXY+=github (idempotente)
  └─ net_run 5 gh release list ...
       ├─ gh eredita NO_PROXY → github DIRECT → risponde ~1s → rc reale + stdout
       └─ (rete giù) → budget 5s scaduto → kill albero → rc=124 + stdout vuoto
            └─ `|| echo ""` al call-site → hook prosegue, nessun blocco
```

---

## 5. Gestione errori

| Scenario | Comportamento |
|----------|---------------|
| github raggiungibile (caso normale) | call ~1s, rc reale, output completo |
| rete giù / DNS down / offline | net_run rc=124 dopo budget, stdout vuoto, hook prosegue |
| `NO_PROXY` già contiene github | `_devforge_no_proxy_github` no-op (idempotente) |
| Git Bash senza `pgrep` | `_net_kill_tree` termina solo pid diretto (sufficiente per gh/git) |
| lib non sourcabile | guard **esplicito** con warning su stderr (no `\|\| true` silente): `source ... \|\| { echo "[devforge] net-timeout.sh non sourcabile" >&2; }`. L'hook prosegue ma la rottura del path è visibile in CI/log. |

---

## 6. Testing

Estendere `tests/lib/test_net_timeout.sh` (già 4/4) e aggiungere copertura
dedicata:

- **T-NP1** `_devforge_no_proxy_github` aggiunge github a NO_PROXY vuoto.
- **T-NP2** idempotenza: secondo invoke non duplica.
- **T-NP3** preserva i domini esistenti (`*.siae.it` ecc.).
- **T-NP4** export effettivo (variabile visibile a subprocess).
- **T-WIRE** per i 3 hook con call reali: test strutturale che NESSUNA call
  `gh`/`git` di rete resti non avvolta da `net_run`. Il grep deve **escludere
  le righe dentro heredoc letterali** (`<< 'INSTRUCTIONS_EOF'` ecc.) e i
  token-matcher (`devforge_cmd_has_subcommand`, `case "$TOOL_COMMAND"`), che
  non sono bash eseguito — altrimenti falso positivo su `pr-gate:248`. Limitare
  il match a call in command-substitution `$(...)`/backtick reali.
- **T-NOREG** il conteggio test no-regression hook esistente va aggiornato se
  cambia (memory `pr252-test-count-drift`).
- **Smoke cross-platform**: il job `windows-smoke` (già previsto in telemetry
  CI) verifica che `net-timeout.sh` sorgi e `net_run` cappi su Git Bash.

Verifica empirica E2E: ri-cronometrare `session-start` → deve scendere da ~744s
a <10s anche con proxy attivo e github DIRECT.

---

## 7. Criteri di accettazione

1. ✅ Nessuna chiamata `gh`/`git` di rete nei 3 hook interessati può bloccare
   oltre il proprio budget (max 8s), su macOS, Linux e Git Bash/Windows.
2. ✅ Con `NO_PROXY` privo di github, il source di `net-timeout.sh` lo aggiunge
   in modo idempotente ed esportato → `gh`/`git` tornano DIRECT.
3. ✅ `session-start` completa in <10s con rete normale (vs ~744s attuali).
4. ✅ Nessuna regressione: call di successo restituiscono lo stesso output;
   guardia `timeout`/`else` rimossa da session-start.
5. ✅ `tests/lib/test_net_timeout.sh` esteso, tutti PASS; test strutturale
   anti-regressione sui 3 hook interessati.
6. ✅ `lib/net-timeout.sh` + test tracciati in git (oggi untracked).

---

## 8. Fuori scope

- Modifica dei profili shell OS o del PAC SIAE (resta config esterna).
- Retry/backoff sulle call github (oggi best-effort; non richiesto).
- Chiamate di rete non-github (S3/telemetry upload ha già il proprio path).
