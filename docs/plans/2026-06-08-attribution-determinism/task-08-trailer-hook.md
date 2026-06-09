# Task 08 — Trailer `DevForge-Author` (Comp.4)

**Stato:** [PENDING]
**File:** `lib/install-trailer-hook.sh` (nuovo), `hooks/session-start` (wiring), `hooks/ENV_VARS.md`
**Obiettivo:** installare un `prepare-commit-msg` self-contained che timbra `DevForge-Author: <sso-email>`
nel commit (sopravvive al mirror), idempotente, zero-harm su hook estranei, mai blocca un commit.
Design: `docs/plans/2026-06-08-attribution-determinism-design.md` §7.

## RED — Test (`tests/hooks/test_trailer_hook.sh`)
Copre: install+marker+exec, idempotenza, skip-foreign (rc=2), opt-out, e2e trailer, amend no-dup,
best-effort no-claude-json, merge-skip, e `--in-place` safety (messaggio preservato).

## GREEN — `lib/install-trailer-hook.sh`
Funzione `devforge_install_trailer_hook`:
- opt-out `DEVFORGE_SKIP_TRAILER_HOOK=1` → return 0; no git / no repo → return 0.
- `hooks_dir=$(git rev-parse --git-path hooks)`; `mkdir -p`.
- target=`$hooks_dir/prepare-commit-msg`, marker `# DEVFORGE-TRAILER-HOOK v1`.
- se target esiste senza marker → **return 2** (foreign, skip, zero-harm).
- altrimenti scrive l'hook (heredoc) + `chmod +x`; return 0.
- guard `if [ "${BASH_SOURCE[0]}" = "$0" ]; then devforge_install_trailer_hook; exit $?; fi` (eseguibile + sourcabile).

Hook installato (self-contained, `set +e`, exit 0 sempre, `--in-place`):
```bash
#!/usr/bin/env bash
# DEVFORGE-TRAILER-HOOK v1
set +e
MSG_FILE="$1"; SRC="${2:-}"
case "$SRC" in merge|squash) exit 0 ;; esac
CJ="${DEVFORGE_CLAUDE_JSON:-${HOME}/.claude.json}"
EMAIL=""
if [ -f "$CJ" ] && command -v python3 >/dev/null 2>&1; then
    EMAIL=$(python3 -c "import json,sys;print((json.load(open(sys.argv[1])).get('oauthAccount') or {}).get('emailAddress','') or '')" "$CJ" 2>/dev/null)
fi
EMAIL=$(printf '%s' "$EMAIL" | tr -d '\n\r')
[ -z "$EMAIL" ] && exit 0
[ -f "$MSG_FILE" ] || exit 0
command -v git >/dev/null 2>&1 || exit 0
git interpret-trailers --in-place --if-exists doNothing --trailer "DevForge-Author: ${EMAIL}" "$MSG_FILE" 2>/dev/null
exit 0
```

## GREEN — wiring `hooks/session-start`
Dopo l'install statusline (riga ~103), aggiungere (safe sotto set -e):
```bash
# Install DevForge-Author trailer hook (idempotente, zero-harm, fast/local).
TRAILER_RC=0; bash "${PLUGIN_ROOT}/lib/install-trailer-hook.sh" >/dev/null 2>&1 || TRAILER_RC=$?
[ "$TRAILER_RC" = "2" ] && devforge_log "trailer_hook_skipped_foreign" "success" "{}" 2>/dev/null || true
```

## GREEN — `hooks/ENV_VARS.md`
Documentare `DEVFORGE_SKIP_TRAILER_HOOK` (install-time opt-out; per-commit via `--no-verify`).

## Verifica
```bash
bash tests/hooks/test_trailer_hook.sh
```

## Accettazione
- [ ] Installer idempotente, marker-guarded, zero-harm (skip foreign rc=2), opt-out.
- [ ] Hook timbra trailer su commit normali, skip merge/squash, exit 0 sempre, `--in-place`.
- [ ] Idempotente (amend no-dup); messaggio preservato se interpret-trailers fallisce.
- [ ] session-start invoca l'installer; ENV_VARS documentato.
