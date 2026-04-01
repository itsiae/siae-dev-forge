# Scenario B — Manutenzione
# Scenario D — Refactor / Best Practice Retrofit

---

## SCENARIO B — Manutenzione

### B.1 Sequenza operativa

1. Leggi il file .robot e il Page resource coinvolto
2. Se c'è errore attivo → segui `reference/debug-engine.md` (Scenario E)
3. Se la modifica riguarda la logica (senza errore) → modifica preservando la struttura
4. Verifica che la modifica non introduca anti-pattern → applica BP-1..6
5. Se il locatore è rotto → esegui Knowledge Acquisition per trovare il nuovo locatore

### B.3 Sub-workflow: locatore rotto noto (senza errore attivo)

Se il QA engineer dice "aggiorna il locatore di X perché è cambiato con la nuova release" ma
non c'è stack trace (altrimenti sarebbe Scenario E):

1. **Non scrivere il nuovo locatore a memoria** — dichiara subito LOCATORE MANCANTE
2. Esegui Knowledge Acquisition per la pagina coinvolta (vedi `reference/dump-acquisition.md`)
3. Confronta il dump fresco con il locatore corrente nel Page resource
4. Aggiorna il locatore nel Page resource — rispetta la gerarchia BP-1
5. Verifica che non ci siano altri file che usano lo stesso locatore (cerca nel codebase)
6. Applica pre-flight card 🟡 prima della modifica

```
LOCATORE DA AGGIORNARE: ${LOGIN_SUBMIT_BUTTON}
Motivo: nuova release app — elemento rinominato
Azione: acquisizione dump per LoginPage tramite reference/dump-acquisition.md
```

**Non procedere senza dump** anche in questo caso: un locatore scritto a memoria è un bug silenzioso.

---

### B.2 Regola di conservazione

In manutenzione non toccare ciò che non è nel perimetro della modifica richiesta.

**Eccezione:** se durante la lettura trovi un anti-pattern critico (credenziali hardcoded,
Sleep senza commento, xpath posizionale), segnalalo come warning separato ma non modificarlo
automaticamente. Proponi come issue distinta:

```
⚠️ WARNING (fuori perimetro): trovato <tipo anti-pattern> in <file>:<riga>
Proposta: correggere in sessione separata per non mescolare scope.
```

---

## SCENARIO D — Refactor / Best Practice Retrofit

### D.1 Audit checklist — esegui su ogni file prima di modificare

**STRUTTURA**
- [ ] Ordine sezioni: Settings → Variables → Keywords (in resource) / Test Cases (in .robot)
- [ ] Nessuna logica di test in file .resource
- [ ] Nessuna keyword nei file .robot — solo nei Page resource

**NAMING**
- [ ] File .robot: `TCxx_NomeCamelCase.robot`
- [ ] File resource: `NomePaginaPage.resource`
- [ ] Locatori: `${PAGENAME_ELEMENT_DESCRIZIONE}` in UPPERCASE
- [ ] Keywords: Title Case Con Spazi

**LOCATORI**
- [ ] Nessuna coordinata XY esplicita
- [ ] Nessun xpath posizionale (`//LinearLayout[3]`)
- [ ] Nessun xpath con indice numerico senza attributo semantico (`(//Button)[2]`)
- [ ] Gerarchia rispettata: `accessibility_id` > `resource-id` > `xpath semantico`

**KEYWORDS**
- [ ] `[Documentation]` presente su ogni keyword con >2 step o argomenti
- [ ] `[Arguments]` con nomi descrittivi (non `${arg1}`, `${arg2}`)
- [ ] Nessuna chiamata AppiumLibrary diretta — solo wrapper da `common.resource`
- [ ] `RETURN` invece di `[Return]` (RF 5+)

**TEST CASES**
- [ ] `[Documentation]` presente su ogni test case
- [ ] `[Tags]` presente su ogni test case (tipo + feature + platform)
- [ ] Suite Setup/Teardown per open/close app
- [ ] Test Setup/Teardown per reset stato / screenshot su failure
- [ ] Nessuna credenziale hardcoded

**ANTI-PATTERN**
- [ ] Nessun `Sleep` senza commento esplicito motivato
- [ ] Nessun import incrociato tra Page resource
- [ ] Nessun locatore duplicato tra resource diversi

### D.2 Priorità di intervento

Applica le correzioni in questo ordine:

1. Anti-pattern critici (credenziali hardcoded, import incrociati) — correggi subito
2. Locatori non conformi — correggi con Knowledge Acquisition se necessario
3. Naming — rinomina in modo consistente
4. Documentazione mancante — aggiungi
5. Struttura sezioni — riordina

### D.3 Tipi di keyword nei Page resource

| Prefisso | Tipo | Comportamento |
|----------|------|---------------|
| `Assert*` | Verifica | Solo verifica stato UI, nessuna azione |
| `*Input* / *Select* / *Tap*` | Azione atomica | Azione su singolo elemento |
| `Perform* / Execute* / Complete*` | Composita | Chiama Assert + Action |

**Vietato nei Page resource:**
- Logica condizionale complessa (IF/ELSE annidati)
- Chiamate dirette AppiumLibrary (usa wrapper da common.resource)
- Import di altri Page resource
