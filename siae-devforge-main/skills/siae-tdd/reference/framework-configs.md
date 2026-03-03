# Framework Configurations — CI/CD Reference

Configurazioni dettagliate per i framework di test usati nei progetti SIAE.
Ogni sezione include la configurazione locale e l'integrazione con GitHub Actions
(da `itsiae/siae-gh-actions`).

---

## Java — Maven Surefire / Failsafe + JaCoCo

### pom.xml — Plugin Surefire (unit test)

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <version>3.2.5</version>
    <configuration>
        <includes>
            <include>**/*Test.java</include>
        </includes>
        <argLine>${argLine} -Xmx512m</argLine>
        <parallel>methods</parallel>
        <threadCount>4</threadCount>
    </configuration>
</plugin>
```

### pom.xml — Plugin Failsafe (integration test)

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-failsafe-plugin</artifactId>
    <version>3.2.5</version>
    <configuration>
        <includes>
            <include>**/*IT.java</include>
            <include>**/*IntegrationTest.java</include>
        </includes>
    </configuration>
    <executions>
        <execution>
            <goals>
                <goal>integration-test</goal>
                <goal>verify</goal>
            </goals>
        </execution>
    </executions>
</plugin>
```

### pom.xml — JaCoCo Coverage

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.12</version>
    <executions>
        <execution>
            <id>prepare-agent</id>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>verify</phase>
            <goals>
                <goal>report</goal>
            </goals>
        </execution>
        <execution>
            <id>check</id>
            <phase>verify</phase>
            <goals>
                <goal>check</goal>
            </goals>
            <configuration>
                <rules>
                    <rule>
                        <element>BUNDLE</element>
                        <limits>
                            <limit>
                                <counter>LINE</counter>
                                <value>COVEREDRATIO</value>
                                <minimum>0.70</minimum>
                            </limit>
                        </limits>
                    </rule>
                </rules>
            </configuration>
        </execution>
    </executions>
</plugin>
```

### Dipendenze test (BOM)

```xml
<dependencies>
    <dependency>
        <groupId>org.junit.jupiter</groupId>
        <artifactId>junit-jupiter</artifactId>
        <version>5.11.3</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.mockito</groupId>
        <artifactId>mockito-core</artifactId>
        <version>5.14.2</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.mockito</groupId>
        <artifactId>mockito-junit-jupiter</artifactId>
        <version>5.14.2</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.assertj</groupId>
        <artifactId>assertj-core</artifactId>
        <version>3.26.3</version>
        <scope>test</scope>
    </dependency>
</dependencies>
```

### Comandi

```bash
# Esegui tutti i test di un modulo
mvn test -pl {module}

# Esegui una singola classe di test
mvn test -pl {module} -Dtest={TestClass}

# Esegui un singolo metodo
mvn test -pl {module} -Dtest={TestClass}#should_{behavior}_when_{condition}

# Esegui test + coverage check
mvn verify -pl {module}

# Solo report coverage (dopo test)
mvn jacoco:report -pl {module}
# Report in: target/site/jacoco/index.html
```

---

## TypeScript (backend) — Jest + ts-jest

### jest.config.ts

```typescript
import type { Config } from 'jest';

const config: Config = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: ['**/*.spec.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.spec.ts',
    '!src/**/*.d.ts',
    '!src/**/index.ts',
  ],
  coverageThreshold: {
    global: {
      lines: 70,
      branches: 70,
      functions: 70,
      statements: 70,
    },
  },
  coverageReporters: ['text', 'text-summary', 'lcov', 'clover'],
  coverageDirectory: 'coverage',
};

export default config;
```

### tsconfig per test (tsconfig.spec.json)

```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "types": ["jest", "node"],
    "esModuleInterop": true,
    "allowJs": true
  },
  "include": ["src/**/*.ts", "src/**/*.spec.ts"]
}
```

### package.json (scripts)

```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:ci": "jest --ci --coverage --reporters=default --reporters=jest-junit"
  }
}
```

### Comandi

```bash
# Esegui tutti i test
yarn test

# Esegui test con pattern
yarn test -- --testPathPattern=FormService

# Esegui un singolo file
yarn test -- src/tests/FormService.spec.ts

# Coverage
yarn test --coverage

# Watch mode (sviluppo)
yarn test -- --watch --testPathPattern={pattern}
```

---

## TypeScript (frontend) — vitest + @testing-library/vue

### vitest.config.ts

```typescript
import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.spec.ts'],
    exclude: ['node_modules', 'dist'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'lcov', 'clover'],
      reportsDirectory: 'coverage',
      include: ['src/**/*.ts', 'src/**/*.vue'],
      exclude: [
        'src/**/*.spec.ts',
        'src/**/*.d.ts',
        'src/**/index.ts',
        'src/main.ts',
      ],
      thresholds: {
        lines: 70,
        branches: 70,
        functions: 70,
        statements: 70,
      },
    },
    setupFiles: ['src/test-setup.ts'],
  },
});
```

### src/test-setup.ts

```typescript
import '@testing-library/jest-dom/vitest';
```

### Comandi

```bash
# Esegui tutti i test
npx vitest run

