# Piano — Determinismo attribuzione (producer-side, Comp.1-3)

> Design: `docs/plans/2026-06-08-attribution-determinism-design.md` (spec-review PASS, 2 iter)
> Branch: `feat/telemetry-raw-value-signals` (corretto — NON creare nuovo branch)
> Scope: Componenti 1-4 (TUTTI). Comp.4 (trailer DevForge-Author) implementato 2026-06-09 (design §7 aggiornato).

## Goal
Rendere l'attribuzione dev↔commit↔repo un **join** invece di inferenza, emettendo 3 campi RAW
top-level in ogni evento (`auth_email`, `auth_account_uuid`, `repo_remote`) + estendendo l'identity
bundle con i campi auth. Additivo (schema_version=2 invariato). No-regression su
`user`/`user_raw`/`user_source`/`actor_canonical`.

## Principi vincolanti
- **Best-effort assoluto:** `~/.claude.json` assente, no `oauthAccount` (Bedrock/API-key), no python3,
  repo senza origin → campo = "" senza crash. Mai abort sotto `set -euo pipefail`.
- **No re-read per-evento** del JSON 141KB: auth pinnato a session-start via env `DEVFORGE_AUTH_*`.
- **Sanitizzazione:** ogni campo passa per `devforge_sanitize_json_str`.
- **TDD:** ogni task RED→GREEN; test in `tests/hooks/`.

## Task

| # | Task | Stato | File principale |
|---|------|-------|-----------------|
| 01 | `devforge_resolve_auth_identity()` legge ~/.claude.json oauthAccount | [DONE] | lib/logger.sh |
| 02 | `devforge_identity_bundle()` esteso con 4 campi auth_* | [DONE] | lib/logger.sh |
| 03 | session-start esporta `DEVFORGE_AUTH_EMAIL`/`DEVFORGE_AUTH_ACCOUNT_UUID` | [DONE] | hooks/session-start |
| 04 | `devforge_init_session()` legge identity.auth_* da user.json + esporta env | [DONE] | lib/logger.sh |
| 05 | `devforge_log` + `devforge_log_timed`: top-level auth_email/auth_account_uuid/repo_remote | [DONE] | lib/logger.sh |
| 06 | Integration test: `commit_created` porta repo_remote top-level + commit_sha nel meta | [DONE] | tests/hooks/ |
| 07 | Docs: handover consumer + ENV_VARS.md | [DONE] | docs/handover/, hooks/ENV_VARS.md |
| 08 | Trailer `DevForge-Author` (Comp.4): prepare-commit-msg hook + installer + wiring | [DONE] | lib/install-trailer-hook.sh, hooks/session-start |

## Ordine & dipendenze
01 → 02 (bundle usa resolve) → 04 (init_session legge ciò che 02/03 scrivono) → 05 (log usa env di 04).
03 dipende da 01 (session-start chiama `devforge_resolve_auth_identity`) ma è indipendente da 04
(entrambe esportano env; 03 per eventi di session-start, 04 per hook successivi).
06 integrazione finale (nessun codice nuovo in post-commit-review: eredita da logger). 07 docs.
Ordine esecuzione consigliato: 01 → 02 → 03 → 04 → 05 → 06 → 07.

## Criteri di accettazione globali (dal design §10)
- Ogni evento porta top-level `auth_email`, `auth_account_uuid`, `repo_remote`.
- `commit_created`: `commit_sha` nel meta + `repo_remote` top-level.
- identity bundle (session_start.meta + user.json) include i 4 `auth_*`.
- Best-effort verificato su tutti gli edge case.
- No-regression: 4 campi identità esistenti invariati; JSONL valido.
- Trailer documentato come follow-up (non implementato).
