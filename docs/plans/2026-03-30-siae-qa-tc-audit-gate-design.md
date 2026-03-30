# siae-qa — TC Audit Gate (Fase 4c)

> **Data:** 2026-03-30
> **Autore:** DevForge brainstorming
> **Branch:** feature/siae-qa-decision-tables-domain-extensions

---

## Contesto

La skill `siae-qa` genera Test Case step-based a partire dagli AC di una Story Jira.
Dopo l'implementazione del Coverage Score (v1.33.0), il workflow calcola metriche
quantitative (Breadth/Depth/Technique/Domain) e blocca l'export se score < 50.

**Gap identificato:** il Coverage Score verifica la distribuzione numerica dei TC,
ma non la tracciabilità qualitativa. Non è garantito che ogni AC abbia almeno 1 TC
esplicito, né che le domande contestuali del req type siano state effettivamente poste
prima di generare i TC.

**Richiesta utente:** "agganciare una logica tipo quella dello spec reviewer per
garantire copertura e qualità dei test" — ovvero un gate che, con approccio
"distrust", audita il TC set generato prima di procedere all'export.

---

## Decisione Architetturale

### Opzione scelta: Fase 4c — TC Audit Gate (inline in SKILL.md)

**Motivazione:**
- Nessun file aggiuntivo: la skill è già self-contained
- Punto architetturale corretto: dopo generazione TC, prima export
- Pattern distrust coerente con spec-reviewer senza creare dipendenza esterna
- Differenziazione netta con Riepilogo Copertura: il Riepilogo mostra distribuzione
  quantitativa, il Audit Gate verifica tracciabilità qualitativa AC per AC

### Opzioni scartate

**Opzione B — sub-skill separata `siae-qa-reviewer`:**
Scartata perché aggiunge friction (caricamento sub-skill), rompe la fluidità
del workflow siae-qa che è self-contained. SP 2x superiori senza benefici.

**Opzione C — upgrade Riepilogo Copertura:**
Scartata perché mescola ruoli: il Riepilogo è "mostra per revisione",
aggiungere logica di blocco ne confonde lo scopo.

---

## Design

### Posizionamento nel workflow

```
Fase 4a  → matrice scenari (4 categorie)
Fase 4a-bis → Decision Table gate
Fase 4b  → generazione TC step-based + Riepilogo Copertura
Fase 4c  → TC Audit Gate [NUOVO] ← distrust pass
Fase 5   → export (MCP / CSV)
```

### Logica di Audit (5 check sequenziali)

| # | Check | Fonte dati | Blocca se |
|---|-------|------------|-----------|
| 1 | Ogni AC ha ≥1 TC tracciabile | AC da Fase 1 + TC generati | AC senza TC corrispondente |
| 2 | Nessuna categoria N/A implicita | Matrice 4a | Categoria non valutata (né TC né N/A esplicito) |
| 3 | TC [DT] presenti se gate 4a-bis=YES | Risposta gate 4a-bis + TC list | DT omessa silenziosamente |
| 4 | Domande L1 poste per req type rilevato | Req Profile Card Phase 0 | Domande saltate senza ragione documentata |
| 5 | Coverage Score ≥ 50 | Riepilogo Fase 4b | Score < 50 (già bloccante, qui si riconferma) |

### Verdetto

- Tutti i check OK → `✅ AUDIT PASS — procedi a Fase 5`
- Almeno 1 check KO → `⛔ AUDIT FAIL` con lista gap specifici e fase da cui riprendere

### Template output (da aggiungere in XRAY-TEMPLATES.md)

```
TC AUDIT GATE — {STORY_ID}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [1] Tracciabilità AC→TC
      AC1: "{testo AC}" → TC #{id} ✅ / ❌ MANCANTE
      AC2: "{testo AC}" → TC #{id} ✅ / ❌ MANCANTE

  [2] Categorie matrice 4a
      Positivi:     N TC ✅ / ❌ 0 TC (N/A mai confermato)
      Edge case:    N TC ✅ / N/A confermato ✅ / ❌ 0 TC
      Negativi:     N TC ✅ / ...
      Profilazioni: N TC ✅ / ...

  [3] Decision Table
      Gate 4a-bis: SI → TC [DT] presenti: ✅ N TC / ❌ 0 TC
      Gate 4a-bis: NO → N/A ✅

  [4] Domande contestuali (Phase 0)
      Tipo: {tipo} — L1 poste: ✅ / ❌ SALTATE
      L2/L3 applicabili: ✅ / N/A

  [5] Coverage Score: {XX}/100 — {OTTIMA/BUONA/PARZIALE/INSUFFICIENTE}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDETTO: ✅ AUDIT PASS / ⛔ AUDIT FAIL
  Gap: [lista gap con riferimento alla fase da cui riprendere]
```

---

## File modificati

| File | Modifica |
|------|----------|
| `skills/siae-qa/SKILL.md` | Aggiunta Fase 4c tra Fase 4b e Fase 5 (~35 righe) |
| `skills/siae-qa/XRAY-TEMPLATES.md` | Aggiunta sezione "TC Audit Gate Template" + voce Checklist |

Nessun file nuovo creato.

---

## Criteri di Accettazione

1. `SKILL.md` contiene la sezione `#### 4c — TC Audit Gate` posizionata dopo `#### 4b` e prima di `### Fase 5`
2. Il gate elenca i 5 check in ordine
3. Il verdetto AUDIT PASS sblocca Fase 5 esplicitamente
4. Il verdetto AUDIT FAIL mostra gap per check + fase da cui riprendere
5. `XRAY-TEMPLATES.md` contiene il template `TC AUDIT GATE` nella sezione appropriata
6. `XRAY-TEMPLATES.md` Checklist di Verifica contiene voce `- [ ] TC Audit Gate (Fase 4c) eseguito: AUDIT PASS ottenuto`
7. Nessun placeholder (TBD/TODO) nei blocchi aggiunti
8. `grep -c "4c" skills/siae-qa/SKILL.md` restituisce ≥ 2

---

## Story Points

**SP:** 3 SP-Umano / 1 SP-Augmented

Tipo dominante: feature con logica chiara e spec definite → accelerazione ~2-3x.
