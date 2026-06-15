# Task 07 — P5: pr_author_emails[] in post-commit-review

**Stato:** PENDING
**Dipende da:** nessuno (usa il trailer `DevForge-Author` già presente)
**File:** `hooks/post-commit-review`, `tests/zero-loss/unit/test_pr_author_emails.sh` (nuovo)

## Obiettivo
Recuperare gli autori reali della PR (set distinto) quando un integratore apre tutte le PR.

## Approccio
Nel punto in cui `post-commit-review` emette `pr_opened`/`pr_merged`, calcolare la lista autori:
```bash
DEFAULT_BRANCH="${DEVFORGE_DEFAULT_BRANCH:-main}"
base=$(git merge-base HEAD "origin/${DEFAULT_BRANCH}" 2>/dev/null || git merge-base HEAD "$DEFAULT_BRANCH" 2>/dev/null || echo "")
authors=""
if [ -n "$base" ]; then
    # git >= 2.32: trailer valueonly
    authors=$(git log "${base}..HEAD" --format='%(trailers:key=DevForge-Author,valueonly)' 2>/dev/null | grep -v '^$' | sort -u)
    # fallback git < 2.32: parse riga "DevForge-Author: <email>"
    if [ -z "$authors" ]; then
        authors=$(git log "${base}..HEAD" --format='%(trailers)' 2>/dev/null | sed -n 's/^DevForge-Author: //p' | sort -u)
    fi
fi
```
Serializzare `authors` come array JSON `pr_author_emails` nel meta (una entry per riga, dedup).
Lista vuota `[]` se nessun trailer trovato.

## Approccio TDD
### RED — `tests/zero-loss/unit/test_pr_author_emails.sh`
- repo fittizio con 2 commit aventi trailer `DevForge-Author` di 2 email diverse → `pr_author_emails`
  contiene entrambe (dedup, ordinate).
- repo fittizio senza trailer → `pr_author_emails` = `[]`.
- **fallback git < 2.32 (WARN-3):** shim `git` in testa al PATH che ritorna stringa vuota per
  `%(trailers:key=DevForge-Author,valueonly)` e ritorna `%(trailers)` in formato plain → il ramo `sed`
  produce comunque la lista corretta. Non richiede una macchina Windows (basta il PATH shim).

### GREEN
Implementare il calcolo + serializzazione JSON sicura (`devforge_sanitize_json_str` per ogni email).

## Criteri di accettazione (design AC 7)
Lista valorizzata su PR con commit DevForge; `[]` altrimenti.

## No-regression
Additivo nel meta di `pr_opened`/`pr_merged`; gli altri campi degli eventi PR invariati.
