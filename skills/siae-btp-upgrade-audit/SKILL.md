---
name: siae-btp-upgrade-audit
description: >
  Rileva regressioni di business logic durante upgrade librerie SAP BTP deprecate.
  Fase 1 (BASELINE): estrae fingerprint strutturato da branch vecchio.
  Fase 2 (AUDIT): confronta con branch nuovo e genera gap report per app.
  Trigger: /forge-btp-baseline, /forge-btp-audit, upgrade SAP BTP, librerie deprecate SAP,
  gap analysis SAP BTP, no-regression upgrade UI5, verifica migrazione BTP.
---

# siae-btp-upgrade-audit — SAP BTP Upgrade Audit

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · siae-btp-upgrade-audit                ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 4. Implementation (tool di supporto upgrade)

---

## LA LEGGE DI FERRO

NESSUNA DICHIARAZIONE DI "MIGRAZIONE OK" SENZA GAP REPORT VERIFICATO.

## Comandi

| Comando | Azione |
|---------|--------|
| `/forge-btp-baseline <branch> [--app=nome]` | Fase 1: genera fingerprint dal branch vecchio |
| `/forge-btp-audit <old-branch> <new-branch> [--app=nome]` | Fase 2: gap analysis completa o per singola app |

**Repo target fisso:** `itsiae/liquidazione`

---

## Prerequisiti

Prima di eseguire qualsiasi fase, verifica:

```bash
gh auth status 2>&1 | grep "Logged in"
```

Output atteso: `✓ Logged in to github.com`

Se fallisce: esegui `gh auth login` prima di procedere.

---

## [PLACEHOLDER: PHASE 1 — BASELINE]
## [PLACEHOLDER: PHASE 2 — AUDIT]
## [PLACEHOLDER: DIFF ENGINE]
## [PLACEHOLDER: GAP REPORT]
