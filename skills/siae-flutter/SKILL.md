---
name: siae-flutter
description: >
  Guida lo sviluppo di app Flutter SIAE: architettura MVVM con Riverpod, persistenza
  ObjectBox, auth Amplify/Cognito, Firebase, networking Dio, code generation.
  Trigger: Flutter, Dart, Riverpod, ObjectBox, Get_it, Amplify, Cognito, app mobile,
  widget, build_runner, Dio, Crashlytics, deep link, geolocation.
---

# SIAE Flutter — DevForge

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · SIAE Flutter Patterns                ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 4. Implementation

---

> 📊 **Dai repo itsiae:** Le app mobile senza pattern MVVM rigoroso accumulano 2.5x piu' bug di stato rispetto a quelle con separazione netta ViewModel/View.
> Fonte: analisi su repository mobile itsiae.

## Panoramica

Pattern Flutter SIAE per sviluppo app mobile. Definisce lo stack standard, l'architettura
MVVM con Riverpod, la gestione della persistenza, autenticazione, networking e integrazioni native.

**Questa skill si applica a tutti i progetti Flutter SIAE.** Lo stack descritto e' lo
standard adottato a partire dal progetto TuneX e replicabile su nuove app.

---

## 1. Stack Tecnologico

| Tecnologia | Ruolo | Versione |
|------------|-------|----------|
| Flutter | Framework UI cross-platform | 3.32.x stable |
| Dart | Linguaggio | 3.x |
| Riverpod | State management (MVVM) | 2.x |
| Get_it | Service Locator / DI | 8.x |
| ObjectBox | Database NoSQL locale | 4.x |
| Flutter Secure Storage | Cifratura dati sensibili | 9.x |
| AWS Amplify (Cognito) | Autenticazione | 2.x |
| Firebase Crashlytics | Crash reporting | 4.x |
| Firebase Messaging | Push notifications | 15.x |
| Firebase Remote Config | Configurazione remota | 5.x |
| Dio | HTTP client | 5.x |
| build_runner | Code generation (DTO, entity) | 2.x |
| Barlow | Font family | — |
| flutter_svg | Grafica vettoriale SVG | 2.x |

Per dettagli su ogni componente vedi [reference/stack-details.md](reference/stack-details.md).

---

## 2. Architettura — MVVM con Riverpod

```
┌─────────────────────────────────────────────────┐
│                    View (Widget)                 │
│  - Solo UI, zero logica business                │
│  - Osserva il ViewModel via ref.watch()         │
└──────────────────────┬──────────────────────────┘
                       │ ref.watch / ref.read
┌──────────────────────▼──────────────────────────┐
│              ViewModel (Notifier)                │
│  - Logica di presentazione                      │
│  - Espone stato immutabile (state)              │
│  - Chiama Repository/Service via ref            │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│          Repository / Service                    │
│  - Accesso dati (API, DB locale)                │
│  - Registrato in Get_it                         │
│  - Iniettato nel ViewModel via Provider         │
└─────────────────────────────────────────────────┘
```

**Regole MVVM:**
- **View**: solo widget, `ref.watch()` per leggere stato, `ref.read()` per azioni
- **ViewModel**: `Notifier` o `AsyncNotifier` di Riverpod, stato immutabile con `copyWith`
- **Repository**: interfaccia + implementazione, registrato in Get_it, testabile con mock
- **Model/Entity**: classi Dart pure, generate con `build_runner` dove possibile

Struttura directory:

