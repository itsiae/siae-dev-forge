# siae-test-data Node.js Fallback — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Aggiungere `generate_profiles.js` (Node.js CJS, zero deps) come secondo
fallback runtime quando Python non è disponibile, riducendo N=50 profili da ~10 min
a <2s su Windows senza Python.

**Architettura:** File unico `scripts/generate_profiles.js` (CJS, `require`).
Stessa interfaccia CLI di `generate_profiles.py`. Legge i medesimi JSON in
`references/`. PRNG Mulberry32 seedato per determinismo per-runtime.

**Stack:** Node.js 10+ (CJS), pytest (test integrazione), SKILL.md (istruzioni Claude)

**SP:** 6.5 Umano / 3.5 Augmented

**Design doc:** `docs/plans/2026-06-10-siae-test-data-node-fallback-design.md`

**Branch:** `feat/test-data-node-fallback` (da `fix/test-data-upgrade`)

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Scaffold: entry point, loadRef, parseArgs, Mulberry32 | `task-01-scaffold.md` | [PENDING] |
| 2 | cfUtils: tabelle checksum + codice CF persona fisica | `task-02-cf-persona-fisica.md` | [PENDING] |
| 3 | pivaUtils + CF enti numerici | `task-03-piva-cf-enti.md` | [PENDING] |
| 4 | addressUtils + _pickNomeCognome | `task-04-address-names.md` | [PENDING] |
| 5 | profileGen PRIVATO/AUTORE (persona fisica) | `task-05-profile-privato.md` | [PENDING] |
| 6 | profileGen BUSINESS/EDITORE + rappresentante legale | `task-06-profile-business.md` | [PENDING] |
| 7 | formatOutput (JSON/CSV) + distribuzione nazionalità + main() | `task-07-format-main.md` | [PENDING] |
| 8 | test_node_fallback.py (7 test pytest integrazione) | `task-08-tests.md` | [PENDING] |
| 9 | SKILL.md Passo 0: detection Node.js + pre-warming | `task-09-skill-md.md` | [PENDING] |

## Dipendenze

- Task 2-4 dipendono da Task 1 (scaffold con loadRef)
- Task 5 dipende da Task 2 + 4
- Task 6 dipende da Task 3 + 5
- Task 7 dipende da Task 5 + 6
- Task 8 dipende da Task 7 (script completo)
- Task 9 è indipendente (solo SKILL.md)
