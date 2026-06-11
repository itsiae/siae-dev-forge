# Design — Match comandi composti nei gate token-based (premortem/blind-review/pre-commit)

**Data:** 2026-06-11 · **Complessità:** Media · **SP:** 2 (Umano) / 0.5 (Augmented)

## Contesto (root cause da siae-debugging, riprodotta)

PR #311 è stata aperta SENZA che `pr-premortem-gate` e `pr-blind-review-gate` bloccassero,
nonostante `siae-premortem`/`siae-blind-review` mai invocate in sessione. Root cause in
`lib/cmd-parser.sh`: `_devforge_primary_cmd` taglia al PRIMO operatore shell (`%%&*` ecc.),
quindi da `cd "..." && env -u http_proxy gh pr create ...` estrae solo `cd "..."` →
primo token `cd` → gate silenziosamente skippa (fail-open by design del tokenizer).
Secondo gap: `env -u VAR cmd` — il flag `-u` non è gestito da `_devforge_strip_prefix`.

Repro deterministiche (hook cache 1.82.0, input simulato):
- `cd X && env -u P gh pr create ...` → `{}` (BYPASS)
- `gh pr create ...` → `block` (logica gate OK)
- `env -u P gh pr create ...` → `{}` (BYPASS)

Hook affetti (token-first-segment): `pr-premortem-gate`, `pr-blind-review-gate`, `pre-commit`.
Hook NON affetti (regex-anywhere): `pr-gate`, `pr-release-gate`, `post-commit-review` — questi
"partono sempre" ma hanno il difetto speculare: falsi positivi su stringhe
(`printf '...gh pr create...'` fa scattare il pr-gate, osservato in sessione).

## Direttiva utente

"Premortem e risk devono partire sempre, come code review e security." Risk
(`pr-release-gate`) è già regex-anywhere → già conforme. Da sistemare: i 3 token-based.

## Decisione

Estendere `lib/cmd-parser.sh` in modo ADDITIVO (nessuna funzione esistente modificata
nel comportamento osservabile dai caller attuali, eccetto il fix `env` flags):

1. `_devforge_segments CMD` — split del comando su `&&`, `||`, `;`, `|`, newline:
   un segmento per riga.
2. `devforge_cmd_has_subcommand CMD TOK1 TOK2 [TOK3]` — itera i segmenti, applica
   `_devforge_strip_prefix` a ciascuno, ritorna 0 se i token 1..N di UN segmento
   matchano. Resta token-based → un `printf '...gh pr create...'` NON matcha
   (primo token `printf`): niente nuovi falsi positivi.
3. Fix `_devforge_strip_prefix`: dopo `env`, droppa i flag (`-u VAR`/`-C dir` = 2 parole,
   altri `-x` = 1 parola) prima delle assegnazioni `VAR=val`.
4. I 3 hook usano `devforge_cmd_has_subcommand` quando disponibile (fallback regex
   leading invariato).

## Alternative scartate

- Passare i 3 hook a regex-anywhere come pr-gate: elimina i falsi negativi ma
  introduce falsi positivi su stringhe/heredoc (osservati in sessione sul pr-gate) e
  per gate BLOCCANTI un falso positivo è peggio (blocca lavoro legittimo).
- Parser bash completo (quote-aware): oltre il necessario, fragile, YAGNI.

## Criteri di accettazione

- `cd X && env -u P gh pr create ...` → pr-premortem-gate **blocca** (senza premortem validato).
- `printf '...gh pr create...'` → pr-premortem-gate NON blocca (no falso positivo).
- `gh pr create` pulito → blocca (regressione zero).
- `git commit -m x` dentro comando composto → pre-commit gate scatta.
- Stessi casi per pr-blind-review-gate.
- Test e2e che pipano JSON reale negli hook (no unit-only: lezione PR2/PR3).
- Suite no-regression hook esistente PASS.
