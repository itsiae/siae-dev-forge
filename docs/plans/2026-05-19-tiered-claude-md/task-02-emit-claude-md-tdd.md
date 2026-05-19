---
task: 02
title: TDD emit-claude-md.py
status: PENDING
estimate_min: 90
type: TDD
depends_on: [01]
---

# Task 02 — TDD `emit-claude-md.py`

## Obiettivo

Implementare via TDD lo script Python che legge `docs/CODEBASE_MAP.md` e
genera la gerarchia `CLAUDE.md` L1+L2+L3 secondo soglie definite nel design.

## File da creare

1. `skills/siae-codebase-map-tiered/scripts/emit-claude-md.py` (~200 righe)
2. `tests/test_emit_claude_md.py` (~150 righe, pytest)
3. `tests/fixtures/codebase-map-samples/` con 3 fixture:
   - `single-repo-java.md` (Maven mono-module)
   - `monorepo-ts.md` (pnpm-workspace 3 package)
   - `single-python.md` (no sub-package)

## CLI signature

```bash
python3 emit-claude-md.py --root <path> --map <CODEBASE_MAP.md> [--dry-run]
```

Output JSON su stdout:
```json
{
  "files_written": ["./CLAUDE.md", "./api/CLAUDE.md", "./web/CLAUDE.md"],
  "l1_lines": 187,
  "l2_count": 2,
  "l3_count": 0,
  "warnings": []
}
```

## Logica L1 (root)

- Estrai sezione "Panoramica Sistema" + "Stack" + "Convenzioni SIAE Osservate" + "Gotcha" da CODEBASE_MAP.md
- Genera max 200 righe
- Aggiungi sezione "## Architettura dettagliata" con link `@docs/CODEBASE_MAP.md`
- Se monorepo: lista sub-package con `@<pkg>/CLAUDE.md`

## Logica L2 (per package)

- Per ogni modulo Maven (`pom.xml` in subdir) o package TS (`package.json` in subdir)
- Estrai sezione modulo da CODEBASE_MAP.md "Guida Moduli > [Nome Modulo]"
- Genera CLAUDE.md con:
  - Header `# <Module> — Local context`
  - Riga `> See @../CLAUDE.md for root context.`
  - Sezione "Local conventions" (export, dependencies, gotcha modulo)
  - Sezione "Files" (tabella file chiave)
- Max 150 righe

## Logica L3 (child on-demand)

- Trigger: subdir interno al modulo con >=10 file source AND pattern locale distintivo
- Pattern locale distintivo: framework diverso (Express vs Vue), convenzione mock, scaffold generato
- Se non identificabile da CODEBASE_MAP.md → skip L3 (no inferenza autonoma)
- Genera CLAUDE.md con header + `> See @../../CLAUDE.md` (root) + `> See @../CLAUDE.md` (parent L2)
- Max 100 righe

## TDD cycle (Red-Green-Refactor)

**RED 1:** Test `test_emit_l1_root_from_single_repo_java`
- Arrange: fixture `single-repo-java.md`
- Act: `subprocess.run(["python3", "emit-claude-md.py", "--root", tmp, "--map", fixture, "--dry-run"])`
- Assert: output JSON `l1_lines <= 200`, `l2_count == 0`, `files_written == ["./CLAUDE.md"]`

**RED 2:** Test `test_emit_l2_per_package_in_monorepo_ts`
- Arrange: fixture `monorepo-ts.md` con 3 package
- Act: invoke con `--dry-run`
- Assert: `l2_count == 3`, ogni L2 contiene `@../CLAUDE.md`

**RED 3:** Test `test_emit_l3_only_above_threshold`
- Arrange: fixture con subdir 8 file (under threshold) + subdir 15 file con pattern distintivo
- Act: invoke
- Assert: `l3_count == 1` (solo subdir 15 file)

**RED 4:** Test `test_emit_l1_anti_bloat_warning`
- Arrange: fixture con CODEBASE_MAP enorme che genererebbe L1 >200 righe
- Act: invoke
- Assert: `warnings` contiene "L1 exceeds 200 lines"

**RED 5:** Test `test_dry_run_writes_nothing`
- Act: invoke `--dry-run`
- Assert: nessun file CLAUDE.md scritto sul fs

**RED 6:** Test `test_missing_codebase_map_fails`
- Act: invoke con path map non esistente
- Assert: exit code 1, stderr contiene "CODEBASE_MAP.md not found"

GREEN: implementa logica minimale per superare ogni test.
REFACTOR: estrai parser frontmatter, splitter sezioni, writer in funzioni separate.

## Criteri di accettazione

1. ✅ 6 test pytest PASS
2. ✅ Coverage >=85% su emit-claude-md.py (`pytest --cov`)
3. ✅ CLI conforme a signature documentata
4. ✅ Dry-run non scrive file
5. ✅ Output JSON valido (jsonschema validation in test)
6. ✅ Nessun import esterno oltre stdlib (Python 3.9+)

## Definition of Done

- Script + test creati
- 6/6 test PASS
- Coverage >=85%
- Commit: `feat(skills): emit-claude-md.py per generazione tiered CLAUDE.md`
