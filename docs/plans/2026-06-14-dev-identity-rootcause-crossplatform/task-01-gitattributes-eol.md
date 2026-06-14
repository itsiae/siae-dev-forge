# Task 01 — F1: line-ending safety (.gitattributes eol=lf)

**Stato:** PENDING
**Dipende da:** nessuno
**File:** `.gitattributes` (nuovo), `tests/zero-loss/unit/test_gitattributes_eol.sh` (nuovo)

## Obiettivo
Impedire che CRLF rompa gli hook bash su Windows (`\r: command not found`).

## Approccio TDD
### RED — `tests/zero-loss/unit/test_gitattributes_eol.sh`
- assert che `.gitattributes` esista alla root del repo.
- assert `git check-attr eol -- hooks/post-commit-review lib/logger.sh lib/install-trailer-hook.sh` ritorni `eol: lf` per ogni file.
- assert che nessun file sotto `hooks/` e `lib/*.sh` contenga byte CR:
  `! grep -lUP '\r' hooks/* lib/*.sh`.

### GREEN — creare `.gitattributes`
```
* text=auto
*.sh text eol=lf
hooks/* text eol=lf
lib/*.sh text eol=lf
*.py text eol=lf
```
Poi renormalizzare in un commit dedicato: `git add --renormalize .`.

## Criteri di accettazione (design AC 1, 2)
- AC1: `git check-attr eol` → `lf` su hook e lib.
- AC2: nessun byte CR negli hook/lib.

## No-regression
Il renormalize non cambia il contenuto logico dei file; la suite test resta verde
(verificato in task-10). Il diff one-shot va in un commit isolato per leggibilità.
