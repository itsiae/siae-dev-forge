---
name: siae-documentation
description: >
  Genera documentazione tecnica per componenti e API SIAE.
  Trigger: richiesta documentazione, /forge-doc, design review, pre-release.
---

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  Documentation                      ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 7. Release

---

> 📊 **Dai repo itsiae:** Servizi senza HLD/LLD richiedono in media 4.7h di knowledge transfer orale per ogni nuovo developer.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## 1. Tipi di Documentazione

### 1.1 HLD (High Level Design)

Visione d'insieme del sistema. Risponde a: "come funziona il sistema e perche' e' fatto cosi'?"

| Contenuto                   | Dettaglio                                              |
|-----------------------------|--------------------------------------------------------|
| Contesto e obiettivi        | Problema risolto, value proposition                    |
| C4 Livello 1 (Context)     | Sistema + attori esterni + sistemi adiacenti           |
| C4 Livello 2 (Container)   | Applicazioni, DB, broker, deployment unit              |
| Decisioni architetturali    | ADR-style: decisione, motivazione, alternative scartate|
| Requisiti Non Funzionali    | Performance, availability, scalability con target      |
| Rischi e mitigazioni        | Probabilita', impatto, piano di mitigazione            |

> Template: `template/hld-template.md`

Template path: `${SKILL_DIR}/template/hld-template.md` (relativo alla directory della skill)

### 1.2 LLD (Low Level Design)

Dettaglio implementativo di un componente o feature. Risponde a: "come si implementa concretamente?"

| Contenuto            | Dettaglio                                              |
|----------------------|--------------------------------------------------------|
| Data model           | Entita', relazioni, schema DB (diagramma ER PlantUML)  |
| Sequence diagram     | Flusso principale e flussi alternativi                 |
| API contract         | Endpoint, request/response, status code                |
| Error handling       | Scenari di errore, codici, messaggi, azioni            |
| Configurazione       | Env vars, feature flags, config esterne                |
| Test plan            | Unit, integration, E2E con framework                   |

> Template: `template/lld-template.md`

Template path: `${SKILL_DIR}/template/lld-template.md` (relativo alla directory della skill)

### 1.3 API Documentation

Documentazione endpoint REST/GraphQL. Segue struttura OpenAPI 3.x.

| Contenuto            | Dettaglio                                              |
|----------------------|--------------------------------------------------------|
| Base URL e versioning| URL pattern, strategia di versionamento                |
| Autenticazione       | Auth flow, header format, token lifecycle              |
| Endpoint reference   | Metodo, path, parametri, body, response                |
| Error codes          | Status HTTP, codice applicativo, descrizione           |
| Esempi               | Request/response completi, cURL                        |

> Template: `template/api-doc-template.md`

Template path: `${SKILL_DIR}/template/api-doc-template.md` (relativo alla directory della skill)

---

## 2. Quando Usare Cosa

| Scenario                                | Documento       |
|-----------------------------------------|-----------------|
| Nuovo sistema o servizio                | **HLD**         |
| Implementazione feature complessa       | **LLD**         |
| Endpoint REST o GraphQL                 | **API doc**     |
| Greenfield project                      | **Tutti e 3**   |

Regola pratica:
- Se stai decidendo **cosa costruire** e **come si collega** → HLD
- Se stai decidendo **come costruirlo nel dettaglio** → LLD
- Se stai documentando **come usarlo dall'esterno** → API doc

---

## 3. Formato Output

Tutto l'output e' in **Markdown** con diagrammi **PlantUML**.

| Elemento             | Formato                                                |
|----------------------|--------------------------------------------------------|
| Testo                | Markdown standard (GFM)                                |
| Diagrammi            | PlantUML (file .puml in docs/diagrams/)                |
| Tabelle              | Markdown table con header                              |
| Code snippet         | Fenced code block con language tag                     |

---

## 4. Pubblicazione Confluence (opzionale)

Se MCP Atlassian e' disponibile, la documentazione puo' essere pubblicata direttamente su Confluence.

**Prerequisiti:**
- L'utente deve specificare **Space** e **Parent Page**
- MCP Atlassian deve essere connesso e funzionante

**Flusso:**

