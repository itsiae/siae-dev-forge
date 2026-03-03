# C4 Diagram Templates — Mermaid

Template Mermaid per ciascun livello del modello C4.
Sostituire i placeholder `[...]` con i dati reali del progetto.

---

## Livello 1 — System Context

Mostra il sistema nel suo contesto: attori umani e sistemi esterni con cui interagisce.

```mermaid
graph TB
    User["[Persona]<br/>[Ruolo/Descrizione]"]
    ExtSystem["[Sistema Esterno]<br/>[Descrizione breve]"]

    System["[Nome Sistema]<br/>[Descrizione breve]"]

    User -->|"[Azione/Relazione]"| System
    System -->|"[Azione/Relazione]"| ExtSystem

    style User fill:#08427b,color:#fff
    style System fill:#1168bd,color:#fff
    style ExtSystem fill:#999999,color:#fff
```

### Legenda colori Context

| Colore   | Significato                |
|----------|----------------------------|
| `#08427b`| Persona / Attore            |
| `#1168bd`| Sistema in scope            |
| `#999999`| Sistema esterno (fuori scope)|

---

## Livello 2 — Container

Mostra i container (applicazioni, database, code unit deployabili) dentro il sistema.

```mermaid
graph TB
    User["[Persona]<br/>[Ruolo]"]

    subgraph System ["[Nome Sistema]"]
        WebApp["[Web App]<br/>[Vue.js 3, S3+CloudFront]"]
        API["[API Service]<br/>[Spring Boot / Lambda]"]
        DB[("[Database]<br/>[PostgreSQL RDS]")]
        Queue["[Message Queue]<br/>[SQS]"]
    end

    ExtSystem["[Sistema Esterno]"]

    User -->|"HTTPS"| WebApp
    WebApp -->|"REST/JSON"| API
    API -->|"SQL"| DB
    API -->|"Publish"| Queue
    Queue -->|"Consume"| ExtSystem

    style User fill:#08427b,color:#fff
    style WebApp fill:#438dd5,color:#fff
    style API fill:#438dd5,color:#fff
    style DB fill:#438dd5,color:#fff
    style Queue fill:#438dd5,color:#fff
    style ExtSystem fill:#999999,color:#fff
```

### Legenda colori Container

| Colore   | Significato                |
|----------|----------------------------|
| `#08427b`| Persona / Attore            |
| `#438dd5`| Container dentro il sistema |
| `#999999`| Sistema esterno             |

---

## Livello 3 — Component

Mostra i componenti interni di un singolo container.

```mermaid
graph TB
    subgraph Container ["[Nome Container] — Componenti"]
        Controller["[Controller Layer]<br/>REST endpoints, validation"]
        Service["[Service Layer]<br/>Business logic, orchestration"]
        Repository["[Repository Layer]<br/>Data access, ORM"]
        Client["[External Client]<br/>HTTP client per sistemi esterni"]
    end

    DB[("[Database]")]
    ExtAPI["[API Esterna]"]

    Controller -->|"Chiama"| Service
    Service -->|"Chiama"| Repository
    Service -->|"Chiama"| Client
    Repository -->|"SQL"| DB
    Client -->|"HTTPS"| ExtAPI

    style Controller fill:#85bbf0,color:#000
    style Service fill:#85bbf0,color:#000
    style Repository fill:#85bbf0,color:#000
    style Client fill:#85bbf0,color:#000
    style DB fill:#438dd5,color:#fff
    style ExtAPI fill:#999999,color:#fff
```

### Legenda colori Component

| Colore   | Significato                      |
|----------|-----------------------------------|
| `#85bbf0`| Componente dentro il container    |
| `#438dd5`| Altro container dello stesso sistema|
| `#999999`| Sistema/servizio esterno          |

---

## Livello 4 — Code

Mostra classi, interfacce e relazioni all'interno di un componente.
Usare class diagram Mermaid.

```mermaid
classDiagram
    class IServiceInterface {
        <<interface>>
        +execute(request: Request) Response
        +validate(input: Input) boolean
    }

    class ServiceImpl {
        -repository: IRepository
        -client: IExternalClient
        +execute(request: Request) Response
        +validate(input: Input) boolean
        -transformData(raw: RawData) ProcessedData
    }

    class IRepository {
        <<interface>>
        +findById(id: String) Entity
        +save(entity: Entity) void
        +findAll(filter: Filter) List~Entity~
    }

    class RepositoryImpl {
        -dataSource: DataSource
        +findById(id: String) Entity
        +save(entity: Entity) void
        +findAll(filter: Filter) List~Entity~
    }

    class RequestDTO {
        +id: String
        +payload: Map
        +timestamp: DateTime
    }

    class ResponseDTO {
        +status: String
        +data: Object
        +errors: List~Error~
    }

    IServiceInterface <|.. ServiceImpl : implements
    IRepository <|.. RepositoryImpl : implements
    ServiceImpl --> IRepository : uses
    ServiceImpl ..> RequestDTO : receives
    ServiceImpl ..> ResponseDTO : returns
```

### Quando usare il Livello 4

- Documentazione tecnica approfondita
- Onboarding di nuovi sviluppatori su un modulo specifico
- Code review architetturale
- Identificazione di accoppiamento o violazioni di layering

> **Nota:** il Livello 4 non e' richiesto per ogni componente. Usarlo solo
> dove il design delle classi non e' ovvio dalla struttura del codice.

---

## Convenzioni generali

1. **Un diagramma per livello** — non mischiare livelli nello stesso grafico
2. **Titoli espliciti** — ogni nodo deve avere nome + tecnologia/ruolo
3. **Frecce etichettate** — indicare protocollo o tipo di relazione
4. **Colori consistenti** — usare la legenda del livello corrispondente
5. **Scope chiaro** — il livello N+1 e' lo zoom di un singolo elemento del livello N
