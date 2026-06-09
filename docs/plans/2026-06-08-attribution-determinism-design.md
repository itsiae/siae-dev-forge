---
status: design
owner: Lorenzo De Tomasi
created: 2026-06-08
topic: Determinismo totale attribuzione dev↔commit↔repo (producer-side)
scope: DevForge producer (lib/logger.sh + hooks). NON ridisegna il consumer developer-telemetry.
related: docs/handover/2026-06-03-telemetry-new-fields.md (contratto consumer identity bundle)
---

# Design — Determinismo TOTALE dell'attribuzione (producer-side)

## 1. Contesto e problema

L'attribuzione dev↔commit↔repo oggi è certa al ~95%. Il 5% residuo è **inferito** e deriva
dal mirror GitLab→GitHub (JGit riscrive author+committer con email bot `last:gitlab`), da
git config vuote/condivise, e dal fatto che `project` è un codice interno non mappabile al repo
GitHub. DevForge è l'unico punto del flusso che conosce l'identità **autenticata** del dev nel
momento dell'azione: timbrarla negli eventi trasforma l'attribuzione da *inferenza* a *join*.

**Verifica empirica della sorgente (HIGH confidence, non assunzione):**
`~/.claude.json` → `oauthAccount` contiene `emailAddress` (= `lorenzo.detomasi@siae.it`, SSO),
`accountUuid` (UUID immutabile), `organizationUuid`, `organizationName`. File locale, perms `0600`,
di proprietà dell'utente. È la sorgente per `auth_email` / `auth_account_uuid`.

**Stato attuale del codice (verificato):**
- `commit_created` **già emette `commit_sha`** nel meta (`hooks/post-commit-review:78`) → spec #1 SHA: GIÀ FATTO.
- `pr_commit_after_open` già emette `commit_sha` (`:131`).
- Identity bundle (`devforge_identity_bundle`, `lib/logger.sh:259`) ha `git_local_email`,
  `git_global_email`, `os_user`, `host` — **manca `auth_email`**. Vive solo in `session_start.meta.identity`
  e `user.json.identity`, consumato a `03_build_facts.py:351` (PRIORITÀ -1).
- Eventi top-level: `repo_root` (path FS), `project`, `project_canonical` — **manca `repo_remote`** (URL git).

## 2. Obiettivo (in-scope) e non-obiettivi

**In-scope (producer):** emettere i campi RAW che rendono l'attribuzione un join.
**Non-obiettivi:** NON modificare la pipeline consumer (`lib_actor_match`, `07e`, aliases,
`03_build_facts`); quella è scope downstream, soltanto *abilitata* da questi campi. NON cambiare
la semantica di `user`/`actor_canonical` esistenti (no-regression: il consumer ci fa join oggi).

## 3. Approcci valutati

### Approccio A — Campi top-level per-evento + estensione identity bundle (SCELTO)
Aggiungere `auth_email`, `auth_account_uuid`, `repo_remote` come **campi top-level in OGNI evento**
(letti da pinning di sessione, non ri-leggendo `~/.claude.json`), ed estendere `devforge_identity_bundle`
con i campi auth (flusso verso `session_start.meta.identity` + `user.json.identity`, già consumato).
- **Pro:** eventi auto-attributivi (no join obbligatorio con session_start, robusto a partizioni S3
  separate / session_start perso); additivo (schema_version resta 2); riusa l'extension point
  `identity` già nel contratto consumer; pinning = zero overhead per-evento.
- **Contro:** lieve ridondanza (auth_email in identity di sessione + top-level per-evento) — intenzionale.
- **Complessità:** Media.

