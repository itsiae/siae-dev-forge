# Task 02 — Implementa `setup_github_network()` + call site (TDD green)

**Goal:** far passare i test del Task 01 aggiungendo la funzione e la chiamata.

## File
- Modifica: `install.sh`

## 1. Definizione funzione
Inserire DOPO i `command -v claude/gh` (attualmente righe 25-26), PRIMA del blocco
`gh auth status` (riga 28-32):

```bash
# github DIRECT su rete SIAE: la CLI risolve lo shorthand github in SSH (bloccato)
# e gh/clone HTTPS vanno sul proxy corporate (irraggiungibile off-VPN). Idempotente.
setup_github_network() {
  local gh_domains="github.com,api.github.com,.github.com,codeload.github.com,objects.githubusercontent.com,uploads.github.com"
  case ",${NO_PROXY:-}," in *,github.com,*) : ;; *) export NO_PROXY="${NO_PROXY:+${NO_PROXY},}${gh_domains}" ;; esac
  case ",${no_proxy:-}," in *,github.com,*) : ;; *) export no_proxy="${no_proxy:+${no_proxy},}${gh_domains}" ;; esac
  git config --global url."https://github.com/".insteadOf "git@github.com:"
  git config --global http."https://github.com/".proxy ""
  info "Rete github configurata (HTTPS direct) — git config globale aggiornata"
}
```

## 2. Call site
Aggiungere la chiamata `setup_github_network` su una riga propria, SUBITO PRIMA
del commento `# Verifica autenticazione GitHub` (riga 28), cioè dopo i due
`command -v` dei prereq:

```bash
command -v gh &>/dev/null    || error "GitHub CLI (gh) non trovato. Installalo: https://cli.github.com"

# github DIRECT prima di ogni chiamata gh/git su rete SIAE
setup_github_network

# Verifica autenticazione GitHub
if ! gh auth status &>/dev/null; then
```

La definizione della funzione va posizionata PRIMA della call (es. subito dopo
i `info/warning/error` helper, riga ~17, oppure appena prima del call site —
purché definita prima di essere invocata in bash).

## Vincolo posizione
`setup_github_network` (definizione) prima della chiamata; chiamata prima di
`gh auth status`. Coerente con T2 del Task 01.

## Done quando
- `bash tests/test_installer_network_resilience.sh` → PASS=4 FAIL=0.
- `bash -n install.sh` pulito.
- Le altre chiamate (`gh repo view`, `marketplace add/update`, `gh api`)
  ereditano NO_PROXY perché esportato.
