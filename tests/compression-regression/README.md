# Compression Regression Suite

Verifica che la compressione SKILL.md (PR #1 anti-dilution) non introduca regressioni E raggiunga i target di miglioramento.

## Run full suite

```bash
bash tests/compression-regression/run-all.sh
```

## Singoli test

- `assert_behavioral_invariants.sh` — K sections preserved
- `assert_compression_targets.sh` — wc -l targets achieved
- `assert_injection_reduction.sh` — devforge-context budget respected
- `assert_baseline_preserved.sh` — 168 PASS / 6 FAIL baseline preserved

Ogni script exit 0 = PASS, exit >0 = FAIL con dettaglio.
