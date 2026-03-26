# Code Scan — Regole di estrazione scenari dal codice

> File di reference per Phase 0-bis della skill siae-qa.
> Usato quando il repo è accessibile e il tipo è in {BE, FE, ETL, Auth}.

---

## Trigger: quando eseguire il Code Scan

| Condizione | Azione |
|-----------|--------|
| Repo git accessibile + tipo in {BE, FE, ETL, Auth} | Esegui Code Scan |
| Tipo = Database | Solo migration files (`**/migration/*.sql`, `**/flyway/*.sql`) |
| Tipo in {Notification, Batch, Report, Feature Flag, File Processing} | Solo config files e client interfaces |
| Tipo = Integration REST/Event | Scan limitato a client interfaces e config |
| Nessun repo disponibile | Skip con `⚠️ Code Scan skippato — nessun repo rilevato` |
| Story puramente documentale/process | Skip senza avviso |

---

## Steps in ordine di esecuzione (max 90 secondi totali)

### Step 1 — Rilevamento stack (Glob, max 30s)

```
Glob("**/pom.xml")                         → Java/Spring
Glob("**/build.gradle")                    → Java/Gradle
Glob("**/package.json")                    → JS/TS stack
Glob("**/requirements.txt")               → Python
Glob("**/pyproject.toml")                 → Python modern
```

### Step 2 — File modificati recentemente (priorità scan)

```bash
git diff --name-only main..HEAD
```

Usa questa lista come filtro primario per lo scan: analizza prima i file toccati dalla branch.
Se la lista è vuota (branch = main) o non disponibile, procedi con i pattern globali.

### Step 3 — Grep selettivo per tipo (Grep, mai Read intero file)

**Per tipo BE (Java/Spring):**
```
Grep(pattern="@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)", type="java")
Grep(pattern="@(NotNull|NotBlank|Size|Pattern|Min|Max|Email|Valid|Positive|Future|Past|DecimalMin|DecimalMax)", type="java")
Grep(pattern="@ExceptionHandler", type="java", -A=3)
Grep(pattern="@PreAuthorize|@Secured|hasRole|hasAuthority", type="java")
Grep(pattern="antMatchers|requestMatchers|permitAll|authenticated()", type="java")
```

**Per tipo FE (Vue/TS):**
```
Grep(pattern="(required|validators|Validators\\.|useForm|defineSchema|z\\.object|yup\\.object)", glob="**/*.vue")
Grep(pattern="meta:\\s*\\{", glob="**/router/**/*.ts", -A=5)
Grep(pattern="beforeEnter|requiresAuth|canActivate", glob="**/*.ts")
Grep(pattern="defineEmits|\\$emit", glob="**/*.vue")
```

**Per tipo ETL (Python/PySpark):**
```
Grep(pattern="(fillna|dropna|coalesce|when.*isNull|isNotNull)", type="py")
Grep(pattern="(filter|where)\\(col", type="py")
Grep(pattern="nullable=False|nullable = False", type="py")
Grep(pattern="dropDuplicates|drop_duplicates", type="py")
```

**Per tipo Auth (Java/Spring Security):**
```
Grep(pattern="SecurityFilterChain|WebSecurityConfigurerAdapter", type="java")
Grep(pattern="@PreAuthorize|@PostAuthorize|@RolesAllowed", type="java")
Grep(pattern="corsConfigurationSource|allowedOrigins", type="java")
```

---

## Code Profile Card — Formato output

```
CODE PROFILE CARD — {STORY_ID}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Stack rilevato:     [Spring Boot 3.x / Vue 3 / PySpark / ...]
Branch analizzato:  [nome branch o "main"]
File analizzati:    [N files]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SEZIONE BE — se tipo BE]
ENDPOINT RILEVATI:
  [METODO] [PATH]   [params]   → [status codes derivati da ControllerAdvice]

VALIDAZIONI RILEVATE:
  [ClassName].[field]:  @[Annotation] — genera TC [NEG/EDGE] per [scenario]

EXCEPTION HANDLERS:
  [ExceptionClass]  → HTTP [status]

SECURITY:
  [path pattern]  → [permitAll / authenticated / hasRole('X')]

[SEZIONE FE — se tipo FE]
ROUTES PROTETTE:
  [path]  → requiresAuth: [true/false], role: [ruolo o N/A]

VALIDATORS RILEVATI:
  [componente].[campo]:  [tipo di validazione] — genera TC [NEG] per [scenario]

ACTIONS ASINCRONE:
  [store].[action]():  try/catch presente → TC [NEG] per API failure

[SEZIONE ETL — se tipo ETL]
TRASFORMAZIONI:
  [filter/where/withColumn] su [colonna] — genera TC [EDGE] per boundary

NULL HANDLING:
  [fillna/dropna/coalesce] su [colonna] — genera TC [EDGE] per null

SCHEMA CONSTRAINT:
  [campo] nullable=False — genera TC [NEG] per null su campo obbligatorio
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCENARI CANDIDATI DERIVATI: [N]
  Positivi:    [N]
  Edge case:   [N]
  Negativi:    [N]
  Profilazioni:[N]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ AVVISO: Questi scenari sono derivati dal codice, non dagli AC.
   Devono essere confermati dal developer in Fase 4a prima di diventare TC.
```

