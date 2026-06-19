---
status: approved
date: 2026-06-19
topic: stop-gate-session-lifecycle-fix
complexity: alta
sp_human: 5
sp_augmented: 2
---

# Design — Fix lifecycle stop-gate / session_end DevForge

## 1. Contesto e causa radice

Il hook `Stop` di Claude Code **fira a ogni fine-turno** (confermato da docs ufficiali:
"Stop hooks fire whenever Claude finishes responding, not only at task completion").
`hooks/stop-gate` però lo tratta come **fine-sessione**, con due conseguenze dannose:

1. **Blocco a torto del git gate** (bug primario). `_devforge_emit_session_end`
   (`stop-gate:48-130`) viene raggiunto su stdin vuoto (`stop-gate:133-136`) o quando
   l'ultimo messaggio non contiene una keyword di completamento (`stop-gate:183-186`) —
   cioè la maggioranza dei turni. Al suo interno, `stop-gate:127-129`:
   ```bash
   rm -f "$SESSION_START_NS_FILE" "$SESSION_COMMITS_FILE" "$SESSION_SKILLS_FILE"
   ```
   cancella il ledger delle skill di sessione. Pattern fatale:
   - Turno N: invoco `siae-git-workflow` → `post-skill` scrive `.devforge-session-skills`.
     Fine turno senza claim → Stop → `session_end` → **wipe del ledger**.
   - Turno N+1: `git commit` → `pre-commit:110` legge il file vuoto → **BLOCCATO**,
     pur avendo invocato la skill.

   Un guard via `mkdir` (`stop-gate:48-51`) rende il danno "una volta sola" per sessione
   invece che "mai". È una regressione del fix PR #313 Fase 3: lo `rm` non è più
   per-turno esplicito ma vive dentro un `session_end` comunque raggiungibile per-turno.

   **Evidenza empirica** (stato vivo letto 2026-06-19): guard PRESENTE +
   `.devforge-session-start-ns` vuoto (cancellato) + `.devforge-session-skills`
   ri-popolato da `post-skill` dopo il wipe → `session_end` è scattato a metà sessione.

2. **Telemetria `session_end` inaccurata** (bug secondario). Essendo emesso al primo
   turno non-completion, i campi `skills_used_count` / `commits_count` /
   `cost_estimate_eur` riflettono solo il lavoro fino a quel turno, **sotto-contando**
   la sessione reale. Il guard impedisce una correzione successiva.

**Vincolo di piattaforma**: NON esiste oggi un hook `SessionEnd` registrato
(`hooks/hooks.json` ha solo `Stop`). Claude Code però **espone** `SessionEnd`
(verificato via docs ufficiali): fira su `clear`/`resume`/`logout`/`prompt_input_exit`/
`other`, è solo-cleanup (non può bloccare), e **non è garantito su crash/`kill -9`**.

## 2. Decisione architetturale (ADR)

**ADR-1 — Separazione delle responsabilità del lifecycle.**

| Hook | Responsabilità DOPO il fix | Cosa NON fa più |
|---|---|---|
| `Stop` (per-turno) | Solo **gate bloccanti**: retrospective gate + verification gate. Flush opportunistico backlog (zero-loss, invariato). | Non emette `session_end`. **Non cancella** stato di sessione. |
| `SessionEnd` (NUOVO) | Emette `session_end` con conteggi **accumulati** fino alla fine reale + flush finale. | Non cancella i file di stato (vedi ADR-2). Non blocca (non può). |
| `SessionStart` | **Unico owner del reset/preserve** dello stato per `source` (già implementato, `session-start:420-477`). | — |

Razionale: `session_end` deve riflettere la sessione intera → va emesso quando la
sessione finisce davvero (`SessionEnd`), non a ogni turno (`Stop`). I conteggi sono
accurati perché i counter su file si accumulano fino al `SessionEnd`.

**ADR-2 — Il reset dello stato vive SOLO in `SessionStart`, mai nell'hook di fine.**

`SessionEnd` con `reason=resume` è seguito da un `SessionStart` con `source=resume` che
**preserva** le skill (`session-start:454-457`). Se `SessionEnd` cancellasse il ledger,
il preserve troverebbe un file vuoto → contraddizione. Quindi `SessionEnd` **non**
fa `rm` dei file di stato: il reset è delegato interamente a `SessionStart`, che già
distingue `startup` (reset) da `resume|clear|compact|unknown` (preserve).

