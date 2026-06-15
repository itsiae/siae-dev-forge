# Task 10 — Handover consumer (developer-telemetry)

**Stato:** PENDING
**Dipende da:** task-03, task-05, task-06, task-07
**File:** `docs/handover/2026-06-14-identity-rootcause-consumer.md` (nuovo)
**Reviewer:** owner repo `developer-telemetry`

## Obiettivo
Contratto perché `developer-telemetry` ritiri i band-aid e usi i campi root-cause.

## Contenuto (dal design sez. 8)
- **P4:** `dim_identity` da eventi S3 (chiave `auth_account_uuid`, fallback `auth_email`), NON da PAT audit-log; eliminare la dipendenza dalla retention 7gg.
- **P5:** PR author reale = unione `pr_author_emails[]`; se vuoto e PR senza commit DevForge → `non_observable`, mai 0.
- **6c:** token per-sessione = valore finale `session_end.total_tokens` o mediana, MAI media del cumulativo.
- **6d:** `duration` = `min(duration_ms, cap 8h)`; usare mediana; rispettare `meta.duration_source`.
- **P2:** detector degeneranza `(host_short, os_user) → distinct auth_account_uuid`; normalizzare host storico FQDN con `host.split('.')[0]` (retrocompat pre-ADR-7); Hare-quota solo sul residuo degenere.
- **P1/P3:** join deterministico via `auth_*` + `commit_sha` + trailer `DevForge-Author`; disattivare `lib_actor_match`/`07c`/`07e`/`07g` sul lazo DevForge.

## Tabella campi nuovi/modificati (contratto)
| Campo | Evento | Semantica |
|---|---|---|
| `repo_slug` | tutti | `org/repo` normalizzato da `repo_remote` (SSH+HTTPS) |
| `pr_author_emails[]` | `pr_opened`, `pr_merged` | set distinto autori reali dei commit della PR |
| `host` (in `meta.identity`) | `session_start` | short name (no FQDN) |
| `meta.duration_source` | eventi temporizzati | `wallclock` (consumer applica cap/mediana) |
| `telemetry_degraded` | (nuovo) | copertura interprete/fsync mancante — escludere dai conteggi, usare come metrica di salute |
| `trailer_hook_skipped_old_git` | (nuovo) | git < 2.15 → trailer assente per quella macchina |

## Criteri di accettazione (design AC 13)
File presente con tutte le sezioni P1-P6 + tabella campi; reviewer designato = owner `developer-telemetry`.

## No-regression
Documentazione; nessun impatto sul codice producer.
