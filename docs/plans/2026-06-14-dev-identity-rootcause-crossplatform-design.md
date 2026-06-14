---
title: Risoluzione root-cause dello spacchettamento identità dev — soluzione cross-platform (Windows + macOS/Linux)
date: 2026-06-14
status: design
author: Lorenzo De Tomasi
scope: producer (siae-dev-forge) + handover consumer (developer-telemetry)
supersedes: nessuno (additivo a 2026-06-08-attribution-determinism + 2026-06-02-developer-identity-bundle)
---

# Risoluzione root-cause — spacchettamento identità dev (cross-platform)

## 1. Contesto e obiettivo

L'attribuzione di commit / PR / sessioni ai dev reali è corrotta da 6 cause a monte. La
ricognizione ha stabilito che la **soluzione root-cause è in gran parte già implementata**
lato producer (attribution determinism Comp.1-4, PR #297 + branch 2026-06-08): ogni evento
porta `auth_email`, `auth_account_uuid`, `repo_remote` top-level (da OAuth SSO locale, immuni
a mirror/git-config) e ogni commit porta il trailer `DevForge-Author` (sopravvive al mirror
perché entra nello SHA). I "band-aid" (`lib_actor_match`, Hare-quota, gate 07c, branch-bridge
07g, `dim_identity` da PAT audit-log) vivono nel consumer `developer-telemetry` (fuori workspace).

**Obiettivo (goal utente 2026-06-14):** per OGNI problema, una soluzione **totale e cross-platform
(Windows + macOS/Linux)** che renda i band-aid non necessari, sfruttando l'identità SSO catturata
a monte di ogni mangling.

**Verità empirica accertata in questa sessione:**
- Leg macOS funzionante: 775 eventi locali, 98% con `auth_*` valorizzati, tutti i campi top-level presenti.
- `.gitattributes` ASSENTE → rischio CRLF su Windows confermato.
- Identità parsata solo via `python3` → non portabile su Windows (Git for Windows non include python3).
- Hook eseguiti su Windows via Git Bash (default doc Anthropic), shebang già portabili.

## 2. Scope

- **In scope:** producer `siae-dev-forge` (questo repo) — root-fix implementabili + fondamenta cross-platform.
- **In scope:** handover spec per il consumer `developer-telemetry` (repo assente dal workspace) per i fix che sono strutturalmente consumer (problemi 4, 5, 6c, 6d).
- **Fuori scope:** modifica diretta di `developer-telemetry` e della dashboard `siae-telemetry-control-tower` (solo handover/contratto).
- **Piattaforme target:** Windows nativo (Git Bash), macOS, Linux. Tutte e tre obbligatorie (team mirror/condivisi/misconfig sono misti — confermato dall'utente).

## 3. Stato attuale — NON riprogettare (già DONE)

| Meccanismo | Dove | Stato |
|---|---|---|
| `auth_email` + `auth_account_uuid` top-level ogni evento | `lib/logger.sh` `devforge_log`/`devforge_log_timed` | DONE |
| `repo_remote` raw top-level ogni evento | idem | DONE |
| `devforge_resolve_auth_identity()` legge `~/.claude.json` | `lib/logger.sh:295` | DONE (python3-only — vedi F2) |
| Identity bundle (10 campi: git/os/host + 4 auth) | `lib/logger.sh:261` + `hooks/session-start` | DONE |
| Trailer `DevForge-Author` via `prepare-commit-msg` | `lib/install-trailer-hook.sh` | DONE (python3-only — vedi F2) |
| `commit_sha` join-key in `commit_created` | `hooks/post-commit-review` | DONE |
| `task_id` join-key (Layer 1 adoption) | branch corrente `feat/telemetry-adoption-events` | in corso |

## 4. Fondamenta cross-platform (cross-cutting — abilitano i problemi 1,3,4,5)

Questi due pilastri sono la radice del "totale per Windows e OS": senza di essi i root-fix esistenti
**girano solo su mac/Linux** e degradano in silenzio su Windows.

### F1 — Line-ending safety (root del fallimento `\r: command not found`)
- **Causa:** nessun `.gitattributes`. Un checkout Windows con `core.autocrlf=true` riscrive gli `*.sh`
  e l'hook `prepare-commit-msg` con CRLF → Git Bash fallisce.
- **Fix:** aggiungere `.gitattributes` al repo: forzare `eol=lf` su tutti gli script shell e hook.
  ```gitattributes
  * text=auto
  *.sh text eol=lf
  hooks/* text eol=lf
  lib/*.sh text eol=lf
  ```
- **Trailer hook installato runtime:** l'installer scrive `prepare-commit-msg` via heredoc → su Windows
  eredita i LF del processo bash, quindi è già LF-safe. Aggiungere comunque un commento normativo
  e un test che verifichi assenza di CR nel file generato.
- **Vincolo interprete:** gli hook usano bashism (`[[ =~ ]]`, `BASH_REMATCH`, `local`) → il requisito è
  **Git Bash (bash 5.x)**, NON `sh` generico. Documentato esplicitamente; coerente con gli shebang `#!/usr/bin/env bash`.
- **Cross-platform:** Windows ✅ (risolve la rottura) · mac/Linux ✅ (no-op).

### F2 — Portabilità interprete identità (root della copertura Windows mancante)
- **Causa:** `devforge_resolve_auth_identity()` (`logger.sh:297`), `devforge_init_session()`
  (`logger.sh:437-442`, pinning identità), `devforge_get_user_raw/source` (`logger.sh:381/394`),
  `devforge_session_token_total` (`logger.sh:319`) e il trailer hook (`install-trailer-hook.sh:44`)
  usano `command -v python3` come unica via per leggere JSON. Git for Windows NON include python3 →
  su Windows senza python3 → `auth_*` vuoti, pinning vuoto, trailer assente → root-fix degrada ai band-aid.
- **Fix:** funzione bash unica `devforge_json_field <file> <dotted.path>` in `lib/logger.sh` con **fallback chain**:
  1. `node -e` (parser JSON nativo) →
  2. `python3` (fallback attuale, mac/Linux) →
  3. degrado esplicito: campo vuoto + segnale osservabile `telemetry_degraded` (`meta.reason="no_json_interpreter"`).
- **Scope completo (WARN-2):** `devforge_json_field` sostituisce TUTTI i siti identità-critici sopra elencati
  (resolve_auth, init_session pinning, get_user_raw/source), non solo `resolve_auth`. `devforge_session_token_total`
  resta python3-friendly ma instradato sulla stessa chain (non identità-critico: degrado → token 0, già gestito).
- **Trailer hook (`git interpret-trailers`) — guard cross-platform (BLOCK-2):** `--if-exists` richiede **git ≥ 2.15**.
  - *Capability check + emissione a INSTALL-TIME (BLOCK-2-EMIT):* il `prepare-commit-msg` generato è un subprocess
    isolato SENZA `lib/logger.sh` né variabili di sessione → NON può chiamare `devforge_log`. Quindi la capability
    check (`git interpret-trailers --help >/dev/null 2>&1` + versione ≥ 2.15) è eseguita da `install-trailer-hook.sh`,
    che gira nel contesto di `session-start` (logger già sourceato): se fallisce emette `trailer_hook_skipped_old_git`
    all'installazione e installa comunque il hook (best-effort). Razionale: la versione di git è stabile entro la
    sessione → l'esito install-time è un proxy fedele del comportamento per-commit.
  - *Hook generato:* resta puramente best-effort — cattura l'exit code di `interpret-trailers` (no `2>/dev/null`
    blanket) e su fallimento runtime NON scrive il trailer ma esce 0 (mai blocca il commit). Edge case "git degradato
    dopo l'install entro la stessa sessione" = rischio residuo accettato (non emette segnale).
- **Re-deploy su macchine già configurate (BLOCK-1):** l'installer riscrive `prepare-commit-msg` ad ogni session-start
  solo se il marker corrisponde (`install-trailer-hook.sh:26`). Per propagare F2 il marker va **bumpato
  `DEVFORGE-TRAILER-HOOK v1` → `v2`**: i vecchi hook (senza node-fallback e senza git-guard) vengono così riscritti
  automaticamente alla sessione successiva, senza azione utente.
- **Verifica BLOCCANTE (Task 0, non differibile — BLOCK-1):** misurare la presenza di `node`/`python3` su PATH
  negli hook Windows nativi. Fonte empirica già disponibile: `hooks/session-start:194` usa `node` con fallback
  a stringa vuota per `skills-core.js` → la % di sessioni Windows con warning catalogo è già un proxy della
  disponibilità node. Esito del Task 0 decide: `node` affidabile → F2 node-first; `node` assente → `python3`
  prerequisito Windows obbligatorio nell'installer + segnale `telemetry_degraded` mantenuto.
- **Cross-platform:** Windows ✅ (via node se su PATH, altrimenti python3-prereq + degrado osservabile) · mac/Linux ✅ (invariato).

### F3 — Semantica `host` consistente cross-OS (root del join `(host, os_user)` spezzato — WARN-1)
- **Causa:** `logger.sh:269` usa `hostname -s 2>/dev/null || hostname`. Su Linux il fallback `hostname` ritorna
  l'**FQDN** (`engsport08.itsiae.it`); su Windows Git Bash `hostname` ritorna già lo **short name** (`engsport08`).
  Stesso box → valore `host` diverso per OS → il detector P2 che fa join `(host, os_user)` si spezza cross-OS.
- **Fix:** normalizzare a short name al producer: `host="${host%%.*}"` dopo la risoluzione. Semantica unica
  ("short hostname") su tutte le piattaforme — è coerenza di campo, NON una metrica derivata (rispetta ADR-4).
- **Cross-platform:** Windows ✅ (no-op) · mac/Linux ✅ (strip dominio → join stabile).

### F4 — Write-path zero-loss su Windows senza interprete (requisito esplicito: "non possiamo perderci dati")
- **Causa:** `lib/atomic_write.py` (lock `flock` + `fsync`) è **python3-only**. Su Windows senza python3 il
  writer cade sul fallback `printf >>` (`logger.sh:62-90`) **senza lock né fsync** → perdita dati sotto
  concorrenza (hook/subagent paralleli) o crash. F2 espone esplicitamente questo path.
- **Fix (additivo, NON tocca il path python3 shipped):** fallback chain di append durabile —
  1. `python3` `atomic_write.py` (flock + fsync) — primario, invariato →
  2. `node` `lib/atomic_append.js` (NUOVO): lock advisory portabile via `mkdir` (già usato nell'outbox) +
     `O_APPEND` + `fs.fsyncSync` →
  3. bash degradato: lock `mkdir` + `printf` (no fsync) + evento `telemetry_degraded` (`reason="no_fsync_interpreter"`).
  Il lock `mkdir`-based (portabile, zero-interprete) serializza i writer concorrenti su TUTTI i path → chiude il
  gap di concorrenza anche su Windows-senza-python3.
- **Verifica esaustiva:** suite data-loss (concorrenza 50-writer, crash mid-write, no-interprete, node-only,
  outbox replay, cursor integrity) con assert numerico `conteggio righe = eventi emessi`. Vedi AC 14.
- **Relazione con cluster-2 #4:** il path python3 zero-loss è GIÀ shipped (PR-A + flush-storm). F4 chiude solo
  il ramo cross-platform che le mie modifiche F2 toccano — non riprogetta il writer.
- **Cross-platform:** Windows ✅ (durabilità via node, lock via mkdir) · mac/Linux ✅ (invariato).

## 5. Matrice per-problema (cross-platform)

Per ogni problema: **radice → root-fix → copertura Windows → copertura mac/Linux → band-aid ritirato → nuovo lavoro**.

### Problema 1 — Mirror GitLab→GitHub (61% dev, 815/899 commit falsi)
- **Radice:** identità derivata da git author, riscritto dal bot mirror.
- **Root-fix:** `auth_email`/`auth_account_uuid` (OAuth, immuni) + trailer `DevForge-Author` (entra nello SHA → il mirror non può riscriverlo senza invalidare lo SHA) + join su `commit_sha`. **Già DONE.**
- **Windows:** completo SOLO con F1+F2 (altrimenti trailer/auth vuoti).
- **mac/Linux:** funzionante (98% locale).
- **Ritira:** falso gonfiamento 07c (es. Santaniello 18→233), `lib_actor_match` per i commit DevForge.
- **Nuovo lavoro:** F1 + F2.

### Problema 2 — 3 account Linux condivisi (10+ dev: engsport08, a200576)
- **Radice:** `$HOME` condiviso → un solo `~/.claude.json` → `auth_account_uuid` degenera all'ultimo login (concorrenza/no re-auth).
- **Root-fix (Option Zero, processo/env):** isolamento config per-persona via `CLAUDE_CONFIG_DIR=$HOME/.claude-$REAL_USER` esportato nel profilo shell di ogni dev (o sotto-profilo OS per-persona). Con config isolata, `auth_*` torna 1:1 con la persona anche su account OS condiviso.
- **Strumentazione (già DONE lato dato):** il bundle `session_start.meta.identity` porta già `os_user`+`host`+`auth_*` → la degeneranza è **rilevabile** a valle senza nuovi campi.
- **Verifica BLOCCANTE `CLAUDE_CONFIG_DIR` (BLOCK-3):** il fix dipende da una funzionalità non documentata
  ufficialmente → va verificata PRIMA di dichiararlo, non assunta. Esito:
  - se Claude Code onora `CLAUDE_CONFIG_DIR` → isolamento per-persona via export nel profilo shell (root-fix).
  - se NON lo onora → il fallback diventa **obbligatorio, non opzionale**: lancio per-persona che fissa `HOME`
    isolato (`HOME=/home/shared/.devforge-personas/$REAL_USER claude ...`) o sotto-account OS per-persona.
- **Test empirico "testalo" (deliverable):**
  - *Probe producer* (`scripts/diagnose-identity.sh`, cross-platform) — output a chiave=valore, una riga per campo:
    `HOME`, `CLAUDE_CONFIG_DIR` (+ esito `onorato=si/no` confrontando il path effettivo del file letto),
    `claude_json_path`, `claude_json_exists`, `oauth_email`, `oauth_account_uuid` (mascherato), `os_user`, `host_short`,
    `json_interpreter` (node|python3|none). Riga finale `VERDICT: ISOLATED | SHARED-DEGENERATE | NO-AUTH`.
    Eseguito da ogni dev su un box condiviso rivela se ottengono identità distinte.
  - *Detector consumer* (handover): raggruppa eventi per `(host_short, os_user)` e conta `distinct auth_account_uuid`.
    Many-persone→1 uuid = degenere; 1 box→N uuid nel tempo = isolamento OK.
- **Windows:** account OS condiviso meno comune ma possibile; stesso fix/verifica `CLAUDE_CONFIG_DIR` su Windows.
- **mac/Linux:** i box reali condivisi.
- **Ritira:** Hare-quota per il lavoro DevForge (resta solo come fallback sul residuo non isolato, scoped).
- **Nuovo lavoro:** probe `diagnose-identity.sh` + guida isolamento per-persona + **verifica bloccante** `CLAUDE_CONFIG_DIR` + detector nell'handover.

### Problema 3 — git config errata/non autenticata (root@host, email collega, bot)
- **Radice:** identità da git config, inaffidabile.
- **Root-fix:** `auth_*` bypassa git config; trailer timbra l'email SSO. **Già DONE.**
- **Windows:** F1+F2.
- **mac/Linux:** funzionante.
- **Ritira:** normalizzazione SSO-prefix (`AzureAD+`/`USERSAD+`/`dominio\`), split camelCase, strip hostname seriali, levenshtein di `lib_actor_match` — per il lavoro DevForge.
- **Nuovo lavoro:** F1 + F2.

### Problema 4 — PAT identity ≠ commit identity + retention 7gg
- **Radice:** `dim_identity` costruita dal PAT audit-log effimero (7gg) → dev senza commit su main persi.
- **Root-fix:** ricostruire `dim_identity` dagli eventi S3 **durevoli** chiave `auth_account_uuid` (già emesso su ogni evento, durevole su S3). L'identità non dipende più dal PAT né dalla retention.
- **Windows/mac/Linux:** producer platform-independent (S3); richiede solo `auth_*` presenti ovunque → F2.
- **Ritira:** dipendenza dal PAT audit-log + perdita a 7gg.
- **Nuovo lavoro:** handover consumer (build `dim_identity` da eventi). Producer: solo F2.

### Problema 5 — Workflow integratore (NTT/pun-spa: 1 dev apre tutte le PR)
- **Radice:** PR author su GitHub = integratore; le PR degli altri non esistono su GitHub.
- **Root-fix:** gli eventi `pr_opened`/`pr_merged` portano l'`auth_email` dell'attore (integratore). Per recuperare gli autori reali: arricchire il meta con `pr_author_emails[]` = set distinto degli autori dei commit della PR. Il caso davvero non osservabile (codice scritto fuori DevForge) → flag `non_observable`, MAI 0.
- **Punto di emissione (WARN-3):** `hooks/post-commit-review` (emette già `pr_opened`/`pr_merged`), non `session-start`.
- **Meccanica di raccolta (WARN-3, portabile):** ricavare il range commit della PR (`git log <base>..<head>` sul branch della PR; il base è il merge-base con il default branch) ed estrarre i trailer:
  `git log <base>..<head> --format='%(trailers:key=DevForge-Author,valueonly)'` → dedup. Fallback per git < 2.32 (formato `%(trailers)` limitato): `git log ... --format='%(trailers:key=DevForge-Author)'` + parsing, oppure `auth_email` correlato per `commit_sha` agli eventi `commit_created` di sessione. PR senza alcun trailer/commit DevForge → `pr_author_emails=[]` + il consumer marca `non_observable`.
- **Windows/mac/Linux:** F2 per auth ovunque; la raccolta è git puro (portabile, attenzione a `%(trailers:...)` ≥ git 2.32 → fallback sopra).
- **Ritira:** nulla (il "flag non osservabile" resta la risposta onesta per il residuo non-DevForge).
- **Nuovo lavoro:** producer arricchisce `pr_*` con `pr_author_emails[]` (in `post-commit-review`) + handover consumer per flagging `non_observable`.

### Problema 6 — Campi DevForge ambigui alla fonte
- **6a `actor_canonical` = git config:** declassato a fonte secondaria, `auth_*` primario. **Già DONE** (additivo, no-regression). Nessun nuovo lavoro.
- **6b `project` ≠ repo GitHub:** emettere `repo_slug` normalizzato (`org/repo`) derivato da `repo_remote` lato producer (parsing bash puro, portabile). Coprire ENTRAMBI i formati (NIT-3): SSH `git@host:org/repo(.git)?` e HTTPS `https://host/org/repo(.git)?` (i dev Windows senza SSH usano HTTPS). Algoritmo: strip schema/host/`user@`/`.git`, prendere gli ultimi due segmenti path `org/repo`. Vuoto se remote assente (no crash). **Nuovo campo producer.**
- **6c `session_tokens_cum` cumulativo → media 246M:** semantica. Il producer emette già il cumulativo (commit) e il finale (`session_end.total_tokens`). Fix = consumer usa **mediana / valore finale per-sessione**, non media del cumulativo. Coerente col principio "telemetria raw-only additiva": producer raw, sanitizzazione a valle. **Handover consumer** + nota di semantica.
- **6d `duration` con idle (22h/giorno) → cap 8h:** raw-only → il producer emette `duration_ms` wallclock raw; il **consumer** applica cap 8h/sessione e usa mediana. Producer aggiunge `meta.duration_source="wallclock"` per esplicitare la semantica. **Handover consumer** + marker.
- **Windows/mac/Linux:** 6b parsing portabile; 6c/6d consumer (platform-independent).
- **Nuovo lavoro:** producer `repo_slug` (6b) + marker `duration_source` (6d) + handover (6c/6d).

## 6. ADR

- **ADR-1 — Hardening additivo, non rewrite (Approccio A).** Bash gira su Windows via Git Bash (obbligatorio per Claude Code). Rewrite Node (B) = rischio regressione e violazione del principio additivo. F2 dà la portabilità del parser senza modulo nuovo.
- **ADR-2 — `node` interprete preferito per il parsing identità.** Claude Code gira su Node → `node` è la via più portabile; `python3` resta fallback. Degrado esplicito + segnale `telemetry_degraded` se nessuno dei due è disponibile (osservabilità della copertura, no silenzio).
- **ADR-3 — Isolamento account condivisi come processo/env, non codice.** `CLAUDE_CONFIG_DIR` per-persona (da verificare empiricamente) anziché logica di disambiguazione nel producer. Coerente con Option Zero.
- **ADR-4 — Producer raw-only.** 6c/6d (mediana, cap idle) sono sanitizzazioni → consumer. Il producer aggiunge solo marker di semantica (`duration_source`) e campi raw normalizzati (`repo_slug`). Coerente con la memoria "telemetry raw-only additive".
- **ADR-5 — Band-aid ritirati solo per il lazo DevForge.** `lib_actor_match`/Hare-quota/07c restano come fallback SCOPED sul residuo non-DevForge (Bedrock/API-key, commit git manuali, codice fuori workflow). 100% deterministico ⟺ ~100% adozione DevForge.
- **ADR-6 — Degrado osservabile, mai silente.** Ogni punto in cui un prerequisito cross-platform manca (no interprete JSON, `git interpret-trailers` assente/legacy, `CLAUDE_CONFIG_DIR` non onorato) emette un segnale telemetrico dedicato (`telemetry_degraded`/`trailer_hook_skipped_old_git`) invece di fallire in silenzio. La copertura diventa una metrica, non un'assunzione.
- **ADR-7 — `host` normalizzato a short name al producer.** Coerenza di campo cross-OS (non metrica derivata): elimina la divergenza FQDN(Linux)/short(Windows) che spezza il join `(host, os_user)`.

## 7. Criteri di accettazione

1. `.gitattributes` presente; `git check-attr eol -- hooks/post-commit-review lib/logger.sh` → `eol: lf`.
2. Il `prepare-commit-msg` generato dall'installer non contiene byte CR (`! grep -q $'\r' <hook>`).
3. `devforge_json_field` legge `oauthAccount.emailAddress` correttamente con `node` (python3 disabilitato) e con `python3` (node disabilitato); con nessuno dei due → stringa vuota + evento `telemetry_degraded` (`reason=no_json_interpreter`) emesso.
4. `auth_email`/`auth_account_uuid` presenti e valorizzati su una sessione simulata con interprete = solo `node` (copre anche il pinning in `devforge_init_session`, non solo `resolve_auth`).
5. **No-regression auth (NIT-4):** dopo il refactoring F2, su sessione con `~/.claude.json` presente, `auth_email` e `auth_account_uuid` restano NON vuoti e identici al baseline pre-F2.
6. `repo_slug` (`org/repo`) corretto su `commit_created` per ENTRAMBI i formati (NIT-3): `git@gitlab.itsiae.it:itsiae/diritti-api.git` → `itsiae/diritti-api` E `https://github.com/itsiae/diritti-api.git` → `itsiae/diritti-api`; vuoto se remote assente (no crash).
7. `pr_opened`/`pr_merged` (emessi da `post-commit-review`) includono `pr_author_emails[]`: lista valorizzata su PR con commit DevForge; `[]` su PR senza commit DevForge.
8. **Trailer guard (BLOCK-2):** con `git interpret-trailers` assente/legacy (< 2.15), `install-trailer-hook.sh` (contesto session-start) emette `trailer_hook_skipped_old_git`; il `prepare-commit-msg` generato non scrive il trailer e non blocca il commit (exit 0).
9. **Isolamento account condivisi (BLOCK-3):** con `CLAUDE_CONFIG_DIR=/tmp/persona-A` settato, l'identità risolta proviene da `$CLAUDE_CONFIG_DIR/.claude.json` e NON da `~/.claude.json`. Se il test dimostra che Claude Code non onora la var → l'AC è soddisfatto dal fallback `HOME`-isolato documentato come obbligatorio.
10. **Probe (WARN-4):** `scripts/diagnose-identity.sh` gira su mac/Linux/Git-Bash sotto `set -euo pipefail`, stampa tutte le chiavi previste (§5 P2) e una riga `VERDICT: ISOLATED|SHARED-DEGENERATE|NO-AUTH`; con `CLAUDE_CONFIG_DIR` non onorato stampa esplicitamente `CLAUDE_CONFIG_DIR onorato=no`.
11. `host` è short name su tutte le piattaforme (ADR-7): `git config`-independent, nessun suffisso dominio (`engsport08`, non `engsport08.itsiae.it`).
12. No-regression: `user`, `user_raw`, `user_source`, `actor_canonical` invariati; suite test esistente verde; nessun nuovo abort negli hook (exit 0 best-effort preservato).
13. Handover consumer in `docs/handover/2026-06-14-identity-rootcause-consumer.md`, reviewer designato = owner `developer-telemetry`, con: dim_identity-da-eventi (P4), flagging non_observable (P5), mediana+cap (6c/6d), detector degeneranza con normalizzazione host (P2/WARN-1).
14. **Write-path zero-loss (F4):** in ogni scenario data-loss (50-writer concorrenti, crash mid-write, no-interprete, node-only, outbox replay) il `conteggio righe JSON valide = conteggio eventi emessi` (zero perdita verificata numericamente); la suite zero-loss esistente (path python3) resta verde; il ramo degradato senza fsync emette `telemetry_degraded`.

## 8. Handover consumer (developer-telemetry) — contratto

**Deliverable:** `docs/handover/2026-06-14-identity-rootcause-consumer.md` · **Reviewer:** owner repo `developer-telemetry`.

- **P4:** costruire `dim_identity` dagli eventi S3 (chiave `auth_account_uuid`, fallback `auth_email`), NON dal PAT audit-log. Eliminare la dipendenza dalla retention 7gg.
- **P5:** PR author reale = unione di `pr_author_emails[]`; se vuoto e PR senza commit DevForge → `non_observable`, mai 0.
- **6c:** metrica token per-sessione = valore finale `session_end.total_tokens` o mediana, MAI media del cumulativo.
- **6d:** `duration` = min(`duration_ms`, cap 8h); usare mediana; rispettare `meta.duration_source`.
- **P2:** detector degeneranza `(host_short, os_user) → distinct auth_account_uuid`. NB (WARN-1): eventi storici pre-ADR-7 possono avere `host` FQDN su Linux → il consumer normalizza con `host.split('.')[0]` prima del join, per compatibilità retroattiva. Hare-quota solo sul residuo degenere.
- **P1/P3:** con `auth_*` + `commit_sha` + trailer, attribuzione = join deterministico; `lib_actor_match`/07c/07e/07g disattivabili sul lazo DevForge.

## 9. Stima SP (doppia scala Umano / Augmented)

| Item | Umano | Augmented |
|---|---|---|
| F1 `.gitattributes` + renormalize + test CR | 1 | 0.5 |
| F2 `devforge_json_field` (node→python3) + segnale degraded + verifica Windows | 3 | 1.5 |
| 6b `repo_slug` producer | 2 | 1 |
| P5 `pr_author_emails[]` | 2 | 1 |
| P2 probe `diagnose-identity.sh` + guida isolamento + test CLAUDE_CONFIG_DIR | 3 | 1.5 |
| 6d marker `duration_source` | 1 | 0.5 |
| Handover consumer (P4/P5/6c/6d/P2) | 2 | 1 |
| **Totale** | **~14** | **~7** |

## 10. Rischi

- `node` non su PATH negli hook Windows nativi → mitigazione: fallback python3 + prerequisito documentato + segnale degraded (osservabile). Quantificato dal Task 0 (proxy: warning catalogo `skills-core.js`).
- `git interpret-trailers` assente o git < 2.15 (policy IT Windows legacy) → trailer non scritto → P1 incompleto su quelle macchine. Mitigazione: capability check + segnale `trailer_hook_skipped_old_git`; requisito **git ≥ 2.15** nelle note installer.
- `CLAUDE_CONFIG_DIR` non onorato → mitigazione: fallback obbligatorio `HOME`-isolato per-persona o sotto-account OS.
- Concorrenza su `~/.claude.json` condiviso anche con isolamento parziale → il detector quantifica il residuo; Hare-quota resta scoped.
- Renormalize line-endings può generare un diff ampio una-tantum → commit dedicato, rivedibile.
