# Attribution Source Completeness — Design

**Data:** 2026-06-19
**Autore:** lorenzo.detomasi@siae.it
**Tipo:** Bug fix sistemico + osservabilità (telemetria DevForge)
**Complessità:** Media (path critico `lib/logger.sh`)

## Contesto

Verifica empirica su S3 (`siae-devforge-telemetry`, campione day04/18/19, ~16k eventi)
sui requisiti di attribuzione R1–R7. Il meccanismo `auth_email` SSO funziona e la
copertura sale con l'adozione del plugin (0% → 79,4% → 87,4% per giorno), ma restano
gap. Quelli **code-addressable lato produttore**:

| Gap | Evidenza empirica | Causa |
|-----|-------------------|-------|
| 1 | `*_task_divergence` con `auth_email=""` — 163 eventi/2gg | `devforge_log` chiamato senza `devforge_init_session` prima (`tdd-gate:149-159`, `plan-gate`) |
| 2 | `auth_email` vuoto su sessioni con plugin vecchio | pinning assente; dipende da `DEVFORGE_AUTH_EMAIL` esportato da `session-start` |
| 4 | `commit_created` perde 26% `auth_email` (181/689) | vecchie versioni / Bedrock-API-key (no `oauthAccount`); ordering corretto (`post-commit-review:60`) |

**Root cause comune:** `auth_email` dipende da un export (`DEVFORGE_AUTH_EMAIL`) che
**non propaga ai subprocess** degli altri hook (memory *Env var not propagated to hooks*).
Ogni hook che non chiama `devforge_init_session` emette vuoto, anche su plugin aggiornato.

Gap **non-code** (versioni vecchie come adozione, domini esterni vendor, mirror R4):
tracciati in [ESCALATION.md](ESCALATION.md), fuori scope implementativo.

## Decisione architetturale (ADR)

Approcci valutati:
- **A — Lazy resolution nel logger** (scelto, base): se `DEVFORGE_AUTH_EMAIL` è vuoto al
  momento del log, risolvi inline via `devforge_resolve_auth_identity`. Fix in **un solo
  punto** → ogni evento si auto-guarisce indipendentemente dall'hook. Version-independent.
- B — `init_session` nei 2 hook: chirurgico ma non sistemico (il prossimo hook ricasca,
  non aiuta gap 2/4). **Scartato** come soluzione unica.
- C — Backfill a valle: non è "alla fonte". **Scartato** (è il recupero euristico che
  vogliamo rendere superfluo).

**B — Eventi osservabilità** (scelto, complementare): rendere misurabili alla fonte i casi
non risolvibili in codice (dominio esterno, identità irrisolta) invece di scaricarli a valle.

Scelta utente: **A + B insieme**.

## Componenti

### Metodo A — Lazy auth resolution (`lib/logger.sh`)

Nuovo helper, con cache per-process per non rileggere `~/.claude.json` ad ogni evento:

```sh
# Resolve auth identity lazily if not already pinned in env.
# Cache flag per-process: legge ~/.claude.json al massimo una volta per processo hook.
_devforge_ensure_auth() {
    [ -n "${_DEVFORGE_AUTH_RESOLVED:-}" ] && return 0
    _DEVFORGE_AUTH_RESOLVED=1
    if [ -z "${DEVFORGE_AUTH_EMAIL:-}" ]; then
        local _auth _rest
        _auth=$(devforge_resolve_auth_identity 2>/dev/null || printf '|||')
        DEVFORGE_AUTH_EMAIL="${_auth%%|*}"
        _rest="${_auth#*|}"
        DEVFORGE_AUTH_ACCOUNT_UUID="${_rest%%|*}"
    fi
}
```

Chiamato in testa a `devforge_log` e `devforge_log_timed`, **prima** di leggere
`auth_email_v="${DEVFORGE_AUTH_EMAIL:-}"`. Precedenza invariata: se l'env è già pinnato
(da `session-start`/`init_session`) non rilegge nulla → zero regressione sul path caldo.

**Trade-off cache (deciso esplicitamente):** il flag `_DEVFORGE_AUTH_RESOLVED=1` è settato
**incondizionatamente** alla prima chiamata, anche se la resolution restituisce vuoto. Scelta
voluta: l'obiettivo è *1 lettura per processo*, e gli hook DevForge sono processi
**short-lived** (terminano in secondi). Un fallimento transitorio di lettura di
`~/.claude.json` (es. placeholder iCloud, scrittura concorrente) resta confinato a
**quel singolo processo hook**; il processo hook **successivo** riparte con flag vuoto e
ritenta. Settare il flag solo su successo causerebbe invece N riletture/processo per i casi
Bedrock legittimamente senza `oauthAccount` (50–200ms/evento) → costo inaccettabile sul path
caldo. Quindi: flag incondizionato.

### Metodo B — Eventi osservabilità (`hooks/session-start`)

**Correzione post spec-review:** `session-start` gira su `startup/resume/clear/compact`
(matcher riga 6), **non** 1×/sessione logica. Emettere al blocco resolution (riga 91-95)
duplicherebbe gli eventi ad ogni compact/resume. L'hook però rileva già la sorgente in
`SESSION_START_SOURCE` (riga 410) con un `case "$SESSION_START_SOURCE"` e un branch
`startup)` = sessione fresca. **L'emit va nel branch `startup)`**, che fa fire gli eventi
**1×/sessione logica** (gli `auth_email` sono già valorizzati alla riga 95, prima della 417).
Nessun sentinel nuovo.

