# Task 20 — SKILL.md hooks Phase 3/5/7 parallel

**Goal:** Innestare in `SKILL.md` i punti di attivazione del flusso parallelo: Phase 3 valuta il trigger e logga `parallel_mode`, Phase 5 carica `phase-5-parallel.md` ed esegue il Dispatch Protocol (saltando il loop sequenziale), Phase 7 dispatcha repair-agent per i fix per-file. Collega l'orchestrazione documentata in Task 19 al workflow inline della skill.

**WS:** WS-5 · **Dipendenze:** Task 19 (reference esistente).

## File coinvolti
- Modifica: `skills/code-coverage/SKILL.md` (Principio 2 riga ~35; Phase 3 riga ~109; Phase 5 riga ~178; Phase 7 riga ~187)

## Prerequisito di lettura
Leggi `skills/code-coverage/SKILL.md` per i punti esatti di Phase 3/5/7 e del Principio 2.

## Step 1 — Principio 2 (riga ~35-36)
Dopo "see Phase 5 batch rule", aggiungi:
```markdown
LARGE/VERY_LARGE con pending_batches >= 2 → parallel multi-agent dispatch (fino a 4
subagent Sonnet, ognuno owner di batch disgiunti). Trigger e protocollo in
`references/phase-5-parallel.md`. Il coordinatore non legge i sorgenti: li leggono i subagent.
```

## Step 2 — Phase 3 (riga ~109)
Dopo il caricamento di `references/phase-3-sizing.md`, aggiungi:
```markdown
Valuta il trigger parallelo (vedi references/phase-5-parallel.md "Trigger"). Logga:
"[phase3] parallel_mode=enabled agents=N" oppure "[phase3] parallel_mode=disabled reason=...".
```

## Step 3 — Phase 5 (riga ~178)
All'inizio di Phase 5, prima del corpo standard, aggiungi il branch condizionale:
```markdown
If parallel_mode == enabled:
  - Verifica che il tool Agent sia disponibile (altrimenti fallback sequenziale + log).
  - Load `references/phase-5-parallel.md`.
  - Esegui il Dispatch Protocol (P1-P5): assegna batch→agenti, dispatcha le Agent call
    Sonnet nello STESSO turno, attendi, join, re-queue partial/failed.
  - SKIP il loop sequenziale standard (gira dentro i subagent).
  - Procedi a Phase 6 (coordinatore).
Else:
  [loop sequenziale standard — invariato]
```

## Step 4 — Phase 7 (riga ~187)
Dopo la formula max_iter (già aggiornata in Task 15), aggiungi:
```markdown
If parallel_mode == enabled: i fix per-file con >= 2 file di categorie diverse sono
dispatchati a repair-agent Sonnet in parallelo (vedi phase-5-parallel.md "Phase 7 parallel
repair"). Systemic fix e full coverage run restano sequenziali (coordinatore).
```

## Step 5 — Verifica
Run: `grep -q "parallel multi-agent dispatch" skills/code-coverage/SKILL.md && echo OK` → `OK`.
Run: `grep -q "parallel_mode=enabled" skills/code-coverage/SKILL.md && echo OK` → `OK`.
Run: `grep -q "Dispatch Protocol" skills/code-coverage/SKILL.md && echo OK` → `OK`.
Run (sanity): `python3 -c "print(len(open('skills/code-coverage/SKILL.md').read().split()))"` → conteggio parole non nullo (file non corrotto).

## Step 6 — Commit
```
git add skills/code-coverage/SKILL.md
git commit -m "feat(code-coverage): wire parallel multi-agent dispatch into Phase 3/5/7"
```

## Criteri di accettazione
- [ ] Principio 2 menziona il dispatch parallelo (≤4 Sonnet, coordinatore non legge i sorgenti).
- [ ] Phase 3 valuta e logga `parallel_mode`.
- [ ] Phase 5 ha il branch condizionale enabled/else con fallback su Agent tool assente.
- [ ] Phase 7 dispatcha repair-agent per i fix per-file quando parallel_mode enabled.
