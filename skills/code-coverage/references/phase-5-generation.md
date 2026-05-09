# Phase 5 — Test Generation

## Purpose
Generate deterministic, enterprise-grade unit tests for each target module.
Tests follow the AAA pattern, cover happy path + edge cases + negative path,
and use idiomatic mocking for the selected framework.

---

## Testability Classification

Before generating any test, classify each target file by testability tier. Within a priority level (P1/P2/P3), process **T1 before T2 before T3 before T4**.

| Tier | Criteria | Mock Setup Cost | Coverage ROI |
|------|----------|-----------------|--------------|
| T1 — Pure Logic | No external imports, no I/O, no framework components — pure functions only | None | Highest |
| T2 — Injectable Services | Class/function with typed dependencies injected via constructor/parameters | Low (`vi.mock` per dep) | High |
| T3 — Framework Components | React/Vue/Angular/Svelte components, hooks, context providers | Medium (jsdom + `render`) | Medium |
| T4 — I/O Handlers | Lambda handlers, DB repositories, HTTP clients, queue consumers | High (AWS mocks, DB fakes) | Low |

**Stop rule:** if the 70% global target is reached before exhausting T3/T4 files, STOP generation. Report remaining T3/T4 files as "deferred — target already met" in Block 9.

---

## Batch Generation Rule

When the next N files in the queue share all three preconditions, generate their tests in a single LLM call:
- (a) Same testing framework target
- (b) Similar export shape: ≤ 3 public functions OR one class with ≤ 5 methods each
- (c) No shared mutable state between siblings

Batch ceilings by tier:
- **T1**: up to 5 files per call
- **T2**: up to 3 files per call
- **T3**: 1 file per call (always)
- **T4**: 1 file per call (always)

**Anti-pattern:** Do NOT batch files with divergent error handling patterns or different mocking requirements — quality degradation on tail items of the batch outweighs the iteration savings.

---

## P2 Early-Exit Checkpoint

After every 10 files generated **within the P2 tier**, run the Coverage Gate (same redirect pattern as Phase 5 Coverage Gate):

```bash
<coverage_command> > .code-coverage/coverage-gate-p2-checkpoint.txt 2>&1 && tail -n 100 .code-coverage/coverage-gate-p2-checkpoint.txt
```

If Global coverage ≥ 70% AND every P1 module has coverage ≥ 80%: **stop P2 generation** immediately and proceed to Block 8 reporting. List remaining P2 and P3 files as "deferred — target met during P2" in Block 9.

---

## Pre-Generation Checklist

Before writing any test file:
1. Apply skip patterns from `assets/priority-rules.json` — skip matching files.
2. Apply P1/P2/P3 classification — process P1 first, then P2, then P3.
   **Composite priority score within each tier:** sort files by `priority_score = (1 - current_coverage) × loc` descending. `current_coverage` and `loc` come from `module_coverage` and `file_list` produced in Phase 1 → Phase 3. Files with no existing coverage data use `current_coverage = 0`. This ordering maximises coverage gain per token spent.
3. Read each source file being tested — extract: exported functions/classes, dependencies/imports, async patterns, error types thrown.
   **Selective read rule:** For files with LOC > 150, first run:
   ```bash
   grep -n "^export\|^class\|^function\|throw new" <file>
   ```
   to extract public API and error patterns. Read the full file only if grep reveals complex patterns (multiple classes, private state affecting public behavior, non-trivial control flow). For files ≤ 150 LOC, read in full.
3b. For each dependency to mock, verify its export type before writing the mock:
    - **Named export** → `import { Dep } from 'path'` + `vi.mock('path', () => ({ Dep: vi.fn() }))`
    - **Default export** → `import Dep from 'path'` + `vi.mock('path', () => ({ default: vi.fn() }))`
    - **Object/class with methods** → include ALL methods actually called by the SUT in the factory: `vi.mock('path', () => ({ methodA: vi.fn(), methodB: vi.fn() }))`
    Never cast a default export as a named-export cast — it produces `ReferenceError` at runtime.
4. Present the full list of files to be created to the user.
5. **Request approval before writing any file to disk.**

---

## AAA Pattern — Mandatory Structure

Every test block MUST follow Arrange / Act / Assert with explicit comments:

```
// Arrange — set up inputs, mocks, expected values
// Act     — call the function or method under test
// Assert  — verify the output or side effects
```

Never combine Arrange + Act in the same line without comments.
Never assert inside the Arrange block.

