# DevForge — Requisiti e Criteri di Accettazione

**Ambito:** miglioramenti a DevForge (Claude Code + plugin `siae-devforge`) su progetti multi-repo SIAE.
**Obiettivo:** allineare DevForge alle convenzioni SIAE (pipeline, best practice PLAN/DEPLOY, struttura multi-repo) e correggere i comportamenti errati su diff, brainstorming e apertura PR.
**Versione:** 0.1 — **Data:** 2026-07-01 — **Owner:** Core Platforms

---

## Legenda priorità

| Codice | Significato |
|--------|-------------|
| P1 | Bloccante — impedisce l'uso corretto del flusso |
| P2 | Alta — degrada l'esperienza o introduce rischio |
| P3 | Media — miglioria |

## Definizioni

- **IaC** — repo *Infrastructure as Code*
- **BFF** — repo *Backend for Frontend*
- **SPA** — repo *Single Page Application* (frontend)
- **Collaudo** — ambiente/stage di test
- **Certificazione** — ambiente/stage pre-produzione
- **PLAN** — workflow di pianificazione DevForge
- **PLAN + DEPLOY** — workflow PLAN esteso alla fase di deploy
- **Fonte di verità** — file versionato (es. `CLAUDE.md` o config `siae-devforge`) da cui DevForge carica le convenzioni come contesto

---

## REQ-DF-01 — Conoscenza ambienti e stage della pipeline di deploy
**Categoria:** Contesto · **Priorità:** P2

**Contesto.** DevForge non conosce gli ambienti e gli stage della pipeline di deploy, né collaudo né certificazione.

**Requisito.** DevForge DEVE conoscere l'elenco canonico degli ambienti/stage della pipeline SIAE e riferirsi ad essi correttamente.

**Criteri di accettazione.**
- [ ] Dato un task che coinvolge il deploy, DevForge nomina gli stage nell'ordine corretto attingendo dalla fonte di verità, **senza inventarli**.
- [ ] DevForge distingue e non confonde **collaudo** e **certificazione**.
- [ ] L'elenco ambienti/stage è definito in un file versionato (non hardcoded a runtime, non dedotto).
- [ ] Se la fonte di verità non è disponibile, DevForge lo dichiara invece di ipotizzare gli stage.

---

## REQ-DF-02 — Best practice PLAN e PLAN + DEPLOY
**Categoria:** Contesto · **Priorità:** P2

**Contesto.** DevForge non conosce le nostre best practice per PLAN e per PLAN + DEPLOY.

**Requisito.** DevForge DEVE seguire le best practice SIAE definite per i workflow PLAN e PLAN + DEPLOY.

**Criteri di accettazione.**
- [ ] L'output di PLAN segue il template/checklist standard (tutti gli step attesi presenti).
- [ ] In PLAN + DEPLOY la progressione ambienti è rispettata: nessuno stage saltato, nessun deploy verso certificazione/produzione senza il gate previsto.
- [ ] Le best practice sono documentate nella fonte di verità e caricate come contesto all'avvio del workflow.
- [ ] Deviazioni dalla best practice vengono segnalate esplicitamente, non applicate silenziosamente.

---

## REQ-DF-03 — Diff PR sul branch corretto (non sempre `main`)
**Categoria:** Comportamento · **Priorità:** P1 (bloccante)

**Contesto.** DevForge calcola la diff delle PR sempre sul branch `main` e non sul branch su cui si è pushato. Risultato: diff troppo lunghi, DevForge va in loop e si blocca.

**Requisito.** DevForge DEVE calcolare la diff rispetto al **merge-base corretto del branch target** della PR, non sempre contro `main`.

**Criteri di accettazione.**
- [ ] Dato un feature branch aperto da base `X`, la diff è calcolata contro il merge-base con `X`, **non** contro `main`.
- [ ] La dimensione della diff elaborata corrisponde alle sole modifiche del branch corrente.
- [ ] **Nessun loop:** se la diff supera una soglia configurata, DevForge la tronca/paginizza e prosegue, invece di bloccarsi.
- [ ] Regressione verificata sul caso branch derivato da branch non-`main` (branch da develop/release/altro feature branch).

