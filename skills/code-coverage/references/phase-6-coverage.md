# Phase 6 — Coverage Execution

## Purpose
Execute the coverage tool for the selected framework, parse the output,
and produce a per-module coverage table. Flag any module below threshold.

---

## Context-Safety Rule

**Always redirect full coverage output to a file. Read only the last 100 lines into context.**

```bash
# Pattern for every framework — replace <coverage_command> with the framework-specific command below
<coverage_command> > .code-coverage/coverage-output.txt 2>&1
tail -n 100 .code-coverage/coverage-output.txt
```

This prevents large verbose output (dependency trees, compiler warnings, 1000+ line lcov reports)
from saturating the context window and triggering B-05.

---

## Coverage Commands by Framework

### Vitest
```bash
# Run with v8 provider (recommended)
npx vitest run --coverage

# With explicit reporter options
npx vitest run --coverage --coverage.reporter=text --coverage.reporter=lcov --coverage.reporter=html

# Threshold enforcement (add to vitest.config.ts instead for CI)
npx vitest run --coverage --coverage.thresholds.lines=70
```

Coverage output: `coverage/` directory with `lcov.info` and `index.html`.

### Jest
```bash
npx jest --coverage --coverageReporters=text --coverageReporters=lcov --coverageReporters=html
```

### pytest
```bash
python -m pytest --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=70
```

`--cov=src` targets the `src/` directory. Adjust to match the repo structure
(e.g., `--cov=app`, `--cov=.` for flat layouts).

### JUnit 5 — Maven
```bash
mvn test jacoco:report
# HTML report: target/site/jacoco/index.html
```

### JUnit 5 — Gradle
```bash
./gradlew test jacocoTestReport
# HTML report: build/reports/jacoco/test/html/index.html
# XML report (CI upload): build/reports/jacoco/test/jacocoTestReport.xml
```

### Kotlin — Kover (Gradle)
```bash
./gradlew test koverHtmlReport koverXmlReport
# HTML report: build/reports/kover/html/index.html
# XML report (CI upload): build/reports/kover/report.xml
```

> **Note**: `koverHtmlReport` alone does NOT produce an XML file. Always run both tasks.
> `koverXmlReport` requires the Kover Gradle plugin (`org.jetbrains.kotlinx.kover`) version ≥ 0.7.

### flutter_test
```bash
flutter test --coverage
# Generates: coverage/lcov.info
# Optional HTML: genhtml coverage/lcov.info -o coverage/html
```

### Go
```bash
go test ./... -coverprofile=coverage.out -covermode=atomic
go tool cover -func=coverage.out        # terminal output
go tool cover -html=coverage.out        # HTML report
```

### Rust (Linux)
```bash
cargo tarpaulin --out Lcov --output-dir coverage
```

### Rust (macOS)
```bash
cargo llvm-cov --html --output-dir coverage
```

### C# (.NET)
```bash
dotnet test /p:CollectCoverage=true \
            /p:CoverletOutputFormat=lcov \
            /p:CoverletOutput=./coverage/lcov.info \
            /p:Threshold=70 \
            /p:ThresholdType=line
```

### Ruby
```bash
COVERAGE=true bundle exec rspec
# SimpleCov writes to coverage/index.html
```

### Ruby (PowerShell)
```powershell
$env:COVERAGE = "true"
bundle exec rspec
```

### PHP
```bash
XDEBUG_MODE=coverage vendor/bin/phpunit --coverage-html coverage --coverage-text
```

### PHP (PowerShell)
```powershell
$env:XDEBUG_MODE = "coverage"
vendor/bin/phpunit --coverage-html coverage --coverage-text
```

---

## Coverage Report Parsing

After running the coverage command, parse the terminal output to build
the coverage summary table. Extract per-module (file-level) coverage.

### Vitest / Jest text output pattern
```
 src/services/payment.ts     |  92.3  |  88.0  |  91.0  |  92.3  |
 src/utils/formatter.ts      |  100   |  100   |  100   |  100   |
 src/handlers/order.ts       |  58.7  |  50.0  |  61.5  |  58.7  | 142,145,201
```
Parse columns: File | Stmts% | Branch% | Funcs% | Lines% | Uncovered Lines

### pytest output pattern
```
src/services/payment.py     60      4    93%   45-48
src/utils/formatter.py      25      0   100%
src/handlers/order.py       80     12    85%   123, 145-150
```
Parse columns: Name | Stmts | Miss | Cover% | Missing Lines

---

## Coverage Summary Table (Required Output)

| Module | Lines% | Branch% | Threshold | Status |
|--------|--------|---------|-----------|--------|
| src/services/payment.ts | 92.3% | 88.0% | 80% P1 | PASS |
| src/utils/formatter.ts | 100.0% | 100.0% | 70% P2 | PASS |
| src/handlers/order.ts | 58.7% | 50.0% | 80% P1 | FAIL (−21%) |
| **TOTAL** | **78.4%** | **73.2%** | **70%** | **PASS** |

Modules with `✗ FAIL` are passed to Phase 7 for repair.

---

## CI Integration Snippet

After coverage passes, emit suggested CI snippet in OUTPUT Block 9 come "Recommended CI integration step". Mai modificare file CI esistenti.

### GitHub Actions
```yaml
- name: Run tests with coverage
  run: npx vitest run --coverage

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    files: coverage/lcov.info
    fail_ci_if_error: true
    threshold: 70
```

### GitLab CI
```yaml
test:coverage:
  script:
    - npx vitest run --coverage --reporter=junit --outputFile=test-results.xml
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'
  artifacts:
    reports:
      junit: test-results.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
```