---

## Coverage Requirements Per Module

Each public function or method in the target module requires:

| Test Case | Description |
|-----------|-------------|
| Happy path | Valid, expected input → correct output |
| Edge case 1 | Boundary value (empty array, zero, null with default, max length) |
| Edge case 2 | Concurrent/async concern OR unexpected but valid input type |
| Negative path | Invalid input → expected error thrown or rejection |

For functions with multiple branches (if/switch), add one test per branch
that represents a distinct business rule.

---

## Mocking Patterns by Framework

### Vitest
```typescript
// Module mock
vi.mock('../path/to/dependency', () => ({
  functionName: vi.fn().mockResolvedValue(expectedValue),
}))

// Spy on method
const spy = vi.spyOn(instance, 'methodName').mockReturnValue(value)

// Reset between tests — choose ONE strategy, do not mix:
// A) Using only vi.mock (no vi.spyOn): clearAllMocks only
beforeEach(() => { vi.clearAllMocks() })
// B) Using vi.spyOn: add restoreAllMocks to restore original implementations
// afterEach(() => { vi.restoreAllMocks() })  // Add ONLY if vi.spyOn is used in this describe
// C) Need to reset return values between tests: use resetAllMocks (replaces A)
// beforeEach(() => { vi.resetAllMocks() })
//
// Note: clearAllMocks + restoreAllMocks together is redundant — restoreAllMocks already clears.
```

### Jest
```typescript
jest.mock('../path/to/dependency', () => ({
  functionName: jest.fn().mockResolvedValue(expectedValue),
}))
beforeEach(() => { jest.clearAllMocks() })
```

### pytest (Python)
```python
# Via pytest-mock fixture
def test_something(mocker):
    mock_dep = mocker.patch('module.path.DependencyClass')
    mock_dep.return_value.method.return_value = expected

# Via unittest.mock patch decorator
@patch('module.path.dependency_function')
def test_something(mock_fn):
    mock_fn.return_value = expected
```

### JUnit 5 + Mockito (Java)
```java
@ExtendWith(MockitoExtension.class)
class ServiceTest {
    @Mock private DependencyInterface dependency;
    @InjectMocks private ServiceUnderTest service;

    @Test void shouldDoSomething() {
        when(dependency.method(any())).thenReturn(expected);
        var result = service.execute(input);
        assertThat(result).isEqualTo(expected);
        verify(dependency).method(input);
    }
}
```

### JUnit 5 + MockK (Kotlin)
```kotlin
@ExtendWith(MockKExtension::class)
class ServiceTest {
    @MockK lateinit var dependency: DependencyInterface
    private lateinit var service: ServiceUnderTest

    @BeforeEach fun setup() { service = ServiceUnderTest(dependency) }

    @Test fun `should do something`() {
        every { dependency.method(any()) } returns expected
        val result = service.execute(input)
        assertThat(result).isEqualTo(expected)
        verify { dependency.method(input) }
    }
}
```

### pytest + chispa (PySpark)
```python
import pytest
from pyspark.sql import SparkSession
from chispa import assert_df_equality

@pytest.fixture(scope="session")
def spark():
    return SparkSession.builder.master("local[*]").appName("test").getOrCreate()

def test_transform(spark):
    input_df = spark.createDataFrame([...], schema)
    result = transform_function(spark, input_df)
    expected = spark.createDataFrame([...], schema)
    assert_df_equality(result, expected, ignore_row_order=True)
```

### flutter_test
```dart
testWidgets('{{widget}} renders correctly', (WidgetTester tester) async {
  // Arrange
  await tester.pumpWidget(MaterialApp(home: {{Widget}}()));
  // Act
  await tester.pump();
  // Assert
  expect(find.byType({{Widget}}), findsOneWidget);
});
```

### Go (testing + testify)
```go
func TestFunctionName(t *testing.T) {
    t.Run("happy path", func(t *testing.T) {
        // Arrange
        input := ...
        // Act
        result, err := FunctionName(input)
        // Assert
        require.NoError(t, err)
        assert.Equal(t, expected, result)
    })
}
```

### Rust (cargo test)
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_function_name_happy_path() {
        // Arrange
        let input = ...;
        // Act
        let result = function_name(input);
        // Assert
        assert_eq!(result, expected);
    }
}
```

---

## Lambda-Specific Mocking (Vitest)

When generating tests for AWS Lambda handlers, mock all AWS SDK clients
and event sources. **Never make real AWS API calls.**

```typescript
import { mockClient } from 'aws-sdk-client-mock'
import { DynamoDBDocumentClient, GetCommand } from '@aws-sdk/lib-dynamodb'

