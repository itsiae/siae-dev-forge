---
name: using-devforge
description: >
  Usa all'inizio di ogni conversazione. Stabilisce come trovare e usare le
  skill siae-devforge, richiedendo l'invocazione dello Skill tool PRIMA di
  qualsiasi risposta incluse domande di chiarimento.
---

## ISTRUZIONE OBBLIGATORIA — ESEGUI PRIMA DI TUTTO

Stampa ADESSO, LETTERALMENTE, senza modifiche, il seguente blocco di testo (copia ogni carattere esattamente come appare, inclusi spazi e simboli):

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · AI Competence Center                  ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

Non riassumere. Non parafrasare. Non sostituire con un messaggio diverso. Stampa il banner sopra esattamente come appare, inclusa qualsiasi riga dopo la cornice di chiusura (es. stato versione). Poi procedi.

<EXTREMELY-IMPORTANT>
Se pensi che ci sia anche l'1% di possibilita' che una skill si applichi a quello che stai facendo, DEVI ASSOLUTAMENTE invocarla.

SE UNA SKILL SI APPLICA AL TUO TASK, NON HAI SCELTA. DEVI USARLA.

Questo non e' negoziabile. Non e' opzionale. Non puoi razionalizzare per evitarlo.

**OBBLIGO CATALOGO:** Per OGNI messaggio utente, DEVI scansionare il Dynamic Skill Catalog in fondo a questo documento. Leggi la colonna **INVOCA SE l'utente menziona** di ogni riga e confrontala col messaggio utente. Se trovi un match anche parziale, invoca la skill corrispondente PRIMA di rispondere. Non saltare mai la scansione del catalogo.
</EXTREMELY-IMPORTANT>

> 📊 **Dai repo itsiae:** L'adozione di skill sale dal 33% al 72% quando il loader le presenta automaticamente al SessionStart.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## Come Accedere alle Skill

**In Claude Code:** Usa lo `Skill` tool. Quando invochi una skill, il suo contenuto viene caricato e presentato — seguilo direttamente. Non usare mai il Read tool sui file delle skill.

**In altri ambienti:** Consulta la documentazione della tua piattaforma per come vengono caricate le skill.

# Usare le Skill

## La Regola

**Invoca le skill rilevanti o richieste PRIMA di qualsiasi risposta o azione.** Anche l'1% di possibilita' che una skill si applichi significa che devi invocarla per verificare. Se una skill invocata si rivela sbagliata per la situazione, non sei obbligato a usarla.

```dot
digraph skill_flow {
    "Messaggio utente ricevuto" [shape=doublecircle];
    "About to EnterPlanMode?" [shape=doublecircle];
    "Brainstorming gia' fatto?" [shape=diamond];
    "Invoca skill brainstorming" [shape=box];
    "Potrebbe applicarsi una skill?" [shape=diamond];
    "Invoca Skill tool" [shape=box];
    "Annuncia: 'Uso [skill] per [scopo]'" [shape=box];
    "Ha checklist?" [shape=diamond];
    "Crea TaskCreate per ogni item" [shape=box];
    "Segui la skill esattamente" [shape=box];
    "Rispondi (incluse domande di chiarimento)" [shape=doublecircle];

    "About to EnterPlanMode?" -> "Brainstorming gia' fatto?";
    "Brainstorming gia' fatto?" -> "Invoca skill brainstorming" [label="no"];
    "Brainstorming gia' fatto?" -> "Potrebbe applicarsi una skill?" [label="si"];
    "Invoca skill brainstorming" -> "Potrebbe applicarsi una skill?";

    "Messaggio utente ricevuto" -> "Potrebbe applicarsi una skill?";
    "Potrebbe applicarsi una skill?" -> "Invoca Skill tool" [label="si, anche 1%"];
    "Potrebbe applicarsi una skill?" -> "Rispondi (incluse domande di chiarimento)" [label="sicuramente no"];
    "Invoca Skill tool" -> "Annuncia: 'Uso [skill] per [scopo]'";
    "Annuncia: 'Uso [skill] per [scopo]'" -> "Ha checklist?";
    "Ha checklist?" -> "Crea TaskCreate per ogni item" [label="si"];
    "Ha checklist?" -> "Segui la skill esattamente" [label="no"];
    "Crea TaskCreate per ogni item" -> "Segui la skill esattamente";
}
```

## Git Operations Intercept

<EXTREMELY-IMPORTANT>
Stai per eseguire QUALSIASI operazione git (`git checkout -b`, `git commit`, `git push`, `git merge`, `git tag`, `gh pr create`)?

STOP. Prima verifica:
- Hai invocato `siae-git-workflow` in questa sessione?
  - NO → Invoca PRIMA siae-git-workflow. NON eseguire il comando git.
  - SI → Procedi seguendo le regole gia' caricate.

Stai per aprire una PR o dichiarare un branch "pronto"?
- Hai invocato `siae-finishing-branch` in questa sessione?
  - NO → Invoca PRIMA siae-finishing-branch. NON aprire la PR.
  - SI → Procedi seguendo il processo a 5 step gia' caricato.

**Ogni operazione git senza la skill caricata = branch naming sbagliato, commit non-conventional, push senza pre-flight, PR senza review.**

Nessuna operazione git e' "troppo semplice" per la skill. Un singolo `git commit` sbagliato inquina la history per sempre.
</EXTREMELY-IMPORTANT>

---

## EnterPlanMode Intercept

<EXTREMELY-IMPORTANT>
Stai per usare EnterPlanMode (il piano nativo di Claude Code)?

STOP. Prima verifica:
- Il brainstorming e' gia' stato fatto in questa sessione?
  - NO → Invoca PRIMA siae-brainstorming. NON entrare in EnterPlanMode.
  - SI → Procedi con EnterPlanMode / siae-subagent-development.

