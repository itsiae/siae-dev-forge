---
name: siae-requesting-review
description: >
  Trigger: "pronto per review", "ho aperto la PR", "chiedo il review",
  PR aperta senza reviewer assegnato.
---

# SIAE Requesting Review — Richiedere una Code Review Efficace

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · REQUESTING CODE REVIEW                ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 3. Branching (post-PR)

---

## Il Principio Fondamentale

La code review e' un dialogo tra colleghi tecnici, non un esame.

**Principio:** Fornisci contesto, non giustificazioni. Il reviewer e' un collega — non un giudice.

Siamo colleghi che lavorano insieme verso lo stesso obiettivo: codice di qualita'.
Il tuo reviewer non ha il tuo contesto — il tuo compito e' darglielo.

---

## Processo in 4 Step

### Step 1 — Scrivi la PR Description

Una PR description efficace risponde a 3 domande:
1. **Cosa** hai cambiato?
2. **Perche'** l'hai cambiato?
3. **Come** verificare che funzioni?

**Template obbligatorio:**

```
## Cosa
[2-3 punti di cosa e' cambiato — focalizza sul behaviour, non sui file]

## Perche'
[Link al ticket JIRA: PROJ-NNN] [oppure: descrizione del problema risolto]

## Come verificare
- [ ] [Step 1 per riprodurre/verificare]
- [ ] [Step 2]
- [ ] Tutti i test passano: `mvn test` / `yarn test` / `pytest`

## Note per il reviewer
[Cosa vuoi che il reviewer guardi con attenzione?
Decisioni architetturali contestabili? Tradeoff tecnici?]
```

**Non difenderti prima che il reviewer dica nulla.** Offri contesto, non giustificazioni preventive.

### Step 2 — Apri la PR e Assegna il Reviewer

```
REQUIRED PRE-SKILL: siae-finishing-branch
```

La PR deve essere gia' stata creata da `siae-finishing-branch`. Se non lo e' ancora,
torna a quella skill prima di procedere qui.

Una volta che la PR esiste, assegna il reviewer corretto:

🟡 MEDIO — Mostra pre-flight card prima di assegnare

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-requesting-review",
  "context": [
    {"emoji": "🌿", "label": "Branch", "value": "<branch-name>"},
    {"emoji": "🎯", "label": "Target", "value": "sviluppo"},
    {"emoji": "📝", "label": "Commit", "value": "<N> commit"}
  ],
  "actions": [
    {"emoji": "🚀", "label": "Assegnazione reviewer alla PR", "path": "PR #<number>"}
  ],
  "reason": "PR pronta, reviewer da assegnare",
  "ifno": "La PR resta senza reviewer assegnato"
}' | python3 design-system/generate-card.py
```

```bash
# Assegna reviewer alla PR gia' aperta
gh pr edit {pr_number} --add-reviewer {github-username}
```

| Tipo di cambiamento | Reviewer consigliato |
|--------------------|---------------------|
| Business logic critica | Tech Lead del team |
| Infrastruttura AWS/Terraform | Specialist IaC |
| Frontend Vue/Angular/React | Developer frontend del team |
| Security / IAM / PII | Security reviewer |
| Hotfix urgente | Chiunque disponibile + notifica sincrona |

Se non sai chi assegnare: chiedi al tech lead.

### Step 3 — Comunica il Contesto al Reviewer

Prima che il reviewer inizi, offri contesto sincrono se:
- Il cambiamento e' ampio (>500 righe)
- Ci sono decisioni architetturali contestabili
- Il reviewer non conosce il dominio di business (ISRC, ISWC, royalties)

**Notifica asincrona (Slack):**

```
@reviewer PR [link] pronta per review.
Focus: [cosa vuoi che guardi con attenzione].
[Deadline solo se urgente — ometti altrimenti]
```

### Step 4 — Gestisci l'Attesa

Durante l'attesa:
- **NON** fare push di nuovi commit sulla stessa PR (interrompe la review in corso)
- **NON** sollecitare piu' di una volta — rispetta i tempi del collega
- **SI'** lavora su altri task nel frattempo
- **SI'** segnala blocchi urgenti al tech lead

Se il review non arriva entro **24 ore lavorative** (soglia default SIAE):

```
@reviewer PR [link] — hai bisogno di piu' contesto?
Posso walkthrough il codice in 15 minuti se preferisci.
```

---

## Signal Phrase

Se sei a disagio con qualcosa nel processo (il reviewer risponde in modo inaspettato,
senti pressione a non fare pushback, la situazione e' ambigua) ma non riesci a dirlo
direttamente in chat:

```
"Situazione insolita al Circle K."
```

Questa frase segnala al tech lead che hai bisogno di un allineamento sincrono.
Il significato e' noto al team — non serve spiegare.

**Quando NON usarla:** per evitare pushback legittimo o per rimandare una
conversazione tecnica normale. Usala solo quando il contesto interpersonale
rende il confronto diretto genuinamente difficile da articolare in chat.

Per la gestione del feedback gia' ricevuto dal reviewer, vedi `siae-receiving-review`.

---

## Anti-Rationalization Table

| Pensiero | Realta' |
|----------|---------|
| "Il codice e' ovvio, non servono note" | Il reviewer non ha il tuo contesto. Dagliele. |
| "Chiedo review solo se sono sicuro" | La review serve proprio per trovare cio' che non sai. |
| "La PR description si scrive dopo" | Scriverla ti forza a chiarire il tuo stesso lavoro. |
| "Sollecito ogni ora" | Una notifica e' rispettosa. Lo spam non lo e'. |
| "Aspetto che il reviewer trovi tutto" | Il contesto che dai accelera la review e migliora il feedback. |
| "Non so a chi assegnarlo" | Chiedi al tech lead. Non indovinare. |

---

## Classificazione Rischio

| Operazione | Livello | Card | Note |
|-----------|---------|------|------|
| Scrivere PR description | 🟢 Sicuro | No | Solo testo |
| Push branch | 🟡 Medio | No | Coperto da siae-finishing-branch |
| Creare PR su GitHub | 🟡 Medio | No | Coperto da siae-finishing-branch |
| Assegnare reviewer | 🟡 Medio | Si | Notifica visibile al reviewer |

---

## Permission Denied Handling

**Se Bash viene negato (gh pr create):**
1. Presenta il comando completo per esecuzione manuale
2. Fornisci il testo della PR description completa
3. L'utente esegue manualmente da terminale

**Se gh non e' installato:**
```bash
# Alternativa: usa la GitHub UI
# Vai su: https://github.com/{org}/{repo}/compare/{branch}
# Incolla la PR description nel campo body
```
