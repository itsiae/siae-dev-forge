# siae-brainstorming — Integrazione JIRA

> Reference linked da `../SKILL.md`. Pattern MCP Atlassian + ticket output.

## Discovery ticket correlati

Se MCP Atlassian disponibile, cerca ticket correlati all'inizio (JQL: `project = <KEY> AND summary ~ "<keyword>" ORDER BY updated DESC`).

## Stima Story Points — Doppia Scala

| SP | SP-Umano (senza AI) | SP-Augmented (dev + Claude) |
|----|---------------------|------------------------------|
| 1  | Triviale, zero rischio | Config, typo, rename |
| 2  | Semplice, <1 giorno | CRUD endpoint, test unitario, IaC isolato |
| 3  | Moderato, 1-2 gg | Feature con 2-3 componenti |
| 5  | Significativo, 2-4 gg | Feature cross-module, pipeline ETL |
| 8  | Complesso, ~1 settimana | Nuovo microservizio, refactoring architetturale |
| 13 | Molto complesso, >1 settimana | Migrazione sistema, nuovo dominio |

**Accelerazione AI per tipo:** boilerplate/CRUD ~5-10x · test+refactor meccanico ~3-5x · feature con spec chiare ~2-3x · integrazione API ~1.5-2x · logica di dominio ambigua ~1-1.5x · debug prod ~1-1.5x.

**Come stimare:** identifica tipo dominante, applica moltiplicatore, arrotonda al Fibonacci piu' vicino. Presenta SEMPRE entrambi: `Story Points: 5 SP-Umano / 3 SP-Augmented`.

## Output JIRA ticket

A fine design produci blocco `JIRA TICKET OUTPUT` con campi: Tipo (Story/Task/Bug), Sommario, Descrizione (da design doc), Story Points (doppia scala), Labels, Acceptance Criteria (lista).

## Pre-flight card creazione ticket (🔴 ALTO)

Creazione ticket = 🔴 ALTO (vedi `lib/risk-taxonomy.md`; extra: JIRA ticket = ALTO). Mostra pre-flight card, attendi conferma esplicita (silenzio ≠ consenso), poi `createJiraIssue`.
