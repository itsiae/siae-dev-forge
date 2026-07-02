# Auto-retrospective (forge-retrospect) — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` (stessa sessione) o
> `siae-executing-plans` (sessione separata) per implementare questo piano task per task,
> con `siae-tdd` per ogni modulo Python.

**Goal:** Portare in DevForge il failure-learning di headroom (`headroom learn`, Apache 2.0): a fine sessione rilevare i fallimenti ripetuti dal transcript e proporre lezioni a `CLAUDE.md`/memory con dry-run/apply.
**Architettura:** 4 stadi — DETECT (hook session-end, ≤2s, no LLM) → NUDGE (hook session-start) → MINE (skill `/forge-retrospect`, LLM inline) → APPLY/DISMISS (writer marker-section). Vedi design §4.
**Stack:** Python 3 puro (no dep esterne), bash (hook), markdown (skill). pytest per i test (conftest inietta REPO_ROOT in sys.path).
**SP:** 6 (Umano) / 3 (Augmented).
**Design doc:** `docs/plans/2026-06-22-auto-retrospective-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | NOTICE Apache-2.0 + scaffold package `lib/retro/` | `task-01-notice-scaffold.md` | [DONE] |
| 2 | `lib/retro/classifier.py` — port taxonomy errori | `task-02-classifier.md` | [DONE] |
| 3 | `lib/retro/writer.py` — marker-section dry-run/apply | `task-03-writer.md` | [DONE] |
| 4 | `lib/retro/digest.py` — digest compresso transcript | `task-04-digest.md` | [DONE] |
| 5 | `lib/retro/scan.py` — DETECT light + soglia + staging | `task-05-scan.md` | [DONE] |
| 6 | `hooks/session-end` — chiama scan.py dopo guard (additivo) | `task-06-session-end-hook.md` | [DONE] |
| 7 | `hooks/session-start` — nudge con sentinel (additivo) | `task-07-session-start-nudge.md` | [DONE] |
| 8 | `skills/forge-retrospect/SKILL.md` — MINE+APPLY+DISMISS | `task-08-skill-forge-retrospect.md` | [DONE] |
| 9 | Integration + probe (transcript reale → staging → lezioni) | `task-09-integration-probe.md` | [DONE] |

> **Esecuzione:** completata 2026-06-22 su `feat/auto-retrospective`. Tutti i task implementati in TDD.
> Fresh-eyes review cross-task: Ready to merge (0 CRITICAL/MAJOR). Nota: `commands/forge-retrospect.md`
> aggiunto post-piano (la skill è user-invocabile come `/forge-retrospect`).

## Dipendenze

- Task 1 è prerequisito di tutti (scaffold package + attribuzione licenza).
- Task 2 (classifier) e Task 3 (writer) sono indipendenti tra loro (dopo Task 1).
- Task 4 (digest) dipende da Task 2 (importa `classify_error`/`is_error_content` da `classifier`).
- Task 5 (scan) dipende da Task 2 (classifier) + Task 4 (importa `iter_tool_events` da `digest`).
- Task 6 (session-end) dipende da Task 5 (invoca scan.py).
- Task 7 (session-start) dipende da Task 5 (legge il formato staging record).
- Task 8 (skill) dipende da Task 3 (writer) + Task 4 (digest).
- Task 9 (integration) dipende da 5, 6, 7, 8.

## Criteri di accettazione globali (design §11)

1. Scan < 2s su transcript da 500 eventi, mai blocca session-end (exit 0).
2. Staging scritto solo se ≥3 error tool-result o pattern `(tool,category)` ripetuto ≥2; record leggero.
3. Nudge ≤1 per sessione (sentinel `.devforge-retro-reminded`), si ripresenta finché pendente.
4. `/forge-retrospect` dry-run di default; nessuna scrittura senza `--apply`.
5. Apply dentro marker-section, idempotente, sezioni umane intatte.
6. python-less: degrada con warn one-shot.
7. `NOTICE` con attribuzione Apache-2.0 headroom.
8. `siae-retrospective` manuale invariata (no-regression).
