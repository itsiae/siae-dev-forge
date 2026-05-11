# Task 13 — Verification Tone-Down (Body)

**Goal:** Ridurre il tono dogmatico di `siae-verification/SKILL.md`: 7+ "ALWAYS/NEVER/MANDATORY" → max 3. Aggiungi sezione "Eccezioni & proporzionalità".

**File coinvolti:**
- `skills/siae-verification/SKILL.md` (body, frontmatter già fatto in PR-4 task 11)

## Step 1 — Conta istanze attuali

```bash
grep -cE '\b(SEMPRE|MAI|NEVER|ALWAYS|MANDATORY)\b' skills/siae-verification/SKILL.md
```

Output atteso: ~7-9.

## Step 2 — Identifica le 7 istanze prime 60 righe

```bash
sed -n '1,60p' skills/siae-verification/SKILL.md | grep -nE '\b(SEMPRE|MAI|NEVER|ALWAYS|MANDATORY)\b'
```

## Step 3 — Strategia tone-down

| Mantieni inline (max 3) | Rimuovi/ammorbidisci |
|---|---|
| 1 nella legge di ferro ("Nessun 'fatto' senza prova") | "Si applica SEMPRE, senza eccezioni" → "Si applica nei contesti rilevanti (vedi Eccezioni)" |
| 1 nel HARD-GATE ("MAI prima di commit/PR") | "FERMATI" → "Considera di fermarti e..." (ma lasciamo HARD-GATE intatto se è critico) |
| 1 nel summary | "verifica non si salta MAI" → "verifica non va saltata in casi rilevanti" |

## Step 4 — Aggiungi sezione "Eccezioni & proporzionalità"

Posizione: dopo HARD-GATE, prima dei step.

```markdown
## Eccezioni & proporzionalità

La verifica deve essere **proporzionata al rischio del cambio**. Non tutti i cambi richiedono full battery di test.

| Tipo cambio | Verifica richiesta |
|---|---|
| Typo fix in commento o doc | Sintassi check (no test funzionali) |
| Comment-only change | Diff review, no test |
| Doc update (README, CHANGELOG) | Lint markdown, no test |
| Config rename (no semantic change) | Smoke test feature interessata |
| Bug fix isolato | Test unit + smoke test feature |
| Feature nuova / cross-module | Full battery (unit + integration + smoke) |

**Default**: piuttosto verificare in eccesso che in difetto. Ma in ottica DX, evita cerimoniale per cambi triviali.
```

## Step 5 — Edit body con tool Edit

Per ogni istanza identificata in Step 2:
1. Leggi contesto (Read tool)
2. Sostituisci con tono ammorbidito (Edit tool)

Attenzione: NON toccare il frontmatter description (già fatto in PR-4 task 11).
NON toccare HARD-GATE se è strutturalmente critico (es. il blocco "NESSUN CLAIM DI COMPLETAMENTO SENZA EVIDENZA FRESCA" mantieni se è il gate principale).

## Step 6 — Verifica conteggio finale

```bash
grep -cE '\b(SEMPRE|MAI|NEVER|ALWAYS|MANDATORY)\b' skills/siae-verification/SKILL.md
```

Output atteso: ≤3.

## Step 7 — Verifica skill ancora si attiva

Smoke test prompt:
- "il fix funziona, posso committare?" → siae-verification attivata
- "test passano" → idem
- "ho finito" → idem

## Step 8 — Commit

```bash
git add skills/siae-verification/SKILL.md
git commit -m "refactor(skills): siae-verification tone-down + 'Eccezioni & proporzionalità'

Ridotti 7+ 'ALWAYS/NEVER/MANDATORY' → 3 mantenuti (legge di ferro + HARD-GATE
critici). Aggiunta sezione Eccezioni: typo/comment-only/doc/config rename
non richiedono full battery. NO-REGRESSION 3 smoke prompt OK."
```

## Criteri accettazione

- Conteggio "ALWAYS/NEVER/MANDATORY/SEMPRE/MAI" ≤3
- Sezione "Eccezioni & proporzionalità" presente
- 3 smoke prompt attivano la skill
- Frontmatter intatto (PR-4 task 11)

## NO-REGRESSION

Tone-down è additivo + parafrastico, non rimuove gate. Skill deve continuare ad attivarsi sulle stesse condizioni.
