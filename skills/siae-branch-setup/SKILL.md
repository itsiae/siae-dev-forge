---
name: siae-branch-setup
description: >
  Use when creating release and feature branches for a new increment/sprint.
  Trigger: "crea branch", "nuovo branch release", "branch feature", "setup branch",
  "crea release e feature", "inizia increment", "nuovo increment".
---

# SIAE Branch Setup — DevForge

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║            🔨 DevForge · SIAE BRANCH SETUP                    ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 3. Branching

---

## LA LEGGE DI FERRO

```
NESSUN BRANCH FEATURE SENZA BRANCH RELEASE. NESSUN BRANCH SENZA PARAMETRI VALIDATI.
```

---

## Input Richiesti

| Parametro | Descrizione | Esempio |
|-----------|-------------|---------|
| `area` | Area funzionale del progetto | `EDW`, `DL`, `PMO` |
| `incremento` | Numero dell'increment nel formato `NN_NN` | `01_27` |
| `ticket-id` | ID numerico del ticket Jira (senza prefisso area) | `1549` |

**Naming convention derivato:**
- Release branch: `release/{AREA}_DL_{INCREMENTO}` → `release/EDW_DL_01_27`
- Feature branch: `feature/{AREA}_DL_{INCREMENTO}/{AREA}-{TICKET-ID}` → `feature/EDW_DL_01_27/EDW-1549`

---

## Quando si Applica

**Sempre:**
- Inizio di un nuovo increment o sprint che richiede branch release + feature
- Setup iniziale di un branch feature su un release già esistente
- Quando l'utente fornisce area, incremento e ticket-id

**Eccezioni (chiedi esplicitamente):**
- Il branch release esiste già su origin → chiedi se usare quello esistente
- Il formato dell'incremento non è `NN_NN` → valida con l'utente prima di procedere

---

## Step 1 — Valida i Parametri

🟢 SICURO

Prima di qualsiasi operazione, verifica che tutti e tre i parametri siano presenti e conformi:

- `area`: stringa uppercase, es. `EDW`, `DL`, `PMO`
- `incremento`: formato `NN_NN` (due numeri separati da underscore), es. `01_27`
- `ticket-id`: solo cifre, es. `1549`

Se uno o più parametri mancano, chiedi all'utente prima di procedere:

```
Parametri necessari per il branch setup:
- area (es. EDW, DL, PMO):
- incremento (formato NN_NN, es. 01_27):
- ticket-id (solo cifre, es. 1549):
```

Costruisci i nomi dei branch:
```
RELEASE_BRANCH=release/{AREA}_DL_{INCREMENTO}
FEATURE_BRANCH=feature/{AREA}_DL_{INCREMENTO}/{AREA}-{TICKET-ID}
```

---

## Step 2 — Verifica Stato Git e Ambiente

🟢 SICURO

Assicurati che `siae-git-env` sia già stata eseguita nella sessione (GH_MODE determinato).
Se non è disponibile, invoca `siae-git-env` prima di procedere.

Verifica lo stato locale:

```bash
git status --short
git fetch origin
git branch -a | grep -E "release/{AREA}_DL_{INCREMENTO}"
```

Se il release branch esiste già su origin, mostralo all'utente e chiedi:
- *"Il branch `{RELEASE_BRANCH}` esiste già su origin. Usare quello esistente o sovrascrivere?"*
- Attendi risposta esplicita prima di procedere.

---

## Step 3 — Crea i Branch

🔴 ALTO — Mostra pre-flight card prima di eseguire

| 🔴 ALTO (push su origin) — 🔨 DevForge · siae-branch-setup |
|:---|
| **⚠️ OPERAZIONE CON EFFETTI REMOTI** |
| 📋 Release branch: `{RELEASE_BRANCH}` · 🌿 Feature branch: `{FEATURE_BRANCH}` |
| **▼ Azioni** |
| 1. 🔀 Checkout `main` + pull latest |
| 2. 🌿 Crea `{RELEASE_BRANCH}` da `main` |
| 3. 🌿 Crea `{FEATURE_BRANCH}` da `{RELEASE_BRANCH}` |
| 4. 🚀 Push `{RELEASE_BRANCH}` su origin |
| 5. 🚀 Push `{FEATURE_BRANCH}` su origin + checkout locale |
| 💡 Perché: Branch su origin visibili a tutto il team — naming errato richiede cleanup manuale |
| 🚫 Se NO: Nessun branch viene creato o pushato |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, esegui in sequenza:

```bash
git checkout main
git pull origin main
git checkout -b {RELEASE_BRANCH}
git checkout -b {FEATURE_BRANCH}
git push origin {RELEASE_BRANCH}
git push origin {FEATURE_BRANCH}
```

---

## Step 4 — Verifica Post-Creazione

🟢 SICURO

Verifica che entrambi i branch siano presenti su origin:

```bash
git branch -a | grep -E "({RELEASE_BRANCH}|{FEATURE_BRANCH})"
git status
```

Mostra riepilogo finale:

