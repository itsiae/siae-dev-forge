# Framework Detection Matrix — nr-test-flows

Questo documento definisce come rilevare il framework di un repository frontend e quali file
raccogliere per il mapping dei flussi navigazionali.

---

## Priorità di Rilevamento

Il framework viene determinato seguendo questo ordine. Il primo match vince.
In caso di mix, applica la regola: **Ionic > Nuxt > framework base**.

```
L1 → File di detection marker (CONFIRMED — presenza file inequivocabile)
L2 → package.json / pubspec.yaml deps (CONFIRMED — dipendenza dichiarata)
L3 → Directory structure (INFERRED — convenzione di naming)
```

---

## Matrice Framework

### Flutter

| Livello | Segnale | File | Confidence |
|---------|---------|------|-----------|
| L1 | `pubspec.yaml` nella root | `pubspec.yaml` | CONFIRMED |
| L2 | dipendenza `flutter:` in pubspec | `pubspec.yaml` | CONFIRMED |
| L3 | directory `lib/` con `main.dart` | `lib/main.dart` | INFERRED |

**File da harvest per routing:**
```
lib/main.dart                          → entry point, MaterialApp/GoRouter
lib/routes/app_router.dart             → GoRouter config (se presente)
lib/router.dart                        → alternative routing file
lib/core/router/                       → router directory
lib/**/*router*.dart                   → qualsiasi file router
lib/**/*routes*.dart                   → qualsiasi file routes
lib/screens/                           → directory screens (naming convention)
lib/pages/                             → directory pages (alternative naming)
lib/features/*/presentation/screens/  → feature-first architecture
```

**File da harvest per auth/guard:**
```
lib/**/*guard*.dart
lib/**/*auth*.dart
lib/**/*middleware*.dart
```

---

### Vue.js 3 (senza Nuxt)

| Livello | Segnale | File | Confidence |
|---------|---------|------|-----------|
| L1 | `vite.config.ts` con plugin `@vitejs/plugin-vue` | `vite.config.ts` | CONFIRMED |
| L2 | `"vue": "^3.*"` in package.json | `package.json` | CONFIRMED |
| L2 | `"vue-router"` in package.json | `package.json` | CONFIRMED |
| L3 | directory `src/views/` o `src/pages/` | — | INFERRED |

**File da harvest per routing:**
```
src/router/index.ts                    → vue-router config principale
src/router/routes.ts                   → route definitions
src/router/*.ts                        → tutti i file router
src/views/                             → directory views (ogni .vue = potenziale sezione)
src/pages/                             → alternative naming
src/layouts/                           → layout components (definiscono struttura navigazionale)
```

**File da harvest per auth/guard:**
```
src/router/guards.ts
src/router/index.ts                    → beforeEach hooks
src/store/auth.ts                      → Pinia auth store
src/composables/useAuth.ts
src/**/*guard*.ts
src/**/*auth*.ts
```

---

### Nuxt 3

| Livello | Segnale | File | Confidence |
|---------|---------|------|-----------|
| L1 | `nuxt.config.ts` nella root | `nuxt.config.ts` | CONFIRMED |
| L2 | `"nuxt"` in package.json | `package.json` | CONFIRMED |
| L3 | directory `pages/` nella root | `pages/` | INFERRED |

> **Nuxt > Vue puro**: se `nuxt.config.ts` esiste, usa il profilo Nuxt (file-based routing).

**File da harvest per routing:**
```
nuxt.config.ts                         → config principale, module list
pages/                                 → file-based routing (ogni .vue = route)
pages/**/*.vue                         → tutte le pagine
layouts/                               → layout templates
middleware/                            → navigation middleware (auth guard)
composables/useAuth.ts                 → auth composable
plugins/                               → Nuxt plugins
```

**File da harvest per auth/guard:**
```
middleware/auth.ts
middleware/*.ts                        → tutti i middleware
server/middleware/                     → server-side middleware
```

---

### Angular

| Livello | Segnale | File | Confidence |
|---------|---------|------|-----------|
| L1 | `angular.json` nella root | `angular.json` | CONFIRMED |
| L2 | `"@angular/core"` in package.json | `package.json` | CONFIRMED |
| L3 | directory `src/app/` con `app.module.ts` | — | INFERRED |

**File da harvest per routing:**
```
src/app/app-routing.module.ts          → routing principale
src/app/app.routes.ts                  → standalone routes (Angular 17+)
src/app/**/*routing.module.ts         → feature routing modules
src/app/**/*routes.ts                  → feature routes (standalone)
src/app/**/*.module.ts                 → feature modules (contengono route declarations)
```

**File da harvest per auth/guard:**
```
src/app/**/*.guard.ts                  → tutti i guard (CanActivate, CanLoad)
src/app/core/guards/                   → guards directory
src/app/core/interceptors/             → HTTP interceptors (auth token)
src/app/**/*auth*.service.ts           → auth service
```

---

### React

| Livello | Segnale | File | Confidence |
|---------|---------|------|-----------|
| L2 | `"react"` in package.json | `package.json` | CONFIRMED |
| L2 | `"react-router-dom"` in package.json | `package.json` | CONFIRMED |
| L3 | directory `src/pages/` o `src/views/` | — | INFERRED |