```
lib/
├── core/                    # Configurazione, costanti, theme, routing
│   ├── config/              # Environment, API URLs
│   ├── constants/           # Stringhe, dimensioni, durate
│   ├── router/              # GoRouter o Navigator 2.0
│   └── theme/               # ThemeData, colori, tipografia (Barlow)
├── data/                    # Layer dati
│   ├── datasources/         # Remote (API Dio) e Local (ObjectBox)
│   ├── models/              # DTO generati (build_runner)
│   └── repositories/        # Implementazioni repository
├── domain/                  # Layer dominio (puro Dart)
│   ├── entities/            # Entita' business
│   ├── repositories/        # Interfacce repository (abstract)
│   └── usecases/            # Casi d'uso (opzionale)
├── presentation/            # Layer UI
│   ├── common/              # Widget condivisi
│   ├── providers/           # Riverpod providers e ViewModels
│   └── screens/             # Schermate (una directory per feature)
│       └── feature_x/
│           ├── feature_x_screen.dart
│           ├── feature_x_viewmodel.dart
│           └── widgets/     # Widget locali della feature
├── services/                # Servizi cross-cutting
│   ├── auth_service.dart    # AWS Amplify/Cognito
│   ├── analytics_service.dart
│   ├── push_service.dart    # Firebase Messaging
│   └── connectivity_service.dart
└── di/                      # Dependency Injection setup
    └── injection.dart       # Get_it registration
```

Per pattern Riverpod dettagliati vedi [reference/riverpod-patterns.md](reference/riverpod-patterns.md).

---

## 3. Persistenza e Sicurezza Dati

### ObjectBox — Database NoSQL locale

