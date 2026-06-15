# Task 02 — .github/workflows/pages.yml

**Stato:** PENDING
**Dipende da:** task-01
**File:** `.github/workflows/pages.yml` (nuovo), test di validazione YAML

## Obiettivo
Workflow Actions che pubblica `docs/api/` su GitHub Pages (build_type=workflow), permessi minimi.

## Approccio TDD
### RED — validazione
- `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/pages.yml'))"` → parse OK.
- assert presenza chiavi: `permissions.pages: write`, `permissions.id-token: write`, `concurrency.group: pages`, uso di `actions/upload-pages-artifact` con `path: docs/api` e `actions/deploy-pages`.

### GREEN — `.github/workflows/pages.yml`
```yaml
name: Deploy API docs (private Pages)
on:
  push:
    branches: [main]
    paths:
      - 'docs/api/**'
      - 'docs/plans/2026-06-14-devforge-telemetry-insights-api.openapi.yaml'
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs/api
      - id: deployment
        uses: actions/deploy-pages@v4
```

## Criteri di accettazione (design AC 3)
Workflow valido (YAML parse), permessi minimi `pages:write`+`id-token:write`, concurrency `pages`, artifact da `docs/api`.

## No-regression
Workflow nuovo; non modifica i 4 workflow esistenti. La suite test esistente resta verde.
