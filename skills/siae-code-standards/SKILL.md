---
name: siae-code-standards
description: >
  Use when writing or reviewing code that must follow SIAE multi-stack coding
  standards (Java, TypeScript, Python, HCL). Applica standard di codifica
  SIAE. Trigger: scrittura codice Java, TypeScript, Python, HCL/Terraform,
  naming conventions, struttura progetto, logging, error handling.
---

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║                                                                  ║
║              🔨  DevForge  ·  AI Competence Center               ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

# siae-code-standards

> **Tipo:** Flexible | **Fase SDLC:** 2. Coding
>
> Questa skill si attiva automaticamente durante la scrittura di codice Java,
> TypeScript, Python o HCL/Terraform. Applica naming conventions, struttura
> progetto, logging e error handling basati su pattern reali da 816 repo itsiae.

---

> 📊 **Dai repo itsiae:** Il 68% dei commenti in code review riguarda naming inconsistente. I repo con standard adottati riducono i review cycle del 40%.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## 1. Convenzioni Trasversali

Regole valide per **tutti** gli stack SIAE.

| Elemento | Convenzione | Esempio |
|----------|-------------|---------|
| Variabili | `camelCase` | `userId`, `totalAmount` |
| Classi / Tipi | `PascalCase` | `UserService`, `PaymentDto` |
| File | `kebab-case` | `user-service.ts`, `payment-handler.ts` |
| Costanti | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT`, `API_BASE_URL` |
| Package / Moduli | `lowercase` (Java), `kebab-case` (TS/HCL) | `it.siae.diritti`, `diritti-service` |

### 1.1 Ambienti SIAE

Usa sempre i nomi italiani canonici, mai traduzioni o abbreviazioni inventate:

| Ambiente | Suffisso tag  | Profile Spring |
|----------|---------------|----------------|
| **sviluppo** | `-dev.*` | `application-sviluppo.yml` |
| **collaudo** | `-rc.*` | `application-collaudo.yml` |
| **certificazione** | `-cert.*` | `application-certificazione.yml` |
| **produzione** | (release) | `application-produzione.yml` |

---

## 2. Java

### 2.1 Package e Naming

```
it.siae.{dominio}.{modulo}
it.siae.{dominio}.{modulo}.controller
it.siae.{dominio}.{modulo}.service
it.siae.{dominio}.{modulo}.repository
it.siae.{dominio}.{modulo}.dto
it.siae.{dominio}.{modulo}.mapper
it.siae.{dominio}.{modulo}.config
it.siae.{dominio}.{modulo}.exception
```

### 2.2 Repository Naming

Pattern: `{domain}-{function}-{type}`

| Tipo | Esempio |
|------|---------|
| Service | `diritti-gestione-service` |
| Frontend | `diritti-portale-frontend` |
| Library | `common-auth-library` |
| IaC | `diritti-infra-iac` |

### 2.3 Configurazione

| Aspetto | Regola |
|---------|--------|
| **Parent POM** | `it.siae:spring-boot-2-parent-pom` |
| **Spring profiles** | `application-{ambiente}.yml` (uno per ambiente) |
| **Mapping DTO** | MapStruct (`@Mapper(componentModel = "spring")`) |
| **Boilerplate** | Lombok (`@Data`, `@Builder`, `@Slf4j`) |
| **Logging** | SLF4J + Logback. Logger via `@Slf4j` di Lombok |
| **JSON** | Jackson (incluso nel parent POM) |
| **Test** | JUnit 5 + Mockito. Coverage minima da POM |

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-code-standards |
|:---|
| **⚠️ WARNING** |
| ⚙️ Operazione: `Modifica configurazione build (POM, package.json)` |
| **▼ Azione** |
| 1. 🔧 Modifica dipendenze / plugin / versioni nel file di build → `pom.xml / package.json` |
| 💡 Perche': Modifiche al POM o package.json impattano tutte le dipendenze, versioni e plugin del progetto. |
| 🚫 Se NO: La modifica non viene applicata. Verifica le regole parent POM e versioning prima di procedere. |

### 2.4 Pattern obbligatori

- **Controller**: `@RestController` + `@RequestMapping("/api/v1/{risorsa}")` + `@Slf4j`
- **Service**: interfaccia `RisorsaService` + implementazione `RisorsaServiceImpl` con `@Service @Slf4j`
- **DTO**: classi separate con `@Data @Builder` (Lombok)
- **Mapper**: interfaccia MapStruct con `@Mapper(componentModel = "spring")`

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-code-standards |
|:---|
| 📝 Operazione: `Creazione nuovo file sorgente` |
| **▼ Azione** |
| 1. ✏️ Crea nuovo file sorgente seguendo naming e package SIAE → `src/main/java/it/siae/{dominio}/{modulo}/` |
| 💡 Perche': La creazione di un nuovo file introduce naming, package e struttura che devono rispettare i pattern SIAE. |
| 🚫 Se NO: Il file non viene creato. Verifica naming conventions e package structure prima di procedere. |

---

## 3. TypeScript

### 3.1 Naming e Struttura

| Elemento | Convenzione | Esempio |
|----------|-------------|---------|
| DAO | `PascalCase` + suffisso `Dao` | `UserDao`, `PaymentDao` |
| Service | `PascalCase` + suffisso `Service` | `UserService`, `AuthService` |
| Handler | `PascalCase` + suffisso `Handler` | `UserHandler` |
| Test file | `{filename}.spec.ts` | `user-service.spec.ts` |
| Composable (Vue) | `use` + `PascalCase` | `useAuth`, `usePayment` |

### 3.2 Build Tool

| Contesto | Tool | Motivazione |
|----------|------|-------------|
| Lambda backend | **esbuild** | Bundling ottimizzato per Lambda |
| Frontend Vue.js | **Vite** | Dev server + build per SPA |

### 3.3 Linting

- **ESLint** + **Prettier** obbligatori
- Configurazione nella root del progetto (`.eslintrc.*`, `.prettierrc`)
- Pre-commit hook consigliato per format automatico

---

## 4. Python

### 4.1 Naming e Struttura

| Elemento | Convenzione | Esempio |
|----------|-------------|---------|
| Moduli | `snake_case` | `user_service.py`, `data_loader.py` |
| Classi | `PascalCase` | `DataProcessor`, `GlueJobConfig` |
| Funzioni | `snake_case` | `process_data()`, `load_bronze()` |
| Costanti | `UPPER_SNAKE_CASE` | `GLUE_DB_NAME`, `S3_BUCKET` |

### 4.2 Glue Job

- Naming file: `{domain}_{operation}.py` (es. `diritti_load_bronze.py`)
- Un file `requirements.txt` per ogni job o gruppo di job correlati
- Test con **pytest** come standard

### 4.3 Struttura progetto tipo

```
jobs/
  diritti_load_bronze.py
  diritti_transform_silver.py
  requirements.txt