- Usare per dati strutturati con query frequenti (cache, entita' offline)
- Annotare entita' con `@Entity()`, relazioni con `@Backlink()`
- Generare binding con `build_runner`

### Flutter Secure Storage — Dati sensibili

- **SEMPRE** per token, credenziali, dati PII
- **MAI** salvare token in ObjectBox, SharedPreferences o file plain text
- Wrappare in un `SecureStorageService` registrato in Get_it

```dart
abstract class SecureStorageService {
  Future<void> write(String key, String value);
  Future<String?> read(String key);
  Future<void> delete(String key);
  Future<void> deleteAll();
}
```

---

## 4. Autenticazione — AWS Amplify (Cognito)

- Configurare Amplify in `main.dart` prima di `runApp()`
- Gestire il ciclo auth via `AuthService` (sign in, sign up, sign out, token refresh)
- Token JWT in Flutter Secure Storage, **MAI** in memoria persistente non cifrata
- Usare `Amplify.Auth.fetchAuthSession()` per ottenere token validi prima di ogni API call

---

## 5. Networking — Dio

- Client Dio centralizzato con interceptor per:
  - **Auth**: inject token Cognito nell'header `Authorization`
  - **Retry**: retry automatico su 5xx e timeout (max 2 retry)
  - **Logging**: log request/response in debug mode
  - **Connectivity**: check connettivita' prima di ogni request
- Base URL da environment config, **MAI** hardcoded
- Timeout: connect 10s, receive 30s

---

## 6. Firebase

| Servizio | Uso | Configurazione |
|----------|-----|----------------|
| Crashlytics | Crash reporting automatico | `FlutterError.onError` + `PlatformDispatcher.onError` |
| Messaging | Push notifications | FCM token registrato su backend |
| Remote Config | Feature flags, config runtime | Fetch con cache 12h, fallback a defaults |

- Inizializzare Firebase in `main.dart` prima di Amplify
- Config da `google-services.json` (Android) e `GoogleService-Info.plist` (iOS)
- **MAI** committare file Firebase config con chiavi di produzione — usare flavor/scheme

---

## 7. Integrazioni Native

| Modulo | Package | Note |
|--------|---------|------|
| Geolocalizzazione | `geolocator` + `geocoding` | Permessi runtime, fallback graceful |
| Mappe | `google_maps_flutter` | API key da env, **MAI** hardcoded |
| Fotocamera | `camera` o `image_picker` | Permessi runtime, compressione immagini |
| Deep Links | App Links (Android) + Universal Links (iOS) | Configurazione in `AndroidManifest.xml` e `Info.plist` |

---

## 8. Code Generation (build_runner)

- Usare `build_runner` per: DTO (`json_serializable`), entita' ObjectBox, router (`go_router_builder`), Riverpod (`riverpod_generator`)
- Comando: `dart run build_runner build --delete-conflicting-outputs`
- File generati: `*.g.dart`, `*.freezed.dart` — **committarli** nel repo (no generation in CI)
- Pattern naming: `model.dart` → `model.g.dart`

---

## 9. Brand e Design

- **Font**: Barlow (Google Fonts), caricato da assets locali per performance offline
- **SVG**: `flutter_svg` per tutte le icone e illustrazioni — no PNG/JPG per icone
- **Theme**: `ThemeData` centralizzato in `core/theme/`, estendere con `ThemeExtension` per colori custom
- **Responsive**: `MediaQuery` e `LayoutBuilder`, breakpoint per tablet/phone

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura/analisi codice Flutter | 🟢 Sicuro | No |
| Creazione/modifica widget e viewmodel | 🟡 Medio | Si |
| Modifica config Amplify/Firebase | 🔴 Alto | Si |
| Modifica dependency injection (Get_it) | 🟡 Medio | Si |
| Modifica `pubspec.yaml` (dipendenze) | 🟡 Medio | Si |
| Esecuzione `build_runner` | 🟡 Medio | Si |
| Modifica `AndroidManifest.xml` / `Info.plist` | 🔴 Alto | Si |
| Build e deploy su store | 🚨 Critico | Si |

---

## Vincoli

1. **NON** usare `setState()` per logica oltre l'UI locale di un singolo widget
2. **NON** salvare token o credenziali fuori da Flutter Secure Storage
3. **NON** hardcodare URL, API key o config Firebase nel codice sorgente
4. **NON** usare `dynamic` o disabilitare type safety — Dart strong typing sempre
5. **SEMPRE** seguire il pattern MVVM: View → ViewModel (Notifier) → Repository
6. **SEMPRE** registrare i servizi in Get_it e iniettarli via Provider, mai istanziare direttamente
7. **SEMPRE** gestire permessi nativi (camera, location) con fallback graceful
8. **PRE-FLIGHT OBBLIGATORIA** per operazioni con rischio >= 🟡

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Per questa schermata basta setState" | setState scala male. Riverpod mantiene lo stato coerente tra schermate. |
| "Il token lo metto in SharedPreferences, tanto e' locale" | SharedPreferences e' plain text. I token vanno in Secure Storage, sempre. |
| "ObjectBox e' overkill, uso un file JSON" | ObjectBox ha query tipizzate e relazioni. Un file JSON diventa ingestibile. |
| "La API key di Google Maps la metto nel codice, tanto e' pubblica" | Le API key vanno in env config. Hardcoded = impossibile ruotare senza release. |
| "Il build_runner lo eseguo solo io, non serve committare i .g.dart" | Senza file generati committati, il CI non builda. Committa sempre i generati. |
| "Amplify lo configuro dopo, prima faccio funzionare l'app" | L'auth e' il primo gate. Senza auth, ogni API call e' un placeholder. |
| "Deep link li aggiungo alla fine" | I deep link richiedono config nativa. Aggiungerli dopo rompe il routing. |
| "Per ora testo manualmente, i test li scrivo dopo" | I widget test in Flutter sono veloci. Scriverli dopo significa non scriverli mai. |

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| File modificati per singolo step | 5 | Se devi toccare piu' file, decomponi in sub-task. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue, non lista esaustiva. |

---

## REQUIRED SUB-SKILL: siae-tdd

Implementa ogni widget e viewmodel seguendo `siae-tdd` (test fallente prima del codice).

---

## Risorse Aggiuntive

- [reference/stack-details.md](reference/stack-details.md) — Dettaglio versioni e configurazione di ogni dipendenza
- [reference/riverpod-patterns.md](reference/riverpod-patterns.md) — Pattern MVVM con Riverpod: Provider, Notifier, AsyncNotifier
- [reference/testing-flutter.md](reference/testing-flutter.md) — Widget test, unit test, integration test con Flutter
