# Language Registry — siae-bug-hunter

## Scopo

Fonte di verità per tutti i pattern grep specifici per linguaggio e framework.
I moduli M1-M5 definiscono le REGOLE (cosa è un bug e come validarlo).
Questo registry definisce i PATTERN (come trovarlo nel codice di ogni stack).

**Lookup:** bug type → sezione → riga del tuo LANG_ID → pattern grep da usare.
**Aggiunta linguaggio:** aggiungi una riga in ogni sezione. Non toccare i moduli M1-M5.

---

## 1. Mappa Completa: Estensione / Manifest → LANG_ID

### 1a. Linguaggi base

| Estensioni | Manifest di rilevamento | LANG_ID | Note |
|---|---|---|---|
| `.java` | `pom.xml`, `build.gradle`, `build.gradle.kts` | `JAVA` | Spring / Quarkus / Micronaut / plain Java |
| `.kt` | `build.gradle.kts`, `pom.xml` | `KOTLIN` | Spring Kotlin / Android / Ktor |
| `.cs` | `*.csproj`, `*.sln` | `CSHARP` | ASP.NET Core / .NET |
| `.py` | `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` | `PYTHON` | subtype vedi §1b |
| `.go` | `go.mod` | `GO` | stdlib / Gin / Echo / Fiber |
| `.scala` | `build.sbt`, `*.sbt` | `SCALA` | Spark / Akka / Play |
| `.rb` | `Gemfile` | `RUBY` | Rails / Sinatra |
| `.php` | `composer.json` | `PHP` | Laravel / Symfony |
| `.tf`, `.hcl` | `*.tf`, `terragrunt.hcl`, `.terraform/` | `HCL` | Terraform / Terragrunt / OpenTofu |
| `.sql` | `dbt_project.yml`, `models/`, `migrations/` | `SQL` | dbt / raw SQL / migrations |
| `.sh`, `.bash`, `.zsh` | assenza di altri manifest principali | `SHELL` | bash scripts / CI scripts |
| `.dart` | `pubspec.yaml` | `DART` | subtype vedi §1c |
| `.ts`, `.tsx`, `.js`, `.mjs`, `.cjs` | `package.json` | `*_TS` | subtype vedi §1d |
| `.vue` | `package.json` + `vue` in deps | `VUE` | Vue 2 / Vue 3 (SFC) |

### 1b. Python — subtypes (rilevati da requirements.txt / pyproject.toml)

| Dipendenza trovata | LANG_ID | Codebase Type |
|---|---|---|
| `fastapi`, `uvicorn` | `PYTHON_FASTAPI` | BE_PYTHON |
| `django`, `djangorestframework` | `PYTHON_DJANGO` | BE_PYTHON |
| `flask`, `flask-restful` | `PYTHON_FLASK` | BE_PYTHON |
| `pyspark`, `awsglue` | `PYTHON_SPARK` | ETL |
| `celery`, `rq` | `PYTHON_WORKER` | WORKER |
| `dbt-core` | `PYTHON_DBT` | DWH |
| `sqlalchemy`, `alembic` | `PYTHON_SQLALCHEMY` | BE_PYTHON / ETL |
| `pydantic` (senza framework web) | `PYTHON_PYDANTIC` | BE_PYTHON |
| nessuno dei precedenti | `PYTHON` | BE_PYTHON / CLI |

### 1c. Dart — subtypes

| Dipendenza in pubspec.yaml | LANG_ID | Codebase Type |
|---|---|---|
| `flutter` | `FLUTTER` | FE_MOBILE |
| `riverpod`, `flutter_riverpod` | `FLUTTER_RIVERPOD` | FE_MOBILE |
| `bloc`, `flutter_bloc` | `FLUTTER_BLOC` | FE_MOBILE |
| nessuno (puro Dart) | `DART` | CLI / BE_DART |

### 1d. TypeScript/JavaScript — subtypes (rilevati da package.json dependencies)

| Dipendenza trovata | LANG_ID | Codebase Type |
|---|---|---|
| `react`, `react-dom` | `REACT` | FE_WEB |
| `react` + `react-native` | `REACT_NATIVE` | FE_MOBILE |
| `@angular/core` | `ANGULAR` | FE_WEB |
| `@ionic/angular` o `@ionic/react` | `IONIC` | FE_MOBILE_WEB |
| `vue` (v3) | `VUE3` | FE_WEB |
| `vue` (v2, `"vue": "^2`) | `VUE2` | FE_WEB |
| `next` (Next.js) | `NEXTJS` | FE_WEB / BFF |
| `nuxt` | `NUXT` | FE_WEB / BFF |
| `express`, `@types/express` | `EXPRESS` | BE_NODE |
| `@nestjs/core` | `NESTJS` | BE_NODE |
| `fastify` | `FASTIFY` | BE_NODE |
| `svelte` | `SVELTE` | FE_WEB |
| TypeScript senza nessuno dei precedenti | `TYPESCRIPT` | BE_NODE / BFF |
| JavaScript senza nessuno dei precedenti | `JAVASCRIPT` | BE_NODE / FE_WEB |

---

## 2. Mappa Codebase Type → Moduli Attivi

