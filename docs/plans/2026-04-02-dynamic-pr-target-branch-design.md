# Dynamic PR Target Branch Detection

**Data:** 2026-04-02
**Stima:** 3 SP
**Stato:** Approvato

---

## Contesto

Il plugin DevForge crea PR con `--base sviluppo` hardcoded in `siae-finishing-branch`.
Nella realta' SIAE, i feature/fix/hotfix branch vengono staccati da branch `release/**`,
non da `sviluppo`. La PR dovrebbe puntare al branch da cui e' stato staccato il branch
corrente, mai al default branch (main) a meno che non sia un branch `release/*`.

## Decisioni

| Decisione | Scelta | Alternative scartate |
|-----------|--------|----------------------|
| Metodo di rilevamento parent | `git merge-base` con euristica + conferma utente se ambiguo | Chiedere sempre (troppo invasivo), salvare parent alla creazione (stato fragile) |
| Candidati parent | `release/*` + `sviluppo` | Solo `release/*` (non copre tutti i repo) |
| Soglia ambiguita' | 3 commit di differenza tra candidati | Nessuna soglia (troppi false positive) |
| Regola default branch | Solo `release/*` puo' aprire PR verso `main` | Blocco totale verso main (troppo restrittivo per release) |

## Trade-off

- **Pro:** Funziona anche per branch creati fuori dal plugin, nessuno stato persistente da mantenere
- **Contro:** Puo' fallire se la storia git e' stata pesantemente riscritta (rebase/squash estensivi)
- **Mitigazione:** In caso di dubbio, chiede sempre all'utente

## Algoritmo di Rilevamento Parent Branch

```
1. RILEVA branch corrente: git branch --show-current
2. DETERMINA tipo:
   - Se release/* → target = main (default branch). Fine.
   - Se feature/*, fix/*, refactor/*, hotfix/* → vai a step 3
3. FETCH e LISTA candidati parent:
   - git fetch origin
   - git branch -r --list 'origin/release/*' + 'origin/sviluppo'
4. Se 0 candidati:
   → CHIEDI all'utente: "Non ho trovato branch release/* o sviluppo.
     Quale branch e' il target della PR?"
5. Se 1 candidato:
   → PROPONI con conferma: "Il parent branch rilevato e' <branch>. Confermi?"
6. Se 2+ candidati:
   → CALCOLA merge-base per ciascuno:
     - Per ogni candidato: git merge-base HEAD origin/<candidato>
     - Calcola distanza: git rev-list --count <merge-base>..HEAD
     - Il candidato con distanza minore e' il "best match"
7. Se best match e' chiaro (distanza unica minima, o diff > 3 con il secondo):
   → "Il parent branch piu' probabile e' <branch> (N commit di distanza). Confermi?"
8. Se ambiguo (2+ candidati con distanza simile, diff ≤ 3):
   → "Ho trovato piu' branch candidati: <lista con distanze>.
      Quale e' il target della PR?"
9. GUARDRAIL: se il target rilevato e' main e il branch NON e' release/*:
   → BLOCCO: "Solo release/* puo' aprire PR verso main. Scegli un altro target."
```

## Criteri di Accettazione

- [ ] AC1: Il plugin rileva automaticamente il parent branch tramite `git merge-base`
      tra il branch corrente e i candidati (`release/*`, `sviluppo`)
- [ ] AC2: Se un solo candidato con match chiaro, lo propone con conferma utente
- [ ] AC3: Se ambiguita' (2+ candidati con distanza ≤ 3 commit), chiede all'utente
      di scegliere dalla lista
- [ ] AC4: Se nessun candidato trovato, chiede all'utente di inserire il target
- [ ] AC5: Se il target rilevato e' `main` e il branch non e' `release/*`, blocca e
      chiede un altro target
- [ ] AC6: Il target rilevato viene usato in tutti gli step di `siae-finishing-branch`
      (diff, log, PR creation) al posto di `sviluppo` hardcoded
- [ ] AC7: `siae-git-workflow` aggiornato per riflettere che i feature branch possono
      partire da `release/*` oltre che da `sviluppo`
- [ ] AC8: L'URL di fallback (FALLBACK_MODE) usa il parent branch rilevato al posto
      di `sviluppo`

## File da Modificare

| File | Tipo modifica | Descrizione |
|------|---------------|-------------|
| `skills/siae-finishing-branch/SKILL.md` | Major | Nuovo Step 0b (rileva parent), aggiornamento Step 1/3/5 per usare parent dinamico |
| `skills/siae-git-workflow/SKILL.md` | Minor | Aggiornamento sezione 2 (branch naming) e sezione 8 (nuova feature) |

## Piano Implementativo

### Step 1 — Aggiungere Step 0b "Rileva Parent Branch" in siae-finishing-branch [AC1, AC2, AC3, AC4, AC5]

Aggiungere una nuova sezione tra Step 0 (Environment Check) e Step 1 (Verifica Stato).
La sezione contiene l'algoritmo completo di rilevamento con i comandi git e le regole
di interazione utente. Il risultato e' `$PARENT_BRANCH`.

### Step 2 — Aggiornare Step 1, 3, 4, 5 di siae-finishing-branch per usare $PARENT_BRANCH [AC6, AC8]

Sostituire ogni occorrenza di `sviluppo` hardcoded con `$PARENT_BRANCH`:
- Step 1: `git log origin/sviluppo..HEAD` → `git log origin/$PARENT_BRANCH..HEAD`
- Step 3: `git diff origin/sviluppo...HEAD` → `git diff origin/$PARENT_BRANCH...HEAD`
- Step 4: `git log origin/sviluppo..HEAD` → `git log origin/$PARENT_BRANCH..HEAD`
- Step 5 GH_MODE: `--base sviluppo` → `--base $PARENT_BRANCH`
- Step 5 FALLBACK_MODE: URL con `sviluppo` → URL con `$PARENT_BRANCH`
- Pre-flight card Step 5: Target `sviluppo` → Target `$PARENT_BRANCH`

### Step 3 — Aggiornare siae-git-workflow [AC7]

- Sezione 2: Sostituire "Creare sempre la feature branch da **sviluppo**" con
  "Creare la feature branch dal branch di riferimento (tipicamente `release/*` o `sviluppo`)"
- Sezione 7: Rimuovere "Feature branch sempre da sviluppo (mai da main)"
- Sezione 8: Aggiornare esempio "Nuova feature" per mostrare checkout da `release/*`
