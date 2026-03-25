# ADR — Migrazione Standard Diagrammi da Mermaid a PlantUML

> **Data:** 2026-03-25
> **Stato:** Approvato
> **Autore:** SIAE AI Competence Center
> **PR:** #139

---

## Contesto

Il plugin DevForge utilizzava Mermaid come formato esclusivo per i diagrammi in tutte le skill, template e agent. La decisione di migrare a PlantUML nasce dalla necessita' della factory di sviluppo OT di avere diagrammi UML formali, con supporto completo per class diagram, state machine, timing diagram e notazione C4 strutturata.

## Decisione

Adottare **PlantUML** come formato esclusivo per tutti i diagrammi generati dal plugin DevForge.

## Alternative valutate

| Alternativa | Pro | Contro | Esito |
|-------------|-----|--------|-------|
| **Mermaid (status quo)** | Rendering nativo GitHub/Confluence, zero setup | UML limitato, no class diagram formale, no state machine dettagliate | Scartato |
| **PlantUML** | UML completo, C4 stdlib ufficiale, rendering offline con stdlib locale | Richiede renderer esterno (VS Code plugin o CLI) | **Scelto** |
| **D2** | Sintassi moderna, layout automatico | Ecosistema immaturo, nessuna adozione SIAE | Scartato |
| **Structurizr DSL** | Specifico per C4 | Troppo specifico, non copre ER/sequence/class | Scartato |

## Criteri di scelta

1. **Completezza UML**: PlantUML supporta tutti i tipi di diagramma necessari (C4, sequence, class, ER, activity, state, deployment)
2. **Offline support**: la stdlib C4 e' inclusa in PlantUML >= 1.2020.14, funziona senza rete
3. **Tooling**: plugin VS Code (jebbs.plantuml), CLI (`plantuml file.puml -tsvg`), server online
4. **Adozione factory**: richiesta esplicita della factory OT per diagrammi formali

## Scope della migrazione

- **15 file modificati**: skill, agent, commands, templates, README, CODEBASE_MAP
- **16 blocchi diagramma** convertiti da Mermaid a PlantUML
- **Enforcement centralizzato** in `using-devforge/SKILL.md` (caricato in ogni sessione)
- **Enforcement distribuito** in `siae-architecture`, `siae-documentation`, `doc-generator`

## Eccezione documentata

I flowchart di processo interni alle skill (```` ```dot ```` / Graphviz) sono accettati per rappresentare flussi decisionali del plugin stesso. Non sono output utente e non rientrano nella policy PlantUML.

## Rendering

- **VS Code**: estensione "PlantUML" (jebbs.plantuml)
- **CLI**: `plantuml docs/diagrams/*.puml -tsvg`
- **Online**: https://www.plantuml.com/plantuml/uml
- **Versione minima**: PlantUML >= 1.2020.14 (per stdlib C4)
