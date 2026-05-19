# Semgrep SIAE Fixtures

100% codice scritto da zero (ADR-004). NO snippet broadcasting reale.

Ogni fixture cita esplicitamente il finding pentest a cui si riferisce
(es. `// Reproduces pattern of PENTEST_REPORT 2026-05-18 F-01`).

Struttura:

- `synthetic/vulnerable/` — codice che la rule DEVE matchare
- `synthetic/safe/` — codice che la rule NON deve matchare (fix raccomandato)
- `synthetic/allowlist/` — pattern legittimi che vanno esclusi via paths.exclude o suppressions.yaml

Test wrapper: `tests/test_semgrep_siae_rules.py` esegue `semgrep --config <rule>`
su ogni fixture e asserta match/no-match atteso.

Per E2E privato con codice broadcasting reale: env `DEVFORGE_BROADCASTING_FIXTURE_PATH=/path/to/clone`
(mai committato, skipped in CI pubblica).
