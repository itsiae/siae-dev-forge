# Task 07 — Comprimere skills/siae-verification/SKILL.md (345→180 righe)

**Stato:** [PENDING]
**Execution:** subagent (parallel-safe)
**Dipendenze:** T01
**Durata stimata:** 8-10 min

## Classificazione K/M/D

| Sezione | Riga | Classe | Azione |
|---|---|---|---|
| `## LA LEGGE DI FERRO` | 30 | K | Verbatim |
| `## Quando si Applica` | 52 | K | Verbatim compatto |
| `## Scaling` | 65 | K | Verbatim compatto |
| `## I 5 Step della Verifica` | 83 | K | Verbatim — IDENTIFICA/ESEGUI/LEGGI/VERIFICA/AFFERMA |
| `### Context-First Rule` | 116 | K | **Mantieni qui come canonical** (rimossa dalle altre skill) |
| `## Cosa NON Conta Come Verifica` | 206 | K | Verbatim (anti-pattern critici) |
| `## Red Flags — Stai Razionalizzando` | 220 | K | Verbatim |
| `## Perche' Importa` | 241 | D | Elimina (retorica) |
| `## Limiti Operativi` | 255 | M | Ref a `lib/operational-limits.md` |
| `## Tabella Anti-Razionalizzazione` | 265 | D | Elimina |
| `## Classificazione Rischio` | 282 | M | Ref a `lib/risk-taxonomy.md` |
| `## Vincoli` | 296 | K | Verbatim (regole hard) |
| `## Permission Denied Handling` | 308 | M | Ref a `lib/permission-denied-handling.md` |
| `## Risorse Aggiuntive` | 343 | D | Elimina |

## Step

Pattern standard T04-T05. Check specifici:

```bash
# Verifica 5 step e Context-First Rule
for s in IDENTIFICA ESEGUI LEGGI VERIFICA AFFERMA; do
  grep -qE "Step [0-9]+.*$s" skills/siae-verification/SKILL.md && echo "PASS step_$s" || echo "FAIL step_$s"
done
grep -q "## Cosa NON Conta" skills/siae-verification/SKILL.md && echo "PASS not_counts"
grep -q "Context-First Rule" skills/siae-verification/SKILL.md && echo "PASS context_first"
```
Output atteso: tutti PASS.

## Acceptance

- [ ] `wc -l` ≤ 180
- [ ] 5 step verifica presenti
- [ ] Context-First Rule in siae-verification (canonical)
- [ ] "Cosa NON Conta Come Verifica" preservato
- [ ] Commit `refactor(skills):`
