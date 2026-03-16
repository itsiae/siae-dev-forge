# Design: Allineamento Skill DevForge alle Best Practices Ufficiali

**Data:** 2026-03-15
**Autore:** Lorenzo (lead AI CC)
**Story Points:** 3 SP-Umano / 1 SP-Augmented
**Approccio:** Batch Incrementale (3 PR separate)

---

## Contesto

Le best practice ufficiali Claude Agent Skills (platform.claude.com) definiscono
standard per naming, description, struttura, progressive disclosure, checklist e
feedback loop. Un'analisi delle 30 skill DevForge ha identificato 3 gap prioritari.

## Riferimento

- Source: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Analisi: confronto eseguito il 2026-03-15 su tutte le 30 skill

---

## PR1: Standardizzare le 30 description

### Problema

Le description usano 4 stili diversi:
- `ALWAYS use when...` (EN imperativo) — 12 skill
- `OBBLIGATORIA per...` (IT imperativo) — 13 skill
- `Use when...` (EN senza ALWAYS) — 6 skill
- Stile nominale senza verbo (anomalo) — 5 skill

5 skill con stile anomalo (`siae-code-standards`, `siae-finops`, `siae-security`,
`siae-git-env`, `using-devforge`) hanno probabilità ridotta di auto-trigger.

### Soluzione

Formato unico per tutte le 30 description:

```
description: >
  [Verbo terza persona IT] [cosa fa].
  Trigger: [keyword list comma-separated].
```

### Regole
- Lingua: italiano per la frase descrittiva
- Keyword trigger: lingua originale (miste IT/EN come usate dai developer)
- Max 1024 char (già rispettato da tutte)
- Terza persona (best practice ufficiale)
- Nessun cambio al body della skill — solo frontmatter

### Esempi di conversione

| Skill | Prima | Dopo |
|---|---|---|
| siae-code-standards | `Standard di codifica SIAE multi-stack. Trigger: ...` | `Applica standard di codifica SIAE multi-stack (Java, TypeScript, Python, HCL). Trigger: ...` |
| siae-finops | `Review costi AWS, stima impatto PR, ...` | `Analizza costi AWS, stima impatto PR e identifica sprechi. Trigger: ...` |
| siae-security | `Sicurezza SIAE: OWASP Top 10, ...` | `Applica policy di sicurezza SIAE (OWASP Top 10, AWS, PII copyright). Trigger: ...` |
| siae-git-env | `Micro-skill di utility per la detection di GitHub CLI (gh).` | `Rileva la disponibilità di GitHub CLI (gh) e stabilisce GH_MODE. Trigger: ...` |
| using-devforge | `Usa all'inizio di ogni conversazione.` | `Stabilisce il framework di discovery e invocazione skill DevForge. Trigger: ...` |
| siae-tdd | `OBBLIGATORIA per qualsiasi scrittura di codice...` | `Guida il ciclo TDD per qualsiasi scrittura di codice di produzione. Trigger: ...` |
| siae-architecture | `ALWAYS use when evaluating architectural patterns...` | `Valuta pattern architetturali, crea diagrammi C4 e guida scelte di design. Trigger: ...` |

### Impatto
- File modificati: 30 SKILL.md (solo frontmatter `description`)
- Rischio: BASSO — nessun cambio logico
- Anche il Dynamic Skill Catalog in `using-devforge/SKILL.md` va aggiornato

---

## PR2: Progressive Disclosure per 3 skill > 470 righe

### Problema

3 skill sono vicine alla soglia di 500 righe senza usare progressive disclosure:
- `siae-service-logic-map` (488 righe)
- `siae-qa` (485 righe)
- `siae-microservices-map` (472 righe)

### Soluzione

Estrarre sezioni template/esempio in file ausiliari:

| Skill | File estratto | Contenuto |
|---|---|---|
| siae-service-logic-map | `TEMPLATES.md` | Template output L1/L2/L3, esempi |
| siae-qa | `XRAY-TEMPLATES.md` | Template Xray, esempi test case |
| siae-microservices-map | `TEMPLATES.md` | Template SYSTEM_MAP, esempi output |

### Regole
- Riferimenti 1 livello di profondità (SKILL.md → file ausiliario)
- TOC nei file ausiliari se > 100 righe
- Body SKILL.md scende sotto 350 righe dopo estrazione
- Zero cambi di logica — solo riorganizzazione

### Impatto
- File modificati: 3 SKILL.md + 3 nuovi file ausiliari
- Rischio: BASSO — riorganizzazione contenuto

---

## PR3: Checklist per debugging, data-engineering, iac

### Problema

3 skill con workflow complessi usano prosa invece di checklist strutturate `- [ ]`.
La best practice ufficiale raccomanda checklist copiabili che Claude traccia nel response.

### Soluzione

Aggiungere checklist all'inizio della sezione workflow di ogni skill:

**siae-debugging:**
```
Debug Progress:
- [ ] Step 1: Reproduci il problema (evidenza del fallimento)
- [ ] Step 2: Raccogli contesto (log, stacktrace, git blame)
- [ ] Step 3: Formula ipotesi di root cause
- [ ] Step 4: Verifica ipotesi (test mirato)
- [ ] Step 5: Applica fix + regression test
```

**siae-data-engineering:**
```
Pipeline Progress:
- [ ] Step 1: Identifica sorgente e schema input
- [ ] Step 2: Definisci trasformazione (mapping campi)
- [ ] Step 3: Implementa Glue job con test locale
- [ ] Step 4: Valida output (data quality checks)
- [ ] Step 5: Configura orchestrazione (Step Functions/EventBridge)
```

**siae-iac:**
```
IaC Progress:
- [ ] Step 1: Definisci risorse in _input.tf / _local.tf
- [ ] Step 2: Implementa modulo (.tf)
- [ ] Step 3: Configura live/ (terragrunt.hcl)
- [ ] Step 4: terraform plan — verifica diff
- [ ] Step 5: Security review (IAM least privilege, encryption)
```

### Regole
- Checklist inserite nel body esistente, non sostitutive della prosa
- Posizionate all'inizio della sezione workflow
- Wording coerente con le checklist delle altre skill DevForge

### Impatto
- File modificati: 3 SKILL.md (body only)
- Rischio: BASSO — aggiunta additiva

---

## Criteri di Accettazione

- [ ] PR1: Tutte le 30 description seguono il formato `[Verbo 3a persona] [cosa fa]. Trigger: [...]`
- [ ] PR1: Dynamic Skill Catalog in using-devforge aggiornato
- [ ] PR1: `bash tests/run-all.sh` passa (test strutturali)
- [ ] PR2: Le 3 skill target scendono sotto 350 righe
- [ ] PR2: I file ausiliari hanno TOC se > 100 righe
- [ ] PR2: Nessun riferimento > 1 livello di profondità
- [ ] PR3: Le 3 skill target hanno checklist `- [ ]` copiabili
- [ ] PR3: Le checklist sono coerenti con lo stile delle altre skill DevForge
- [ ] Tutte: Nessun cambio di comportamento — solo miglioramento strutturale

---

## Ordine di Esecuzione

1. PR1 (description) — indipendente, può partire subito
2. PR2 (progressive disclosure) — indipendente da PR1
3. PR3 (checklist) — indipendente da PR1 e PR2

Le 3 PR sono parallelizzabili ma si raccomanda merge sequenziale per evitare conflitti.
