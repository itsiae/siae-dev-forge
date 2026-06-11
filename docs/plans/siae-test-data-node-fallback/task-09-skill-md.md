# Task 09 — SKILL.md Passo 0: detection Node.js + Passo 6-bis

**Stato:** [PENDING]

**Goal:** Aggiornare `skills/siae-test-data/SKILL.md` per aggiungere Node.js come
secondo fallback nel Passo 0 e il Passo 6-bis con il comando CLI `node generate_profiles.js`.

**File coinvolti:**
- `skills/siae-test-data/SKILL.md` — MODIFICA

> **Nota TDD:** SKILL.md è documentazione, non codice eseguibile → nessun test
> unitario applicabile (vedi regola TDD: "Documentazione → NO"). La verifica è
> manuale (lettura diff) + smoke test Bash del comando Node.js.

---

## Step 1 — Smoke test RED (verifica baseline)

```bash
cd /Users/mazzacuv/Git/siae-dev-forge/skills/siae-test-data
grep -n "NODE_OK\|nodejs\|Passo 6-bis" SKILL.md
```

Output atteso: nessun match (le modifiche non sono ancora presenti)

---

## Step 2 — Modifica SKILL.md

### 2a — Passo 0: aggiungi detection Node.js

Individua il blocco attuale (dopo il check Python):

```
Altrimenti (path Claude-native, passi 1-5):
```

Sostituisci con:

```markdown
Altrimenti, se Python non è disponibile, prova **Node.js**:

```bash
(node --version 2>/dev/null || nodejs --version 2>/dev/null) && echo NODE_OK
```

> **Windows:** su alcune installazioni il binario è `nodejs`; il comando prova entrambi.

Se Node.js 10+ è disponibile:
- Avvia il pre-warming del data_store Node.js emettendo il comando sotto **nello stesso
  turno** della prima `AskUserQuestion`. Non aspettare il risultato.
  ```bash
  # Eseguire da REPO ROOT (non da siae-test-data/scripts)
  node -e "const p=require('path'),f=require('fs'),r=p.join(process.cwd(),'skills','siae-test-data','references');['nomi_italiani.json','nomi_esteri.json','forme_giuridiche.json','cap_citta.json','belfiore_comuni.json','belfiore_esteri.json'].forEach(n=>JSON.parse(f.readFileSync(p.join(r,n))))" 2>/dev/null
  ```
  > Eseguire da **repo root** (dove risiede `skills/`). Se Claude ha già fatto
  > `cd siae-test-data/scripts`, usare `process.cwd()+'/../../references'` o il
  > path assoluto del workspace.
- Dopo aver raccolto tutti i parametri del wizard, salta al **Passo 6-bis (Esecuzione Node.js)**.

Altrimenti (né Python né Node.js disponibili — path Claude-native, passi 1-5):
- Se N > 10: avvisa l'utente — "Generazione Claude-native per N={N} profili senza runtime
  locale richiede ~{N×12}s. Installa Python 3.8+ o Node.js 10+ per ridurre a <2s."
- Emetti tutte le **Read del Passo 2** nello stesso turno della prima `AskUserQuestion`.
- Al Passo 2 salta le Read già emesse al Passo 0.
```

### 2b — Aggiungi Passo 6-bis prima di Passo 6

Inserisci prima della riga `### Passo 6 — Scorciatoia Python`:

```markdown
### Passo 6-bis — Scorciatoia Node.js (solo se Passo 0 ha rilevato Node.js 10+)

```bash
cd siae-test-data/scripts
node generate_profiles.js \
  --categorie <CSV> \
  --nazionalita <ITA|UE|EXTRA-UE|ITA,UE|ITA,EXTRA-UE|UE,EXTRA-UE|ITA,UE,EXTRA-UE> \
  --distribuzione "<pct_ITA>,<pct_UE>,<pct_EXTRA-UE>" \
  --forme-giuridiche <CSV> \
  --profilo <FULL|LIGHT> \
  --quantita <5|10|25|50|100|500> \
  --formato <JSON|CSV> \
  [--skip-validation] \
  --output <path>
```

Lo script Node.js è il secondo fallback opzionale. Python ha priorità se disponibile.
Edge case indirizzo (14 pattern) e formato Markdown non sono supportati nella versione
Node.js — usare il path Claude-native se richiesti.
```

---

## Step 3 — Verifica smoke test GREEN

```bash
cd /Users/mazzacuv/Git/siae-dev-forge/skills/siae-test-data
grep -n "NODE_OK\|Passo 6-bis\|node generate_profiles" SKILL.md
```

Output atteso: almeno 3 match (NODE_OK, Passo 6-bis, node generate_profiles.js)

Smoke test CLI Node.js:
```bash
cd skills/siae-test-data/scripts
node generate_profiles.js --categorie PRIVATO --nazionalita ITA --quantita 2 --formato JSON --skip-validation 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))"
```
Output atteso: `2`

---

## Step 4 — Commit

```
docs(siae-test-data): SKILL.md Passo 0 + Passo 6-bis — Node.js fallback detection e CLI
```

## Criteri di accettazione

- [ ] `grep "NODE_OK" SKILL.md` → match trovato
- [ ] `grep "Passo 6-bis" SKILL.md` → match trovato
- [ ] Smoke test CLI Node.js → output `2` (2 profili JSON validi)
- [ ] Detection order nel testo: Python → Node.js → Claude-native
