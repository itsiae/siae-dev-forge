# Task 02 — Scrivi `cases.yml` (30 prompt rappresentativi)

**Goal:** Catalogo 30 prompt che coprono i casi d'uso DevForge tipici, con expected skill chain.

**File coinvolti:**
- `tests/skill-activation/cases.yml` (nuovo)

## Step 1 — Distribuzione

| Categoria | # case | Skill primary attese |
|---|---|---|
| Bug/debug | 8 | siae-debugging, siae-tdd, siae-verification |
| Feature/design | 8 | siae-brainstorming, siae-writing-plans, siae-tdd |
| Verification/PR | 6 | siae-verification, siae-finishing-branch, siae-requesting-review |
| Architecture/microservices | 4 | siae-architecture, siae-microservices-map, siae-service-logic-map |
| Misc (frontend, IaC, security, data) | 4 | siae-frontend, siae-iac, siae-security, siae-data-engineering |

## Step 2 — Scrivi `cases.yml`

```yaml
# tests/skill-activation/cases.yml
# 30 prompt rappresentativi per misurare skill activation accuracy
# Format: id, prompt, expected_primary, expected_chain (optional), forbidden (optional)

# === Bug/debug (8) ===
- id: bug-npe-endpoint
  prompt: "ho un NPE su /detailLocale, fixiamo"
  expected_primary: siae-debugging
  expected_chain: [siae-debugging, siae-tdd, siae-verification]

- id: bug-test-fail-ci
  prompt: "il test test_validate_isrc fallisce in CI"
  expected_primary: siae-debugging
  expected_chain: [siae-debugging]

- id: bug-prod-incident
  prompt: "incident in produzione, errore 500 sul payment endpoint"
  expected_primary: siae-debugging
  forbidden: [siae-tdd]  # debug PRIMA di TDD

- id: bug-stacktrace-typeerror
  prompt: "TypeError nello script Python di ingestion, ecco lo stacktrace [...]"
  expected_primary: siae-debugging

- id: bug-frontend-broken
  prompt: "la dashboard non carica più i dati, console mostra 401"
  expected_primary: siae-debugging

- id: bug-build-fail
  prompt: "build Maven fallisce con BUILD FAILURE su artifact X"
  expected_primary: siae-debugging

- id: bug-timeout-api
  prompt: "API gateway risponde con timeout dopo 30s su /list-locale"
  expected_primary: siae-debugging

- id: bug-not-working
  prompt: "non funziona, guarda qua: [errore]"
  expected_primary: siae-debugging

# === Feature/design (8) ===
- id: feature-new-field-dto
  prompt: "voglio aggiungere un campo 'tipo' a DichiarazioneEventoDTO"
  expected_primary: siae-brainstorming
  expected_chain: [siae-brainstorming, siae-writing-plans]
  forbidden: [siae-tdd]  # no jump to TDD before design

- id: feature-new-microservice
  prompt: "creo un nuovo microservizio per gestire le notifiche push"
  expected_primary: siae-brainstorming

- id: feature-refactor-auth
  prompt: "refactoring del modulo di autenticazione per usare OAuth2"
  expected_primary: siae-brainstorming

- id: feature-new-endpoint
  prompt: "aggiungo endpoint REST per esporre il catalogo locale"
  expected_primary: siae-brainstorming

- id: feature-config-change
  prompt: "modifico il timeout del client HTTP da 5s a 30s"
  expected_primary: siae-brainstorming
  # anche cambio config richiede brainstorm (memory: zero eccezioni)

- id: feature-options-tradeoff
  prompt: "valutiamo se usare Kafka o SQS per la coda eventi"
  expected_primary: siae-brainstorming

- id: feature-data-pipeline
  prompt: "costruisco una pipeline ETL bronze-to-silver per i dati di pagamento"
  expected_primary: siae-brainstorming
  expected_chain: [siae-brainstorming, siae-data-engineering]

- id: feature-jasper-from-pdf
  prompt: "ricostruisci template JasperReports da questo PDF"
  expected_primary: siae-brainstorming

# === Verification/PR (6) ===
- id: verify-fix-works
  prompt: "il fix funziona, ho testato in locale, posso committare?"
  expected_primary: siae-verification

- id: verify-tests-pass
  prompt: "tutti i test passano, è pronto"
  expected_primary: siae-verification

- id: verify-completed
  prompt: "ho completato l'implementazione del task 03"
  expected_primary: siae-verification

- id: pr-ready
  prompt: "sono pronto per aprire la PR"
  expected_primary: siae-finishing-branch
  expected_chain: [siae-finishing-branch, siae-requesting-review]

- id: pr-open
  prompt: "apro la pull request su main"
  expected_primary: siae-finishing-branch

- id: review-feedback
  prompt: "ho ricevuto feedback sulla PR #215, come rispondo ai commenti"
  expected_primary: siae-receiving-review

# === Architecture/microservices (4) ===
- id: arch-c4-system
  prompt: "creiamo il C4 model per il sistema di gestione licenze"
  expected_primary: siae-architecture

- id: arch-bounded-context
  prompt: "definiamo i bounded context per il dominio pagamenti"
  expected_primary: siae-architecture

- id: ms-map-system
  prompt: "mappa il sistema a microservizi del dominio sport"
  expected_primary: siae-microservices-map

- id: service-impact-dto
  prompt: "modifica DTO DichiarazioneEvento, quali consumer impatta?"
  expected_primary: siae-service-logic-map

# === Misc (4) ===
- id: frontend-vue-component
  prompt: "creo un componente Vue.js per drag & drop file upload"
  expected_primary: siae-frontend

- id: iac-terraform-vpc
  prompt: "modifico il modulo Terraform per aggiungere subnet private alla VPC"
  expected_primary: siae-iac

- id: security-iam-policy
  prompt: "review della IAM policy per il nuovo Lambda di ingestion"
  expected_primary: siae-security

- id: data-glue-job
  prompt: "scrivo un Glue job PySpark per la trasformazione bronze-to-silver"
  expected_primary: siae-data-engineering
```

## Step 3 — Verifica YAML

```bash
python3 -c "import yaml; data=yaml.safe_load(open('tests/skill-activation/cases.yml')); print(f'{len(data)} cases'); assert len(data)==30, 'Expected 30'"
```

Output atteso: `30 cases`.

## Step 4 — Verifica id univoci

```bash
python3 -c "
import yaml
data = yaml.safe_load(open('tests/skill-activation/cases.yml'))
ids = [c['id'] for c in data]
assert len(set(ids)) == len(ids), f'Duplicate ids: {set([x for x in ids if ids.count(x)>1])}'
print('All ids unique')
"
```

## Step 5 — Commit

```bash
git add tests/skill-activation/cases.yml
git commit -m "test(skill-activation): 30 prompt rappresentativi (8 bug/8 feature/6 verify/4 arch/4 misc)"
```

## Criteri accettazione

- 30 case in `cases.yml`
- ID univoci
- YAML valido
- Distribuzione: 8 bug, 8 feature, 6 verification, 4 arch, 4 misc

## Note

Il file resta editabile per future iterazioni. Aggiunte/rimozioni richiedono ri-baseline.
