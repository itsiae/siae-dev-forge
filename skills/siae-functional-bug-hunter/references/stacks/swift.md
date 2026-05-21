# Stack: Swift

## Stack id

`swift`

## Manifest fingerprints

- File globs: `**/Package.swift`, `**/*.xcodeproj/project.pbxproj`, `**/*.xcworkspace`, `**/Podfile`, `**/Cartfile`, `**/*.swift`
- Content patterns: `let package = Package(...)` in `Package.swift`; `Pod` declarations in `Podfile`.
- Negative match: a `pubspec.yaml` sibling with `flutter:` block + iOS folder → the iOS sub-tree is dispatched to `flutter-dart.md`, not here.

## Analysis-unit granularity

- **Swift Package Manager (SPM)**: each `target` in `Package.swift` is one analysis unit when source sets diverge.
- **Xcode workspace**: each project file is one unit.
- **App + extensions**: the main app and each extension (Today, Notification Service, Share) are separate units.
- See [../repo_granularity.md](../repo_granularity.md).

## Parser

- Tree-sitter grammar: `tree-sitter-swift`.
- Max AST depth: 5.
- `Info.plist` and `*.entitlements` parsed as XML for capability / entry-point detection.

## Entry-point kinds detected

| Framework / surface | `entry_point.kind` | Detection signal |
|---|---|---|
| SwiftUI scene / view | `ui-screen` | `@main struct App: App` + `WindowGroup { ContentView() }`; child views declared in scene hierarchy |
| UIKit view controller | `ui-screen` | class extending `UIViewController` referenced from a storyboard segue / programmatic navigation |
| Vapor (server-side Swift) | `http-route` | `app.get("path", use: handler)` / `app.post(...)` |
| AWS Lambda Swift runtime | depends on event | `Lambda.run(handler)` in `@main` struct |
| Push notification handler | `event-publisher` (passive) | `application(_:didReceiveRemoteNotification:fetchCompletionHandler:)` |
| URL scheme / Universal Link | `http-route` (deep-link entry) | `Info.plist` `CFBundleURLTypes` + `application(_:open:options:)` |
| WidgetKit timeline provider | `scheduled-job` | conformance to `TimelineProvider` |
| App Intents | `cli-command` (voice / Shortcuts) | `struct <X>: AppIntent` with `perform()` |
| BackgroundTasks framework | `scheduled-job` | `BGTaskScheduler.shared.register(...)` |
| In-app Share Extension | `ui-screen` | `Info.plist` `NSExtensionPointIdentifier = "com.apple.share-services"` |

## Inputs typing

- SwiftUI `@State`, `@Binding`, `@ObservedObject` → recorded as `inputs[]` only when bound to external state (UserDefaults, server, file).
- UIKit: `IBOutlet` properties bound to storyboard fields → `inputs[]`.
- Vapor: `try req.content.decode(DTO.self)` → `inputs[].type = DTO`; `req.parameters.get("id")` → `String`.
- Deep-link: `URLComponents` query items are extracted as `inputs[]`.
- Codable conformance and `CodingKeys` enum capture rename/transform rules.

## Side-effect detection

- Persistence: Core Data `NSManagedObjectContext.save`, SwiftData `modelContext.insert`, GRDB / SQLite.swift write statements, UserDefaults writes for sensitive keys (flagged).
- HTTP clients: `URLSession.shared.data(for:)`, `Alamofire.request`.
- Push: `APNS` send via Vapor APNS; client side only receives.
- Filesystem: `FileManager` `createFile`, `Data.write(to:)`.
- Keychain: `SecItemAdd` / `SecItemUpdate` are flagged as side effects (and as targets for the bug-pattern row on credentials handling).

## Cross-stack bridge hints

- iOS app calling a backend → `URLSession` `URL` literal → `http-route` resolution against other units.
- Universal Link domain → resolved against `aws-serverless` API Gateway / CloudFront aliases.
- Push notification topic → cross-reference with `aws-serverless` SNS topic ARNs.
- See [../cross_stack_bridges.md](../cross_stack_bridges.md).

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — rows where column `swift` =
`MUST-if-applicable`. Specifically: force-unwrap (`!`) on optional in
user-visible path (crash to user), `@MainActor` violation causing UI
desync, Combine subscription leak (cancellable retained too long), Core
Data context concurrency violation, deep-link path parameter validation
gap, BackgroundTask expiration not handled.

## Empty-input branch

If a unit is detected as `swift` (`Package.swift` or `*.xcodeproj`
present) but **zero** entry points are extracted (e.g. a pure utility
SPM library), the unit is recorded in `coverage.md` with skip reason
`no-entry-points`. Test bundles (`*Tests/`) are auto-excluded with
`out-of-scope`.
