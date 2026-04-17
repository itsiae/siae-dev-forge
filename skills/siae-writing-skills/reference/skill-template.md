# Template SKILL.md — DevForge

Copia questo template per creare una nuova skill. Sostituisci tutti i placeholder `<...>`.

---

```markdown
---
name: <nome-skill>
description: >
  <Trigger conditions: Use when... Trigger: ...>
  <Max 3 righe. Solo QUANDO si usa, non COSA fa.>
---

# <Titolo Skill> — DevForge

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · <NOME SKILL MAIUSCOLO>             ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** <Rigid | Flexible> | **Fase SDLC:** <N. Nome Fase>

---

## LA LEGGE DI FERRO
<!-- Solo per skill Rigid. Rimuovi per Flexible. -->

```
<UNA FRASE. MAIUSCOLO. NON NEGOZIABILE.>
```

---

## Quando si Applica

**Sempre:**
- <Caso d'uso 1>
- <Caso d'uso 2>
- <Caso d'uso 3>

**Eccezioni (chiedi esplicitamente al partner umano):**
- <Eccezione 1>
- <Eccezione 2>

---

## Istruzioni

### Step 1 — <Nome Step>

🟢 SICURO

<Istruzioni per lo step. Imperative e dirette.>

### Step 2 — <Nome Step>

🟡 MEDIO — Mostra pre-flight card prima di eseguire

Costruisci la pre-flight card come markdown table inline:

```markdown
| <LEVEL_EMOJI> <MEDIO|ALTO|CRITICO> (<subtitle>) — 🔨 DevForge · <nome-skill> |
|:---|
| [⚠️ WARNING — solo per ALTO e CRITICO] |
| <emoji> <Label>: `<valore rilevato>` |
| 1. <emoji> Azione: <Descrizione azione> |
| 📂 `<file o path>` |
| 💡 Perche': <motivazione> |
| 🚫 Se NO: <cosa succede se rifiutato> |
```

Per card **🔴 ALTO** e **🚨 CRITICO**, aggiungi SEMPRE questa istruzione dopo la tabella:

```
⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente (es. "sì, procedi" / "no, annulla"). Silenzio ≠ consenso.
```

<Istruzioni per lo step.>

### Step 3 — <Nome Step>

🟡 MEDIO — Mostra pre-flight card prima di eseguire

<Istruzioni per lo step.>

<!-- Aggiungi step secondo necessita'. Max 7-8 step. -->

---

## Fallback Obbligatori
<!-- Obbligatorio per skill con card 🔴/🚨. Rimuovi per skill senza operazioni irreversibili. -->

### Risposta ambigua dell'utente alla card
Se l'utente non risponde con "sì, procedi" o "no, annulla" ma usa frasi ambigue
("forse", "aspetta", "va bene", cambio argomento): NON eseguire.
Chiedere: *"Confermo l'operazione? Rispondi 'sì, procedi' oppure 'no, annulla'."*

### Tool call negato dopo conferma
Se l'utente ha confermato la card ma poi nega il tool call:
1. NON riprovare automaticamente
2. Comunicare: "Hai confermato ma il permesso è stato negato. Esegui manualmente:"
3. Fornire il comando esatto pronto da incollare
4. Aspettare conferma: "Dimmi quando hai eseguito"

### Operazione fallita a runtime
Se il comando critico fallisce dopo l'esecuzione:
1. Comunicare lo stato attuale con precisione (cosa è riuscito, cosa no)
2. NON procedere autonomamente ai passi successivi
3. NON eseguire rollback automatico senza consenso
4. Presentare le opzioni: retry / rollback manuale / skip
5. Aspettare istruzioni esplicite

---

## Tabella Anti-Razionalizzazione
<!-- Solo per skill Rigid. Rimuovi per Flexible. -->

| Pensiero | Realta' |
|----------|---------|
| "<Razionalizzazione 1>" | <Risposta che blocca la scorciatoia> |
| "<Razionalizzazione 2>" | <Risposta> |
| "<Razionalizzazione 3>" | <Risposta> |
| "<Razionalizzazione 4>" | <Risposta> |
| "<Razionalizzazione 5>" | <Risposta> |
| "<Razionalizzazione 6>" | <Risposta> |
| "<Razionalizzazione 7>" | <Risposta> |
| "<Razionalizzazione 8>" | <Risposta> |

<!-- Minimo 8 razionalizzazioni per skill Rigid -->

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| <Operazione sicura> | 🟢 Sicuro | No |
| <Operazione media> | 🟡 Medio | Si |
| <Operazione alta> | 🔴 Alto | Si |

---

## Vincoli

1. **NON** <vincolo negativo>
2. **NON** <vincolo negativo>
3. **SEMPRE** <vincolo positivo>
4. **SEMPRE** <vincolo positivo>
5. **PRE-FLIGHT OBBLIGATORIA** per operazioni con rischio >= 🟡 — costruisci come markdown table inline (vedi `design-system/devforge-visual.md` sezione 0.3)

---

## Risorse Aggiuntive

- [reference/<file>.md](reference/<file>.md) — <descrizione>
```

---

## Note sul Template

- **Lunghezza:** il template compilato deve restare sotto 500 righe
- **Legge di Ferro:** solo per skill Rigid (TDD, verification, debugging, git-workflow)
- **Anti-razionalizzazione:** minimo 8 entry per skill Rigid, opzionale per Flexible
- **Step:** minimo 3, massimo 8. Ogni step ha un'etichetta rischio
- **Vincoli:** minimo 4 vincoli espliciti
- **Reference files:** usa `reference/` per dettagli lunghi
