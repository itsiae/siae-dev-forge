# Task 07 — Documentazione (handover consumer + ENV_VARS)

**Stato:** [PENDING]
**File:** `docs/handover/2026-06-08-attribution-determinism-fields.md` (nuovo), `hooks/ENV_VARS.md` (append)
**Dipende da:** Task 05 (campi finali noti)
**Obiettivo:** documentare il contratto dei nuovi campi per il consumer e le env var.

## GREEN — Contenuto handover (`docs/handover/2026-06-08-attribution-determinism-fields.md`)
Front-matter `status: handover`, `target: developer-telemetry`, `supersedes_partial: 2026-06-03-telemetry-new-fields.md` (additivo).
Sezioni richieste:
1. **Nuovi campi top-level per-evento** (tutti gli eventi, schema_version=2, additivi):
   - `auth_email` (string, SSO da oauthAccount; "" se Bedrock/API-key)
   - `auth_account_uuid` (string, UUID account immutabile; chiave di join più stabile dell'email)
   - `repo_remote` (string RAW = `git remote get-url origin`; "" se repo senza origin)
2. **identity bundle esteso** (`session_start.meta.identity` + `user.json.identity`): aggiunti
   `auth_email`, `auth_account_uuid`, `auth_org_uuid`, `auth_org_name`.
3. **Uso consumer:** `auth_account_uuid`/`auth_email` abilitano join deterministico (PRIORITÀ -2,
   sopra l'identity bundle git/os/host); `repo_remote` mappa l'evento al repo GitHub reale (sopra `project`).
   `commit_sha` (già presente in `commit_created`) sopravvive al mirror GitLab→GitHub → join commit↔GitHub.
4. **Regola di consumo:** leggere con `.get(...)` default (eventi storici non hanno i campi).
5. **Coverage caveat:** determinismo 100% solo per lavoro timbrato DevForge da utenti OAuth/SSO.
   Bedrock/API-key → `auth_email` vuoto, fallback alla chain esistente. Commit fuori DevForge → niente campi.
6. **Trailer DevForge-Author:** NON ancora emesso (follow-up; vedi design §7).

## GREEN — Append a `hooks/ENV_VARS.md`
Documentare:
- `DEVFORGE_AUTH_EMAIL` — email SSO pinnata della sessione (da `~/.claude.json` oauthAccount).
- `DEVFORGE_AUTH_ACCOUNT_UUID` — UUID account pinnato della sessione.
- `DEVFORGE_CLAUDE_JSON` — override path del file oauth (default `~/.claude.json`; usato nei test).

## Verifica
```bash
test -f docs/handover/2026-06-08-attribution-determinism-fields.md
grep -q 'DEVFORGE_AUTH_EMAIL' hooks/ENV_VARS.md
grep -q 'DEVFORGE_CLAUDE_JSON' hooks/ENV_VARS.md
grep -q 'auth_account_uuid' docs/handover/2026-06-08-attribution-determinism-fields.md
```

## Accettazione
- [ ] Handover doc creato con le 6 sezioni (campi, bundle, uso, regola, caveat, trailer-deferred).
- [ ] `ENV_VARS.md` documenta le 3 env var.
- [ ] Nessun TBD/placeholder.
