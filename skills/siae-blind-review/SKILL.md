---
name: siae-blind-review
description: >
  Review cieca: riceve SOLO la spec, trova il codice autonomamente, valuta come auditor ostile.
  Trigger: "blind review", "review cieca", "audit spec", "verifica spec vs codice",
  "review senza diff", /forge-blind-review, REQUIRED SUB-SKILL da siae-finishing-branch.
---

# SIAE Blind Review — Audit Ostile Spec vs Codice

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · BLIND REVIEW                        ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 6. QA Gate

---

## LA LEGGE DI FERRO

NESSUN BIAS DI CONFERMA. IL REVIEWER PARTE DALLA SPEC, NON DAL DIFF.

<EXTREMELY-IMPORTANT>
Stai per leggere il git diff, il piano implementativo, i commit messages, o l'output dei test?
FERMATI. Questa skill ti VIETA di leggere qualsiasi cosa che non sia il design doc e il codice sorgente.

Il bias di conferma e' il nemico. Se sai cosa l'implementer ha fatto, cercherai conferme
invece di cercare problemi. L'auditor ostile non sa. Trova.
</EXTREMELY-IMPORTANT>

---

> 📊 **Dai repo itsiae:** Il 28% dei task implementati senza blind review conteneva spec drift scoperto solo in produzione.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## Quando si Applica

**Sempre:**
- Come REQUIRED SUB-SKILL di siae-finishing-branch (prima di ogni PR)
- Quando l'utente chiede esplicitamente una blind review

**Eccezioni (chiedi esplicitamente al partner umano):**
- Hotfix P1 dove il tempo e' critico (l'utente deve autorizzare esplicitamente lo skip)
- Modifiche esclusivamente documentali (nessun codice di produzione)

---

## Istruzioni

### Step 1 — Carica la Spec

🟢 SICURO

1. Cerca il design doc piu' recente in `docs/plans/`:
   ```bash
   ls -t docs/plans/*-design.md 2>/dev/null | head -1
   ```
   Se formato split: cerca `docs/plans/*/overview.md` e il design doc associato.

2. Leggi SOLO il design doc. Estrai:
   - Lista requisiti funzionali
   - Criteri di accettazione
   - Decisioni architetturali (ADR)
   - Componenti/file previsti dal design

3. NON leggere: piano implementativo, commit messages, git diff, output test.

**Se non esiste un design doc:**
Il blind review non puo' procedere. Segnala:
```
BLIND REVIEW: IMPOSSIBILE — Nessun design doc trovato in docs/plans/.
Senza spec, non c'e' metro di giudizio. Procedi con la PR senza blind review,
oppure scrivi una spec retroattiva con siae-brainstorming.
```

### Step 2 — Trova il Codice

🟢 SICURO

Per ogni requisito estratto dal design doc:

1. Usa Grep e Glob per trovare il codice che lo implementa
2. Parti da keyword del requisito: nomi di classe, funzione, endpoint, tabella
3. Naviga il codice trovato — leggi le implementazioni
4. Mappa: `Requisito N → file:riga trovato`

**Regole:**
- NON usare `git diff` o `git log` — trova il codice dal sorgente
- Se non trovi codice per un requisito → segnalo come MISSING
- Se trovi codice che non corrisponde a nessun requisito → segnalo come YAGNI

### Step 3 — Audit Ostile

🟡 MEDIO — Questo step produce il verdetto

Per ogni requisito, valuta:

| Verdetto | Significato |
|----------|------------|
| **PASS** | Il codice soddisfa il requisito come descritto nella spec |
| **DRIFT** | Il codice diverge dalla spec (implementa qualcosa di diverso) |
| **MISSING** | Nessun codice trovato per questo requisito |
| **YAGNI** | Codice trovato che non corrisponde a nessun requisito |
| **PARTIAL** | Il codice implementa parzialmente il requisito |

**Output strutturato obbligatorio:**

```
BLIND REVIEW REPORT
═══════════════════
Spec: docs/plans/YYYY-MM-DD-<topic>-design.md
Reviewer mode: BLIND (no diff, no plan, no commit history)

| # | Requisito | Codice trovato | Verdetto | Note |
|---|-----------|---------------|----------|------|
| 1 | ... | src/... | PASS | — |
| 2 | ... | NON TROVATO | MISSING | ... |
| 3 | — | src/extra.js | YAGNI | ... |

═══════════════════
Riepilogo:
  PASS: N | DRIFT: M | MISSING: K | YAGNI: J | PARTIAL: L

Verdetto finale: PASS / FAIL
  FAIL se: Missing > 0 OR Drift critico OR YAGNI con rischio sicurezza
```

**Se verdetto FAIL:**
Elenca i finding bloccanti. La PR NON deve essere aperta finche' i finding
non sono risolti o l'utente autorizza esplicitamente il bypass.

**Se verdetto PASS:**
Procedi con il flusso di finishing-branch.

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Ho gia' visto il diff, non posso de-vederlo" | Allora non guardare il diff PRIMA di questa skill. L'ordine conta. |
| "Il code-reviewer fa gia' questo" | Il code-reviewer ha il diff. Tu hai la spec. Prospettive diverse. |
| "La spec e' troppo vaga per fare audit" | Se la spec e' vaga, il problema e' la spec. Segnalalo come finding. |
| "Non trovo il codice, probabilmente e' ok" | NON TROVATO = MISSING. Mai assumere che esiste. |
| "E' solo un refactoring, la spec non cambia" | Anche i refactoring possono introdurre drift. Verifica. |
| "Il codice extra sembra utile" | Se non e' nella spec, e' YAGNI. La spec decide, non il gusto. |
| "Mi fido dell'implementer" | L'auditor ostile non si fida di nessuno. Verifica sempre. |
| "E' troppo tardi per bloccare la PR" | E' peggio scoprire drift in produzione. Blocca ora. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura design doc | 🟢 Sicuro | No |
| Grep/Glob nel codice | 🟢 Sicuro | No |
| Emissione verdetto PASS | 🟢 Sicuro | No |
| Emissione verdetto FAIL (blocca PR) | 🟡 Medio | No (il blocco e' il comportamento corretto) |

---

## Vincoli

1. **NON** leggere git diff, git log, commit messages, piano implementativo
2. **NON** leggere output di test o CI
3. **SEMPRE** partire dal design doc come unica fonte di verita'
4. **SEMPRE** produrre il report strutturato con verdetto per ogni requisito
5. **PRE-FLIGHT OBBLIGATORIA** per operazioni con rischio >= 🟡
