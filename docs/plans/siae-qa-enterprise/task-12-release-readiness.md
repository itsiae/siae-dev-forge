# Task 12 — Release Readiness Score [PENDING]

**File:** `skills/siae-qa/SKILL.md`
**Sezione:** aggiungere dopo il "Riepilogo prima dell'export" in Fase 4b
**Cluster:** C — Output enterprise

---

## Obiettivo

Aggiungere il calcolo del Release Readiness Score (RRS) parziale dopo la Fase 4b,
con gate Go/No-Go espliciti e formula documentata.

---

## Step 1 — Aggiungi sezione RRS in SKILL.md

Leggi `skills/siae-qa/SKILL.md`. Individua la sezione `### Fase 5 — Export / Sincronizzazione`.

Inserisci PRIMA di Fase 5 (dopo Fase 4c se già inserita, altrimenti dopo 4b):

```markdown
### Fase 4d — Release Readiness Score (RRS) [AUTOMATICO]

Dopo aver mostrato il riepilogo copertura al developer, calcola e mostra il RRS parziale.

#### Formula RRS

```
RRS = (W1 × Coverage_Score) + (W2 × Critical_Coverage_Score) + (W3 × Execution_Score) + (W4 × Defect_Score)

Pesi:
  W1 = 0.25  (copertura generale)
  W2 = 0.35  (copertura scenari critici — maggior peso)
  W3 = 0.30  (esito esecuzione TC — disponibile post-esecuzione)
  W4 = 0.10  (assenza bug P1 aperti)

Coverage_Score = TC_generati / TC_attesi_minimi
  dove: TC_attesi_minimi = (N_AC × 1) + minimi_per_tipo (vedi tabella cardinalità Fase 4a)

Critical_Coverage_Score = TC_P1_generati / AC_critici_totali
  dove: AC critici = AC che toccano Auth + AC del flusso principale positivo

Execution_Score = TC_passed / TC_executed
  [N/A nella fase corrente — aggiornare dopo l'esecuzione dei test]

Defect_Score = 1 - (Bugs_P1_aperti / TC_totali)
  [N/A nella fase corrente — aggiornare dopo l'esecuzione dei test]
```

#### Calcolo automatico (parziale — pre-esecuzione)

Alla fine di Fase 4b, la skill conosce:
- Numero di AC letti in Fase 1
- Numero di TC generati per categoria e priorità
- Tipo requisito e minimi attesi dalla tabella cardinalità

Calcola e mostra:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RELEASE READINESS SCORE (RRS) — {STORY_ID}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Coverage Score:          {X:.2f}  ({TC_generati}/{TC_attesi_minimi} scenari)
Critical Coverage Score: {Y:.2f}  ({TC_P1}/{AC_critici} AC critici coperti)
Execution Score:         N/A      (aggiornare dopo esecuzione TC)
Defect Score:            N/A      (aggiornare dopo esecuzione TC)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RRS parziale (Coverage + Critical): {Z:.2f}
Stato: IN PROGRESS — eseguire TC e aggiornare con Execution + Defect Score
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Gate di rilascio (RRS completo — post-esecuzione)

| RRS | Decisione | Condizioni |
|-----|-----------|-----------|
| ≥ 0.90 | ✅ **Go** | Nessun bug P1 aperto |
| 0.75–0.89 | ⚠️ **Go condizionale** | Richiede approvazione QA Lead + lista rischi documentata |
| 0.60–0.74 | ❌ **No-Go raccomandato** | Possibile eccezione con approvazione Product Owner + remediation plan entro N giorni |
| < 0.60 | 🚫 **Hard No-Go** | Blocco — nessuna eccezione senza approvazione CTO/equivalente |

**Regola assoluta:** se ci sono bug P1 aperti collegati ai TC di questa Story,
il Defect_Score = 0 e il gate è Hard No-Go indipendentemente dagli altri assi.

#### Aggiornamento RRS post-esecuzione

Dopo l'esecuzione dei TC in Xray (Fase 5), aggiorna il RRS con:
- `Execution_Score` = percentuale TC passed / TC executed
- `Defect_Score` = 1 - (Bugs_P1_aperti / TC_totali)

Il RRS completo determina la decisione go/no-go per il collaudo.
```

---

## Step 2 — Aggiungi RRS alla classificazione rischio

Nella tabella "Classificazione Rischio Operazioni" di SKILL.md, aggiungi:

```markdown
| Calcolo RRS (pre-esecuzione) | 🟢 Sicuro | No |
| Decisione Go/No-Go su RRS < 0.75 | 🔴 Alto | Si |
```

---

## Step 3 — Aggiungi RRS alla checklist di verifica in XRAY-TEMPLATES.md

```markdown
- [ ] RRS parziale calcolato e mostrato al developer dopo il riepilogo copertura
- [ ] Coverage_Score e Critical_Coverage_Score mostrati con formula trasparente
- [ ] Gate di rilascio comunicato al developer con decisione consigliata
```

---

## Step 4 — Aggiorna Anti-Razionalizzazione in SKILL.md

Aggiungi alla tabella:

```markdown
| "Il go/no-go lo decide il PM, non la skill" | Il PM decide sulla base di evidenza. Il RRS fornisce l'evidenza quantitativa. Senza RRS, la decisione è soggettiva e non difendibile davanti a un auditor. |
| "Il RRS è basso ma rilasciamo lo stesso" | Un RRS < 0.75 senza approvazione documentata è un rischio QA non gestito. Documenta l'eccezione esplicitamente — non ignorare il valore. |
```

---

## Step 5 — Commit

```bash
git add skills/siae-qa/SKILL.md skills/siae-qa/XRAY-TEMPLATES.md
git commit -m "feat(siae-qa): add Release Readiness Score (RRS) with Go/No-Go gates and partial auto-calculation"
```
