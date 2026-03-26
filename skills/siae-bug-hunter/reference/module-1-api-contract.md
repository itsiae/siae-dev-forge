# M1 — API Contract Mismatch Detector

## Regola Fondamentale

Un disallineamento è bug confermato SOLO se il campo/tipo mancante è usato
nel FE senza optional chain (`?.`) e senza fallback esplicito.

---

## 1. ESTRAZIONE CHIAMATE API — Frontend

| Stack | Pattern Grep | Cosa Estrarre |
|---|---|---|
| TypeScript/JS | `fetch\(|axios\.(get\|post\|put\|patch\|delete)` | URL, metodo, body type |
| Angular | `HttpClient\.(get\|post\|put\|delete)` | generic type, header |
| Vue (composables) | `useQuery\|useMutation\|useFetch` | chiave operazione, variabili |
| Flutter/Dart | `http\.get\|http\.post\|Dio\(\)` | endpoint string |
| React Query | `useQuery\(\[` | query key, fetch function |

Per ogni chiamata estrarre: `[file:riga] → [METODO] [path] → [body_type] → [response_type_usato]`

---

## 2. ESTRAZIONE ENDPOINT — Backend

| Stack | Pattern Grep | Cosa Estrarre |
|---|---|---|
| Spring Boot | `@(Rest)?Controller\|@(Get\|Post\|Put\|Delete\|Patch)Mapping` | path, metodo, @RequestBody class |
| Express | `(app\|router)\.(get\|post\|put\|patch\|delete)\(` | path string, handler |
| FastAPI | `@(app\|router)\.(get\|post\|put\|patch\|delete)` | path, request model, response model |
| Gin (Go) | `router\.(GET\|POST\|PUT\|DELETE)` | path, handler |
| ASP.NET Core | `\[Http(Get\|Post\|Put\|Delete)\]\|Map(Get\|Post)` | route template, return type |

Per ogni endpoint estrarre: `[file:riga] → [METODO] [path] → [request_type] → [response_type]`

---

## 3. ESTRAZIONE BFF

**Definizione BFF (binaria — entrambe le condizioni devono essere presenti):**
- **(a)** Il file contiene almeno un import/call verso un servizio BE interno — pattern: URL hostname interno, client generato (`UserServiceClient`, `axios.create({baseURL: process.env.INTERNAL_API}`), `@FeignClient`, `WebClient` Spring, `HttpClient` Angular verso BE)
- **(b)** Il file espone almeno un endpoint verso l'esterno (`@Controller`, `router.get(`, `app.post(`, route Express/Nest)

Se **solo (a)** → classificare come BE aggregator (non BFF). Se **solo (b)** → classificare come FE-facing BE.
Se **nessuna** → non è un layer BFF.

Applicare le regole BFF-1, BFF-2, BFF-3 di M3 **solo ai file classificati come BFF** con entrambe le condizioni.

**Pattern BFF specifici da cercare:**
- GraphQL gateway: `@apollo/gateway`, `apollo-subgraph`, `@Subgraph`
- Mapping/transform: riceve `X` dal FE, trasforma in `Y` per BE (cerca `mapper.`, `transform(`, `toDto(`)

Estrarre: `[BFF_endpoint] → [BE_calls] → [transform_rules]`

---

## 4. REGOLE DI MATCHING (binario, no ambiguità)

### 4.1 Path Match
- FE path == BE path (dopo template expansion) → MATCH
- Endpoint richiamato da FE non esiste in BE → **MISMATCH → candidato bug**

### 4.2 Metodo HTTP Match
- FE `GET` chiama BE `POST` → **MISMATCH → candidato bug**

### 4.3 Request Body Match
- Campo presente nel body FE, assente nel @RequestBody BE → **MISMATCH**
  - Ma SOLO bug se: FE lo invia sempre (no guard) E BE non ha default
- Campo in BE non usato in FE → OK

### 4.4 Response Body Match
- Campo letto nel FE dal response (es. `response.user.name`), non presente in response BE → **MISMATCH**
  - Ma SOLO bug se: FE accede senza `?.` E senza fallback
- Campo in response BE non usato in FE → OK

### 4.5 Tipo Dato Match
| FE aspetta | BE ritorna | Guard presente | Esito |
|---|---|---|---|
| `string` | `null` | no `?.` o `?? default` | **BUG** |
| `boolean` | `"true"` (string) | no conversione esplicita | **BUG** — sempre truthy |
| `number` | `"123"` (string) | no `Number(x)` | **BUG** — aritmetica → NaN |
| `Date` | Unix timestamp (ms) | `new Date(ts)` | OK |
| `List<T>` | `T \| null` | no guard | **BUG** |

### 4.6 HTTP Status Code Match
- FE ha `if (response.status === 200)` ma BE ritorna 201 → **BUG**
- BE ritorna 401, FE non ha catch per 401 e non redirige → **BUG**
- FE usa `if (response.ok)` (2xx generico) → OK anche se status varia

---

## 5. REGOLE DI FALSIFICAZIONE

Un mismatch NON è un bug se:
- FE usa optional chain: `response?.data?.user?.name` → falsificato
- FE ha null-coalescing: `response.data?.user?.name ?? "N/A"` → falsificato
- FE ha if-guard: `if (response.user) { ... }` → falsificato
- BE ha `@Nullable` + FE gestisce null → falsificato
- BFF normalizza il campo prima di passarlo al FE → falsificato (analizza BFF)

---

## 6. TEMPLATE OUTPUT CANDIDATO

```
[M1-API] file_fe:riga | file_be:riga
  Tipo:     [Missing Field | Type Mismatch | HTTP Method | Status Code | Null Handling]
  FE:       response.data.user.name (riga 42, nessun null-check)
  BE:       UserDto.name può essere null (@Nullable o Optional)
  Path:     GET /api/users/{id}
  Trigger:  Utente accede a profilo → BE ritorna name=null → FE crash
```

---

## 7. LIMITI DEL MODULO

NON rileva:
- Endpoint costruiti a runtime (`app.post(\`/api/${entity}\`)`) → skip con nota
- GraphQL fragments/aliases complessi → match solo su operationName
- Custom serializer BE che trasforma il tipo → analizza il serializer se presente
- Business logic mismatch (calcoli diversi FE/BE) → fuori scope
- Performance (payload size) → fuori scope
