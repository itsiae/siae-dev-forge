# Repo granularity rules

This file is the deterministic algorithm used by phase 1 (inventory) to
split each `args.roots[i]` into one or more **analysis units**. The
phase-3 subagent fan-out operates on analysis units, not on raw roots.

## Why analysis units matter

A monorepo containing twelve packages should NOT be analyzed as a
single unit — that would defeat the per-unit subagent dispatch and
flood any single subagent's context. Conversely, a single-package repo
should NOT be artificially split.

The split is deterministic: given the same root contents, the same
list of analysis units is produced on every run.

## Detection priority (top wins)

Phase 1 evaluates the rules below **in order**. The first matching rule
wins for a given root; remaining rules are not evaluated for that root.

### Rule 1 — Nx workspace

**Detection**: `nx.json` AT root level.

**Split**: each subdirectory containing a `project.json` is one
analysis unit. The unit id is `nx:<project.json.name>`.

```
repo/
├── nx.json
├── apps/
│   ├── web/project.json       → unit nx:web
│   └── api/project.json       → unit nx:api
└── libs/
    ├── ui/project.json        → unit nx:ui
    └── core/project.json      → unit nx:core
```

### Rule 2 — Turborepo workspace

**Detection**: `turbo.json` AT root level.

**Split**: each package referenced in `package.json` `workspaces`
field is one analysis unit. The unit id is `turbo:<package-name>` (the
name from each package's `package.json`).

### Rule 3 — pnpm workspace

**Detection**: `pnpm-workspace.yaml` AT root level.

**Split**: each package matching one of the `packages:` globs is one
analysis unit. The unit id is `pnpm:<package-name>`.

### Rule 4 — Yarn / npm workspaces (without Turbo / Nx / pnpm)

**Detection**: `package.json` with a `"workspaces"` field AT root level.

**Split**: each workspace package is one analysis unit. The unit id is
`yarn:<package-name>` (or `npm:<package-name>`).

### Rule 5 — Bazel

**Detection**: `WORKSPACE` or `WORKSPACE.bazel` or `MODULE.bazel` AT
root level.

**Split**: each directory containing a `BUILD` / `BUILD.bazel` file
with at least one `*_binary` rule (`java_binary`, `py_binary`,
`go_binary`, `rust_binary`, `cc_binary`, `kt_jvm_binary`, etc.) is one
analysis unit. The unit id is `bazel:<package-path>`.

Library-only `BUILD` files (only `*_library` targets) are NOT units;
they are recorded in the dependency closure as referenced libraries.

### Rule 6 — Gradle multi-project

**Detection**: `settings.gradle` or `settings.gradle.kts` AT root
level, containing at least one `include` directive.

**Split**: each `include(":<name>")` is one analysis unit. The unit id
is `gradle:<name>`. The runtime then dispatches each unit's stack
based on the unit's plugins (`kotlin("jvm")` → kotlin; `id("java")` →
java).

### Rule 7 — Maven multi-module

**Detection**: `pom.xml` AT root level with a `<modules>` element.

**Split**: each `<module>` element is one analysis unit. The unit id
is `maven:<artifactId>`.

### Rule 8 — Go workspace

**Detection**: `go.work` AT root level.

**Split**: each `use` directive is one analysis unit. The unit id is
`go-work:<module-path>`.

### Rule 9 — Cargo workspace

**Detection**: `Cargo.toml` AT root level with `[workspace]` table.

**Split**: each `members` entry is one analysis unit. The unit id is
`cargo:<crate-name>`.

### Rule 10 — SBT multi-project

**Detection**: `build.sbt` AT root level containing one or more
`lazy val <x> = project ...` declarations.

**Split**: each `project` declaration is one analysis unit. The unit
id is `sbt:<project-name>`.

### Rule 11 — Mill

**Detection**: `build.sc` AT root level.

**Split**: each `module` declaration (`object <name> extends Module`)
is one analysis unit. The unit id is `mill:<module-path>`.

### Rule 12 — Melos (Flutter / Dart)

**Detection**: `melos.yaml` AT root level.

**Split**: each package in `packages:` is one analysis unit. The unit
id is `melos:<package-name>`.

### Rule 13 — Terragrunt monorepo

**Detection**: more than one `terragrunt.hcl` file under the root,
none of them at the root itself.

**Split**: each directory containing a `terragrunt.hcl` is one
analysis unit. The unit id is `terragrunt:<relative-path>`.

### Rule 14 — Plain Terraform monorepo

**Detection**: more than one directory containing `*.tf` with a
`terraform { ... }` block (a "root module") under the root.

**Split**: each such directory is one analysis unit. The unit id is
`tf-root:<relative-path>`. Module libraries (directories with `*.tf`
but NO `terraform { }` block) are recorded as referenced libraries
but are NOT units.

### Rule 15 — CDK multi-stack

**Detection**: `cdk.json` AT root level + a `lib/` (TS) or `cdk/`
(Python) folder with multiple stack files.

**Split**: each stack file is one analysis unit. The unit id is
`cdk:<stack-class-name>` extracted from the source.

### Rule 16 — dbt project

**Detection**: `dbt_project.yml` AT root level.

**Split**: the entire dbt project is **one unit** (no further split).
The unit id is `dbt:<project-name>`.

### Rule 17 — Single-package fallback

**Detection**: none of the above rules matched.

**Split**: the entire root is one analysis unit. The unit id is
`single:<root-basename>`.

## Cross-rule layering

When a single root matches **two or more rules at the same priority**
(e.g. a `package.json` workspace AND a `WORKSPACE` Bazel file co-exist),
the runtime applies the rule with the **lower number** first (Bazel
has higher priority than Turbo because `WORKSPACE` is rule 5 vs rule
2). This is a deliberate choice based on Bazel's higher target
granularity; the operator can override via `args.skip_paths` if a
different split is desired.

## Sub-unit dispatch for native sub-trees

For Flutter / Dart projects (rule 12 or rule 17 with a `pubspec.yaml`),
the runtime additionally creates two **sub-units** when present:

- `<unit-id>/ios` → dispatched to `swift.md`,
- `<unit-id>/android` → dispatched to `kotlin.md` (or `java.md` if the
  Android Gradle file uses pure Java plugin).

These sub-units carry the parent's unit-id prefix so subagent merge in
phase 3 reconciles them with the parent.

## Cap on unit count

The runtime caps the number of analysis units per root at **64**. When
the cap is exceeded, the runtime selects the top 64 by file count and
records the rest in `coverage.md` with skip reason `unit-count-cap`.
The operator can override by setting `args.max_units_per_root` (when
supported in a future minor version).

## Empty-input branch

If a root matches no rule and contains no recognizable source code
(e.g. an empty directory or a docs-only directory), the runtime
records the root in `coverage.md` with skip reason `out-of-scope` and
moves on. The run does NOT fail.

## Determinism

The unit list is sorted lexicographically by `unit_id` ASC before
phase 2 starts. Subagent dispatch follows this order. Tie-breaking is
by path string.

## Adding a new monorepo manifest

To add a new monorepo detection rule (minor semver bump):

1. Append a numbered rule above, choosing a priority slot.
2. Update `scripts/detect_stacks.sh` to detect the manifest.
3. Add a fixture in `eval/golden_set/monorepo_<name>/` to exercise the
   new rule.
4. No edit to `SKILL.md` is required.