---

## REQ-DF-04 — Brainstorming proporzionato alla complessità
**Categoria:** Comportamento · **Priorità:** P2

**Contesto.** Il brainstorming è troppo invasivo: viene applicato anche per cambiamenti triviali.

**Requisito.** DevForge DEVE scalare la profondità di brainstorming/planning alla complessità del cambiamento.

**Criteri di accettazione.**
- [ ] Dato un cambiamento triviale (es. fix typo, 1–2 righe, rename locale), DevForge **non** attiva il brainstorming completo.
- [ ] Dato un cambiamento complesso (multi-file, multi-repo, modifiche a IaC), DevForge attiva il brainstorming.
- [ ] Esiste una soglia/euristica configurabile (es. n. file, n. righe, presenza di modifiche IaC) che governa l'attivazione.
- [ ] L'utente può forzare `skip` o attivazione del brainstorming con un flag esplicito, che ha precedenza sull'euristica.

---

## REQ-DF-05 — Gestione apertura PR
**Categoria:** Comportamento · **Priorità:** P1

**Contesto.** Troppe aperture manuali di PR. Claude Code stesso chiede di aprire la PR spiegando che non c'è bisogno di review. In ogni caso, aprire una PR direttamente da DevForge è quasi impossibile.

**Requisito.** DevForge DEVE gestire la creazione delle PR in modo coerente: aprirle programmaticamente quando previsto e **non** richiedere apertura manuale quando la review non è necessaria.

**Criteri di accettazione.**
- [ ] DevForge apre la PR programmaticamente tramite integrazione con il provider Git, senza passaggi manuali dell'utente.
- [ ] Se la review non è necessaria, DevForge segue il path corretto (auto-merge / no-review) invece di chiedere l'apertura manuale.
- [ ] DevForge **non** richiede ripetutamente all'utente di aprire la PR.
- [ ] Caso end-to-end: apertura PR da DevForge completata con successo (branch → PR aperta → esito atteso), verificata sui repo target.

---

## REQ-DF-06 — Convenzione struttura multi-repo (`iac` / `bff` / `spa`)
**Categoria:** Contesto · **Priorità:** P2

**Contesto.** DevForge non conosce la nostra convenzione di struttura multi-repo base: `iac` / `bff` / `spa`.

**Requisito.** DevForge DEVE conoscere e rispettare la convenzione multi-repo SIAE (`iac`, `bff`, `spa`).

**Criteri di accettazione.**
- [ ] Dato un prodotto con i tre repo, DevForge identifica correttamente il repo da toccare: modifiche infra → `iac`; API/backend → `bff`; frontend → `spa`.
- [ ] DevForge **non** applica modifiche nel repo sbagliato.
- [ ] Naming e ruoli dei repo sono riconosciuti automaticamente a partire dalla convenzione documentata nella fonte di verità.
- [ ] Su un cambiamento cross-cutting (es. nuovo endpoint con relativa infra e consumo frontend), DevForge riparte le modifiche sui tre repo in modo coerente.

---

## Riepilogo requisiti

| ID | Titolo | Categoria | Priorità |
|----|--------|-----------|----------|
| REQ-DF-01 | Conoscenza ambienti e stage pipeline | Contesto | P2 |
| REQ-DF-02 | Best practice PLAN e PLAN + DEPLOY | Contesto | P2 |
| REQ-DF-03 | Diff PR sul branch corretto | Comportamento | P1 |
| REQ-DF-04 | Brainstorming proporzionato alla complessità | Comportamento | P2 |
| REQ-DF-05 | Gestione apertura PR | Comportamento | P1 |
| REQ-DF-06 | Convenzione multi-repo `iac`/`bff`/`spa` | Contesto | P2 |

**Nota trasversale.** REQ-DF-01, -02 e -06 condividono la stessa leva: caricare le convenzioni SIAE come contesto versionato (`CLAUDE.md` / config `siae-devforge`). REQ-DF-03, -04 e -05 sono difetti di comportamento da correggere nel flusso DevForge.
