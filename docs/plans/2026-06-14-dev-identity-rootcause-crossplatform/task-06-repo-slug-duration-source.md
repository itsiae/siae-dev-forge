# Task 06 — 6b+6d: campo repo_slug + marker duration_source

**Stato:** PENDING
**Dipende da:** nessuno
**File:** `lib/logger.sh`, `tests/zero-loss/unit/test_repo_slug.sh` (nuovo)

## Obiettivo
- 6b: emettere `repo_slug` normalizzato (`org/repo`) top-level per join esatto col repo, da SSH e HTTPS.
- 6d: aggiungere `meta.duration_source="wallclock"` agli eventi temporizzati per esplicitare la semantica (il consumer applica cap/mediana).

## Approccio TDD
### RED — `tests/zero-loss/unit/test_repo_slug.sh`
`devforge_repo_slug` per:
- `git@gitlab.itsiae.it:itsiae/diritti-api.git` → `itsiae/diritti-api`
- `https://github.com/itsiae/diritti-api.git` → `itsiae/diritti-api`
- `https://github.com/itsiae/diritti-api` → `itsiae/diritti-api`
- `""` (no remote) → `""`
Inoltre: un evento timed simulato (`devforge_log_timed`) deve contenere nel JSON emesso il campo
`repo_slug` (non vuoto) e il campo `duration_source` valorizzato a `wallclock`.

### GREEN — `lib/logger.sh`
```bash
# org/repo from a git remote URL (SSH scp-form or HTTPS). Empty if not derivable.
devforge_repo_slug() {
    local url="$1"
    [ -n "$url" ] || { printf ''; return 0; }
    url="${url%.git}"
    url="${url#*://}"      # strip scheme (https://)
    url="${url#*@}"        # strip user@ (ssh)
    url="${url/://}"       # first ':' -> '/' (ssh scp-form host:org/repo)
    local repo rest org
    repo="${url##*/}"; rest="${url%/*}"; org="${rest##*/}"
    if [ -n "$org" ] && [ -n "$repo" ] && [ "$org" != "$repo" ]; then
        printf '%s/%s' "$org" "$repo"
    else
        printf ''
    fi
}
```
Aggiungere `"repo_slug":"<slug>"` accanto a `repo_remote` nell'envelope di `devforge_log` e
`devforge_log_timed` (area `logger.sh:556`).
Per `duration_source` (WARN-1): aggiungerlo come **campo separato nel template printf** di
`devforge_log_timed`, inserendo il token `"duration_source":"wallclock"` subito dopo il campo
`"duration_ms":%s` (NON un merge JSON del `meta` passato dai caller — fragile in bash).

## Criteri di accettazione (design AC 6)
4 casi `repo_slug` verdi; campo presente su `commit_created`; `duration_source` presente sugli eventi timed.

## No-regression
Additivo; `repo_remote` e `duration_ms` invariati.
