# LLD — [Nome Componente/Feature]

> **HLD di riferimento**: [link]
> **Data**: YYYY-MM-DD
> **Autore**: [nome]

---

## 1. Scope
[Cosa copre questo LLD]

## 2. Data Model
[Entita', relazioni, schema DB]

```plantuml
@startuml DataModel
skinparam defaultFontName Arial
skinparam shadowing false

entity "ENTITY_A" as A {
    *id : STRING <<PK>>
    --
    name : STRING
    created_at : DATETIME
}

entity "ENTITY_B" as B {
    *id : STRING <<PK>>
    --
    entity_a_id : STRING <<FK>>
}

A ||--o{ B : has
@enduml
```

## 3. API Contract
[Endpoint, request/response, status codes]

## 4. Sequence Diagram — Flusso Principale

```plantuml
@startuml SequenceFlusso
skinparam defaultFontName Arial
skinparam shadowing false

actor Client
participant API
database DB

Client -> API : POST /resource
activate API
API -> DB : INSERT
activate DB
DB --> API : OK
deactivate DB
API --> Client : 201 Created
deactivate API
@enduml
```

## 5. Error Handling
| Scenario | HTTP Code | Messaggio | Azione |
|----------|-----------|-----------|--------|

## 6. Configurazione
[Environment variables, feature flags, external config]

## 7. Test Plan
| Tipo | Cosa testa | Framework |
|------|-----------|-----------|
| Unit | Business logic | JUnit5/vitest/pytest |
| Integration | API + DB | TestContainers/supertest |
| E2E | Flusso completo | Playwright/Cypress |
