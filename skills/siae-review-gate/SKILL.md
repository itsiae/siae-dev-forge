---
name: siae-review-gate
description: >
  Orchestra la fase di review: verifica file modificati, suggerisce tipo
  di review, avanza la fase SDLC. Backbone skill per la fase review.
triggers:
  - review
  - pronto per review
  - code review
  - chiedi review
  - rivedi il codice
type: Rigid
sdlc_phase: "5. Review"
backbone_role: backbone
backbone_stage: review
hard_gate: true
---

# siae-review-gate — Fase Review SDLC

> **Tipo:** Rigid | **Fase SDLC:** 5. Review

---

## LA LEGGE DI FERRO

```
NESSUNA CHIUSURA SENZA REVIEW
```

## Scopo

Orchestra la fase di review del backbone SDLC. Verifica che ci sia codice
da revieware, suggerisce il tipo di review appropriato, e avanza la fase.

---

## Processo

### Step 1 — Verifica file modificati

Controlla che ci siano file modificati rispetto al branch base:

```bash
git diff --stat $(git merge-base HEAD origin/main)..HEAD
```

Se nessun file modificato: "Nessun codice da revieware. La fase review e'
completata vacuamente."

### Step 2 — Suggerisci tipo di review

| Condizione | Review suggerita | Skill |
|-----------|-----------------|-------|
| PR aperta e review richiesta | Ricevi feedback da reviewer | siae-receiving-review |
| Codice pronto, nessuna PR | Chiedi review a un collega | siae-requesting-review |
| Utente chiede audit indipendente | Review cieca senza contesto | siae-blind-review |
| Nessun reviewer disponibile | Auto-review con checklist | (inline) |

### Step 3 — Auto-review checklist (se nessun reviewer)

Se non ci sono reviewer disponibili, esegui una checklist minimale:

- [ ] I test passano tutti?
- [ ] Il codice segue le convenzioni del progetto?
- [ ] Non ci sono secret/credenziali nel codice?
- [ ] La logica e' comprensibile senza commenti eccessivi?
- [ ] Le modifiche sono coerenti col design doc?

### Step 4 — Avanza fase

Dopo che il review type scelto e' stato completato, la fase review e' completata.
L'utente puo' procedere a verification.

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi max per step | 2 | Fermati. Chiedi all'utente. |
| Output max | 200 righe | Sintetizza. |

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Il codice e' semplice, non serve review" | Anche codice semplice ha bug. La review li trova. |
| "Ho gia' testato, basta cosi'" | Test verifica funzionalita'. Review verifica design e manutenibilita'. |
| "Non c'e' nessuno disponibile per il review" | Usa l'auto-review checklist. Meglio di niente. |

## Classificazione Rischio

| Operazione | Rischio | Card |
|-----------|---------|------|
| Verifica file modificati | 🟢 Sicuro | No |
| Suggerimento tipo review | 🟢 Sicuro | No |
| Auto-review checklist | 🟢 Sicuro | No |
