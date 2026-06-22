# Design — Release Risk: dimensione Piattaforma (REQ-13/14/15)

> Data: 2026-06-19 · Branch: `feat/release-risk-platform-hierarchy` (da `origin/main` 8e034e8, v1.95.0)
> Autorizzazione utente a procedere senza gate di approvazione separato ("ok continua con il risk+"); rationale tracciato qui (delivery-pragmatism).

## Contesto

La skill `siae-release-risk` è già mergiata e copre **17/20** requisiti operativi
(PR #311/#328/#330/#349). Gap analysis empirica → l'unica dimensione mancante è la
**piattaforma applicativa**:

| REQ | Stato pre | Gap |
|---|---|---|
| REQ-13 — Identificazione piattaforma (sport, SPA, …) da repo/branch | ❌ | nessun concetto `platform` nel codice |
| REQ-14 — Separazione output per piattaforma (no aggregazione cross-sistema) | ❌ | storage piatto `docs/releases/` |
| REQ-15 — Gerarchia `piattaforma → release → scorecard` | ❌ | path piatto `<date>-<service>-<branch>.md` |

Gli altri 17 requisiti restano invariati: **zero regressioni** è vincolo duro
(baseline `tests/test_release_risk_*.py` = **247 passed**).

## Decisioni (default scelti, l'utente ha autorizzato a procedere)

### D1 — Identificazione piattaforma (REQ-13) — config-as-code + fallback deterministico
Nuovo modulo `lib/release_risk/platform_resolver.py`. Regola `resolve_platform()`, fail-safe (mai eccezione):
1. override esplicito `--platform` → `slug(override)`;
2. match **prefisso più lungo** in `PLATFORM_PREFIXES` (single source of truth, allineato a `KG_PREFIXES`) → piattaforma canonica (es. `sport-`, `digital-channels-sport-`, `esb-sport-` → `sport`);
3. fallback: **primo token** del servizio prima del primo `-` → ogni famiglia ha la sua cartella (niente bucket `unknown` condiviso → rispetta REQ-14).

Estendibile via env `DEVFORGE_RELEASE_RISK_PLATFORM_MAP` (`plat:pref1|pref2;…`). "SPA": un servizio `spa-*` cade già su platform `spa` via fallback (token); se serve mappatura canonica multi-prefisso si aggiunge una riga — niente placeholder hardcoded.

### D2 — Gerarchia storage (REQ-15) — `docs/releases/<platform>/<release>/scorecard.md`
`release` = `slug(<service>-<version>)`, fallback `slug(<service>-<branch>)` se version `unknown`.
File a nome fisso `scorecard.md` → **idempotente per release** (re-run sovrascrive, versionato via git — coerente con il modello "una pagina per rilascio" di Confluence). La data resta nel contenuto (`generated_at`).

### D3 — Backward-compat — nessuna migrazione
I file storici flat in `docs/releases/*.md` restano dove sono. I nuovi run scrivono gerarchico. Test `test_cli_writes_output_file` aggiornato a glob ricorsivo (modifica attesa, non regressione).

### D4 — Cache (flag esplicito utente) — invalidazione + verifica path su hit
Il rischio segnalato: su cache hit `cli.py` ritorna `cached.output_path` **stale** (vecchio path flat) senza ri-renderizzare. Tripla difesa:
1. **Bump `SCHEMA_VERSION` 1.0 → 2.0**: `cache.get()` scarta entry con `schema_version` diverso → invalida tutte le entry pre-platform.
2. **Verifica path su hit**: in `assess()` calcolo `output_path` PRIMA del lookup; su hit accetto la cache solo se `cached.output_path == output_path` **e** il file esiste, altrimenti miss + ricalcolo.
3. La chiave cache resta `(branch, diff_hash, baseline_main_sha)` — `diff_hash` già disambigua i contenuti; la verifica path (#2) copre i cambi di schema futuri.

### D5 — Confluence (REQ-11/14) — platform nel corpo, titolo/parent invariati
La piattaforma compare nella tabella Identificazione (REQ-13 visibile anche su Confluence). Titolo e `parentId` **invariati** per non rompere l'idempotenza find-by-title delle pagine già pubblicate. Il foldering Confluence per-piattaforma è enhancement futuro; lo store autoritativo versionato (REQ-09) è la gerarchia git, che è pienamente conforme a REQ-14/15.

### D6 — Hook & traceability
- `hooks/pr-release-gate`: **nessuna modifica** — passa `--service $(basename repo)`, la piattaforma è risolta dentro `cli.py` (REQ-13 "da contesto"); l'hook posta `output_path` che ora è gerarchico → funziona invariato.
- REQ-12: aggiungo `platform` al meta dell'activity event.

## Componenti toccati

| File | Modifica |
|---|---|
| `lib/release_risk/platform_resolver.py` | **NUOVO** — `resolve_platform`, `release_slug`, `scorecard_path` |
| `lib/release_risk/schema.py` | `ReleaseRiskReport.platform: Optional[str]`; `SCHEMA_VERSION="2.0"` |
| `lib/release_risk/cache.py` | `get()` scarta `schema_version` mismatch |
| `lib/release_risk/cli.py` | risolve platform, path gerarchico, `platform` in identification+report+event, verifica path su cache hit, arg `--platform` |
| `tests/test_release_risk_platform_resolver.py` | **NUOVO** (TDD) |
| `tests/test_release_risk_cli.py` | glob ricorsivo + assert platform nel path |
| `tests/test_release_risk_cache.py` | test invalidazione schema_version |
| `skills/siae-release-risk/SKILL.md`, `commands/forge-release-risk.md` | path gerarchico + `--platform` |

## Criteri di accettazione — VERIFICATI

- [x] `resolve_platform("sport-x-service")=="sport"`, `("esb-sso-x")=="ciam"`, `("foo-bar")=="foo"`, override rispettato, mai eccezione (22 test unit verdi)
- [x] Scorecard scritta in `docs/releases/<platform>/<release>/scorecard.md` (E2E: `sport/sport-gestione-licenze-service-2.4.0/scorecard.md`, `billing/billing-core-1.0.0/scorecard.md`)
- [x] `platform` presente in report JSON, tabella Identificazione (`| **platform** | sport |`), meta event
- [x] Cache pre-platform (schema 1.0) invalidata; hit servito solo se path coincide ed esiste (E2E: RUN2 hit, RUN3 file-mancante→ricalcolo)
- [x] Hook posta il path gerarchico senza modifiche al file hook (cli ritorna `output_path` gerarchico)
- [x] **Suite no-regression**: baseline 247 → 241 passed, delta riconciliato esatto (−30 duplicato iCloud untracked rimosso, +22 resolver, +2 cache); **0 test tracciati persi**

## SP (doppia scala)
Umano: ~3 SP (mezza giornata). Augmented: ~1 SP.
