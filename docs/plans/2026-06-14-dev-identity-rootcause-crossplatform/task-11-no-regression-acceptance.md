# Task 11 — No-regression + verifica 13 criteri + registrazione test

**Stato:** PENDING
**Dipende da:** task-01..task-10
**File:** suite test, `plugin.json` + `marketplace.json` (bump versione), `CHANGELOG.md`

## Obiettivo
Chiudere il design: verificare i 14 criteri di accettazione, no-regression, registrare i nuovi test.

## Attività
1. Eseguire l'intera suite (bash zero-loss + python) → verde.
2. No-regression:
   - `user`/`user_raw`/`user_source`/`actor_canonical` invariati (AC12);
   - `auth_email`/`auth_account_uuid` invariati su sessione con `~/.claude.json` (AC5);
   - suite zero-loss esistente verde (no perdita dati sul path python3 — task-09).
3. Mappare ogni nuovo test ai **14** criteri di accettazione del design (sez. 7):
   AC1/AC2→task-01, AC3→task-02, AC4/AC5→task-03, AC6→task-06, AC7→task-07, AC8→task-04,
   AC9→task-00 (verifica EMPIRICA spike, NON suite automatizzata; task-08 fornisce il fallback documentato),
   AC10→task-08, AC11→task-05, AC12→questo task, AC13→task-10, **AC14 (zero-loss numerico)→task-09**.
4. Aggiornare il conteggio test no-regression se il repo lo traccia
   (cfr. memoria "PR #252 test count drift": hook aggiunto ma count non bumpato).
5. Bump versione in `plugin.json` E `marketplace.json` (memoria "Plugin version dual source": entrambi obbligatori).
6. Aggiornare `CHANGELOG.md`.

## Criteri di accettazione
Tutti i 14 AC del design verdi; suite verde; conteggi/versione allineati; CHANGELOG aggiornato.

## No-regression
Questo task È la verifica no-regression complessiva: nessun comportamento esistente alterato,
solo aggiunte di copertura cross-platform.
