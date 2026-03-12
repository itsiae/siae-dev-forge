# Evidence Patterns — nr-test-flows

Dove cercare route, navigazione e guard per ogni framework frontend.
Ogni pattern include il tipo di evidenza e l'esempio di codice da cercare.

---

## I 5 Pattern Meccanici di Estrazione Flussi NRT

Un flusso NRT = uno di questi 5 pattern, cercabili con grep/Grep tool.
NON esiste un flusso che non corrisponda ad almeno uno di questi pattern.
Se un component non ha nessun pattern → LOW/SKIP, non genera flusso NRT.

| Pattern | Grep | Produce |
|---------|------|---------|
| **P1 — Mutating API call** | `axios\.post\|axios\.put\|axios\.delete\|axios\.patch\|fetch.*POST\|fetch.*PUT` | 1 flusso per call + component che la ospita |
| **P2 — Router navigation in handler** | `router\.push\|navigate\(\|\$router\.push\|this\.router\.navigate` | 1 flusso per navigazione programmatica in @click/@submit |
| **P3 — Store action con state transition** | (in store file) funzioni che modificano stato nominato | 1 flusso per transizione nominata |
| **P4 — Form submit handler** | `@submit\|handleSubmit\|onSubmit\|v-on:submit` | 1 flusso per submit handler |
| **P5 — Form discriminator** | `v-if="\|*ngIf="\|{condition &&}` su variabile di form state | 1 variant per branch distinto |

### Regole P5 — Distinguere form discriminator da guard

```
INCLUDI (form discriminator → variants):
  tipologia, tipo, categoria, step, mode, fase, stato_form, tipoEvento

ESCLUDI (guard/auth → non crea variants, già coperto da TIER 3):
  isAuthenticated, isAdmin, isLoading, isError, showError, hasPermission
```

### Regole Priority — Code-Derivable (Step 3 di nr-test-flows)

```
CRITICAL se almeno uno di:
  → component ha canActivate/redirect guard E almeno un P1 (API mutante)
    rule: "mutating-api+canActivate-guard"
  → è la prima route dopo redirect post-login (entry point autenticato)
    rule: "entry-point-post-login"
  → API endpoint contiene: /auth, /payment, /submit, /sign, /confirm, /delete
    rule: "endpoint-path-contains-{keyword}"

HIGH se almeno uno di:
  → P1 (API mutante) senza pattern CRITICAL
    rule: "mutating-api"
  → P5 (form discriminator) con branches che cambiano payload API
    rule: "form-discriminator-changes-payload"
  → rendering condizionale su ruolo utente
    rule: "role-based-rendering"

MEDIUM se:
  → solo P4 (submit) senza API call
    rule: "submit-no-api"
  → solo P2 (router navigation) senza API
    rule: "nav-only"

LOW/SKIP se:
  → nessuno dei 5 pattern → component presentazionale, non genera flusso NRT
    Non aggiungere alla flow map.
```

---

## ANTI-HALLUCINATION PROTOCOL

```
MAI MAPPARE UNA SEZIONE O UN FLUSSO SENZA CITARE IL FILE SORGENTE CHE LO PROVA.
SE NON HAI LETTO IL FILE, LA SEZIONE NON ESISTE.
```

### Tag di Confidence

```
[CONFIRMED]    codice sorgente letto direttamente (router file, component, guard)
[INFERRED]     naming convention o directory structure — DEVI citare file:riga
[UNVERIFIED]   nessuna evidenza diretta — va nel Gap Report, mai rimosso
```

---

## Flutter

### Dove cercare le route

**GoRouter (moderno, pattern preferito):**
```dart
// Cerca in: lib/routes/app_router.dart, lib/core/router/, lib/router.dart
// Pattern da cercare:
GoRouter(routes: [...])
GoRoute(path: '/login', builder: ...)
ShellRoute(routes: [...])                    // sezioni con shell navigation
```

**Navigator 2.0 (MaterialApp.router):**
```dart
// Cerca in: lib/main.dart
MaterialApp.router(
  routerConfig: _router,
  ...
)
```

**Navigator 1.0 (push/pop classico):**
```dart
// Cerca in: qualsiasi file .dart
Navigator.pushNamed(context, '/home')
Navigator.push(context, MaterialPageRoute(builder: (_) => HomeScreen()))
```

**Named routes dichiarative:**
```dart
// Cerca in: lib/main.dart
MaterialApp(
  routes: {
    '/login': (ctx) => LoginScreen(),
    '/home': (ctx) => HomeScreen(),
  }
)
```

### Dove cercare le sezioni (screens)

```
lib/screens/           → naming convention più comune
lib/pages/             → alternative naming
lib/features/*/presentation/screens/   → feature-first architecture
lib/ui/screens/        → UI layer separation
```

### Dove cercare i guard (navigation middleware)

