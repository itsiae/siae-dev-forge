# Robustness Policy — siae-dev-analytics v2 (NF1-NF30)

Copia operativa della §3 del design doc `docs/plans/2026-04-15-dev-analytics-v2-robust-design.md`.
Questa policy e' source-of-truth per i gate automatici (AST audit + mutation testing).

---

## 3.1 Zero silent failures (invariante assoluto)

Ogni funzione Python deve rispettare:
- **NF1** NO `try/except: pass` — ogni eccezione logga con contesto + fallback esplicito
- **NF2** Return value di fallback documentato in docstring
- **NF3** Warnings list propagata fino a Executive Summary ("Dati parziali: X, Y, Z")

## 3.2 Actionable errors

- **NF4** Ogni `raise RuntimeError` ha messaggio >= 20 caratteri con verbo azione (`run`, `verifica`, `configura`, `controllare`, `install`)
- **NF5** Test automatico (grep AST) che verifica tutte le RuntimeError rispettano NF4

## 3.3 Validation boundaries

- **NF6** Input utente (YAML config, CLI args) validato con Pydantic strict
- **NF7** Input da external API (gh, S3, Anthropic) validato con schema (pydantic o jsonschema)
- **NF8** Runtime type checking su signature pubbliche via `typeguard` decorator

## 3.4 Fault injection coverage

Ogni chiamata a sistema esterno DEVE avere test per:
- **NF9** Success (happy path) — 1 test
- **NF10** Timeout — 1 test
- **NF11** Auth failure (401/403) — 1 test
- **NF12** Rate limit primary (backoff retry) — 1 test
- **NF13** Rate limit secondary (sleep + retry) — 1 test
- **NF14** 404 not found — 1 test
- **NF15** 500 server error — 1 test
- **NF16** Malformed response (JSON invalido / troncato) — 1 test
- **NF17** Empty response — 1 test

**Minimo 9 test per esterno call.** API esterne identificate:
- `gh api graphql` (collect_github)
- `gh api orgs/.../teams/.../repos` (resolve teams)
- `gh search repos --topic` (resolve topics)
- `gh api repos/.../branches` (branch tracking)
- AWS S3 `head_bucket`, `list_objects_v2`, `get_object` (3 chiamate x 9 = 27 test)
- Anthropic Console API `usage_report/messages`

## 3.5 Property-based testing

- **NF18** `hypothesis` library per funzioni matematiche (z_score, roi_index, health_score, seasonality_adj)
- **NF19** Invariants runtime: `assert 0 <= rate <= 1` ovunque rate sia output, `assert not pd.isna(score)` su z-score finali

## 3.6 Mutation testing

- **NF20** `mutmut` target >= 85% mutation score su moduli core (`compute_kpis.py`, `autodetect_sources.py`, `compute_ai_impact.py` — nuovo)

## 3.7 Logging coverage

- **NF21** Ogni branch condizionale (if/else/except/try) ha `log.*` call appropriato
- **NF22** Livelli corretti: DEBUG per tracing, INFO per milestones, WARNING per degradation, ERROR per failure
- **NF23** Test automatico (AST walker) che audita logging coverage

## 3.8 Edge case exhaustive

Edge case matrix obbligatoria per ogni modulo (vedi design doc §11).

## 3.9 Concurrency safety

- **NF24** Cache file write atomic (write-to-temp + rename)
- **NF25** Test concurrent-read-during-write leggi vecchio, no corruption

## 3.10 Encoding

- **NF26** Dev name con unicode (emoji, accenti) preservato in output
- **NF27** Excel output con UTF-8 nativo, no mojibake

## 3.11 Timezone

- **NF28** Tutti timestamp parsed as UTC, display in CEST locale-aware
- **NF29** DST transitions handled (ottobre, marzo)
- **NF30** Working days exclude weekend + festivita' italiane (calendario hardcoded)
