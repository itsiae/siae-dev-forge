# SIAE Global Rules

> **Fonte unica versionata.** Questo file è iniettato in OGNI sessione da `hooks/session-start`
> (blocco `<EXTREMELY_IMPORTANT>`). NON duplicare queste regole altrove: per i topic con una skill
> owner, rimanda alla skill (git → `siae-git-workflow`, GitHub env → `siae-github-env-sync`).
> Si modifica SOLO qui. Nessun dato per-persona/segreto: l'unico indirizzo ammesso è il proxy corporate.

## Contesto di sistema (DISCRIMINA prima di applicare ambienti / CI-CD / deploy)
SIAE ha due famiglie di sistemi con convenzioni DIVERSE. Riconosci il contesto dai marker nel repo PRIMA di applicare le regole di ambiente/deploy:
- **Cloud/AWS** (data platform, IaC): marker `*.tf`, `terragrunt.hcl`, repo `datalake-*` / `*-iac`. Runtime AWS (Glue/Lambda/ECS/S3). Deploy via reusable `terragrunt-*`. → ambienti tecnici `dev`/`qa`/`prod`.
- **SPORT/PAE/POP** (microservizi Java): marker `pom.xml`+`mvnw`, `Dockerfile`, `chart/` (Helm); repo `sport-*` / `pae-*` / `pop-*`. Runtime **OpenShift** (K8s). Deploy via reusable `MVN_CI`/`MVN_CD`. → ambienti `sviluppo`/`collaudo`/`certificazione`/`produzione`.
- Nel dubbio: ispeziona `.github/workflows/` (terragrunt → cloud; MVN_CD → microservizio) e CHIEDI invece di assumere.

## Scope Control
- Do NOT over-scope changes. When asked to create IAM policies, Terraform modules, or any resource, start minimal and ask before adding extras.
- Never include permissions, resources, or files not explicitly requested.
- Always check existing patterns in the repo before scaffolding new code.

## Interaction Style
- If the user interrupts, stop immediately and ask what they need.
- Confirm understanding of task scope before starting complex work.
- Start sessions with the exact repo, branch, environment, and scope — do not assume.

## Data Handling
- When working with CSV files, always read the actual column names from the file header before writing any mapping code.

## Conventions
- Environment names — DIPENDONO dal contesto di sistema (vedi sopra):
  - **Cloud/AWS** (datalake/IaC): valore tecnico `dev`/`qa`/`prod` (`AWS_ENV`). I GitHub Environment si chiamano `collaudo`/`certificazione`/`produzione`, ma `AWS_ENV` resta dev/qa/prod. NON usare i nomi italiani come valore tecnico AWS salvo indicazione esplicita.
  - **SPORT/PAE/POP** (microservizi OpenShift): gli ambienti SONO `sviluppo`/`collaudo`/`certificazione`/`produzione` (profili Spring `application-<AMB>.yml`, Helm `values-<ambiente>.yaml`, namespace OpenShift). Qui NON usare dev/qa/prod.

## CI/CD — Cloud/AWS (datalake/IaC): SIAE GitHub Environments
Le pipeline di deploy AWS SIAE (reusable workflow `itsiae/siae-gh-actions/.github/workflows/terragrunt-plan.yaml` e `cd-terragrunt-plan-deploy.yaml`) cercano SEMPRE queste 5 GitHub Environment variables nell'environment configurato per il job (es. `collaudo`, `certificazione`, `produzione`):
- `AWS_ENV` — valore tecnico AWS (es. `dev`, `qa`, `prod`), usato come `$ENV` per leggere `live/_envs/$AWS_ENV.tmpl` e per nomenclatura risorse.
- `AWS_ORG_ACCOUNT` — account master billing (`104589273752` per SIAE), primo step nel role chaining.
- `AWS_REGION` — region target (es. `eu-west-1`).
- `AWS_ROLE` — nome del role IAM assumibile via OIDC GitHub (es. `github-pipeline-rw`), uguale in entrambi gli account.
- `AWS_TARGET_ACCOUNT_ID` — account ID dove si deploya effettivamente (es. `134565215127` enterprise_dev_qa, `100649704385` digital, ecc.).
Altre var possono essere presenti per pattern envsubst specifici (es. `VPC_STAGE`, `SIAE_ROUTE53_ZONE_NAME`) ma sono opzionali.
Verifica/sync delle var di un repo: `gh api repos/itsiae/<repo>/environments/<env>/variables` (richiede gh autenticato). Workflow completo: skill `siae-github-env-sync`.

## CI/CD — SPORT/PAE/POP (microservizi OpenShift)
I microservizi Java (Spring Boot Maven + Docker + Helm) usano i reusable workflow `itsiae/siae-gh-actions/.github/workflows/MVN_CI.yaml` e `MVN_CD.yaml` (NON terragrunt). Verificato sui repo `pae-auth-be`, `sport-gestione-licenze-service`, `sport-payments-service`:
- **CI** (`MVN_CI`): trigger su push `main`/`release/**` + PR su `main` → build Maven + JUnit.
- **CD** (`MVN_CD`): trigger su **push di un tag git** `sviluppo` o `collaudo` (+ `workflow_dispatch`) → build → push immagine su GitHub Packages → update del Helm chart → deploy su **OpenShift**. Il rilascio si fa TAGGANDO (`git tag sviluppo|collaudo` + push del tag), NON con plan/apply Terraform.
- **Ambienti = namespace OpenShift**, configurati come repo Variables: `OPENSHIFT_NAMESPACE_DEV` (sviluppo), `_COLL` (collaudo), `_CERT` (certificazione), `_PROD` (produzione). Cluster es. `apps.ocp-noprod.openshift.siae`.
- **Helm**: `chart/deployment-<servizio>/values-<ambiente>.yaml` — un file values per ambiente (`sviluppo`/`collaudo`/`certificazione`/`main`).
- Branch flow e tagging: skill `siae-git-workflow`.

## Workspace
- If file writes fail (especially on synced paths — OneDrive/iCloud), alert immediately rather than retrying silently.

## Network — Corporate SIAE
- Sulla rete corporate SIAE il TCP/22 in uscita è firewallato e il proxy trasparente `10.255.1.241:8080` fa deep packet inspection su 443, chiudendo anche SSH-over-443 (`ssh.github.com:443`). L'HTTPS puro verso github.com funziona.
- Per QUALSIASI operazione git (push/fetch/clone) usa remote HTTPS (`https://github.com/...`), mai SSH (`git@github.com:...`). Cambiare rete è un palliativo — il problema torna sulla corporate.
- Sintomi da riconoscere: `ssh: connect to host github.com port 22: Operation timed out`, `Connection closed by 10.255.1.241 port 8080`. NON suggerire di cambiare rete.
- Fix recipe: `git remote set-url origin https://github.com/<owner>/<repo>.git` + `gh auth setup-git` (gh è già autenticato nella keychain con scope `repo`/`workflow`/`gist`). Per nuovi clone: `gh repo clone owner/name`. Workflow git completo: skill `siae-git-workflow`.
- Per download grossi che falliscono con `Connection reset by peer` / `Recv failure` (font brew cask, blob GitHub release, tarball grossi) attiva il proxy corporate prima del comando: la shell function `set_proxy` è definita in `~/.zshrc` (esporta `HTTPS_PROXY`/`HTTP_PROXY`/`ALL_PROXY` su `$SIAE_PROXY_HOST`). Uso nei tool Bash: `source ~/.zshrc && set_proxy && <comando>`. Disattiva: `unset_proxy`. Sintomo: il download muore a metà su `github.com/.../releases/download/...`.
