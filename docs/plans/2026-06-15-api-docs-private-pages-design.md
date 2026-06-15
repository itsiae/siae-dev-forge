---
title: Pubblicazione API contract come GitHub Pages privato (Redoc)
date: 2026-06-15
status: design
author: Lorenzo De Tomasi
complexity: bassa
---

# API docs browsable — GitHub Pages privato + Redoc

## Contesto
L'API contract OpenAPI 3.1 (`docs/plans/2026-06-14-devforge-telemetry-insights-api.openapi.yaml`,
su main) va pubblicato come **documentazione navigabile "che mostra tutto"** su GitHub.
Repo `itsiae/siae-dev-forge` = **private**; org `itsiae` = **GitHub Enterprise Cloud**.

## Decisione (risolve il conflitto Pages-vs-esposizione)
GitHub Pages è pubblico su repo privato SALVO Enterprise Cloud con **private Pages (access control)**.
Poiché itsiae è Enterprise, si pubblica con **`visibility: private`** → sito visibile SOLO ai membri
dell'org, NON pubblicamente. Soddisfa "Pages + Redoc" + "no esposizione pubblica".

## Componenti
- `docs/api/index.html` — Redoc standalone (JS da CDN `cdn.redocly.com`) con `spec-url` **same-origin**
  alla copia dello spec (così il contract è servito dal Pages privato, mai da CDN esterna).
- `docs/api/telemetry-insights-api.openapi.yaml` — copia (o sync) dello spec, servita same-origin dal sito.
- `.github/workflows/pages.yml` — workflow Actions: `actions/upload-pages-artifact` (path `docs/api`) +
  `actions/deploy-pages`; trigger `push` su `main` con `paths: [docs/api/**, docs/plans/2026-06-14-devforge-telemetry-insights-api.openapi.yaml]`; permessi `pages: write`, `id-token: write`; concurrency `pages`.
- Abilitazione Pages: source = GitHub Actions (`build_type: workflow`) + **visibility: private** (via repo Settings→Pages o `gh api`). Richiede permessi admin repo.
- README: link alla URL del sito Pages privato.

## ADR
- **ADR-1 Redoc** (non Swagger UI): reference pulita single-page "che mostra tutto"; niente backend/try-it-out (non serve, è un contract). Swagger UI scartato (più pesante, orientato all'esecuzione).
- **ADR-2 private Pages** (Enterprise) non public: il contract è di un tool interno → mai pubblico.
- **ADR-3 spec same-origin**: la copia dello spec è servita dal Pages privato; Redoc JS dal CDN (libreria pubblica, nessun dato sensibile). No fetch del contract da origine esterna.
- **ADR-4 sync dello spec**: il workflow include nel paths-trigger il path dello spec sorgente; la copia in `docs/api/` è aggiornata (step di copy nel workflow o test che verifica l'allineamento) per evitare drift.

## Criteri di accettazione
1. `docs/api/index.html` renderizza l'OpenAPI completo via Redoc (endpoint + schemi + esempi).
2. Lo spec è caricato **same-origin** (relative `spec-url`), non da URL esterno.
3. Workflow Pages valido (actionlint/yaml-lint) con permessi minimi (`pages: write`, `id-token: write`) e concurrency.
4. Istruzioni precise per abilitare Pages con **visibility: private** (Settings→Pages o `gh api`), con verifica che il sito NON sia accessibile anonimamente.
5. Copia spec in `docs/api/` allineata al sorgente (no drift) — test o step di sync.
6. README linka la URL del sito.
7. Fallback documentato: se la policy org NON consente private Pages, NON pubblicare; ripiegare su markdown-native render (no esposizione).

## Rischi
- Abilitare Pages + visibility private richiede admin repo → step manuale/utente o token admin.
- Se private Pages non consentito dalla policy org → STOP, fallback markdown (AC-7). Verifica all'abilitazione che il sito sia members-only.
- Spec drift tra `docs/plans/...yaml` e la copia in `docs/api/` → mitigato da AC-5.

## Stima SP
~2 umano / ~1 augmented (static HTML + workflow + enable).
