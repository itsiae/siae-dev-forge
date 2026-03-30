# Task 05 — Albero IaC/Terraform in question-trees.md

**Stato:** [PENDING]
**File:** `skills/siae-qa/reference/question-trees.md`
**Dipendenze:** Task 04 completato (stesso file — va in sequenza)

---

## Obiettivo

Aggiungere l'albero domande `IaC / Terraform` in `question-trees.md`,
dopo l'albero `Mobile / Flutter` aggiunto dal Task 04.

---

## Step 1 — Verifica che IaC/Terraform non esista già

Cerca in `skills/siae-qa/reference/question-trees.md`:
```
IaC / Terraform
```

Se trovato → il task è già applicato. Marca `[DONE]` e fermati.
Se non trovato → procedi a Step 2.

---

## Step 2 — Verifica che Task 04 sia completato

Cerca in `skills/siae-qa/reference/question-trees.md`:
```
Mobile / Flutter
```

Se NON trovato → Task 04 non è ancora completato. Blocca questo task con `[BLOCKED]`
e attendi il completamento di Task 04.

---

## Step 3 — Aggiungi l'albero IaC/Terraform

Usa Edit per aggiungere il seguente blocco alla fine del file
(dopo l'ultimo contenuto dell'albero Mobile/Flutter):

```markdown

---

## IaC / Terraform

**Segnali di inferenza:** "Terraform", "terragrunt", "modulo", "VPC", "ECS", "Lambda",
"plan", "apply", "destroy", "IAM", "security group", "S3 bucket", "RDS", "tfvars",
"remote state", "output", "provider"

### L1 — Flusso principale
1. "Il modulo è idempotente? `terraform apply` eseguito due volte su uno stato identico
   produce zero diff? Ci sono risorse che cambiano ad ogni apply
   (es. timestamp, random ID) che potrebbero generare rumore nel plan?"
2. "Quali variabili di input sono obbligatorie e quali hanno default?
   Ci sono default che potrebbero essere accettati silenziosamente ma scorretti
   per certi ambienti (es. `instance_type = t2.micro` in produzione)?"

### L2 — Edge case specifici IaC
3. "Cosa succede se una risorsa è stata modificata manualmente fuori da Terraform
   (configuration drift)? Il `terraform plan` rileva la differenza e la corregge,
   o produce un piano inconsistente?"
4. "Il `terraform destroy` del modulo lascia risorse orfane (S3 bucket con dati,
   snapshot RDS, log group CloudWatch, certificate ACM)?
   Ci sono risorse che richiedono `lifecycle { prevent_destroy = true }`?"

### L3 — Integrazioni / dipendenze
5. "Il modulo dipende da output di altri moduli tramite `data terraform_remote_state`
   o variabili passate esternamente?
   Se il modulo upstream non è ancora stato applicato (stato assente),
   il plan fallisce con errore chiaro o degrada silenziosamente?"
```

---

## Step 4 — Output atteso

```
Run: grep -n "IaC / Terraform" skills/siae-qa/reference/question-trees.md
Output atteso: una riga con "## IaC / Terraform"
```

Se il grep trova il testo → task completato.
Aggiorna lo stato a `[DONE]` in `overview.md`.
