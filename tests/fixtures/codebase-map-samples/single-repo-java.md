---
last_mapped: 2026-05-01T10:00:00Z
total_files: 42
stack:
  - java
  - maven
---

# Codebase Map — sample-java

> Mono-module Maven project. Single root, no sub-packages.

## Panoramica Sistema

Servizio REST Spring Boot 3.x esposto su porta 8080. Single-module Maven con
package `com.siae.sample`. Persistenza PostgreSQL via Spring Data JPA. Build
gestita con Maven 3.9.

## Stack

- Java 21 (Temurin)
- Spring Boot 3.2
- Maven 3.9
- PostgreSQL 15

## Convenzioni SIAE Osservate

- Naming: `*Service`, `*Repository`, `*Controller`
- Logging: SLF4J + Logback JSON
- Test: JUnit 5 + Mockito
- Coverage minima: 70%

## Gotcha

- `application-prod.yml` non versionato (parametri tramite Vault)
- Test Testcontainers richiede Docker daemon attivo

## Guida Moduli

### sample-service

**Path:** .
**Stack:** Java 21 + Spring Boot 3.2
**Description:** Modulo unico, root del progetto Maven.

## Navigation Guide

Entry point: `src/main/java/com/siae/sample/Application.java`.
