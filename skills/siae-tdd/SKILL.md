---
name: siae-tdd
description: >
  Trigger: implementazione feature, bug fix, refactoring, qualsiasi scrittura di codice.
---

# SIAE TDD — Test-Driven Development

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · AI Competence Center                  ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 5. Testing

---

## LA LEGGE DI FERRO

```
NESSUN CODICE DI PRODUZIONE SENZA UN TEST FALLENTE PRIMA
```

**Violare la lettera di questa regola significa violare lo spirito della regola.**

Hai scritto codice prima del test? **Cancellalo. Ricomincia.**

Nessuna eccezione:
- Non tenerlo come "riferimento"
- Non "adattarlo" mentre scrivi i test
- Non guardarlo nemmeno
- Cancellare significa cancellare

Reimplementa partendo dai test. Punto.

---

> 📊 **Dai repo itsiae:** Il 73% dei bug in produzione negli ultimi 6 mesi proveniva da moduli con coverage < 40%. I repo con TDD attivo hanno 3.2x meno hotfix.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## Quando si applica

**Sempre:**
- Nuove feature
- Bug fix
- Refactoring
- Qualsiasi modifica comportamentale

**Eccezioni (chiedi esplicitamente al tuo partner umano):**
- Prototipi usa-e-getta (che verranno cancellati, non "evoluti")
- Codice generato automaticamente
- File di configurazione puri

Stai pensando "salto il TDD solo questa volta"? Fermati. Quella e' razionalizzazione.

---

## Rilevamento Tipo Codice

**Prima del ciclo RED-GREEN-REFACTOR**, identifica il tipo di codice. Il tipo determina il framework di test e i pattern da applicare.

### Detection — Segnali e Mapping

| Segnale nel codice / progetto                                                         | Tipo                   | Framework test                        | Skill di riferimento |
|---------------------------------------------------------------------------------------|------------------------|---------------------------------------|----------------------|
| File `.vue`, `vitest.config.ts` con `environment: 'jsdom'`, import da `@testing-library/vue` | **Frontend (Vue.js)**  | vitest + @testing-library/vue         | **siae-frontend**    |
| `package.json` con `"vue"`, `"vite"`, `"pinia"` nella stessa root                    | **Frontend (Vue.js)**  | vitest + @testing-library/vue         | **siae-frontend**    |
| `package.json` con `"@angular/core"`, `angular.json`, file `.component.ts`           | **Frontend (Angular)** | vitest + @testing-library/angular     | **siae-frontend**    |
| `package.json` con `"react"` / `"react-dom"`, file `.tsx` / `.jsx`                   | **Frontend (React)**   | vitest + @testing-library/react       | **siae-frontend**    |
| `package.json` con `"express"` / `"serverless-http"`, `jest.config.ts`               | **TypeScript Backend** | Jest + ts-jest                        | —                    |
| `pom.xml`, file `.java`, package `it.siae.*`                                          | **Java / Spring Boot** | JUnit 5 + Mockito + AssertJ           | —                    |
| File `.py`, `pyproject.toml`, `requirements.txt`, Glue job                            | **Python**             | pytest + pytest-mock                  | —                    |
| File `.tf`, `.hcl`, `terragrunt.hcl`                                                  | **IaC**                | Terratest (Go)                        | siae-iac             |

### Codice Frontend — integrazione con siae-frontend

Se il tipo rilevato e' **Frontend** (Vue.js, Angular, React o qualsiasi altro framework UI), questa skill integra i pattern definiti in `siae-frontend`. Il runner e' sempre **vitest**, indipendentemente dal framework.

**Cosa cambia rispetto agli altri stack:**
- **Runner test**: vitest (uguale per tutti i framework frontend)
- **Library DOM**: `@testing-library/{vue|angular|react}` in base al framework rilevato
- **File test**: `{Component}.spec.ts`, affiancato al componente nella stessa directory
- **Focus**: comportamento utente (render DOM, interazioni, eventi) — MAI implementazione interna
- **Coverage**: `npx vitest run --coverage`, soglia minima >= 70%
- **Setup file**: `src/test-setup.ts` con `import '@testing-library/jest-dom/vitest'`

**Cosa NON cambia:** il ciclo RED-GREEN-REFACTOR e' identico per tutti i tipi di codice.

> **Codice di produzione frontend:** se nel ciclo TDD devi creare o modificare componenti, hooks/composables o service, invoca `siae-frontend` per i pattern di struttura e le convenzioni di stile.

---

## Workflow Obbligatorio: RED-GREEN-REFACTOR

### 1. RED — Scrivi il test PRIMA del codice

