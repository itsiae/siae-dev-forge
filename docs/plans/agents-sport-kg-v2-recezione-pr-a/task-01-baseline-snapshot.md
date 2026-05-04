# Task 01 — Baseline pre-modifica: snapshot 2 dispatch

**Stato:** [PENDING]
**Owner:** human-in-the-loop (richiede dispatch Agent live)
**Dipende da:** nessuno
**Blocca:** Task 02-09

## Goal

Salvare snapshot output corrente di `mcp-impact-analyst` e `qa-investigator` su 2 dispatch noti, da usare come baseline per AC-3 no-regression diff.

## File coinvolti

- Nuovi: `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-01-mia-pagamento.md`
- Nuovi: `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-02-qa-apigateway.md`

## Step 1 — Snapshot 1: mcp-impact-analyst pre-modifica

Da una sessione Claude Code (può essere questa o separata), dispatcha:

```
Agent({
  subagent_type: "mcp-impact-analyst",
  description: "Pre-flight licenze pagamento",
  prompt: "Devo aggiungere arricchimento profili locale alla conferma pagamento in PagamentoServiceImpl di sport-gestione-licenze-service. Esegui pre-flight."
})
```

Salva l'output completo (blocco markdown ritornato dall'agent) in `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-01-mia-pagamento.md` con header:

```markdown
# Snapshot 1 — mcp-impact-analyst pre-modifica
**Data:** 2026-05-03
**Agent commit:** <hash dell'agent file pre-mod>
**Dispatch prompt:** "Devo aggiungere arricchimento profili locale alla conferma pagamento in PagamentoServiceImpl di sport-gestione-licenze-service. Esegui pre-flight."

---

<output completo dell'agent qui>
```

## Step 2 — Snapshot 2: qa-investigator pre-modifica

Dispatcha:

```
Agent({
  subagent_type: "qa-investigator",
  description: "Caller apigateway-ext auth",
  prompt: "Quali sono i clienti che eseguono chiamate dei MS SPORT contattando apigateway-service-ext e che tipo di auth usano?"
})
```

Salva output in `docs/measurements/2026-05-03-pre-modifica-baseline/snapshot-02-qa-apigateway.md` con stesso header pattern.

## Step 3 — Verifica salvataggio

```bash
ls -la docs/measurements/2026-05-03-pre-modifica-baseline/
```

Output atteso: 2 file `.md` non vuoti (size > 500 bytes ciascuno).

## Step 4 — Commit baseline

```bash
git add docs/measurements/2026-05-03-pre-modifica-baseline/
git commit -m "docs(measurements): baseline pre-modifica agents PR-A (2 snapshot)

Snapshot 1: mcp-impact-analyst su task pagamento sport-gestione-licenze-service
Snapshot 2: qa-investigator su domanda auth apigateway-service-ext

Baseline per AC-3 no-regression diff dopo PR-A.

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 9.1

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] 2 file snapshot salvati in `docs/measurements/2026-05-03-pre-modifica-baseline/`
- [ ] Ogni snapshot contiene output completo dell'agent (non vuoto, formato markdown valido)
- [ ] Commit creato

## Note

Se il dispatch dell'agent fallisce per MCP down o altro, l'agent ritorna `{"applicable": true, "blocked": "mcp_unavailable"}` o simile. Salva comunque quello che ritorna come "snapshot di stato MCP-blocked" — è valido baseline per il diff.
