---
name: siae-tdd
description: >
  Use when implementing production code following test-driven development:
  failing test BEFORE implementation, then Red-Green-Refactor cycle. Best
  after: siae-brainstorming + siae-writing-plans (design + plan approved).
  Trigger: "TDD per feature nuova", "Red-Green-Refactor", "scrivo test
  prima del codice", "ciclo TDD", "test-driven development", "scrittura test prima del codice".
validates_via:
  predicate: tdd_red_green_observed
  evidence_type: state_file
  evidence_path: ~/.claude/.devforge-tdd-state
  evidence_check: "phase in (GREEN, REFACTOR), transitioned from RED"
---

# SIAE TDD — Test-Driven Development

> **Tipo:** Rigid | **Fase SDLC:** 5. Testing

## LA LEGGE DI FERRO

```
NESSUN CODICE DI PRODUZIONE SENZA UN TEST FALLENTE PRIMA
```

**Violare la lettera di questa regola significa violare lo spirito della regola.**

<EXTREMELY-IMPORTANT>
Stai per scrivere, modificare, o generare codice di produzione?
Esiste gia' un test fallente che giustifica questa modifica?
- NO → FERMATI. Scrivi il test prima. Poi torna qui.
- SI → Procedi. Il test deve essere in stato RED (fallente).

Stai razionalizzando ("scrivo il test dopo", "troppo semplice")? Fermati.
Un test scritto dopo l'implementazione prova niente: passa subito, non sai se testa la cosa giusta.
Costo di un bug in produzione = 10x il costo di scrivere il test ora.
</EXTREMELY-IMPORTANT>

Hai scritto codice prima del test? **Cancellalo. Ricomincia.** Nessuna eccezione.

## Quando si applica

**Sempre:** feature nuove, bug fix, refactoring, qualsiasi modifica comportamentale. **Eccezioni (chiedi al partner umano):** prototipi usa-e-getta, codice generato, config puri.

## Scaling — Quando il TDD Completo Non Si Applica

GATE: valuta se il task modifica comportamento eseguibile.

| Tipo di modifica | TDD? | Perche' |
|---|---|---|
| Logica, endpoint, business rule | **SI — ciclo completo** | Modifica comportamento |
| Refactoring con test esistenti | **SI — run test prima/dopo** | Test esistenti = rete sicurezza |
| Config pura (.env, .yml, tfvars) | **NO — validate/plan** | Nessun comportamento unit-testabile |
| Documentazione (.md, commenti) | **NO** | Nessun codice eseguibile |
| Rename/typo senza cambio comportamento | **NO — run test esistenti** | Verifica non-regressione |

Dubbio: "Questa modifica cambia comportamento osservabile?" SI → TDD. NO → test esistenti.

## Rilevamento Tipo Codice

**Context-First Rule:** prima di leggere file o chiedere, verifica se l'informazione e' gia' nella conversazione (messaggi, output tool, skill invocate).

| Segnale | Tipo | Framework test | Skill |
|---|---|---|---|
| `.vue`, vitest jsdom, `@testing-library/vue` | Frontend Vue | vitest + @testing-library/vue | siae-frontend |
| `@angular/core`, `.component.ts` | Frontend Angular | vitest + @testing-library/angular | siae-frontend |
| `react`/`react-dom`, `.tsx`/`.jsx` | Frontend React | vitest + @testing-library/react | siae-frontend |
| `express`/`serverless-http`, `jest.config.ts` | TS Backend | Jest + ts-jest | — |
| `pom.xml`, `.java`, `it.siae.*` | Java/Spring | JUnit 5 + Mockito + AssertJ | — |
| `.py`, `pyproject.toml`, Glue job | Python | pytest + pytest-mock | — |
| `.tf`, `.hcl`, `terragrunt.hcl` | IaC Terraform | terraform test (HCL) | siae-iac |

Per frontend: ciclo RED-GREEN-REFACTOR identico; runner sempre vitest. Pattern UI in `siae-frontend`.

## Workflow Obbligatorio: RED-GREEN-REFACTOR

### 1. RED — Scrivi il test PRIMA del codice
Scrivi UN test minimale che dimostra il comportamento atteso. Il test **DEVE fallire**.
- Un solo comportamento per test, nome chiaro, codice reale (mock solo se inevitabile)
- Fallisce per feature mancante, non per typo/compile error
- Passa al primo colpo? Stai testando comportamento esistente → riscrivi

### 2. GREEN — Scrivi il codice MINIMO per far passare il test
Codice piu' semplice possibile. Niente di piu'.
- No feature non richieste, no refactoring altrove, no edge case non testati
- Nuovo test passa + tutti i precedenti passano + output pulito
- Non passa? Correggi il codice, non il test.

### 3. REFACTOR — Migliora il codice mantenendo i test verdi
Solo dopo GREEN: rimuovi duplicazioni, migliora nomi, estrai helper, semplifica struttura. Test restano verdi. Non aggiungere comportamento. Operazione 🟡 MEDIO — card pre-flight per refactor non banali.

**Guard anti-premature-abstraction.** Refactor = semplificare cio' che esiste, NON introdurre flessibilita' speculativa. Vietato in questa fase: aggiungere interfaccia astratta per UNA sola implementazione, estrarre Strategy/Factory pattern "in caso domani serva", introdurre flag di configurabilita' non richiesti, aggiungere error handling per scenari impossibili. Regola: l'astrazione si introduce quando arriva la **seconda** implementazione concreta o il **secondo** caso reale, non prima. Domanda: *"un senior engineer direbbe che e' overengineered?"* Se si', annulla il refactor.

