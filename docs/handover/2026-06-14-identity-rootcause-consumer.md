---
status: handover
owner: Lorenzo De Tomasi
created: 2026-06-14
target: developer-telemetry (consumer)
reviewer: owner repo developer-telemetry
topic: Contratto root-cause identità — ritiro band-aid (cross-platform)
supersedes_partial: docs/handover/2026-06-08-attribution-determinism-fields.md (additivo, non sostitutivo)
branch: feat/identity-rootcause-crossplatform
---

# Handover — Contratto root-cause identità dev (consumer developer-telemetry)

## Contesto

Il branch `feat/identity-rootcause-crossplatform` completa la soluzione root-cause all'attribuzione
identità dev portando l'intero stack producer a coprire Windows (Git Bash) + macOS + Linux. Tutti
i campi necessari a rendere i band-aid non necessari sono ora emessi in modo cross-platform.

Questo documento è il contratto operativo perché il consumer `developer-telemetry` ritiri i
band-aid esistenti e adopti i dati root-cause. È **additivo** rispetto a
`2026-06-08-attribution-determinism-fields.md` (leggere prima per la base `auth_*`/`repo_remote`).

**Principio:** il producer emette dati **RAW** e marcatori di semantica. Ogni sanitizzazione,
cap, mediana, flag è responsabilità del consumer.

---

## Campi nuovi e modificati emessi da questo branch

Verifica del codice effettivo (grep su `lib/logger.sh` + `hooks/post-commit-review` +
`lib/install-trailer-hook.sh`, branch `feat/identity-rootcause-crossplatform`).

| Campo | Evento/i | Semantica | File sorgente |
|---|---|---|---|
| `repo_slug` | tutti (ogni evento `devforge_log` e `devforge_log_timed`) | `org/repo` normalizzato da `repo_remote`: strip schema, host, `.git`; ultimi due segmenti path. Vuoto se remote assente. Copre SSH (`git@host:org/repo.git`) e HTTPS (`https://host/org/repo.git`). | `lib/logger.sh` (`devforge_repo_slug()` + `devforge_log`/`devforge_log_timed`) |
| `pr_author_emails` | `pr_opened`, `pr_merged` | Array JSON di email distinte degli autori reali dei commit della PR. Deriva dal trailer `DevForge-Author` via `git log --format='%(trailers:key=DevForge-Author,valueonly)'` sul range `<merge-base>..<head>`. Vuoto `[]` su PR senza commit DevForge (vedi P5 sotto). | `hooks/post-commit-review` (`_devforge_pr_author_emails_json()`, linee 102–149) |
| `host` (in `session_start.meta.identity`) | `session_start` | Short hostname, mai FQDN: `host="${host%%.*}"` — uguale su tutti i OS (ADR-7). Su Linux rimuove il suffisso dominio (`engsport08.itsiae.it` → `engsport08`); su Windows già short. | `lib/logger.sh` (`devforge_build_identity_bundle()`, linea 367) |
| `duration_source` | eventi temporizzati (`devforge_log_timed`, es. `session_start`, `session_end`, `commit_created`, `pr_opened`, `pr_merged`) | Valore fisso `"wallclock"`: indica che `duration_ms` è misurato via epoch-ns (clock di parete), non tempo CPU. Il consumer deve applicare cap e mediana — il producer non li applica (ADR-4). | `lib/logger.sh` (`devforge_log_timed`, linea 775) |
| `telemetry_degraded` | evento autonomo (nuovo) | Emesso quando manca un prerequisito cross-platform. `meta.reason` può essere `"no_json_interpreter"` (node e python3 assenti → `auth_*` vuoti, `repo_slug` vuoto) oppure `"no_fsync_interpreter"` (node e python3 assenti sul write-path → scrittura senza fsync). Da escludere dai conteggi di produttività; usare come metrica di salute infrastrutturale. | `lib/logger.sh` (linee 172–183 e 869) |
| `trailer_hook_skipped_old_git` | evento autonomo (nuovo) | Emesso da `install-trailer-hook.sh` nel contesto di `session-start` quando `git interpret-trailers` è assente o git < 2.15. Indica che il trailer `DevForge-Author` non sarà scritto su quei commit. `meta.git_version` riporta la versione rilevata. | `lib/install-trailer-hook.sh` (linea 56) |

**Regola di consumo:** tutti i nuovi campi vanno letti con `.get(...)` e default (eventi storici
pre-branch non li hanno). `user`, `user_raw`, `user_source`, `actor_canonical` sono invariati.

---

## P1 / P3 — Join deterministico (Mirror + git config errata)

Con `auth_email`/`auth_account_uuid` (già DONE, `2026-06-08`), `commit_sha` e trailer
`DevForge-Author` (aggiunto da `lib/install-trailer-hook.sh` a ogni commit), l'attribuzione
diventa un **join**, non un'inferenza.

**Azione consumer:**

- Usare `auth_account_uuid` (o `auth_email` come fallback) come ramo **PRIORITÀ -2** nel
  resolver, sopra l'identity bundle git/os/host.
