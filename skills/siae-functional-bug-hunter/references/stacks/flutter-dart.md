# Stack: Flutter / Dart

## Stack id

`flutter-dart`

## Manifest fingerprints

- File globs: `**/pubspec.yaml`, `**/pubspec.lock`, `**/*.dart`
- Content patterns: `flutter:` key (with `sdk: flutter` under `dependencies`) in `pubspec.yaml`. Pure Dart (server-side or CLI) is detected by absence of `flutter:` key.
- Negative match: an `ios/` directory with only Swift / Objective-C → that sub-tree dispatches to `swift.md`; the Dart side remains here.

## Analysis-unit granularity

- **Melos monorepo**: each package in `packages/*` is one analysis unit.
- **Flutter app + native modules**: app is one unit; each `ios/` and `android/` native sub-tree dispatches to `swift.md` / `kotlin.md` respectively.
- **Single Flutter app**: the repo root is one unit.
- See [../repo_granularity.md](../repo_granularity.md).

## Parser

- Tree-sitter grammar: `tree-sitter-dart`.
- Max AST depth: 5.
- Generated files (`*.g.dart`, `*.freezed.dart`) are excluded by default with skip reason `generated-code`.

## Entry-point kinds detected

| Framework / surface | `entry_point.kind` | Detection signal |
|---|---|---|
| Flutter screen / route | `ui-screen` | `MaterialApp(routes: { '/<path>': (_) => <Screen>() })`, `GoRouter`, `Navigator.pushNamed`, `Beamer` location |
| Riverpod async provider | `event-publisher` (internal) | `final <name>Provider = FutureProvider((ref) async { ... })` invoked by UI |
| Push notification handler | `event-publisher` (passive) | `FirebaseMessaging.onMessage.listen` + foreground/background handlers |
| Deep link / Universal Link | `http-route` | `uni_links` `getInitialUri()` / `app_links` `AppLinks().uriLinkStream` + handler |
| Method channel handler | `cli-command` | `MethodChannel('<name>').setMethodCallHandler(...)` |
| Background task (`workmanager`, `flutter_background_service`) | `scheduled-job` | `Workmanager().registerPeriodicTask(...)` |
| Dart server (shelf) | `http-route` | `Router()` + `app.get('<path>', handler)` |
| AWS Lambda (`aws_lambda_dart_runtime`) | depends on event | `Runtime<Event>(handler)` registration |
| CLI entry | `cli-command` | `void main(List<String> args)` + `args` parsing |

## Inputs typing

- UI screens: route arguments via `ModalRoute.of(context)!.settings.arguments` → captured as `inputs[]` with the declared cast type.
- Riverpod providers: family providers `Provider.family<T, Param>(...)` expose `Param` as input.
- Method channel: `call.arguments` is `dynamic`; the cast inside the handler (e.g. `call.arguments as Map<String, dynamic>`) is the typing source.
- Freezed unions / sealed classes with `@Freezed` + JSON serialization provide strong DTO typing.

## Side-effect detection

- Persistence: ObjectBox (`box.put`), Hive (`box.put`), `sqflite` `db.insert / update / delete`, Isar.
- HTTP clients: `dart:io HttpClient`, `package:http`, `dio`, `chopper`.
- Message publishers: Firebase Realtime DB writes, Firestore writes, AWS Amplify Datastore.
- Filesystem: `dart:io File.writeAsString` / `writeAsBytes`.
- Platform side effects: `MethodChannel.invokeMethod` (delegates to native side; flagged for cross-boundary risk).

## Cross-stack bridge hints

- `dio.get('<url>')` / `http.get(Uri.parse('<url>'))` → `http-route` resolution.
- Amplify GraphQL: cross-reference with `aws-serverless` AppSync schemas.
- Method channel name → cross-reference with native handler in `swift.md` / `kotlin.md` units.
- See [../cross_stack_bridges.md](../cross_stack_bridges.md).

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — rows where column
`flutter-dart` = `MUST-if-applicable`. Specifically: `late` variable
accessed before init (LateInitializationError to user), `Future`
swallowed (no `await`), `setState` after `dispose` (crash), navigation
stack desync (broken back-button), deep-link parameter validation gap,
overflow in `Container` causing layout exception visible to user,
`SharedPreferences` writes not awaited losing user data on app kill.

## Empty-input branch

If a unit is detected as `flutter-dart` but **zero** entry points are
extracted (e.g. a utility Dart package with no UI and no CLI main), the
unit is recorded in `coverage.md` with skip reason `no-entry-points`.
`test/` directory is auto-excluded with `out-of-scope`.
