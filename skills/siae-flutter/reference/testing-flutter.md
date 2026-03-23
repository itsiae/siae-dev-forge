# Testing Flutter — SIAE

## Piramide dei Test

```
         ╱╲
        ╱  ╲        Integration Test (pochi, lenti, E2E)
       ╱────╲
      ╱      ╲      Widget Test (molti, veloci, singolo widget)
     ╱────────╲
    ╱          ╲    Unit Test (moltissimi, velocissimi, puro Dart)
   ╱────────────╲
```

| Tipo | Target | Runner | Velocita' |
|------|--------|--------|-----------|
| Unit | ViewModel, Repository, Service | `flutter test` | < 1s |
| Widget | Singolo widget o schermata | `flutter test` | 1-5s |
| Integration | Flusso utente completo | `flutter test integration_test/` | 10-60s |

---

## Unit Test — ViewModel e Repository

Framework: `flutter_test` + `mocktail` (preferito a mockito per null safety).

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockAuthService extends Mock implements AuthService {}

void main() {
  group('LoginViewModel', () {
    late MockAuthService mockAuth;
    late ProviderContainer container;

    setUp(() {
      mockAuth = MockAuthService();
      container = ProviderContainer(overrides: [
        authServiceProvider.overrideWithValue(mockAuth),
      ]);
    });

    tearDown(() => container.dispose());

    test('login con credenziali valide aggiorna stato a authenticated', () async {
      when(() => mockAuth.signIn(any(), any())).thenAnswer((_) async => true);

      await container.read(loginViewModelProvider.notifier).login('user@test.com', 'pass');
      final state = container.read(loginViewModelProvider).valueOrNull;

      expect(state?.isAuthenticated, isTrue);
    });

    test('login fallito mostra errore', () async {
      when(() => mockAuth.signIn(any(), any())).thenThrow(AuthException('Invalid'));

      await container.read(loginViewModelProvider.notifier).login('bad', 'cred');
      final state = container.read(loginViewModelProvider);

      expect(state.hasError, isTrue);
    });
  });
}
```

---

## Widget Test

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() {
  testWidgets('UserCard mostra nome e email', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: UserCard(user: User(name: 'Alice', email: 'alice@test.com')),
        ),
      ),
    );

    expect(find.text('Alice'), findsOneWidget);
    expect(find.text('alice@test.com'), findsOneWidget);
  });

  testWidgets('LoginScreen chiama login on tap', (tester) async {
    final mockVm = MockLoginViewModel();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          loginViewModelProvider.overrideWith(() => mockVm),
        ],
        child: const MaterialApp(home: LoginScreen()),
      ),
    );

    await tester.enterText(find.byKey(const Key('email')), 'test@test.com');
    await tester.enterText(find.byKey(const Key('password')), 'password');
    await tester.tap(find.byKey(const Key('login_button')));
    await tester.pump();

    verify(() => mockVm.login('test@test.com', 'password')).called(1);
  });
}
```

---

## Integration Test

File in `integration_test/`, eseguiti su device/emulatore reale.

```dart
// integration_test/login_flow_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('flusso login completo', (tester) async {
    app.main();
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('email')), 'user@test.com');
    await tester.enterText(find.byKey(const Key('password')), 'password');
    await tester.tap(find.byKey(const Key('login_button')));
    await tester.pumpAndSettle(const Duration(seconds: 5));

    expect(find.text('Dashboard'), findsOneWidget);
  });
}
```

---

## Struttura File Test

```
test/
├── unit/
│   ├── viewmodels/
│   │   └── login_viewmodel_test.dart
│   ├── repositories/
│   │   └── user_repository_test.dart
│   └── services/
│       └── auth_service_test.dart
├── widget/
│   ├── screens/
│   │   └── login_screen_test.dart
│   └── common/
│       └── user_card_test.dart
└── helpers/
    ├── mocks.dart          # Mock centralizzati
    └── test_helpers.dart   # pumpApp, ProviderScope wrapper

integration_test/
├── login_flow_test.dart
└── onboarding_flow_test.dart
```

---

## Convenzioni

- File test: `{name}_test.dart`, affiancato o in directory `test/` mirrorando `lib/`
- Mock library: `mocktail` (preferito per Dart 3 e null safety)
- Coverage minima: **70%** (statements, branches, functions, lines)
- CI: `flutter test --coverage` + enforcement soglia
- Golden test: opzionali per schermate critiche (`matchesGoldenFile`)
