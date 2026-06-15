# Task 05 — F3: normalizzazione host short-name

**Stato:** PENDING
**Dipende da:** nessuno
**File:** `lib/logger.sh`, `tests/zero-loss/unit/test_host_shortname.sh` (nuovo)

## Obiettivo
`host` coerente cross-OS (short name) per non spezzare il join `(host, os_user)` del detector P2.

## Approccio TDD
### RED — `tests/zero-loss/unit/test_host_shortname.sh`
Con uno shim `hostname` che ritorna l'FQDN (`engsport08.itsiae.it`), il campo `host` nel bundle
identità prodotto da `devforge_identity_bundle` è `engsport08`.

### GREEN
In `devforge_identity_bundle` (`logger.sh:269`), dopo la risoluzione:
```bash
host=$(hostname -s 2>/dev/null || hostname 2>/dev/null || echo "")
host="${host%%.*}"
```

## Criteri di accettazione (design AC 11)
`host` short su tutte le piattaforme; nessun suffisso dominio.

## No-regression
Su host già short, `${host%%.*}` è no-op. Bundle identità invariato negli altri 9 campi.