| Codebase Type | Moduli attivi | Note |
|---|---|---|
| FE_WEB (REACT, VUE2, VUE3, ANGULAR, NEXTJS, NUXT, SVELTE) | M1, M3, M4, M5 | M2 per state management (Redux/Pinia/NgRx) |
| FE_MOBILE (FLUTTER, FLUTTER_RIVERPOD, FLUTTER_BLOC, REACT_NATIVE) | M1, M3, M4, M5 | |
| FE_MOBILE_WEB (IONIC) | M1, M3, M4, M5 | Pattern ibridi FE_WEB + FE_MOBILE |
| BE_JAVA / BE_KOTLIN | M1, M2, M3, M4, M5 | Coverage completa |
| BE_CSHARP | M1, M2, M3, M4, M5 | |
| BE_NODE (EXPRESS, NESTJS, FASTIFY) | M1, M2, M3, M4, M5 | |
| BE_PYTHON (tutti i subtypes) | M1, M2, M3, M4, M5 | |
| BE_GO | M1, M2, M3, M4, M5 | |
| BE_SCALA | M1, M2, M3, M4, M5 | |
| BE_RUBY | M1, M2, M3, M5 | M4 limitato |
| BE_PHP | M1, M2, M3, M5 | M4 limitato |
| BFF (NEXTJS, NUXT, NESTJS con proxy) | M1, M3 | Solo contract e error propagation |
| ETL (PYTHON_SPARK, SCALA) | M2 (B1,B2,B3), M3, M5 (A,E,F) | Pattern ETL dedicati §9 |
| DWH (SQL, PYTHON_DBT) | M2 (B1,B5), M5 (E,F) | Pattern SQL/dbt §10 |
| IAC (HCL) | M2 (S3), M5 (A,E) | Pattern Terraform §11 |
| WORKER (PYTHON_WORKER, JAVA con @Scheduled) | M2 (S2,S3), M3, M4 (CC1,CC3) | |
| CLI | M2 (B1,B4,B6), M3, M5 | |
| INFRA_SCRIPT (SHELL) | M3 | Solo error propagation |

---

## 3. Pattern Registry per Bug Type

---

### NULL-ACCESS — Accesso senza null-check (M2-B4, M2-B6)

| LANG_ID | Pattern grep | Cosa cerca | Falsificatori sicuri |
|---|---|---|---|
| `JAVA` | `\.findFirst\(\)\.get\(\)\|Optional\.get\(\)` | Unsafe Optional unwrap | `.orElseThrow()`, `.orElse()`, `.isPresent()` |
| `KOTLIN` | `!![a-zA-Z]\|\.first\(\)\.[a-z]\|\.single\(\)\.[a-z]` | `!!` senza guard, first/single su lista | `?.`, `?:`, `?.let`, `firstOrNull()` |
| `CSHARP` | `\.Value\b\|\.First\(\)\.\|\.Single\(\)\.` | Nullable.Value, LINQ First/Single | `.HasValue`, `?.`, `FirstOrDefault()` |
| `REACT` | `\.(find\|filter)\(.*\)\.[a-zA-Z]\|props\.[a-z]+\.[a-z]+(?!\?)` | find/filter result senza guard, props non-optional chained | `?.`, `??`, PropTypes `isRequired` |
| `VUE2` | `this\.\$store\.state\.[a-z]+\.[a-z]+\b(?!\?)` | Vuex state access senza guard | `?.`, computed con default |
| `VUE3` | `\{\{[^}]*\.[a-z]+\.[a-z]+[^?}]\}\}\|store\.[a-z]+\.[a-z]+(?!\?)` | Template o Pinia access senza optional chain | `?.`, `?? ''`, `v-if` |
| `ANGULAR` | `this\.[a-z]+\.[a-z]+\.[a-z]+(?!\?)\|observable\$\.[a-z]+` | Service property chain, observable non guardato | `?.`, AsyncPipe con `*ngIf`, `?.` in template |
| `IONIC` | come ANGULAR / REACT a seconda del framework base | | |
| `NEXTJS` | `props\.[a-z]+\.[a-z]+(?!\?)\|data\?\.pages\?` | getServerSideProps / getStaticProps result | `?.`, `??` |
| `NUXT` | `useAsyncData.*\.data\.[a-z]+(?!\?)` | Nuxt 3 composable data access | `?.`, `pending` check |
| `SVELTE` | `\$[a-z]+\.[a-z]+\.[a-z]+(?!\?)` | Svelte store access | `?.`, `{#if}` block |
| `FLUTTER` | `\![a-zA-Z]\|\.first\.[a-z]\|\.single\.[a-z]` | Null assertion `!`, list first/single | `?.`, `??`, `firstWhere(orElse:)` |
| `FLUTTER_RIVERPOD` | `ref\.read\(.*\)\.[a-z]+\.[a-z]+(?!\?)` | Provider state access | `?.`, `AsyncValue.when()` |
| `FLUTTER_BLOC` | `state\.[a-z]+\.[a-z]+(?!\?)\b` | BLoC state access senza guard | type check `is`, `?.` |
| `REACT_NATIVE` | come REACT | | |
| `PYTHON` | `next\(filter\(.*\)\)\.[a-z]\|\[0\]\.[a-z]` | next() o [0] senza try/except | `try/except`, `or None`, guard |
| `PYTHON_DJANGO` | `\w+\.objects\.get\(.*\)\.[a-z]\|\.first\(\)\.[a-z]` | QuerySet.get() (lancia se assente), first() (ritorna None) | `get_or_404()`, `filter().first()` con guard |
| `PYTHON_FASTAPI` | `Optional\[.*\]\s*=\s*None.*\n.*\.[a-z]+` | Parametro Optional usato senza check | `if x is not None` |
| `PYTHON_SQLALCHEMY` | `session\.query\(.*\)\.first\(\)\.[a-z]` | first() result acceduto direttamente | guard `if result:` |
| `GO` | `\w+,\s*err\s*:=.*\n\s*[^i]` | err ritornato ma riga successiva non ha `if err` | `if err != nil` |
| `SCALA` | `\.get\b(?!\s*OrElse)\|\.head\b(?!\s*Option)` | Option.get() o List.head | `.getOrElse()`, `.headOption` |
| `RUBY` | `\w+\.find\(.*\)\.[a-z]\|\.first\.[a-z]` | ActiveRecord find senza rescue | `find_by`, rescue, `&.` safe navigator |
| `PHP` | `->\w+\s*->\w+(?!\?)` | Null object chain | `?->`, null check, `isset()` |
| `EXPRESS` | `req\.body\.[a-z]+\.[a-z]+(?!\?)` | body property access senza validation | joi/zod validate prima, `?.` |
| `NESTJS` | `@Body\(\).*\n.*\.[a-z]+\.[a-z]+(?!\?)` | DTO property chain | class-validator, `?.` |