1. Genera il documento in Markdown
2. Mostra anteprima all'utente
3. Pre-flight card 🟡 MEDIO prima di scrivere il file su disco:

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-documentation |
|:---|
| 📝 Documento: `<tipo: HLD / LLD / API doc>` |
| **▼ Azione** |
| 1. ✏️ Azione: Scrittura file Markdown → `docs/<nome-file>.md` |
| 💡 Perche': Crea o sovrascrive il file di documentazione su disco |
| 🚫 Se NO: Il documento resta solo in chat — non salvato su disco |

4. Pre-flight card 🔴 ALTO prima della pubblicazione su Confluence:

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-documentation |
|:---|
| **⚠️ OPERAZIONE DIFFICILE DA ANNULLARE** |
| 📚 Space: `{space}` · 📄 Parent: `{parent-page}` |
| **▼ Azione** |
| 1. 📤 Azione: Pubblicazione pagina su Confluence → `Space/{space} Parent/{parent-page}` |
| 💡 Perche': Crea/aggiorna pagina visibile a tutto il team |
| 🚫 Se NO: Il documento resta solo in locale (Markdown) |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

4. Pubblica via `createConfluencePage` o `updateConfluencePage`

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| File modificati per singolo step | 5 | Se devi toccare piu' file, decomponi in sub-task. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue, non lista esaustiva. |

---

```
REQUIRED SUB-SKILL: siae-verification
```
Invoca `siae-verification` prima di dichiarare la documentazione completa.

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Il codice e' la documentazione" | Il codice dice come. La doc dice perche'. Sono complementari. |
| "La aggiorneremo dopo il rilascio" | Dopo il rilascio il team passa alla feature successiva. Non si aggiorna mai. |
| "Il team sa gia' come funziona" | Il team cambia. I nuovi arrivati non sanno nulla. |
| "L'HLD e' eccessivo per questa feature" | L'HLD e' un investimento. La mancanza di contesto e' un costo. |
| "Confluence e' sempre stale" | Confluence stale e' meglio di nessuna doc. Aggiornala prima del rilascio. |
| "I developer non leggono la doc" | I developer leggono la doc quando sono bloccati. Assicurati che esista. |
| "OpenAPI si genera automaticamente" | Generata != accurata. Rivedi sempre le descrizioni generate. |

---

## 5. Classificazione Rischio Operazioni

| Operazione                        | Rischio | Card               |
|-----------------------------------|---------|--------------------|
| Generazione documento (locale)    | 🟢 SICURO | Nessuna card     |
| Scrittura file Markdown su disco  | 🟡 MEDIO  | Card gialla      |
| Pubblicazione su Confluence       | 🔴 ALTO   | Card rossa       |
| Aggiornamento pagina esistente    | 🔴 ALTO   | Card rossa       |

---

## Permission Denied Handling

**Se Write viene negato (scrittura documento su disco):**
1. Presenta il documento completo come output testuale formattato in chat
2. Indica il path suggerito (es. `docs/hld-<progetto>.md`, `docs/lld-<feature>.md`)
3. L'utente puo' copiare il contenuto manualmente nel file
4. Se anche la pubblicazione Confluence e' richiesta, fornisci il contenuto pronto per copia

**Fasi completabili senza permessi:** generazione documento (analisi codebase con Read/Grep), diagrammi PlantUML
**Fasi che richiedono permessi:** Write (salvataggio file), MCP Atlassian (pubblicazione Confluence)

Se i permessi sono negati:
1. Completa la generazione del documento
2. Presenta il contenuto completo in chat
3. NON entrare in loop di retry su tool negato
4. NON dichiarare completamento per fasi non eseguite

---

## 6. Vincoli

1. **Ogni HLD include diagramma C4** — almeno Livello 1 (Context), in PlantUML
2. **Ogni LLD include sequence diagram** — flusso principale, in PlantUML
3. **API doc segue OpenAPI 3.x** — struttura, naming, status code standard
4. **Nessun placeholder generico** — niente "TBD", "TODO", "da definire".
   Se un'informazione non e' disponibile, ometti la sezione. Non inventare.
5. **Diagrammi solo PlantUML** — nei documenti Markdown: blocchi ` ```plantuml ` inline.
   Per rendering standalone: file `.puml` in `docs/diagrams/`. **MAI usare Mermaid.**
6. **Template obbligatori** — usa i template in `template/` come base.
   Puoi aggiungere sezioni, non rimuoverle.
