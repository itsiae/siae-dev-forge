# siae-brainstorming — Checklist 7 Punti Dettagliata

> Reference linked da `../SKILL.md`. Dettaglio operativo Step 1-7.

## 1. Smart Intake — Inferisci il contesto dal codebase

**NON chiedere cio' che il codice sa gia'.** Leggi prima, chiedi dopo. Verifica prima se l'informazione e' gia' nella conversazione corrente.

**Fonti (in ordine):** (1) `CLAUDE.md` progetto (stack, regole); (2) manifest `pom.xml`/`package.json`/`requirements.txt`/`terragrunt.hcl` (dipendenze); (3) struttura directory via Glob (pattern architetturale); (4) `git log --oneline -10` (lavoro recente); (5) `docs/plans/` (design precedenti); (6) auto-memory `~/.claude/projects/<project>/memory/MEMORY.md` (lezioni cross-sessione); (6b) memoria episodica `project_session_*.md` (branch, PR, stato sessione precedente); (7) JIRA via MCP Atlassian (ticket correlati).

**Ogni inferenza:** Confidence HIGH (≥90%) / MEDIUM (60-89%) / LOW (<60%) + citation `file:riga`.

## 2. Scope Assessment — Valuta se decomporre

**Test:** dominio coeso o piu' sottosistemi indipendenti?

**Segnali scope troppo ampio:** 3+ domini, componenti potenzialmente repo separati, stack diversi, piu' team/factory.

**Se troppo ampio:** presenta decomposizione numerata, chiedi quale affrontare per primo, gli altri restano nel backlog.

**Se scope ok:** procedi a Step 3.

## 3. Presenta inferenze + domande mirate

Presenta le inferenze in tabella compatta `Campo | Valore | [Confidence] | file:riga` per conferma rapida.

**Regole:** conferma in blocco o correzioni puntuali. Domande SOLO per confidence LOW, campi non inferiti, scopo. Una alla volta. Scelta multipla preferita. Se tutto HIGH e confermato, procedi direttamente a Step 4.

## 3b. Option Zero Gate

Prima di proporre codice, verifica se il problema si risolve con configurazione, infrastruttura o processo.

**Verifiche:** AWS Parameter Store / SSM, Terraform variables, feature flag esistente, env var, ticket DevOps/infra, servizio o libreria SIAE esistente, config applicativa (`application.yml`, `.env`).

**Se applicabile:** presenta la soluzione config/infra, chiedi conferma. Anche config/infra passa per design doc (breve) e piano (anche 1-subtask). Emetti checkpoint `[BRAINSTORM:OPTION-ZERO]`.

**Se non applicabile:** documenta brevemente perche' ("non esiste parameter store per X") e procedi a Step 4.

## 4. Proponi 2-3 approcci con trade-off e raccomandazione

- Ogni approccio: descrizione, pro, contro, complessita'
- Raccomandazione tua + motivazione
- Stima SP doppia scala (SP-Umano / SP-Augmented) — vedi `brainstorming-jira.md`

## 5. Presenta design per sezioni, approvazione dopo ciascuna

- Scala la sezione alla complessita' (poche frasi → 200-300 parole)
- Approvazione incrementale dopo ciascuna sezione
- Copri: architettura, componenti, flusso dati, gestione errori, testing

## 6. Scrivi design doc in `docs/plans/YYYY-MM-DD-<topic>-design.md`

Salva il design validato. Includi contesto, decisioni, trade-off scelti, stima SP, criteri di accettazione. Committa con card 🟡 MEDIO (vedi `lib/risk-taxonomy.md`) — senza commit il design resta invisibile in git history.

## 6b. Spec Review Gate (con reviewer automatico)

Prima del gate utente, lancia subagent spec-reviewer con prompt in [../design-reviewer-prompt.md](../design-reviewer-prompt.md) passando `{design_doc_path}` e `{user_goal}`.

**Processo:**
1. Lancia reviewer, leggi report
2. Se BLOCK: fixa, ri-lancia (max 5 iterazioni); dopo 5 → escalation utente
3. Se solo WARN: presenta al gate utente
4. Se zero issue: gate standard

Emetti checkpoint `[BRAINSTORM:SPEC-REVIEW]`.

Dopo PASS reviewer, gate utente:
```
Design reviewato automaticamente (N iterazioni, 0 BLOCK).
Conferma:
- Requisiti completi?
- Criteri accettazione coprono tutti i casi?
- Decisioni architetturali corrette?
- Stime SP realistiche?
- Dominio focalizzato?
```

NON invocare siae-writing-plans senza conferma esplicita a questo gate.

## 7. REQUIRED: Transizione al piano implementativo

Design approvato, committato, Spec Review Gate confermato?

```
REQUIRED SUB-SKILL: siae-writing-plans
```

`siae-writing-plans` gestisce decomposizione task, template TDD, execution handoff (subagent o sessione separata). NON scrivere il piano in questa skill.