- Disattivare `lib_actor_match`, gate `07c`, `07e`, `07g` **scoped al lazo DevForge**: restano
  come fallback esclusivamente per eventi senza `auth_*` (Bedrock/API-key, commit git manuali).
- Join `commit_sha` ↔ commit GitHub rimane il meccanismo anti-mirror (lo SHA non cambia con il
  mirror perché il trailer entra nel contenuto del commit).
- Dove `trailer_hook_skipped_old_git` è emesso per una macchina, il trailer sarà assente nei
  commit da quella macchina: il join `auth_*` è ancora disponibile, ma non il trailer.

---

## P2 — Detector degeneranza account condivisi

Il producer emette `session_start.meta.identity.host` come **short hostname** (ADR-7, già
verificato nel codice: `host="${host%%.*}"`). Il consumer può ora fare il join `(host, os_user)`
in modo stabile cross-OS.

**Azione consumer — detector:**

```python
# Raggruppa eventi session_start per (host_short, os_user)
# e conta distinct auth_account_uuid nel tempo.
# Many-persone → 1 uuid = account degenere (box condiviso, CLAUDE_CONFIG_DIR non settato).
# 1 box → N uuid nel tempo = isolamento OK.

for (host, os_user), events in group_by(session_starts, key=lambda e: (
    e["meta"]["identity"]["host"],   # già short name dal producer (ADR-7)
    e["meta"]["identity"]["os_user"]
)):
    distinct_uuids = {e["auth_account_uuid"] for e in events if e.get("auth_account_uuid")}
    if len(distinct_uuids) == 1 and len(events) > THRESHOLD:
        flag_degenerate(host, os_user, list(distinct_uuids)[0])
```

**Retrocompatibilità (WARN-1):** eventi storici pre-ADR-7 (pre-branch) possono avere `host`
come FQDN (`engsport08.itsiae.it`) su Linux. Normalizzare nel consumer prima del join:

```python
host_short = identity.get("host", "").split(".")[0]
```

**Hare-quota:** applicare solo al **residuo** effettivamente degenere (distint uuid = 1),
non ai box con isolamento corretto.

---

## P4 — `dim_identity` da eventi S3 (ritiro dipendenza PAT audit-log)

**Problema attuale (band-aid):** `dim_identity` costruita dal PAT audit-log (GitHub), retention
7 giorni → dev senza commit su main recenti spariscono dalla dimensione.

**Root-fix:** ogni evento porta `auth_account_uuid` e `auth_email` top-level, su S3 (durevole).

**Azione consumer:**

- Costruire `dim_identity` **dagli eventi S3**, usando `auth_account_uuid` come chiave primaria
  e `auth_email` come chiave alternativa/fallback (in caso di `auth_account_uuid` vuoto = Bedrock).
- Il primo evento che porta una coppia `(auth_account_uuid, auth_email)` valorizzata arricchisce
  la dimensione; eventi successivi la aggiornano solo se cambiano.
- Eliminare la dipendenza dal PAT audit-log e dalla retention 7gg.
- I dev che lavorano solo da Bedrock/API-key avranno `auth_account_uuid=""` → usare
  `auth_email` o restare nell'identity bundle git (`git_local_email`) come fallback.

---

## P5 — PR author reale (`pr_author_emails[]`) e flagging `non_observable`

**Problema attuale (band-aid):** `pr_author` = chi ha aperto la PR su GitHub (l'integratore NTT
o pun-spa), non gli autori reali del codice.

**Root-fix:** `pr_opened` e `pr_merged` portano `pr_author_emails[]` (array).

**Semantica del campo:**

- **PR con commit DevForge:** `pr_author_emails` è l'insieme distinto delle email SSO (`auth_email`)
  estratte dal trailer `DevForge-Author` dei commit della PR. Rappresenta i dev reali che hanno
  prodotto il codice.
- **PR senza commit DevForge** (codice scritto fuori workflow, path catch-up/orphan): il producer
  emette `pr_author_emails: []` by design. Il commento nel codice lo esplicita:
  *"Calling `_devforge_pr_author_emails_json` here would compute merge-base against wrong HEAD
  and return incorrect or empty authors. Emit [] best-effort."*

**Azione consumer:**

```python
if event["event"] in ("pr_opened", "pr_merged"):
    authors = event.get("meta", {}).get("pr_author_emails", [])
    if authors:
        pr_real_authors = set(authors)
    else:
        # Vuoto = PR senza commit DevForge o path catch-up/orphan
        # Non è 0 autori: è "non osservabile con i dati disponibili"
        pr_real_authors = NON_OBSERVABLE   # mai 0, mai inferenza
```

- **Non usare mai `0`** come valore di fallback: significherebbe "nessun autore", che è falso.
- `NON_OBSERVABLE` esclude la PR dai KPI che richiedono autore reale, senza distorcere i totali.

---

## 6c — Token per-sessione: valore finale, non media del cumulativo

