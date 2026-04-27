# Classificazione Rischio Operazioni — Standard DevForge

| Livello | Definizione | Card richiesta |
|---------|-------------|----------------|
| 🟢 SICURO | Operazione locale, reversibile istantaneamente | No |
| 🟡 MEDIO | Reversibile ma richiede azione (git revert, undo) | Sì |
| 🔴 ALTO | Difficile da annullare (force-push, tag pubblicati) | Sì |
| 🚨 CRITICO | Irreversibile o con impatto esterno (prod deploy, credenziali) | Sì + conferma esplicita |

## Esempi standard

| Operazione | Livello |
|-----------|---------|
| Read, Glob, Grep | 🟢 SICURO |
| Edit file locale, scrittura design doc | 🟢 SICURO |
| git commit, git add | 🟡 MEDIO |
| git push feature branch | 🟡 MEDIO |
| git push --force su main | 🚨 CRITICO |
| git tag push (release) | 🔴 ALTO |
| gh pr create | 🟡 MEDIO |
| AWS deploy (Terraform apply) | 🔴 ALTO |
| DROP TABLE, rm -rf | 🚨 CRITICO |

Le skill individuali referenziano questa tabella invece di duplicarla.
