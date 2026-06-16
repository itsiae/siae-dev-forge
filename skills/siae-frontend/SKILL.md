---
name: siae-frontend
description: >
  Use when writing Vue.js/Angular/React components, Vitest tests, S3+CloudFront
  deploys, or frontend integrations (Pinia, Vue Router, Firebase). Guida la
  scrittura di componenti frontend, test e deploy.
  Trigger: componente Vue.js, Vitest, test frontend, deploy S3 CloudFront,
  Firebase, Pinia, Vue Router, responsive design, drag drop, upload file.
---

# SIAE Frontend

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  SIAE Frontend Patterns             ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 4. Implementation

---

> 📊 **Dai repo itsiae:** Il 45% dei bug frontend reportati in collaudo era riproducibile solo con test E2E — unit test insufficienti.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## Panoramica

Pattern frontend SIAE per sviluppo, testing, deploy e brand. **Vue.js 3 e' lo stack standard SIAE** per i nuovi progetti. Angular e React sono supportati dove gia' adottati.

Le sezioni di **deploy**, **Firebase** e **brand** si applicano a tutti i framework. Le sezioni di **stack** e **testing** variano per framework.

**Trigger**: componenti frontend (Vue/Angular/React), test frontend, deploy S3+CloudFront, Firebase config, GA error tracking.

---

## 1. Stack Tecnologico

### Vue.js 3 — Stack standard SIAE

| Tecnologia    | Ruolo                    | Versione    |
|---------------|--------------------------|-------------|
| Vue.js 3      | Framework UI             | 3.x         |
| TypeScript    | Type safety              | 5.x         |
| Pinia         | State management         | 2.x         |
| PrimeVue      | UI component library     | 4.x         |
| Vite          | Build tool               | 5.x         |
| vitest        | Testing framework        | 1.x         |

Struttura `src/`: `assets/styles/` (CSS variables), `components/` (common, layout), `composables/` (use*), `router/`, `stores/` (Pinia), `views/`, `services/` (api.ts, firebase.ts, analytics.ts), `types/`

### Angular — Stack supportato

| Tecnologia               | Ruolo                    | Versione    |
|--------------------------|--------------------------|-------------|
| Angular                  | Framework UI             | 17+         |
| TypeScript               | Type safety              | 5.x         |
| RxJS                     | State/async management   | 7.x         |
| Angular Material / CDK   | UI component library     | 17+         |
| Vite (via @analogjs/vite-plugin-angular) | Build tool | —  |
| vitest                   | Testing framework        | 1.x         |

Struttura `src/app/`: `components/`, `services/`, `models/`, `guards/`, `pipes/`

### React — Stack supportato

| Tecnologia               | Ruolo                    | Versione    |
|--------------------------|--------------------------|-------------|
| React                    | Framework UI             | 18+         |
| TypeScript               | Type safety              | 5.x         |
| Zustand / Redux Toolkit  | State management         | —           |
| Vite                     | Build tool               | 5.x         |
| vitest                   | Testing framework        | 1.x         |

Struttura `src/`: `components/`, `hooks/`, `services/`, `store/`, `types/`

---

## 2. Deploy (S3 + CloudFront)

🔴 CRITICO — Mostra pre-flight card prima di eseguire

Costruisci la card come MARKDOWN TABLE direttamente nella risposta testuale.

| 🔴 CRITICO (Deploy S3 + CloudFront) — 🔨 DevForge · siae-frontend |
|:---|
| **⚠️ OPERAZIONE REMOTA — WRITE/UPDATE/DELETE SU S3 + CloudFront** |
| 📋 Risorsa: `{BUCKET_NAME}` · 🌍 Ambiente: `{AMBIENTE}` |
| **▼ Azioni** |
| 1. `aws s3 sync dist/ s3://{BUCKET_NAME}` — sovrascrive tutti gli asset nel bucket |
| 2. `aws cloudfront create-invalidation --distribution-id {DISTRIBUTION_ID}` — invalida la cache CloudFront |
| 💡 Perché: Il deploy sovrascrive gli asset in produzione e invalida la cache CloudFront. L'operazione è irreversibile senza un re-deploy. |
| 🚫 Se NO: STOP — nessun sync S3 né invalidazione CloudFront eseguiti |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, esegui:

`vite build` -> `dist/` -> S3 bucket (no static hosting, access via CloudFront OAI/OAC). `index.html` no-cache, assets con hash per cache busting.

Pipeline: `git push tag rc-*` --> GitHub Actions --> vite build --> S3 sync --> CloudFront invalidation

---

## 3. Testing

**Runner comune: vitest.** La library DOM cambia per framework. Coverage minima **70%** per tutti gli stack (CI enforcement). Testa comportamento utente, non implementazione interna.

`vitest.config.ts` (comune): environment `jsdom`, coverage provider `v8`, thresholds 70% (statements, branches, functions, lines).

### Vue.js

Stack: `vitest` + `@testing-library/vue` + `@vue/test-utils`
File test: `{Component}.spec.ts`, affiancato al componente.

```typescript
import { render, screen, fireEvent } from '@testing-library/vue'
import { describe, it, expect } from 'vitest'
import MyComponent from './MyComponent.vue'

describe('MyComponent', () => {
  it('mostra il titolo', () => {
    render(MyComponent, { props: { title: 'Test' } })
    expect(screen.getByText('Test')).toBeTruthy()
  })
  it('emette evento click', async () => {
    const { emitted } = render(MyComponent)
    await fireEvent.click(screen.getByRole('button'))
    expect(emitted()).toHaveProperty('click')
  })
})
```

### Angular

Stack: `vitest` + `@testing-library/angular`
File test: `{component}.spec.ts`, affiancato al componente.

```typescript
import { render, screen, fireEvent } from '@testing-library/angular'
import { describe, it, expect } from 'vitest'
import { MyComponent } from './my.component'

describe('MyComponent', () => {
  it('mostra il titolo', async () => {
    await render(MyComponent, { componentProperties: { title: 'Test' } })
    expect(screen.getByText('Test')).toBeTruthy()
  })
})
```

### React

Stack: `vitest` + `@testing-library/react`
File test: `{Component}.spec.tsx` o `{Component}.test.tsx`, affiancato al componente.

```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import MyComponent from './MyComponent'

describe('MyComponent', () => {
  it('mostra il titolo', () => {
    render(<MyComponent title="Test" />)
    expect(screen.getByText('Test')).toBeTruthy()
  })
  it('chiama onClick al click', async () => {
    const onClick = vi.fn()
    render(<MyComponent onClick={onClick} />)
    await fireEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalled()
  })
})
```

---

## 4. Configurazioni Esterne

### Firebase Remote Config

Feature flags e app settings senza deploy. Config da env variables (`VITE_FIREBASE_*`), MAI hardcoded.

```typescript
// services/firebase.ts
import { initializeApp } from 'firebase/app'
import { getRemoteConfig, fetchAndActivate, getValue } from 'firebase/remote-config'

const app = initializeApp({
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
})
const remoteConfig = getRemoteConfig(app)

export async function getFeatureFlag(key: string): Promise<boolean> {
  await fetchAndActivate(remoteConfig)
  return getValue(remoteConfig, key).asBoolean()
}
```

Firebase Analytics: `getAnalytics(app)` + `logEvent()` per tracking eventi.

#### Aggiornamento parametri Remote Config (write/update/delete)

🔴 CRITICO — Mostra pre-flight card prima di eseguire

Per qualsiasi operazione di scrittura, aggiornamento o eliminazione di parametri Firebase Remote Config (via Firebase Console, Admin SDK o REST API), mostra la card seguente prima di procedere.

| 🔴 CRITICO (Firebase Remote Config Update) — 🔨 DevForge · siae-frontend |
|:---|
| **⚠️ OPERAZIONE REMOTA — WRITE/UPDATE/DELETE SU Firebase Remote Config** |
| 📋 Risorsa: `{NOME_PARAMETRO}` · 🌍 Ambiente: `{AMBIENTE}` |
| **▼ Azioni** |
| 1. Aggiorna/crea/elimina il parametro `{NOME_PARAMETRO}` su Firebase Remote Config |
| 2. Pubblica la nuova versione della configurazione (publish) |
| 💡 Perché: Le modifiche alla Remote Config hanno effetto immediato su tutti i client alla prossima fetch. Valori errati possono disabilitare feature flags o alterare comportamenti in produzione. |
| 🚫 Se NO: STOP — nessuna modifica alla Remote Config eseguita |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, esegui:

---

## 5. Error Tracking con Google Analytics

Funzione centralizzata `trackError(category, detail)` con `gtag('event', 'error', ...)`:

| Tipo         | Condizione                          | Category    | Label      |
|--------------|-------------------------------------|-------------|------------|
| Server       | HTTP 5xx                            | `'Server'`  | statusCode |
| Client       | HTTP 4xx                            | `'Client'`  | statusCode |
| Network      | timeout / DNS / connection failure  | `'Network'` | errorType  |

```typescript
type ErrorCategory = 'Server' | 'Client' | 'Network'
export function trackError(category: ErrorCategory, detail: string): void {
  gtag('event', 'error', { event_category: category, event_label: detail })
}
```

---

## 6. SIAE Brand

### Palette colori

| Ruolo       | Colore   | Uso                                    |
|-------------|----------|----------------------------------------|
| Primary     | `#000000`| Testi principali, header               |
| Secondary   | `#2F3546`| Sidebar, elementi secondari            |
| Accent      | `#00B4F9`| CTA, link, elementi interattivi        |
| Background  | `#F6F6F6`| Sfondo pagine, card                    |

### CSS Variables e Font

```css
:root {
  --siae-primary: #000000;  --siae-secondary: #2F3546;
  --siae-accent: #00B4F9;   --siae-background: #F6F6F6;
  --siae-font-family: 'Roboto', sans-serif;
}
```

Font: **Roboto** (Google Fonts), fallback sans-serif.

---

## 7. Vincoli Inviolabili

Queste regole sono **OBBLIGATORIE**. Violarne una significa bloccare la review.

| #  | Vincolo                                    | Motivazione                              |
|----|--------------------------------------------|------------------------------------------|
| V1 | No CSS inline                              | Usa CSS variables o Tailwind utilities   |
| V2 | Responsive mobile-first                    | Breakpoint min-width, mobile come base   |
| V3 | No `any` in TypeScript                     | Type safety e' il motivo di usare TS     |
| V4 | Accessibilita' WCAG 2.1 AA                | `aria-*` attributes, contrasto colori    |
| V5 | Coverage test >= 70%                       | Enforcement in CI, no merge sotto soglia |
| V6 | No secret in codice frontend               | Usa env variables (`VITE_*`)             |
| V7 | Componenti tipizzati con `defineComponent` | Props, emits, slots tipizzati            |
| V8 | No dipendenze non approvate                | Review team lead per nuovi package       |

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| File modificati per singolo step | 5 | Se devi toccare piu' file, decomponi in sub-task. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue, non lista esaustiva. |

---

## REQUIRED SUB-SKILL: siae-tdd

Implementa ogni componente frontend seguendo `siae-tdd` (test Vitest fallente prima del codice).

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Questo componente e' solo per questa pagina" | I componenti 'locali' vengono riusati. Costruiscili per il riuso. |
| "I test Vitest rallentano il build" | I bug UI in produzione rallentano i developer per giorni. |
| "Il CSS lo sistemo dopo" | Il CSS non sistemato diventa tech debt che blocca il restyling. |
| "Non serve il brand SIAE per questo prototipo" | I prototipi diventano produzione. Il brand si aggiunge male in corsa. |
| "Firebase config la metto nel codice" | Le config hardcoded vanno in git. Le credenziali non devono andare in git. |
| "L'error tracking lo aggiungo in produzione" | Senza error tracking non sai cosa sta rompendosi in produzione. |
| "Vue 2 funziona ancora, non migro" | Vue 2 e' EOL. Il debito di migrazione cresce ogni giorno. |

---

## Classificazione Rischio Operazioni

| Operazione                                | Rischio    |
|-------------------------------------------|------------|
| Lettura/analisi componenti frontend       | 🟢 Sicuro  |
| Creazione/modifica componenti             | 🟡 Medio   |
| Modifica CSS variables / brand      | 🟡 Medio   |
| Esecuzione test (`vitest`)          | 🟡 Medio   |
| Modifica Firebase config            | 🔴 Alto    |
| Modifica analytics/error tracking   | 🔴 Alto    |
| Deploy S3 + CloudFront invalidation | 🚨 Critico |
| Modifica variabili environment      | 🔴 Alto    |