tests/
  test_diritti_load_bronze.py
  conftest.py
```

---

## 5. Terraform / HCL

### 5.1 File Naming

File di infrastruttura con **underscore prefix** per i file di base:

| File | Contenuto |
|------|-----------|
| `_input.tf` | Variabili di input (`variable {}`) |
| `_local.tf` | Locals (`locals {}`) |
| `_output.tf` | Output (`output {}`) |
| `{servizio}-{risorsa}.tf` | Risorsa specifica (es. `api-gateway.tf`, `lambda-handler.tf`) |

### 5.2 Directory e Naming

- Directory: **kebab-case** (es. `diritti-api/`, `common-networking/`)
- Risorse Terraform: **snake_case** (`aws_lambda_function.diritti_handler`)
- Variabili: **snake_case** (`var.environment_name`)

### 5.3 Terragrunt

Struttura **live/modules mirror**:

- `live/{ambiente}/{servizio}/terragrunt.hcl` + `config.yaml`
- `modules/{servizio}/_input.tf`, `_local.tf`, `_output.tf`, `{risorsa}.tf`

### 5.4 State Management

- Backend: **S3** + **DynamoDB** per locking
- Naming bucket: `{env}-{repo-name}-terraform-state`
- Una tabella DynamoDB per ambiente per il lock

---

## 6. Logging Pattern

### 6.1 Structured JSON Logging

Tutti gli stack SIAE usano logging strutturato in formato JSON.

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "message": "Operazione completata",
  "correlationId": "abc-123-def",
  "service": "diritti-gestione-service",
  "environment": "collaudo"
}
```

