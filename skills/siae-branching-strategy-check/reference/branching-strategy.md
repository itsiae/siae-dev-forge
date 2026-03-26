# SIAE Branching Strategy

## Principi

Il branch `main` rappresenta lo stato del codice attualmente installato in produzione.
Ogni modifica a `main` deve transitare attraverso un branch di release.

## Schema dei branch

| Tipo | Pattern | Target | Scopo |
|---|---|---|---|
| **Main** | `main` | — | Produzione. Branch di default del repository |
| **Release** | `release/**` | `main` | Contenitore di una nuova release. Unico tipo di branch autorizzato ad aprire PR verso main |
| **Feature** | `feature/**` | `release/**` | Sviluppo di nuove funzionalita'. Confluisce nel branch di release, mai direttamente in main |
| **Hotfix** | `hotfix/**` | `release/**` | Fix urgenti. Confluisce nel branch di release, mai direttamente in main |

## Regole

1. Il branch di default di ogni repository **deve** essere `main`.
2. Solo i branch `release/**` possono aprire pull request verso `main`.
3. I branch `feature/**` e `hotfix/**` devono aprire pull request verso il branch `release/**` di riferimento, **mai** verso `main`.
4. Una pull request verso `main` proveniente da un branch diverso da `release/**` e' una **violazione** della strategia e non puo' essere mergiata.

## Flusso

```
feature/xyz ──┐
               ├──→ release/1.2.0 ──→ PR verso main ──→ merge ──→ produzione
hotfix/abc  ──┘
```

## Regole di classificazione

- **Compliant**: default branch `main` E nessuna PR aperta verso main da branch non-`release/**`
- **Non compliant**: default branch != `main` OPPURE almeno una PR da branch non-release verso main
- **Non soggetta**: PR che non punta a `main` (nessun controllo richiesto)
