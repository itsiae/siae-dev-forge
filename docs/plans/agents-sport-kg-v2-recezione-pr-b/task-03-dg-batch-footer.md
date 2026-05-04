# Task 03 — doc-generator: HLD swim lane Batch Schedulers + footer freshness

**Stato:** [PENDING]
**Dipende da:** Task 02
**Blocca:** Task 04

## Goal

Aggiungere alle istruzioni di generazione HLD due nuovi elementi: swim lane "Batch Schedulers" nel C4 Container diagram (popolata da BatchJob[]) e footer "Topologia osservata a..." dal envelope D1.

## File coinvolti

- `agents/doc-generator.md` — aggiungiamo nuove sotto-sezioni alle ISTRUZIONI OPERATIVE dell'agent (NON modifichiamo template HLD esterni, NON cerchiamo sezioni "Security"/"Domain rules" pre-esistenti — sono nei template `.md` esterni che l'agent usa per generare).

## Step 1 — Identifica posizione di inserimento nelle istruzioni operative

```bash
grep -n "Step 0\|Step 1\|Step 2\|Flusso Operativo\|HLD" agents/doc-generator.md | head -20
```

Output atteso: trova la struttura del flusso operativo dell'agent (Step 0 Tool Loading → Step 1 Capire la richiesta → ...). Le nuove sotto-sezioni vanno aggiunte come **nuovi Step** o sotto-sezioni del flusso operativo (es. dopo Step 0, o all'interno dello step di generazione HLD se esiste).

**Importante**: le sezioni "Batch Schedulers swim lane" e "Footer freshness" sono **istruzioni** che dicono all'agent COSA generare quando produce un HLD. Vanno scritte come istruzioni operative (imperative: "se trovi BatchJob, aggiungi swim lane..."), non come sezioni di un HLD esistente.

## Step 2 — TDD test pre-modifica

```bash
grep -c "Batch Schedulers\|batch_jobs\[\]" agents/doc-generator.md
```
Output atteso pre-modifica: 0

```bash
grep -c "Topologia osservata\|observed_at" agents/doc-generator.md
```
Output atteso pre-modifica: 0

## Step 3 — Aggiungi istruzioni "C4 Container — Batch Schedulers swim lane"

Aggiungi nelle istruzioni operative dell'agent (es. nuovo Step o sotto-sezione del flusso HLD generation), il seguente blocco di istruzioni:

```markdown
#### Swim lane "Batch Schedulers" (Onda 10)

Se il servizio target ha BatchJob (@Scheduled, cron, scheduler), aggiungi una
swim lane dedicata nel C4 Container diagram.

**Discovery**:
1. Chiama `mcp__sport-kg__describe_service(<service>)` ed estrai `batch_jobs[]`
   se presente
2. Se assente, chiama `mcp__sport-kg__find_batch_for_keyword(<service-domain>)`
   per discovery alternativa
3. Se entrambi vuoti, **OMETTI** la swim lane (no "nessun batch" in HLD —
   è rumore informativo)

**PlantUML pattern** (se BatchJob trovati):

```plantuml
@startuml
package "Batch Schedulers" as Batch <<scheduler>> {
    component "<batch_name_1>" as B1 <<@Scheduled>> {
        note right: cron: <cron_expr>
    }
    component "<batch_name_2>" as B2 <<@Scheduled>> {
        note right: cron: <cron_expr>
    }
}
Batch --> Service : triggers
@enduml
```

**Naming**: usa il nome esatto della classe Java/metodo `@Scheduled` da KG.
Cron expression nel `note right`.
```

## Step 4 — Aggiungi istruzioni "Footer freshness"

Aggiungi nelle istruzioni operative dell'agent (sezione adiacente a Step 3 o nelle istruzioni cover doc):

```markdown
#### Footer freshness (envelope D1)

Inserisci alla fine della cover page dell'HLD (o nel footer del documento):

```markdown
---
*Topologia osservata a `<observed_at ISO8601>` — TTL stimato `<ttl_hint_seconds>`s
(da sport-kg v2 envelope D1). Per topology aggiornata, ri-generare l'HLD dopo
`<ttl_expiration ISO8601>`.*
```

**Source**: campi `observed_at` e `ttl_hint_seconds` dalla response di
`describe_service` o `service_full_context` (envelope D1, sport-kg v2).

Se i campi sono assenti (KG v1 ancora deployato), **OMETTI** il footer —
non scrivere "n/d".
```

## Step 5 — TDD verify

```bash
grep -c "Batch Schedulers\|batch_jobs\[\]" agents/doc-generator.md
```
Output atteso post-modifica: ≥ 3

```bash
grep -c "Topologia osservata\|observed_at\|ttl_hint" agents/doc-generator.md
```
Output atteso post-modifica: ≥ 3

```bash
grep -c "find_batch_for_keyword" agents/doc-generator.md
```
Output atteso post-modifica: ≥ 2 (select bulk + Batch Schedulers section)

## Step 6 — Commit

```bash
git add agents/doc-generator.md
git commit -m "feat(agents): doc-generator HLD swim lane Batch Schedulers + footer freshness

C4 Container diagram:
- Nuova swim lane 'Batch Schedulers' (popolata da BatchJob[]) - Onda 10
- Discovery via describe_service + fallback find_batch_for_keyword
- PlantUML pattern documentato con note cron
- Omissione se nessun batch trovato (no rumore informativo)

Cover doc footer:
- Linea 'Topologia osservata a observed_at - TTL ttl_hint_seconds'
- Source: envelope D1 sport-kg v2
- Omissione se KG v1 (campi assenti)

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.3

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] Sezione "Batch Schedulers swim lane" presente con pattern PlantUML
- [ ] Sezione "Footer freshness" presente con format esplicitato
- [ ] Discovery via describe_service + fallback find_batch_for_keyword documentato
- [ ] Omissione documentata (no rumore)
- [ ] grep checks passano
- [ ] Commit creato
