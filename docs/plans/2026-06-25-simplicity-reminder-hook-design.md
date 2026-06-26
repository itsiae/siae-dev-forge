# Simplicity Reminder Hook — Design

## 1. Contesto e problema
Le sessioni lunghe derivano verso l'**over-engineering**. Serve un **nudge periodico, leggero e non invasivo** che ricordi i principi ingegneristici **di semplicità del codice** (KISS, YAGNI, AHA). Vincolo utente: tenere tutto semplice; il principio iniettato è **fondato sulla letteratura** di software design, non inventato (vedi §9).

## 2. Approccio (B — contatore globale)
Un solo hook `UserPromptSubmit` (`hooks/simplicity-reminder`) con un **contatore globale cumulativo**: **ogni 5 prompt** inietta il principio via `additional_context`.

**Perché globale e non per-sessione (decisione da premortem):** uno slot per-sessione (Approccio A iniziale, `"<session_id> <n>"`) si **auto-annulla con 2+ sessioni concorrenti** nella stessa repo — il `session_id` alterna ad ogni prompt → reset continuo a `n=1` → il reminder **non scatta mai**. L'utente lavora abitualmente con sessioni concorrenti, quindi A renderebbe la feature inerte. Il contatore globale è **anche più semplice**: non legge stdin, non parsa `session_id`.

Scartati: **A** (slot per-sessione — race fatale con concorrenza), **C** (due hook SessionStart+counter — over-engineering).

## 3. Componenti e flusso
- **Stato**: `${HOME}/.claude/.devforge-simplicity-counter` = `"<n>"` (intero; scrittura atomica `.tmp`+`mv`).
- **Logica**: `n = (cat file || 0) + 1`; salva; se `n % 5 == 0` → emetti; altrimenti `exit 0`.
- **Non legge stdin** (nessun rischio di hang in attesa dell'input dell'evento).
- **Output**: schema identico a `hooks/devforge-context` (`additional_context` + `hookSpecificOutput.{hookEventName, additionalContext}`). Escape via `devforge_sanitize_json_str`.
- **Telemetria**: `devforge_log "simplicity_reminder_emitted"` best-effort.

## 4. Testo iniettato (il principio)
Fondato su KISS / YAGNI / AHA (§9):
> **DevForge — Semplicità del codice**: **KISS** (fai la cosa più semplice che funziona); **YAGNI** (implementa solo ciò che serve ora, non ciò che forse servirà); evita **astrazioni premature** (AHA: meglio un po' di duplicazione che l'astrazione sbagliata). Meno codice = meno bug; la complessità si aggiunge solo con una ragione concreta e dimostrata.

## 5. Errori / edge (fail-safe)
- State file assente/corrotto → riparte da `n=1` (guard `case`).
- **Invariante**: il hook non blocca MAI il prompt — ogni ramo d'errore fa `exit 0`. Niente `set -e/-u/pipefail`. Non legge stdin.

## 6. Testing
`tests/hooks/test_simplicity_reminder.sh`:
- T1: 1° prompt → nessuna iniezione.
- T2: 5° prompt → inietta (lo stdout contiene "YAGNI").
- T5: stdout è JSON valido (`jq`).
- T4: 10° prompt → inietta (periodicità ogni 5).
- T3: **contatore cumulativo robusto a session_id concorrenti** — alternando sid, al 15° inietta comunque (verifica la mitigazione del premortem).
- T6: input malformato → `exit 0` (fail-safe).

## 7. Criteri di accettazione
1. Hook registrato in `hooks/hooks.json` come `UserPromptSubmit`.
2. Ogni 5 prompt (globale) inietta il principio.
3. Output JSON valido e **non bloccante**.
4. Fail-safe: non blocca mai il prompt utente.
5. **Robusto a sessioni concorrenti** (nessun reset reciproco).
6. Test PASS, registrato in `tests/run-all.sh`; nessuna regressione.
7. Nessun segreto / PII.

## 8. Out of scope
- Configurabilità della frequenza (env var = follow-up).
- Opt-out (follow-up).
- Testo dinamico (statico).

## 9. Riferimenti (principi fondanti — ricerca online)
- **KISS** (Keep It Simple): la soluzione più semplice che funziona; evita complessità non necessaria.
- **YAGNI** (You Aren't Gonna Need It): pratica XP — implementa solo ciò che serve ora.
- **AHA** (Avoid Hasty Abstractions, Kent C. Dodds / Sandi Metz: "prefer duplication over the wrong abstraction").
- **Occam's Razor** applicato al software design.

## File
Manifest esaustivo (sezione strutturata per spec-drift detection):
- `hooks/simplicity-reminder` — nuovo hook UserPromptSubmit (contatore globale + iniezione)
- `hooks/hooks.json` — aggiunta entry UserPromptSubmit `simplicity-reminder`
- `tests/hooks/test_simplicity_reminder.sh` — test di guardia (nuovo)
- `tests/run-all.sh` — registrazione del nuovo test
- `tests/hooks/hooks-json-var-expansion.test.sh` — allineamento count hook (29→30) per il nuovo hook
- `.claude-plugin/plugin.json` — bump versione
- `.claude-plugin/marketplace.json` — bump versione
- `CHANGELOG.md` — entry feature

## Stima
SP Umano 1 · Augmented 0.5
