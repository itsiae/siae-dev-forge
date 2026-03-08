---
name: siae-writing-skills
description: >
  Use when creating new DevForge skills — covers persuasion principles, TDD
  methodology for documentation, and SIAE-specific patterns. Trigger: creare
  una nuova skill, migliorare skill esistenti, progettare behaviour change.
---

# Scrivere Skill DevForge Efficaci — Guida per Autori

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · WRITING SKILLS                     ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** Meta (creazione skill)

---

## Obiettivo

Questa skill insegna a scrivere skill DevForge che **funzionano** — non solo documentazione,
ma strumenti di behaviour change che modificano realmente il modo in cui Claude opera.

Una skill ben scritta non si limita a descrivere un processo: lo **impone** attraverso
principi di persuasione, protocolli anti-razionalizzazione e verifica strutturata.

---

## I 3 Pilastri di una Skill Efficace

### 1. CSO — Claude Search Optimization

La `description` nel frontmatter e' il campo piu' importante della skill.
Claude la usa per decidere se caricarla. Se la description e' sbagliata, la skill non viene mai invocata.

**Regole:**
- La description descrive **trigger conditions ONLY**, mai il workflow
- Usa verbi all'imperativo: "Use when...", "Trigger: ..."
- Includi keyword che Claude associa al task: "bug fix", "feature", "commit"
- NON riassumere cosa fa la skill — descrivi QUANDO si applica
- Massimo 3 righe — Claude scansiona velocemente

**Esempio buono:**
```yaml
description: >
  Use when about to claim work is complete, fixed, or passing — requires
  running verification commands before any success claims. Trigger: prima
  di commit, PR, task complete, dichiarazioni di successo.
```

**Esempio cattivo:**
```yaml
description: >
  Questa skill implementa un protocollo di verifica a 5 step che garantisce
  la qualita' del codice attraverso esecuzione di test e analisi dell'output.
```

### 2. Struttura che Forza il Comportamento

Una skill non e' un documento da leggere. E' un **protocollo da eseguire**.

| Elemento | Funzione | Obbligatorio? |
|----------|----------|---------------|
| Frontmatter YAML | Trigger e metadata | Si |
| Banner DevForge | Identita' visiva, autorevolezza | Si |
| Legge di Ferro | Principio non negoziabile (1 frase) | Si (Rigid) |
| Step numerati | Workflow eseguibile | Si (Task) |
| Tabella Anti-Razionalizzazione | Blocca scorciatoie cognitive | Si (Rigid) |
| Classificazione Rischio | Pre-flight card awareness | Si |
| Vincoli | Guardrail espliciti | Si |
| Reference files | Dettagli per chi vuole approfondire | Consigliato |

### 3. Principi di Persuasione

Le skill DevForge usano principi di scienza della persuasione per massimizzare
la compliance di Claude. Vedi [reference/persuasion-principles.md](reference/persuasion-principles.md)
per l'approfondimento completo.

**Quick Reference — Principi per tipo di skill:**

| Tipo Skill | Top 3 Principi | Esempio |
|------------|----------------|---------|
| **Rigid** (TDD, verification, debugging) | Authority, Commitment, Scarcity | Legge di Ferro, Iron Law, "non negoziabile" |
| **Flexible** (architecture, standards) | Social Proof, Authority, Consistency | Pattern osservati in 60+ repo, standard SIAE |
| **Meta** (using-devforge, writing-skills) | Authority, Unity, Reciprocity | "DevForge Visual Design System", "La skill ti guida" |

---

## Workflow per Creare una Skill

### Step 1 — Definisci il Problema

Prima di scrivere, rispondi a queste domande:

1. **Quale comportamento vuoi cambiare?** (non "cosa vuoi documentare")
2. **Quale razionalizzazione impedisce il comportamento corretto?**
3. **Qual e' il costo della non-compliance?** (bug, sicurezza, debito tecnico)
4. **Rigid o Flexible?** Le skill di processo sono Rigid. Le skill di dominio sono Flexible.

### Step 2 — Scrivi i Test

Applica TDD alla documentazione. Vedi [reference/testing-skills.md](reference/testing-skills.md).

1. Scrivi un prompt di test che dovrebbe attivare la skill
2. Scrivi un "pressure scenario" che tenta di bypassare la skill
3. Definisci i criteri di successo (cosa deve fare Claude con la skill attiva)

### Step 3 — Scrivi il SKILL.md

🟡 MEDIO — Mostra pre-flight card prima di procedere

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-writing-skills",
  "context": [
    {"emoji": "🛠️", "label": "Operazione", "value": "Creazione directory skill"},
    {"emoji": "📁", "label": "Skill", "value": "<nome skill che si sta creando>"}
  ],
  "actions": [
    {"emoji": "✏️", "label": "Crea directory", "path": "skills/<nome-skill>/"}
  ],
  "reason": "La creazione della directory introduce un nuovo percorso nel plugin; un nome errato o duplicato rompe il catalogo skill e la discovery automatica.",
  "ifno": "La directory skill non viene creata e nessun file viene scritto."
}' | python3 design-system/generate-card.py
```

🟡 MEDIO — Mostra pre-flight card prima di procedere

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-writing-skills",
  "context": [
    {"emoji": "🛠️", "label": "Operazione", "value": "Scrittura SKILL.md e reference files"},
    {"emoji": "📁", "label": "Skill", "value": "<nome skill che si sta creando>"}
  ],
  "actions": [
    {"emoji": "✏️", "label": "Scrivi SKILL.md", "path": "skills/<nome-skill>/SKILL.md"},
    {"emoji": "✏️", "label": "Scrivi reference files", "path": "skills/<nome-skill>/reference/"}
  ],
  "reason": "La scrittura di SKILL.md e dei file reference definisce il comportamento della skill in modo permanente; errori nel frontmatter o nella struttura impediscono la corretta attivazione da parte di Claude.",
  "ifno": "SKILL.md e i file reference non vengono scritti; la skill non esiste nel plugin."
}' | python3 design-system/generate-card.py
```

