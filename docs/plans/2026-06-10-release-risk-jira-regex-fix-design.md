# Design — Fix regex jira tickets in release_risk CLI

**Data:** 2026-06-10 · **Complessità:** Bassa · **SP:** 0.5 (Umano) / 0.1 (Augmented)

## Contesto
Durante la campagna di coverage 100% su `lib/release_risk`, il nuovo test in-process
`test_extract_jira_tickets` ha rivelato che `_extract_jira_tickets` (`lib/release_risk/cli.py:163`)
usa un gruppo catturante: `re.findall(r"\b(SPORT|DIRITTI|OASIS|POP|TAU)-\d+\b")` ritorna
solo il contenuto del gruppo (es. `['DIRITTI']`) invece del ticket completo (`['DIRITTI-9']`).
La scorecard release-risk mostra quindi prefissi progetto al posto dei ticket Jira.
La SKILL.md (Step 4) prescrive `grep -oE '(SPORT|...)-[0-9]+'` che ritorna il match completo:
la porta Python ha introdotto la regressione.

## Decisione
Gruppo non-catturante: `r"\b(?:SPORT|DIRITTI|OASIS|POP|TAU)-\d+\b"`. One-liner, nessun
cambio di firma o comportamento d'errore (resta `except → []`).

## Alternative scartate
`re.finditer` + `group(0)`: equivalente, più codice.

## Criteri di accettazione
- `test_extract_jira_tickets` PASS: ritorna `['DIRITTI-9']` da commit `feat: x DIRITTI-9`.
- Suite release_risk completa PASS, coverage `lib/release_risk` = 100%.

## Addendum 2026-06-10 — finding verifica e2e

La verifica end-to-end (CLI reale su repo `sport-licenze-service` simulato) ha rivelato
un secondo falso positivo: il file pattern del criterio 1 (`detector.py`) includeva
`\.xml$` generico, quindi `pom.xml`/`logback.xml` venivano flaggati come DB change (+3).

**Decisione:** xml conta come DB change solo con hint DB nel path (`db/.*\.xml$`; gli hint
`migration|liquibase|flyway|changelog` esistenti restano) + content pattern esteso con i tag
liquibase (`<createTable`, `<addColumn`, `<dropColumn`, `<dropTable`, `<renameColumn`,
`<modifyDataType`) per i changelog XML con nome non standard. 4 test nuovi in
`test_release_risk_detector_1_5.py` (2 anti falso-positivo, 1 guard path, 1 anti falso-negativo).

**Doc:** SKILL.md Step 7 ora documenta i limiti della cache (input KG fuori chiave;
`--no-cache` salta solo la lettura ma riscrive la entry).
