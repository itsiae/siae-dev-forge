# Task 07 — Tabella Segnali Req Typing (+3 righe) in XRAY-TEMPLATES.md

**Stato:** [PENDING]
**File:** `skills/siae-qa/XRAY-TEMPLATES.md`
**Dipendenze:** nessuna (ma eseguire dopo Task 03 per non rileggere il file due volte)

---

## Obiettivo

Aggiungere 3 righe alla `## Tabella Segnali Req Typing` in `XRAY-TEMPLATES.md`
per i tipi Mobile/Flutter, IaC/Terraform, Event-driven/Async.

---

## Step 1 — Verifica che i tipi non esistano già

Cerca in `skills/siae-qa/XRAY-TEMPLATES.md`:
```
Mobile / Flutter
```

Se trovato → il task è già applicato. Marca `[DONE]` e fermati.
Se non trovato → procedi a Step 2.

---

## Step 2 — Individua il punto di inserimento

La tabella attuale termina con la riga:
```
| **Integration / External** | "webhook", "chiamata esterna", "API terza parte", "evento", "Kafka", "SQS", "SNS", "notifica", "callback", "polling" |
```

Le 3 nuove righe vanno inserite **dopo** questa riga, prima della riga vuota
che chiude la tabella.

---

## Step 3 — Aggiungi le 3 righe

Usa Edit per aggiungere le seguenti 3 righe dopo la riga `Integration / External`:

```
| **Mobile / Flutter**       | "Flutter", "Dart", "Riverpod", "app mobile", "iOS", "Android", "widget", "schermata", "deep link", "notifica push", "ObjectBox", "Amplify", "offline" |
| **IaC / Terraform**        | "Terraform", "terragrunt", "modulo", "VPC", "ECS", "Lambda", "plan", "apply", "destroy", "IAM", "security group", "tfvars", "remote state" |
| **Event-driven / Async**   | "Kafka", "SQS", "SNS", "consumer", "producer", "DLQ", "dead letter", "Step Functions", "async", "messaggio", "topic", "coda", "EventBridge" |
```

---

## Step 4 — Output atteso

```
Run: grep -c "Mobile / Flutter\|IaC / Terraform\|Event-driven / Async" skills/siae-qa/XRAY-TEMPLATES.md
Output atteso: 3
```

Se il count è 3 → task completato.
Aggiorna lo stato a `[DONE]` in `overview.md`.
