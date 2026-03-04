# Common Failures — Tabella Claim / Verifica / Errori per Stack

Questa reference contiene le combinazioni piu' comuni di claim, comandi di verifica richiesti,
output atteso e errori tipici che invalidano il claim. Organizzata per stack tecnologico SIAE.

---

## Java (Spring Boot / Maven)

| Claim | Comando Richiesto | Output Atteso | Errore Tipico |
|-------|-------------------|---------------|---------------|
| "I test passano" | `mvn test -pl {module}` | `BUILD SUCCESS`, `Tests run: N, Failures: 0, Errors: 0` | `Tests run: N, Failures: X` — test falliti ignorati |
| "La build compila" | `mvn compile -pl {module}` | `BUILD SUCCESS` | `COMPILATION ERROR` — import mancanti, tipi incompatibili |
| "La coverage e' ok" | `mvn verify -pl {module}` (JaCoCo) | `Coverage >= 70%` nel report JaCoCo | Coverage sotto soglia, JaCoCo non configurato |
| "Il codice e' pulito" | `mvn checkstyle:check` | `BUILD SUCCESS`, 0 violations | Violations di naming, import order, javadoc |
| "Ho fixato il bug" | `mvn test -Dtest={TestClass}#{testMethod}` | Test di regressione specifico PASS | Test di regressione non scritto o non eseguito |
| "L'endpoint funziona" | `mvn test -Dtest={ControllerTest}` | Integration test PASS | Test solo happy path, error handling non testato |
| "Il mapping e' corretto" | `mvn test -Dtest={MapperTest}` | MapStruct mapper test PASS | Campi null, mapping mancanti, NPE |

---

## TypeScript Backend (Lambda / Express / Jest)

| Claim | Comando Richiesto | Output Atteso | Errore Tipico |
|-------|-------------------|---------------|---------------|
| "I test passano" | `yarn test` o `npm test` | `Tests: N passed, N total`, exit code 0 | `Tests: X failed` — assertion error, timeout |
| "La build compila" | `npx tsc --noEmit` | Nessun output (0 errori) | `error TS2xxx` — tipi incompatibili, import errati |
| "La coverage e' ok" | `yarn test --coverage` | `All files: >= 70%` | Coverage sotto soglia, file non coperti |
| "Il lint e' pulito" | `npx eslint src/` | `0 problems` | Regole ESLint violate, import non ordinati |
| "L'handler funziona" | `yarn test -- --testPathPattern={handler}` | Handler test PASS | Event mock errato, context non gestito |
| "Ho fixato il bug" | `yarn test -- --testPathPattern={test-file}` | Test di regressione specifico PASS | Test non scritto, async non awaited |
| "Il bundle e' pronto" | `npx esbuild --bundle` | Bundle generato senza errori | Dynamic import non risolti, external mancanti |

---

## TypeScript Frontend (Vue.js / vitest)

| Claim | Comando Richiesto | Output Atteso | Errore Tipico |
|-------|-------------------|---------------|---------------|
| "I test passano" | `npx vitest run` | `Tests: N passed`, exit code 0 | Component mount fallito, prop mancante |
| "La coverage e' ok" | `npx vitest run --coverage` | `All files: >= 70%` | Componenti UI non testati, store non coperto |
| "Il componente funziona" | `npx vitest run {Component}.spec.ts` | Test specifico PASS | Rendering condizionale non testato |
| "Il lint e' pulito" | `npx eslint src/` | `0 problems` | `<script setup>` warnings, template errors |
| "Lo store e' corretto" | `npx vitest run {store}.spec.ts` | Pinia store test PASS | Stato mutato senza action, getter non testato |
| "La build e' pronta" | `npx vite build` | Build completata senza errori | Import circolari, chunk troppo grandi |

---

## Python (AWS Glue / PySpark / pytest)

| Claim | Comando Richiesto | Output Atteso | Errore Tipico |
|-------|-------------------|---------------|---------------|
| "I test passano" | `pytest tests/ -v` | `N passed`, exit code 0 | `FAILED` — assertion error, fixture mancante |
| "La coverage e' ok" | `pytest --cov={module}` | `TOTAL >= 70%` | Coverage sotto soglia, moduli esclusi |
| "Il job Glue funziona" | `pytest tests/test_{job}.py -v` | Job test PASS | SparkContext non inizializzato, schema mismatch |
| "Il codice e' pulito" | `flake8 src/` | Nessun output (0 errori) | `E501` line too long, `F401` import unused |
| "Lo schema e' corretto" | `pytest tests/test_{schema}.py -v` | Schema validation PASS | Colonna mancante, tipo errato, nullable violato |
| "Il tipo e' corretto" | `mypy src/` | `Success: no issues found` | Type mismatch, missing stubs |
| "La partizione funziona" | `pytest tests/test_{partition}.py -v` | Partition test PASS | Partition key mancante, overwrite non idempotente |

---

## HCL / Terraform / Terragrunt

| Claim | Comando Richiesto | Output Atteso | Errore Tipico |
|-------|-------------------|---------------|---------------|
| "Il modulo e' valido" | `terraform validate` | `Success! The configuration is valid.` | `Error: Missing required argument`, provider non configurato |
| "Il plan e' pulito" | `terraform plan` | `Plan: N to add, 0 to change, 0 to destroy` | Risorse da distruggere non previste, drift |
| "Il lint e' ok" | `tflint` | `0 issue(s) found` | Regole AWS violate, variabili non usate |
| "I file sono corretti" | `terraform fmt -check` | Exit code 0 | Formattazione inconsistente |
| "La security e' ok" | `tfsec .` | `0 potential problems detected` | IAM `*` policy, S3 senza encryption, SG aperto |
| "Lo state e' configurato" | `terraform init` | `Terraform has been successfully initialized!` | Backend S3 non raggiungibile, lock DynamoDB mancante |

---

## Git (Cross-stack)

| Claim | Comando Richiesto | Output Atteso | Errore Tipico |
|-------|-------------------|---------------|---------------|
| "Il commit e' pronto" | `git status` + `git diff --staged` | Solo file intenzionali staged | File dimenticati, file di debug inclusi |
| "Il branch e' aggiornato" | `git log --oneline -5` | Commit recenti coerenti | Merge conflict non risolto, commit fuori ordine |
| "Non ci sono secret" | `git diff --staged` + grep per pattern | Nessun pattern secret trovato | AWS key, password, token in chiaro nel diff |
| "Il naming e' corretto" | `git branch --show-current` | `feature/{JIRA-ID}-desc` o `fix/{JIRA-ID}-desc` | Branch naming non conforme SIAE |

---

## Pattern Trasversali

### Il "Dovrebbe Funzionare" Cascade

```
Claim: "Dovrebbe funzionare"
  ↓ IDENTIFICA: quali test servono?
  ↓ ESEGUI: lancia i test
  ↓ LEGGI: 3 test falliti su 47
  ↓ VERIFICA: NO — 3 fallimenti
  ↓ AFFERMA: NON POSSO — torno a fixare

RISULTATO: Il "dovrebbe" era sbagliato. I 5 step lo hanno scoperto.
```

### Il "Cambio Piccolo" Trap

```
Claim: "E' solo una riga, non puo' rompere nulla"
  ↓ IDENTIFICA: test unitari + test di integrazione
  ↓ ESEGUI: `mvn test`
  ↓ LEGGI: NullPointerException in un test di integrazione
  ↓ VERIFICA: NO — la riga cambiata ha un side effect
  ↓ AFFERMA: NON POSSO — il cambio piccolo ha rotto un test

RISULTATO: I "cambi piccoli" causano i bug peggiori.
```