---

### STATE-SWITCH — Switch/match non exhaustivo (M2-S1)

| LANG_ID | Pattern grep | Note | Falsificatori |
|---|---|---|---|
| `JAVA` | `switch\s*\(.*[Ss]tatus\|switch\s*\(.*[Ss]tate\|switch\s*\(.*[Tt]ype` | Switch su enum | `default:` con throw o log |
| `KOTLIN` | `when\s*\(.*[Ss]tatus\|when\s*\(.*[Ss]tate` | `when` su sealed/enum | `else ->` |
| `CSHARP` | `switch\s*\(.*[Ss]tatus\|switch\s*\(.*[Ss]tate` | switch expression o statement | `default:`, `_ =>` in switch expression |
| `REACT` | `switch\s*\(.*action\.type\|switch\s*\(.*[Ss]tate\.[Ss]tatus` | Redux reducer switch | `default:` return state |
| `VUE2` | `switch\s*\(\s*state\.[Ss]tatus\|switch\s*\(\s*mutation\.type` | Vuex mutation/getter | `default:` case |
| `VUE3` | `switch\s*\(\s*\w+\.value\)\|switch\s*\(\s*[Ss]tatus` | Pinia getter/action | `default:` |
| `ANGULAR` | `switch\s*\(.*\.[Ss]tatus\)\|switch\s*\(.*this\.[Ss]tate` | Component/service switch | `default:` |
| `FLUTTER` | `switch\s*\(.*[Ss]tatus\|switch\s*\(.*[Ss]tate` | Switch su enum Dart | `default:` |
| `FLUTTER_BLOC` | `on<\w+>\|switch.*state\s+is\b` | BLoC event handler / state type check | tutti gli `is` coperti |
| `PYTHON` | `match\s+\w+[^:]*:\s*\n(?!.*case\s+_)` | match senza `case _` wildcard | `case _:` |
| `GO` | `switch\s+\w+(\.\w+)?\s*\{[^}]*\}(?!\s*//)` | switch senza default | `default:` |
| `SCALA` | `\w+\s+match\s*\{[^}]*\}` | match — verifica sealed coverage | `case _ =>` |
| `EXPRESS` | `switch\s*\(\s*req\.body\.[a-z]\|switch\s*\(\s*req\.params` | Route handler switch | `default:` |
| `NESTJS` | come EXPRESS | | |

**Validazione post-grep (tutti i linguaggi):**
1. Estrai i valori dell'enum/union/sealed class dal progetto (cerca la definizione)
2. Estrai i case presenti nello switch/match
3. Se almeno un valore enum manca nei case E non c'è default/wildcard → CANDIDATO

---

### FLOAT-MONEY — Float/double per importi finanziari (M2-B3)

**APPLICA SEMPRE Step Z1/Z2/Z3 di M2-B3 prima di segnalare.**

