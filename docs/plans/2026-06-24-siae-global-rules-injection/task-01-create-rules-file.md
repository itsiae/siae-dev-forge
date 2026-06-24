# Task 01 — Crea la fonte unica versionata delle regole

**Goal:** creare `skills/using-devforge/reference/siae-global-rules.md` con le SIAE Global Rules normalizzate per distribuzione team. Stato: `[DONE]`.

## File coinvolti
- CREA: `skills/using-devforge/reference/siae-global-rules.md`
- CREA (dir, se non esiste): `skills/using-devforge/reference/`

## Step

### Step 1 — Crea la directory reference
```bash
mkdir -p "skills/using-devforge/reference"
```

### Step 2 — Scrivi il file con questo contenuto ESATTO (verbatim, wording originale EN/IT)
Path: `skills/using-devforge/reference/siae-global-rules.md`
```markdown
# SIAE Global Rules

> **Fonte unica versionata.** Questo file è iniettato in OGNI sessione da `hooks/session-start`
> (blocco `<EXTREMELY_IMPORTANT>`). NON duplicare queste regole altrove: per i topic con una skill
> owner, rimanda alla skill (git → `siae-git-workflow`, GitHub env → `siae-github-env-sync`).
> Si modifica SOLO qui. Nessun dato per-persona/segreto: l'unico indirizzo ammesso è il proxy corporate.

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
- Environment names: dev/qa/prod (NOT Italian equivalents like collaudo/certificazione/produzione unless explicitly told).

## CI/CD — SIAE GitHub Environments
Le pipeline di deploy SIAE (reusable workflow `itsiae/siae-gh-actions/.github/workflows/terragrunt-plan.yaml` e `cd-terragrunt-plan-deploy.yaml`) cercano SEMPRE queste 5 GitHub Environment variables nell'environment configurato per il job (es. `collaudo`, `certificazione`, `produzione`):
- `AWS_ENV` — valore tecnico AWS (es. `dev`, `qa`, `prod`), usato come `$ENV` per leggere `live/_envs/$AWS_ENV.tmpl` e per nomenclatura risorse.
- `AWS_ORG_ACCOUNT` — account master billing (`104589273752` per SIAE), primo step nel role chaining.
- `AWS_REGION` — region target (es. `eu-west-1`).
- `AWS_ROLE` — nome del role IAM assumibile via OIDC GitHub (es. `github-pipeline-rw`), uguale in entrambi gli account.
- `AWS_TARGET_ACCOUNT_ID` — account ID dove si deploya effettivamente (es. `134565215127` enterprise_dev_qa, `100649704385` digital, ecc.).
Altre var possono essere presenti per pattern envsubst specifici (es. `VPC_STAGE`, `SIAE_ROUTE53_ZONE_NAME`) ma sono opzionali.
Verifica/sync delle var di un repo: `gh api repos/itsiae/<repo>/environments/<env>/variables` (richiede gh autenticato). Workflow completo: skill `siae-github-env-sync`.

## Workspace
- If file writes fail (especially on synced paths — OneDrive/iCloud), alert immediately rather than retrying silently.

## Network — Corporate SIAE
- Sulla rete corporate SIAE il TCP/22 in uscita è firewallato e il proxy trasparente `10.255.1.241:8080` fa deep packet inspection su 443, chiudendo anche SSH-over-443 (`ssh.github.com:443`). L'HTTPS puro verso github.com funziona.
- Per QUALSIASI operazione git (push/fetch/clone) usa remote HTTPS (`https://github.com/...`), mai SSH (`git@github.com:...`). Cambiare rete è un palliativo — il problema torna sulla corporate.
- Sintomi da riconoscere: `ssh: connect to host github.com port 22: Operation timed out`, `Connection closed by 10.255.1.241 port 8080`. NON suggerire di cambiare rete.
- Fix recipe: `git remote set-url origin https://github.com/<owner>/<repo>.git` + `gh auth setup-git` (gh è già autenticato nella keychain con scope `repo`/`workflow`/`gist`). Per nuovi clone: `gh repo clone owner/name`. Workflow git completo: skill `siae-git-workflow`.
- Per download grossi che falliscono con `Connection reset by peer` / `Recv failure` (font brew cask, blob GitHub release, tarball grossi) attiva il proxy corporate prima del comando: la shell function `set_proxy` è definita in `~/.zshrc` (esporta `HTTPS_PROXY`/`HTTP_PROXY`/`ALL_PROXY` su `$SIAE_PROXY_HOST`). Uso nei tool Bash: `source ~/.zshrc && set_proxy && <comando>`. Disattiva: `unset_proxy`. Sintomo: il download muore a metà su `github.com/.../releases/download/...`.
```

### Step 3 — Verifica anti-leak (gate di sicurezza)
Account-personale / path-macchina (NB: `git@github.com` è un esempio anti-pattern legittimo → whitelisted):
```bash
grep -nE 'federicoarcangeli|/Users/|OneDrive[^/[:space:]]' "skills/using-devforge/reference/siae-global-rules.md"
```
Output atteso: **nessun match** (exit 1).
Email personali (whitelist `git@github.com`):
```bash
grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' "skills/using-devforge/reference/siae-global-rules.md" | grep -v '^git@github\.com$'
```
Output atteso: **nessun match** (exit 1). Se resta qualcosa → rimuovi il dato per-persona prima di proseguire.

Run (verifica che l'unico IP sia il proxy whitelisted):
```bash
grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' "skills/using-devforge/reference/siae-global-rules.md" | sort -u
```
Output atteso: esattamente `10.255.1.241` e nient'altro. (Gli account AWS a 12 cifre non sono IP e non matchano.)

## Criteri di accettazione
- [ ] `skills/using-devforge/reference/siae-global-rules.md` esiste.
- [ ] Contiene 7 sezioni `##` (Scope Control, Interaction Style, Data Handling, Conventions, CI/CD, Workspace, Network) + header `# SIAE Global Rules`. Verifica: `grep -c '^## ' skills/using-devforge/reference/siae-global-rules.md` → `7`.
- [ ] Anti-leak grep (Step 3) → nessun match (oltre alla whitelist `git@github.com`).
- [ ] Unico IP presente = `10.255.1.241`.
- [ ] git/GitHub-env rimandano alle skill (no duplicazione divergente del workflow).

## Commit
```bash
git add skills/using-devforge/reference/siae-global-rules.md
git commit -m "feat(rules): fonte unica versionata SIAE Global Rules"
```
