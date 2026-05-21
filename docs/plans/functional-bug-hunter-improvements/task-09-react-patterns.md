# Task 09 — Add BP-024 + BP-025 in stacks/typescript-javascript.md

**Stato**: [PENDING] · **Effort**: 2h · **File toccati**: 1

## Goal

Chiudere il gap A4 #1 (React recall 50%): aggiungere 2 pattern lifecycle
React/TS che un QA umano ISTQB troverebbe e che oggi sfuggono alla
pattern matrix. Additive nel reference esistente (no split bug_patterns.md).

## Acceptance

- `references/stacks/typescript-javascript.md` contiene:
  - **BP-024 react-lifecycle-race**: pattern per `useEffect` con stale
    closure (deps array incomplete, fetch+setState senza guard).
    Trigger: `useEffect.*\bfetch\b` + assenza `AbortController` + dep
    array che esclude variabili usate dentro.
  - **BP-025 setState-after-unmount**: pattern per cancellation race
    (component unmount con promise pending → setState → warning console
    + state inconsistency).
- Ogni BP ha: id stable, title, trigger condition, actor primitive,
  evidence template, severity hint.
- Allineamento stilistico con BP esistenti in `bug_patterns.md`.

## Implementation

1. Read `references/bug_patterns.md` per format BP-NNN canonico.
2. Read `references/stacks/typescript-javascript.md` per stile inline.
3. Edit `references/stacks/typescript-javascript.md` appendendo le 2
   nuove BP nella sezione apposita (creare se assente).

## Why additive (no catalog split)

Round 2 consensus: split bug_patterns.md in matrix+catalog è
over-engineering (drop ADR-02). BP stack-specific stanno nel reference
del rispettivo stack — è la progressive disclosure naturale.
