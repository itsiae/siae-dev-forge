# PR Gate Bloccante — Design Doc

> **Data:** 2026-03-09
> **Autore:** DevForge AI CC
> **SP:** 2

## Contesto

Il hook `pr-gate` attuale esce sempre `exit 0` e inietta solo `additional_context`
con istruzioni soft. Claude può ignorarle e creare la PR senza security scan né review.

## Decisione

Modificare `hooks/pr-gate` per:

1. **Security scan automatico bloccante** — il hook esegue regex sul diff per
   pattern CRITICI (secrets, credentials, private keys). Se trova match →
   `{"decision": "block", "reason": "..."}`. Questo impedisce fisicamente
   l'esecuzione di `gh pr create`.

2. **Code review + security via istruzioni forti** — il hook inietta istruzioni
   che obbligano Claude a invocare `siae-devforge:code-reviewer` e
   `siae-devforge:siae-security` PRIMA di procedere con `gh pr create`.

## Modifiche

### `hooks/pr-gate` (unico file)

- Aggiungere funzione `run_security_scan()` che:
  - Calcola merge-base (origin/sviluppo || origin/main || HEAD~1)
  - Esegue `git diff` sui file modificati
  - Grep per pattern CRITICI (AKIA, private key, password hardcoded, connection string, api key)
  - Se match → return 1
- Cambiare il flusso:
  - Se security scan fallisce → output `{"decision": "block", "reason": "CRITICO: ..."}`
  - Se security scan passa → output `additional_context` con istruzioni bloccanti
    per code-reviewer e siae-security
- Aggiornare le istruzioni iniettate per richiedere esplicitamente invocazione
  dei 2 agent (code-reviewer, security) prima di `gh pr create`

## Pattern CRITICI (bloccanti)

```
AKIA[0-9A-Z]{16}
-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----
[pP]assword\s*[:=]\s*["'][^"']+["']
(mysql|postgres|mongodb)://[^:]+:[^@]+@
[aA][pP][iI][-_]?[kK][eE][yY]\s*[:=]\s*["'][^"']+["']
```

## Criteri di accettazione

- [ ] Hook blocca `gh pr create` se trova secrets nel diff
- [ ] Hook inietta istruzioni che richiedono code-reviewer e siae-security
- [ ] `bash tests/run-all.sh` passa
- [ ] Timeout hook rispettato (< 15s)
