# Task 03 — abilita Pages (workflow) + visibility private

**Stato:** PENDING
**Dipende da:** task-02
**Tipo:** operazione infra (gh api, admin repo) — NON codice
**Output:** Pages attiva members-only + nota nel design/handover con la URL

## Obiettivo
Abilitare GitHub Pages con source = GitHub Actions e **visibility: private** (members-only, Enterprise), verificando che il sito NON sia accessibile anonimamente. Fallback se la policy org nega private Pages.

## Procedura (bypass proxy: env -u *proxy + NO_PROXY github.com)
1. Abilita Pages con build_type workflow:
   ```
   gh api --method POST repos/itsiae/siae-dev-forge/pages -f build_type=workflow
   ```
2. Imposta visibility private (Enterprise):
   ```
   gh api --method PUT repos/itsiae/siae-dev-forge/pages -f build_type=workflow -f visibility=private
   ```
3. Verifica:
   ```
   gh api repos/itsiae/siae-dev-forge/pages --jq '{url: .html_url, visibility: .visibility, build_type: .build_type}'
   ```
   Atteso: `visibility=private`. Se l'API rifiuta `visibility=private` (policy org / piano non abilitato) → STOP.
4. Verifica members-only: la URL `html_url` NON deve essere accessibile anonimamente (HTTP 404/401/302→login per utente non autenticato). Confermare che `visibility=private` sia effettivo.

## Fallback (AC 7 design)
Se private Pages NON è consentito (PUT visibility=private fallisce o resta `public`):
- NON pubblicare un sito pubblico.
- Disabilitare Pages (`gh api --method DELETE repos/itsiae/siae-dev-forge/pages` se creato).
- Ripiegare su markdown-native render (generare `docs/api/telemetry-insights-api.md` dall'OpenAPI) — visibile solo ai membri via UI GitHub, zero esposizione. Aggiornare il design come scope-change.

## Permessi
Richiede admin repo. Se `gh api` ritorna 403/permessi insufficienti → fornire all'utente i passi esatti per Settings→Pages (Source: GitHub Actions; Visibility: Private).

## Criteri di accettazione (design AC 4)
Pages attiva con `visibility=private` verificata; sito non accessibile anonimamente; oppure fallback eseguito (nessun sito pubblico).
