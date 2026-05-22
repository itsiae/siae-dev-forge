# gh API — GitHub Actions Variables

## Prerequisito: gh CLI autenticata

```bash
gh auth status 2>&1
```

---

## Scopri ambienti di un repo

```bash
gh api repos/itsiae/{repo}/environments \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(v['name']) for v in d.get('environments',[])]"
```

---

## Lista variabili di un ambiente

```bash
gh api "repos/itsiae/{repo}/environments/{env}/variables?per_page=100" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"{v['name']}={v['value']}\") for v in d.get('variables',[])]"
```

## Lista variabili di tutti gli ambienti (loop)

```bash
for env in collaudo certificazione produzione; do
  echo "=== $env ==="
  gh api "repos/itsiae/{repo}/environments/$env/variables?per_page=100" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"  {v['name']}={v['value']}\") for v in d.get('variables',[])]"
done
```

---

## Crea variabile (POST)

```bash
gh api --method POST repos/itsiae/{repo}/environments/{env}/variables \
  -f name=NOME_VARIABILE \
  -f value='valore'
```

Response: `{}` (HTTP 201 Created)

---

## Aggiorna variabile esistente (PATCH)

```bash
gh api --method PATCH repos/itsiae/{repo}/environments/{env}/variables/NOME_VARIABILE \
  -f name=NOME_VARIABILE \
  -f value='nuovo-valore'
```

Response: `{}` (HTTP 204 No Content)

---

## Elimina variabile (DELETE)

```bash
gh api --method DELETE repos/itsiae/{repo}/environments/{env}/variables/NOME_VARIABILE
```

---

## Note operative

- `gh api` con versione 2.4.0 (Ubuntu) **non supporta** `gh variable list` — usare sempre `gh api` direttamente
- I valori con spazi o caratteri speciali vanno quotati: `-f value='cron(0 0 0 ? * * *)'`
- POST restituisce `{}` se ok, errore JSON se la variabile esiste già → usare PATCH per aggiornare
- PATCH restituisce `{}` se ok, 404 se la variabile non esiste → usare POST per creare

## Variabili standard repo datalake-*-iac

| Variabile | collaudo | certificazione | produzione |
|---|---|---|---|
| `AWS_ENV` | `dev` | `qa` | `prod` |
| `AWS_ORG_ACCOUNT` | `104589273752` | `104589273752` | `104589273752` |
| `AWS_REGION` | `eu-west-1` | `eu-west-1` | `eu-west-1` |
| `AWS_ROLE` | `github-pipeline-rw` | `github-pipeline-rw` | `github-pipeline-rw` |
| `AWS_TARGET_ACCOUNT_ID` | `613577363574` | `613577363574` | `043188932291` |
| `CRON_SCHED` | `cron(0 0 0 ? * * *)` | `cron(0 0/6 * * ? *)` | `cron(0 0/6 * * ? *)` |
| `CRON_SCHED_STATUS` | `false` | `true` | `true` |
| `S3_DATALAKE_BRONZE_NAME` | `dev-datalake-bronze-tier-eu-west-1-613577363574` | `qa-datalake-bronze-tier-eu-west-1-613577363574` | `prod-datalake-bronze-tier-eu-west-1-043188932291` |
| `S3_DATALAKE_SILVER_NAME` | `dev-datalake-silver-tier-eu-west-1-613577363574` | `qa-datalake-silver-tier-eu-west-1-613577363574` | `prod-datalake-silver-tier-eu-west-1-043188932291` |
