---
last_mapped: 2026-04-22T16:45:00Z
total_files: 28
stack:
  - python
---

# Codebase Map — sample-python

> Single Python package, no sub-package.

## Panoramica Sistema

CLI tool Python 3.11 distribuito come wheel. Package singolo `siae_sample/`,
test in `tests/`. Nessun sub-module di rilievo.

## Stack

- Python 3.11
- pip + venv
- pytest 8

## Convenzioni SIAE Osservate

- Naming: snake_case, PEP 8
- Type hints obbligatori su API pubblica
- Coverage minima: 80%

## Gotcha

- `pyproject.toml` source-of-truth (no setup.py)

## Guida Moduli

### siae_sample

**Path:** siae_sample
**Stack:** Python 3.11
**Description:** Package unico, contiene tutto il codice di produzione.

## Navigation Guide

Entry point CLI: `siae_sample/__main__.py`.
