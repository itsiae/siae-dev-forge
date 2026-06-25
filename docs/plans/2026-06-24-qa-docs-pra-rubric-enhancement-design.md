# qa-docs — Rafforzo Rubrica PRA e Tassonomia SIAE — Design Doc

> **Data:** 2026-06-24
> **Status:** APPROVATO (analisi 4 agenti ciechi blind-review + simulazione 10 agenti round 2)
> **Skill:** `skills/qa-docs/`

---

## Problema

La skill `qa-docs` generava MTP e PRA con tre gap ricorrenti identificati dall'analisi blind a 4 agenti:

1. **G-01 — Tassonomia rischi assente**: il campo `fattore_rischio` non aveva una lista di codici SIAE definiti. Gli agenti inventavano descrizioni generiche o usavano un singolo codice per tutto il PRA.
2. **G-02 — Bias criticità Alta**: l'esempio hardcoded in `pra_obiettivi` mostrava sempre `criticita: "Alta"` e `frequenza_uso: "Alta"`, inducendo gli agenti a usare Alta come default su ogni riga.
3. **G-03 — Assenza guida casi limite**: nessuna regola operativa per (a) operazioni una tantum ad alto impatto legale, (b) interfacce di gestione vs funzione core, (c) frequenza di batch per cadenza effettiva. Produceva inflazione Bloccante (5/8 scenari in Sim #7) e assenza di Media (0/8 in Sim #10 antifrode).
4. **G-04 — req_\* re-inferiti dal contesto**: i flag `req_nrt` / `req_performance` / `req_e2e_uat` in Fase 6 venivano dedotti dal contesto conversazionale invece di essere letti dal JSON MTP già prodotto in Fase 2, producendo incoerenze MTP↔PRA.
5. **G-05 — Granularità non vincolata**: nessun limite esplicito al numero di macro-scenari. I PRA da 12-15 scenari perdevano potere discriminante.
6. **G-06 — Obiettivi_test duplicati dai macro-scenari**: la skill non indicava esplicitamente che `obiettivi_test` deve esprimere l'intento per livello di test, non essere una copia del perimetro.

---

## Soluzione

### Modifiche a `pra-structure.md`

- Tassonomia completa 30 codici SIAE: **B-01..B-08** (business), **T-01..T-10** (tecnici), **Q-01..Q-12** (qualità) con definizione operativa + "quando usarlo" contestualizzato al dominio SIAE
- Rubrica operativa criticità 4 livelli con criteri espliciti e **esempi concreti SIAE** (calcolo royalties errato = Bloccante; errore rendicontazione autori = Alta; report secondario in ritardo = Media)
- Nuova sezione **"Casi limite e decisioni ambigue"** con 4 pattern operativi:
  1. Alta criticità + Bassa frequenza (operazioni una tantum legalmente critiche — es. firma mandato)
  2. Interfaccia di gestione vs. funzione core (dashboard monitoring ≠ sistema sottostante)
  3. Frequenza batch per cadenza effettiva (giornaliero → Molto Alta; trimestrale → Media)
  4. Anti-pattern con segnale e correzione (inflazione Bloccante, assenza Media, req_nrt inferito, Q-01 catch-all)
- Tabella frequenza d'uso con proxy empirici per tipo di funzionalità SIAE

### Modifiche a `phase-playbook.md`

- Nuova checklist decisionale **5-step** in Fase 2, eseguita per ogni scenario prima di scrivere `pra_obiettivi`:
  1. Gate check Bloccante (4 criteri letterali)
  2. Regola operazioni una tantum (frequenza bassa ≠ criticità bassa se conseguenze legali)
  3. Regola interfaccia di gestione
  4. Frequenza con fonte obbligatoria nel campo `motivazione`
  5. Sanity check distribuzione (≤5/8 Bloccante, ≥1 Media, req_\* solo se espliciti)
- Vincolo granularità 4–8 macro-scenari con motivazione
- Regola derivazione obiettivi_test (verbo + oggetto + livello, NON duplicati del perimetro)
- Proxy frequenza con obbligo documentare fonte

### Modifiche a `SKILL.md`

- Schema `rischi` aggiornato: da `["..."]` a `[{rischio, probabilita, impatto, mitigazione, owner}]`
- Esempi `pra_obiettivi` diversificati: Bloccante/Molto Alta, Alta/Alta, Media/Media
- Passo **6.3a**: lettura obbligatoria di `req_nrt` / `req_performance` / `req_e2e_uat` dal JSON MTP già prodotto
- Passo **6.3b**: diff check cardinalità `len(perimetro_test) == len(pra_obiettivi)`
- Nota livelli opzionali: T2 omesso solo per progetti puramente tecnici senza interfacce utente

### Modifiche a `template-structure.md`

- Tabella stili Word obbligatori per sezione (previene il bug "Normal" silenzioso)
- Disambiguazione anchor TOC (cercare `" TOC "` con spazi)
- Sezione 1.2 documentata come statica nel template (non generata dal JSON)

---

## Criteri di accettazione

| # | Criterio | Verificato con |
|---|---|---|
| CA1 | Simulazione 10 agenti: tutti producono ≥1 Media | Sim Round 2 — 10/10 |
| CA2 | Simulazione 10 agenti: Bloccante ≤ 5/8 per ogni simulazione | Sim Round 2 — massimo 4/8 |
| CA3 | Step5 sanity check: ≥9/10 simulazioni OK | Sim Round 2 — 9/10 |
| CA4 | req_nrt falsi positivi: 0 | Sim Round 2 — 0 |
| CA5 | Cardinalità MS = PRA: 10/10 | Sim Round 2 — 10/10 |
| CA6 | SIM-07 firma mandati: motivazione Bloccante cita gate esplicito | Verificato in output Round 2 |
| CA7 | SIM-10 antifrode: dashboard revisione classificata Media | Verificato in output Round 2 — 2 Media |

---

## Scope e limitazioni

- Non modifica `build_mtp.py` né `build_pra.py` — solo documentazione skill
- Non introduce requisiti NRT sui template Word/Excel
- La policy "marker DA CONFERMARE rimangono visibili nel .docx" non è stata modificata (richiede conferma da QA SIAE)