**Robustezza all'ordine di esecuzione (ISSUE-8 review)**: la sequenza esatta
`SessionEnd(resume)` ↔ `SessionStart(resume)` non è garantita da docs ufficiali. Ma
il fix è **order-safe** per costruzione: (a) su `resume` `SessionStart` *preserva* lo
stato (non resetta), quindi i counter restano leggibili da `SessionEnd` qualunque sia
l'ordine; (b) su fine non-resume (logout/clear/exit) non c'è un `SessionStart`
concorrente nello stesso processo. L'unico reset distruttivo (`source=startup`) avviene
solo all'avvio di una sessione fresca, non preceduta da un `SessionEnd(resume)`. Nessuna
dipendenza dall'ordine → nessun rischio di conteggi-zero su resume.

**ADR-3 — Idempotenza via guard, dedup tra `SessionEnd` e recovery.**

Il guard `.devforge-session-end-guard` (mkdir-lock) resta per garantire emissione
**at-most-once per segmento di sessione**. `SessionStart` lo pulisce all'avvio
(`session-start:340`), così ogni segmento può emettere una volta.

**ADR-4 — Limite crash documentato, no over-engineering.**

Su crash/`kill -9` né lo `Stop` (interrotto) né `SessionEnd` (non garantito) emettono il
summary: il `session_end` di quella sessione manca. È lo **stesso limite della
piattaforma** ed è accettabile: gli eventi della sessione (skill_invoked, commit,
ecc.) sono già drenati dal flush opportunistico su `Stop`/`SessionStart` (zero-loss),
si perde solo la riga riassuntiva. NON si aggiunge orphan-recovery in `SessionStart`
(attribuzione al sid precedente complessa, counter sono file globali → rischio
mis-attribuzione superiore al beneficio).

## 3. Componenti

### 3.1 `hooks/session-end` (NUOVO)
Estrae da `stop-gate` la funzione `_devforge_emit_session_end` **senza** il blocco `rm`
(righe 127-129). Logica:
1. `set -euo pipefail`, source `logger.sh`, `devforge_init_session`.
2. Guard mkdir `.devforge-session-end-guard` → se esiste, exit 0 (già emesso).
3. Chiusura ultima skill via `.devforge-skill-start` (timestamp chaining) — invariata.
4. Lettura counter: `.devforge-session-start-ns`, `.devforge-session-commits`,
   `.devforge-session-skills` → conteggi accumulati.