EnterPlanMode senza brainstorming = design non validato = lavoro da rifare.
</EXTREMELY-IMPORTANT>

Il flowchart sopra modella questo comportamento nel nodo "About to EnterPlanMode?".
Non bypassarlo mai, nemmeno per task "semplici".

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Skill invocate per singolo messaggio utente | 3 | Se ne servono di piu', il messaggio e' troppo ampio. Chiedi di decomporre. |
| Output max per skill check | 100 righe | Il loader deve essere veloce e trasparente. |

---

## Red Flags

Questi pensieri significano STOP — stai razionalizzando:

| Pensiero | Realta' |
|----------|---------|
| "E' solo una domanda semplice" | Le domande sono task. Controlla le skill. |
| "Ho bisogno di piu' contesto prima" | Il check delle skill viene PRIMA delle domande di chiarimento. |
| "Fammi esplorare il codebase prima" | Le skill ti dicono COME esplorare. Controlla prima. |
| "Posso controllare git/file velocemente" | I file non hanno contesto della conversazione. Controlla le skill. |
| "Fammi raccogliere informazioni prima" | Le skill ti dicono COME raccogliere informazioni. |
| "Questo non richiede una skill formale" | Se una skill esiste, usala. |
| "Mi ricordo questa skill" | Le skill evolvono. Leggi la versione corrente. |
| "Questo non conta come task" | Azione = task. Controlla le skill. |
| "La skill e' eccessiva" | Le cose semplici diventano complesse. Usala. |
| "Faccio solo questa cosa prima" | Controlla PRIMA di fare qualsiasi cosa. |
| "Mi sembra produttivo" | L'azione indisciplinata spreca tempo. Le skill lo prevengono. |
| "So cosa significa" | Conoscere il concetto != usare la skill. Invocala. |
| "E' solo un commit/push veloce" | Ogni commit senza siae-git-workflow = naming sbagliato, no pre-flight. |
| "Creo il branch e poi carico la skill" | Il branch naming si decide PRIMA di `git checkout -b`. Carica la skill. |
| "La PR e' banale, non serve finishing-branch" | Anche 1 file cambiato merita test verdi e diff review. Sempre. |
| "Pusho e poi sistemo" | Dopo il push non sistemi. La history e' pubblica. |

## Priorita' Skill

Quando piu' skill potrebbero applicarsi, usa questo ordine:

1. **Skill di processo prima** (brainstorming, debugging, git-workflow) — determinano COME affrontare il task
2. **Skill di implementazione dopo** (code-standards, frontend, iac, data-engineering) — guidano l'esecuzione

"Costruiamo X" → brainstorming prima, poi skill di implementazione.
"Fix questo bug" → debugging prima, poi skill specifiche del dominio.

## Gerarchia Istruzioni

Quando istruzioni provenienti da fonti diverse sono in conflitto, segui questa
gerarchia (la piu' alta vince):

| Priorita' | Fonte | Esempio |
|-----------|-------|---------|
| 1 (max) | `CLAUDE.md` del progetto | "Git flow obbligatorio su siae-dev-forge" |
| 2 | `CLAUDE.md` dell'utente (~/.claude/) | Preferenze personali |
| 3 | Skill del plugin (invocata) | Regole di siae-tdd, siae-code-standards |
| 4 | Agent prompt (subagent) | Istruzioni nel prompt del subagent |
| 5 (min) | Contesto ereditato dal parent | Skill caricate ma non nella allowlist |

**Regola:** se una skill dice X e CLAUDE.md dice Y, segui CLAUDE.md.
Se un agent prompt dice X e la skill invocata dice Y, segui la skill.
Il contesto parent e' sempre la fonte meno autorevole.

## Tipi di Skill

**Rigid** (TDD, debugging, brainstorming, git-workflow): Segui esattamente. Non adattare. Non saltare passi. La disciplina e' il valore.

**Flexible** (architecture, code-standards, security, iac, data-engineering, frontend, documentation): Adatta i principi al contesto. Usa il giudizio su quali sezioni applicare, ma non ignorare la skill.

La skill stessa ti dice quale tipo e'. In caso di dubbio, trattala come Rigid.

## Catena SDLC

7 fasi: Init → Design → Branching → Implementation → Testing → QA Gate → Release.
L'ordine e' sacro. Non saltare fasi. Il catalogo skill mostra quale skill si applica a ogni fase.

## DevForge Visual Design System

Tutte le skill seguono il DevForge Visual Design System. Vedi `design-system/devforge-visual.md` per banner, pre-flight cards, e codifica rischio.

Quando segui una skill, rispetta le convenzioni visive:
- **Banner** di apertura con nome skill e contesto
- **Pre-flight cards** per checklist e prerequisiti
- **Codifica rischio** (LOW / MEDIUM / HIGH / CRITICAL) per classificare operazioni

## Istruzioni Utente

Le istruzioni dicono COSA, non COME. "Aggiungi X" o "Fixa Y" non significa saltare i workflow.

## Verifica Prima del Completamento

<EXTREMELY-IMPORTANT>
Affermare che il lavoro e' completo senza verifica e' disonesta', non efficienza.
</EXTREMELY-IMPORTANT>

```
REQUIRED SUB-SKILL: siae-verification
```

Prima di dichiarare qualsiasi task "fatto", "completato", "fixato", o "funzionante",
invoca la skill `siae-verification` che implementa il protocollo completo a 5 step:
**IDENTIFICA → ESEGUI → LEGGI → VERIFICA → AFFERMA**.

Non dire "Perfetto!", "Fatto!", "Completato!" prima di aver eseguito la verifica. Mai.