| LANG_ID | Pattern grep | Tipo sicuro atteso |
|---|---|---|
| `JAVA` | `(double\|float)\s+\w*(price\|amount\|total\|fee\|cost\|importo\|valore)` | `BigDecimal` |
| `KOTLIN` | `:\s*(Double\|Float)\b.*\n.*\w*(price\|amount\|total\|fee)` | `BigDecimal` |
| `CSHARP` | `(double\|float)\s+\w*(price\|amount\|total\|fee)\|double\s+\w*Price` | `decimal` |
| `REACT` | `const\s+(price\|amount\|total\|fee)\s*=\s*[0-9]+\.[0-9]\|:\s*number.*price` | Dinero.js / centesimi interi |
| `VUE2` | `(price\|amount\|total\|fee)\s*:\s*[0-9]+\.[0-9]` in data() | idem |
| `VUE3` | `const\s+(price\|amount\|total\|fee)\s*=\s*ref\([0-9]+\.[0-9]` | idem |
| `ANGULAR` | `(price\|amount\|total\|fee)\s*:\s*number\b` in classe | idem |
| `FLUTTER` | `double\s+\w*(price\|amount\|total\|fee)` | int (centesimi) |
| `PYTHON` | `(price\|amount\|total\|fee)\s*=\s*float\(` | `Decimal` |
| `PYTHON_DJANGO` | `FloatField\(\)\s*#.*(price\|amount\|fee)\|models\.FloatField.*price` | `DecimalField` |
| `PYTHON_SQLALCHEMY` | `Column\(Float\).*#.*(price\|amount)\|Float.*price` | `Numeric(precision, scale)` |
| `GO` | `float(32\|64)\s+\w*(price\|amount\|total\|fee)` | int64 centesimi / `shopspring/decimal` |
| `SCALA` | `(Double\|Float)\s+\w*(price\|amount\|total\|fee)` | `BigDecimal` |
| `RUBY` | `(price\|amount\|total\|fee)\s*:\s*:float\|t\.float\s+:(price\|amount)` | `:decimal` in migration |
| `PHP` | `float\s+\$(price\|amount\|total\|fee)` | `bcmath` / int centesimi |
| `EXPRESS` | `(price\|amount\|total)\s*=\s*parseFloat\(` | idem REACT |
| `NESTJS` | `@IsNumber\(\).*\n.*price\|:\s*number.*price` | idem REACT |

---

### DIV-ZERO — Divisione senza guard (M2-B1)

| LANG_ID | Pattern grep | Falsificatori |
|---|---|---|
| `JAVA` | `\s/\s[^/=]\|\.divide\(\|BigDecimal.*divide` | `if (x == 0)`, `== 0 ? 0 :`, `ROUND_HALF_UP` non implica guard |
| `KOTLIN` | `\s/\s[^/=*]\b` | `takeIf { it != 0 }`, guard esplicito |
| `CSHARP` | `\s/\s[^/=]\b` | guard esplicito, `checked {}` |
| `REACT` | `\s/\s[^/=]\|Math\.floor\(.*\/` | ternary `x === 0 ? 0 : ...` |
| `VUE2` | `\s/\s[^/=]\b` in metodi/computed | idem |
| `VUE3` | `\s/\s[^/=]\b` in composable | idem |
| `ANGULAR` | `\s/\s[^/=]\b` in pipe/service | idem |
| `PYTHON` | `\s/\s[^/0-9=]\|\/\/\s*\w` | `if x != 0`, `try/except ZeroDivisionError` |
| `PYTHON_SPARK` | `\.groupBy.*\.agg.*\/\|\.withColumn.*\/\s*col\(` | `when(col != 0, ...)` |
| `GO` | `\s/\s[^/=]\b` | `if divisor == 0` prima |
| `SCALA` | `\s/\s[^/=]\b` | guard esplicito |
| `SQL` | `NULLIF\s*\(.*,\s*0\)\s*$` mancante vicino a `/` | `NULLIF(x, 0)` |
| `HCL` | `/\s*(var\.\|local\.)\w+` | guard con `condition` in variable validation |
| `RUBY` | `\s/\s[^/=]\b` | guard, `rescue ZeroDivisionError` |
| `PHP` | `\s/\s[^/=]\b\|intdiv\(` | guard esplicito |
| `SHELL` | `\$((\w+\s*/\s*\w+))` | `[ $x -eq 0 ]` prima |

---

### DATE-TZ — Date senza timezone (M2-B2, M5-F)

| LANG_ID | Pattern grep | Tipo sicuro | Falsificatori |
|---|---|---|---|
| `JAVA` | `LocalDateTime\.now\(\)\|LocalDate\.now\(\)` | `ZonedDateTime`, `Instant` | `.atZone(ZoneOffset.UTC)` |
| `KOTLIN` | `LocalDateTime\.now\(\)\|LocalDate\.now\(\)` | `ZonedDateTime` | idem |
| `CSHARP` | `DateTime\.Now\b\|DateTime\.Today\b` | `DateTimeOffset`, `DateTime.UtcNow` | `.ToUniversalTime()` |
| `REACT` | `new\s+Date\(\)\s*[<>!=]\|Date\.now\(\)\s*[<>]` | UTC timestamp | `toISOString()`, `date-fns-tz`, `dayjs.utc()` |
| `VUE2` | `new\s+Date\(\)\s*[<>!=]` in metodi | idem | idem |
| `VUE3` | `new\s+Date\(\)\s*[<>!=]` in composable | idem | idem |
| `ANGULAR` | `new\s+Date\(\)\s*[<>!=]` in service/pipe | idem | `DatePipe` con timezone, `date-fns-tz` |
| `FLUTTER` | `DateTime\.now\(\)` confrontato con altra data | `DateTime.now().toUtc()` | `.toUtc()` prima del confronto |
| `PYTHON` | `datetime\.now\(\)(?!\s*tz=)\|datetime\.utcnow\(\)` | `datetime.now(timezone.utc)` | `timezone.utc` passato |
| `PYTHON_DJANGO` | `timezone\.now\(\)` vs `datetime\.now\(\)` | `django.utils.timezone.now()` | `USE_TZ = True` in settings |
| `GO` | `time\.Now\(\)` comparato senza `.UTC()` | `time.Now().UTC()` | `.UTC()` su entrambe le date |
| `SCALA` | `LocalDateTime\.now\(\)` | `ZonedDateTime` | idem Java |
| `SQL` | `GETDATE\(\)\|NOW\(\)\|CURRENT_TIMESTAMP` | `GETUTCDATE()`, `UTC_TIMESTAMP()` | `AT TIME ZONE 'UTC'` |
| `RUBY` | `Time\.now\b` | `Time.now.utc` | `.utc` |
| `PHP` | `new\s+DateTime\(\)(?!\s*'now',\s*new\s+DateTimeZone)` | `new DateTime('now', new DateTimeZone('UTC'))` | UTC timezone esplicita |