Usa il template in [reference/skill-template.md](reference/skill-template.md).

**Budget token:** massimo **500 righe** per SKILL.md. Sposta i dettagli nei file `reference/`.

**Struttura obbligatoria:**
1. Frontmatter YAML (name, description)
2. Banner DevForge
3. Tipo e Fase SDLC
4. Legge di Ferro (per skill Rigid)
5. "Quando si Applica"
6. Step numerati con etichette rischio
7. Tabella Anti-Razionalizzazione (per skill Rigid)
8. Classificazione Rischio Operazioni
9. Vincoli
10. Risorse Aggiuntive (link a reference/)

### Step 4 — Cross-referencing

🟡 MEDIO — Mostra pre-flight card prima di procedere

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-writing-skills",
  "context": [
    {"emoji": "🛠️", "label": "Operazione", "value": "Modifica using-devforge per registrazione"},
    {"emoji": "📁", "label": "Skill", "value": "<nome skill che si sta creando>"}
  ],
  "actions": [
    {"emoji": "✏️", "label": "Registra skill in using-devforge", "path": "skills/using-devforge/SKILL.md"}
  ],
  "reason": "La modifica di using-devforge aggiorna il catalogo centrale del plugin; un errore nella registrazione rende la skill invisibile o rompe la discovery per tutti i developer.",
  "ifno": "La skill non viene registrata in using-devforge e non sarà inclusa nel catalogo attivo del plugin."
}' | python3 design-system/generate-card.py
```

Per referenziare altre skill, usa il pattern `REQUIRED SUB-SKILL:`:

```
REQUIRED SUB-SKILL: siae-verification
```

Questo dice a Claude di invocare la skill specificata come prerequisito.
**NON usare** `@file-path` o path assoluti — usa sempre il nome della skill.

### Step 5 — Valida

🟡 MEDIO — Mostra pre-flight card prima di procedere

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-writing-skills",
  "context": [
    {"emoji": "🛠️", "label": "Operazione", "value": "Test di attivazione con prompt"},
    {"emoji": "📁", "label": "Skill", "value": "<nome skill che si sta creando>"}
  ],
  "actions": [
    {"emoji": "✏️", "label": "Esegui prompt di attivazione", "path": "skills/<nome-skill>/SKILL.md"}
  ],
  "reason": "Il test di attivazione verifica che la skill venga caricata da Claude nel contesto corretto; un test eseguito su una skill mal configurata può dare falsi positivi e mascherare problemi di trigger.",
  "ifno": "Il test di attivazione non viene eseguito e non si ha garanzia che la skill funzioni correttamente in produzione."
}' | python3 design-system/generate-card.py
```

Checklist di validazione:

- [ ] `name` e' lowercase con trattini, max 64 char
- [ ] `description` descrive trigger conditions, non workflow
- [ ] SKILL.md e' sotto 500 righe
- [ ] Banner DevForge presente
- [ ] Ogni step ha etichetta rischio
- [ ] Tabella anti-razionalizzazione presente (se Rigid)
- [ ] Classificazione rischio operazioni presente
- [ ] Vincoli definiti
- [ ] Reference files linkati da SKILL.md
- [ ] Test di attivazione superato (prompt naturale → skill si attiva)

---

## Errori Comuni

| Errore | Perche' e' un Problema | Fix |
|--------|----------------------|-----|
| Description troppo lunga | Claude non la legge tutta | Max 3 righe, solo trigger |
| Description descrive il workflow | Claude non trova i trigger | Riscrivi con "Use when..." |
| Nessuna Legge di Ferro | La skill non ha un punto focale | Aggiungi una frase non negoziabile |
| Step senza etichette rischio | Le pre-flight card non si attivano | Classifica ogni step |
| Nessuna tabella anti-razionalizzazione | Claude puo' bypassare la skill | Aggiungi 8-12 razionalizzazioni |
| SKILL.md troppo lungo (> 500 righe) | Consumo contesto eccessivo | Sposta dettagli in reference/ |
| Path assoluti ai file | Si rompono se il plugin si sposta | Usa nomi skill e link relativi |
| Nessun test | Non sai se la skill funziona | Scrivi prompt di test e pressure scenario |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Analisi requisiti skill | 🟢 Sicuro | No |
| Lettura skill esistenti come riferimento | 🟢 Sicuro | No |
| Creazione directory skill | 🟡 Medio | Si |
| Scrittura SKILL.md e reference files | 🟡 Medio | Si |
| Modifica using-devforge per registrazione | 🟡 Medio | Si |
| Test di attivazione con prompt | 🟡 Medio | Si |

---

## Vincoli

1. **OGNI** skill generata deve seguire il Visual Design System DevForge
2. **MAI** superare 500 righe per SKILL.md
3. **MAI** usare path assoluti — solo nomi skill e link relativi
4. **SEMPRE** includere almeno una tabella anti-razionalizzazione per skill Rigid
5. **SEMPRE** classificare le operazioni per livello di rischio
6. **PRE-FLIGHT OBBLIGATORIA** per scrittura file (rischio >= 🟡)

---

## Risorse Aggiuntive

- [reference/persuasion-principles.md](reference/persuasion-principles.md) — 7 principi Cialdini adattati a DevForge
- [reference/testing-skills.md](reference/testing-skills.md) — TDD per documentazione (RED-GREEN-REFACTOR su skill)
- [reference/skill-template.md](reference/skill-template.md) — Template SKILL.md pronto all'uso