# Esegui un singolo file
npx vitest run src/components/EmailForm.spec.ts

# Coverage
npx vitest run --coverage

# Watch mode (sviluppo)
npx vitest --watch

# UI mode (browser-based test explorer)
npx vitest --ui
```

---

## Python — pytest + pytest-cov

### pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks integration tests",
]

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/migrations/*",
]

[tool.coverage.report]
fail_under = 70
show_missing = true
precision = 2
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

### Dipendenze test (requirements-test.txt o pyproject.toml)

```toml
[project.optional-dependencies]
test = [
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "pytest-mock>=3.14",
    "pytest-asyncio>=0.24",
]
```

### Comandi

```bash
# Esegui tutti i test
pytest tests/ -v

# Esegui test di un modulo specifico
pytest tests/test_form_service.py -v

# Esegui un singolo test
pytest tests/test_form_service.py::test_should_reject_empty_email -v

# Coverage
pytest --cov=src tests/ -v

# Coverage con report HTML
pytest --cov=src --cov-report=html tests/ -v
# Report in: htmlcov/index.html

# Coverage con fail-under
pytest --cov=src --cov-fail-under=70 tests/ -v

# Escludi test lenti
pytest tests/ -v -m "not slow"
```

---

## GitHub Actions — Integrazione con itsiae/siae-gh-actions

### Struttura tipica del workflow

I progetti SIAE usano le reusable actions da `itsiae/siae-gh-actions`.
Di seguito le configurazioni per eseguire i test in CI.

### Java (Maven)

```yaml
name: Test Java
on:
  pull_request:
    paths:
      - '**.java'
      - '**/pom.xml'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'maven'

      - name: Run tests with coverage
        run: mvn verify --batch-mode --no-transfer-progress

      - name: Upload coverage to artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: jacoco-report
          path: '**/target/site/jacoco/'

      - name: Check coverage threshold
        run: |
          # JaCoCo check e' gia' nel pom.xml (fase verify)
          # Il build fallisce automaticamente se < 70%
          echo "Coverage check passed (threshold: 70%)"
```

### TypeScript backend (Jest)

```yaml
name: Test TS Backend
on:
  pull_request:
    paths:
      - '**.ts'
      - 'package.json'
      - 'yarn.lock'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'yarn'

      - name: Install dependencies
        run: yarn install --frozen-lockfile

      - name: Run tests with coverage
        run: yarn test:ci
        env:
          CI: true

      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: jest-coverage
          path: coverage/
```

### TypeScript frontend (vitest)

```yaml
name: Test TS Frontend
on:
  pull_request:
    paths:
      - 'frontend/**'

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Run tests with coverage
        run: npx vitest run --coverage --reporter=verbose
        env:
          CI: true

      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: vitest-coverage
          path: frontend/coverage/
```

### Python (pytest)

```yaml
name: Test Python
on:
  pull_request:
    paths:
      - '**.py'
      - 'pyproject.toml'
      - 'requirements*.txt'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -e ".[test]"

      - name: Run tests with coverage
        run: |
          pytest --cov=src --cov-report=xml --cov-report=term --cov-fail-under=70 tests/ -v

      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pytest-coverage
          path: coverage.xml
```

---

## Coverage Reporters — Formati comuni

Tutti i framework producono report in formati compatibili:

| Framework | Reporter | Output | Per CI |
|-----------|----------|--------|--------|
| JaCoCo | XML + HTML | `target/site/jacoco/` | XML per SonarQube |
| Jest/Istanbul | lcov + text | `coverage/lcov.info` | lcov per Codecov/Coveralls |
| vitest/v8 | lcov + text | `coverage/lcov.info` | lcov per Codecov/Coveralls |
| pytest-cov | XML + term | `coverage.xml` | XML per SonarQube/Codecov |

### Soglie di coverage (riepilogo)

| Scope | Soglia | Enforcement |
|-------|--------|-------------|
| Globale progetto | >= 70% linee | CI fallisce sotto soglia |
| Feature nuova | >= 80% linee | Code review enforcement |
| Bug fix | Test di regressione | PR review obbligatoria |

---

## Note operative

1. **Non disabilitare mai il coverage check in CI.** Se il build fallisce per coverage, la soluzione e' scrivere test, non abbassare la soglia.
2. **I report di coverage vanno sempre come artifact** per permettere revisione in PR.
3. **Coverage thresholds nel codice** (pom.xml, jest.config, vitest.config, pyproject.toml) sono la source of truth. Non sovrascriverli con flag CLI.
4. **Test parallelism:** Surefire usa `parallel=methods`, Jest/vitest parallelizzano di default, pytest richiede `pytest-xdist` per parallelismo esplicito.