---

### MISSING-ERROR-PROPAGATION — Errore non propagato (M3)

| LANG_ID | Pattern grep | Note | Falsificatori |
|---|---|---|---|
| `JAVA` | `catch\s*\([^)]+\)\s*\{\s*(?:log\|logger)\.[a-z]+\(` | catch + solo log | `throw`, risposta HTTP esplicita |
| `KOTLIN` | `catch\s*\([^)]+\)\s*\{\s*(?:log\|logger)\.[a-z]+\(` | idem | idem |
| `CSHARP` | `catch\s*\([^)]+\)\s*\{\s*(?:_logger\|Console\.Write)\b` | idem | `throw`, return Problem() |
| `REACT` | `\.catch\s*\(\s*(?:err\|e)\s*=>\s*(?:console\.(?:log\|error\|warn))` | .catch con solo console | setState con error, toast |
| `VUE2` | `\.catch\s*\(\s*(?:err\|e)\s*=>\s*(?:console\.)\|\.catch\s*\(\s*\(\s*\)\s*=>\s*\{` | .catch vuoto o solo console | `this.error =`, `this.$emit('error')` |
| `VUE3` | `\.catch\s*\(\s*(?:err\|e)\s*=>\s*(?:console\.)\|onError\s*\(` | idem Vue 2 | `error.value =`, `useErrorHandler` |
| `ANGULAR` | `catchError\s*\(\s*(?:err\|e)\s*=>\s*\{\s*(?:console\.)\b` | RxJS catchError con solo log | `throwError`, `return EMPTY` con side effect |
| `NEXTJS` | `catch\s*\([^)]+\)\s*\{\s*console\.` in API route | idem | `res.status(500).json(...)` |
| `FLUTTER` | `catch\s*\([^)]+\)\s*\{\s*(?:print\|debugPrint)\b(?!.*rethrow)` | catch + solo print | `rethrow`, `showSnackBar`, setState con error |
| `FLUTTER_BLOC` | `on<\w+>.*\{\s*(?:print\|log)\b(?!.*emit)` | handler senza emit ErrorState | `emit(ErrorState(...))` |
| `PYTHON` | `except\s+\w+[^:]*:\s*\n\s*(?:logger\|logging\|print)\b(?!\s*raise)` | except + log senza re-raise | `raise`, `return JSONResponse(status=500)` |
| `PYTHON_FASTAPI` | `except\s+\w+[^:]*:\s*\n\s*(?:logger\|print)\b(?!.*raise\|.*HTTPException)` | nessun HTTPException né raise | `raise HTTPException(status_code=...)` |
| `PYTHON_DJANGO` | `except\s+\w+[^:]*:\s*\n\s*(?:logger\|print)\b(?!.*raise\|.*Http404)` | nessun Http404 né raise | `raise Http404`, `return HttpResponseServerError` |
| `GO` | `if\s+err\s*!=\s*nil\s*\{\s*(?:log\.|fmt\.Print)` + nessun `return` | err loggato ma non ritornato | `return ..., err` |
| `EXPRESS` | `catch\s*\([^)]+\)\s*\{\s*console\.\b(?!.*next\()` | catch senza next(err) | `next(err)` |
| `NESTJS` | `catch\s*\([^)]+\)\s*\{\s*(?:this\.logger\|console\.)\b(?!.*throw)` | catch senza throw o HttpException | `throw new HttpException(...)` |
| `SCALA` | `\.recover\s*\{\s*case.*=>\s*(?:logger\|log)\b` | recover con solo log | `Future.failed(...)`, risposta HTTP |
| `RUBY` | `rescue\s+\w+\s*\n\s*(?:Rails\.logger\|puts\|p\s)\b(?!\s*raise)` | rescue + solo log | `raise`, `render status:` |
| `PHP` | `catch\s*\([^)]+\)\s*\{\s*(?:error_log\|var_dump\|echo)\b(?!.*throw)` | catch + solo log | `throw $e`, `return response()->json(...)` |
| `SHELL` | `2>/dev/null\s*$\|\|\s*true\s*$\|\|\s*:\s*$` | errore ignorato | `\|\| { echo "ERROR"; exit 1; }` |

---

