---
status: handover
owner: Lorenzo De Tomasi
created: 2026-06-08
target: developer-telemetry (consumer)
topic: Campi attribuzione deterministica (auth_email, auth_account_uuid, repo_remote)
supersedes_partial: docs/handover/2026-06-03-telemetry-new-fields.md (additivo, non sostitutivo)
---

# Handover — Campi per attribuzione deterministica dev↔commit↔repo

## Contesto

DevForge è l'unico punto del flusso che conosce l'identità **autenticata** del dev (SSO/login
aziendale) nel momento dell'azione. Questa PR timbra quell'identità (+ lo SHA del commit, già
presente) negli eventi, trasformando l'attribuzione da **inferenza** a **join**. Tutti additivi
(`schema_version` resta 2; campi/eventi esistenti invariati). Regola di consumo: leggere con
`.get(...)` e default — un evento storico non avrà i campi nuovi.

---

## 1. Nuovi campi TOP-LEVEL per-evento (TUTTI gli eventi)

Emessi da `lib/logger.sh` (`devforge_log` + `devforge_log_timed`) → presenti in **ogni** evento,
non solo `commit_created`. Self-attributivi: nessun join obbligatorio con `session_start`.

```json
{
  "event": "commit_created",
  "auth_email": "carmen.lasala@siae.it",   // SSO da ~/.claude.json oauthAccount.emailAddress; "" se Bedrock/API-key o git manuale
  "auth_account_uuid": "1d9cbbdb-9eab-...", // UUID account immutabile; chiave di join PIÙ STABILE dell'email
  "repo_remote": "https://github.com/itsiae/sport-licenze.git", // RAW = `git remote get-url origin`; "" se repo senza origin
  "meta": { "commit_sha": "a1b2c3d4...", ... }  // commit_sha INVARIATO nel meta
}
```

| Campo | Tipo | Sorgente | Vuoto quando |
|---|---|---|---|
| `auth_email` | string | `~/.claude.json` → `oauthAccount.emailAddress` (pinnato a session-start) | Bedrock/API-key auth, o lavoro fuori DevForge |
| `auth_account_uuid` | string | `oauthAccount.accountUuid` | come sopra |
| `repo_remote` | string (RAW) | `git remote get-url origin` | repo senza remote `origin` |

---

## 2. Identity bundle esteso (`session_start.meta.identity` + `user.json.identity`)

L'oggetto `identity` (già consumato a `03_build_facts.py:351`, PRIORITÀ -1) acquisisce 4 campi auth:

```json
"identity": {
  "git_local_email": "...", "git_local_name": "...", "git_global_email": "...",
  "git_global_name": "...", "os_user": "...", "host": "...",
  "auth_email": "carmen.lasala@siae.it",
  "auth_account_uuid": "1d9cbbdb-9eab-...",
  "auth_org_uuid": "779f34e4-56d2-...",
  "auth_org_name": "Information Technology"
}
```

---

## 3. Uso consumer (abilitazione, NON imposizione)

- **Join deterministico:** `auth_account_uuid` (o `auth_email`) come ramo **PRIORITÀ -2**, sopra
  l'identity bundle git/os/host. Risolve i casi: box condiviso (`a200576`), git-config errata/vuota
  (Carmen `root@calasalaw1`), SSO `AzureAD+...`.
- **Mapping repo reale:** `repo_remote` mappa l'evento al repo GitHub/GitLab effettivo, sopra il
  `project` code interno (`analisi_licenze` → URL reale).
- **Mirror GitLab→GitHub:** `commit_sha` (già in `commit_created`/`pr_commit_after_open`) **non
  cambia** col mirror (cambia solo l'autore). Join `commit_sha`↔commit GitHub = attribuzione 100%
  del lavoro DevForge anche dopo il mirror.
- **Eliminazione inferenza (scope consumer):** con questi campi, `lib_actor_match` (resolver
  os_user/host), `07e` (stima push-share), `devforge_*_aliases.csv`, `repo_root_aliases` diventano
  non necessari; `03_build_facts` attribuisce per join e `resolution` → `deterministic`.

---

## 4. Regola di consumo
Leggere con `.get(...)` e default. Eventi pre-feature non hanno i campi (graceful). `actor_canonical`
/`user`/`user_raw`/`user_source` sono **invariati** (no-regression): la chain di attribuzione esistente
resta valida come fallback.

## 5. Coverage caveat (condizione del 100%)
Determinismo 100% solo per il lavoro **timbrato** da DevForge **di utenti OAuth/SSO**:
- Auth via **Bedrock/API-key** → `oauthAccount` assente → `auth_email`/`auth_account_uuid` = "" →
  fallback alla chain esistente. Nessuna regressione, ma nessun guadagno deterministico per quegli eventi.
- **Commit fuori DevForge** (git manuale) → niente `auth_*`/`repo_remote`/`commit_sha` → restano inferenza.
- ⟹ **100% attribuzione ⟺ ~100% adozione DevForge** dei team (in primis i mirror: Engineering Sport, Reply).

## 6. Trailer `DevForge-Author` — NON ancora emesso
Il trailer firmato nel commit (robustezza oltre la telemetria, per consumer esterni a questa pipeline)
è DEFERRED a follow-up dedicato (richiede git hook `prepare-commit-msg` cross-repo). Il gap mirror è
già chiuso da `commit_sha`. Vedi `docs/plans/2026-06-08-attribution-determinism-design.md` §7.