Scrivi UN test minimale che dimostra il comportamento atteso. Il test **DEVE fallire**.

**Requisiti:**
- Un solo comportamento per test
- Nome chiaro che descrive il comportamento
- Codice reale (mock solo se inevitabile)

**Esegui il test. Verifica che:**
- Il test fallisce (non errori di compilazione/sintassi)
- Il messaggio di errore e' quello atteso
- Fallisce perche' la feature manca, non per un typo

Il test passa al primo colpo? Stai testando comportamento esistente. Riscrivi il test.

### 2. GREEN — Scrivi il codice MINIMO per far passare il test

Scrivi il codice piu' semplice possibile che fa passare il test. Niente di piu'.

**Non aggiungere:**
- Feature non richieste dal test
- Refactoring di altro codice
- "Miglioramenti" oltre lo scope del test
- Gestione di edge case non ancora testati

**Esegui tutti i test. Verifica che:**
- Il nuovo test passa
- Tutti i test precedenti passano ancora
- Output pulito (nessun errore, nessun warning)

Il test non passa? Correggi il codice, non il test.
Altri test rotti? Correggi subito.

### 3. REFACTOR — Migliora il codice mantenendo i test verdi

Costruisci la card come MARKDOWN TABLE direttamente nella risposta testuale.

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-tdd |
|:---|
| 🔬 Ciclo: `RED-GREEN-REFACTOR` |
| 📁 File: `<file target>` |
| 1. 🔀 Refactor codice: `<path file>` |
| 💡 Perche': Si sta modificando codice funzionante (test GREEN). Il rischio e' rompere il comportamento esistente. |
| 🚫 Se NO: Il refactoring non viene eseguito. Il codice rimane funzionante ma non ottimizzato. |

Solo dopo il GREEN:
- Rimuovi duplicazioni
- Migliora i nomi
- Estrai helper/utility
- Semplifica la struttura

I test devono restare verdi. Non aggiungere comportamento.

### 4. COMMIT — Un commit per ciclo RED-GREEN-REFACTOR

Costruisci la card come MARKDOWN TABLE direttamente nella risposta testuale.

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-tdd |
|:---|
| 🔬 Ciclo: `RED-GREEN-REFACTOR` |
| 📁 File: `<file target>` |
| 1. 🔀 Git commit ciclo TDD: `<path file>` |
| 💡 Perche': Si sta committando il ciclo completo RED-GREEN-REFACTOR. Un commit errato o incompleto registra codice non verificato nella storia del repo. |
| 🚫 Se NO: Il commit non viene eseguito. Le modifiche rimangono staged e il ciclo non viene chiuso. |

Ogni commit contiene sia il test che l'implementazione. Nessun commit senza test.

### Ripeti

Prossimo test fallente per la prossima feature.

---

## Permission Denied Handling

**Se Edit/Write viene negato:**
1. Presenta il codice (test o implementazione) in un blocco code fenced
2. Indica file path e nome dove deve essere scritto
3. L'utente copia il codice manualmente nel file
4. Procedi con la guida al passo successivo

**Se Bash viene negato (esecuzione test):**
1. Presenta il comando test esatto da eseguire (con flag e directory)
2. Chiedi all'utente di eseguirlo e riportare l'output
3. Analizza l'output riportato per determinare RED/GREEN
4. NON assumere il risultato — attendi l'output reale

**Se entrambi sono negati (Guida TDD Assistita):**
La skill diventa una guida interattiva:
- Genera codice test e implementazione come output testuale
- Indica i comandi da eseguire per ogni fase (RED, GREEN, REFACTOR)
- L'utente esegue manualmente e riporta i risultati
- Claude analizza e guida il passo successivo

**Fasi completabili senza permessi:** analisi, generazione codice, guida step-by-step
**Fasi che richiedono permessi:** Edit/Write (scrittura file), Bash (esecuzione test)

La disciplina TDD (test prima del codice, codice minimo, refactor solo dopo GREEN)
si preserva anche in modalita' assistita.

Se i permessi sono negati:
1. Completa tutte le fasi di analisi e generazione codice
2. Presenta riepilogo di cosa e' stato generato
3. Lista comandi/operazioni per esecuzione manuale
4. NON entrare in loop di retry su tool negato
5. NON dichiarare completamento per fasi non eseguite

---

## Framework per Linguaggio

### Java

- **Framework:** JUnit 5 + Mockito + AssertJ
- **Test class:** `{ClassName}Test.java`
- **Test method:** `should_{behavior}_when_{condition}()`
- **Run:** `mvn test -pl {module} -Dtest={TestClass}`
- **Coverage:** `mvn verify -pl {module}` (JaCoCo, >= 70%)

