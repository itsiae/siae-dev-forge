# Task 04 — F2c: hardening trailer hook

**Stato:** PENDING
**Dipende da:** task-02
**File:** `lib/install-trailer-hook.sh`, `tests/zero-loss/unit/test_trailer_hook_hardening.sh` (nuovo)

## Obiettivo
Trailer `DevForge-Author` funzionante su Windows + degrado osservabile su git legacy.

## Modifiche
1. **Bump marker** `# DEVFORGE-TRAILER-HOOK v1` → `v2` (righe 22 e 34) → re-deploy automatico
   dei hook già installati alla session-start successiva.
2. **node→python3 nel hook generato:** la lettura di `oauthAccount.emailAddress` (righe 44-45) usa
   una chain inline self-contained (il hook NON sorcia logger.sh):
   ```bash
   EMAIL=""
   if command -v node >/dev/null 2>&1; then
       EMAIL=$(node -e 'try{const fs=require("fs");process.stdout.write(String((JSON.parse(fs.readFileSync(process.argv[1],"utf8")).oauthAccount||{}).emailAddress||""))}catch(e){process.exit(3)}' "$CJ" 2>/dev/null)
   fi
   if [ -z "$EMAIL" ] && command -v python3 >/dev/null 2>&1; then
       EMAIL=$(python3 -c "import json,sys;print((json.load(open(sys.argv[1])).get('oauthAccount') or {}).get('emailAddress','') or '')" "$CJ" 2>/dev/null)
   fi
   ```
3. **Guard `git interpret-trailers` (install-time):** in `devforge_install_trailer_hook()`, prima di
   scrivere il hook, capability check `git interpret-trailers --help >/dev/null 2>&1` + versione ≥ 2.15
   (`git --version` parse); se fallisce → `devforge_log "trailer_hook_skipped_old_git" "warning" '{"git_version":"<v>"}'`
   (contesto session-start ha il logger). Installare comunque il hook (best-effort).
4. **Hook generato:** catturare l'exit code di `interpret-trailers` (no `2>/dev/null` blanket sul comando
   finale); su fallimento runtime NON scrive il trailer ma `exit 0` (mai blocca il commit).

## Approccio TDD
### RED — `tests/zero-loss/unit/test_trailer_hook_hardening.sh`
- il `prepare-commit-msg` generato contiene il marker `v2` e la chain node→python3;
- con `python3` mascherato e `node` presente, un commit di prova ottiene il trailer `DevForge-Author`;
- simulando `git interpret-trailers` assente (shim PATH), l'installer emette `trailer_hook_skipped_old_git`
  e un commit di prova NON viene bloccato (exit 0).

### GREEN
Applicare le 4 modifiche.

## Criteri di accettazione (design AC 8)
Emissione install-time del segnale; hook exit-0; trailer scritto con node-only.

## No-regression
Zero-harm su `prepare-commit-msg` estranei preservato (marker check riga 26); skip merge/squash preservato (riga 40).