```sh
# dentro:  case "$SESSION_START_SOURCE" in
#            startup)  ... reset skills ...
DEVFORGE_AUTH_DOMAIN="${DEVFORGE_AUTH_DOMAIN:-siae.it}"   # dominio aziendale, override via env
if [ -z "$DEVFORGE_AUTH_EMAIL" ]; then
    devforge_log "identity_unresolved" "warning" '{"reason":"oauthAccount_absent"}' 2>/dev/null || true
else
    _dom="${DEVFORGE_AUTH_EMAIL##*@}"
    if [ "$_dom" != "$DEVFORGE_AUTH_DOMAIN" ]; then
        devforge_log "identity_external_domain" "warning" \
            "{\"domain\":\"$(devforge_sanitize_json_str "$_dom")\"}" 2>/dev/null || true
    fi
fi
```

`auth_email` completo NON viene duplicato nel meta (è già top-level nell'evento stesso).
`DEVFORGE_AUTH_DOMAIN` (default `siae.it`) è l'unica nuova var di config: documentata qui e
da aggiungere a `hooks/ENV_VARS.md`.

## Flusso dati

```
hook subprocess → devforge_log/_timed
   → _devforge_ensure_auth (lazy, 1×/processo)
      → DEVFORGE_AUTH_EMAIL pinnato?  sì → usa   |  no → devforge_resolve_auth_identity(~/.claude.json)
   → riga JSON con auth_email/auth_account_uuid top-level → S3

session-start (1×/sessione)
   → resolution auth → emit identity_unresolved | identity_external_domain (warning)
```

## Gestione errori

- `~/.claude.json` assente / no `oauthAccount` (Bedrock): `auth_email` resta `""` (best-effort,
  comportamento attuale invariato) + evento `identity_unresolved` per misura.
- `devforge_resolve_auth_identity` già robusto (node→python3→degraded, mai aborta sotto `set -e`).
- Cache flag impedisce loop/riletture; nessuna nuova dipendenza.

## Testing (TDD)

- **AC1**: `tdd_gate_task_divergence` emesso senza `init_session` precedente porta
  `auth_email` valorizzato quando `~/.claude.json` ha `oauthAccount` (via `DEVFORGE_CLAUDE_JSON` fixture).
- **AC2**: stesso per un `devforge_log` generico **e** un `devforge_log_timed` senza pinning
  (entrambi gli emitter coperti dal lazy resolution).
- **AC3** (precedenza pin, no-rilettura): esporta `DEVFORGE_AUTH_EMAIL=pinned@siae.it` e punta
  `DEVFORGE_CLAUDE_JSON` a un file con `emailAddress=other@example.it`. Dopo `devforge_log`,
  asserisci `auth_email=pinned@siae.it` (non `other@…`): prova che il pin vince e che il file
  NON è stato letto/sovrascritto. (Nota: `DEVFORGE_FORCE_BASH_FALLBACK` controlla solo il
  write-path, NON la resolution → non usarlo qui; la sola asserzione pin-vince è sufficiente
  per il criterio "1 lettura max/processo".)
- **AC4**: `~/.claude.json` con dominio `@gmail.com` + `SESSION_START_SOURCE=startup` →
  `session-start` emette `identity_external_domain` con `meta.domain="gmail.com"`.
- **AC5**: `~/.claude.json` senza `oauthAccount` + `startup` → `session-start` emette `identity_unresolved`.
- **AC6 (no-regression)**: suite logger esistente verde; riga JSON identica quando l'env è pinnato.
- **AC7 (degraded resolver)**: `~/.claude.json` con `oauthAccount` presente ma **node E python3
  assenti** (`DEVFORGE_FORCE_BASH_FALLBACK=1` + PATH ridotto) → `auth_email=""`, **nessun crash**,
  hook ritorna 0. Protegge il path best-effort da regressioni future di `devforge_json_field`.
- **AC8 (no doppia emissione)**: `SESSION_START_SOURCE=compact` → il blocco metodo B NON emette
  `identity_unresolved`/`identity_external_domain` (solo `startup` li emette).

## Criteri di accettazione

1. Ogni evento emesso da qualunque hook porta `auth_email` se `oauthAccount` è presente,
   anche senza `init_session` esplicito (gap 1 chiuso; gap 2/4 mitigati su versione corrente).
2. Lettura `~/.claude.json` al massimo 1×/processo (cache).
3. Eventi `identity_external_domain` e `identity_unresolved` emessi **1×/sessione logica**
   (solo su `SESSION_START_SOURCE=startup`, non su resume/clear/compact) nei casi rilevanti.
4. Zero regressione: tutti i test logger esistenti passano; nessun campo chiave cambia path.
5. ESCALATION.md creato per i gap non-code (versioni/IdP/mirror) con owner e azione.

## Stima

| Scala | SP |
|-------|----|
| Umano | 3 |
| Augmented | 1 |

## File toccati

- `lib/logger.sh` — `_devforge_ensure_auth` + chiamata in `devforge_log`/`devforge_log_timed`
- `hooks/session-start` — emit osservabilità nel branch `startup)` (post-resolution)
- `hooks/ENV_VARS.md` — documenta `DEVFORGE_AUTH_DOMAIN` (default `siae.it`)
- `tests/hooks/test_lazy_auth_resolution.sh` — nuovo (AC1–AC3, AC6, AC7)
- `tests/hooks/test_identity_observability.sh` — nuovo (AC4–AC5, AC8)
- `docs/plans/2026-06-19-attribution-source-completeness/ESCALATION.md` — creato