### ASYNC-STALE — Async senza cleanup / race condition FE (M4)

| LANG_ID | Pattern grep | Bug | Falsificatori |
|---|---|---|---|
| `REACT` | `useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*(?:fetch\|axios)[^}]*\}[^,]*,` senza `return` con cleanup | stale response su unmount | AbortController, return cleanup |
| `REACT` | `useMemo\s*\(\s*\(\s*\)\s*=>\s*debounce\s*\(.*\[\s*\]` | stale closure nel debounce | deps corrette, useCallback |
| `VUE3` | `onMounted\s*\(\s*async\s*\(\s*\)\s*=>\s*\{[^}]*await[^}]*\}` senza `onUnmounted` | stale response su unmount | `onUnmounted(() => controller.abort())` |
| `VUE3` | `watch\s*\(.*async.*\{[^}]*await[^}]*\}` senza `onCleanup` | WebSocket / subscription leak | `onCleanup(cleanup)` |
| `VUE2` | `mounted\s*\(\s*\)\s*\{[^}]*\$http\.[^}]*\}` senza `beforeDestroy` | idem Vue3 | cleanup in `beforeDestroy` |
| `ANGULAR` | `this\.service\.\w+\(\)\.subscribe\((?!.*takeUntil\|.*takeUntilDestroyed)` | subscription leak | `takeUntil(destroy$)`, `takeUntilDestroyed()` |
| `ANGULAR` | `ngOnInit.*subscribe\((?!.*this\.\w+\$\s*=)` | subscription non salvata per unsubscribe | `this.sub = ...subscribe()`, `async pipe` |
| `FLUTTER` | `StreamSubscription.*\n(?!.*cancel\(\))` nel widget | stream leak | `subscription.cancel()` in `dispose()` |
| `FLUTTER_BLOC` | `\bBlocProvider\b.*\n(?!.*close\(\))` — verifica `dispose` | BLoC non chiuso | `context.read<Bloc>().close()`, `BlocProvider` auto-close |
| `REACT_NATIVE` | come REACT | | |
| `NEXTJS` | come REACT (client components) | | |

---

### OPTIMISTIC-NO-ROLLBACK — Optimistic update senza rollback (M4-FE-RC3)

| LANG_ID | Pattern grep | Falsificatori |
|---|---|---|
| `REACT` | `set\w+\s*\(.*prev.*=>\s*\[\.\.\.prev\|dispatch\s*\(.*add\|optimistic` senza rollback nel `.catch` | `.catch(err => set\w+(prev))` |
| `VUE3` | `\w+\.value\.push\(\|state\.\w+\.push\(` senza ripristino in catch | catch con rollback |
| `VUE2` | `this\.\w+\.push\(` in azione Vuex senza rollback nel catch | `commit('rollback...')` nel catch |
| `ANGULAR` | `this\.\w+\.push\(.*\n.*this\.service\.\w+\(` senza catchError con rollback | `catchError` con ripristino array |
| `FLUTTER` | `setState.*list\.add\(` seguito da await senza `.catchError\|on Exception` | catch con setState rollback |

---

### REQUIRED-MISMATCH — Validazione FE vs BE (M5-A)

**BE — Pattern campo obbligatorio:**

| LANG_ID | Pattern grep | Note |
|---|---|---|
| `JAVA` | `@NotNull\|@NotBlank\|@NotEmpty\|@NonNull` | Bean Validation JSR-380 |
| `KOTLIN` | `@NotNull\|@field:NotNull\|@NotBlank` | |
| `CSHARP` | `\[Required\]\|\[BindRequired\]\|\[JsonRequired\]` | Data Annotations |
| `PYTHON_FASTAPI` | `Field\(\.\.\.\)\|Body\(\.\.\.\)\|Query\(\.\.\.\)` | `...` = required in Pydantic |
| `PYTHON_DJANGO` | `blank=False\b(?!,\s*default)\|null=False\b(?!,\s*default)` | default assente = required |
| `PYTHON_PYDANTIC` | `Field\(\.\.\.\)\|:\s*\w+\s*(?!=)` in BaseModel | campo senza default |
| `GO` | `binding:"required"\|validate:"required"` | gin/validator struct tag |
| `NESTJS` | `@IsNotEmpty\(\)\|@IsDefined\(\)\|@IsString\(\)(?!.*optional)` | class-validator |
| `EXPRESS` | `Joi\.string\(\)\.required\(\)\|z\.string\(\)\.min\(1\)` | Joi / Zod schema |
| `RUBY` | `validates\s+:\w+,\s*presence:\s*true` | ActiveRecord |
| `PHP` | `'required'\s*=>\s*true\|\[Required\]` | Laravel validation rules |

**FE — Pattern campo required:**

| LANG_ID | Pattern grep | Note |
|---|---|---|
| `REACT` | `required:\s*true\|Validators\.required\|z\.string\(\)\.min\(1\)\|yup\.\w+\(\)\.required` | RHF / Zod / Yup |
| `VUE2` | `required:\s*true\|v-validate.*required` | Vuelidate / vee-validate |
| `VUE3` | `required:\s*true\|z\.string\(\)\.min\(1\)\|\.required\(\)` | Zod / Vuelidate 2 |
| `ANGULAR` | `Validators\.required\|\[Validators\.required\]` | ReactiveFormsModule |
| `IONIC` | come ANGULAR o REACT a seconda del framework base | |
| `FLUTTER` | `validator.*isEmpty\|FormBuilderValidators\.required` | TextFormField validator |
| `NEXTJS` | come REACT | |

