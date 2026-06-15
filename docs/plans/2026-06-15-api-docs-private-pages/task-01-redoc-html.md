# Task 01 — docs/api/index.html (Redoc) + spec same-origin

**Stato:** PENDING
**Dipende da:** nessuno
**File:** `docs/api/index.html` (nuovo), `docs/api/telemetry-insights-api.openapi.yaml` (copia), `tests/docs/test_api_docs_site.sh` (nuovo)

## Obiettivo
Pagina Redoc che renderizza l'OpenAPI completo, con lo spec caricato **same-origin** (servito dal Pages privato, mai da CDN esterna).

## Approccio TDD
### RED — `tests/docs/test_api_docs_site.sh`
- assert `docs/api/index.html` esiste e contiene `<redoc` + il bundle Redoc da CDN `cdn.redocly.com`.
- assert lo `spec-url` è **relativo same-origin**: matcha `spec-url="./telemetry-insights-api.openapi.yaml"` e NON contiene `spec-url="http`.
- **no-drift**: `docs/api/telemetry-insights-api.openapi.yaml` è identico a `docs/plans/2026-06-14-devforge-telemetry-insights-api.openapi.yaml` (`diff -q` → identici).

### GREEN
1. `cp docs/plans/2026-06-14-devforge-telemetry-insights-api.openapi.yaml docs/api/telemetry-insights-api.openapi.yaml`
2. Creare `docs/api/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8"/>
    <title>DevForge Telemetry Insights API</title>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <style>body { margin: 0; padding: 0; }</style>
  </head>
  <body>
    <redoc spec-url="./telemetry-insights-api.openapi.yaml"></redoc>
    <script src="https://cdn.redocly.com/redoc/latest/bundle/redoc.standalone.js"></script>
  </body>
</html>
```

## Criteri di accettazione (design AC 1, 2, 5)
- index.html renderizza l'OpenAPI via Redoc; spec-url relativo same-origin; copia spec allineata al sorgente (no-drift).

## No-regression
File nuovi additivi; nessun impatto su codice/hook esistenti.