5. Refresh token-collector + costruzione payload `session_end` (schema **identico**
   all'attuale `stop-gate:104-105`: `token_state_complete`, `by_*`, ecc.).
6. `devforge_log_timed "session_end" ...` + `task_adoption` + recap stderr + flush.
7. **NESSUN `rm`** dei file di stato (delegato a `SessionStart`).
8. `echo '{}'; exit 0`.

### 3.2 `hooks/stop-gate` (MODIFICA)
- Rimuovere il corpo di `_devforge_emit_session_end` (intera funzione migra in
  `hooks/session-end`); in particolare spariscono le righe `rm -f` (127-129) dello
  stato di sessione.
- Sostituire le 3 chiamate a `_devforge_emit_session_end` con `exit 0` puro (lo Stop
  deve solo *permettere* lo stop, non emettere telemetria di fine):
  - `stop-gate:134` (stdin vuoto)
  - `stop-gate:184` (no-completion keyword)
  - `stop-gate:246` (verification OK)
- **Aggiornare il commento `stop-gate:188`** ("file was cleaned in telemetry block
  above"): diventa falso dopo il fix (i file NON sono più cancellati). Riscriverlo per
  riflettere che `SKILLS_LIST` è letto in-memory e lo stato persiste (ISSUE-6 review).
- **Retro-block path** (`stop-gate:204`, già senza emit): quando il retrospective gate
  blocca, la sessione NON è finita → nessun `session_end`. Corretto: dopo che l'utente
  completa la retro e ri-ferma, `SessionEnd` emette il summary. Documentato qui per
  chiarezza (ISSUE-2 review).
- **Conservare**: flush opportunistico iniziale (`stop-gate:27`, zero-loss),
  retrospective gate (`stop-gate:193-204`), verification gate (`stop-gate:206-265`).
- (Opzionale, nice-to-have) guard anti-block-cap: `stop_hook_active==true` → exit 0.
  *Fuori scope di questo fix salvo richiesta esplicita.*

### 3.3 `hooks/session-start` (MODIFICA minima)
- Nessun cambiamento al reset (già corretto). Verificare solo che il flush iniziale e
  la pulizia guard (`session-start:340`) restino prima di qualsiasi call fallibile.

### 3.4 `hooks/hooks.json` (MODIFICA)
- Registrare evento `SessionEnd` (matcher `""` = tutti i `reason`) →
  `run-hook.cmd session-end`.

### 3.5 Test con contatori hardcoded (MODIFICA — ISSUE-4 review)
Aggiungere un comando in `hooks.json` rompe i contatori hardcoded:
- `tests/hooks/hooks-json-var-expansion.test.sh:33` e `:66` asseriscono `-ne 26` sul
  pattern `\"${CLAUDE_PLUGIN_ROOT}` e sul totale command.
- Verificare anche `tests/test_count_consistency.py` e `tests/run-all.sh`.

**Il nuovo valore NON va indovinato**: si esegue il test in RED dopo l'aggiunta di
`SessionEnd`, si legge il conteggio reale (oggi `run-hook.cmd` = 28; il pattern del
test conta diversamente, quindi il delta esatto va misurato) e si aggiornano i
contatori al valore osservato. Coperto da AC-9.

### 3.6 `reason` del payload SessionEnd (decisione esplicita — ISSUE-3b review)
Il payload stdin di `SessionEnd` include `reason` (clear/resume/logout/...). **Decisione**:
NON si aggiunge `reason` allo schema dell'event `session_end` (vedi Out of scope §8) —
schema invariato per retrocompatibilità a valle. `hooks/session-end` può loggarlo a
fini diagnostici in un campo separato/log, ma l'event `session_end` resta identico.

## 4. Flusso dati (prima → dopo)

```
PRIMA (bug):
  turno → Stop → [no completion] → emit session_end (conteggi parziali) + rm stato
        → guard set → gate ciechi nei turni successivi

DOPO (fix):
  turno → Stop → [no completion] → exit 0 (gate-only, stato intatto)
  ...accumulo skill/commit per tutta la sessione...
  fine reale → SessionEnd → emit session_end (conteggi completi) + flush
  prossimo avvio → SessionStart → reset/preserve per source + clear guard
```

## 5. Gestione errori
- `session-end` non può bloccare (limite piattaforma) → tutte le call sono best-effort
  (`|| true`), `set -euo pipefail` con guardie come negli altri hook.
- Token-collector / flush assenti → no-op silenzioso (come oggi).
- Guard stale da crash → pulito al `SessionStart` successivo (invariato).

## 6. Testing (TDD — RED prima)

Harness esistente: `tests/hooks/test_evidence_stop_gate.sh` (temp HOME + seed + assert).

**Nuovo `tests/hooks/test_session_lifecycle_fix.sh`:**

- **AC-1** (regressione bug primario): invoco `stop-gate` con transcript **senza**
  keyword di completamento e `.devforge-session-skills` seedato con
  `siae-git-workflow`. Asserzione: dopo l'hook il file **esiste ancora e contiene
  `siae-git-workflow`** (oggi verrebbe cancellato).
- **AC-2**: `stop-gate` con stdin vuoto → `.devforge-session-skills`,
  `.devforge-session-commits`, `.devforge-session-start-ns` **non cancellati**.
- **AC-3** (no-regression gate): completion claim + no verification → ancora
  `"decision":"block"` con `siae-verification`. (porting dei casi 1-2 esistenti)
- **AC-4** (no-regression gate): completion claim + `siae-verification` presente →
  allow. retrospective gate invariato.
- **AC-5** (SessionEnd emit): invoco `hooks/session-end` con counter seedati
  (skills=`a,b,c`, commits=`4`, start-ns valorizzato) e log file temporaneo →
  asserzione: emessa **una** riga `"event":"session_end"` con
  `"skills_used_count":3` e `"commits_count":4`.
- **AC-6** (idempotenza): seconda invocazione di `hooks/session-end` con guard già
  presente → **nessuna** seconda riga `session_end`.
- **AC-7** (no-rm in SessionEnd): dopo `hooks/session-end`, i file di stato
  **restano** (reset è di SessionStart, non di SessionEnd).
- **AC-8** (conteggio accurato): emit a fine sessione riflette conteggi accumulati
  (skills=3) e non parziali (es. 1 di un turno intermedio).
- **AC-9** (hooks.json valido + contatori): `SessionEnd` registrato, JSON parsabile,
  punta a `session-end`. **Aggiornare i contatori hardcoded** al valore osservato in
  RED: `tests/hooks/hooks-json-var-expansion.test.sh:33,66` e qualsiasi assert in
  `tests/test_count_consistency.py`. Il valore si misura eseguendo il test, NON si
  indovina.
- **AC-10** (ADR-2 resume case): invoco `hooks/session-end` con stdin
  `{"reason":"resume", ...}` e counter seedati → asserzione: i file di stato
  (`.devforge-session-skills/-commits/-start-ns`) **sono ancora presenti** dopo
  l'esecuzione (SessionEnd non resetta, il preserve di SessionStart resta valido).

**Verifica no-regression suite**: delta test count vs baseline committato; eseguire
`tests/hooks/test_evidence_stop_gate.sh`, `tests/hooks/hooks-json-var-expansion.test.sh`
e `tests/test_count_consistency.py`.

## 7. Criteri di accettazione (sintesi)
1. Dopo un Stop senza completion claim, `.devforge-session-skills/-commits/-start-ns`
   NON vengono cancellati (AC-1, AC-2, AC-7).
2. `git commit` non viene più bloccato a torto quando `siae-git-workflow` è stato
   invocato in un turno precedente (conseguenza di 1).
3. `session_end` è emesso una sola volta a fine sessione reale via `SessionEnd`, con
   conteggi accumulati e schema event invariato (AC-5, AC-6, AC-8).
4. Retrospective gate e verification gate restano invariati (AC-3, AC-4).
5. `hooks.json` registra `SessionEnd` ed è valido (AC-9).
6. Suite no-regression verde; nessun test esistente rotto.

## File creati e modificati (manifest)

Enumerazione esplicita dei file toccati dalla PR (manifest machine-readable):

- `hooks/session-end` — nuovo hook SessionEnd
- `hooks/stop-gate` — rimozione emit + rm stato
- `hooks/hooks.json` — registrazione evento SessionEnd
- `tests/hooks/test_session_end_hook.sh` — nuovo test
- `tests/hooks/test_stop_gate_no_state_wipe.sh` — nuovo test
- `tests/hooks/hooks-json-var-expansion.test.sh` — allineamento contatori
- `.claude-plugin/plugin.json` e `.claude-plugin/marketplace.json` — count hook 27→28

## 8. Out of scope / limitazioni note
- **Crash/`kill -9`** → `session_end` summary mancante (ADR-4). Limite di piattaforma
  (anche `SessionEnd` nativo non fira). Gli eventi di sessione sono già drenati dal
  flush zero-loss; si perde solo la riga riassuntiva.
- **Orphan-recovery** del `session_end` su crash: NON implementata (attribuzione al sid
  precedente complessa, counter sono file globali → rischio mis-attribuzione > beneficio).
- **Sessioni concorrenti** sullo stesso `$HOME` (ISSUE-5 review): i counter sono file
  globali condivisi; `SessionEnd` di una sessione può includere lavoro di un'altra.
  **Difetto pre-esistente**, non introdotto da questo fix; già rilevato come
  `session_conflict` warning in `session-start:409-418`. Fuori scope qui.
- **Campo `reason`** nel payload event `session_end`: NON aggiunto (schema invariato per
  retrocompatibilità, §3.6).
- **Timeout `SessionEnd`** (ISSUE-7 review): `SessionEnd` è only-cleanup e non blocca; non
  si configura un timeout di blocco. Le operazioni lente (`token-collector update`,
  `upload_logs`) restano best-effort `|| true` come oggi su `Stop`.
- **Guard anti-block-cap** `stop_hook_active` (menzionato, non implementato salvo richiesta).
- Ridisegno schema event `session_end` (resta identico).
