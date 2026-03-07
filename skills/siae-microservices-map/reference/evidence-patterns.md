# Pattern Evidenza per Stack — siae-microservices-map

Guida per i subagent: dove cercare le evidenze di dipendenza per ogni stack.

---

## Java Spring Boot

### Chi chiama chi (REST)

| Pattern Codice | File Tipico | Confidence |
|----------------|-------------|-----------|
| `@FeignClient(name = "sport-X", url = "${sport.x.url}")` | `src/main/java/**/client/*Client.java` | CONFIRMED |
| `restTemplate.getForObject("http://sport-X/..."` | `src/main/java/**/service/*.java` | CONFIRMED |
| `webClient.get().uri("http://sport-X/..."` | `src/main/java/**/service/*.java` | CONFIRMED |
| `${sport.x.url}` in application.yml | `application.yml` | INFERRED — URL variabile |
| `spring.cloud.openfeign.client.config.sport-x.url` | `application.yml` | INFERRED |

### Kafka

| Pattern | File Tipico | Confidence |
|---------|-------------|-----------|
| `@KafkaListener(topics = "nome.topic")` | `src/main/java/**/listener/*.java` | CONFIRMED |
| `kafkaTemplate.send("nome.topic", ...)` | `src/main/java/**/service/*.java` | CONFIRMED |
| `spring.kafka.consumer.topics=nome.topic` | `application.yml` | CONFIRMED |
| `@SendTo("nome.topic")` | qualsiasi classe | CONFIRMED |

### Database

| Pattern | File Tipico | Confidence |
|---------|-------------|-----------|
| `spring.datasource.url=jdbc:postgresql://.../{db_name}` | `application.yml` | INFERRED |
| `spring.data.mongodb.uri=mongodb://.../{db_name}` | `application.yml` | INFERRED |
| `@Entity` + `@Table(name="...")` | entita' JPA | CONFIRMED (schema locale) |

### API Esposta

| Pattern | File | Confidence |
|---------|------|-----------|
| `@RestController` + `@RequestMapping("/api/v1/...")` | controller | CONFIRMED |
| `openapi.yaml` / `swagger.yaml` | radice repo | CONFIRMED |
| `@Tag(name="...")` in Swagger annotations | controller | CONFIRMED |

---

## Node.js / TypeScript

### Chi chiama chi (REST)

| Pattern | File Tipico | Confidence |
|---------|-------------|-----------|
| `axios.get('http://sport-X/...')` | `src/services/*.ts` | CONFIRMED |
| `fetch('http://sport-X/...')` | qualsiasi file | CONFIRMED |
| `SPORT_X_URL=http://sport-X` in `.env` | `.env.example` | INFERRED |
| `process.env.SPORT_X_URL` in codice | qualsiasi file | INFERRED |

### Kafka / Event Bus

| Pattern | File | Confidence |
|---------|------|-----------|
| `consumer.subscribe(['nome.topic'])` | `src/kafka/*.ts` | CONFIRMED |
| `producer.send({ topic: 'nome.topic' })` | qualsiasi file | CONFIRMED |
| `KAFKA_TOPICS=nome.topic` | `.env.example` | CONFIRMED |

---

## Python

### Chi chiama chi (REST)

| Pattern | File Tipico | Confidence |
|---------|-------------|-----------|
| `requests.get('http://sport-X/...')` | qualsiasi `.py` | CONFIRMED |
| `httpx.get('http://sport-X/...')` | qualsiasi `.py` | CONFIRMED |
| `SPORT_X_URL=http://sport-X` | `.env` / `config.py` | INFERRED |

### Kafka

| Pattern | File | Confidence |
|---------|------|-----------|
| `consumer = KafkaConsumer('nome.topic'` | qualsiasi `.py` | CONFIRMED |
| `producer.send('nome.topic'` | qualsiasi `.py` | CONFIRMED |

---

## File NON Validi come Fonte

| File | Perche' NON valido |
|------|--------------------|
| `README.md` | Documentazione aspirazionale, spesso obsoleta |
| `CHANGELOG.md` | Storia, non stato attuale |
| `docs/*.md` | Documentazione manuale, non contratto |
| `.github/workflows/*.yml` | Pipeline CI/CD, non topologia runtime |
| Commenti nel codice | Non eseguiti, possono essere obsoleti |
| Qualsiasi file non nel repo corrente | Non e' evidenza di quel repo |

---

## Gestione Casi Edge

### URL Dinamici (INFERRED)

Quando una chiamata usa variabili invece di URL hardcoded:
```java
restTemplate.getForObject(sportXUrl + "/api/endpoint", ...)
// dove sportXUrl e' da @Value("${sport.x.url}")
```

Traccia il valore in `application.yml`. Se l'URL risolve a un repo noto → `[INFERRED]`.
Se non risolve → `[UNVERIFIED]` con nota "URL dinamico non tracciato".

### Service Discovery (Eureka/Consul)

Quando un servizio usa service discovery invece di URL statici:
```java
@FeignClient(name = "sport-anagrafe")  // senza url= esplicito
```

Il target e' il service name registrato in Eureka/Consul. Cerca `spring.application.name`
nel repo target. Se corrisponde → `[CONFIRMED]`. Se non trovi conferma → `[INFERRED]`.

### Config Server Centralizzato

Se il sistema usa Spring Cloud Config Server, i file `application.yml` locali
potrebbero non contenere i valori reali (sono in un repo separato di config).
Nota nel Gap Report: "Config da Config Server esterno — valori runtime non verificabili".
