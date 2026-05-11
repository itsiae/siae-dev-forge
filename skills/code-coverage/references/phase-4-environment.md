# Phase 4 — Environment Setup

**Goal**: garantire che runtime + framework siano installati prima di Phase 5.

## Auto-install policy

Read `.code-coverage/env.json`. Per ogni framework con `installed: false` e command non-null in `assets/install-snippets.json`:

1. Snapshot lockfile: `cp <lockfile> .code-coverage/lockfile.bak`
   (lockfile = `package-lock.json` / `yarn.lock` / `pnpm-lock.yaml` / `poetry.lock`).
2. Run install command da `assets/install-snippets.json[<framework>].command`
   (alternative `alt_yarn` / `alt_pnpm` / `alt_poetry` se il PM rilevato è diverso).
3. If exit-code != 0:
   - Restore lockfile from backup.
   - Append error to `.code-coverage/install-log.txt`.
   - emit Block 4 entry "framework install failed" + END Phase 4.
4. If exit-code == 0: log to `decisions.log` and proceed.

Per framework con `command: null` (junit5/junit5-gradle/mockk/cargo-test/flutter_test):
- Read `assets/install-snippets.json[<framework>].manual_manifest_edit`.
- Apply edit autonomously to pom.xml/build.gradle/Cargo.toml/pubspec.yaml.
- Run subsequent verification (e.g., `mvn dependency:resolve`, timeout 30s).

## Vitest config generation

Solo se `vitest.config.ts` ASSENTE e framework=vitest. Generate skeleton:

```typescript
import { defineConfig } from 'vitest/config'
export default defineConfig({
  test: {
    environment: 'jsdom',  // 'node' for backend/serverless
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary'],
      include: ['src/**/*.{ts,tsx,js,jsx}'],
      exclude: ['**/*.test.*', '**/*.spec.*', '**/node_modules/**']
    }
  }
})
```

Mai sovrascrivere config esistente. Decisione loggata in `.code-coverage/decisions.log`.

## Blocking Check Handler

Se `env.json.missing` contiene un runtime essenziale (Node/Python/Java/Go/Rust/Dotnet/Flutter):

```
ENVIRONMENT BLOCKER

Required runtime not available: <runtime>

Install:
  <runtime-specific install command from official docs>
  e.g. "brew install node@20" / "nvm use 20" / "sudo apt-get install nodejs"

Then re-run /code-coverage.
```

STOP execution. Don't continue without runtime.

## TIMEOUT handling

Se `env.json.available[i].reason == "TIMEOUT"`:
- Log warning, do NOT block.
- Treat as "available but slow"; subsequent install commands use 60s timeout.
- Comportamento per JVM (mvn/gradle, timeout 30s default) e Flutter (timeout 30s default) — vedi `validate_env.py`.

## Output

Phase 4 termina con:
- `.code-coverage/install-log.txt` aggiornato con tutti i comandi eseguiti
- `.code-coverage/lockfile.bak` (rollback artifact)
- `decisions.log` con outcome del framework install
