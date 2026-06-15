# Guida isolamento per-persona — Account condivisi Claude Code

**Data:** 2026-06-14
**Autore:** DevForge Task 08 (feat/identity-rootcause-crossplatform)
**Stato:** Handover per team operator/infra

---

## Problema

Su macchine Linux condivise (server di sviluppo, VM di team, runner CI) più developer
usano lo stesso OS user o lo stesso account Anthropic SSO. Claude Code legge l'identità
autenticata da `~/.claude.json` → `oauthAccount.emailAddress`.

Se tutti i developer lanciano Claude Code con lo stesso `$HOME` (o dallo stesso account OS),
la telemetria DevForge registra la stessa `auth_email` per eventi di developer diversi:
attribuzione impossibile downstream.

---

## Diagnosi rapida

Usa `scripts/diagnose-identity.sh` (script standalone, nessun side-effect sugli hook):

```bash
bash scripts/diagnose-identity.sh
```

L'output è una riga `chiave=valore` per ogni segnale, più un `VERDICT`:

| VERDICT | Significato |
|---|---|
| `ISOLATED` | `CLAUDE_CONFIG_DIR` è settato, onorato, e il file esiste: ogni persona ha la propria identità |
| `SHARED-DEGENERATE` | Si legge `~/.claude.json` globale: attribuzione condivisa, identità non disambiguabile |
| `NO-AUTH` | Nessuna sessione autenticata trovata (bedrock/API key, o file mancante) |

---

## Soluzione raccomandata — CLAUDE_CONFIG_DIR per-persona

Ogni developer aggiunge nel proprio profilo shell (`~/.bashrc` / `~/.zshrc` / `~/.profile`):

```bash
export CLAUDE_CONFIG_DIR="$HOME/.claude-$(whoami)"
```

In questo modo Claude Code (se onora la variabile) legge `~/.claude-<username>/.claude.json`,
che contiene le credenziali OAuth dell'account Anthropic di quella persona specifica.

**Verifica:**

```bash
bash scripts/diagnose-identity.sh
# Atteso: VERDICT: ISOLATED
```

---

## Fallback obbligatorio se CLAUDE_CONFIG_DIR non è onorato

Il task-00 del piano verifica empiricamente se Claude Code onora `CLAUDE_CONFIG_DIR`.
Se l'esito è negativo (VERDICT resta `SHARED-DEGENERATE` anche con la var settata),
usare uno dei due fallback:

### Fallback A — HOME isolato per-persona

```bash
HOME=/srv/devforge-personas/$REAL_USER claude code ...
```

Ogni persona ha un `HOME` separato → `~/.claude.json` separato → identità separata.
Richiede che l'amministratore di sistema crei le home-directory per-persona in `/srv/devforge-personas/`.

### Fallback B — Sotto-account OS separati

Creare un account Linux distinto per developer, così l'isolamento è a livello OS:
ogni account ha il proprio `$HOME` e la propria sessione Claude Code.

---

## Come verificare l'isolamento con lo script

### Scenario 1 — ISOLATED (atteso su setup corretto)

```bash
export CLAUDE_CONFIG_DIR="$HOME/.claude-$(whoami)"
mkdir -p "$CLAUDE_CONFIG_DIR"
# (dopo il login Claude Code, il file viene creato da Claude Code stesso)
bash scripts/diagnose-identity.sh
```

Output atteso:
```
CLAUDE_CONFIG_DIR=/home/mario/.claude-mario
claude_json_path=/home/mario/.claude-mario/.claude.json
claude_json_exists=yes
oauth_email=mario.rossi@siae.it
CLAUDE_CONFIG_DIR onorato=si
VERDICT: ISOLATED
```

### Scenario 2 — SHARED-DEGENERATE (situazione da correggere)

```bash
unset CLAUDE_CONFIG_DIR
bash scripts/diagnose-identity.sh
```

Output atteso (su macchina condivisa con account di team):
```
CLAUDE_CONFIG_DIR=
claude_json_path=/home/shared/.claude.json
oauth_email=team-account@siae.it
CLAUDE_CONFIG_DIR onorato=no
VERDICT: SHARED-DEGENERATE
```

### Scenario 3 — NO-AUTH (runner CI o bedrock)

```bash
bash scripts/diagnose-identity.sh
```

Output atteso su ambiente senza login Anthropic OAuth:
```
claude_json_exists=no
oauth_email=
VERDICT: NO-AUTH
```

In questo caso la telemetria DevForge usa `auth_email=""` (stringa vuota) e la
downstream developer-telemetry attribuisce l'evento via `git_local_email` o `os_user`.

---

## Sicurezza

Lo script non stampa mai il contenuto del file `~/.claude.json` in chiaro.
L'`oauth_account_uuid` è mascherato: vengono mostrati solo i primi 8 caratteri seguiti da `…`.

---

## Riferimenti

- Design: `docs/plans/2026-06-14-dev-identity-rootcause-crossplatform-design.md`
- Piano: `docs/plans/2026-06-14-dev-identity-rootcause-crossplatform/overview.md`
- Script: `scripts/diagnose-identity.sh`
- Test: `tests/zero-loss/unit/test_diagnose_identity.sh`
- Handover consumer: `docs/handover/2026-06-08-attribution-determinism-fields.md`
