---
name: siae-documentation
description: >
  Use when technical documentation is needed for a SIAE component or API.
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

---

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

### 1.2 LLD (Low Level Design)

Dettaglio implementativo di un componente o feature. Risponde a: "come si implementa concretamente?"

| Contenuto            | Dettaglio                                              |
|----------------------|--------------------------------------------------------|
| Data model           | Entita', relazioni, schema DB (diagramma ER Mermaid)   |
| Sequence diagram     | Flusso principale e flussi alternativi                 |
| API contract         | Endpoint, request/response, status code                |
| Error handling       | Scenari di errore, codici, messaggi, azioni            |
| Configurazione       | Env vars, feature flags, config esterne                |
| Test plan            | Unit, integration, E2E con framework                   |

> Template: `template/lld-template.md`

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

Tutto l'output e' in **Markdown** con diagrammi **Mermaid**.

| Elemento             | Formato                                                |
|----------------------|--------------------------------------------------------|
| Testo                | Markdown standard (GFM)                                |
| Diagrammi            | Mermaid (renderizzabile in GitHub e Confluence)        |
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
3. Pre-flight card 🔴 ALTO prima della pubblicazione:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔨 DevForge — 🔴 RISCHIO ALTO  ·  1 operazione                  ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  1.  Azione:    Pubblicazione pagina su Confluence               ┃
┃      File/Path: Space/{space} Parent/{parent-page}               ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  Perche':       Crea/aggiorna pagina visibile a tutto il team    ┃
┃  Se NO:         Il documento resta solo in locale (Markdown)     ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  ⬆️  Leggi prima, poi decidi nella dialog qui sopra              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

4. Pubblica via `createConfluencePage` o `updateConfluencePage`

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

**Fasi completabili senza permessi:** generazione documento (analisi codebase con Read/Grep), diagrammi Mermaid
**Fasi che richiedono permessi:** Write (salvataggio file), MCP Atlassian (pubblicazione Confluence)

Se i permessi sono negati:
1. Completa la generazione del documento
2. Presenta il contenuto completo in chat
3. NON entrare in loop di retry su tool negato
4. NON dichiarare completamento per fasi non eseguite

---

## 6. Vincoli

1. **Ogni HLD include diagramma C4** — almeno Livello 1 (Context), in Mermaid
2. **Ogni LLD include sequence diagram** — flusso principale, in Mermaid
3. **API doc segue OpenAPI 3.x** — struttura, naming, status code standard
4. **Nessun placeholder generico** — niente "TBD", "TODO", "da definire".
   Se un'informazione non e' disponibile, ometti la sezione. Non inventare.
5. **Diagrammi solo Mermaid** — renderizzabili in GitHub e Confluence
6. **Template obbligatori** — usa i template in `template/` come base.
   Puoi aggiungere sezioni, non rimuoverle.