**File da harvest per routing:**
```
src/App.tsx                            → root component con Router
src/routes/                            → routes directory
src/router/                            → alternative naming
src/pages/                             → page components
src/views/                             → alternative naming
src/**/*Router*.tsx                    → router components
src/**/*routes*.ts                     → route definitions
```

**File da harvest per auth/guard:**
```
src/components/ProtectedRoute.tsx      → protected route component
src/contexts/AuthContext.tsx           → auth context
src/hooks/useAuth.ts                   → auth hook
src/**/*guard*.tsx
src/**/*protected*.tsx
```

---

### Ionic + Angular

| Livello | Segnale | File | Confidence |
|---------|---------|------|-----------|
| L1 | `ionic.config.json` nella root | `ionic.config.json` | CONFIRMED |
| L2 | `"@ionic/angular"` in package.json | `package.json` | CONFIRMED |

> **Ionic wins**: se `ionic.config.json` esiste, usa il profilo Ionic + Angular (IonTabs, IonNav, modal navigation).

**File da harvest per routing:**
```
src/app/app-routing.module.ts          → routing principale (lazy loading tabs)
src/app/tabs/tabs-routing.module.ts    → IonTabs routing
src/app/**/*routing.module.ts         → feature routing
src/app/app.component.html            → IonRouterOutlet declarations
```

**File da harvest per tab navigation:**
```
src/app/tabs/tabs.page.html           → IonTabBar structure
src/app/tabs/                         → tabs directory
src/app/**/tabs.page.*               → tab pages
```

**File da harvest per auth/guard:**
```
src/app/**/*.guard.ts                  → CanActivate guards
src/app/core/services/auth.service.ts
```

---

### Ionic + Vue

| Livello | Segnale | File | Confidence |
|---------|---------|------|-----------|
| L1 | `ionic.config.json` nella root | `ionic.config.json` | CONFIRMED |
| L2 | `"@ionic/vue"` in package.json | `package.json` | CONFIRMED |

**File da harvest per routing:**
```
src/router/index.ts                    → Vue Router con IonicVue
src/views/                             → views (ogni .vue = potenziale sezione)
src/App.vue                            → IonRouterOutlet
src/views/TabsPage.vue                 → IonTabs structure
```

---

### Ionic + React

| Livello | Segnale | File | Confidence |
|---------|---------|------|-----------|
| L1 | `ionic.config.json` nella root | `ionic.config.json` | CONFIRMED |
| L2 | `"@ionic/react"` in package.json | `package.json` | CONFIRMED |

**File da harvest per routing:**
```
src/App.tsx                            → IonReactRouter, IonRouterOutlet
src/pages/                             → page components
src/components/                        → reusable components con navigazione
```

---

### Drupal (CMS)

| Livello | Segnale | File | Confidence |
|---------|---------|------|-----------|
| L1 | `composer.json` con `drupal/core` | `composer.json` | CONFIRMED |
| L2 | directory `web/modules/custom/` | — | INFERRED |
| L3 | directory `web/themes/custom/` | — | INFERRED |

**File da harvest per routing:**
```
web/modules/custom/**/*.routing.yml   → custom module routes
web/modules/custom/**/*.module        → hook_menu / hook_permission
web/themes/custom/**/*.twig           → templates principali
```

---

### Strapi (Headless CMS)

| Livello | Segnale | File | Confidence |
|---------|---------|------|-----------|
| L1 | `config/server.ts` con tipo strapi | — | CONFIRMED |
| L2 | `"@strapi/strapi"` in package.json | `package.json` | CONFIRMED |

> **Nota Strapi**: è un backend CMS. I flussi navigazionali si trovano nell'admin panel e nei content-type.
> Harvest focus: content-type definitions, routes custom, middleware.

**File da harvest per routing:**
```
src/api/**/routes/                    → custom API routes
src/extensions/                       → admin panel extensions
config/routes/                        → global routes
```

---

## Regole di Precedenza Mix Framework

| Condizione | Framework Rilevato |
|-----------|-------------------|
| `ionic.config.json` + `@angular/core` | **Ionic + Angular** |
| `ionic.config.json` + `vue` | **Ionic + Vue** |
| `ionic.config.json` + `react` | **Ionic + React** |
| `nuxt.config.ts` + `vue` | **Nuxt** (non Vue puro) |
| `angular.json` + `vue` | **Analizza entrambi** (repo monorepo) |
| `pubspec.yaml` + qualsiasi | **Flutter** (non è un repo frontend JS) |

---

## File Comuni a Tutti i Framework

Questi file contengono informazioni utili indipendentemente dal framework:

```
package.json / pubspec.yaml           → version, scripts, dipendenze
README.md                             → descrizione progetto, sezioni UI documentate
.env.example / .env.local.example    → endpoint API (rivela integrazioni backend)
src/config/                           → configuration files
src/constants/                        → route name constants (es. ROUTES.HOME)
src/api/ o src/services/             → API calls (rivela sezioni con dati backend)
```

---

## Output del Rilevamento

Al termine della detection, il risultato deve essere riportato in questo formato:

```
Framework: {nome} [{versione se disponibile}]
Confidence: CONFIRMED | INFERRED
Evidenza L1: {file:riga oppure "N/A"}
Evidenza L2: {package.json:dipendenza oppure "N/A"}
File router identificati: {lista}
File guard identificati: {lista oppure "nessuno"}
```
