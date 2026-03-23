# Stack Dettagliato — Flutter SIAE

## Flutter & Dart

- **Flutter** 3.32.x stable — framework UI cross-platform (iOS, Android, Web)
- **Dart** 3.x — null safety obbligatoria, pattern matching, sealed classes

### Versioning

Pinare la versione Flutter nel file `.fvmrc` o `fvm_config.json` (FVM - Flutter Version Management).
Tutti i developer devono usare la stessa versione. CI/CD deve usare la stessa versione.

---

## State Management — Riverpod 2.x

Riverpod e' lo state manager standard per replicare il pattern MVVM.

### Perche' Riverpod (non Bloc, non Provider)

| Criterio | Riverpod | Bloc | Provider |
|----------|----------|------|----------|
| Compile-time safety | Si (code gen) | Parziale | No |
| Testabilita' | Eccellente (ProviderContainer) | Buona | Limitata |
| Indipendenza da BuildContext | Si | No | No |
| Code generation | Si (riverpod_generator) | No | No |
| Learning curve | Media | Alta | Bassa |

### Provider Types

| Provider | Uso | Esempio |
|----------|-----|---------|
| `Provider` | Valore computato, dipendenza | Repository instance |
| `StateProvider` | Stato semplice (toggle, counter) | Filtro attivo |
| `NotifierProvider` | ViewModel con logica | Form state, business logic |
| `AsyncNotifierProvider` | ViewModel con async | Fetch dati, submit |
| `FutureProvider` | Dato async one-shot | Config iniziale |
| `StreamProvider` | Stream reattivo | Real-time data, connectivity |

---

## Service Locator — Get_it 8.x

Get_it gestisce la dependency injection. Registrare tutti i servizi in `di/injection.dart`.

```dart
final getIt = GetIt.instance;

void setupDependencies() {
  // Singletons
  getIt.registerLazySingleton<SecureStorageService>(() => SecureStorageServiceImpl());
  getIt.registerLazySingleton<AuthService>(() => AmplifyAuthService());
  getIt.registerLazySingleton<ConnectivityService>(() => ConnectivityServiceImpl());

  // Factories (nuova istanza ogni volta)
  getIt.registerFactory<Dio>(() => createDioClient(getIt<AuthService>()));

  // Repositories
  getIt.registerLazySingleton<UserRepository>(() => UserRepositoryImpl(
    remoteDataSource: getIt<UserRemoteDataSource>(),
    localDataSource: getIt<UserLocalDataSource>(),
  ));
}
```

**Regola:** Get_it per la DI infrastrutturale (servizi, repository). Riverpod per lo stato UI (viewmodel, provider).

---

## Database — ObjectBox 4.x

Database NoSQL embedded ad alte prestazioni.

### Setup

1. Aggiungere `objectbox` e `objectbox_flutter_libs` in `pubspec.yaml`
2. Aggiungere `objectbox_generator` in `dev_dependencies`
3. Eseguire `build_runner` per generare `objectbox.g.dart` e `objectbox-model.json`

### Entita'

```dart
@Entity()
class UserEntity {
  @Id()
  int id = 0;

  String name;
  String email;

  @Property(type: PropertyType.date)
  DateTime createdAt;

  final tracks = ToMany<TrackEntity>();

  UserEntity({required this.name, required this.email, required this.createdAt});
}
```

### Regole

- `objectbox-model.json` va committato (traccia lo schema)
- Migrazioni: ObjectBox gestisce l'aggiunta di campi automaticamente
- Per rimozione/rename campi: usare `@Entity(uid: ...)` e `@Property(uid: ...)`

---

## Networking — Dio 5.x

### Configurazione base

