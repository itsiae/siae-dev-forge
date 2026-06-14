# Task 03 — F2b: instrada i siti identità-critici su devforge_json_field

**Stato:** PENDING
**Dipende da:** task-02
**File:** `lib/logger.sh`, `tests/zero-loss/unit/test_identity_portable_sites.sh` (nuovo)

## Obiettivo
Far funzionare su Windows (senza python3) TUTTI i punti identità-critici, non solo resolve_auth.

## Siti da convertire (da python3-only a devforge_json_field)
- `devforge_resolve_auth_identity()` (`logger.sh:295-313`) → leggere i 4 campi
  `oauthAccount.{emailAddress,accountUuid,organizationUuid,organizationName}` via `devforge_json_field`.
- `devforge_init_session()` (`logger.sh:437-442`) → pinning `auth_email`/`auth_account_uuid` da `user.json`
  (`identity.auth_email`, `identity.auth_account_uuid`) via `devforge_json_field`.
- `devforge_get_user_raw()` / `devforge_get_user_source()` (`logger.sh:381/394`) → letture `user.json`
  (`raw`, `source`) via `devforge_json_field`.
- `devforge_session_token_total()` (`logger.sh:319`): instradare su `devforge_json_field` con path `total`
  (`total` È un campo top-level di `token-stats.json`, esprimibile come dotted-path). NON identità-critico:
  il degrado a 0 è già il comportamento atteso e non richiede gestione aggiuntiva.

## Approccio TDD
### RED — `tests/zero-loss/unit/test_identity_portable_sites.sh`
Con `python3` mascherato e `node` presente, una sessione simulata (HOME temp + `.claude.json` fittizio +
`user.json` scritto da session-start simulato) deve produrre:
- `auth_email`/`auth_account_uuid` non vuoti negli eventi emessi;
- `DEVFORGE_PINNED_USER`, `DEVFORGE_AUTH_EMAIL`, `DEVFORGE_AUTH_ACCOUNT_UUID` valorizzati dopo `devforge_init_session`.

### GREEN
Sostituire le invocazioni inline `python3 -c` esistenti ai siti elencati con chiamate a `devforge_json_field`,
preservando i fallback e i default esistenti (catena `devforge_resolve_user_raw` invariata nei rami non-JSON).

## Criteri di accettazione (design AC 4, 5)
- AC4: con interprete = solo node, auth_* valorizzati (incluso pinning `init_session`).
- AC5: no-regression — con `~/.claude.json` presente, `auth_email`/`auth_account_uuid` identici al baseline pre-F2.

## No-regression
Catturare auth_* su una sessione PRE-modifica e POST-modifica → identici. `user`/`actor_canonical` invariati.