const ddbMock = mockClient(DynamoDBDocumentClient)

beforeEach(() => { ddbMock.reset() })

it('should handle APIGatewayProxyEvent', async () => {
  // Arrange
  ddbMock.on(GetCommand).resolves({ Item: { id: '1', name: 'test' } })
  const event: APIGatewayProxyEvent = {
    httpMethod: 'GET',
    path: '/resource/1',
    pathParameters: { id: '1' },
    headers: { 'Content-Type': 'application/json' },
    multiValueHeaders: {},
    queryStringParameters: null,
    multiValueQueryStringParameters: null,
    body: null,
    isBase64Encoded: false,
    resource: '/resource/{id}',
    stageVariables: null,
    requestContext: {
      accountId: '123456789012',
      apiId: 'test-api',
      httpMethod: 'GET',
      identity: { sourceIp: '127.0.0.1' } as any,
      path: '/resource/1',
      protocol: 'HTTP/1.1',
      requestId: 'test-request-id',
      requestTimeEpoch: Date.now(),
      resourceId: 'test-resource',
      resourcePath: '/resource/{id}',
      stage: 'test',
    },
  }

  // Act
  const result = await handler(event, {} as Context)

  // Assert
  expect(result.statusCode).toBe(200)
  expect(JSON.parse(result.body)).toMatchObject({ id: '1' })
})
```

### Event Mock Templates
```typescript
// SQS
const sqsEvent: SQSEvent = {
  Records: [{ body: JSON.stringify({ key: 'value' }), messageId: '1', ... }]
}

// SNS
const snsEvent: SNSEvent = {
  Records: [{ Sns: { Message: JSON.stringify({ key: 'value' }), ... } }]
}

// EventBridge
const eventBridgeEvent: EventBridgeEvent<'detail-type', { key: string }> = {
  source: 'my.source', 'detail-type': 'MyEvent',
  detail: { key: 'value' }, ...
}
```

---

## Naming Convention

Test files must follow the convention of the target stack:

| Stack | Convention | Example |
|-------|-----------|---------|
| Vitest / Jest | `<module>.test.ts` | `payment.service.test.ts` |
| pytest | `test_<module>.py` | `test_payment_service.py` |
| JUnit 5 | `<Class>Test.java` | `PaymentServiceTest.java` |
| MockK (Kotlin) | `<Class>Test.kt` | `PaymentServiceTest.kt` |
| Go | `<file>_test.go` | `payment_service_test.go` |
| Rust | Module `tests` block in same file or `tests/<module>.rs` |
| C# | `<Class>Tests.cs` | `PaymentServiceTests.cs` |
| Flutter | `<widget>_test.dart` | `payment_screen_test.dart` |

Test files are placed in:
- JS/TS: use `<module>.test.ts` co-located with the source file **by default**.
  Exception: check once at the **workspace root** for an `__tests__/` directory:
  ```bash
  find <workspace_root> -maxdepth 3 -type d -name "__tests__" | head -1
  ```
  If the output is non-empty, use the `__tests__/` pattern for the entire workspace. Apply one pattern per workspace — never mix co-location and `__tests__/` within the same workspace.
- Python: in `tests/` directory mirroring source structure
- Java: in `src/test/java/<package>/` mirroring `src/main/java/<package>/`.
  Package derivation rule: strip the `src/main/java/` prefix from the source path, replace `/` with `.`, drop the filename. Example: `src/main/java/com/siae/service/PaymentService.java` → package `com.siae.service` → test at `src/test/java/com/siae/service/PaymentServiceTest.java`.
- Kotlin: in `src/test/kotlin/<package>/` mirroring `src/main/kotlin/<package>/`. Apply the same package derivation rule as Java but strip `src/main/kotlin/` prefix.
- Go: same package directory as source
- Rust: use inline `#[cfg(test)] mod tests { use super::*; ... }` for unit tests that need access to private or `pub(crate)` items. Use a separate `tests/<module>.rs` file only for integration tests that exercise the public API.
- Flutter/Dart: in `test/` directory at the package root, mirroring the `lib/` structure. Example: `lib/services/payment_service.dart` → `test/services/payment_service_test.dart`.
