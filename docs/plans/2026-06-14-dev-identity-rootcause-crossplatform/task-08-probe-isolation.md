# Task 08 — P2: probe diagnose-identity.sh + guida isolamento

**Stato:** PENDING
**Dipende da:** task-00
**File:** `scripts/diagnose-identity.sh` (nuovo), `docs/handover/2026-06-14-shared-account-isolation.md` (nuovo), `tests/zero-loss/unit/test_diagnose_identity.sh` (nuovo)

## Obiettivo
Test empirico account condivisi (il "testalo") + guida isolamento per-persona.

## diagnose-identity.sh (cross-platform, `set -euo pipefail` safe)
Stampa una riga `chiave=valore` per:
`HOME`, `CLAUDE_CONFIG_DIR`, `claude_json_path` (path effettivamente letto),
`claude_json_exists`, `oauth_email`, `oauth_account_uuid` (mascherato: primi 8 char + `…`),
`os_user`, `host_short` (`${host%%.*}`), `json_interpreter` (`node`|`python3`|`none`).
Riga `CLAUDE_CONFIG_DIR onorato=si|no` (confronto tra `claude_json_path` e `$CLAUDE_CONFIG_DIR/.claude.json`).
Riga finale `VERDICT`:
- `NO-AUTH` se `oauth_email` vuoto;
- `SHARED-DEGENERATE` se `claude_json_path == ~/.claude.json` e `CLAUDE_CONFIG_DIR` non settato/non onorato;
- `ISOLATED` se `claude_json_path` proviene da `CLAUDE_CONFIG_DIR` per-persona.

## Guida isolamento — `docs/handover/2026-06-14-shared-account-isolation.md`
- raccomandato: `export CLAUDE_CONFIG_DIR="$HOME/.claude-$(whoami)"` nel profilo shell di ogni dev sul box condiviso;
- se l'esito del task-00 dimostra che Claude Code NON onora la var → fallback obbligatorio:
  lancio per-persona con `HOME` isolato (`HOME=/srv/devforge-personas/$REAL_USER claude …`) o sotto-account OS.

## Approccio TDD
### RED — `tests/zero-loss/unit/test_diagnose_identity.sh`
- lo script gira sotto `set -euo pipefail` senza errori;
- stampa tutte le chiavi previste + riga `VERDICT`;
- con `CLAUDE_CONFIG_DIR` impostato a un path il cui `.claude.json` esiste → `onorato=si` e `VERDICT: ISOLATED`;
- con `oauth_email` vuoto → `VERDICT: NO-AUTH`.

### GREEN
Implementare lo script (riuso di `devforge_json_field` se sourcia logger.sh, altrimenti chain inline node→python3) + la guida.

## Criteri di accettazione (design AC 10)
Output completo + `VERDICT` + caso `CLAUDE_CONFIG_DIR onorato=no` esplicito.

## No-regression
Script + doc nuovi standalone; nessun impatto sul runtime degli hook.