**Problema attuale (band-aid):** la media di `session_tokens_cumulative` (presente in
`pr_merged.meta`) produce valori gonfiati (media armonico su 246M token).

**Dati disponibili:**

- `session_end.meta.total_tokens` — valore **finale** della sessione (unico, autorevole).
- `pr_merged.meta.session_tokens_cumulative` — snapshot cumulativo al momento del merge
  (può essere letto prima della `session_end`).

**Azione consumer:**

```python
# PER SESSIONE:
# Fonte preferita: session_end.total_tokens (valore finale definitivo).
# Fallback: session_tokens_cumulative dell'ultimo pr_merged della sessione.
# MAI: media di session_tokens_cumulative su più eventi della stessa sessione.

if session_end_found:
    tokens_for_session = session_end["meta"]["total_tokens"]
else:
    tokens_for_session = max_by_seq(pr_merged_events)["meta"]["session_tokens_cumulative"]

# PER AGGREGAZIONE:
# Usare la mediana dei token-per-sessione tra le sessioni del periodo, non la media.
# La distribuzione è asimmetrica (sessioni lunghe con migliaia di tool calls distorcono la media).
tokens_kpi = median([tokens_for_session(s) for s in sessions_in_period])
```

---

## 6d — `duration_ms`: cap 8 ore e mediana

**Problema attuale (band-aid):** `duration_ms` include idle (sessione aperta overnight → 22h/gg).

**Dato disponibile:** `duration_ms` è `wallclock` puro; `duration_source: "wallclock"` è il
marcatore emesso dal producer (`lib/logger.sh:775`, fisso su tutti gli eventi `devforge_log_timed`).

**Azione consumer:**

```python
MAX_SESSION_DURATION_MS = 8 * 60 * 60 * 1000   # cap 8 ore

def session_duration(event):
    if event.get("duration_source") == "wallclock":
        return min(event["duration_ms"], MAX_SESSION_DURATION_MS)
    return event["duration_ms"]   # sorgente futura con semantica diversa: non cappare

# Aggregazione: mediana, non media (distribuzione asimmetrica).
duration_kpi = median([session_duration(e) for e in session_ends_in_period])
```

---

## Note di qualità del segnale `telemetry_degraded`

Il segnale `telemetry_degraded` va usato come **health indicator**, non come evento da contare
nel lavoro dei developer:

| `meta.reason` | Significa | Azione consigliata |
|---|---|---|
| `no_json_interpreter` | node e python3 assenti su quella macchina → `auth_*` vuoti, `repo_slug` vuoto. Tutti gli eventi della sessione non sono attribuibili via SSO. | Escludere la sessione dai KPI che richiedono `auth_account_uuid`. Alertare il team infra per installare node o python3. |
| `no_fsync_interpreter` | node e python3 assenti sul write-path → durabilità ridotta (lock `mkdir` + no fsync). | Monitorare % sessioni degradate su Windows. Non impatta l'attribuzione. |

Il segnale `trailer_hook_skipped_old_git` indica che su quella macchina il trailer `DevForge-Author`
sarà assente da tutti i commit. Il join deterministico P1/P3 resta disponibile via `auth_*`
top-level (non è perso, è solo meno robusto al mirror per quei commit).

---

## Riepilogo band-aid da ritirare (per lazo DevForge)

| Band-aid | Condizione di ritiro | Fallback da mantenere |
|---|---|---|
| `lib_actor_match` (fuzzy resolver os_user/host) | `auth_account_uuid` valorizzato sull'evento | Sì, per eventi senza `auth_*` (Bedrock, git manuale) |
| Gate `07c` (gonfiamento mirror 815 commit) | `commit_sha` + trailer `DevForge-Author` coprono i commit della PR | Sì, per commit pre-branch senza trailer |
| Gate `07e` (stima push-share) | `auth_*` top-level su ogni evento | Sì, per eventi storici |
| Gate `07g` (branch-bridge) | `repo_slug` + `auth_*` coprono il mapping repo | Sì, per eventi senza `repo_slug` |
| `dim_identity` da PAT audit-log | `auth_account_uuid`/`auth_email` su eventi S3 coprono tutti i dev attivi | No (S3 è la fonte primaria) |
| Hare-quota globale | Detector degeneranza scoped (P2) — applicare solo al residuo degenere | Sì, sul residuo `distinct auth_account_uuid = 1` |

**Scoping obbligatorio:** non rimuovere i band-aid per gli eventi storici pre-branch o per il
lavoro proveniente da Bedrock/API-key (dove `auth_*` è vuoto). Il ritiro è selettivo, non globale.

---

## Riferimenti

- Design completo: `docs/plans/2026-06-14-dev-identity-rootcause-crossplatform-design.md`
- Piano task: `docs/plans/2026-06-14-dev-identity-rootcause-crossplatform/overview.md`
- Handover precedente (base `auth_*`): `docs/handover/2026-06-08-attribution-determinism-fields.md`
- Guida isolamento account condivisi: `docs/handover/2026-06-14-shared-account-isolation.md`
- Script diagnosi: `scripts/diagnose-identity.sh`