```
✅ Branch creati e pushati su origin
   release: {RELEASE_BRANCH}
   feature: {FEATURE_BRANCH}
   Sei ora su: {FEATURE_BRANCH}
```

---

## Step 5 — Crea la Pull Request (draft)

🔴 ALTO — Richiede GH_MODE

> **Nota:** GitHub non permette PR senza commit. Questo step crea una PR **draft** con un commit vuoto iniziale per permettere la tracciabilità su GitHub fin dal setup del branch.

**Solo se GH_MODE è attivo**, esegui:

```bash
git commit --allow-empty -m "chore: init branch {FEATURE_BRANCH}"
git push origin {FEATURE_BRANCH}
gh pr create \
  --base {RELEASE_BRANCH} \
  --head {FEATURE_BRANCH} \
  --draft \
  --title "{AREA}-{TICKET-ID} — increment {INCREMENTO}" \
  --body "## Summary
- Feature branch per il ticket {AREA}-{TICKET-ID}, increment {INCREMENTO}
- Branch base: \`{RELEASE_BRANCH}\`

## Ticket
{AREA}-{TICKET-ID}

## Note
PR creata al setup del branch — da aggiornare con descrizione delle modifiche implementate."
```

**Se FALLBACK_MODE**, fornisci il link diretto per aprire la PR manualmente:
```
https://github.com/<owner>/<repo>/compare/{RELEASE_BRANCH}...{FEATURE_BRANCH}
```

Mostra riepilogo finale completo:

```
✅ Branch e PR pronti
   release: {RELEASE_BRANCH}
   feature: {FEATURE_BRANCH}
   PR draft: <URL PR>
   Sei ora su: {FEATURE_BRANCH}
```

---

## Fallback Obbligatori

### Risposta ambigua alla card
Se l'utente non risponde con "sì, procedi" o "no, annulla": NON eseguire.
Chiedere: *"Confermo la creazione dei branch? Rispondi 'sì, procedi' oppure 'no, annulla'."*
**Risposte valide:** "sì", "vai", "procedi", "confermo", "esegui"

### Tool call negato dopo conferma
Se il tool call viene negato dopo conferma:
1. NON riprovare automaticamente
2. Fornire i comandi esatti da eseguire manualmente nel terminale
3. Aspettare conferma di esecuzione manuale

### Branch già esistente su origin
Se il push fallisce perché il branch esiste già:
1. Comunicare il conflitto senza forzare nulla
2. Presentare opzioni: usa quello esistente / rinomina / forza (solo se esplicito)
3. Aspettare istruzioni esplicite — MAI `--force` senza richiesta esplicita

### Parametri in formato non standard
Se l'utente fornisce `1_27` invece di `01_27`, o `edw` invece di `EDW`:
1. Mostrare il valore ricevuto e quello normalizzato
2. Chiedere conferma prima di usare il valore normalizzato

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realtà |
|----------|--------|
| "So già i nomi, creo direttamente senza chiedere" | I parametri devono essere validati esplicitamente — un typo nel nome richiede cleanup su origin |
| "Il release esiste già, creo solo il feature" | Verifica sempre lo stato su origin prima — potrebbe puntare a un commit diverso da main |
| "Faccio push --force se il branch esiste" | MAI force senza richiesta esplicita — sovrascrive lavoro altrui su origin |
| "L'incremento è ovvio dal contesto" | Chiedi sempre se non è nei parametri — `01_27` e `1_27` producono branch diversi |
| "Checkout e push in una sola riga per velocità" | Esegui in sequenza controllata — un errore a metà lascia stato inconsistente |
| "Il formato dell'area non importa, tanto è solo un prefisso" | La naming convention è contratto di team — `edw` ≠ `EDW` in git |
| "Se il push fallisce riprovo automaticamente" | Un push fallito ha una causa — diagnostica prima di riprovare |
| "Non serve la pre-flight, sono solo branch" | I branch su origin sono visibili al team immeditamente — naming errato impatta tutti |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Validazione parametri | 🟢 Sicuro | No |
| Verifica stato git locale | 🟢 Sicuro | No |
| Fetch origin | 🟢 Sicuro | No |
| Creazione branch locali | 🟡 Medio | No |
| Push branch su origin | 🔴 Alto | Sì |
| Commit vuoto iniziale | 🟡 Medio | No |
| Creazione PR draft | 🔴 Alto | Sì (inclusa nel push) |

---

## Vincoli

1. **MAI** creare il feature branch senza che il release branch esista
2. **MAI** eseguire push su origin senza pre-flight card confermata
3. **MAI** usare `--force` su push senza richiesta esplicita dell'utente
4. **SEMPRE** validare formato di area, incremento e ticket-id prima di costruire i nomi
5. **SEMPRE** fare `git pull origin main` prima di creare i branch
6. **PRE-FLIGHT OBBLIGATORIA** per il push su origin (rischio 🔴)
7. **MAI** aprire la PR senza commit — usare commit vuoto iniziale se necessario
8. **SEMPRE** creare la PR come **draft** al setup — sarà promossa a ready dal developer
