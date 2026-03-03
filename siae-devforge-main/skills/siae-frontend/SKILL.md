---
name: siae-frontend
description: >
  Pattern frontend SIAE: Vue.js 3, vitest, Firebase, Google Analytics.
  Trigger: sviluppo componenti Vue, test frontend, deploy S3+CloudFront,
  configurazione Firebase, error tracking GA.
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
║              🔨  DevForge  ·  SIAE Frontend Patterns              ║
╚══════════════════════════════════════════════════════════════════╝
```

## Panoramica

Pattern frontend SIAE: Vue.js 3, testing, deploy, Firebase, error tracking e brand identity.

**Trigger**: componenti Vue, test frontend, deploy S3+CloudFront, Firebase config, GA error tracking.

---

## 1. Stack Tecnologico

| Tecnologia    | Ruolo                    | Versione    |
|---------------|--------------------------|-------------|
| Vue.js 3      | Framework UI             | 3.x         |
| TypeScript    | Type safety              | 5.x         |
| Pinia         | State management         | 2.x         |
| PrimeVue      | UI component library     | 4.x         |
| Vite          | Build tool               | 5.x         |
| vitest        | Testing framework        | 1.x         |

### Struttura progetto

`src/`: `assets/styles/` (CSS variables), `components/` (common, layout), `composables/` (use*), `router/`, `stores/` (Pinia), `views/`, `services/` (api.ts, firebase.ts, analytics.ts), `types/`

---

## 2. Deploy (S3 + CloudFront)

`vite build` -> `dist/` -> S3 bucket (no static hosting, access via CloudFront OAI/OAC). `index.html` no-cache, assets con hash per cache busting.

Pipeline: `git push tag rc-*` --> GitHub Actions --> vite build --> S3 sync --> CloudFront invalidation

---

## 3. Testing

Stack: vitest (runner) + @testing-library/vue (DOM) + @vue/test-utils (mounting).

File test: `{Component}.spec.ts`. **Coverage minima: 70%** (CI enforcement). Testa comportamento utente, non implementazione.

### Esempio test

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

### Configurazione vitest

`vitest.config.ts`: environment `jsdom`, coverage provider `v8`, thresholds 70% (statements, branches, functions, lines).

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

## Classificazione Rischio Operazioni

| Operazione                          | Rischio    |
|-------------------------------------|------------|
| Lettura/analisi componenti Vue      | 🟢 Sicuro  |
| Creazione/modifica componenti       | 🟡 Medio   |
| Modifica CSS variables / brand      | 🟡 Medio   |
| Esecuzione test (`vitest`)          | 🟡 Medio   |
| Modifica Firebase config            | 🔴 Alto    |
| Modifica analytics/error tracking   | 🔴 Alto    |
| Deploy S3 + CloudFront invalidation | 🚨 Critico |
| Modifica variabili environment      | 🔴 Alto    |