```dart
Dio createDioClient(AuthService authService) {
  final dio = Dio(BaseOptions(
    baseUrl: AppConfig.apiBaseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 30),
    headers: {'Content-Type': 'application/json'},
  ));

  dio.interceptors.addAll([
    AuthInterceptor(authService),
    RetryInterceptor(dio: dio, retries: 2),
    if (kDebugMode) LogInterceptor(requestBody: true, responseBody: true),
  ]);

  return dio;
}
```

### AuthInterceptor

```dart
class AuthInterceptor extends Interceptor {
  final AuthService _authService;

  AuthInterceptor(this._authService);

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _authService.getAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      final refreshed = await _authService.refreshToken();
      if (refreshed) {
        return handler.resolve(await _retry(err.requestOptions));
      }
    }
    handler.next(err);
  }
}
```

---

## Auth — AWS Amplify (Cognito)

### Inizializzazione

```dart
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  await Amplify.addPlugins([AmplifyAuthCognito()]);
  await Amplify.configure(amplifyconfig);
  setupDependencies();
  runApp(const ProviderScope(child: MyApp()));
}
```

### AuthService

```dart
abstract class AuthService {
  Future<bool> signIn(String email, String password);
  Future<void> signOut();
  Future<String?> getAccessToken();
  Future<bool> refreshToken();
  Future<bool> isSignedIn();
  Stream<AuthHubEvent> get authEvents;
}
```

---

## Firebase

### Crashlytics

```dart
void setupCrashlytics() {
  FlutterError.onError = FirebaseCrashlytics.instance.recordFlutterFatalError;
  PlatformDispatcher.instance.onError = (error, stack) {
    FirebaseCrashlytics.instance.recordError(error, stack, fatal: true);
    return true;
  };
}
```

### Remote Config

```dart
class RemoteConfigService {
  final FirebaseRemoteConfig _config = FirebaseRemoteConfig.instance;

  Future<void> init() async {
    await _config.setConfigSettings(RemoteConfigSettings(
      fetchTimeout: const Duration(seconds: 10),
      minimumFetchInterval: const Duration(hours: 12),
    ));
    await _config.setDefaults(<String, dynamic>{
      'feature_x_enabled': false,
    });
    await _config.fetchAndActivate();
  }

  bool isFeatureEnabled(String key) => _config.getBool(key);
}
```

---

## Code Generation — build_runner

### Dipendenze tipiche in `dev_dependencies`

```yaml
dev_dependencies:
  build_runner: ^2.4.0
  json_serializable: ^6.7.0
  freezed: ^2.4.0
  riverpod_generator: ^2.3.0
  objectbox_generator: ^4.0.0
```

### Comandi

```bash
# Build una tantum
dart run build_runner build --delete-conflicting-outputs

# Watch mode (sviluppo)
dart run build_runner watch --delete-conflicting-outputs
```

### Convenzioni file generati

| Sorgente | Generato | Generator |
|----------|----------|-----------|
| `model.dart` | `model.g.dart` | json_serializable, objectbox |
| `model.dart` | `model.freezed.dart` | freezed |
| `viewmodel.dart` | `viewmodel.g.dart` | riverpod_generator |

**Regola:** i file `.g.dart` e `.freezed.dart` vanno committati nel repository.

---

## Design — Font e SVG

### Barlow Font

Caricare da assets locali (non Google Fonts runtime) per garantire disponibilita' offline:

```yaml
# pubspec.yaml
flutter:
  fonts:
    - family: Barlow
      fonts:
        - asset: assets/fonts/Barlow-Regular.ttf
        - asset: assets/fonts/Barlow-Medium.ttf
          weight: 500
        - asset: assets/fonts/Barlow-SemiBold.ttf
          weight: 600
        - asset: assets/fonts/Barlow-Bold.ttf
          weight: 700
```

### SVG

Usare `flutter_svg` per tutte le icone e illustrazioni:

```dart
SvgPicture.asset('assets/icons/logo.svg', width: 48, height: 48);
```

Assets SVG in `assets/icons/` e `assets/images/`. Mai usare PNG per icone monocromatiche.