```java
@Test
void should_reject_empty_email_when_submitting_form() {
    // Arrange
    var request = new SubmitFormRequest("");

    // Act
    var result = formService.submit(request);

    // Assert
    assertThat(result.getErrors())
        .containsExactly("Email obbligatoria");
}
```

### TypeScript (backend)

- **Framework:** Jest + ts-jest
- **Test file:** `{filename}.spec.ts` (in `src/tests/`)
- **Run:** `yarn test -- --testPathPattern={pattern}`
- **Coverage:** `yarn test --coverage` (>= 70%)

```typescript
describe('FormService', () => {
  it('should reject empty email when submitting form', async () => {
    const result = await formService.submit({ email: '' });
    expect(result.error).toBe('Email obbligatoria');
  });
});
```

### TypeScript (frontend)

- **Framework:** vitest + @testing-library/vue
- **Test file:** `{Component}.spec.ts`
- **Run:** `npx vitest run {file}`
- **Coverage:** `npx vitest run --coverage` (>= 70%)

```typescript
import { render, screen } from '@testing-library/vue';
import EmailForm from './EmailForm.vue';

test('should show error when email is empty', async () => {
  render(EmailForm);
  await screen.getByRole('button', { name: 'Invia' }).click();
  expect(screen.getByText('Email obbligatoria')).toBeTruthy();
});
```

### Python

- **Framework:** pytest + pytest-mock
- **Test file:** `test_{module}.py`
- **Run:** `pytest tests/{path} -v`
- **Coverage:** `pytest --cov={module}` (>= 70%)

```python
def test_should_reject_empty_email_when_submitting_form(form_service):
    result = form_service.submit(email="")
    assert result.error == "Email obbligatoria"
```

> Per configurazioni CI dettagliate di ogni framework, vedi `reference/framework-configs.md`.

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Scrittura test fallente (RED) | 🟢 Sicuro | No |
| Esecuzione test per verifica RED | 🟢 Sicuro | No |
| Implementazione minimale (GREEN) | 🟢 Sicuro | No |
| Esecuzione test per verifica GREEN | 🟢 Sicuro | No |
| Refactor del codice | 🟡 Medio | Si |
| Git commit del ciclo RED-GREEN-REFACTOR | 🟡 Medio | Si |

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi max per step | 2 | Fermati. Chiedi all'utente prima di riprovare. |
| Step totali del ciclo RED-GREEN-REFACTOR | 5 | Se ne servono di piu', il task e' mal definito. Torna al design. |
| Output max per analisi | 300 righe | Sintetizza. L'utente non legge wall-of-text. |

---

REQUIRED SUB-SKILL: siae-verification

Invoca `siae-verification` prima di dichiarare il ciclo TDD completato.

---

## Tabella Anti-Razionalizzazione

**Stai per razionalizzare? Leggila. Poi torna a scrivere il test.**

| Pensiero | Realta' |
|----------|---------|
| "Il progetto legacy non ha test" | Inizia dal codice che stai toccando. Ogni nuovo codice ha un test. |
| "E' solo una config change" | Se puo' rompersi, testa che funzioni. |
| "La coverage e' gia' al 70%" | Il 70% e' il minimo, non il traguardo. |
| "Scrivo il test dopo" | Dopo non arriva mai. Il test viene PRIMA. Un test scritto dopo prova niente: passa subito, non sai se testa la cosa giusta. |
| "E' troppo semplice per testarlo" | Le cose semplici sono le piu' facili da testare. Fallo. Ci metti 30 secondi. |
| "Il test rallenterebbe lo sviluppo" | I bug rallentano lo sviluppo. I test li prevengono. TDD e' piu' veloce del debugging in produzione. |
| "Non so come testare questa cosa" | Chiedi. Non e' una scusa per saltare il test. Se e' difficile da testare, il design e' troppo accoppiato. |
| "Sto solo facendo refactoring" | Il refactoring senza test e' roulette russa. I test sono la rete di sicurezza. |
| "Ho gia' testato manualmente" | I test manuali non prevengono regressioni. Serve automazione. "Funzionava quando l'ho provato" non e' una prova. |
| "Il framework non supporta questo tipo di test" | Cambia approccio, non saltare il test. Ogni comportamento e' testabile. |
| "E' un prototipo, i test non servono" | I prototipi diventano produzione. Sempre. Testa dall'inizio o cancella tutto quando finisci di esplorare. |
| "Ho fretta, aggiungo i test nello sprint dopo" | Il debito tecnico costa piu' dell'investimento iniziale. Lo "sprint dopo" non arriva mai. |
| "Cancellare X ore di lavoro e' uno spreco" | Sunk cost fallacy. Il tempo e' gia' andato. Tenere codice non verificato e' debito tecnico. |
| "TDD e' dogmatico, io sono pragmatico" | TDD E' pragmatico. Trova bug prima del commit, previene regressioni, documenta il comportamento. "Pragmatico" senza test = debugging in produzione = piu' lento. |
| "I test dopo raggiungono lo stesso obiettivo" | No. Test-dopo = "cosa fa questo codice?" Test-prima = "cosa DEVE fare questo codice?" Test-dopo sono viziati dall'implementazione. |

