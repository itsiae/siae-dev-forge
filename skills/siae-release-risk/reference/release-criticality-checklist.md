# Release Criticality Checklist

## 📋 Identificazione

| Campo | Valore |
|-------|--------|
| **Microservizio** | _________________ |
| **Versione** | _________________ |
| **Data rilascio** | _________________ |
| **Owner** | _________________ |
| **Jira/Ticket** | _________________ |
| **Diff hash** | _________________ |
| **Baseline main SHA** | _________________ |

---

## 🌱 Release Genesis

**Feature confermate:** _________________
**Feature non attese (anomaly):** _________________

---

## 🔴 Fattori di Rischio (18 criteri)

| # | Criterio | Sì | No | Peso |
|---|----------|----|----|------|
| 1 | **Database change** (DDL/DML) | ☐ | ☐ | +3 |
| 2 | **OCP/K8s config change** | ☐ | ☐ | +2 |
| 3 | **Breaking API changes** | ☐ | ☐ | +3 |
| 4 | **External dependencies** changed | ☐ | ☐ | +2 |
| 5 | **Critical service** | ☐ | ☐ | +3 |
| 6 | **First release** | ☐ | ☐ | +2 |
| 7 | **Complex rollback** | ☐ | ☐ | +2 |
| 8 | **Downtime required** | ☐ | ☐ | +3 |
| 9 | **Data migration required** | ☐ | ☐ | +3 |
| 10 | **Feature flag** (mitigation) | ☐ | ☐ | -1 |
| 11 | **Coverage < 70%** | ☐ | ☐ | +2 |
| 12 | **E2E tests not run** | ☐ | ☐ | +2 |
| 13 | **Performance tests** (mitigation) | ☐ | ☐ | -1 |
| 14 | **User impact > 50%** | ☐ | ☐ | +2 |
| 15 | **Modified > 10 files** | ☐ | ☐ | +1 |
| 16 | **Functional regression delta** (NUOVO) | ☐ | ☐ | +2 |
| 17 | **Security vulnerability state** (NUOVO, HEAD-only MVP) | ☐ | ☐ | +2 |
| 18 | **Unexpected feature in release** (NUOVO, da genesis) | ☐ | ☐ | +2 |

**Punteggio Totale:** _____ / 36

---

## 📊 Classificazione Criticità

| Punteggio | Livello | Azione Richiesta |
|-----------|---------|------------------|
| **0-4** | 🟢 **LOW** | Deploy standard, monitoring standard |
| **5-9** | 🟡 **MEDIUM** | 2+ persone, monitoring 2h, rollback verificato |
| **10-14** | 🟠 **HIGH** | TL + Ops on-call, war room 4h, approvazione TL |
| **15+** | 🔴 **CRITICAL** | CAB approval, deploy fuori orario, war room completa |

**Livello Assegnato:** ___________

---

## 📌 Suggested Follow-up

- [ ] `siae-security` deep analysis (se Criterion 17 trova ≥1 critical CVE)
- [ ] _________________

---

## ✅ Pre-Deploy Checklist

### Testing & Quality
- [ ] Test in staging completati
- [ ] Performance test eseguiti (se HIGH/CRITICAL)
- [ ] Security scan completato (Criterion 17 OK)
- [ ] Code review approvata
- [ ] review-evidence v2 PASS o AUTO_APPROVE

### Preparazione Deploy
- [ ] Rollback plan documentato
- [ ] Comunicazione stakeholder preparata
- [ ] Monitoring/alerting configurato
- [ ] Backup DB eseguito (se applicabile)
- [ ] Feature flags configurati (se applicabile)

### Team & Risorse
- [ ] Team di deploy identificato
- [ ] On-call roster aggiornato
- [ ] War room schedulata (se MEDIUM+)

### Approvazioni
- [ ] Approvazione Team Leader (se HIGH+)
- [ ] Approvazione CAB (se CRITICAL)

---

## 📝 Note Aggiuntive

**Rischi Specifici Identificati:**
_______________________________________________

**Mitigazioni Implementate:**
_______________________________________________

**Decisione Finale:** GO / GO_WITH_MONITORING / POSTPONE_WITHOUT_TL / NO_GO_WITHOUT_CAB

**Approvato da:** _________________ **Data:** _________

---

## 🔄 Post-Deploy Checklist

- [ ] Smoke test superati
- [ ] Metriche di business verificate
- [ ] Log errors controllati
- [ ] Performance baseline verificata
- [ ] Comunicazione successo deploy inviata
