# Pattern MVVM con Riverpod — Flutter SIAE

## Il Pattern

```
View (Widget)
    │ ref.watch(viewModelProvider)
    ▼
ViewModel (Notifier)
    │ ref.read(repositoryProvider)
    ▼
Repository (Get_it)
    │
    ▼
DataSource (API / ObjectBox)
```

---

## ViewModel con Notifier (Sync)

```dart
// Stato immutabile
@freezed
class CounterState with _$CounterState {
  const factory CounterState({
    @Default(0) int count,
    @Default(false) bool isLoading,
  }) = _CounterState;
}

// ViewModel
@riverpod
class CounterViewModel extends _$CounterViewModel {
  @override
  CounterState build() => const CounterState();

  void increment() {
    state = state.copyWith(count: state.count + 1);
  }

  void reset() {
    state = const CounterState();
  }
}
```

---

## ViewModel con AsyncNotifier (Async)

```dart
@freezed
class UserListState with _$UserListState {
  const factory UserListState({
    @Default([]) List<User> users,
    @Default(false) bool isLoadingMore,
    String? errorMessage,
  }) = _UserListState;
}

@riverpod
class UserListViewModel extends _$UserListViewModel {
  @override
  Future<UserListState> build() async {
    final repo = ref.read(userRepositoryProvider);
    final users = await repo.getUsers();
    return UserListState(users: users);
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final repo = ref.read(userRepositoryProvider);
      final users = await repo.getUsers();
      return UserListState(users: users);
    });
  }

  Future<void> deleteUser(int id) async {
    final current = state.valueOrNull;
    if (current == null) return;

    final repo = ref.read(userRepositoryProvider);
    await repo.deleteUser(id);
    state = AsyncData(current.copyWith(
      users: current.users.where((u) => u.id != id).toList(),
    ));
  }
}
```

---

## View (Widget)

```dart
class UserListScreen extends ConsumerWidget {
  const UserListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncState = ref.watch(userListViewModelProvider);

    return asyncState.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(child: Text('Errore: $error')),
      data: (state) => ListView.builder(
        itemCount: state.users.length,
        itemBuilder: (context, index) => UserTile(
          user: state.users[index],
          onDelete: () => ref
              .read(userListViewModelProvider.notifier)
              .deleteUser(state.users[index].id),
        ),
      ),
    );
  }
}
```

---

## Provider per Repository (bridge Get_it → Riverpod)

```dart
// Bridge: esponi il repository di Get_it come Riverpod Provider
@riverpod
UserRepository userRepository(Ref ref) {
  return getIt<UserRepository>();
}
```

Questo pattern permette di:
- Usare Get_it per la DI infrastrutturale (lifecycle singleton)
- Usare Riverpod per la reattivita' UI (auto-dispose, watch)
- Testare con `ProviderContainer` overridando il provider

---

## Testing ViewModel

```dart
void main() {
  late ProviderContainer container;
  late MockUserRepository mockRepo;

  setUp(() {
    mockRepo = MockUserRepository();
    container = ProviderContainer(overrides: [
      userRepositoryProvider.overrideWithValue(mockRepo),
    ]);
  });

  tearDown(() => container.dispose());

  test('build carica utenti', () async {
    when(() => mockRepo.getUsers()).thenAnswer(
      (_) async => [User(id: 1, name: 'Alice')],
    );

    final vm = container.read(userListViewModelProvider.notifier);
    final state = await container.read(userListViewModelProvider.future);

    expect(state.users, hasLength(1));
    expect(state.users.first.name, 'Alice');
  });
}
```

---

## Regole d'Oro

1. **Stato immutabile** — usa `freezed` o `copyWith`. Mai mutare state direttamente
2. **Un ViewModel per feature/schermata** — non condividere ViewModel tra schermate diverse
3. **Repository come interfaccia** — il ViewModel dipende dall'astrazione, non dall'implementazione
4. **ref.watch per UI, ref.read per azioni** — mai `ref.watch` in callback o event handler
5. **AsyncValue.when per gestire loading/error/data** — pattern obbligatorio per dati async
6. **autoDispose** — preferire `@riverpod` (auto-dispose default) per evitare memory leak