---

## Red Flags — FERMATI e Ricomincia

Se riconosci uno di questi segnali, stai saltando il TDD. Fermati. Ricomincia.

1. **Codice di implementazione scritto prima che esista il file di test**
2. **Test che passa al primo run** — non hai iniziato dal RED
3. **Commit multipli senza modifiche ai test** — stai scrivendo codice senza copertura
4. **"Tutti i test passano" senza averli visti fallire** — non hai prove che testino qualcosa
5. **Coverage in calo** — stai aggiungendo codice non testato
6. **File di test creato dopo il file di implementazione** (controlla i timestamp git)
7. **Test che verificano l'implementazione invece del comportamento** — mock ovunque, nessun assert reale
8. **"Solo questa volta" ripetuto piu' di zero volte** — la razionalizzazione si accumula
9. **Test copiati e incollati senza capirli** — non hai fatto design tramite test
10. **Nessun test di regressione nel commit di un bug fix** — il bug tornera'
11. **Test commentati o con `@Disabled`/`.skip`/`@pytest.mark.skip`** — test che non girano non esistono
12. **"Lo testo in staging/QA"** — staging non e' un sostituto per unit test

**Tutti questi significano: Cancella il codice. Ricomincia con TDD.**

---

## Coverage Target

| Scope | Target | Note |
|-------|--------|------|
| Globale progetto | >= 70% linee | Soglia minima, non obiettivo |
| Feature nuova | >= 80% linee | Standard piu' alto per codice nuovo |
| Bug fix | Test di regressione obbligatorio | Il test che riproduce il bug, poi il fix |

Il test di regressione per un bug fix segue esattamente il ciclo TDD:
1. **RED:** Scrivi il test che riproduce il bug. Deve fallire.
2. **GREEN:** Correggi il bug. Il test passa.
3. **REFACTOR:** Pulisci se necessario.

Il test garantisce che il bug non tornera' mai.

---

## Checklist di Verifica

Prima di dichiarare il lavoro completato:

- [ ] Il test e' stato scritto PRIMA del codice?
- [ ] Il test ha fallito (RED) prima dell'implementazione?
- [ ] Il codice implementato e' il MINIMO necessario?
- [ ] Tutti i test passano (GREEN)?
- [ ] Il refactoring non ha rotto nessun test?
- [ ] Il commit contiene sia test che implementazione?
- [ ] La coverage e' >= 70% (>= 80% per feature nuove)?
- [ ] Ogni bug fix ha il suo test di regressione?
- [ ] I test usano codice reale (mock solo se inevitabile)?
- [ ] I nomi dei test descrivono il comportamento, non l'implementazione?

**Non riesci a spuntare tutte le caselle? Hai saltato il TDD. Ricomincia.**

---

## Quando sei bloccato

| Problema | Soluzione |
|----------|-----------|
| Non sai come testare | Scrivi l'API che vorresti usare. Scrivi l'assert prima. Chiedi al tuo partner umano. |
| Test troppo complicato | Il design e' troppo complicato. Semplifica l'interfaccia. |
| Devi mockare tutto | Il codice e' troppo accoppiato. Usa dependency injection. |
| Setup del test enorme | Estrai helper. Ancora complesso? Semplifica il design. |

---

## Regola Finale

```
Codice di produzione → esiste un test che ha fallito prima
Altrimenti → non e' TDD
```

Nessuna eccezione senza il permesso esplicito del tuo partner umano.

---

## Tecniche di Supporto

- **[testing-anti-patterns.md](testing-anti-patterns.md)** — 5 anti-pattern comuni nei test (mock sbagliati, metodi test-only nel codice di produzione, mock incompleti). Da leggere quando aggiungi mock o utility di test.

- **[condition-based-waiting.md](condition-based-waiting.md)** — Elimina test flaky da `setTimeout` fissi. Pattern `waitFor()` per TypeScript, Python e Java (Awaitility). Da applicare quando un test fallisce sporadicamente in CI o usa sleep arbitrari.
