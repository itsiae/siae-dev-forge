# Task 04 — Wire dei 6 campi in `devforge_identity_bundle` (Capability A)

**AC:** AC1, AC8 · **File:** `lib/logger.sh`, `tests/zero-loss/unit/test_logger_identity_signals.sh`

## Obiettivo

Integrare i 6 nuovi campi (da task-02/03) nel JSON di `devforge_identity_bundle` (logger.sh:371),
**additivi** rispetto ai campi esistenti, ognuno passato per `devforge_sanitize_json_str`.

## RED — test che fallisce

Aggiungi a `test_logger_identity_signals.sh`:
- `bundle=$(devforge_identity_bundle)` deve essere JSON valido (parse con python3/node).
- Deve contenere TUTTI i campi esistenti (`git_local_email`, `auth_email`, ...) E i 6 nuovi
  (`os_full_name`, `os_login`, `os_domain`, `ssh_fingerprint`, `npm_email`, `gh_email`).
- Con un `id -F` simulato che ritorna `O'Brien "Jörg"` (quote+apostrofo+unicode) → bundle resta
  JSON valido (sanitize).
- Atteso PRE-fix: FAIL (campi assenti).

## GREEN — implementazione

In `devforge_identity_bundle`, prima della `printf` finale, aggiungi:

```bash
local _os _tools osfn oslg osdm sshfp npme ghe
_os=$(_devforge_local_identity_signals_os)
osfn="${_os%%$'\t'*}"; _os="${_os#*$'\t'}"; oslg="${_os%%$'\t'*}"; osdm="${_os#*$'\t'}"
_tools=$(_devforge_local_identity_signals_tools)
sshfp="${_tools%%$'\t'*}"; _tools="${_tools#*$'\t'}"; npme="${_tools%%$'\t'*}"; ghe="${_tools#*$'\t'}"
```

Sostituisci la `printf` finale (logger.sh:390-395, 10 campi) con la versione **completa a 16 campi**
(BLOCK-2: format token e argomenti devono corrispondere esattamente, 16 `%s` ↔ 16 argomenti):

```bash
printf '{"git_local_email":"%s","git_local_name":"%s","git_global_email":"%s","git_global_name":"%s","os_user":"%s","host":"%s","auth_email":"%s","auth_account_uuid":"%s","auth_org_uuid":"%s","auth_org_name":"%s","os_full_name":"%s","os_login":"%s","os_domain":"%s","ssh_fingerprint":"%s","npm_email":"%s","gh_email":"%s"}' \
    "$(devforge_sanitize_json_str "$gle")" "$(devforge_sanitize_json_str "$gln")" \
    "$(devforge_sanitize_json_str "$gge")" "$(devforge_sanitize_json_str "$ggn")" \
    "$(devforge_sanitize_json_str "$osu")" "$(devforge_sanitize_json_str "$host")" \
    "$(devforge_sanitize_json_str "$ae")" "$(devforge_sanitize_json_str "$au")" \
    "$(devforge_sanitize_json_str "$ou")" "$(devforge_sanitize_json_str "$onm")" \
    "$(devforge_sanitize_json_str "$osfn")" "$(devforge_sanitize_json_str "$oslg")" \
    "$(devforge_sanitize_json_str "$osdm")" "$(devforge_sanitize_json_str "$sshfp")" \
    "$(devforge_sanitize_json_str "$npme")" "$(devforge_sanitize_json_str "$ghe")"
```
(I primi 10 campi/argomenti sono identici all'originale — solo aggiunta in coda. NON rimuovere né
riordinare i 10 esistenti: additivo puro.)

## REFACTOR

Verifica che l'ordine dei campi esistenti sia invariato (additivo in coda). Nessun campo rimosso.

## Verifica / Done

- `bash tests/zero-loss/unit/test_logger_identity_signals.sh` PASS completo.
- No-regression: tutta la suite zero-loss/telemetria verde. Marca `[DONE]`.