### 6.2 Regole

| Regola | Dettaglio |
|--------|-----------|
| **Correlation ID** | Propagare sempre tra servizi. Header: `X-Correlation-Id` |
| **No PII nei log** | MAI loggare email, nomi, codici fiscali, IBAN |
| **Livelli** | `ERROR` per eccezioni, `WARN` per situazioni anomale, `INFO` per flusso normale, `DEBUG` solo in sviluppo |
| **Formato** | JSON strutturato in tutti gli ambienti (anche sviluppo) |

---

## 7. Vincoli

1. **Segui i pattern esistenti** nel repository. Se il progetto usa una convenzione, adottala anche se differisce leggermente da queste linee guida.
2. **Non inventare nuove convenzioni.** Se non trovi un pattern nel repo, usa queste linee guida come default.
3. **Non mischiare stili.** Se un file usa camelCase, tutto il file deve usare camelCase.
4. **Chiedi conferma** se trovi conflitti tra queste linee guida e il codice esistente nel repo.
5. **Rischio**: la scrittura di codice e' 🟡 MEDIO. Mostra la pre-flight card prima di creare o modificare file.

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-code-standards |
|:---|
| 📝 Operazione: `Modifica file sorgente esistente` |
| **▼ Azione** |
| 1. ✏️ Modifica codice esistente rispettando lo stile e le convenzioni del file → `<path file target>` |
| 💡 Perche': Modificare un file sorgente puo introdurre inconsistenze di stile rispetto al codice esistente. |
| 🚫 Se NO: La modifica non viene applicata. Analizza le convenzioni del file prima di procedere. |

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-code-standards |
|:---|
| 📝 Operazione: `Refactoring naming / struttura` |
| **▼ Azione** |
| 1. ✏️ Rinomina classi, metodi, file o riorganizza la struttura del progetto → `<path moduli coinvolti>` |
| 💡 Perche': Il refactoring di naming o struttura impatta tutti i riferimenti. Un rename non coordinato puo rompere dipendenze e build pipeline. |
| 🚫 Se NO: Il refactoring non viene eseguito. Verifica tutti i riferimenti e allinea il team prima di procedere. |

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| File modificati per singolo step | 5 | Se devi toccare piu' file, decomponi in sub-task. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue, non lista esaustiva. |

---

```
REQUIRED SUB-SKILL: siae-verification
```
Invoca `siae-verification` prima di dichiarare il codice conforme agli standard.

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Questo naming e' piu' chiaro per me" | Il codice viene letto dal team, non solo da te. Segui il pattern. |
| "I test rallentano la delivery" | I bug in produzione rallentano di piu'. I test sono investimento. |
| "Il logging lo aggiungo dopo" | 'Dopo' non arriva mai. I log mancanti rendono il debug cieco. |
| "Questa classe fa due cose ma e' piccola" | Le classi piccole crescono. Single Responsibility va applicata ora. |
| "Gli altri nel team capiscono lo stesso" | Il prossimo developer non conosce il tuo contesto. |
| "L'exception handler non serve qui" | I casi impossibili accadono in produzione. Gestiscili. |
| "Questo metodo ha 200 righe ma e' leggibile" | Oltre 30 righe e' un segnale. Spezza il metodo. |
| "I commenti spiegano il codice brutto" | Il codice dovrebbe spiegare se stesso. Riscrivi, non commentare. |

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|------------|---------|------|
| Analisi codice esistente | 🟢 Sicuro | No |
| Suggerimento convenzione | 🟢 Sicuro | No |
| Creazione nuovo file sorgente | 🟡 Medio | Si |
| Modifica file sorgente esistente | 🟡 Medio | Si |
| Refactoring naming / struttura | 🟡 Medio | Si |
| Modifica configurazione build (POM, package.json) | 🔴 Alto | Si |
