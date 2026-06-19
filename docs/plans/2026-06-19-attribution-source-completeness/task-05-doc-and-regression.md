# Task 05 — Doc ENV_VARS + no-regression suite

**Tipo:** doc/verify · **AC:** AC6 · **File:** `hooks/ENV_VARS.md`

## Obiettivo

Documentare la nuova var `DEVFORGE_AUTH_DOMAIN` e confermare zero regressione sull'intera
suite hook/logger prima di chiudere.

## Implementazione

### 1. Documenta `DEVFORGE_AUTH_DOMAIN` in `hooks/ENV_VARS.md`

Aggiungi una voce coerente col formato esistente del file (apri `hooks/ENV_VARS.md` e
replica lo stile della tabella/sezione già presente). Contenuto:

- **Nome:** `DEVFORGE_AUTH_DOMAIN`
- **Default:** `siae.it`
- **Scopo:** dominio email aziendale atteso. Se `auth_email` ha un dominio diverso,
  `session-start` (branch startup) emette `identity_external_domain`. Override per altri org.
- **Usato da:** `lib/logger.sh` (`devforge_emit_identity_observability`), `hooks/session-start`.

### 2. No-regression suite

Esegui i test che toccano il logger / attribuzione e raccogli gli exit code:

```bash
cd "$(git rev-parse --show-toplevel)"
for t in \
  tests/hooks/test_lazy_auth_resolution.sh \
  tests/hooks/test_identity_observability.sh \
  tests/hooks/test_log_toplevel_attribution.sh \
  tests/hooks/test_init_session_auth_pin.sh \
  tests/hooks/test_commit_created_attribution_e2e.sh \
  tests/hooks/test_identity_bundle_auth.sh \
  tests/zero-loss/unit/test_json_field_portable.sh ; do
  [ -f "$t" ] || { echo "SKIP (assente) $t"; continue; }
  bash "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL($?) $t"
done
```

**Atteso:** tutti `PASS` (o `SKIP` se un file non esiste in questa checkout).
Qualsiasi `FAIL` va investigato prima di chiudere — verifica via exit code, non grep.

## Done quando

- `DEVFORGE_AUTH_DOMAIN` documentata in `ENV_VARS.md`.
- Tutta la lista test sopra: nessun `FAIL`.
- Le 5 task del piano completate → handoff a `siae-verification` + `siae-git-workflow`.