---

### STRING-TRUNCATION — Troncamento silente (M5-E)

**BE — lunghezza colonna:**

| LANG_ID | Pattern grep | Note |
|---|---|---|
| `JAVA` | `@Column\s*\(.*length\s*=\s*[0-9]+` | JPA |
| `KOTLIN` | `@Column\s*\(.*length\s*=\s*[0-9]+` | |
| `CSHARP` | `\[MaxLength\s*\([0-9]+\)\]\|\[StringLength\s*\([0-9]+` | Data Annotations |
| `PYTHON_DJANGO` | `CharField\(max_length\s*=\s*[0-9]+\)\|SlugField\(max_length` | Django models |
| `PYTHON_SQLALCHEMY` | `Column\(String\([0-9]+\)\)\|String\([0-9]+\)` | SQLAlchemy |
| `GO` | `gorm:"size:[0-9]+"\|json:"[^"]*" db:"varchar\([0-9]+\)"` | GORM tags |
| `RUBY` | `limit:\s*[0-9]+` in migration | ActiveRecord |
| `PHP` | `'string',\s*\[.*'length'\s*=>\s*[0-9]+` in Doctrine | |
| `SQL` | `varchar\s*\([0-9]+\)\|nvarchar\s*\([0-9]+\)\|char\s*\([0-9]+\)` | DDL |

**FE — maxLength input:**

| LANG_ID | Pattern grep | Note |
|---|---|---|
| `REACT` | `maxLength:\s*[0-9]+\|maxlength\s*=\s*[0-9]+` | HTML attr o RHF |
| `VUE2` | `:maxlength\s*=\s*["']\|maxlength\s*=\s*[0-9]+` | |
| `VUE3` | idem VUE2 | |
| `ANGULAR` | `maxlength\s*=\s*[0-9]+\|Validators\.maxLength\([0-9]+\)` | |
| `FLUTTER` | `maxLength:\s*[0-9]+` | TextField / TextFormField |

---

### LONG-OVERFLOW — Long BE → number JS (M5-D)

Applicabile alle coppie: `JAVA`/`KOTLIN`/`CSHARP` BE + `REACT`/`VUE2`/`VUE3`/`ANGULAR`/`NEXTJS` FE.

| Layer | LANG_ID | Pattern grep | Sicuro se |
|---|---|---|---|
| BE | `JAVA` | `private\s+Long\s+\w*[iI][dD]\|@GeneratedValue.*strategy.*IDENTITY` | `@JsonSerialize(using=ToStringSerializer.class)` |
| BE | `KOTLIN` | `val\s+\w*[iI][dD]\s*:\s*Long` | idem |
| BE | `CSHARP` | `public\s+long\s+\w*[iI][dD]` | serializzato come stringa |
| FE | `REACT` | `parseInt\s*\(\w*[iI][dD]\|Number\s*\(\w*[iI][dD]` | BigInt, stringa |
| FE | `VUE2` | `parseInt\s*\(\w*[iI][dD]\|Number\s*\(\w*[iI][dD]` | idem |
| FE | `VUE3` | idem VUE2 | idem |
| FE | `ANGULAR` | idem REACT | idem |
| FE | `NEXTJS` | idem REACT | idem |

---

### N-PLUS-ONE — N+1 query in loop (M4-BE-CC5)

| LANG_ID | Pattern grep | Falsificatori |
|---|---|---|
| `JAVA` | `for\s*\(.*:\s*\w+[Ll]ist\b[^{]*\{[^}]*\.get\w+\(\)` | `@EntityGraph`, `JOIN FETCH`, MapStruct projection |
| `KOTLIN` | `\.forEach\s*\{[^}]*\.\w+\(\)\s*\.\w+\b` | idem Java |
| `CSHARP` | `foreach\s*\(.*in\s+\w+\)\s*\{[^}]*\.\w+\.\w+\b` | `.Include()` in EF Core, DTO projection |
| `PYTHON_DJANGO` | `for\s+\w+\s+in\s+\w+\.all\(\)\s*:\s*\n[^:]*\.\w+\s*\.\w+` | `select_related()`, `prefetch_related()` |
| `PYTHON_SQLALCHEMY` | `for\s+\w+\s+in\s+session\.query\(\w+\)\s*:\s*\n[^:]*\.\w+\.\w+` | `joinedload()`, `subqueryload()` |
| `GO` | `for\s+[^{]+range\s+\w+\s*\{[^}]*db\.(Where\|Find\|First)` | JOIN nella query iniziale |
| `SCALA` | `\.map\s*\{[^}]*repo\.\w+\(\|for\s*\{[^}]*<-.*\.findAll` | Slick joinedload |
| `RUBY` | `\.each\s*\{\s*\|\w+\|\s*\n[^}]*\.\w+\.[^}]*\}` | `includes(:relation)`, `eager_load` |
| `PHP` | `foreach\s*\(\$\w+\s+as\s+\$\w+\)\s*\{[^}]*->\w+->\w+` | Doctrine `JOIN FETCH`, Laravel `with()` |

