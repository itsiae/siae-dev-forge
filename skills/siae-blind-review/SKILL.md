---
name: siae-blind-review
description: >
  Review cieca: riceve SOLO la spec, trova il codice autonomamente, valuta come auditor ostile.
  Trigger: "blind review", "review cieca", "audit spec", "verifica spec vs codice",
  "review senza diff", /forge-blind-review, REQUIRED SUB-SKILL da siae-finishing-branch.
validates_via:
  predicate: blind_review_completed
  evidence_type: log_event
  evidence_check: "DEVFORGE_LOG_FILE contains blind_review_verdict event for current sid"
---

# SIAE Blind Review — Audit Ostile Spec vs Codice

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

> 📊 **Dai repo itsiae:** Il 28% dei task implementati senza blind review conteneva spec drift scoperto solo in produzione.

---

## Quando si Applica

**Sempre:**
- Come REQUIRED SUB-SKILL di siae-finishing-branch (prima di ogni PR)
- Quando l'utente chiede esplicitamente una blind review

**Eccezioni (chiedi esplicitamente al partner umano):**
- Hotfix P1 dove il tempo e' critico (l'utente deve autorizzare esplicitamente lo skip)
- Modifiche esclusivamente documentali (nessun codice di produzione)

---

## Istruzioni

### Step 1 — Carica la Spec (🟢 SICURO)

1. Cerca il design doc piu' recente in `docs/plans/`:
   ```bash
   ls -t docs/plans/*-design.md 2>/dev/null | head -1
   ```
   Se formato split: cerca `docs/plans/*/overview.md` e il design doc associato.

2. Leggi SOLO il design doc. Estrai: requisiti funzionali, criteri di accettazione, ADR, componenti/file previsti.

3. NON leggere: piano implementativo, commit messages, git diff, output test.

**Se non esiste un design doc:** `BLIND REVIEW: IMPOSSIBILE — Nessun design doc trovato in docs/plans/.` Senza spec, non c'e' metro di giudizio. Procedi senza blind review o scrivi una spec retroattiva con siae-brainstorming.

### Step 2 — Trova il Codice (🟢 SICURO)

Per ogni requisito estratto dal design doc:

1. Usa Grep e Glob per trovare il codice che lo implementa (parti da keyword: classi, funzioni, endpoint, tabelle).
2. Naviga e leggi le implementazioni trovate.
3. Mappa: `Requisito N → file:riga trovato`.

**Regole:** NON usare `git diff` o `git log`. Codice non trovato → MISSING. Codice senza requisito → YAGNI.

### Step 3 — Audit Ostile (🟡 MEDIO — produce il verdetto)

Per ogni requisito, emetti verdetto: **PASS** (soddisfatto), **DRIFT** (diverge), **MISSING** (non trovato), **YAGNI** (extra non richiesto), **PARTIAL** (parziale).

**Output obbligatorio:** header `BLIND REVIEW REPORT`, spec path, `Reviewer mode: BLIND (no diff, no plan, no commit history)`, tabella `| # | Requisito | Codice trovato | Verdetto | Note |`, riepilogo counts per verdetto, verdetto finale `PASS` o `FAIL`.

**Regola FAIL:** `Missing > 0 OR Drift critico OR YAGNI con rischio sicurezza`.

**Se FAIL:** elenca finding bloccanti. La PR NON si apre finche' non risolti o l'utente autorizza bypass. **Se PASS:** procedi con finishing-branch.

---

## Classificazione Rischio / Limiti / Permission Denied

Vedi `lib/risk-taxonomy.md`, `lib/operational-limits.md`, `lib/permission-denied-handling.md`.

In questa skill: Step 1-2 e verdetto PASS → 🟢 Sicuro. Verdetto FAIL (blocca PR) → 🟡 Medio (il blocco e' il comportamento corretto). Step 1-3 sono tutti read-only (Read/Grep/Glob): se Bash negato, richiedi contenuto design doc all'utente e prosegui.

---

## Vincoli

1. **NON** leggere git diff, git log, commit messages, piano implementativo
2. **NON** leggere output di test o CI
3. **SEMPRE** partire dal design doc come unica fonte di verita'
4. **SEMPRE** produrre il report strutturato con verdetto per ogni requisito
5. **PRE-FLIGHT OBBLIGATORIA** per operazioni con rischio >= 🟡
