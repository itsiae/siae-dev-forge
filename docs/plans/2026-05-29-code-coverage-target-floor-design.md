# Design — Code-Coverage Skill: il valore utente come floor minimo per ogni soglia

**Date:** 2026-05-29
**Author:** mario.mazzacuv@siae.it
**Skill target:** `skills/code-coverage/`
**Status:** approved at GATE (preview-confirmed)

## Contesto

L'utente ha riportato un bug nella skill `code-coverage`: quando si imposta un target
di coverage (preset 40/70 o custom), il valore inserito **non** viene rispettato come
minimo. In particolare il `target_branch` veniva derivato come `max(1, target_line - 10)`,
quindi un input di `83` produceva `branch = 73` — 10 punti sotto il valore digitato.

> "il valore utente deve essere il minimo non può essere come in questo caso 10 in meno"
> "La logica che deve guidare [è] che il valore che immette l'utente è il valore MINIMO per ogni parametro (custom, 40, 70 ecc)"

### Bug diagnosi

La regola `branch = line - 10` (gap fisso) era hardcoded in più punti:

1. `scripts/estimate_effort.py` → `derive_branch_target()` = `max(1, N-10)`
2. `lib/sentinel-handshake.sh` → logica inline + helper shell `_derive_branch_target()`
3. preset A/B del sentinel (40→30, 70→60)
4. `scripts/parse_coverage.py` → fallback `min_branch_pct` = `line - 10` (3 occorrenze)
5. asset `assets/priority-rules.json` → `min_branch_pct` con gap −10 (80/70, 70/60, 60/50)

Inoltre le soglie per-file P1/P2/P3 e il floor globale (70% / P1 80%) erano **scollegati**
dal valore inserito dall'utente: un target custom alto (es. 83) non alzava né le soglie
per-file né il floor globale.

## Decisione (principio unico)

**`effective = max(default_documentato, valore_utente)`, con `branch == line`.**

Il valore inserito dall'utente (`user-choice.json.target_line`) è il **MINIMO** applicato
a OGNI soglia. Nessuna sottrazione: `target_branch == target_line`. I default documentati
(global 70%, P1 80%, P2 70%, P3 60%) restano come **floor**: il valore utente può solo
alzarli, mai abbassarli. La soglia CI (Phase 2.5) può alzare ulteriormente.

Esempi:
- utente **40** → nessuna soglia sale (40 < tutti i default); preset resta 40/40
- utente **70** → P3 sale a 70 (da 60), P1/P2 invariati; global 70
- utente **83** → tutte le soglie (global, P1/P2/P3, line E branch) salgono a 83/83

### Componenti modificati

| File | Modifica |
|------|----------|
| `scripts/estimate_effort.py` | `derive_branch_target()` → identità; preset sentinel A 40/40, B 70/70; docstring |
| `lib/sentinel-handshake.sh` | inline `target_branch = target`; helper `_derive_branch_target()` → echo identità |
| `scripts/parse_coverage.py` | `assign_priority_and_threshold(path, rules, user_floor=0.0)`: branch==line + clamp `max(default, user_floor)`; `resolve_user_floor()` (precedenza `--min-floor` → auto-read `user-choice.json` risalendo le dir → 0.0, clamp difensivo `[0,95]`); `parse(..., user_floor)` propaga e salva nel result; view builders `threshold_met = max(70, floor)`, P1 violators `< max(80, floor)` |
| `lib/phase6-coverage.sh` | passa `--min-floor <target_line>` letto da `user-choice.json` |
| `assets/priority-rules.json` | `min_branch_pct = min_coverage_pct` (80/70/60), version 1.2.0 |
| `SKILL.md` + `lib/state-schema.json` | documentazione del modello floor |

### ADR

- **branch == line**: il branch target non è più derivato con gap. Coerente con "valore
  utente = minimo". Le priority-rules esplicitano `min_branch_pct == min_coverage_pct`.
- **`user_floor` come parametro (default 0.0)**: backward-compat totale — i chiamanti che
  non passano il floor (e i test esistenti) mantengono il comportamento storico.
- **clamp `[0,95]` su `resolve_user_floor`**: difesa da `user-choice.json` corrotto; range
  coerente con la validazione `[1,95]` del sentinel. Negativo → 0 (nessun floor).
- **CI override invariato**: la logica `max(user, CI)` in `estimate_effort`/`sentinel`
  resta; la CI può solo alzare il floor.

## Criteri di accettazione

- [x] `target_branch == target_line` per preset 40/70 e custom (no gap −10)
- [x] soglie per-file P1/P2/P3 = `max(default, target_line)`, branch == line
- [x] floor globale e P1-violators rispettano `max(default, target_line)`
- [x] `resolve_user_floor`: precedenza explicit → auto-read → 0.0, clamp `[0,95]`
- [x] CI threshold può solo alzare il floor
- [x] backward-compat: `user_floor=0.0` → comportamento invariato
- [x] E2E: input 83 → ogni soglia 83/83 (verificato su path interattivo + CLI)

## SP

Umano ~3 / Augmented ~0.5

## Note

Cambiamento nato da bug report utente + iterazione interattiva (AskUserQuestion con
preview numerica approvata). Implementato in single-pass accelerated path (estensione
lineare con simulazione empirica E2E). 438 test pass.