```dart
// GoRouter redirect (guard equivalente)
GoRouter(
  redirect: (context, state) {
    final isLoggedIn = ...;
    if (!isLoggedIn && state.location != '/login') return '/login';
    return null;
  }
)

// RouteObserver per analytics/guard
navigatorObservers: [routeObserver]

// Cerca file con pattern:
lib/**/*guard*.dart
lib/**/*middleware*.dart
lib/**/*redirect*.dart
```

### Dove cercare le tab navigation

```dart
// BottomNavigationBar / NavigationBar
BottomNavigationBar(items: [...])
NavigationBar(destinations: [...])

// CupertinoTabBar (iOS style)
CupertinoTabScaffold(tabBar: ...)

// Cerca in:
lib/screens/main_screen.dart
lib/widgets/bottom_nav.dart
lib/app.dart
```

### L5 Scan — Flutter (Step 2d obbligatorio)

```bash
# P5 — Form discriminators (conditional widget rendering)
Grep pattern: if\s*\([a-zA-Z][a-zA-Z0-9_]*\s*[=!]==.*\)\s*\n?\s*[A-Z]
# cerca blocchi if/switch che rendono widget diversi basati su form state

# P3 — Store states (Riverpod/Bloc/Provider)
Grep pattern: StateNotifier<|Cubit<|BlocBuilder|ChangeNotifier
# poi leggi i metodi che cambiano stato

# Computed rendering su ruolo
Grep pattern: userRole|hasPermission|isAdmin|canEdit
```

---

## Vue.js 3

### Dove cercare le route

**vue-router config:**
```typescript
// src/router/index.ts — configurazione principale
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { requiresAuth: false }        // meta fields per guard
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true }
  }
]
```

**Nested routes (sezioni con sub-navigazione):**
```typescript
{
  path: '/admin',
  component: AdminLayout,
  children: [
    { path: 'users', component: UserList },
    { path: 'settings', component: Settings }
  ]
}
```

### Dove cercare le sezioni (views)

```
src/views/              → directory views (ogni .vue tendenzialmente = una sezione)
src/pages/              → alternative naming
src/layouts/            → layout components (definiscono struttura navigazionale)
```

### Dove cercare i guard

```typescript
// src/router/index.ts — navigation guards globali
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !isAuthenticated()) {
    next('/login')
  } else {
    next()
  }
})

// src/router/guards.ts — guard separati
export function authGuard(to, from, next) { ... }

// Pinia store (src/stores/auth.ts)
const authStore = useAuthStore()
if (!authStore.isAuthenticated) router.push('/login')
```

### Dove cercare le API calls (per identificare sezioni con dati backend)

```typescript
// src/api/ o src/services/
import axios from 'axios'
export const loginUser = (credentials) => axios.post('/api/auth/login', credentials)

// composables
// src/composables/useApi.ts
const { data } = useFetch('/api/dashboard')
```

### L5 Scan — Vue.js 3 (Step 2d obbligatorio)

```bash
# P5 — Form discriminators (crea variants)
# Cerca v-if su variabili di form state (NON su isAuthenticated/isAdmin/isLoading)
Grep pattern: v-if="[a-zA-Z][a-zA-Z0-9_]*\s*[=!]=
# poi filtra manualmente: escludi isAuthenticated|isAdmin|isLoading|isError|show|has
# Includi: tipologia, tipo, categoria, step, mode, fase

# P3 — Store states
# Cerca in src/stores/: ref() o reactive() con stati nominati
Grep pattern: const [a-zA-Z]+ = ref\(|states:\s*\[
# poi leggi le actions che li modificano

# Computed rendering su ruolo
Grep pattern: v-if.*[Rr]ole|v-if.*[Aa]dmin|:class.*[Rr]ole|computed.*[Pp]ermission
```

---

## Nuxt 3

### Dove cercare le route

**File-based routing (automatico):**
```
pages/                          → ogni file .vue = route automatica
pages/index.vue                 → route /
pages/login.vue                 → route /login
pages/dashboard/index.vue       → route /dashboard
pages/admin/[id].vue            → route /admin/:id (dynamic)
pages/[...slug].vue             → catch-all route
```

**nuxt.config.ts — router options:**
```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  router: {
    options: { ... }
  }
})
```

### Dove cercare i middleware (guard equivalente)

```typescript
// middleware/auth.ts — route middleware
export default defineNuxtRouteMiddleware((to, from) => {
  const user = useSupabaseUser()
  if (!user.value) return navigateTo('/login')
})

// Applicazione nei page component:
definePageMeta({
  middleware: 'auth'
})
```

### Dove cercare i layout (struttura navigazionale)

```
layouts/default.vue             → layout principale con nav
layouts/auth.vue                → layout per pagine auth
layouts/admin.vue               → layout admin con sidebar
```

---

## Angular

### Dove cercare le route

**app-routing.module.ts:**
```typescript
const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [AuthGuard] },
  {
    path: 'admin',
    loadChildren: () => import('./admin/admin.module').then(m => m.AdminModule),
    canLoad: [AdminGuard]
  }
]
```

