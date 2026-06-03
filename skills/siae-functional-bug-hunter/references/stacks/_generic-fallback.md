# Stack: Generic fallback

## Stack id

`_generic`

## Manifest fingerprints

This file is the **dispatcher of last resort**: it is loaded only when
none of the Tier-1 stack references in [INDEX.md](INDEX.md) match the
unit. By construction it has no positive fingerprints; it is selected
by elimination.

Examples of units that land here:

- Elixir / Erlang (`mix.exs`, `rebar.config`)
- Clojure / ClojureScript (`deps.edn`, `project.clj`, `shadow-cljs.edn`)
- PHP (`composer.json`)
- Perl (`cpanfile`, `dist.ini`)
- Lua (`*.lua` without OpenResty)
- Haskell (`stack.yaml`, `cabal.project`)
- OCaml (`dune-project`, `*.opam`)
- Crystal (`shard.yml`)
- Julia (`Project.toml` with `[deps]` for Julia, not for poetry — disambiguation rule below)
- R (`DESCRIPTION` with `Package:`, `renv.lock`)
- COBOL, Fortran, Ada, Assembly, Zig, Nim
- Mixed-language repos that don't declare a primary stack

## Analysis-unit granularity

- One unit per repository root by default.
- If a `Makefile` / `CMakeLists.txt` / build orchestration file declares
  sub-targets, those targets become sub-units (best-effort, regex-based).

## Parser

- **No tree-sitter grammar assumed**.
- Regex-only parsing with the following patterns (loaded conservatively):
  - HTTP route patterns across multiple frameworks: `/route\s*\(\s*['"]<METHOD>['"]\s*,\s*['"]<path>['"]/`, `match\s+['"]<path>['"]\s+do`, etc.
  - Handler / endpoint patterns: `function\s+handler\s*\(`, `def\s+handler`, `sub\s+handler`.
  - Common DB call patterns: `INSERT INTO`, `UPDATE`, `DELETE FROM`, `MERGE INTO` in string literals.
  - Common HTTP client patterns: literal URLs in code, `curl` invocations.
- Max regex passes per file: 10.

## Entry-point kinds detected

| Surface | `entry_point.kind` | Detection signal |
|---|---|---|
| Generic HTTP handler | `http-route` | function definition where the name or surrounding comment contains "handler", "endpoint", "controller", "action", "route" + at least one HTTP verb literal in proximity |
| Generic message consumer | `message-consumer` | function definition where the name contains "consumer", "subscriber", "listener", "worker", "processor" |
| Generic scheduled job | `scheduled-job` | a cron literal pattern (`* * * * *`) within 10 lines of a function definition |
| Generic CLI | `cli-command` | a `main` / `Main` / `__main__` symbol or shebang `#!/usr/bin/env <interp>` |

## Inputs typing

- All inputs are typed `unknown` unless the language is known to have a
  parser (which would route the unit to a Tier-1 stack).
- Inline comments matching `# input: <name>: <type>` are honored as a
  documentation-driven typing hint.

## Side-effect detection

- Generic regex catalog: SQL write statements in string literals, HTTP
  client calls, file writes (`fopen`, `File.open`, `open(`, etc.),
  message-publishing patterns.
- Confidence is downgraded: each side effect is recorded with
  `confidence: low_pattern_match` and surfaced in `coverage.md`.

## Cross-stack bridge hints

- The generic fallback contributes URL literals and resource-name
  literals to the boundary identifier registry, but it does not perform
  identifier resolution by itself. Cross-stack matches are computed on
  the Tier-1 side.

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — the `_generic` column
in the matrix lists which patterns degrade gracefully on regex-only
analysis. Patterns marked `N/A` for `_generic` are intentionally
suppressed (they require AST or framework knowledge that the fallback
cannot provide).

## Empty-input branch

If a unit is dispatched to `_generic` and **zero** entry points are
extracted (even with the broad heuristics above), the unit is recorded
in `coverage.md` with skip reason `unparseable` and a one-line note
explaining what was tried. The unit is excluded from phases 4–7. The
operator is notified via `open_questions.md` with a suggestion: "Add a
Tier-1 manifest for this stack" or "Add explicit entry-point
annotations / comments to surface intent."

## Disambiguation note (Julia / poetry conflict)

A `Project.toml` file matches both Julia (`[deps]` table for Julia
package management) and Python Poetry until 1.x. The runtime
disambiguates by:

1. presence of `[tool.poetry]` → `python.md` (Poetry-style);
2. presence of `julia_version` field → `_generic-fallback.md` (Julia);
3. neither → `_generic-fallback.md` with a low-confidence flag.
