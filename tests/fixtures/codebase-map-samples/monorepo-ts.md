---
last_mapped: 2026-05-10T08:30:00Z
total_files: 184
stack:
  - typescript
  - pnpm
  - nodejs
---

# Codebase Map — sample-monorepo-ts

> pnpm-workspace monorepo with 3 packages: api, web, shared.

## Panoramica Sistema

Monorepo TypeScript con 3 package:
- `api/`: server Express REST
- `web/`: SPA Vue 3 + Vite
- `shared/`: tipi e schemi Zod condivisi

Build orchestrata da pnpm workspace + Turbo.

## Stack

- TypeScript 5.3
- Node.js 20 LTS
- pnpm 8
- Express 4 (api), Vue 3 + Vite (web)

## Convenzioni SIAE Osservate

- Naming: kebab-case file, camelCase identifier
- Test: Vitest per ogni package
- Lint: ESLint flat config, Prettier 3
- Coverage minima: 75%

## Gotcha

- `pnpm install` lento (>5min) la prima volta su CI
- `shared` deve essere built prima di `api`/`web` per type resolution

## Guida Moduli

### api

**Path:** api
**Stack:** Express 4 + TypeScript
**Description:** REST server. Endpoints documentati in OpenAPI.

### web

**Path:** web
**Stack:** Vue 3 + Vite 5
**Description:** SPA frontend. Composition API + Pinia store.

### shared

**Path:** shared
**Stack:** TypeScript only
**Description:** Tipi e schemi Zod condivisi tra api e web.

## Navigation Guide

Entry points: `api/src/index.ts`, `web/src/main.ts`.
