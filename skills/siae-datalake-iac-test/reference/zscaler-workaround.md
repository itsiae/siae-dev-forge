# Workaround Zscaler per `terraform init`

> **Ambiente di esecuzione richiesto: WSL (Linux).** I comandi di questo
> workaround presuppongono shell bash su WSL/Linux. Da PowerShell o cmd su
> Windows i path (`/etc/ssl/...`, `~/.terraformrc`) e i binari del provider
> (`terraform-provider-aws_v*_x5` ELF Linux) **non funzionano**.

Negli ambienti SIAE il proxy Zscaler intercetta il TLS verso
`releases.hashicorp.com`, quindi `terraform init` fallisce con:

```
x509: certificate signed by unknown authority
```

La soluzione validata e' un **filesystem mirror locale** dichiarato in
`~/.terraformrc`. Setup una volta sola, riutilizzato da tutti i repo.

## 0. Pre-check (NON ri-scaricare se gia' presente)

Prima di eseguire qualsiasi `curl`, verifica cosa e' gia' installato. Lo zip
del provider pesa ~190 MB: scaricarlo di nuovo ogni volta e' inutile e lento.

```bash
# Sei su WSL / Linux?
uname -a   # deve contenere "Linux"; su WSL appare anche "microsoft"

# Terraform e' gia' installato?
command -v terraform && terraform version
# Se stampa una versione >= 1.6.0, salta lo step "installa Terraform".

# Provider AWS gia' nel filesystem mirror?
ls ~/terraform-mirror/registry.terraform.io/hashicorp/aws/*/linux_amd64/terraform-provider-aws_v*_x5 2>/dev/null
# Se elenca il binario per la versione richiesta dal repo, salta gli step 1-2.

# ~/.terraformrc gia' configurato?
cat ~/.terraformrc 2>/dev/null
# Se contiene il blocco filesystem_mirror, salta lo step 3.
```

Procedi solo con gli step mancanti.

> Nota: il provider richiesto e' quello dichiarato dai moduli `bronze`/`silver`
> del repo (vedi `.terraform.lock.hcl` o l'output di `terraform init`). Negli
> esempi sotto la versione e' `6.44.0`; sostituiscila se il repo ne usa una
> diversa.

## 1. Scarica il provider (con cert Zscaler dal trust store)

Il trust store di sistema contiene gia' il root CA Zscaler, quindi `curl
--cacert` funziona senza disabilitare la verifica TLS.

```bash
mkdir -p ~/terraform-providers && cd ~/terraform-providers
curl -fL --cacert /etc/ssl/certs/ca-certificates.crt \
  -o terraform-provider-aws_6.44.0_linux_amd64.zip \
  https://releases.hashicorp.com/terraform-provider-aws/6.44.0/terraform-provider-aws_6.44.0_linux_amd64.zip
unzip -o terraform-provider-aws_6.44.0_linux_amd64.zip -d ./extracted/
```

In alternativa, se `--cacert` non basta, scarica lo zip dal browser Windows
(che ha il cert Zscaler nello store) e copialo in WSL:

```bash
cp "/mnt/c/Users/<USER>/Downloads/terraform-provider-aws_6.44.0_linux_amd64.zip" \
   ~/terraform-providers/
```

## 2. Layout del filesystem mirror

```bash
MIRROR=~/terraform-mirror/registry.terraform.io/hashicorp/aws/6.44.0/linux_amd64
mkdir -p "$MIRROR"
cp ~/terraform-providers/extracted/terraform-provider-aws_v6.44.0_x5 "$MIRROR/"
chmod +x "$MIRROR/terraform-provider-aws_v6.44.0_x5"
```

## 3. Configura `~/.terraformrc`

```hcl
provider_installation {
  filesystem_mirror {
    path    = "/home/<USER>/terraform-mirror"
    include = ["registry.terraform.io/hashicorp/aws"]
  }
  direct {
    exclude = ["registry.terraform.io/hashicorp/aws"]
  }
}
```

Sostituisci `<USER>` con il tuo username (`echo $USER`).

## 4. Esegui i test

```bash
# Bronze
cd modules/bronze
rm -rf .terraform .terraform.lock.hcl   # solo se hai gia' provato un init fallito
terraform init -backend=false
terraform test

# Silver
cd ../silver
rm -rf .terraform .terraform.lock.hcl
terraform init -backend=false
terraform test

# tables_definition/tests NON dichiara provider — init standard funziona sempre
cd ../../tables_definition/tests
terraform init -backend=false
terraform test
```

## Aggiornare il provider a una nuova versione

Quando un repo bumpa la versione AWS, ripeti gli step 1-2 con la nuova
versione: il filesystem mirror puo' contenere piu' versioni in parallelo,
nessuna modifica a `~/.terraformrc` e' necessaria.

## Anti-pattern da evitare

| Anti-pattern | Perche' |
|---|---|
| `curl -k` (skip TLS) | Funziona ma maschera errori reali; preferire `--cacert` |
| `terraform init -plugin-dir=/tmp/...` per ogni repo | Va aggiunto a ogni comando; il filesystem mirror e' globale |
| Committare `.terraform/` o lo zip | Mai, sono artefatti locali |
| Disabilitare Zscaler | Non sempre possibile, e cambia stato di rete |