---

## Tabella derivazione automatica scenari — BE

| Annotation | Scenari da generare |
|------------|---------------------|
| `@NotNull` | 1 TC [NEG]: campo assente nel payload → 400 |
| `@NotBlank` | 2 TC [NEG]: campo null, campo `" "` (solo spazi) → 400 |
| `@Size(min=M, max=N)` | 2 TC [EDGE]: stringa M-1 chars → 400, stringa N+1 chars → 400 |
| `@Pattern(regexp=R)` | 1 TC [NEG]: stringa che viola il pattern → 400 |
| `@Min(value=V)` | 1 TC [EDGE]: valore V-1 → 400 |
| `@Max(value=V)` | 1 TC [EDGE]: valore V+1 → 400 |
| `@Email` | 2 TC [NEG]: formato non email, dominio mancante → 400 |
| `@Positive` | 2 TC [NEG]: valore 0 → 400, valore -1 → 400 |
| `@Future` | 1 TC [NEG]: data nel passato → 400 |
| `@Past` | 1 TC [NEG]: data nel futuro → 400 |
| `@ExceptionHandler(X.class)` | 1 TC [NEG]: condizione che causa X → HTTP status dall'handler |
| `@PreAuthorize("hasRole('R')")` | 1 TC [PROFILO]: utente con ruolo R → successo; 1 TC [PROFILO][NEG]: senza ruolo R → 403 |
| `antMatchers("/path").authenticated()` | 1 TC [PROFILO]: richiesta autenticata → pass; 1 TC [PROFILO][NEG]: non autenticato → 401 |

---

## Domande del tree eliminate dal code scan

Le seguenti domande diventano pre-compilate quando il Code Scan trova evidenza:

| Domanda tree | Eliminata se |
|-------------|--------------|
| BE L1/Q1: metodi HTTP e status code | Endpoint trovati da Grep su `@*Mapping` |
| BE L1/Q2: campi obbligatori e vincoli | Bean Validation annotations trovate |
| BE Auth L1/Q1: ruoli che possono eseguire | `@PreAuthorize` trovata |
| FE L1/Q2: campi obbligatori e formato | Validation schema Zod/Yup trovato |
| FE L2/Q5: guardia di navigazione | `meta.requiresAuth` o `beforeEnter` trovata |

Quando una domanda è pre-compilata dal Code Scan, la skill dice:
"Ho rilevato nel codice [evidenza]. Confermo: [scenario derivato]. Vuoi aggiungerlo
alla matrice o è fuori scope di questa story?"

---

## Integrazione con Fase 4a

In Fase 4a, la Code Profile Card diventa input primario:
1. Mostra gli "Scenari candidati" per categoria prima di fare domande
2. Per ogni scenario candidato: chiedi conferma o scarto (1 alla volta)
3. Solo per categorie non coperte dal Code Scan → fai le domande del tree standard
4. La matrice finale ha colonna `Fonte`: `AC` / `Code Scan` / `Developer`

---

## Fallback e casi limite

| Scenario | Comportamento |
|---------|--------------|
| Branch corrente ≠ main | Avvisa: "Code Scan su branch [branch] — il codice analizzato è quello in sviluppo" |
| Grep ritorna 0 risultati | Segnala "Codice non analizzabile — procedo con approccio solo-AC" |
| Codebase > 500 file | Usa solo i file da `git diff --name-only main..HEAD` |
| Codice generato da annotation processor | Segnala "Rilevato codice generato — scan parziale" |
| Endpoint non in scope della story | Filtra: analizza solo file modificati nella branch |
