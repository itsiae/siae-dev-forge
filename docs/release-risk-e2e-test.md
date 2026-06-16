# Release-Risk — Test E2E trigger automatico

Nota tecnica generata per verificare end-to-end che l'hook `pr-release-gate`
(PostToolUse:Bash) scatti da solo su una PR `release/**` → `main` e produca:

1. Scorecard release-risk
2. Commento sulla PR GitHub
3. Pagina su Confluence TechOps/Rilasci con paragrafo razionale funzionale

Branch di test: `release/zz-test`. Questo file fornisce un diff reale all'assessor.
Da rimuovere a test concluso (la PR verrà chiusa, non mergiata).
