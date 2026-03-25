# Template — docs/SYSTEM_MAP.md

Copia questo template come output del Phase 5. Sostituisci tutti i placeholder `{...}`.

---

```markdown
---
last_mapped: {YYYY-MM-DDTHH:MM:SSZ}
system: {SYSTEM_NAME}
org: {ORG}
pattern: {PATTERN}
total_repos: {N}
mapped_repos: {N}
unverified_edges: {N}
generated_by: siae-microservices-map
---

# System Map — {SYSTEM_NAME}

> AVVISO ANTI-ALLUCINAZIONE: Ogni relazione in questo documento e' supportata da
> evidenza citata (file sorgente + riga). Le relazioni marcate [UNVERIFIED] sono
> ipotesi non provate da codice. Non rimuovere i gap: sono informazione preziosa.
> Aggiornato il: {data}. Non usare questa mappa come fonte di verita' dopo 90 giorni
> senza re-esecuzione della skill.

## C4 — System Context

```plantuml
@startuml C4_SystemContext
!include <C4_Context>

title System Context — SYSTEM_NAME

System(system_id, "SYSTEM_NAME", "descrizione sistema")
System_Ext(ext_1, "Sistema Esterno 1", "descrizione")
Rel(system_id, ext_1, "relazione", "protocollo")
@enduml
```

> **Nota:** sostituire `SYSTEM_NAME`, `system_id`, `ext_1` e le descrizioni con i valori reali del progetto prima del rendering.

## C4 — Container Diagram

```plantuml
@startuml C4_ContainerDiagram
!include <C4_Container>

title Container Diagram — SYSTEM_NAME

Container(svc_1, "nome-repo-1", "Stack", "Scopo")
Container(svc_2, "nome-repo-2", "Stack", "Scopo")
Container(svc_X, "nome-repo-X", "Stack", "Scopo")
Container(svc_Y, "nome-repo-Y", "Stack", "Scopo")

Rel(svc_1, svc_2, "path chiamata", "REST [CONFIRMED — DirittiClient.java:8]")
Rel(svc_1, svc_2, "topic", "Kafka [CONFIRMED — AutoreService.java:45]")
Rel(svc_X, svc_Y, "path", "REST [UNVERIFIED]")
@enduml
```

> **Nota:** sostituire `svc_1`, `svc_2`, `svc_X`, `svc_Y` e le descrizioni con i valori reali. Aggiungere `Container()` per ogni servizio prima di usarlo nelle `Rel()`.

## Dependency Graph

| From | To | Tipo | Confidence | Fonte |
|------|----|------|-----------|-------|
| {repo-A} | {repo-B} | REST GET | CONFIRMED | {path/file.java:riga} |
| {repo-C} | {repo-D} | REST POST | INFERRED | {application.yml:chiave} |
| {repo-X} | {repo-Y} | REST | UNVERIFIED | nessuna evidenza trovata |

## Kafka Topic Map

| Topic | Publisher | Fonte Publisher | Consumer | Fonte Consumer |
|-------|-----------|-----------------|----------|----------------|
| {topic.nome} | {repo-A} | {Service.java:45} | {repo-B} | {application.yml:topics} |
| {topic.altro} | {repo-C} | {Emitter.java:12} | [UNVERIFIED] | nessun consumer trovato |

## Database Inventory

| Repo | DB Type | DB Name / Schema | Confidence | Fonte |
|------|---------|-----------------|-----------|-------|
| {repo-A} | PostgreSQL | {nome_db} | INFERRED | {application.yml:spring.datasource.url} |
| {repo-B} | MongoDB | {nome_db} | CONFIRMED | {MongoConfig.java:22} |

## Service Inventory

| Repo | Stack | API Esposta | Stato Mapping |
|------|-------|-------------|---------------|
| {repo-A} | Java Spring Boot | /api/v1/{resource} | MAPPED |
| {repo-B} | Node.js Express | /api/{resource} | MAPPED |
| {repo-X} | Unknown | Sconosciuta | FILE_NOT_FOUND |

## Gap Report

> Queste relazioni NON sono verificate da codice. Investigare prima di usarle
> per decisioni architetturali.

- [ ] `{repo-X} → {repo-Y}`: nessun Feign client ne' config URL trovati. Possibile chiamata diretta a DB?
- [ ] `{repo-Z}`: nessun file accessibile — repo vuoto, privato, o archiviato non rilevato
- [ ] Topic `{nome.topic}`: publisher identificato ma nessun consumer trovato nei {N} repo analizzati
- [ ] {N} repo non hanno openapi spec — API pubbliche sconosciute

## Evidence Index

Ogni relazione CONFIRMED con path esatto per riprodurre l'evidenza:

| Edge | File | Riga | Tipo Evidenza |
|------|------|------|---------------|
| {repo-A} → {repo-B} | `src/main/java/.../DirittiClient.java` | 8 | FeignClient annotation |
| {repo-A} pubblica `autori.creato` | `src/main/java/.../AutoreService.java` | 45 | KafkaTemplate.send() |
| {repo-B} consuma `autori.creato` | `src/main/resources/application.yml` | spring.kafka.consumer.topics | Config |
```
