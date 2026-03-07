# Skill Visual Completeness — Design

> **Stato:** Approvato
> **Data:** 2026-03-07
> **Branch:** feature/service-logic-map-skill (PR #46)

## Contesto

12 skill del plugin mancano di uno o più elementi del DevForge Visual Design System:
- **Legge di Ferro** — principio non negoziabile (solo skill Rigid)
- **Tabella Classificazione Rischio Operazioni** — ogni skill
- **Tabella Anti-Razionalizzazione** — ogni skill (Rigid obbligatorio, Flexible consigliato)

Queste omissioni riducono la compliance di Claude: senza anti-razionalizzazione,
le skill Rigid vengono bypassate più facilmente. Senza risk table, le pre-flight
card non hanno contesto di riferimento.

## Goal

Aggiungere gli elementi mancanti a tutte le 12 skill, con contenuto contestuale
al dominio di ciascuna (non generico).

## Decisioni

- **Contenuto contestuale**: ogni tabella deve riflettere il dominio specifico della skill
  (le razionalizzazioni per siae-iac sono diverse da quelle per siae-brainstorming)
- **1 subagent per skill**: parallelizzazione massima, contesto fresco per ogni skill
- **Formato identico**: DevForge Visual Design System già in uso nelle skill complete
  (siae-debugging, siae-subagent-development come riferimento)
- **Posizione fissa**: Legge di Ferro dopo il banner, Risk Table e Anti-Razi prima dei Vincoli

## Gap per Skill

| Skill | Tipo | Legge di Ferro | Risk Table | Anti-Razi |
|-------|------|:-:|:-:|:-:|
| siae-brainstorming | Rigid | ❌ | ❌ | ❌ |
| siae-qa | Rigid | ❌ | ❌ | — |
| siae-tdd | Rigid | — | ❌ | — |
| siae-automation | Rigid | — | ❌ | — |
| siae-git-workflow | Rigid | ❌ | — | — |
| siae-architecture | Flexible | n/a | ❌ | ❌ |
| siae-code-standards | Flexible | n/a | — | ❌ |
| siae-codebase-map | Flexible | n/a | — | ❌ |
| siae-data-engineering | Flexible | n/a | — | ❌ |
| siae-documentation | Flexible | n/a | — | ❌ |
| siae-frontend | Flexible | n/a | — | ❌ |
| siae-iac | Flexible | n/a | — | ❌ |

## Template di Riferimento

### Legge di Ferro (Rigid)
```markdown
## LA LEGGE DI FERRO

```
[PRINCIPIO NON NEGOZIABILE IN MAIUSCOLO — 1 RIGA]
```
```

### Tabella Classificazione Rischio
```markdown
## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| [operazione specifica] | 🟢 Sicuro | No |
| [operazione specifica] | 🟡 Medio | Si |
| [operazione specifica] | 🔴 Alto | Si |
```

### Tabella Anti-Razionalizzazione
```markdown
## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "[scusa comune nel dominio]" | [risposta diretta] |
```

## Skill di Riferimento

- `skills/siae-debugging/SKILL.md` — Anti-Razionalizzazione + Risk Table completi
- `skills/siae-subagent-development/SKILL.md` — Legge di Ferro + tutte le tabelle
- `skills/siae-writing-skills/SKILL.md` — Risk Table + Anti-Razi per skill Flexible

## Stima SP

**SP: 5** — 12 file, contenuto contestuale per ognuno, parallelizzabile.
Rischio: il contenuto generico non aggiunge valore. Ogni subagent DEVE leggere
la skill e scrivere razionalizzazioni reali del dominio.

## Criteri di Accettazione

- [ ] Tutte le 12 skill hanno Risk Table (se mancante)
- [ ] Tutte le 5 skill Rigid hanno Legge di Ferro (se mancante)
- [ ] Tutte le 12 skill hanno Tabella Anti-Razionalizzazione (se mancante)
- [ ] Il contenuto di ogni tabella è contestuale al dominio della skill
- [ ] `wc -l` di ogni SKILL.md modificato non supera 600 righe
- [ ] Test suite 39/39 PASS dopo le modifiche