**Feature module routing (lazy loaded):**
```typescript
// src/app/admin/admin-routing.module.ts
const routes: Routes = [
  { path: '', component: AdminDashboardComponent },
  { path: 'users', component: UserListComponent },
]
```

### Dove cercare i guard

```typescript
// src/app/**/*.guard.ts
@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  canActivate(route, state): boolean | UrlTree {
    return this.authService.isLoggedIn() || this.router.createUrlTree(['/login'])
  }
}

// Functional guards (Angular 15+)
export const authGuard: CanActivateFn = (route, state) => {
  return inject(AuthService).isAuthenticated() || inject(Router).createUrlTree(['/login'])
}
```

### Dove cercare tab/nav structure (Ionic + Angular)

```html
<!-- src/app/tabs/tabs.page.html -->
<ion-tabs>
  <ion-tab-bar slot="bottom">
    <ion-tab-button tab="home">
      <ion-icon name="home"></ion-icon>
      <ion-label>Home</ion-label>
    </ion-tab-button>
    <ion-tab-button tab="profilo">
      <ion-icon name="person"></ion-icon>
      <ion-label>Profilo</ion-label>
    </ion-tab-button>
  </ion-tab-bar>
</ion-tabs>
```

### L5 Scan — Angular (Step 2d obbligatorio)

```bash
# P5 — Form discriminators
Grep pattern: \*ngIf="[a-zA-Z][a-zA-Z0-9_]*\s*[=!]==
# poi filtra: escludi isAuthenticated|isAdmin|isLoading|isError

# P3 — Store states (NgRx)
Grep pattern: createReducer\|on\(.*Action|\.pipe\(select
# oppure (servizi con BehaviorSubject):
Grep pattern: BehaviorSubject<|new BehaviorSubject

# Computed rendering su ruolo
Grep pattern: \*ngIf.*role|hasRole|canAccess|isAdmin
```

---

## React

### Dove cercare le route

**React Router v6:**
```tsx
// src/App.tsx o src/routes/
<Routes>
  <Route path="/" element={<Home />} />
  <Route path="/login" element={<Login />} />
  <Route element={<ProtectedRoute />}>       {/* layout route per auth */}
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/profile" element={<Profile />} />
  </Route>
</Routes>
```

**Route definitions separate:**
```typescript
// src/routes/index.tsx
export const routes = createBrowserRouter([
  { path: '/', element: <Home /> },
  { path: '/dashboard', element: <Dashboard />, loader: dashboardLoader },
])
```

### Dove cercare i guard (ProtectedRoute)

```tsx
// src/components/ProtectedRoute.tsx
const ProtectedRoute = () => {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />
}
```

### Dove cercare le API calls

```typescript
// src/services/ o src/api/
export const api = axios.create({ baseURL: process.env.REACT_APP_API_URL })

// React Query / SWR
const { data } = useQuery('dashboard', () => fetchDashboard())
const { data } = useSWR('/api/stats', fetcher)
```

### L5 Scan — React (Step 2d obbligatorio)

```bash
# P5 — Form discriminators
Grep pattern: \{[a-zA-Z][a-zA-Z0-9_]*\s*===.*&&|condition\s*&&
# poi filtra: escludi isAuthenticated|isAdmin|isLoading|error

# P3 — Store states (Redux/Zustand)
Grep pattern: createSlice\|useSelector\|slice\.actions|set[A-Z][a-zA-Z]+\(
# Zustand:
Grep pattern: create\(\(set\)

# Computed rendering su ruolo
Grep pattern: user\.role|hasPermission|canEdit|isAdmin
```

---

## Pattern Comuni Trasversali

### Costanti di routing (rivela sezioni senza leggere il router)

```typescript
// Cerca in: src/constants/routes.ts, src/config/routes.ts, src/router/routes.ts
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  PROFILE: '/profile',
  ADMIN: '/admin',
} as const
```

### Store Pinia / Vuex / NgRx / Redux (rivela sezioni con stato gestito)

```typescript
// Cerca store con navigazione o auth
// Pinia: src/stores/
// Vuex: src/store/
// NgRx: src/app/store/
// Redux: src/redux/ o src/store/

// Pattern da cercare:
router.push(...)          // navigazione programmatica in store action
this.router.navigate(...) // Angular
navigate(...)             // React Router
```

### i18n keys (rivelano sezioni anche senza leggere il router)

```
// Cerca in: src/locales/, src/i18n/, public/locales/
// es. it.json:
{
  "nav": {
    "home": "Home",
    "dashboard": "Dashboard",
    "profile": "Profilo",
    "admin": "Amministrazione"
  }
}
```

---

## Come Usare Questo File

1. Determina il framework con `framework-detection-matrix.md`
2. Vai alla sezione corrispondente in questo file
3. Usa i pattern per identificare dove cercare route, sezioni e guard
4. Ogni elemento trovato → cita `file:riga` nel flow map YAML
5. Ogni elemento non trovato → aggiungi al Gap Report con `confidence: UNVERIFIED`
