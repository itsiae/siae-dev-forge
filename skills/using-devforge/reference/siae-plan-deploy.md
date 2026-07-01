# SIAE PLAN e PLAN+DEPLOY

> Fonte canonica versionata (REQ-DF-02). Iniettata da `hooks/session-start`.
> Se questo file manca, DICHIARA l'assenza — non inventare la checklist.

## Disambiguazione obbligatoria (collisione di nomi)
Qui "PLAN" = **pipeline infrastrutturale SIAE** (reusable workflow
`terragrunt-plan.yaml`; PLAN+DEPLOY = `cd-terragrunt-plan-deploy.yaml`).
NON è il "PLAN" interno DevForge (EnterPlanMode / `siae-writing-plans`).
Se il task riguarda un design/piano DevForge, questo file non si applica.

## PLAN — checklist standard
1. `terragrunt plan` sull'ambiente target.
2. Review del plan output (risorse create/modificate/distrutte).
3. Nessun `apply` senza un plan verde e revisionato.

## PLAN+DEPLOY — progressione ambienti
- Cloud: `dev` → `qa` → `prod`, **senza salti**.
- Microservizi: `sviluppo` → `collaudo` → `certificazione` → `produzione`, **senza salti**.
- Nessun deploy verso `certificazione`/`produzione` senza il gate previsto:
  produzione = merge su `main`, e solo branch `release/**` può aprire PR verso
  `main` (branching strategy SIAE).

## Deviazioni
Qualsiasi deviazione dalla progressione o dal gate va **segnalata esplicitamente
all'utente**, mai applicata in silenzio.
