# Stacks INDEX — dispatcher contract

This index is the single point of dispatch for stack-specific parsing and
entry-point extraction. The framework-agnostic core in `SKILL.md` calls
into exactly one row of this table per analysis unit. A new stack is added
by dropping `<id>.md` into this directory and appending a row to the table
below; **no edit to `SKILL.md` is required**. This pluggability is verified
by `tools/check_pluggability.sh`.

## Loading rule

For each analysis unit produced by phase 1, the runtime:

1. matches the unit against the **Detection** column below in priority order
   (top of table wins),
2. loads the corresponding `<id>.md` reference,
3. applies that reference's "Entry-point kinds" and "Side-effect detection"
   sections,
4. on no match, falls back to `_generic-fallback.md` (tier 2).

A unit may match more than one stack (e.g. a Python repo with Terraform
under `infra/`). In that case the runtime splits the unit by directory
according to `repo_granularity.md` and dispatches per sub-unit.

## Tier-1 stacks (dedicated references)

| Stack id | Display name | Detection (manifest fingerprints) | Tree-sitter grammar | Reference |
|---|---|---|---|---|
| `java` | Java / JVM | `pom.xml`, `build.gradle`, `build.gradle.kts`, `settings.gradle*` | `tree-sitter-java` | [java.md](java.md) |
| `kotlin` | Kotlin | `build.gradle.kts` with kotlin plugin, `*.kt` files | `tree-sitter-kotlin` | [kotlin.md](kotlin.md) |
| `scala` | Scala | `build.sbt`, `*.scala` | `tree-sitter-scala` | [scala.md](scala.md) |
| `typescript-javascript` | TypeScript / JavaScript | `package.json`, `tsconfig.json`, `*.ts`, `*.tsx`, `*.js`, `*.jsx` | `tree-sitter-typescript` + `tree-sitter-javascript` | [typescript-javascript.md](typescript-javascript.md) |
| `python` | Python | `pyproject.toml`, `requirements.txt`, `setup.py`, `setup.cfg`, `Pipfile` | `tree-sitter-python` | [python.md](python.md) |
| `go` | Go | `go.mod`, `go.work` | `tree-sitter-go` | [go.md](go.md) |
| `rust` | Rust | `Cargo.toml`, `Cargo.lock` | `tree-sitter-rust` | [rust.md](rust.md) |
| `swift` | Swift | `Package.swift`, `*.xcodeproj`, `Podfile` | `tree-sitter-swift` | [swift.md](swift.md) |
| `ruby` | Ruby | `Gemfile`, `*.gemspec` | `tree-sitter-ruby` | [ruby.md](ruby.md) |
| `dotnet` | .NET / C# | `*.csproj`, `*.sln`, `global.json` | `tree-sitter-c-sharp` | [dotnet.md](dotnet.md) |
| `flutter-dart` | Flutter / Dart | `pubspec.yaml`, `*.dart` | `tree-sitter-dart` | [flutter-dart.md](flutter-dart.md) |
| `terraform-hcl` | Terraform / HCL | `*.tf`, `*.tfvars`, `terragrunt.hcl`, `providers.tf` | `tree-sitter-hcl` | [terraform-hcl.md](terraform-hcl.md) |
| `aws-serverless` | AWS serverless | `template.yaml` (SAM), `cdk.json`, `serverless.yml`, `*.asl.json` (Step Functions), `samconfig.toml` | regex fallback + YAML/JSON parsing | [aws-serverless.md](aws-serverless.md) |
| `data-platform` | Data platform | `dbt_project.yml`, Airflow `dags/*.py`, `*.ipynb`, `spark-defaults.conf`, `airflow.cfg` | regex fallback + Python AST for DAGs | [data-platform.md](data-platform.md) |

## Tier-2 — generic fallback

| Stack id | Display name | Detection | Reference |
|---|---|---|---|
| `_generic` | Generic fallback | No Tier-1 manifest match | [_generic-fallback.md](_generic-fallback.md) |

## Per-file contract (template enforced)

Every `<id>.md` MUST contain the following sections in this order:

1. **Stack id** — stable kebab-case identifier matching the table above.
2. **Manifest fingerprints** — concrete file globs + content patterns.
3. **Analysis-unit granularity** — how monorepo splits work for this stack.
4. **Parser** — tree-sitter grammar name OR "regex fallback (no grammar)".
5. **Entry-point kinds detected** — table mapping framework → `entry_point.kind` → detection signal.
6. **Inputs typing** — how to infer `inputs[].type` for this stack.
7. **Side-effect detection** — persistence libs, HTTP clients, message publishers, IaC apply surfaces.
8. **Cross-stack bridge hints** — local-only; the global identifier-resolution table lives in [../cross_stack_bridges.md](../cross_stack_bridges.md).
9. **Bug-patterns row pointer** — link to the matrix row(s) in [../bug_patterns.md](../bug_patterns.md) where this stack is `MUST-if-applicable`.
10. **Empty-input branch** — behavior when no entry points are found in a unit of this stack.

The runtime considers a stack reference **valid** iff all 10 sections are
present. `tools/check_pluggability.sh` enforces this.

## Out-of-scope (intentional)

The following stacks are NOT covered as Tier-1 in v1.0.0 — they fall back
to `_generic-fallback.md`: Elixir, Clojure, Erlang, PHP, Perl, Lua, Haskell,
OCaml, Crystal, Nim, Zig, Julia, R, MATLAB, Fortran, COBOL, Ada, Assembly.
A future minor bump may promote any of these to Tier-1 by dropping a new
file here.