### 4. COMMIT — Un commit per ciclo RED-GREEN-REFACTOR
Ogni commit contiene sia il test che l'implementazione. **Nessun commit senza test.** Operazione 🟡 MEDIO — card pre-flight richiesta.

### Ripeti
Prossimo test fallente per la prossima feature.

## Permission Denied Handling
Se Edit/Write/Bash negato, passa a modalita' assistita (presenta codice + comandi, utente esegue, Claude analizza output). Dettaglio in `lib/permission-denied-handling.md`.

## Framework per Linguaggio

| Linguaggio | Framework | File test | Run | Coverage |
|---|---|---|---|---|
| Java | JUnit 5 + Mockito + AssertJ | `{Class}Test.java`, `should_{behavior}_when_{condition}` | `mvn test -pl {module} -Dtest={TestClass}` | `mvn verify` JaCoCo ≥70% |
| TS backend | Jest + ts-jest | `{file}.spec.ts` in `src/tests/` | `yarn test -- --testPathPattern={p}` | `yarn test --coverage` ≥70% |
| TS frontend | vitest + @testing-library | `{Component}.spec.ts` affiancato | `npx vitest run {file}` | `npx vitest run --coverage` ≥70% |
| Python | pytest + pytest-mock | `test_{module}.py` | `pytest tests/{path} -v` | `pytest --cov={module}` ≥70% |
| Terraform/HCL | terraform test (≥1.6) | `{risorsa}.tftest.hcl` in `tests/` | `terraform test` (post init) | qualitativa (IAM/SG/encryption assert) |

**Terraform RED/GREEN:** RED = assert su risorsa non esistente (errore riferimento o assert fail); GREEN = aggiungi la risorsa `.tf`; REFACTOR = riorganizza locals/moduli. Naming run block: `{risorsa}_{verifica}` snake_case. Config CI per framework: `reference/framework-configs.md`.

## Classificazione Rischio e Limiti
RED/GREEN/verifica test = 🟢 Sicuro (no card). REFACTOR + COMMIT = 🟡 Medio (card richiesta). Taxonomy in `lib/risk-taxonomy.md`. Limiti: max 2 retry/step, max 5 step/ciclo, max 300 righe/output. Dettaglio in `lib/operational-limits.md`.

REQUIRED SUB-SKILL: siae-verification — invoca prima di dichiarare il ciclo TDD completato.

## Red Flags — FERMATI e Ricomincia

Se riconosci uno di questi segnali, stai saltando il TDD. Fermati. Ricomincia.
1. **Codice di implementazione scritto prima che esista il file di test**
2. **Test che passa al primo run** — non hai iniziato dal RED
3. **Commit multipli senza modifiche ai test** — codice senza copertura
4. **"Tutti i test passano" senza averli visti fallire** — non hai prove
5. **Coverage in calo** — stai aggiungendo codice non testato
6. **File di test creato dopo il file di implementazione** (timestamp git)
7. **Test che verificano l'implementazione invece del comportamento** — mock ovunque, no assert reale
8. **"Solo questa volta" ripetuto piu' di zero volte** — razionalizzazione si accumula
9. **Test copiati e incollati senza capirli** — nessun design tramite test
10. **Nessun test di regressione nel commit di un bug fix** — il bug tornera'
11. **Test commentati o con `@Disabled`/`.skip`/`@pytest.mark.skip`** — test che non girano non esistono
12. **"Lo testo in staging/QA"** — staging non sostituisce unit test

**Tutti questi significano: Cancella il codice. Ricomincia con TDD.**

## Coverage Target

| Scope | Target |
|---|---|
| Globale / TS frontend / Python / Java | ≥70% linee (soglia minima) |
| Feature nuova | ≥80% linee |
| Bug fix | Test di regressione obbligatorio (riproduce bug → fix → verde) |

## Output Strutturato Obbligatorio

<EXTREMELY-IMPORTANT>Per OGNI transizione di fase TDD, DEVI emettere il blocco strutturato. Non parafrasare, non omettere campi.</EXTREMELY-IMPORTANT>

```
[TDD:RED] Test: {nome_test}
  File: {path_file_test} | Assert: {cosa verifica}
  Atteso: FAIL (il test DEVE fallire) | Comando: {comando}
```
```
[TDD:GREEN] Implementazione: {descrizione minima}
  File: {path_file_produzione} | Test: {nome_test che deve passare}
  Atteso: PASS (tutti i test DEVONO passare) | Comando: {comando}
```
```
[TDD:REFACTOR] Refactor: {descrizione}
  File: {path_file_modificati}
  Invariante: tutti i test DEVONO restare verdi | Comando: {comando}
```
```
[TDD:COMMIT] Ciclo completato
  Test: {nome_test} | Impl: {path_file_produzione}
  Copertura: {N test aggiunti, M esistenti passano}
  Commit: {tipo}({scope}): {descrizione}
```

Questo formato rende tracciabile ogni transizione, forza dichiarazione del comando test PRIMA dell'esecuzione, impedisce skip di fasi.

## Regola Finale

```
Codice di produzione → esiste un test che ha fallito prima
Altrimenti → non e' TDD
```

Nessuna eccezione senza il permesso esplicito del tuo partner umano.