### Approccio B — Solo a session_start, consumer fa join via `sid`
Mettere auth solo in `session_start.meta.identity` (di fatto già possibile oggi) e lasciare al
consumer il join evento→sessione via `sid`.
- **Pro:** zero modifiche a `devforge_log`; footprint per-evento nullo.
- **Contro:** NON auto-attributivo; fragile se session_start è in altra partizione/perso; sposta lavoro
  e rischio sul consumer (contro l'intento "eventi auto-attributivi" della spec). **SCARTATO.**

### Approccio C — Oggetto `identity` completo embedded in ogni evento
Embeddare l'intero bundle in ogni evento.
- **Pro:** massima ricchezza per-evento.
- **Contro:** byte per-evento elevati su milioni di eventi; ridondante con `user`/`user_raw`. **SCARTATO**
  in favore del set minimo di A (3 campi).

**Raccomandazione: Approccio A.** Set minimo per-evento (`auth_email`, `auth_account_uuid`, `repo_remote`),
bundle completo a session-level.

## 4. Design (Approccio A)

### Componente 1 — `repo_remote` in ogni evento
`lib/logger.sh` `devforge_log` + `devforge_log_timed`: aggiungere top-level
`"repo_remote":"<raw>"` dove `<raw>` = `git remote get-url origin 2>/dev/null` (RAW, no normalizzazione;
empty string se assente — best-effort come gli altri segnali). Operazione git locale veloce, coerente
col costo del già presente `git rev-parse --show-toplevel` per-evento. Sanitizzato via `devforge_sanitize_json_str`.

### Componente 2 — Risoluzione + pinning identità autenticata
- `lib/logger.sh`: nuova funzione `devforge_resolve_auth_identity()` che legge `~/.claude.json`
  → `oauthAccount.{emailAddress,accountUuid,organizationUuid,organizationName}` via python3.
  Best-effort: file assente / no `oauthAccount` (Bedrock/API-key) / no python3 → tutti empty. Mai abort sotto `set -euo pipefail`.
- `devforge_identity_bundle()`: chiama internamente `devforge_resolve_auth_identity()` ed è esteso con
  `auth_email`, `auth_account_uuid`, `auth_org_uuid`, `auth_org_name` (additivo all'oggetto esistente).

**Struttura `user.json` (BLOCK-2 — esplicita, niente ambiguità):** i campi auth vivono **dentro
il sotto-oggetto `identity`**, NON come chiavi di primo livello. Niente duplicazione. Struttura post-PR:
```json
{ "raw": "...", "source": "...", "canonical": "...",
  "identity": { "git_local_email":"...", "...", "os_user":"...", "host":"...",
                "auth_email":"lorenzo.detomasi@siae.it", "auth_account_uuid":"1d9cbbdb-...",
                "auth_org_uuid":"779f34e4-...", "auth_org_name":"Information Technology" } }
```
- `hooks/session-start`: **nessuna modifica alla logica di scrittura** di `user.json` — la riga esistente
  `d['identity']=json.loads(IDENTITY_BUNDLE)` (`session-start:62-64`) incorpora automaticamente i campi auth
  appena `devforge_identity_bundle` li include. Unica aggiunta: dopo la scrittura, esportare
  `DEVFORGE_AUTH_EMAIL`/`DEVFORGE_AUTH_ACCOUNT_UUID` (per gli eventi emessi da session-start stesso, es. `session_start`).
- `devforge_init_session()`: legge da `user.json` con path JSON esatto
  `d.get('identity',{}).get('auth_email','')` e `d.get('identity',{}).get('auth_account_uuid','')`,
  ed esporta `DEVFORGE_AUTH_EMAIL` / `DEVFORGE_AUTH_ACCOUNT_UUID` (pattern identico a `DEVFORGE_PINNED_USER`).

### Componente 3 — Propagazione per-evento (auto-attribuzione)
`devforge_log` + `devforge_log_timed`: aggiungere top-level `"auth_email"` e `"auth_account_uuid"`
letti da `DEVFORGE_AUTH_EMAIL`/`DEVFORGE_AUTH_ACCOUNT_UUID` (empty fallback). Pinning ⇒ nessun
re-read del JSON 141KB per-evento.

**`commit_created` (spec #1):** con `repo_remote` top-level (Comp.1) + `commit_sha` già nel meta,
il join esatto commit↔GitHub è soddisfatto. `commit_sha` resta nel meta (self-contained per l'evento commit).

### Risoluzione semantica — NO regression
`user`, `user_raw`, `user_source`, `actor_canonical` restano **identici** (il consumer ci fa join oggi).
`auth_email`/`auth_account_uuid` sono campi NUOVI additivi. Il consumer potrà elevarli a PRIORITÀ -2
(sopra l'identity bundle) — decisione di scope consumer, fuori da questo PR.

## 5. Flusso dati
```
session-start ──► resolve_auth_identity(~/.claude.json) ──► user.json.identity {+auth_email, auth_account_uuid, auth_org_*}
                                                          └► session_start.meta.identity {+auth_*}
        │
init_session ──► export DEVFORGE_AUTH_EMAIL / DEVFORGE_AUTH_ACCOUNT_UUID
        │
devforge_log / log_timed ──► ogni evento: + auth_email + auth_account_uuid + repo_remote (top-level)
```

## 6. Gestione errori / edge case
| Caso | Comportamento |
|---|---|
| `~/.claude.json` assente/illeggibile | auth_* = "" (best-effort), evento valido, fallback chain esistente |
| Auth via Bedrock/API-key (no `oauthAccount`) | auth_email = "" → coverage 100% solo per utenti OAuth/SSO; no-regression |
| python3 assente | resolve_auth = "" (degradato, come token-collector) |
| Repo senza `origin` | repo_remote = "" |
| Caratteri speciali in remote URL/email | `devforge_sanitize_json_str` su tutti i campi |
| Evento storico pre-feature | consumer legge con `.get(...)` default (contratto additivo) |

## 7. Componente 4 — Trailer `DevForge-Author` (IMPLEMENTATO)

Scrive nel commit stesso un trailer `DevForge-Author: <sso-email>` così che l'autore reale
sopravviva nel commit anche **fuori** dalla telemetria — qualunque consumer (non solo questa
pipeline) lo recupera dopo il mirror GitLab→GitHub.

### Meccanismo: git `prepare-commit-msg` hook self-contained, installato per-repo a session-start
- **Perché prepare-commit-msg:** è l'unico punto git-native che modifica il messaggio PRIMA del
  calcolo dello SHA → il trailer entra nel commit senza rewrite/amend (lo SHA lo include
  naturalmente). Vale per OGNI stile di messaggio (`-m`, `-F`, heredoc, template) e per i commit
  di Claude Code E manuali nello stesso repo.
- **Installer** `lib/install-trailer-hook.sh` (invocato da `hooks/session-start`, foreground, fast,
  solo file-ops locali, idempotente):
  - No-op se fuori da un repo git, o se `DEVFORGE_SKIP_TRAILER_HOOK=1` (opt-out).
  - `HOOKS_DIR=$(git rev-parse --git-path hooks)` (rispetta `core.hooksPath`/husky); `mkdir -p`.
  - TARGET=`$HOOKS_DIR/prepare-commit-msg`. Marker DevForge: `# DEVFORGE-TRAILER-HOOK v1`.
  - Se TARGET esiste e NON contiene il marker → **hook estraneo (husky ecc.) → SKIP install**
    (zero-harm: non clobbera mai un hook utente), log `trailer_hook_skipped_foreign`. Chaining =
    enhancement futuro.
  - Se assente o già nostro → scrive l'hook + `chmod +x` (idempotente).
- **L'hook** (self-contained, `set +e`, exit 0 SEMPRE — non blocca mai un commit):
  - Skip se `$2` (source) ∈ {merge, squash} (nessun autore singolo significativo).
  - Risolve l'email da `~/.claude.json` oauthAccount.emailAddress (best-effort, override
    `DEVFORGE_CLAUDE_JSON`); se vuota (Bedrock/no-python3) → exit 0 senza timbrare. `tr -d '\n\r'` difensivo.
  - Appende il trailer con **`git interpret-trailers --in-place --if-exists doNothing --trailer
    "DevForge-Author: ${EMAIL}" "$MSG_FILE"`** (email tra DOUBLE-quote, no eval):
    - **`--in-place` OBBLIGATORIO** (BLOCK spec-review Q8): se `interpret-trailers` fallisce
      (es. exit 128) NON tocca il file → `COMMIT_EDITMSG` preservato. Vietato il pattern
      `RESULT=$(...) && printf > file` che azzererebbe il messaggio su failure (data loss anche con exit 0).
    - `--if-exists doNothing` → **idempotente per-token** (amend/re-run non duplicano; verificato git 2.50.1).

### Edge case
| Caso | Comportamento |
|---|---|
| Repo con prepare-commit-msg estraneo (husky) | SKIP install, hook utente intatto, log telemetria |
| `~/.claude.json` assente / Bedrock / no-python3 | commit procede SENZA trailer (no block) |
| Commit merge/squash | nessun trailer |
| Amend / hook ri-eseguito | nessun duplicato (`--if-exists doNothing`) |
| `core.hooksPath` impostato (husky) | install nella dir corretta via `git rev-parse --git-path` |
| Email con caratteri speciali | `tr -d '\n\r'` + double-quote nell'arg `--trailer` (no eval) |
| `interpret-trailers` fallisce/assente | `--in-place` non tocca il file → `COMMIT_EDITMSG` invariato, commit procede |
| Opt-out per-commit (non per-repo) | `DEVFORGE_SKIP_TRAILER_HOOK=1` è check a INSTALL-time; per saltare un singolo commit usare `git commit --no-verify` |
| Cherry-pick | source=`message` → trailer iniettato (comportamento corretto e intenzionale) |

### Testing (TDD) — Comp.4
1. Installer crea `prepare-commit-msg` con marker + eseguibile in repo fresco.
2. Installer idempotente (2ª esecuzione no-error, hook presente).
3. Installer **skippa** hook estraneo (pre-esistente senza marker resta intatto).
4. Opt-out `DEVFORGE_SKIP_TRAILER_HOOK=1` → nessun hook.
5. E2E: `git commit -m x` in repo con hook + fixture → messaggio contiene `DevForge-Author: <email>`.
6. E2E idempotenza: amend non duplica il trailer.
7. Best-effort: no `~/.claude.json` → commit OK senza trailer.
8. session-start invoca l'installer.
9. **Safety (BLOCK Q8):** con `interpret-trailers` reso indisponibile/fallente, `git commit` procede e
   il messaggio originale è PRESERVATO (non azzerato).

### Criteri di accettazione — Comp.4
- [ ] `lib/install-trailer-hook.sh` installa un `prepare-commit-msg` idempotente, marker-guarded, zero-harm su hook estranei.
- [ ] L'hook timbra `DevForge-Author: <sso-email>` su commit normali, skip merge/squash, mai blocca (exit 0).
- [ ] Idempotente per-token (no duplicati su amend); usa `--in-place`.
- [ ] **`COMMIT_EDITMSG` invariato se `interpret-trailers` fallisce/è assente** (no data loss).
- [ ] Opt-out via `DEVFORGE_SKIP_TRAILER_HOOK=1` (install-time); per-commit via `--no-verify`. Documentato in ENV_VARS.md.
- [ ] session-start invoca l'installer (foreground, fast).

## 8. Copertura: la condizione organizzativa (nota, non codice)
Il 100% vale solo per il lavoro **timbrato** da DevForge. Commit fatti fuori DevForge (git manuale)
non hanno `commit_sha`/`auth_email` → restano inferenza. 100% attribuzione ⟺ ~100% adozione DevForge
(in primis team mirror: Engineering Sport, Reply). Fuori scope codice; tracciato per la narrativa.

## 9. Testing (TDD)
1. `repo_remote` presente e = `git remote get-url origin` in `commit_created` e in un evento generico.
2. `repo_remote` = "" se repo senza origin (no crash).
3. `devforge_resolve_auth_identity`: estrae email/uuid da `~/.claude.json` fixture con `oauthAccount`.
4. resolve = "" se fixture senza `oauthAccount` (caso Bedrock) — no crash.
5. `devforge_identity_bundle` include i 4 campi `auth_*`.
6. Evento generico porta `auth_email`/`auth_account_uuid` top-level quando pinnati via env.
7. No-regression: `user`/`user_raw`/`user_source`/`actor_canonical` invariati; JSON resta parsabile (jq/python) — verificato su ENTRAMBE `devforge_log` E `devforge_log_timed`.
8. session-start scrive `auth_email` in `user.json`; `init_session` esporta `DEVFORGE_AUTH_EMAIL`.

## 10. Criteri di accettazione
- [ ] Ogni evento (`devforge_log` + `devforge_log_timed`) porta top-level `auth_email`, `auth_account_uuid`, `repo_remote`.
- [ ] `commit_created` conserva `commit_sha` nel meta + ha `repo_remote` top-level.
- [ ] `identity` bundle (session_start.meta + user.json) include `auth_email`/`auth_account_uuid`/`auth_org_uuid`/`auth_org_name`.
- [ ] Tutti i campi best-effort: empty string senza crash su `~/.claude.json` assente, no-oauthAccount, no python3, no-origin.
- [ ] `user`/`user_raw`/`user_source`/`actor_canonical` invariati (no-regression verificato da test).
- [ ] JSONL resta valido (schema_version=2, additivo).
- [ ] Trailer `DevForge-Author` documentato come follow-up ADR (non implementato qui).
- [ ] Docs aggiornate: `docs/handover/` (nuovi campi per consumer) + `hooks/ENV_VARS.md` (DEVFORGE_AUTH_*).

## 11. Stima SP
- Umano: 5 SP (multi-file bash, edge case auth, test cross-platform).
- Augmented (Claude Code): 2 SP.