---

### IAC-PATTERNS — Regole specifiche HCL/Terraform (M2-S3, M5-A)

| Pattern ID | Grep | Bug | Falsificatori |
|---|---|---|---|
| IAC-1 | `variable\s+"[^"]+"\s*\{\s*\}` | Variabile senza default/description/type → errore runtime | `default =`, `type =` |
| IAC-2 | `count\s*=\s*var\.\w+(?!\s*>\s*0\|\s*==\s*[1-9])` | count=var senza guard > 0 → resource distrutta se 0 | condition validation |
| IAC-3 | `value\s*=\s*\w+\.\w+\.\w+\.id\b(?!\s*=\s*null)` in output | Output su resource con count condizionale → crash plan | `try(...)`, `?` ternary HCL |
| IAC-4 | `variable\s+"[^"]*(?:password\|secret\|token\|key)[^"]*"\s*\{[^}]*sensitive\s*=\s*false` | Segreto esposto in state/plan | `sensitive = true` |
| IAC-5 | `lifecycle\s*\{[^}]*prevent_destroy\s*=\s*false` su db/storage | Risorsa stateful distruttibile senza protezione | `prevent_destroy = true` |

---

### ETL-PATTERNS — Regole specifiche PySpark/Glue/Scala Spark (M2, M3, M5)

| Pattern ID | LANG_ID | Grep | Bug | Falsificatori |
|---|---|---|---|---|
| ETL-1 | `PYTHON_SPARK` | `\.collect\(\)(?!\s*\[0\]\|\s*\[:\d)` | OOM su dataset grande → collect tutto in driver | `.take(N)`, `.limit(N).collect()` |
| ETL-2 | `PYTHON_SPARK` | `@udf\s*\(.*\)\s*\ndef\s+\w+\([^)]+\)\s*:\s*\n\s*(?!.*if.*None\|.*is None)` | UDF senza None check → NullPointerException su null input | `if value is None: return None` |
| ETL-3 | `PYTHON_SPARK` | `\.join\s*\(\s*\w+\s*,(?!.*broadcast)` | Join senza broadcast su tabella piccola → shuffle inutile | `broadcast(small_df)` |
| ETL-4 | `PYTHON_SPARK`/`SCALA` | `for\s+\w+.*:\s*\n[^:]*\.count\(\)` | Spark action in loop → N job separati | pre-calcola count fuori dal loop |
| ETL-5 | `PYTHON_SPARK` | `spark\.read\.\w+\s*\([^)]*\)(?!.*\.schema\s*\()` | Schema inferito senza `schema=` → schema drift silente | `schema=StructType(...)` esplicito |
| ETL-6 | `SCALA` | `\.toDS\(\)\.map\b(?!.*Encoder)` | Dataset map senza Encoder → SerializationException a runtime | Encoder implicito definito |

---

### DWH-PATTERNS — Regole specifiche SQL/dbt (M2, M5)

| Pattern ID | LANG_ID | Grep | Bug | Falsificatori |
|---|---|---|---|---|
| DWH-1 | `SQL` | `SELECT\s+\*\s+FROM` in view/model | SELECT * → schema drift silente quando la tabella sorgente cambia | colonne esplicite |
| DWH-2 | `SQL` | `/\s*(?:SUM\|COUNT\|AVG\|\w+)\b(?!.*NULLIF)` | Divisione senza NULLIF → division-by-zero se aggregato è 0 | `NULLIF(expr, 0)` |
| DWH-3 | `SQL` | `CAST\s*\([^)]+AS\s+INT\)` su colonna decimale | Cast che tronca silenziosamente | `ROUND(x)` prima del cast |
| DWH-4 | `PYTHON_DBT` | `{{ ref\('.*'\) }}` in `models/` senza `config(materialized=...)` | Materializzazione default (view) su modello pesante | `config(materialized='table')` |
| DWH-5 | `SQL` | `WHERE\s+\w+\s*=\s*NULL\b` | `= NULL` non funziona in SQL, restituisce sempre empty | `IS NULL` |

---

## 4. Come Usare Questo Registry

```
1. Per ogni file da analizzare:
   a. Determina LANG_ID dalla tabella §1 (estensione + manifest)
   b. Se LANG_ID = *_TS o *_PY, raffina al subtype da §1b/§1c/§1d
   c. Determina Codebase Type da §1 → Moduli attivi da §2

2. Per ogni modulo attivo, per ogni bug type:
   a. Vai alla sezione §3 corrispondente
   b. Trova la riga con il tuo LANG_ID
   c. Applica quel pattern grep — non altri
   d. Applica le regole di validazione del modulo M1-M5 (condizioni + falsificatori)

3. Se il LANG_ID non è in una sezione:
   → Il bug type non è applicabile a questo linguaggio per questo pattern
   → Scrivi [N/A] nel report di estrazione
   → NON inventare un pattern

4. Per aggiungere un nuovo linguaggio:
   → Aggiungi la riga in §1
   → Aggiungi la riga in ogni sezione di §3 con il pattern grep
   → Non toccare M1-M5
```
