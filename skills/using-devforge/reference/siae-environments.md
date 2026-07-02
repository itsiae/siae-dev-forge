# SIAE Environments

> Fonte canonica versionata (REQ-DF-01). Iniettata da `hooks/session-start`.
> Se questo file manca, DICHIARA l'assenza — non inventare gli stage.

## Discrimina il contesto PRIMA di applicare gli ambienti
- **Cloud/AWS** (datalake/IaC): marker `*.tf`, `terragrunt.hcl`, repo `datalake-*`/`*-iac`.
- **SPORT/PAE/POP** (microservizi OpenShift): marker `pom.xml`+`mvnw`, `Dockerfile`, `chart/`.
- Nel dubbio: ispeziona `.github/workflows/` (terragrunt → cloud; MVN_CD → microservizio).

## Cloud/AWS — ordine ambienti
`dev` → `qa` → `prod` (valore tecnico `AWS_ENV`).
GitHub Environment corrispondenti: `collaudo` / `certificazione` / `produzione`.
Deploy via reusable workflow `terragrunt-plan.yaml` / `cd-terragrunt-plan-deploy.yaml`.

## SPORT/PAE/POP — ordine ambienti
`sviluppo` → `collaudo` → `certificazione` → `produzione`.
Deploy via **git tag** (`git tag sviluppo|collaudo` + push) → build → OpenShift.
Ambienti = namespace OpenShift (repo Variables `OPENSHIFT_NAMESPACE_DEV/_COLL/_CERT/_PROD`).

## Regola anti-confusione
- **collaudo** = stage di TEST (non pre-produzione).
- **certificazione** = stage di PRE-PRODUZIONE (viene dopo collaudo, prima di produzione).
- Non sono sinonimi e non sono intercambiabili.

## Se la fonte non è disponibile
Dichiara esplicitamente "fonte ambienti/stage non disponibile" — non ipotizzare l'elenco.
